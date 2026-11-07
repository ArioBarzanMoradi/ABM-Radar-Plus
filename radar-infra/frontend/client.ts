import { commandSchema, type Change, type Snapshot, type Workspace } from "./lib/radar/model";
import { createWorkspace } from "./lib/radar/seed";
import { simulatedProvider } from "./lib/radar/monitoring";
import { applyChange } from "./lib/radar/reducer";

export const demo = document.body.dataset.mode === "demo";
let csrf = "";
export let username = "مدیر رادار";
const key="radar-public-demo-v1";
let memory: {space:Workspace;revision:number;requests:string[]}|undefined;
function demoStore(){
  if(memory) return memory;
  try {const saved=JSON.parse(localStorage.getItem(key)||"null");if(saved?.space?.servers&&saved?.space?.settings&&Array.isArray(saved.requests))return memory=saved as NonNullable<typeof memory>;}catch{}
  return memory={space:createWorkspace(Date.now()),revision:0,requests:[]};
}
export async function privateAPI(path:string,body?:unknown){
  if(demo)throw Error("این عملیات فقط از پنل نصب‌شده در دسترس است.");
  const response=await fetch(path,body===undefined?{cache:"no-store"}:{method:"POST",cache:"no-store",headers:{"Content-Type":"application/json","X-Radar-CSRF":csrf},body:JSON.stringify(body)});
  if(response.status===401){location.assign("/");throw Error("نشست پایان یافته است.");}
  return response;
}
export async function workspaceRequest(body?:{id:string;command:Change["command"]}):Promise<Response>{
  if(!demo)return privateAPI("/api/workspace",body);
  const d=demoStore();
  if(body&&!d.requests.includes(body.id)){
    try{
      const command=commandSchema.parse(body.command),at=Date.now();
      const change:Change={command,at,id:body.id};
      const next=structuredClone(d.space);
      if(command.type==="test.run"){
        const s=next.servers.find(h=>h.id===command.serverId);
        if(!s)throw Error("سرور پیدا نشد.");
        change.result=await simulatedProvider.diagnose(next,s,command.input,body.id,at);
      }
      applyChange(next,change);
      const nextStore={space:next,revision:d.revision+1,requests:[...d.requests.slice(-199),body.id]};
      try{localStorage.setItem(key,JSON.stringify(nextStore));}catch{throw Error("فضای ذخیرهٔ نسخهٔ نمایشی در مرورگر در دسترس نیست.");}
      Object.assign(d,nextStore);
    }catch(e){return Response.json({error:e instanceof Error&&/[\u0600-\u06ff]/.test(e.message)?e.message:"فرم معتبر نیست."},{status:400});}
  }
  return Response.json({space:d.space,revision:d.revision,telemetry:await simulatedProvider.snapshot(d.space,Date.now())});
}
export async function start():Promise<Snapshot>{
  if(!demo){
    const s=await privateAPI("/api/session");if(!s.ok)throw Error("نشست در دسترس نیست.");
    const body=await s.json();csrf=body.csrf;username=body.username;
  }
  const r=await workspaceRequest();if(!r.ok)throw Error("دریافت فضای پایش ممکن نشد.");
  return r.json();
}
export async function logout(){const r=await privateAPI("/api/logout",{});if(r.ok)location.replace("/");}
