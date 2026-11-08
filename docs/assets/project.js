// Discover this Pages repository without hard-coding an account.
(()=>{
  let url="https://github.com/ArioBarzanMoradi/ABM-Radar-Plus";
  if(location.hostname.endsWith(".github.io")){
    const owner=location.hostname.slice(0,-".github.io".length);
    const folder=location.pathname.split("/").filter(Boolean)[0];
    const repo=folder&&!folder.endsWith(".html")?folder:location.hostname;
    url="https://github.com/"+encodeURIComponent(owner)+"/"+encodeURIComponent(repo);
  }
    const link=document.getElementById("repository");link.href=url;link.hidden=false;
    const download=document.getElementById("download-source");download.href=url+"/archive/refs/heads/main.zip";download.hidden=false;
    const guide=document.getElementById("github-guide");guide.href=url;guide.textContent="رفتن به مخزن GitHub ↗";
  let timer;
  document.querySelectorAll("[data-copy]").forEach(button=>button.addEventListener("click",async()=>{
    const feedback=document.getElementById("copy-feedback");
    try{await navigator.clipboard.writeText(button.dataset.copy);feedback.textContent="فرمان کپی شد.";}catch{feedback.textContent="فرمان را از کادر انتخاب و کپی کن.";}
    feedback.hidden=false;clearTimeout(timer);timer=setTimeout(()=>feedback.hidden=true,3000);
  }));
  const image=document.getElementById("dashboard-preview");
  if(image){const update=()=>{const light=document.documentElement.dataset.theme==="light";image.closest("picture").querySelector("source").srcset="./assets/dashboard-"+(light?"light":"dark")+".png";image.src="./assets/dashboard-"+(light?"light":"dark")+".png";};new MutationObserver(update).observe(document.documentElement,{attributes:true,attributeFilter:["data-theme"]});update();}
})();
