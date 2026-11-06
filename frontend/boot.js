"use strict";
(async()=>{
 const app=document.getElementById("app");
 try {
  const r=await fetch("/api/auth/me",{credentials:"same-origin"});if(r.status===401){location.replace("/login?portal="+(location.pathname==="/mentor"?"mentor":"learner"));return;}
  if(!r.ok)throw new Error("Не удалось проверить вход.");
  const auth=await r.json();window.TRAINER_AUTH=auth;
  if(auth.user.must_change_password){
   app.innerHTML='<main class="card login-card"><h1>Измените временный пароль</h1><p>Тренировки станут доступны после смены пароля.</p><form id="initial-password"><label for="old-password">Временный пароль</label><input id="old-password" type="password" autocomplete="current-password" required><label for="new-password">Новый пароль, 12–128 символов</label><input id="new-password" type="password" autocomplete="new-password" minlength="12" maxlength="128" required><label for="confirm-password">Повторите новый пароль</label><input id="confirm-password" type="password" autocomplete="new-password" required><p id="password-error" class="form-error" role="alert"></p><button class="btn primary" type="submit">Сохранить новый пароль</button></form><button class="btn gap-top" id="initial-logout">Выйти</button></main>';
   document.getElementById("initial-logout").onclick=async()=>{await fetch("/api/auth/logout",{method:"POST",credentials:"same-origin",headers:{"X-CSRF-Token":auth.csrf}});location.replace("/login");};
   document.getElementById("initial-password").onsubmit=async event=>{
    event.preventDefault();const old=document.getElementById("old-password").value,pw=document.getElementById("new-password").value;
    const error=document.getElementById("password-error");if(pw!==document.getElementById("confirm-password").value){error.textContent="Пароли не совпали.";return;}
    try {const r=await fetch("/api/auth/password",{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json","X-CSRF-Token":auth.csrf},body:JSON.stringify({current_password:old,new_password:pw})});const data=await r.json();if(!r.ok)throw new Error(data.error?.message||"Пароль не изменён.");location.reload();}catch(e){error.textContent=e.message;}
   };return;
  }
  const expected=auth.user.role==="mentor_admin"?"/mentor":"/learner";if(location.pathname!==expected){location.replace(expected);return;}
  for(const src of ["/static/voice.js","/static/mentor_studio.js","/static/app.js"]){await new Promise((resolve,reject)=>{const script=document.createElement("script");script.src=src;script.onload=resolve;script.onerror=reject;document.head.appendChild(script);});}
 }catch(_){app.textContent="Не удалось открыть кабинет. Обновите страницу или вернитесь на /login.";}
 window.addEventListener("pageshow",event=>{if(event.persisted)location.reload();});
})();
