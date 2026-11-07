import {useState} from "react";
import {Radio,KeyRound} from "lucide-react";
import { type Reading, dayFa,timeFa } from "@/lib/radar/model";
import {privateAPI} from "@/client";
import {SectionHead,Modal,Feedback} from "./ui";

export default function Enrollment({id,reading}:{id:string;reading?:Reading}){
  const [paired,setPaired]=useState(!!reading?.paired),[open,setOpen]=useState(false),[token,setToken]=useState(""),[err,setErr]=useState(""),[busy,setBusy]=useState(false);
  const rotate=paired||!!reading?.paired;
  function close(){if(!busy){setOpen(false);setToken("");setErr("");}}
  async function issue(){
    setBusy(true);setErr("");
    try{const r=await privateAPI("/api/agents/issue",{serverId:id,rotate});const v=await r.json();if(!r.ok)throw Error(v.error||"ساخت کلید ممکن نشد.");setToken(v.token);setPaired(true);}
    catch(e){setErr(e instanceof Error?e.message:"ارتباط برقرار نشد.");}finally{setBusy(false);}
  }
  return <section className="panel"><SectionHead title="اتصال عامل لینوکس" icon={Radio}/><div className="panel-body form-stack">
    <p>{reading?.lastSeen?`آخرین نمونه در ${dayFa(reading.lastSeen)}، ساعت ${timeFa(reading.lastSeen)} به پنل رسید.`:"پس از نصب عامل، اولین نمونهٔ واقعی این سرور اینجا نمایش داده می‌شود."}</p>
    {reading?.pingTarget&&<p className="form-hint">مقصد پینگ عامل <bdi>{reading.pingTarget}</bdi></p>}
    <button className="btn fit" onClick={()=>setOpen(true)}><KeyRound size={16}/>{rotate?"جایگزینی کلید عامل":"دریافت کلید نصب عامل"}</button>
    </div>{open&&<Modal title="اتصال عامل این سرور" close={close}><div className="modal-body form-stack">
    {token?<><p>در همین سرور لینوکسی، از پوشهٔ پروژه فرمان زیر را اجرا کن. نصب‌کننده آدرس پنل و کلید را می‌پرسد.</p><pre dir="ltr">sudo bash install-agent.sh</pre><label className="field"><span>کلید اختصاصی · فقط همین بار نمایش داده می‌شود</span><input dir="ltr" readOnly type="text" value={token} onFocus={e=>e.target.select()}/></label><p className="form-hint">کلید را فقط در نصب‌کنندهٔ عامل وارد کن. برای عامل راه‌دور از آدرس HTTPS پنل یا تونل SSH استفاده کن.</p></>:<><p>{rotate?"با صدور کلید جدید، عامل دارای کلید قبلی باید دوباره پیکربندی شود.":"این کلید فقط اجازهٔ ارسال آمار و دریافت تست‌های همین سرور را به عامل می‌دهد."}</p><button disabled={busy} className="btn primary fit" onClick={issue}>{busy?"در حال صدور…":rotate?"تأیید و جایگزینی کلید":"صدور کلید عامل"}</button></>}
    {err&&<Feedback error text={err}/>}</div></Modal>}</section>;
}
