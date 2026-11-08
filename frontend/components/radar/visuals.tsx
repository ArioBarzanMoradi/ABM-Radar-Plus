"use client";
import { useId, useState } from "react";
import { Server, ServerCog, Activity, BellRing, Globe2, Maximize2, ChartNoAxesCombined, ChevronDown, ArrowDownLeft, MapPin } from "lucide-react";
import {COUNTRIES, WINDOWS, fa, dayFa, timeFa, type Country, type Snapshot, type WindowKey, type Point } from "@/lib/radar/model";
import {SectionHead, Flag, Modal, cn} from "./ui";

export type MetricMode="resources"|"ping"|"traffic";
const keys=Object.keys(COUNTRIES) as Country[];
const avg=(a:number[])=>a.length?Math.round(a.reduce((v,n)=>v+n,0)/a.length):0;
function smooth(pts:[number,number][]) {
  if(!pts.length) return "";
  let d=`M${pts[0][0]},${pts[0][1]}`;
  for(let i=1;i<pts.length;i++){ const a=pts[i-1], b=pts[i], pre=pts[i-2]||a, after=pts[i+1]||b;
    d+=` C${a[0]+(b[0]-pre[0])/6},${a[1]+(b[1]-pre[1])/6} ${b[0]-(after[0]-a[0])/6},${b[1]-(after[1]-a[1])/6} ${b[0]},${b[1]}`;
  }
  return d;
}
function Spark({values,bars=false}:{values:number[];bars?:boolean}) {
  const g=useId().replace(/:/g,"");
  const lo=Math.min(...values),hi=Math.max(...values),p=values.map((n,i)=>[2+i*89/Math.max(1,values.length-1),27-(n-lo)*19/(hi-lo||1)] as [number,number]);
  return <svg className="spark" viewBox="0 0 94 33" aria-hidden="true" preserveAspectRatio="none">
    <defs><linearGradient id={g} x1="0" y1="0" x2="0" y2="1"><stop stopColor="currentColor" stopOpacity=".22"/><stop offset="1" stopColor="currentColor" stopOpacity="0"/></linearGradient></defs>
    {bars?p.map(([x,y],i)=><rect key={i} x={x-1} y={y-1} width={Math.min(8,57/p.length)} height={30-y} rx="1.4" fill="currentColor" opacity={.3+.68*i/p.length}/>):<><path d={smooth(p)+" L91,33 L2,33Z"} fill={`url(#${g})`}/><path d={smooth(p)} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/></>}
  </svg>;
}
export function OverviewCards({snap,go}:{snap:Snapshot;go:(which:string)=>void}) {
  const {space,telemetry}=snap, all=space.servers.length, online=Object.values(telemetry.metrics).filter(m=>m.online), alerts=space.alerts.filter(a=>a.state!=="resolved"), regions=new Set(space.servers.map(s=>s.country)).size;
  const waiting=Object.values(telemetry.metrics).filter(m=>m.awaiting).length;
  const pingValues=online.flatMap(m=>m.ping===null?[]:[m.ping]);
  const h=telemetry.history["24h"], byRegion=keys.map(c=>space.servers.filter(s=>s.country===c).length);
  const sparkHosts=space.servers.slice(0,15).map(s=>telemetry.metrics[s.id]?.online?1:0);
  const cards=[
    {id:"servers",title:"کل سرورها",value:all,detail:`${fa(regions)} موقعیت جغرافیایی`,icon:Server,tone:"violet",v:byRegion,bars:true},
    {id:"online",title:"سرورهای آنلاین",value:online.length,detail:waiting?`${fa(waiting)} در انتظار عامل · ${fa(all-online.length-waiting)} آفلاین`:`${fa(all-online.length)} سرور آفلاین`,icon:ServerCog,tone:"green",v:sparkHosts,bars:true},
    {id:"ping",title:"میانگین پینگ",value:pingValues.length?avg(pingValues):null,detail:"بین سرورهای آنلاین",icon:Activity,tone:"blue",v:h.flatMap(p=>p.ping==null?[]:[p.ping]).slice(-20),unit:"ms"},
    {id:"alerts",title:"هشدارهای جاری",value:alerts.length,detail:`${fa(alerts.filter(a=>a.severity==="critical").length)} هشدار بحرانی`,icon:BellRing,tone:"amber",v:alerts.length?h.map(p=>p.alerts).slice(-20):[0,0]},
  ];
  return <div className="kpis">{cards.map(({id,title,value,icon:I,tone,v,bars,detail,unit})=><button className={`kpi tint-${tone}`} key={id} onClick={()=>go(id)}>
    <div className="kpi-head"><span className="kpi-icon"><I size={19}/></span><span>{title}</span></div>
    <div className="kpi-bottom"><div><div className="kpi-number">{value===null?"—":fa(value)}{unit&&<small dir="ltr">{unit}</small>}</div><div className="kpi-detail">{detail}</div></div>
      {id==="servers"&&all>0?<div className="country-bars" aria-hidden="true">{byRegion.map((n,i)=><i key={i} style={{height:8+n*4+"px"}}/>)}</div>:
       id==="online"?<div className="health-ticks" aria-hidden="true">{sparkHosts.map((x,i)=><i key={i} className={x?"up":""}/>)}</div>:v.length>1&&id!=="alerts"&&id!=="servers"?<Spark values={v} bars={bars}/>:null}
    </div>
  </button>)}</div>;
}
const anchors:Record<Country,{lon:number;lat:number;dx:number;dy:number;color:string}>={US:{lon:-97,lat:38,dx:-11,dy:27,color:"#8ab4f8"},DE:{lon:9,lat:51.5,dx:-15,dy:-24,color:"#8ab4f8"},TR:{lon:33,lat:39,dx:-9,dy:36,color:"#fbbc04"},IR:{lon:53,lat:33,dx:33,dy:12,color:"#81c995"},CH:{lon:8.2,lat:46.8,dx:-44,dy:24,color:"#f28b82"},CA:{lon:-106,lat:56,dx:-20,dy:-18,color:"#f28b82"},NL:{lon:5.3,lat:52.2,dx:-32,dy:-44,color:"#fbbc04"},FR:{lon:2.2,lat:46.2,dx:-51,dy:-8,color:"#8ab4f8"},GB:{lon:-2,lat:54,dx:-45,dy:-22,color:"#8ab4f8"},FI:{lon:26,lat:64,dx:8,dy:-21,color:"#81c995"},AE:{lon:54,lat:24,dx:25,dy:20,color:"#f28b82"},SG:{lon:104,lat:1.4,dx:15,dy:20,color:"#fbbc04"},OTHER:{lon:0,lat:0,dx:0,dy:0,color:"#8ab4f8"}};
const xy=(lon:number,lat:number)=>[360+lon*1.90*(1-.17*(Math.abs(lat)/86)**2),9+(83-lat)*1.79];
function Atlas({snap,onRegion,large=false}:{snap:Snapshot;onRegion:(c:Country)=>void;large?:boolean}) {
  const prefix=useId().replace(/:/g,"");
  const active=keys.filter(code=>code!=="OTHER"&&snap.space.servers.some(s=>s.country===code));
  const nodes=Object.fromEntries(keys.map(k=>[k,xy(anchors[k].lon,anchors[k].lat)])) as Record<Country,number[]>;
  const routes:[Country,Country,number,string][]=[];
  const pairs=new Set<string>();
  for(const s of snap.space.servers) {
    for(const link of snap.telemetry.metrics[s.id]?.services??[]) {
      const peer=link.kind==="tunnel"&&link.peerId?snap.space.servers.find(h=>h.id===link.peerId):undefined;
      if(!peer||peer.country===s.country||peer.country==="OTHER"||s.country==="OTHER")continue;
      const pair=[s.country,peer.country].sort().join("-");
      if(pairs.has(pair))continue;
      pairs.add(pair);
      const width=Math.abs(nodes[s.country][0]-nodes[peer.country][0]);
      routes.push([s.country,peer.country,Math.max(14,Math.min(70,width*.38)),width<60?"#76daca":"#8ab4f8"]);
    }
  }
  return <div className={cn("atlas-wrap",large&&"atlas-large")}><svg className="atlas" viewBox="0 0 720 270" preserveAspectRatio="none" aria-label="نقشهٔ موقعیت سرورهای ثبت‌شده" role="group">
    <defs>
      <pattern id={prefix+"grid"} width="44" height="37" patternUnits="userSpaceOnUse"><path d="M44 0H0V37" fill="none" stroke="#414356" strokeOpacity=".24" strokeWidth=".7"/><circle r="1.05" fill="#646078" opacity=".3"/></pattern>
      <filter id={prefix+"glow"} x="-120%" y="-120%" width="340%" height="340%"><feGaussianBlur stdDeviation="2.7"/></filter>
      <radialGradient id={prefix+"light"}><stop stopColor="#66569e" stopOpacity=".18"/><stop offset="1" stopColor="#66569e" stopOpacity="0"/></radialGradient>
    </defs>
    <rect width="720" height="270" fill={`url(#${prefix}grid)`}/><ellipse cx="398" cy="102" rx="242" ry="115" fill={`url(#${prefix}light)`}/>
    <image href="./assets/atlas.svg" width="720" height="270"/>
    {routes.filter(([a,b])=>active.includes(a)&&active.includes(b)).map(([a,b,h,col])=>{
      const [x,y]=nodes[a],[u,v]=nodes[b],d=`M${x},${y} Q${(x+u)/2},${Math.min(y,v)-h} ${u},${v}`;
      return <g key={a+b}><path d={d} fill="none" stroke={col} strokeWidth="4.6" opacity=".22" filter={`url(#${prefix}glow)`}/><path d={d} fill="none" stroke={col} strokeWidth="1.55" opacity=".96"/><path d={d} fill="none" stroke="#f6f1ff" strokeDasharray="2 155" strokeWidth="1.9" opacity=".78" className="link-signal"/></g>;
    })}
    {active.map(k=>{
      const [x,y]=nodes[k],{dx,dy,color}=anchors[k],n=snap.space.servers.filter(s=>s.country===k).length;
      const w=k==="US"?47:43;
      const minX=Math.min(x-16,x+dx-w/2),maxX=Math.max(x+16,x+dx+w/2);
      const minY=Math.min(y-16,y+dy-10),maxY=Math.max(y+16,y+dy+10);
      return <g key={k} className="map-node" tabIndex={0} role="button" aria-label={`سرورهای ${COUNTRIES[k]}، ${fa(n)} سرور`} onClick={()=>onRegion(k)} onKeyDown={e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();onRegion(k);}}}>
        <rect className="map-hit" x={minX} y={minY} width={maxX-minX} height={maxY-minY} fill="transparent" pointerEvents="all"/>
        {k==="IR"&&<circle cx={x} cy={y} r="21" fill="none" stroke={color} strokeOpacity=".18" strokeWidth=".8"/>}
        <circle cx={x} cy={y} r="15" fill={color} fillOpacity=".11"/><circle cx={x} cy={y} r="9.5" fill={color} fillOpacity=".16" stroke={color} strokeOpacity=".48" strokeWidth="1"/>
        <circle cx={x} cy={y} r="4.3" fill={color} stroke="#f3edff" strokeWidth="1.2"/>
        <path d={`M${x},${y+(dy<0?-7:7)} L${x+dx},${y+dy}`} stroke={color} strokeOpacity=".55" fill="none" strokeWidth=".8"/>
        <rect x={x+dx-w/2} y={y+dy-9} width={w} height="18" rx="5" fill="#212330" stroke={color} strokeOpacity=".38" strokeWidth=".8"/>
        <text x={x+dx} y={y+dy+3.7} fill="#e7e5f0" textAnchor="middle" fontSize="11" fontWeight="550">{COUNTRIES[k]}</text>
      </g>;
    })}
  </svg></div>;
}
export function NetworkMap({snap,onRegion}:{snap:Snapshot;onRegion:(c:Country)=>void}) {
  const [max,setMax]=useState(false);
  const footer=<div className="map-foot">{keys.filter(k=>snap.space.servers.some(s=>s.country===k)).map(k=><button key={k} onClick={()=>{setMax(false);onRegion(k);}}><Flag code={k}/><span>{COUNTRIES[k]}</span><b>{fa(snap.space.servers.filter(s=>s.country===k).length)}</b></button>)}</div>;
  return <section className="panel map-panel"><SectionHead title="نقشه زیرساخت" icon={Globe2}><button className="icon-btn quiet" title="بزرگ‌نمایی نقشه" aria-label="بزرگ‌نمایی نقشه" onClick={()=>setMax(true)}><Maximize2 size={15}/></button></SectionHead>
    <Atlas snap={snap} onRegion={onRegion}/>{snap.space.servers.length?footer:<p className="map-empty">سرورت را اضافه کن تا موقعیتش اینجا روشن شود.</p>}
    {max&&<Modal title="نقشه زیرساخت" wide close={()=>setMax(false)}><Atlas snap={snap} onRegion={k=>{setMax(false);onRegion(k);}} large/>{footer}</Modal>}
  </section>;
}
export function Trends({snap,mode,setMode}:{snap:Snapshot;mode:MetricMode;setMode:(m:MetricMode)=>void}) {
  const [range,setRange]=useState<WindowKey>("24h"),[hover,setHover]=useState<number|null>(null);
  const src=snap.telemetry.history[range].map(p=>({...p,rx:p.rx==null?null:p.rx/1024,tx:p.tx==null?null:p.tx/1024})),g=useId().replace(/:/g,"");
  const ping=mode==="ping",traffic=mode==="traffic", tracks: {key:"ping"|"ram"|"cpu"|"disk"|"rx"|"tx";name:string;color:string}[]=traffic?[{key:"rx",name:"دریافت",color:"#8ab4f8"},{key:"tx",name:"ارسال",color:"#81c995"}]:ping?[{key:"ping" as const,name:"میانگین پینگ",color:"#80b6ff"}]:[{key:"ram" as const,name:"حافظه",color:"#8ab4f8"},{key:"cpu" as const,name:"پردازنده",color:"#81c995"},{key:"disk",name:"دیسک",color:"#fdd663"}];
  const high=traffic?Math.max(1,Math.ceil(Math.max(0,...src.flatMap(p=>[p.rx??0,p.tx??0]))*1.15)):ping?Math.max(60,Math.ceil(Math.max(0,...src.map(p=>p.ping??0))/20)*20):100;
  const W=400,H=148,L=29,R=5,B=15,T=9,PW=W-L-R,PH=H-B-T;
  const x=(i:number)=>L+i*PW/(src.length-1),y=(v:number)=>T+PH*(1-v/high);
  const point=hover!==null?src[hover]:null;
  return <section className="panel trends" id="performance"><SectionHead title="روند عملکرد" icon={ChartNoAxesCombined}><label className="range"><select value={range} aria-label="بازه زمانی نمودار" onChange={e=>{setRange(e.target.value as WindowKey);setHover(null);}}>{(Object.entries(WINDOWS) as [WindowKey,string][]).map(([v,l])=><option value={v} key={v}>{l} گذشته</option>)}</select><ChevronDown size={12}/></label></SectionHead>
    <div className="chart-meta"><div className="chart-legends">{tracks.map(t=><span key={t.key}><i style={{background:t.color}}/>{t.name}</span>)}</div><span>{traffic?"KiB/s":ping?"میلی‌ثانیه":"درصد مصرف"}</span></div>
    <div className="plot-shell" tabIndex={0} aria-label="نمودار روند. با کلیدهای جهت، نمونه‌های زمانی را مرور کنید." onBlur={()=>setHover(null)} onKeyDown={e=>{
      if(e.key==="ArrowLeft"||e.key==="ArrowRight"){e.preventDefault();setHover(i=>Math.max(0,Math.min(src.length-1,(i??0)+(e.key==="ArrowRight"?1:-1))));}
    }}>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" onPointerMove={e=>{const rect=e.currentTarget.getBoundingClientRect(),p=(e.clientX-rect.left)/rect.width*W;setHover(Math.min(src.length-1,Math.max(0,Math.round((p-L)/PW*(src.length-1)))));}} onPointerLeave={()=>setHover(null)} role="img" aria-label={traffic?"روند دریافت و ارسال شبکه":ping?"روند میانگین تأخیر":"روند مصرف پردازنده، حافظه و دیسک"}>
        <defs>{tracks.map(t=><linearGradient key={t.key} id={g+t.key} x1="0" x2="0" y1="0" y2="1"><stop stopColor={t.color} stopOpacity=".21"/><stop offset="1" stopColor={t.color} stopOpacity=".012"/></linearGradient>)}</defs>
        {[0,1,2,3,4].map(i=>{const v=high*i/4;return <g key={i}><path d={`M${L} ${y(v)}H${W-R}`} stroke="#323541" strokeWidth=".8" strokeDasharray="3 4"/><text x="1" y={y(v)+3} textAnchor="start" fill="#838698" fontSize="10.3" direction="ltr">{fa(Math.round(v))}{!ping&&!traffic&&"٪"}</text></g>;})}
        {tracks.map(t=>{const runs:[number,number][][]=[];let part:[number,number][]=[];
          src.forEach((v,i)=>{const n=v[t.key];if(n==null){part=[];return;}if(!part.length)runs.push(part);part.push([x(i),y(n)]);});
          return runs.map((p,j)=>p.length===1?<circle key={t.key+j} cx={p[0][0]} cy={p[0][1]} r="3" fill={t.color}/>:<g key={t.key+j}><path d={smooth(p)+` L${p[p.length-1][0]},${H-B} H${p[0][0]} Z`} fill={`url(#${g+t.key})`}/><path d={smooth(p)} fill="none" stroke={t.color} strokeWidth="2.35" vectorEffect="non-scaling-stroke" strokeLinecap="round" strokeLinejoin="round"/></g>);})}
        {hover!==null&&point&&<g><path d={`M${x(hover)},${T}V${H-B}`} stroke="#a29baa" strokeDasharray="3 3"/>{tracks.filter(t=>point[t.key]!=null).map(t=><circle key={t.key} cx={x(hover)} cy={y(point[t.key]??0)} r="3.3" fill={t.color} stroke="#181b23" strokeWidth="1.5"/>)}</g>}
      </svg>
      {!src.some(p=>tracks.some(t=>p[t.key]!=null))&&<span className="empty-plot">در این بازه نمونه‌ای ثبت نشده است.</span>}<div className="x-axis">{[0,.25,.5,.75,1].map(i=>{const t=src[0].at+i*(src[src.length-1].at-src[0].at);return <span key={i}>{range==="7d"?dayFa(t):timeFa(t)}</span>;})}</div>
      {point&&<div className="plot-tip" style={{left:Math.min(68,Math.max(4,((hover??0)/(src.length-1))*87))+"%"}}><b>{dayFa(point.at)} · {timeFa(point.at)}</b>{tracks.map(t=><span key={t.key}>{t.name} <strong>{point[t.key]==null?"—":fa(point[t.key]!)+(traffic?" KiB/s":ping?" ms":"٪")}</strong></span>)}</div>}
    </div>
    <div className="chart-foot"><div className="segmented"><button className={mode==="resources"?"selected":""} onClick={()=>{setHover(null);setMode("resources");}}>مصرف منابع</button><button className={ping?"selected":""} onClick={()=>{setHover(null);setMode("ping");}}>تأخیر شبکه</button><button className={traffic?"selected":""} onClick={()=>{setHover(null);setMode("traffic");}}>ترافیک</button></div><Activity size={16}/></div>
  </section>;
}
