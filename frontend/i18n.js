"use strict";
window.TrainerI18n=(()=>{
 const supported=['de','en','ru'],dict={},storage='trainer.ui.locale';let locale='de',explicit=false;
 try{const saved=localStorage.getItem(storage);if(supported.includes(saved))locale=saved;}catch(_){}
 function t(key,vars={}){const text=dict[locale]?.[key]??dict.de?.[key]??dict.ru?.[key];if(text===undefined){console.warn('Missing UI translation:',key);return locale==='de'?'Text nicht verfügbar':locale==='ru'?'Текст недоступен':'Text unavailable';}return text.replace(/\{([a-zA-Z_][\w]*)\}/g,(m,k)=>Object.hasOwn(vars,k)?String(vars[k]):'—');}
 function apply(){document.documentElement.lang=locale;document.querySelectorAll('[data-i18n]').forEach(n=>{n.textContent=t(n.dataset.i18n);});document.querySelectorAll('[data-i18n-placeholder]').forEach(n=>n.placeholder=t(n.dataset.i18nPlaceholder));const select=document.getElementById('ui-locale');if(select)select.value=locale;document.querySelectorAll('[data-i18n-title]').forEach(n=>n.title=t(n.dataset.i18nTitle));}
 function remember(value){locale=supported.includes(value)?value:'de';try{localStorage.setItem(storage,locale);}catch(_){}apply();}
 function mount(){if(document.getElementById('ui-locale'))return;const bar=document.createElement('div');bar.className='language-bar';bar.innerHTML='<label><span data-i18n="settings.language">Sprache</span> <select id="ui-locale" aria-label="Deutsch / English / Русский"><option value="de">Deutsch</option><option value="en">English</option><option value="ru">Русский</option></select></label>';document.body.prepend(bar);apply();document.getElementById('ui-locale').onchange=e=>selectLocale(e.target.value);}
 async function selectLocale(value){
   if(!supported.includes(value)||value===locale)return;
   const auth=window.TRAINER_AUTH;
   if(auth&&window.TrainerVoice?.busy()&&!confirm(t('dictation18.leave')))return;
   if(auth){
     if((window.TrainerHasUnsavedChanges?.()??[...document.querySelectorAll('textarea,input:not([type=hidden]):not([type=checkbox]):not([type=radio]):not([type=search])')].some(el=>el.value.length>0))&&!confirm(t('settings.unsaved'))){apply();return;}
     try{const r=await fetch('/api/auth/preferences',{method:'PUT',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':auth.csrf},body:JSON.stringify({locale:value})});if(!r.ok)throw new Error();remember(value);window.TrainerLocaleReload=true;location.reload();}
     catch(_){alert(t('settings.save_failed'));apply();}
   }else {explicit=true;remember(value);document.dispatchEvent(new Event('trainer-language'));}
 }
 const ready=Promise.all(supported.map(async lang=>{const r=await fetch('/static/locales/'+lang+'.json',{credentials:'same-origin',cache:'no-cache'});if(!r.ok)throw new Error('Language catalogue unavailable');dict[lang]=await r.json();})).then(()=>{mount();apply();});
 function error(data){const key='errors.'+(data?.code||'REQUEST_FAILED');return Object.hasOwn(dict.de||{},key)?t(key):t('errors.REQUEST_FAILED');}
 function systemText(value){
   let count=/^simple_actor: (\d+) ответов одного OpenAI Actor;/.exec(value);
   if(count){const n=Number(count[1]),form=new Intl.PluralRules(locale).select(n);return t('report.actor.'+(form==='one'?'one':form==='few'?'few':'other'),{count:number(n)});}
   if(locale==='ru')return value;
   const key=Object.keys(dict.ru||{}).find(k=>dict.ru[k]===value);if(key)return t(key);
   for(const base of ['report.complete','report.incomplete']){if(value.startsWith(dict.ru[base]))return t(base)+(value.length>dict.ru[base].length?t('report.early'):'');}
   let m=/^Фактических API-запросов: (\d+);/.exec(value);if(m)return t('report.api',{count:number(m[1])});
   return t('report.original_note');
 }
 function number(n){return new Intl.NumberFormat(locale).format(n);}
 function plural(n,forms){const cat=new Intl.PluralRules(locale).select(n);return forms[cat==='one'?0:cat==='few'?1:2]||forms[0];}
 return {ready,t,error,plural,apply,systemText,selectLocale,use:remember,get locale(){return locale;},get explicit(){return explicit;},number};
})();
