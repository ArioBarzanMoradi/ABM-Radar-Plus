import { ALERT_STATES, CHECK_TYPES, DEFAULT_STEPS, makeChecklist, type Change, type Workspace, type Level, type Server } from "./model";

export class InputError extends Error {}
function need<T>(value:T|undefined,message:string):T { if(value===undefined) throw new InputError(message); return value; }
export function applyChange(space:Workspace,change:Change):void {
  const {command:c,id,at}=change;
  const log=(serverId:string,title:string,body:string="",level:Level="change")=>{
    space.events.unshift({id:"log-"+id,serverId,at,title,body,level});
  };
  if(c.type==="settings.save") { space.settings={auto:c.auto,interval:c.interval};return; }
  if(c.type==="alert.set") {
    const a=need(space.alerts.find(a=>a.id===c.alertId),"این هشدار پیدا نشد.");
    if(a.state!==c.state) {a.transitions=[...(a.transitions??[{at:a.at,state:a.state}]),{at,state:c.state}];a.state=c.state;log(a.serverId,`وضعیت هشدار به «${ALERT_STATES[c.state]}» تغییر کرد.`,a.title);}
    return;
  }
  const found=space.servers.find(s=>s.id===c.serverId);
  if(c.type==="server.save") {
    if(c.fields.services.some(v=>v.peerId && (v.kind!=="tunnel" || v.peerId===c.serverId || !space.servers.some(s=>s.id===v.peerId)))) throw new InputError("برای مقصد تونل یک سرور دیگر انتخاب کنید.");
    if(space.servers.some(s=>s.host.toLowerCase()===c.fields.host.toLowerCase() && s.id!==c.serverId)) throw new InputError("این نشانی میزبان قبلاً برای یک سرور ثبت شده است.");
    if(found) {
      if(found.editedAt!==c.expected) throw new InputError("مشخصات سرور در جای دیگری تغییر کرده است. فرم را دوباره باز کنید.");
      const labels:Record<keyof typeof c.fields,string>={name:"نام",host:"میزبان",country:"کشور",city:"شهر",group:"گروه",os:"سیستم‌عامل",online:"وضعیت نمونه",domains:"دامنه‌ها",ports:"پورت‌ها",services:"سرویس‌ها"};
      const fields=(Object.keys(labels) as (keyof typeof labels)[]).filter(k=>JSON.stringify(found[k])!==JSON.stringify(c.fields[k])).map(k=>labels[k]);
      const previous=found.online;
      Object.assign(found,c.fields,{editedAt:at});
      log(found.id,"ویرایش پیکربندی سرور",fields.length?fields.join("، "):"مشخصات ذخیره شد.");
      if(previous && !found.online) space.alerts.unshift({id:"offline-"+id,serverId:found.id,at,title:"سرور آفلاین شد",body:"وضعیت سرور در محیط شبیه‌سازی به آفلاین تغییر کرد.",state:"open",severity:"critical"});
    } else {
      if(c.expected!==undefined) throw new InputError("سرور مورد ویرایش پیدا نشد.");
      const server:Server={...c.fields,id:c.serverId,createdAt:at,editedAt:at,baseline:{cpu:30,ram:47,ping:{IR:22,DE:53,TR:39,US:95}[c.fields.country]},notes:[],tests:[],lists:[makeChecklist("base","بررسی دسترسی و سرویس",DEFAULT_STEPS)]};
      space.servers.unshift(server); log(server.id,"سرور به زیرساخت افزوده شد",server.group);
      if(!server.online) space.alerts.unshift({id:"offline-"+id,serverId:server.id,at,title:"میزبان تازه آفلاین است",body:"وضعیت اولیهٔ میزبان در شبیه‌سازی آفلاین است.",state:"open",severity:"warning"});
    }
    return;
  }
  const s=need(found,"این سرور پیدا نشد.");
  switch(c.type) {
    case "checklist.add": s.lists.push(makeChecklist(id,c.title,c.steps)); log(s.id,"افزودن چک‌لیست عیب‌یابی",c.title);break;
    case "step.add": {
      const list=need(s.lists.find(l=>l.id===c.listId),"چک‌لیست پیدا نشد.");
      list.steps.push({id,title:c.title,done:false});log(s.id,"افزودن مرحله به چک‌لیست",c.title);break;
    }
    case "step.set": {
      const step=need(s.lists.find(l=>l.id===c.listId)?.steps.find(v=>v.id===c.stepId),"مرحلهٔ انتخابی پیدا نشد.");
      if(step.done!==c.done) {step.done=c.done;log(s.id,c.done?"مرحلهٔ عیب‌یابی انجام شد":"مرحلهٔ عیب‌یابی بازگشایی شد",step.title);}
      break;
    }
    case "note.add": s.notes.unshift({id,at,body:c.body}); log(s.id,"یادداشت جدید ثبت شد");break;
    case "event.add":
      log(s.id,c.title,c.body,c.level);
      if(c.level==="error" || c.level==="warning") space.alerts.unshift({id:"alert-"+id,serverId:s.id,at,title:c.title,body:c.body,severity:c.level==="error"?"critical":"warning",state:"open"});
      break;
    case "test.run": {
      const r=need(change.result,"نتیجهٔ تست دریافت نشد.");
      s.tests.unshift(r);log(s.id,`تست ${CHECK_TYPES[r.input.kind]} ${r.ok?"موفق بود":"ناموفق بود"}`,r.summary,r.ok?"info":"error");
      if(!r.ok) space.alerts.unshift({id:"alert-"+id,serverId:s.id,at,title:`تست ناموفق ${CHECK_TYPES[r.input.kind]}`,body:r.summary,severity:"warning",state:"open"});
      break;
    }
  }
}
