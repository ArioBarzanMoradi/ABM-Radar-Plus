/* Shared appearance for the private panel and the public project page. */
(()=>{
  const root=document.documentElement,key="abm-radar-plus-appearance",allowed=["system","dark","light"],media=matchMedia("(prefers-color-scheme: dark)");
  let preference="system";
  try{const saved=localStorage.getItem(key);if(allowed.includes(saved))preference=saved;}catch{}
  const labels={system:"سیستم",dark:"تیره",light:"روشن"};
  function apply(){root.dataset.theme=preference==="system"?(media.matches?"dark":"light"):preference;root.dataset.appearance=preference;document.querySelectorAll("[data-theme-label]").forEach(el=>el.textContent=labels[preference]);document.querySelectorAll("[data-theme-cycle]").forEach(el=>el.setAttribute("aria-label","پوسته: "+labels[preference]+"؛ تغییر پوسته"));}
  apply();media.addEventListener("change",apply);document.addEventListener("DOMContentLoaded",apply);
  document.addEventListener("click",e=>{if(!(e.target instanceof Element)||!e.target.closest("[data-theme-cycle]"))return;preference=allowed[(allowed.indexOf(preference)+1)%allowed.length];try{localStorage.setItem(key,preference);}catch{}apply();});
  window.addEventListener("storage",e=>{if(e.key!==key)return;preference=allowed.includes(e.newValue)?e.newValue:"system";apply();});
})();
