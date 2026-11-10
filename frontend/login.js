"use strict";
(async()=>{
 const I=window.TrainerI18n;await I.ready;
 const $=s=>document.querySelector(s);let configured=true,lastError=null;
 const requested=new URLSearchParams(location.search).get('portal');if(['mentor','learner'].includes(requested))$('#portal').value=requested;window.TrainerHeaderMenus.enhanceSelects();
 const render=()=>{I.apply();document.title=I.t('auth.login.title')+' · Klare KI';$('#password-toggle').textContent=I.t($('#password').type==='password'?'auth.login.show':'auth.login.hide');$('#setup-help').textContent=I.t(configured?'auth.login.recovery':'auth.login.setup');if(lastError)$('#login-error').textContent=I.error(lastError);};
 $('#password-toggle').onclick=()=>{const p=$('#password'),show=p.type==='password';p.type=show?'text':'password';$('#password-toggle').setAttribute('aria-pressed',String(show));render();p.focus();};
 document.addEventListener('trainer-language',render);
 try{configured=(await (await fetch('/api/auth/bootstrap-status',{credentials:'same-origin'})).json()).configured;}catch(_){}render();
 $('#login-form').addEventListener('submit',async event=>{
  event.preventDefault();const button=$('#login-submit');button.disabled=true;lastError=null;$('#login-error').textContent='';
  try{
   const body={username:$('#username').value,password:$('#password').value,portal:$('#portal').value};if(I.explicit)body.locale=I.locale;
   const r=await fetch('/api/auth/login',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-UI-Locale':I.locale},body:JSON.stringify(body)});const data=await r.json();
   if(!r.ok){lastError=data.error||{code:'REQUEST_FAILED'};throw new Error();}
   I.use(data.user.locale);$('#password').value='';location.replace(data.user.role==='mentor_admin'?'/mentor':'/learner');
  }catch(_){lastError=lastError||{code:'NETWORK_ERROR'};render();button.disabled=false;}
 });
})().catch(()=>{document.getElementById('login-error').textContent='Sprachdateien nicht verfügbar / Language files unavailable. Bitte neu laden / Reload.';});
