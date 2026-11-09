"use strict";
(async()=>{
 const assetVersion=new URL(document.currentScript.src).search;
 const app=document.getElementById("app");
 try {
  await window.TrainerI18n.ready;
  const r=await fetch("/api/auth/me",{credentials:"same-origin"});if(r.status===401){location.replace("/login?portal="+(location.pathname==="/mentor"?"mentor":"learner"));return;}
  if(!r.ok)throw new Error(window.TrainerI18n.t("auth.text_616"));
  const auth=await r.json();window.TRAINER_AUTH=auth;window.TrainerI18n.use(auth.user.locale);document.title=window.TrainerI18n.t("app.title")+" · Klare KI";
  if(auth.user.must_change_password){
   app.innerHTML=("<main class=\"card login-card\"><h1>"+window.TrainerI18n.t("auth.text_617")+"</h1><p>"+window.TrainerI18n.t("auth.text_618")+"</p><form id=\"initial-password\"><label for=\"old-password\">"+window.TrainerI18n.t("mentor.text_522")+"</label><input id=\"old-password\" type=\"password\" autocomplete=\"current-password\" required><label for=\"new-password\">"+window.TrainerI18n.t("dashboard.text_054")+"</label><input id=\"new-password\" type=\"password\" autocomplete=\"new-password\" minlength=\"12\" maxlength=\"128\" required><label for=\"confirm-password\">"+window.TrainerI18n.t("auth.text_619")+"</label><input id=\"confirm-password\" type=\"password\" autocomplete=\"new-password\" required><p id=\"password-error\" class=\"form-error\" role=\"alert\"></p><button class=\"btn primary\" type=\"submit\">"+window.TrainerI18n.t("auth.text_620")+"</button></form><button class=\"btn gap-top\" id=\"initial-logout\">"+window.TrainerI18n.t("dashboard.text_047")+"</button></main>");
   document.getElementById("initial-logout").onclick=async()=>{await fetch("/api/auth/logout",{method:"POST",credentials:"same-origin",headers:{"X-CSRF-Token":auth.csrf}});location.replace("/login");};
   document.getElementById("initial-password").onsubmit=async event=>{
    event.preventDefault();const old=document.getElementById("old-password").value,pw=document.getElementById("new-password").value;
    const error=document.getElementById("password-error");if(pw!==document.getElementById("confirm-password").value){error.textContent=window.TrainerI18n.t("auth.text_621");return;}
    try {const r=await fetch("/api/auth/password",{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json","X-CSRF-Token":auth.csrf},body:JSON.stringify({current_password:old,new_password:pw})});const data=await r.json();if(!r.ok)throw new Error(window.TrainerI18n.error(data.error)||window.TrainerI18n.t("auth.text_622"));location.reload();}catch(e){error.textContent=e.message;}
   };return;
  }
  const expected=auth.user.role==="mentor_admin"?"/mentor":"/learner";if(location.pathname!==expected){location.replace(expected);return;}
  for(const src of ["/static/voice.js","/static/mentor_studio.js","/static/app.js"]){await new Promise((resolve,reject)=>{const script=document.createElement("script");script.src=src+assetVersion;script.onload=resolve;script.onerror=reject;document.head.appendChild(script);});}
 }catch(_){app.textContent=window.TrainerI18n.t("auth.text_623");}
 window.addEventListener("pageshow",event=>{if(event.persisted)location.reload();});
})();
