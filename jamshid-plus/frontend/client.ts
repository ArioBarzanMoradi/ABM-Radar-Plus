import { type Command, type Snapshot } from "./lib/radar/model";

let csrf = "";
export let username = "مدیر جمشید پلاس";
export async function privateAPI(path:string,body?:unknown){
  const response=await fetch(path,body===undefined?{cache:"no-store"}:{method:"POST",cache:"no-store",headers:{"Content-Type":"application/json","X-Radar-CSRF":csrf},body:JSON.stringify(body)});
  if(response.status===401){location.assign("/");throw Error("نشست پایان یافته است.");}
  return response;
}
export async function workspaceRequest(body?:{id:string;command:Command}):Promise<Response>{
  return privateAPI("/api/workspace",body);
}
export async function start():Promise<Snapshot>{
  const session=await privateAPI("/api/session");
  if(!session.ok)throw Error("نشست در دسترس نیست.");
  const body=await session.json();csrf=body.csrf;username=body.username;
  const response=await workspaceRequest();
  if(!response.ok)throw Error("دریافت فضای پایش ممکن نشد.");
  return response.json();
}
export async function logout(){const r=await privateAPI("/api/logout",{});if(r.ok)location.replace("/");}
