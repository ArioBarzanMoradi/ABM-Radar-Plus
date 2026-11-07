import { z } from "zod";

export const COUNTRIES = { IR: "ایران", DE: "آلمان", TR: "ترکیه", US: "آمریکا" } as const;
export type Country = keyof typeof COUNTRIES;
export const SERVICE_PRESETS = ["3x-ui", "WireGuard", "Outline", "تونل"];
export const CHECK_TYPES = { ping: "پینگ", tcp: "اتصال به پورت TCP", udp:"بررسی پورت UDP", dns: "بررسی DNS", trace: "ردیابی مسیر" } as const;
export type CheckType = keyof typeof CHECK_TYPES;
export const LEVELS = { error: "خطا", warning: "هشدار", change: "تغییر", info: "اطلاع" } as const;
export const ALERT_STATES = { open: "باز", tracking: "در پیگیری", resolved: "رفع‌شده" } as const;
export const SERVICE_STATES = { active: "فعال", stopped: "متوقف", degraded: "مختل" } as const;
export const PORT_STATES = { open: "باز", closed: "بسته", unknown: "نامشخص" } as const;
export type Level = keyof typeof LEVELS;
export type AlertState = keyof typeof ALERT_STATES;
export const fa = (n: number) => n.toLocaleString("fa-IR");
export const TIME_ZONE = "Asia/Tehran";
const clock = new Intl.DateTimeFormat("fa-IR", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: TIME_ZONE });
const shortDay = new Intl.DateTimeFormat("fa-IR", { month: "short", day: "numeric", timeZone: TIME_ZONE });
const fullDay = new Intl.DateTimeFormat("fa-IR", { weekday: "long", day: "numeric", month: "long", year: "numeric", timeZone: TIME_ZONE });
export const timeFa = (t: number) => clock.format(t);
export const dayFa = (t: number) => shortDay.format(t);
export const dateFa = (t:number) => {
  const parts=Object.fromEntries(fullDay.formatToParts(t).map(v=>[v.type,v.value]));
  return `${parts.weekday}، ${parts.day} ${parts.month} ${parts.year}`;
};
export const toAscii = (x: string) => x.replace(/[۰-۹٠-٩]/g, d => String(d.charCodeAt(0) - (d <= "٩" ? 1632 : 1776)));
export function isHost(value: string): boolean {
  if (!value || value.length > 253 || /[\s/@?#%\\]/.test(value)) return false;
  if (value.includes(":")) {
    if (!/^[\da-fA-F:[\].]+$/.test(value)) return false;
    try { return new URL("http://" + (value.startsWith("[") ? value : `[${value}]`)).hostname.startsWith("["); } catch { return false; }
  }
  if (/^[\d.]+$/.test(value)) return value.split(".").length===4 && value.split(".").every(v=>/^\d{1,3}$/.test(v) && Number(v)<=255);
  try {
    const h = new URL("http://" + value).hostname.replace(/\.$/,"");
    return h.split(".").every(p => /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/i.test(p));
  } catch { return false; }
}
const host = z.string().trim().transform(toAscii).refine(isHost, "یک نشانی IP یا نام میزبان معتبر وارد کنید.");
const label = z.string().trim().min(1, "این فیلد الزامی است.").max(100, "عنوان باید حداکثر ۱۰۰ نویسه باشد.");
const id = z.string().min(1).max(90);
const portNumber = z.number().int().min(1).max(65535);
export const serverForm = z.object({
  name: label, host, country: z.enum(["IR","DE","TR","US"]), city: z.string().trim().max(65),
  group: z.string().trim().max(65), os: z.string().trim().max(70), online: z.boolean(),
  domains: z.array(host).max(100),
  ports: z.array(z.object({number: portNumber, protocol: z.enum(["TCP","UDP"]), state: z.enum(["open","closed","unknown"])})).max(150),
  services: z.array(z.object({name: label, kind: z.enum(["service","tunnel"]), peerId:id.optional(), state: z.enum(["active","stopped","degraded"])})).max(100),
}).superRefine((s,ctx) => {
  if (new Set(s.domains.map(d=>d.toLowerCase())).size!==s.domains.length) ctx.addIssue({code:"custom",message:"دامنهٔ تکراری را حذف کنید."});
  if (new Set(s.ports.map(p=>p.number+p.protocol)).size!==s.ports.length) ctx.addIssue({code:"custom",message:"شمارهٔ پورت و پروتکل تکراری است."});
  if (new Set(s.services.map(v=>v.name.toLowerCase())).size!==s.services.length) ctx.addIssue({code:"custom",message:"نام سرویس‌های هر سرور باید یکتا باشد."});
});
export type ServerForm = z.infer<typeof serverForm>;
export const diagnosticForm=z.object({kind:z.enum(["ping","tcp","udp","dns","trace"]),target:host,port:portNumber.optional()}).refine(v=>(v.kind!=="tcp" && v.kind!=="udp") || v.port!==undefined,{message:"شمارهٔ پورت را در بازهٔ ۱ تا ۶۵۵۳۵ وارد کنید."});
export type DiagnosticForm=z.infer<typeof diagnosticForm>;
export const commandSchema=z.discriminatedUnion("type",[
  z.object({type:z.literal("server.save"),serverId:id,fields:serverForm,expected:z.number().optional()}),
  z.object({type:z.literal("checklist.add"),serverId:id,title:label,steps:z.array(label).min(1).max(55)}),
  z.object({type:z.literal("step.add"),serverId:id,listId:id,title:label}),
  z.object({type:z.literal("step.set"),serverId:id,listId:id,stepId:id,done:z.boolean()}),
  z.object({type:z.literal("note.add"),serverId:id,body:z.string().trim().min(1).max(4000)}),
  z.object({type:z.literal("event.add"),serverId:id,title:label,level:z.enum(["error","warning","change","info"]),body:z.string().trim().max(2000)}),
  z.object({type:z.literal("test.run"),serverId:id,input:diagnosticForm}),
  z.object({type:z.literal("alert.set"),alertId:id,state:z.enum(["open","tracking","resolved"])}),
  z.object({type:z.literal("settings.save"),interval:z.union([z.literal(15),z.literal(30),z.literal(60),z.literal(120)]),auto:z.boolean()}),
]);
export type Command=z.infer<typeof commandSchema>;
export interface Checklist { id:string; title:string; steps:{id:string;title:string;done:boolean}[] }
export interface TestResult { id:string; at:number; input:DiagnosticForm; ok:boolean; inconclusive?:boolean; summary:string; lines:string[]; source:"simulated"|"agent" }
export interface Server extends ServerForm {
  id:string; createdAt:number; editedAt:number; baseline:{ping:number;cpu:number;ram:number};
  pendingTests?:number; lists:Checklist[]; notes:{id:string;at:number;body:string}[]; tests:TestResult[];
}
export interface EventItem { id:string; serverId:string; at:number; title:string; body:string; level:Level }
export interface Alert { id:string; serverId:string; title:string; body:string; at:number; severity:"critical"|"warning"; state:AlertState; transitions?:{at:number;state:AlertState}[] }
export interface Workspace {
  servers:Server[]; events:EventItem[]; alerts:Alert[]; settings:{auto:boolean;interval:15|30|60|120};
}
export interface Change { id:string; at:number; command:Command; result?:TestResult }
export interface ObservedService { name:string; kind:"service"|"tunnel"; peerId?:string; state:keyof typeof SERVICE_STATES|"unknown" }
export interface Reading {
  online:boolean; paired?:boolean; awaiting?:boolean; lastSeen?:number|null; pingTarget?:string; portCoverage?:Record<string,boolean>; ping:number|null; cpu:number|null; ram:number|null;
  ports:ServerForm["ports"]; services:ObservedService[];
}
export interface Point { at:number; cpu:number|null; ram:number|null; ping:number|null; online:number; total:number; alerts:number }
export type WindowKey="6h"|"24h"|"7d";
export const WINDOWS:Record<WindowKey,string>={"6h":"۶ ساعت","24h":"۲۴ ساعت","7d":"۷ روز"};
export interface Telemetry { at:number; metrics:Record<string,Reading>; history:Record<WindowKey,Point[]>; source:"simulated"|"agent" }
export interface Snapshot { space:Workspace; revision:number; telemetry:Telemetry }
export const DEFAULT_STEPS=["بررسی دسترسی به نشانی سرور","آزمایش پورت سرویس","بررسی وضعیت سرویس و تونل","ثبت نتیجهٔ بررسی"];
export function makeChecklist(key:string,title:string,steps:string[]):Checklist {
  return {id:key,title,steps:steps.map((text,i)=>({id:`${key}-${i}`,title:text,done:false}))};
}
