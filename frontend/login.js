"use strict";
(() => {
 const $=s=>document.querySelector(s);const requested=new URLSearchParams(location.search).get("portal");if(["mentor","learner"].includes(requested))$("#portal").value=requested;
 fetch("/api/auth/bootstrap-status",{credentials:"same-origin"}).then(r=>r.json()).then(s=>{if(!s.configured)$("#setup-help").textContent="Первый наставник ещё не создан. Владелец Mac должен открыть SETUP_MENTOR.command в рабочей папке и задать собственные реквизиты. Открытой регистрации администратора нет.";}).catch(()=>{});
 $("#login-form").addEventListener("submit",async event=>{
  event.preventDefault();const button=event.target.querySelector("button");button.disabled=true;$("#login-error").textContent="";
  try {
   const r=await fetch("/api/auth/login",{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json"},body:JSON.stringify({username:$("#username").value,password:$("#password").value,portal:$("#portal").value})});
   const data=await r.json();if(!r.ok)throw new Error(data.error?.message||"Не удалось войти.");
   $("#password").value="";location.replace(data.user.role==="mentor_admin"?"/mentor":"/learner");
  }catch(e){$("#login-error").textContent=e.message||"Не удалось подключиться.";button.disabled=false;}
 });
})();
