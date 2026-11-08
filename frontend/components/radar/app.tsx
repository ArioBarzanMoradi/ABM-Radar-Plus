"use client";
import {workspaceRequest,username,logout,privateAPI} from "@/client";
import {createPortal} from "react-dom";
import {useEffect, useRef, useState, useCallback} from "react";
import { LayoutDashboard, Server as ServerIcon, Network, Bell, History, Settings2, PanelsTopLeft, ChevronLeft, Menu, X, Plus, RefreshCw, CalendarDays, Activity, Radio, Check, CircleAlert, Pencil, ArrowRight, BellRing, MapPin, Clock3, CircleDot, ArrowUpLeft, PanelRight, SlidersHorizontal, SunMoon, ArrowDownToLine } from "lucide-react";
import {COUNTRIES, dateFa, fa, timeFa, type Country, type Snapshot, type Command} from "@/lib/radar/model";
import {OverviewCards, NetworkMap, Trends, type MetricMode} from "./visuals";
import {AlertList, EventList, FleetTable, ServiceList, countries} from "./fleet";
import Mesh from "./mesh";
import {Detail} from "./detail";
import {Settings, ServerEditor} from "./forms";
import {cn, Flag, Status, Empty, uid, AgentLabel} from "./ui";

const navItems=[
 {id:"dashboard",title:"داشبورد",icon:LayoutDashboard},
 {id:"mesh",title:"شبکهٔ پنل‌ها",icon:PanelsTopLeft},
 {id:"servers",title:"سرورها",icon:ServerIcon},
 {id:"services",title:"سرویس‌ها و تونل‌ها",icon:Network},
 {id:"alerts",title:"هشدارها",icon:BellRing},
 {id:"events",title:"رخدادها",icon:History},
];
const headers:Record<string,string>={mesh:"شبکهٔ پنل‌ها",dashboard:"داشبورد زیرساخت",servers:"مدیریت سرورها",services:"سرویس‌ها و تونل‌ها",alerts:"مرکز هشدارها",events:"گزارش رخدادها"};
function readRoute(){return window.location.hash.slice(1)||"dashboard";}
function nav(path:string){if(window.location.hash!=="#"+path)window.location.hash=path;}
function Brand(){return <a className="brand" href="#dashboard" aria-label="ABM Radar Plus، بازگشت به داشبورد"><img src="./assets/favicon.svg" width="43" height="43" alt=""/><span><b dir="ltr">ABM Radar <em>Plus</em></b><small>NETWORK OBSERVATORY</small></span></a>;}
export default function RadarApp({initial,initialIssue=""}:{initial:Snapshot;initialIssue?:string}) {
  const [snap,setSnap]=useState(initial),[route,setRoute]=useState("dashboard"),[drawer,setDrawer]=useState(false),[editor,setEditor]=useState<{id?:string;tab?:number}|null>(null),[settings,setSettings]=useState(false),[mode,setMode]=useState<MetricMode>("resources"),[refreshing,setRefreshing]=useState(false),[issue,setIssue]=useState(initialIssue),[toast,setToast]=useState<{msg:string;error:boolean;key:number}|null>(null);
  const mounted=useRef(true),reading=useRef(false),pending=useRef(new Map<string,string>()),toastCounter=useRef(0);
  const notify=useCallback((msg:string,error=false)=>setToast({msg,error,key:++toastCounter.current}),[]);
  const accept=useCallback((data:Snapshot)=>{if(mounted.current){setSnap(old=>(data.revision>old.revision||(data.revision===old.revision&&data.telemetry.at>=old.telemetry.at))?data:old);setIssue("");}},[]);
  const refresh=useCallback(async(manual=false)=>{
    if(reading.current)return;
    reading.current=true;setRefreshing(true);
    try{const r=await workspaceRequest();if(!r.ok)throw Error(r.status===401?"برای ذخیره و پایش وارد حساب خود شوید.":"ارتباط با فضای پایش قطع است. آخرین داده‌های دریافتی نمایش داده می‌شوند.");
      accept(await r.json());if(manual)notify("شاخص‌های پایش به‌روزرسانی شدند.");
    }catch(e){if(mounted.current){const msg=e instanceof Error&&/[\u0600-\u06ff]/.test(e.message)?e.message:"ارتباط با فضای پایش برقرار نشد.";setIssue(msg);if(manual)notify(msg,true);}}
    finally{reading.current=false;if(mounted.current)setRefreshing(false);}
  },[accept,notify]);
  const save=useCallback(async(command:Command,message?:string)=>{
    const signature=JSON.stringify(command),id=pending.current.get(signature)??uid();pending.current.set(signature,id);
    try{const r=await workspaceRequest({command,id});
      if(!r.ok){let err="ذخیرهٔ تغییرات ممکن نشد. دوباره تلاش کنید.";try{const d=await r.json() as {error?:string};if(d.error)err=d.error;}catch{}if(r.status<500)pending.current.delete(signature);throw Error(err);}
      const data:Snapshot=await r.json();accept(data);pending.current.delete(signature);if(message)notify(command.type==="test.run"?"تست برای عامل این سرور صف شد.":message);return true;
    }catch(e){notify(e instanceof Error&&/[\u0600-\u06ff]/.test(e.message)?e.message:"ارتباط قطع شد. فرم را دوباره ذخیره کنید.",true);return false;}
  },[accept,notify]);
  useEffect(()=>{mounted.current=true;const update=()=>{setRoute(readRoute());setDrawer(false);setEditor(null);window.scrollTo({top:0,behavior:"instant"});};update();if(!window.location.hash)void privateAPI("/api/mesh").then(r=>r.ok?r.json():null).then(d=>{if(mounted.current&&!window.location.hash&&d?.peers?.length)nav("mesh");}).catch(()=>{});window.addEventListener("hashchange",update);
    return ()=>{mounted.current=false;window.removeEventListener("hashchange",update);};},[]);
  useEffect(()=>{if(!snap.space.settings.auto)return;const ping=()=>{if(document.visibilityState==="visible")void refresh();};const id=window.setInterval(ping,snap.space.settings.interval*1000);document.addEventListener("visibilitychange",ping);return()=>{clearInterval(id);document.removeEventListener("visibilitychange",ping);};},[snap.space.settings.auto,snap.space.settings.interval,refresh]);
  useEffect(()=>{if(!toast)return;const t=setTimeout(()=>setToast(null),toast.error?6500:3500);return()=>clearTimeout(t);},[toast]);
  useEffect(()=>{if(!drawer)return;const old=document.body.style.overflow;document.body.style.overflow="hidden";const esc=(e:KeyboardEvent)=>{if(e.key==="Escape")setDrawer(false);};window.addEventListener("keydown",esc);return()=>{document.body.style.overflow=old;window.removeEventListener("keydown",esc);};},[drawer]);
  const [path,qs=""]=route.split("?"),[section,id,tab="overview"]=path.split("/"),current=section==="server"?"servers":section,qp=new URLSearchParams(qs),country=qp.get("country")??"",status=qp.get("status")??"";
  const server=section==="server"?snap.space.servers.find(s=>s.id===id):undefined,showDetail=section==="server"&&!!server,known=navItems.some(i=>i.id===current);
  const open=(id:string,t="overview")=>nav(`server/${encodeURIComponent(id)}/${t}`);
  const region=(c:Country)=>nav("servers?country="+c);
  const activeAlerts=snap.space.alerts.filter(a=>a.state!=="resolved").length,active=snap.space.settings.auto;
  const menuTitle=navItems.find(v=>v.id===current)?.title??"صفحه",headline=showDetail?server!.name:headers[section]??"صفحه پیدا نشد";
  const sub=section==="dashboard"?null:section==="server"?null:section==="servers"?`${fa(snap.space.servers.length)} سرور ثبت‌شده در ${fa(new Set(snap.space.servers.map(s=>s.country)).size)} کشور`:section==="services"?`${fa(snap.space.servers.reduce((v,s)=>v+s.services.length,0))} سرویس و تونل ثبت‌شده در زیرساخت`:section==="events"?`${fa(snap.space.events.length)} رخداد ثبت‌شده در تاریخچهٔ زیرساخت`:section==="alerts"?`${fa(activeAlerts)} هشدار جاری برای بررسی و پیگیری`:"";
  useEffect(()=>{document.title=headline+" | ABM Radar Plus";},[headline]);
  const hitCard=(k:string)=>{if(k==="ping"){setMode("ping");document.getElementById("performance")?.scrollIntoView({behavior:"smooth",block:"center"});}else nav(k==="online"?"servers?status=online":k);};
  return <div className="workspace">
    {drawer&&<button aria-label="بستن فهرست" className="drawer-shade" onClick={()=>setDrawer(false)}/>}
    <aside className={cn("sidebar",drawer&&"opened")}><div className="brand-wrap"><Brand/><button className="drawer-close icon-btn" aria-label="بستن منو" onClick={()=>setDrawer(false)}><X size={18}/></button></div>
      <div className="sidebar-body"><div className="rail-label">فضای کاری</div>
      <nav className="nav-list" aria-label="ناوبری اصلی">{navItems.map(({id,title,icon:I})=><a className={cn("nav-item",current===id&&!country&&"current")} href={"#"+id} onClick={()=>setDrawer(false)} key={id} aria-current={current===id&&!country?"page":undefined}><I size={18}/><span>{title}</span>{id==="alerts"&&activeAlerts>0&&<b className="nav-count">{fa(activeAlerts)}</b>}</a>)}</nav>
      <div className="rail-line"/><div className="rail-label region-heading">موقعیت سرورها</div><nav className="region-list" aria-label="سرورها بر اساس کشور">{countries.filter(([c])=>snap.space.servers.some(s=>s.country===c)).map(([c,n])=><a key={c} className={cn("region-item",section==="servers"&&country===c&&"current")} href={"#servers?country="+c} onClick={()=>setDrawer(false)}><Flag code={c}/><span>{n}</span><small>{fa(snap.space.servers.filter(s=>s.country===c).length)}</small></a>)}{snap.space.servers.length===0&&<p className="rail-empty">موقعیت سرورها پس از افزودن نمایش داده می‌شود.</p>}</nav>
      </div>
      <div className="rail-bottom"><button className="engine" onClick={()=>{setDrawer(false);setSettings(true);}}><div className="engine-heading"><i className={cn("live-dot",!active&&"paused")}/><strong>{active?"پایش خودکار فعال":"پایش خودکار متوقف"}</strong><Activity size={16}/></div><span>{active?`فاصله بازخوانی · ${fa(snap.space.settings.interval)} ثانیه`:"به‌روزرسانی دستی شاخص‌ها"}</span></button>
        <button className="nav-item settings-link" onClick={()=>{setDrawer(false);setSettings(true);}}><Settings2 size={18}/><span>تنظیمات پایش</span></button>
        <div className="profile"><span className="avatar">A</span><div><strong>{username}</strong><small>مدیر زیرساخت</small></div><button className="text-btn push-left" onClick={()=>void logout()}>خروج</button></div>
      </div>
    </aside>
    <div className="main-frame"><header className="topbar"><div className="crumbs"><button className="mobile-menu icon-btn" onClick={()=>setDrawer(true)} aria-label="باز کردن منو" aria-expanded={drawer}><Menu size={20}/></button><PanelRight size={16} className="crumb-icon"/><span>فضای کاری</span><ChevronLeft size={13}/>{showDetail?<><a href="#servers">سرورها</a><ChevronLeft size={13}/><strong>{server!.name}</strong></>:<strong>{menuTitle}</strong>}</div>
    <div className="top-tools"><button className="icon-btn theme-toggle" data-theme-cycle aria-label="تغییر پوسته" title="پوسته: سیستم، تیره یا روشن"><SunMoon size={19}/></button><div className="date"><CalendarDays size={15}/><span>{dateFa(snap.telemetry.at)}</span></div><i className="vertical"/><button aria-label={`هشدارها، ${fa(activeAlerts)} هشدار جاری`} className="notification" onClick={()=>nav("alerts")}><Bell size={19}/>{activeAlerts>0&&<i/>}</button></div></header>
    <main className="content"><div className="hero"><div className="heading-copy"><div className="heading-line"><h1>{headline}</h1><AgentLabel/>{showDetail&&<Status online={!!snap.telemetry.metrics[server!.id]?.online} awaiting={snap.telemetry.metrics[server!.id]?.awaiting}/>}</div>
      {section==="dashboard"?<p className="last-update"><i className="live-dot"/><span>آخرین به‌روزرسانی {timeFa(snap.telemetry.at)} به وقت تهران</span></p>:showDetail?<p className="host-sub"><Flag code={server!.country}/>{COUNTRIES[server!.country]}<i/> <bdi>{server!.host}</bdi>{server!.group&&<><i/>{server!.group}</>}</p>:<p>{sub}</p>}
    </div><div className="hero-actions">{(section==="dashboard"||showDetail)&&<button className="icon-btn refresh" onClick={()=>refresh(true)} disabled={refreshing} aria-label="به‌روزرسانی شاخص‌ها" title="به‌روزرسانی شاخص‌ها"><RefreshCw size={17} className={refreshing?"spin":""}/></button>}
      {showDetail?<><button className="btn back-btn" onClick={()=>nav("servers")}><ArrowRight size={15}/>فهرست سرورها</button><button className="btn primary" onClick={()=>setEditor({id:server!.id})}><Pencil size={15}/>ویرایش سرور</button></>:(section==="dashboard"||section==="servers"||section==="services")&&<button className="btn primary add-server" onClick={()=>setEditor({})}><Plus size={18}/>افزودن سرور</button>}
    </div></div>
    {issue&&<div className="connection-warning" role="status"><CircleAlert size={16}/>{issue}<button className="text-btn" onClick={()=>refresh(true)}>تلاش دوباره</button></div>}
    {section==="dashboard"&&snap.space.servers.length===0&&<section className="panel setup-intro">
      <div className="setup-copy"><span className="eyebrow"><span className="color-dots"><i/><i/><i/><i/></span>ABM Radar Plus · فضای کار تو</span><h2>همهٔ سرورهایت،<br/>در یک نگاه.</h2><p>اولین سرورت را اضافه کن؛ از همان‌جا وضعیت منابع، سرویس‌ها و مسیر شبکه را دنبال کن.</p><div className="setup-actions"><button className="btn primary" onClick={()=>setEditor({})}><Plus size={17}/>اتصال اولین سرور</button><a className="text-btn" href="./about.html#connect" target="_blank" rel="noreferrer">راهنمای اتصال<ArrowUpLeft size={15}/></a></div></div>
      <div className="setup-steps"><div><span>۱</span><section><strong>مشخصات سرور</strong><p>نام، نشانی و موقعیت سرورت را ثبت کن.</p></section><ServerIcon size={20}/></div><div><span>۲</span><section><strong>کلید اختصاصی</strong><p>برای هر سرور، یک کلید عامل بگیر.</p></section><Radio size={20}/></div><div><span>۳</span><section><strong>شروع پایش</strong><p>عامل را نصب کن؛ آمار واقعی خودکار می‌رسد.</p></section><Activity size={20}/></div></div>
    </section>}{section==="dashboard"&&<><OverviewCards snap={snap} go={hitCard}/><div className="analytics-grid"><NetworkMap snap={snap} onRegion={region}/><Trends snap={snap} mode={mode} setMode={setMode}/></div><FleetTable snap={snap} onServer={open} onAll={()=>nav("servers")}/><AlertList space={snap.space} save={save} onServer={open} compact onAll={()=>nav("alerts")}/></>}
    {section==="mesh"&&<Mesh/>}
    {section==="servers"&&<FleetTable key={route} snap={snap} full initialCountry={country} initialStatus={status} onServer={open} onAll={()=>nav("servers")}/>}
    {section==="services"&&<ServiceList snap={snap} onServer={open}/>}
    {section==="events"&&<EventList space={snap.space} onServer={open}/>}
    {section==="alerts"&&<AlertList space={snap.space} save={save} onServer={open}/>}
    {showDetail&&<Detail key={server!.id} snap={snap} server={server!} tab={["overview","health","diagnostics","events","notes"].includes(tab)?tab:"overview"} open={open} save={save} edit={t=>setEditor({id:server!.id,tab:t})}/>}
    {(!known||(section==="server"&&!server))&&<div className="panel"><Empty title="این صفحه پیدا نشد"><a className="text-btn" href="#dashboard">بازگشت به داشبورد</a></Empty></div>}
    </main></div>
    {editor&&<ServerEditor server={editor.id?snap.space.servers.find(s=>s.id===editor.id):undefined} space={snap.space} startTab={editor.tab} save={save} close={()=>setEditor(null)} created={open}/>}
    {settings&&<Settings space={snap.space} save={save} close={()=>setSettings(false)}/>}
    {toast&&createPortal(<div key={toast.key} className={cn("toast",toast.error&&"bad")} role={toast.error?"alert":"status"}>{toast.error?<CircleAlert size={18}/>:<Check size={18}/>}<span>{toast.msg}</span><button onClick={()=>setToast(null)} aria-label="بستن اعلان"><X size={14}/></button></div>,(toast.error&&document.querySelector("dialog[open]"))||document.body)}
  </div>;
}
