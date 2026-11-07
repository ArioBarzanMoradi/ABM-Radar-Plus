import { fa, type DiagnosticForm, type Server, type Workspace, type Reading, type WindowKey, type Point, type Telemetry, type TestResult } from "./model";

/** Agent integrations implement this server-only boundary. No credentials are sent to the UI. */
export interface MonitoringProvider {
  snapshot(space:Workspace,at:number):Promise<Telemetry>;
  diagnose(space:Workspace,server:Server,input:DiagnosticForm,id:string,at:number):Promise<TestResult>;
}
const clamp=(v:number,a:number,b:number)=>Math.min(b,Math.max(a,v));
function hash(s:string) { let n=0; for (const c of s) n=(n*31+c.charCodeAt(0))>>>0; return n; }
function reading(s:Server,t:number):Pick<Reading,"online"|"ping"|"cpu"|"ram"> {
  if (!s.online) return {online:false,ping:null,cpu:null,ram:null};
  const seed=hash(s.id)%887, x=Math.floor(t/15000)/8;
  const wave=(period:number,phase:number)=>Math.sin(x/period+phase);
  const shared=(wave(65,0)*5+wave(37,1)*3+wave(134,0.7)*6);
  return {online:true,ping:Math.max(1,Math.round(s.baseline.ping+shared*.4+wave(9,seed)*3)),cpu:Math.round(clamp(s.baseline.cpu+shared+wave(13,seed)*6,2,99)),ram:Math.round(clamp(s.baseline.ram+wave(89,1)*6+wave(51,2)*3+wave(14,seed)*3,3,99))};
}
function point(space:Workspace,t:number):Point {
  const hosts=space.servers.filter(s=>s.createdAt<=t);
  const m=hosts.map(s=>reading(s,t)).filter(m=>m.online);
  const avg=(k:"cpu"|"ram"|"ping")=>Math.round(m.reduce((n,v)=>n+(v[k]??0),0)/Math.max(1,m.length));
  return {at:t,cpu:avg("cpu"),ram:avg("ram"),ping:avg("ping"),online:m.length,total:hosts.length,alerts:space.alerts.filter(a=>a.at<=t && (a.transitions?.filter(v=>v.at<=t).at(-1)?.state??(a.transitions?.length?"open":a.state))!=="resolved").length};
}
const periods:Record<WindowKey,number>={"6h":21600000,"24h":86400000,"7d":604800000};
export const simulatedProvider:MonitoringProvider={
  async snapshot(space,at) {
    const metrics:Record<string,Reading>={};
    for (const s of space.servers) {
      const sample=reading(s,at);
      metrics[s.id]={...sample,ports:s.ports.map(p=>({...p,state:sample.online?p.state:"unknown"})),
        services:s.services.map(v=>({...v,state:sample.online?v.state:"unknown"}))};
    }
    const history={} as Telemetry["history"];
    for(const k of Object.keys(periods) as WindowKey[]) {
      history[k]=Array.from({length:39},(_,i)=>point(space,at-periods[k]*(38-i)/38));
    }
    return {at,source:"simulated",metrics,history};
  },
  async diagnose(space,server,input,id,at) {
    const target=input.target.toLowerCase().replace(/\.$/,"");
    const dest=space.servers.find(s=>[s.host,...s.domains].some(h=>h.toLowerCase().replace(/\.$/,"")===target));
    const proto=input.kind==="udp"?"UDP":"TCP";
    const port=dest?.ports.find(p=>p.number===input.port && p.protocol===proto);
    const remoteUp=dest?dest.online:!target.endsWith(".invalid");
    const external=!dest;
    const syntheticIp="203.0.113."+(1+hash(target)%253);
    const remoteIP=dest?.host??syntheticIp;
    const ms=dest?Math.max(1,Math.round(((reading(dest,at).ping??dest.baseline.ping)+(reading(server,at).ping??0))/2)):23+hash(server.id+target)%115;
    let ok=server.online&&remoteUp, summary="", lines:string[]=[];
    if(!server.online) {ok=false;summary="مبدأ تست آفلاین است.";lines=["ارسال درخواست از این سرور ممکن نیست."];}
    else if(input.kind==="dns") {
      const domain=!target.includes(":")&&!/^[\d.]+$/.test(target);
      ok=domain&&(dest?dest.domains.some(d=>d.toLowerCase().replace(/\.$/,"")===target):remoteUp);
      summary=ok?"دامنه با موفقیت به نشانی میزبان تبدیل شد.":"برای این ورودی رکورد دامنه‌ای در شبیه‌سازی وجود ندارد.";
      lines=ok?[`${target} → ${remoteIP}`]:["یک نام دامنه معتبر را برای جستجوی DNS وارد کنید."];
    } else if(!remoteUp) {ok=false;summary="مهلت دریافت پاسخ پایان یافت.";lines=["مقصد در شبیه‌سازی آفلاین است.","پاسخی از میزبان دریافت نشد."];}
    else if(input.kind==="tcp" || input.kind==="udp") {
      const typical=proto==="UDP"?[53,51820]:[80,443];
      ok=dest?port?.state==="open":typical.includes(input.port??0);
      summary=proto==="UDP"?(ok?"پاسخ نمونه از سرویس UDP دریافت شد.":"پاسخی از سرویس UDP دریافت نشد."):(ok?"اتصال به پورت برقرار شد.":"اتصال به پورت برقرار نشد.");
      lines=[`${input.target} · ${proto}/${input.port}`,ok?`زمان پاسخ: ${fa(ms)} میلی‌ثانیه`:port?.state==="closed"?"وضعیت نمونهٔ پورت: بسته":"پورت پاسخ‌گو در الگوی مقصد ثبت نشده است."];
    } else if(input.kind==="trace") {
      summary="مسیر نمونه تا مقصد کامل شد.";lines=[`۱. مبدأ · ${server.host}`,`۲. گذرگاه نمونه · ${fa(Math.max(1,Math.round(ms/2)))} میلی‌ثانیه`,`۳. مقصد · ${dest?.host??input.target} · ${fa(ms)} میلی‌ثانیه`];
    } else {summary=`۴ پاسخ دریافت شد؛ میانگین تأخیر ${fa(ms)} میلی‌ثانیه.`;lines=[`حداقل ${fa(Math.max(1,ms-2))} · میانگین ${fa(ms)} · حداکثر ${fa(ms+2)} میلی‌ثانیه`,"بستهٔ ازدست‌رفته: ۰٪"];}
    if(external&&server.online)lines.push("مقصد خارج از فهرست سرورهاست. این نتیجه بر اساس الگوی نمونهٔ مقصد ساخته شد.");
    return {id,at,input,ok,summary,lines,source:"simulated"};
  }
};
export function getMonitoringProvider():MonitoringProvider { return simulatedProvider; }
