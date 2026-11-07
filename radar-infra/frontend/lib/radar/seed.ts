import { DEFAULT_STEPS, makeChecklist, type Server, type Workspace, type Country, type Level } from "./model";

type HostSpec=[string,string,Country,string,string,string,number,number,number,boolean,string[]];
const HOSTS:HostSpec[]=[
  ["tehran-01","تهران ۰۱","IR","تهران","ورودی ایران","192.0.2.11",19,32,54,true,["3x-ui","تونل فرانکفورت"]],
  ["frankfurt-01","فرانکفورت ۰۱","DE","فرانکفورت","خروجی اروپا","198.51.100.21",52,45,61,true,["3x-ui","WireGuard","Outline","تونل نیویورک"]],
  ["istanbul-01","استانبول ۰۱","TR","استانبول","خروجی اروپا","203.0.113.31",38,51,65,true,["WireGuard","Outline"]],
  ["losangeles-01","لس‌آنجلس ۰۱","US","لس‌آنجلس","خروجی آمریکا","198.51.100.41",104,35,53,false,["Outline","3x-ui"]],
  ["tehran-02","تهران ۰۲","IR","تهران","ورودی ایران","192.0.2.12",21,28,42,true,["WireGuard","تونل استانبول"]],
  ["nuremberg-01","نورنبرگ ۰۱","DE","نورنبرگ","پشتیبان","198.51.100.22",56,34,50,true,["3x-ui","Outline"]],
  ["istanbul-02","استانبول ۰۲","TR","استانبول","خروجی اروپا","203.0.113.32",35,83,72,true,["3x-ui","WireGuard"]],
  ["newyork-01","نیویورک ۰۱","US","نیویورک","خروجی آمریکا","198.51.100.42",92,42,58,true,["WireGuard","Outline"]],
  ["mashhad-01","مشهد ۰۱","IR","مشهد","پشتیبان","192.0.2.13",24,31,47,true,["3x-ui"]],
  ["tehran-03","تهران ۰۳","IR","تهران","ورودی ایران","192.0.2.14",17,23,38,false,["WireGuard","تونل نورنبرگ"]],
  ["berlin-01","برلین ۰۱","DE","برلین","خروجی اروپا","198.51.100.23",53,44,63,true,["WireGuard","3x-ui"]],
  ["ankara-01","آنکارا ۰۱","TR","آنکارا","پشتیبان","203.0.113.33",41,29,49,true,["Outline"]],
];
export function createWorkspace(t:number):Workspace {
  const servers:Server[]=HOSTS.map(([id,name,country,city,group,host,ping,cpu,ram,online,names],i)=>{
    const made=t-(30-i*1.7)*86400000;
    return {id,name,country,city,group,host,online,os:"Ubuntu 24.04",createdAt:made,editedAt:made,
      baseline:{ping,cpu,ram},domains:[id+".example.net"],
      ports:[{number:22,protocol:"TCP",state:online?"open":"unknown"},{number:443,protocol:"TCP",state:online?"open":"unknown"},...(names.includes("WireGuard")?[{number:51820,protocol:"UDP" as const,state:online?"open" as const:"unknown" as const}]:[])],
      services:names.map(name=>({name,kind:name.startsWith("تونل")?"tunnel":"service",state:online?"active":"stopped",
        peerId:({"تونل فرانکفورت":"frankfurt-01","تونل استانبول":"istanbul-01","تونل نورنبرگ":"nuremberg-01","تونل نیویورک":"newyork-01"} as Record<string,string>)[name]})),
      lists:[makeChecklist("base","بررسی دسترسی و سرویس",DEFAULT_STEPS)],notes:[],tests:[]};
  });
  const alerts:Workspace["alerts"]=[
    {id:"alert-west",serverId:"losangeles-01",title:"قطع ارتباط با سرور",body:"سرور لس‌آنجلس در سه نمونهٔ متوالی به پینگ پاسخ نداده است.",severity:"critical",state:"open",at:t-9*60000},
    {id:"alert-cpu",serverId:"istanbul-02",title:"افزایش مصرف پردازنده",body:"مصرف پردازنده از آستانهٔ ۸۰ درصد عبور کرده است.",severity:"warning",state:"tracking",at:t-38*60000},
    {id:"alert-tunnel",serverId:"tehran-03",title:"تونل نورنبرگ در دسترس نیست",body:"ارتباط ورودی تهران با مقصد تونل قطع شده است.",severity:"warning",state:"open",at:t-76*60000},
  ];
  const logs = servers.map((s,i)=>({id:"evt-"+s.id,at:t-(i+2)*450000,serverId:s.id,level:"info" as Level,title:"ثبت نمونهٔ وضعیت سرور",body:s.online?"پاسخ سرور و وضعیت سرویس‌ها ثبت شد.":"پاسخی از میزبان دریافت نشد."}));
  return {servers,alerts,events:[...alerts.map(a=>({id:"evt-"+a.id,at:a.at,serverId:a.serverId,level:(a.severity==="critical"?"error":"warning") as Level,title:a.title,body:a.body})),...logs].sort((a,b)=>b.at-a.at),settings:{auto:true,interval:30}};
}
