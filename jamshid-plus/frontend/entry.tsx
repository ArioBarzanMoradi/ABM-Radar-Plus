import React from "react";
import { createRoot } from "react-dom/client";
import RadarApp from "./components/radar/app";
import { start } from "./client";
const root=createRoot(document.getElementById("root")!);
start().then(initial=>root.render(<RadarApp initial={initial}/>)).catch(()=>root.render(<main className="auth-screen"><section className="panel auth-card"><h1>دریافت فضای پایش ممکن نشد</h1><button className="btn primary" onClick={()=>location.reload()}>تلاش دوباره</button></section></main>));
