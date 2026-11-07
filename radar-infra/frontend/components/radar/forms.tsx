"use client";
import { useState } from "react";
import { Plus, Trash2, CircleAlert, Save as SaveIcon, Radio, ListChecks, ChevronLeft } from "lucide-react";
import { COUNTRIES, SERVICE_PRESETS, PORT_STATES, SERVICE_STATES, LEVELS, serverForm, toAscii, fa, type ServerForm, type Server, type Workspace, type Country, type Level, type Command } from "@/lib/radar/model";
import { Modal, Field, Feedback, uid, type Save } from "./ui";

const base:ServerForm={name:"",host:"",country:"IR",city:"",group:"",os:"Ubuntu 24.04",online:true,domains:[],ports:[],services:[]};
export function ServerEditor({server,space,save,close,created,startTab=0,source}:{server?:Server;space:Workspace;save:Save;close:()=>void;created:(id:string)=>void;startTab?:number;source:"simulated"|"agent"}) {
  const [v,setV]=useState<ServerForm>(()=>server?{...server,ports:server.ports.map(p=>({...p})),services:server.services.map(s=>({...s})),domains:[...server.domains]}:{...base});
  const [domains,setDomains]=useState(v.domains.join("\n")),[tab,setTab]=useState(startTab),[busy,setBusy]=useState(false),[error,setError]=useState(""),[newId]=useState(()=>server?.id??uid());
  const set=<K extends keyof ServerForm>(k:K,value:ServerForm[K])=>setV(p=>({...p,[k]:value}));
  const setPort=(i:number,fields:Partial<ServerForm["ports"][number]>)=>set("ports",v.ports.map((p,j)=>i===j?{...p,...fields}:p));
  const setService=(i:number,fields:Partial<ServerForm["services"][number]>)=>set("services",v.services.map((p,j)=>i===j?{...p,...fields}:p));
  const submit=async(e:React.FormEvent)=>{e.preventDefault();if(busy)return;
    const parsed=serverForm.safeParse({...v,domains:domains.split(/[\n,،]+/).map(x=>x.trim()).filter(Boolean)});
    if(!parsed.success){const issue=parsed.error.issues[0],field=String(issue.path[0]??"");
      const msg=/[\u0600-\u06ff]/.test(issue.message)?issue.message:field==="ports"?"شمارهٔ پورت باید بین ۱ و ۶۵۵۳۵ باشد.":"مقادیر واردشده را بررسی کنید.";
      setError(msg);if(field==="services")setTab(2);else if(field==="domains"||field==="ports")setTab(1);else if(field)setTab(0);return;
    }
    setBusy(true);setError("");const ok=await save({type:"server.save",serverId:newId,expected:server?.editedAt,fields:parsed.data},server?"مشخصات سرور ذخیره شد.":"سرور جدید ثبت شد.");setBusy(false);if(ok){close();if(!server)created(newId);}
  };
  return <Modal title={server?`ویرایش ${server.name}`:"افزودن سرور"} close={()=>{if(!busy)close();}}>
    <div className="form-tabs">{["مشخصات سرور","دامنه‌ها و پورت‌ها","سرویس‌ها و تونل‌ها"].map((t,i)=><button key={t} className={tab===i?"active":""} onClick={()=>{setTab(i);setError("");}}>{t}</button>)}</div>
    <form onSubmit={submit} noValidate><div className="modal-body">
      {tab===0&&<div className="form-grid">
        <Field label="نام سرور"><input autoFocus maxLength={100} placeholder="مثلاً تهران ۰۴" value={v.name} onChange={e=>set("name",e.target.value)}/></Field>
        <Field label="کشور"><select value={v.country} onChange={e=>set("country",e.target.value as Country)}>{Object.entries(COUNTRIES).map(([k,n])=><option key={k} value={k}>{n}</option>)}</select></Field>
        <Field full label="نشانی IP یا نام میزبان"><input dir="ltr" placeholder="192.0.2.15" value={v.host} maxLength={253} onChange={e=>set("host",e.target.value)}/></Field>
        <Field label="شهر"><input placeholder="مثلاً تهران" value={v.city} onChange={e=>set("city",e.target.value)} maxLength={65}/></Field>
        <Field label="گروه سرور"><input list="host-groups" placeholder="انتخاب یا افزودن گروه" value={v.group} onChange={e=>set("group",e.target.value)} maxLength={65}/><datalist id="host-groups">{[...new Set(space.servers.map(s=>s.group).filter(Boolean))].map(g=><option value={g} key={g}/>)}</datalist></Field>
        <Field label="سیستم‌عامل"><input dir="auto" value={v.os} onChange={e=>set("os",e.target.value)} maxLength={70}/></Field>
        {source==="simulated"&&<Field label="وضعیت شبیه‌سازی‌شده"><select value={v.online?"online":"offline"} onChange={e=>set("online",e.target.value==="online")}><option value="online">آنلاین</option><option value="offline">آفلاین</option></select></Field>}
      </div>}
      {tab===1&&<div className="form-stack">
        <Field label="دامنه‌ها، هر دامنه در یک سطر"><textarea rows={3} dir="ltr" placeholder="node.example.net" value={domains} onChange={e=>setDomains(e.target.value)}/></Field>
        <div className="subhead"><h3>پورت‌های شبکه</h3><button type="button" className="text-btn" onClick={()=>set("ports",[...v.ports,{number:0,protocol:"TCP",state:"open"}])}><Plus size={14}/>افزودن پورت</button></div>
        {!v.ports.length&&<p className="form-hint">شماره و پروتکل پورت مورد انتظار را وارد کنید.</p>}
        {v.ports.map((p,i)=><div className="array-row" key={i}><Field label="شماره پورت"><input inputMode="numeric" dir="ltr" placeholder="443" value={p.number||""} onChange={e=>setPort(i,{number:Number(toAscii(e.target.value))||0})}/></Field><Field label="پروتکل"><select value={p.protocol} onChange={e=>setPort(i,{protocol:e.target.value as typeof p.protocol})}><option>TCP</option><option>UDP</option></select></Field>{source==="simulated"?<Field label="وضعیت"><select value={p.state} onChange={e=>setPort(i,{state:e.target.value as typeof p.state})}>{Object.entries(PORT_STATES).map(([k,n])=><option value={k} key={k}>{n}</option>)}</select></Field>:<span className="form-hint">اندازه‌گیری توسط عامل</span>}<button type="button" className="icon-btn danger-hover" aria-label={`حذف پورت ${fa(i+1)}`} onClick={()=>set("ports",v.ports.filter((_,j)=>j!==i))}><Trash2 size={15}/></button></div>)}
      </div>}
      {tab===2&&<div className="form-stack"><div className="subhead"><h3>سرویس‌های این سرور</h3><button type="button" className="text-btn" onClick={()=>set("services",[...v.services,{name:"",kind:"service",state:"active"}])}><Plus size={14}/>افزودن سرویس یا تونل</button></div>
        {!v.services.length&&<p className="form-hint">نام سرویس دلخواه یا یکی از گزینه‌های پیشنهادی را ثبت کنید.</p>}
        <datalist id="service-presets">{SERVICE_PRESETS.map(s=><option key={s} value={s}/>)}</datalist>
        {v.services.map((s,i)=><div className="array-row service-edit" key={i}><Field label="نام"><input list="service-presets" dir="auto" placeholder="WireGuard" maxLength={100} value={s.name} onChange={e=>setService(i,{name:e.target.value})}/></Field><Field label="نوع"><select value={s.kind} onChange={e=>setService(i,{kind:e.target.value as typeof s.kind,peerId:undefined})}><option value="service">سرویس</option><option value="tunnel">تونل</option></select></Field>{source==="simulated"?<Field label="وضعیت"><select value={s.state} onChange={e=>setService(i,{state:e.target.value as typeof s.state})}>{Object.entries(SERVICE_STATES).map(([k,n])=><option value={k} key={k}>{n}</option>)}</select></Field>:<span className="form-hint">اندازه‌گیری توسط عامل</span>}<button type="button" aria-label={`حذف سرویس ${fa(i+1)}`} className="icon-btn danger-hover" onClick={()=>set("services",v.services.filter((_,j)=>j!==i))}><Trash2 size={15}/></button>{s.kind==="tunnel"&&<label className="field field-full"><span>مقصد تونل</span><select value={s.peerId??""} onChange={e=>setService(i,{peerId:e.target.value||undefined})}><option value="">خارج از فهرست سرورها</option>{space.servers.filter(h=>h.id!==newId).map(h=><option key={h.id} value={h.id}>{h.name} · {COUNTRIES[h.country]}</option>)}</select></label>}</div>)}
      </div>}
      {error&&<Feedback text={error} error/>}
    </div><div className="modal-foot"><button className="btn primary" disabled={busy}><SaveIcon size={16}/>{busy?"در حال ذخیره…":server?"ذخیره تغییرات":"ثبت سرور"}</button>{tab<2&&<button type="button" className="btn" onClick={()=>setTab(tab+1)}>مرحله بعد<ChevronLeft size={14}/></button>}<button type="button" className="text-btn muted push-left" onClick={close} disabled={busy}>انصراف</button></div></form>
  </Modal>;
}
export type EntryMode="note"|"event"|"checklist"|"step";
export function EntryForm({mode,serverId,listId,save,close}:{mode:EntryMode;serverId:string;listId?:string;save:Save;close:()=>void}) {
  const [title,setTitle]=useState(""),[body,setBody]=useState(""),[level,setLevel]=useState<Level>("change"),[busy,setBusy]=useState(false),[err,setErr]=useState("");
  const names={note:"افزودن یادداشت",event:"ثبت رخداد",checklist:"افزودن چک‌لیست",step:"افزودن مرحله"};
  const submit=async(e:React.FormEvent)=>{e.preventDefault();let command:Command;
    if(mode==="note") command={type:"note.add",serverId,body:body.trim()};
    else if(mode==="step")command={type:"step.add",serverId,listId:listId!,title:title.trim()};
    else if(mode==="event")command={type:"event.add",serverId,title:title.trim(),body:body.trim(),level};
    else {const steps=body.split("\n").map(s=>s.trim()).filter(Boolean);if(!steps.length||steps.length>55||steps.some(s=>s.length>100)){setErr("۱ تا ۵۵ مرحله وارد کنید. هر مرحله حداکثر ۱۰۰ نویسه است.");return;}command={type:"checklist.add",serverId,title:title.trim(),steps};}
    setErr("");setBusy(true);const ok=await save(command,"تغییرات ثبت شد.");setBusy(false);if(ok)close();
  };
  return <Modal title={names[mode]} close={()=>{if(!busy)close();}}><form onSubmit={submit}><div className="modal-body form-stack">
    {mode!=="note"&&<Field label={mode==="step"?"عنوان مرحله":"عنوان"}><input autoFocus required maxLength={100} value={title} onChange={e=>setTitle(e.target.value)}/></Field>}
    {mode==="event"&&<Field label="نوع رخداد"><select value={level} onChange={e=>setLevel(e.target.value as Level)}>{Object.entries(LEVELS).map(([v,t])=><option key={v} value={v}>{t}</option>)}</select></Field>}
    {mode!=="step"&&<Field label={mode==="note"?"متن یادداشت":mode==="checklist"?"مراحل، هر مرحله در یک سطر":"شرح رخداد"}><textarea autoFocus={mode==="note"} rows={5} value={body} required={mode!=="event"} maxLength={mode==="event"?2000:mode==="note"?4000:5555} onChange={e=>setBody(e.target.value)}/></Field>}
    {err&&<Feedback text={err} error/>}
  </div><div className="modal-foot"><button className="btn primary" disabled={busy}><Plus size={15}/>{busy?"در حال ثبت…":"ثبت"}</button><button type="button" className="btn" onClick={close} disabled={busy}>انصراف</button></div></form></Modal>;
}
export function Settings({space,save,close,source}:{source:"simulated"|"agent";space:Workspace;save:Save;close:()=>void}) {
  const [auto,setAuto]=useState(space.settings.auto),[interval,setIntervalValue]=useState(space.settings.interval),[busy,setBusy]=useState(false);
  return <Modal title="تنظیمات پایش" close={()=>{if(!busy)close();}}><form onSubmit={async e=>{e.preventDefault();setBusy(true);const ok=await save({type:"settings.save",auto,interval},"تنظیمات پایش ذخیره شد.");setBusy(false);if(ok)close();}}><div className="modal-body form-stack">
    <div className="setting-row"><div><strong>پایش خودکار</strong><p>به‌روزرسانی شاخص‌ها هنگام باز بودن داشبورد</p></div><button type="button" className={"switch "+(auto?"on":"")} role="switch" aria-label="پایش خودکار" aria-checked={auto} onClick={()=>setAuto(!auto)}><i/></button></div>
    <Field label="فاصله بازخوانی داشبورد"><select value={interval} disabled={!auto} onChange={e=>setIntervalValue(Number(e.target.value) as typeof interval)}>{[15,30,60,120].map(n=><option value={n} key={n}>{fa(n)} ثانیه</option>)}</select></Field>
    <div className="source-box"><Radio size={20}/><div><strong>منبع داده‌ها · {source==="simulated"?"شبیه‌ساز":"عامل سرور"}</strong><p>{source==="simulated"?"شاخص‌ها و تست‌ها در محیط نمونه تولید می‌شوند. پنل نصب‌شده روی لینوکس، داده‌های واقعی را از عامل می‌گیرد.":"شاخص‌ها و نتایج تست از عامل پایش سرور دریافت می‌شوند."}</p></div></div>
  </div><div className="modal-foot"><button className="btn primary" disabled={busy}><SaveIcon size={15}/>ذخیره تنظیمات</button><button type="button" className="btn" onClick={close}>انصراف</button></div></form></Modal>;
}
