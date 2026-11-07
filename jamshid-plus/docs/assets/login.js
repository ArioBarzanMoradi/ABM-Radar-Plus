const form=document.getElementById("login");
form.addEventListener("submit",async (event)=>{
  event.preventDefault();
  const button=form.querySelector("button"),message=document.getElementById("error");
  button.disabled=true;message.hidden=true;
  try {
    const r=await fetch("/api/login",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(Object.fromEntries(new FormData(form)))});
    if(!r.ok){const body=await r.json();throw new Error(body.error);}
    location.replace("/");
  } catch(error) {
    message.textContent=error instanceof Error&&/[\u0600-\u06ff]/.test(error.message)?error.message:"ورود انجام نشد. ارتباط را بررسی کنید.";
    message.hidden=false;
  } finally {button.disabled=false;}
});
