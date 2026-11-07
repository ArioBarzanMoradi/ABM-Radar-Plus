"use client";
import React, { useEffect, useRef, useId } from "react";
import { X, Server, SearchX, CircleAlert, Check, Activity, AlertTriangle, Info, ListFilter } from "lucide-react";
import { COUNTRIES, LEVELS, type Country, type Level, type Command } from "@/lib/radar/model";

export type Save = (command:Command, message?:string)=>Promise<boolean>;
export function uid():string {
  if(typeof crypto.randomUUID==="function")return crypto.randomUUID();
  const bytes=crypto.getRandomValues(new Uint8Array(16));
  bytes[6]=(bytes[6]&15)|64;
  bytes[8]=(bytes[8]&63)|128;
  const hex=Array.from(bytes,b=>b.toString(16).padStart(2,"0")).join("");
  return [hex.slice(0,8),hex.slice(8,12),hex.slice(12,16),hex.slice(16,20),hex.slice(20)].join("-");
}
export const cn=(...parts:(string|false|null|undefined)[])=>parts.filter(Boolean).join(" ");
export function Flag({code}:{code:Country}) {
  const gid=useId().replace(/:/g,"");
  const extra:Partial<Record<Country,string>>={CH:"🇨🇭",CA:"🇨🇦",NL:"🇳🇱",FR:"🇫🇷",GB:"🇬🇧",FI:"🇫🇮",AE:"🇦🇪",SG:"🇸🇬",OTHER:"🌐"};
  if(extra[code])return <span className="flag flag-emoji" aria-hidden="true">{extra[code]}</span>;
  return <svg className="flag" viewBox="0 0 28 20" aria-hidden="true" focusable="false">
    <defs><clipPath id={gid}><rect width="28" height="20" rx="3"/></clipPath></defs>
    <g clipPath={`url(#${gid})`}>
      {code==="DE" && <><path fill="#34363e" d="M0 0h28v7H0z"/><path fill="#d85257" d="M0 7h28v6H0z"/><path fill="#f0bd52" d="M0 13h28v7H0z"/></>}
      {code==="IR" && <><path fill="#35a67b" d="M0 0h28v7H0z"/><path fill="#f0efe9" d="M0 7h28v6H0z"/><path fill="#d44c58" d="M0 13h28v7H0z"/><path d="M14 8v4m-2.1-3.5q-1.1 2.5 1.7 3.2m2.5-3.2q1.1 2.5-1.7 3.2" stroke="#cb4653" strokeWidth=".85" fill="none"/></>}
      {code==="TR" && <><rect width="28" height="20" fill="#da3e51"/><circle cx="11" cy="10" r="5.1" fill="white"/><circle cx="12.5" cy="9.6" r="4.15" fill="#da3e51"/><path d="m17.5 7.4.7 1.9 2 .1-1.6 1.2.5 2-1.6-1.2-1.7 1.1.6-1.9-1.5-1.3h2z" fill="white"/></>}
      {code==="US" && <><rect width="28" height="20" fill="#ede7df"/>{Array.from({length:7},(_,i)=><rect key={i} width="28" y={i*3.1} height="1.55" fill="#c35d68"/>)}<rect width="12.5" height="10.8" fill="#475881"/>{Array.from({length:12},(_,i)=><circle key={i} cx={2+i%4*2.7} cy={2+Math.floor(i/4)*3} r=".65" fill="#faf9f4"/>)}</>}
      <rect x=".35" y=".35" width="27.3" height="19.3" rx="3" stroke="white" opacity=".14" strokeWidth=".7" fill="none"/>
    </g></svg>;
}
export function Badge({children,tone="green",dot=true}:{children:React.ReactNode;tone?:string;dot?:boolean}) {
  return <span className={`badge tone-${tone}`}>{dot && <i/>}{children}</span>;
}
export function Status({online,awaiting=false}:{online:boolean;awaiting?:boolean}){if(awaiting)return <Badge tone="muted">در انتظار عامل</Badge>;return <Badge tone={online?"green":"red"}>{online?"آنلاین":"آفلاین"}</Badge>;}
export function SectionHead({icon:Icon=Server,title,children}:{icon?:React.ElementType;title:string;children?:React.ReactNode}) {
  return <div className="section-head"><div className="section-title"><span className="section-icon"><Icon size={18}/></span><h2>{title}</h2></div><div className="head-tools">{children}</div></div>;
}
export function Empty({title="موردی پیدا نشد",detail,icon:Icon=SearchX,children}:{title?:string;detail?:string;icon?:React.ElementType;children?:React.ReactNode}) {
  return <div className="empty"><span><Icon size={23}/></span><strong>{title}</strong>{detail && <p>{detail}</p>}{children}</div>;
}
export function Modal({title,children,close,wide=false}:{title:string;children:React.ReactNode;close:()=>void;wide?:boolean}) {
  const ref=useRef<HTMLDialogElement>(null);
  const titleId=useId();
  useEffect(()=>{
    const el=ref.current, previous=document.activeElement as HTMLElement|null, old=document.body.style.overflow;
    el?.showModal(); document.body.style.overflow="hidden";
    return ()=>{el?.close();document.body.style.overflow=old;previous?.focus();};
  },[]);
  return <dialog className={cn("modal",wide&&"wide-modal")} aria-labelledby={titleId} ref={ref} onCancel={e=>{e.preventDefault();close();}} onClick={e=>{if(e.target===e.currentTarget){const r=e.currentTarget.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)close();}}}>
    <div className="modal-head"><h2 id={titleId}>{title}</h2><button type="button" onClick={close} className="icon-btn" aria-label="بستن"><X size={18}/></button></div>{children}
  </dialog>;
}
export function Field({label,children,full=false}:{label:string;children:React.ReactNode;full?:boolean}){
  const labelId=useId();
  return <label className={cn("field",full&&"field-full")}><span id={labelId}>{label}</span>{React.Children.map(children,child=>{
    if(!React.isValidElement<React.HTMLAttributes<HTMLElement>>(child)||typeof child.type!=="string"||!["input","select","textarea"].includes(child.type))return child;
    return React.cloneElement(child,{"aria-labelledby":labelId});
  })}</label>;
}
export function LevelIcon({level}:{level:Level}){const I={error:CircleAlert,warning:AlertTriangle,change:ListFilter,info:Info}[level];return <span className={"list-mark tone-"+({error:"red",warning:"amber",change:"violet",info:"blue"}[level])} title={LEVELS[level]}><I size={17}/></span>;}
export function MiniProgress({value,tone="violet"}:{value:number|null;tone?:string}) {return value===null?<span className="missing">—</span>:<div className={"mini-progress "+tone}><span dir="ltr">{value.toLocaleString("fa-IR")}٪</span><i><b style={{width:value+"%"}}/></i></div>;}
export function Feedback({text,error=false}:{text:string;error?:boolean}) {return <div className={cn("feedback",error&&"error")} role={error?"alert":"status"}>{error?<CircleAlert size={16}/>:<Check size={16}/>}<span>{text}</span></div>;}
export function AgentLabel(){return <span className="agent-label"><Activity size={12}/>پایش واقعی</span>;}
