import {useState} from "react";
import {Radio,KeyRound,Copy,Check,ExternalLink} from "lucide-react";
import {type Reading,dayFa,timeFa} from "@/lib/radar/model";
import {privateAPI} from "@/client";
import {SectionHead,Modal,Feedback,Badge} from "./ui";

export default function Enrollment({id,reading}:{id:string;reading?:Reading}){
  const [paired,setPaired]=useState(!!reading?.paired),[open,setOpen]=useState(false),[token,setToken]=useState(""),[err,setErr]=useState(""),[busy,setBusy]=useState(false),[copied,setCopied]=useState(false);
  const rotate=paired||!!reading?.paired;
  function close(){if(!busy){setOpen(false);setToken("");setErr("");setCopied(false);}}
  async function issue(){
    setBusy(true);setErr("");
    try{const r=await privateAPI("/api/agents/issue",{serverId:id,rotate});const v=await r.json();if(!r.ok)throw Error(v.error||"ساخت کلید ممکن نشد.");setToken(v.token);setPaired(true);}
    catch(e){setErr(e instanceof Error?e.message:"ارتباط برقرار نشد.");}finally{setBusy(false);}
  }
  async function copy(){try{await navigator.clipboard.writeText(token);setCopied(true);}catch{setErr("کلید را از کادر انتخاب و کپی کن.");}}
  return <section className="panel enrollment"><SectionHead title="اتصال عامل لینوکس" icon={Radio}><Badge tone={reading?.lastSeen?"green":"muted"}>{reading?.lastSeen?"نمونه دریافت شده":"در انتظار اتصال"}</Badge></SectionHead><div className="panel-body form-stack">
    <p>{reading?.lastSeen?"آخرین نمونه در "+dayFa(reading.lastSeen)+"، ساعت "+timeFa(reading.lastSeen)+" به پنل رسید.":"کلید این سرور را بگیر و عامل را روی همان میزبان نصب کن. آمار منابع و سرویس‌ها پس از اتصال نمایش داده می‌شود."}</p>
    {reading?.pingTarget&&<p className="form-hint">مقصد پینگ عامل <bdi>{reading.pingTarget}</bdi></p>}
    <div className="enroll-actions"><button className="btn primary fit" onClick={()=>setOpen(true)}><KeyRound size={16}/>{rotate?"جایگزینی کلید عامل":"دریافت کلید نصب عامل"}</button><a className="text-btn" href="./about.html#connect" target="_blank" rel="noreferrer">راهنمای اتصال<ExternalLink size={14}/></a></div>
    </div>{open&&<Modal title="اتصال عامل این سرور" close={close}><div className="modal-body form-stack">
    {token?<><div className="enroll-step"><b>۱</b><div><strong>کلید را کپی کن</strong><p>این کلید فقط همین بار نمایش داده می‌شود.</p></div></div><label className="field"><span>کلید اختصاصی سرور</span><input dir="ltr" readOnly type="text" value={token} onFocus={e=>e.target.select()}/></label><button className="btn fit" onClick={()=>void copy()}>{copied?<Check size={15}/>:<Copy size={15}/>} {copied?"کلید کپی شد":"کپی کلید"}</button>
    <div className="enroll-step"><b>۲</b><div><strong>نصب عامل روی همین سرور</strong><p>از پوشهٔ دانلودشدهٔ پروژه اجرا کن؛ نصب‌کننده نشانی پنل و کلید را می‌پرسد.</p></div></div><pre dir="ltr">sudo bash install-agent.sh</pre>
    <div className="source-box"><Radio size={20}/><div><strong>نشانی اتصال</strong><p>{location.protocol==="https:"?"برای این پنل HTTPS، نشانی زیر را به نصب‌کننده بده:":"برای عامل روی میزبان پنل، نشانی محلی زیر را بده. برای سرور دیگر، نشانی HTTPS پنل یا انتهای تونل SSH روی همان سرور را وارد کن."}</p><code dir="ltr">{location.protocol==="https:"?location.origin:"http://127.0.0.1:8788"}</code></div></div>
    <p className="form-hint">اگر پورت پنل را هنگام نصب تغییر داده‌ای، پورت واقعی را وارد کن. معمولاً نخستین نمونه ظرف ۳۰ ثانیه می‌رسد.</p></>:<><p>{rotate?"با صدور کلید جدید، عامل دارای کلید قبلی باید با کلید تازه پیکربندی شود.":"این کلید فقط اجازهٔ ارسال آمار و دریافت تست‌های همین سرور را به عامل می‌دهد."}</p><button disabled={busy} className="btn primary fit" onClick={()=>void issue()}>{busy?"در حال صدور…":rotate?"جایگزینی کلید":"صدور کلید عامل"}</button></>}
    {err&&<Feedback error text={err}/>}</div></Modal>}</section>;
}
