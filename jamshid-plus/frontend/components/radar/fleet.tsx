"use client";
import { useMemo, useState } from "react";
import { Server as ServerIcon, Search, SlidersHorizontal, ChevronLeft, ChevronRight, ArrowDownUp, Network, ArrowLeft, BellRing, TriangleAlert, CircleAlert, History, Layers3, Link2, ShieldCheck } from "lucide-react";
import { ALERT_STATES, COUNTRIES, LEVELS, SERVICE_STATES, fa, dayFa, timeFa, toAscii, type AlertState, type Country, type Level, type Snapshot, type Workspace, type Server, type ObservedService } from "@/lib/radar/model";
import { SectionHead, Flag, Status, Badge, Empty, MiniProgress, LevelIcon, type Save, cn } from "./ui";
export const serviceState=(online:boolean,v:ObservedService,awaiting=false)=>awaiting?"در انتظار عامل":!online?"دور از دسترس":v.state==="unknown"?"نامشخص":SERVICE_STATES[v.state];
const serviceTone=(online:boolean,v:ObservedService)=>!online||v.state==="unknown"?"muted":v.state==="active"?"green":v.state==="degraded"?"amber":"red";
export const countries=Object.entries(COUNTRIES) as [Country,string][];
export type OpenServer=(id:string,tab?:string)=>void;
const norm=(s:string)=>toAscii(s.toLowerCase()).replace(/ي/g,"ی").replace(/ك/g,"ک").replace(/[\s‌-]+/g,"");
export function FleetTable({snap,onServer,onAll,initialCountry="",initialStatus="",full=false}:{snap:Snapshot;onServer:OpenServer;onAll:()=>void;initialCountry?:string;initialStatus?:string;full?:boolean}) {
  const [query,setQuery]=useState(""),[country,setCountry]=useState(initialCountry),[status,setStatus]=useState(initialStatus),[service,setService]=useState(""),[group,setGroup]=useState(""),[showFilters,setShow]=useState(!!(initialCountry||initialStatus)),[index,setIndex]=useState(0),[sort,setSort]=useState<""|"name"|"ping">(""),[asc,setAsc]=useState(true);
  const {space,telemetry}=snap, groups=[...new Set(space.servers.map(s=>s.group).filter(Boolean))], services=[...new Set(Object.values(telemetry.metrics).flatMap(m=>m.services.map(v=>v.name)))];
  const active=[country,status,group,service].filter(Boolean).length;
  const filtered=useMemo(()=>{
    const q=norm(query);
    const rows=space.servers.filter(s=>(!q||norm([s.name,s.host,s.city,s.group,COUNTRIES[s.country],...s.domains,...(telemetry.metrics[s.id]?.services??s.services).map(v=>v.name)].join(" ")).includes(q))&&(!country||s.country===country)&&(!status||(status==="pending"?telemetry.metrics[s.id]?.awaiting:!telemetry.metrics[s.id]?.awaiting&&(status==="online")===telemetry.metrics[s.id]?.online))&&(!group||s.group===group)&&(!service||(telemetry.metrics[s.id]?.services??s.services).some(v=>v.name===service)));
    if(sort) rows.sort((a,b)=>(sort==="name"?a.name.localeCompare(b.name,"fa"):(telemetry.metrics[a.id]?.ping??Infinity)-(telemetry.metrics[b.id]?.ping??Infinity))*(asc?1:-1));
    return rows;
  },[space,telemetry,query,country,status,group,service,asc,sort]);
  const limit=full?10:5,pages=Math.max(1,Math.ceil(filtered.length/limit)),page=Math.min(index,pages-1),rows=filtered.slice(page*limit,(page+1)*limit);
  const reset=()=>{setQuery("");setCountry("");setStatus("");setGroup("");setService("");setIndex(0);};
  const setFilter=(fn:(s:string)=>void,v:string)=>{fn(v);setIndex(0);};
  const setOrder=(field:"name"|"ping")=>{setAsc(sort===field?!asc:true);setSort(field);setIndex(0);};
  return <section className="panel table-panel" id="servers-table"><SectionHead title="فهرست سرورها" icon={ServerIcon}>
    <label className="search-input"><Search size={15}/><input aria-label="جستجوی سرورها" placeholder="جستجوی سرور..." value={query} onChange={e=>setFilter(setQuery,e.target.value)}/></label>
    <button className={cn("btn small filter-button",(active>0||showFilters)&&"is-filtered")} onClick={()=>setShow(!showFilters)} aria-expanded={showFilters}><SlidersHorizontal size={15}/>فیلترها{active>0&&<b>{fa(active)}</b>}</button>
    </SectionHead>
    {showFilters&&<div className="filters">
      <label>موقعیت<select value={country} onChange={e=>setFilter(setCountry,e.target.value)}><option value="">همه کشورها</option>{countries.map(([v,t])=><option key={v} value={v}>{t}</option>)}</select></label>
      <label>وضعیت<select value={status} onChange={e=>setFilter(setStatus,e.target.value)}><option value="">همه وضعیت‌ها</option><option value="online">آنلاین</option><option value="offline">آفلاین</option>{telemetry.source==="agent"&&<option value="pending">در انتظار عامل</option>}</select></label>
      <label>سرویس<select value={service} onChange={e=>setFilter(setService,e.target.value)}><option value="">همه سرویس‌ها</option>{services.map(v=><option key={v}>{v}</option>)}</select></label>
      <label>گروه<select value={group} onChange={e=>setFilter(setGroup,e.target.value)}><option value="">همه گروه‌ها</option>{groups.map(v=><option key={v}>{v}</option>)}</select></label>
      {(active>0||query)&&<button className="text-btn" onClick={reset}>پاک کردن فیلترها</button>}
    </div>}
    <div className="table-scroll" role="region" tabIndex={0} aria-label="فهرست سرورها"><table className="fleet-table"><thead><tr>
      <th><button onClick={()=>setOrder("name")}>نام سرور <ArrowDownUp size={11}/></button></th><th>موقعیت</th><th>وضعیت</th><th><button onClick={()=>setOrder("ping")}>پینگ <ArrowDownUp size={11}/></button></th><th>پردازنده</th><th>حافظه</th><th>پورت‌های باز</th><th>سرویس‌ها</th><th aria-label="جزئیات"/>
    </tr></thead><tbody>{rows.map(s=>{const m=telemetry.metrics[s.id],observed=m?.services??[],openPorts=(m?.ports??[]).filter(p=>p.state==="open");return <tr key={s.id} onClick={()=>onServer(s.id)}>
      <td><button className="host-name" onClick={e=>{e.stopPropagation();onServer(s.id);}}><span className={"host-icon "+(m?.online?"":"host-down")}><ServerIcon size={17}/></span><span><strong>{s.name}</strong><small dir="ltr">{s.host}</small></span></button></td>
      <td><span className="country-cell"><Flag code={s.country}/>{COUNTRIES[s.country]}</span></td><td><Status online={m?.online??false} awaiting={m?.awaiting}/></td>
      <td><span className="ping-value" dir="ltr">{m?.ping!=null?<>{fa(m.ping)} <small>ms</small></>:"—"}</span></td><td><MiniProgress value={m?.cpu??null} tone="mint"/></td><td><MiniProgress value={m?.ram??null}/></td>
      <td><span className="port-preview" dir="ltr" title={m?.online?openPorts.map(p=>p.number+"/"+p.protocol).join(" · "):"نامشخص"}>{!m?.online?"—":openPorts.length?openPorts.slice(0,2).map(p=>p.number).join(" · "):((m.portCoverage?.TCP&&m.portCoverage?.UDP))?"۰":"—"}{m?.online&&openPorts.length>2&&<small> +{fa(openPorts.length-2)}</small>}</span></td>
      <td><span className="svc-tags">{observed.slice(0,1).map(v=><span className="svc-tag" dir="auto" key={v.name}>{v.name}</span>)}{observed.length>1&&<span className="svc-extra" dir="ltr" title={observed.slice(1).map(v=>v.name).join("، ")}>+{fa(observed.length-1)}</span>}{observed.length===0&&"—"}</span></td>
      <td><button className="row-arrow" aria-label={`جزئیات ${s.name}`} onClick={e=>{e.stopPropagation();onServer(s.id);}}><ChevronLeft size={16}/></button></td>
    </tr>;})}</tbody></table></div>
    {!rows.length&&<Empty title={space.servers.length?"سروری با این مشخصات پیدا نشد":"هنوز سروری اضافه نکرده‌ای"} detail={space.servers.length?undefined:"از «افزودن سرور»، اولین میزبان خودت را ثبت کن."}>{space.servers.length>0&&<button className="text-btn" onClick={reset}>نمایش همه سرورها</button>}</Empty>}
    <div className="table-foot"><span>{filtered.length?`نمایش ${fa(page*limit+1)} تا ${fa(Math.min((page+1)*limit,filtered.length))} از ${fa(filtered.length)} سرور`:"۰ سرور"}</span><div className="pages">
      {!full&&<button className="text-btn all-link" onClick={onAll}>همه سرورها <ArrowLeft size={13}/></button>}
      <button className="icon-btn pager" aria-label="صفحه قبل" disabled={page===0} onClick={()=>setIndex(page-1)}><ChevronRight size={14}/></button>
      <small>{fa(page+1)} / {fa(pages)}</small>
      <button className="icon-btn pager" aria-label="صفحه بعد" disabled={page+1===pages} onClick={()=>setIndex(page+1)}><ChevronLeft size={14}/></button>
    </div></div>
  </section>;
}
export function AlertList({space,save,onServer,compact=false,onAll}:{space:Workspace;save:Save;onServer:OpenServer;compact?:boolean;onAll?:()=>void}) {
  const [filter,setFilter]=useState<""|AlertState|"current">("current"),[busy,setBusy]=useState("");
  const list=space.alerts.filter(a=>compact?a.state!=="resolved":filter==="current"?a.state!=="resolved":!filter||a.state===filter);
  const rows=compact?list.slice(0,3):list;
  return <section className="panel"><SectionHead icon={BellRing} title={compact?"هشدارهای نیازمند پیگیری":"فهرست هشدارها"}>{compact?<button className="text-btn" onClick={onAll}>همه هشدارها <ArrowLeft size={14}/></button>:<select className="compact-select" value={filter} aria-label="فیلتر وضعیت هشدارها" onChange={e=>setFilter(e.target.value as typeof filter)}><option value="current">هشدارهای جاری</option><option value="">همه وضعیت‌ها</option>{Object.entries(ALERT_STATES).map(([k,t])=><option key={k} value={k}>{t}</option>)}</select>}</SectionHead>
    {rows.map(a=>{const s=space.servers.find(s=>s.id===a.serverId);return <div key={a.id} className="alert-row">
      <span className={"list-mark tone-"+(a.severity==="critical"?"red":"amber")}>{a.severity==="critical"?<CircleAlert size={17}/>:<TriangleAlert size={17}/>}</span>
      <div className="item-main"><strong>{a.title}</strong><div className="item-sub"><button onClick={()=>onServer(a.serverId,"diagnostics")}>{s?.name}</button><i/> <span>{dayFa(a.at)} · {timeFa(a.at)}</span></div>{!compact&&a.body&&<p>{a.body}</p>}</div>
      <Badge dot={false} tone={a.severity==="critical"?"red":"amber"}>{a.severity==="critical"?"بحرانی":"هشدار"}</Badge>
      <select className="compact-select state-select" aria-label={`پیگیری ${a.title}`} value={a.state} disabled={busy===a.id} onChange={async e=>{setBusy(a.id);await save({type:"alert.set",alertId:a.id,state:e.target.value as AlertState},"وضعیت هشدار ذخیره شد.");setBusy("");}}>{Object.entries(ALERT_STATES).map(([v,t])=><option key={v} value={v}>{t}</option>)}</select>
    </div>;})}
    {!rows.length&&<Empty icon={ShieldCheck} title="هشداری با این وضعیت وجود ندارد"/>}
  </section>;
}
export function EventList({space,serverId,onServer,action}:{space:Workspace;serverId?:string;onServer:OpenServer;action?:React.ReactNode}) {
  const [level,setLevel]=useState(""),[count,setCount]=useState(20);
  const rows=space.events.filter(e=>(!serverId||e.serverId===serverId)&&(!level||e.level===level));
  return <section className="panel"><SectionHead title={serverId?"تاریخچه رخدادهای سرور":"تاریخچه رخدادها"} icon={History}>{action}<select aria-label="نوع رخداد" className="compact-select" value={level} onChange={e=>{setLevel(e.target.value);setCount(20);}}><option value="">همه رخدادها</option>{Object.entries(LEVELS).map(([v,t])=><option value={v} key={v}>{t}</option>)}</select></SectionHead>
    {rows.slice(0,count).map(e=><div className="event-row" key={e.id}><LevelIcon level={e.level}/><div className="item-main"><strong>{e.title}</strong><div className="item-sub">{!serverId&&<><button onClick={()=>onServer(e.serverId,"events")}>{space.servers.find(s=>s.id===e.serverId)?.name}</button><i/></>}<span>{LEVELS[e.level]}</span></div>{e.body&&<p>{e.body}</p>}</div><time>{dayFa(e.at)} · {timeFa(e.at)}</time></div>)}
    {!rows.length&&<Empty icon={History} title="رخدادی برای این انتخاب ثبت نشده است"/>}
    {count<rows.length&&<div className="load-more"><button className="btn" onClick={()=>setCount(count+20)}>نمایش رخدادهای بیشتر</button></div>}
  </section>;
}
export function ServiceList({snap,onServer}:{snap:Snapshot;onServer:OpenServer}) {
  const {space,telemetry}=snap;
  const [kind,setKind]=useState(""),[q,setQ]=useState("");
  const all=space.servers.flatMap(s=>(telemetry.metrics[s.id]?.services??[]).map(v=>({s,v})));
  const counts=[{title:"کل سرویس‌ها و تونل‌ها",value:all.length,icon:Layers3,tone:"violet"},{title:"سرویس‌های فعال",value:all.filter(({s,v})=>telemetry.metrics[s.id]?.online&&v.kind==="service"&&v.state==="active").length,icon:ShieldCheck,tone:"green"},{title:"تونل‌های ثبت‌شده",value:all.filter(({v})=>v.kind==="tunnel").length,icon:Link2,tone:"blue"}];
  const list=all.filter(({s,v})=>(!kind||v.kind===kind)&&norm(v.name+s.name+COUNTRIES[s.country]).includes(norm(q)));
  return <><div className="mini-stats">{counts.map(({title,value,icon:I,tone})=><div className={`panel mini-stat tint-${tone}`} key={title}><span className="kpi-icon"><I size={19}/></span><span>{title}</span><strong>{fa(value)}</strong></div>)}</div><section className="panel"><SectionHead title="سرویس‌ها و تونل‌ها" icon={Network}><label className="search-input"><Search size={15}/><input value={q} onChange={e=>setQ(e.target.value)} placeholder="جستجوی سرویس..." aria-label="جستجوی سرویس"/></label><select className="compact-select" aria-label="نوع سرویس" value={kind} onChange={e=>setKind(e.target.value)}><option value="">همه انواع</option><option value="service">سرویس</option><option value="tunnel">تونل</option></select></SectionHead>
    <div className="table-scroll"><table className="simple-table"><thead><tr><th>نام سرویس</th><th>نوع</th><th>سرور</th><th>موقعیت</th><th>وضعیت</th><th/></tr></thead><tbody>{list.map(({s,v})=><tr onClick={()=>onServer(s.id)} key={s.id+v.name}><td><strong dir="auto">{v.name}</strong></td><td>{v.kind==="tunnel"?"تونل":"سرویس"}</td><td><button className="link-btn" onClick={()=>onServer(s.id)}>{s.name}</button></td><td><span className="country-cell"><Flag code={s.country}/>{COUNTRIES[s.country]}</span></td><td><Badge tone={serviceTone(telemetry.metrics[s.id]?.online??false,v)}>{serviceState(telemetry.metrics[s.id]?.online??false,v,telemetry.metrics[s.id]?.awaiting)}</Badge></td><td><ChevronLeft size={14}/></td></tr>)}</tbody></table></div>
    {!list.length&&<Empty title="سرویسی با این فیلتر پیدا نشد"/>}</section></>;
}
