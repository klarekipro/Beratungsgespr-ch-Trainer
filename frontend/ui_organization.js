"use strict";
/* UI only: native disclosures retain every form control in the DOM. */
window.TrainerUI=(()=>{
 const t=k=>window.TrainerI18n.t('ui16.'+k);
 const openState=new Map();let topObserver;
 function openAncestors(el){for(let p=el?.parentElement;p;p=p.parentElement)if(p.tagName==='DETAILS')p.open=true;}
 function revealError(el){if(!el)return;openAncestors(el);el.setAttribute('aria-invalid','true');let error=el.parentElement.querySelector('.ui-field-error');if(!error){error=document.createElement('span');error.className='ui-field-error';error.setAttribute('role','alert');el.after(error);}error.textContent=el.validity?.valueMissing?t('required'):el.validationMessage||t('field_error');requestAnimationFrame(()=>{el.focus({preventScroll:true});el.scrollIntoView({block:'center',behavior:'smooth'});});}
 function disclosure(title,key,children,opened=false){const d=document.createElement('details');d.className='ui-section';d.dataset.uiSection=key;d.open=openState.get(key)??opened;const s=document.createElement('summary');s.textContent=title;d.append(s,...children.filter(Boolean));return d;}
 function compactForms(){
  for(const form of document.querySelectorAll('#scenario-form,#company-form')){
   form.noValidate=true;
   form.querySelectorAll('section.form-section').forEach((section,i)=>{
    const heading=section.querySelector('h2');const key=location.hash+':section:'+i;
    const d=disclosure(heading?.textContent||t('additional'),key,[...section.children].filter(x=>!x.classList.contains('form-section-title')),i===0);d.classList.add('card','card-pad','form-section');section.replaceWith(d);
   });
   form.querySelectorAll('.fact-row,.service-row').forEach((row,i)=>{
    const label=row.querySelector('[data-field="label"],[data-field="title"]');const name=label?.value||row.querySelector('legend')?.textContent||t('fact');
    const d=disclosure(name,location.hash+':item:'+i,[...row.children]);d.classList.add(row.classList.contains('fact-row')?'fact-row':'service-row');
    for(const a of row.attributes)if(a.name.startsWith('data-'))d.setAttribute(a.name,a.value);row.replaceWith(d);
   });
  }
 }
 function afterRender(){
  const bar=document.querySelector('.topbar');const actions=bar?.querySelector('.topbar-actions');const language=document.querySelector('.language-bar');
  if(actions&&language)actions.append(language);
  const user=actions?.querySelector('.portal-user');if(user&&!user.closest('details')){const d=document.createElement('details');d.className='user-menu';const s=document.createElement('summary');s.textContent=window.TRAINER_AUTH.user.display_name;user.before(d);d.append(s,user);}
  document.querySelectorAll('.user-menu').forEach(menu=>{
   const panel=menu.querySelector('.portal-user');if(!panel)return;
   if(!panel.querySelector('[data-close-popover]')){
    const close=document.createElement('button');close.type='button';close.className='btn popup-close';close.dataset.closePopover='';
    close.textContent='×';close.setAttribute('aria-label',window.TrainerI18n.t('menus18.close_profile'));close.title=window.TrainerI18n.t('menus18.close_profile');panel.prepend(close);
   }
  });
  actions?.querySelector('.local-label')?.remove();
  if(bar){topObserver?.disconnect();topObserver=new ResizeObserver(()=>document.documentElement.style.setProperty('--app-topbar-height',bar.offsetHeight+'px'));topObserver.observe(bar);}
  compactForms();
  const search=document.getElementById('history-search');if(search)search.closest('label').hidden=location.hash.endsWith('/certificates');
  if(window.TRAINER_AUTH.user.role==='employee'&&document.getElementById('learning-published-review'))document.querySelector('.report-aside>.review-card')?.remove();
 }
 function expand(target,title){
  const source=document.querySelector(target);if(!source)return;
  const oldFocus=document.activeElement,scroll=window.scrollY,placeholder=document.createComment('expanded content');
  const dialog=document.createElement('dialog');dialog.className='ui-reader';dialog.setAttribute('aria-label',title);
  const head=document.createElement('header');const h=document.createElement('h2');h.textContent=title;const close=document.createElement('button');close.className='btn';close.textContent=t('close');head.append(h,close);dialog.append(head);
  const wasDetails=source.tagName==='DETAILS';const wasOpen=source.open;source.before(placeholder);dialog.append(source);if(wasDetails)source.open=true;
  (document.getElementById('app')||document.body).append(dialog);dialog.showModal();close.focus();
  let closed=false;function done(){if(closed)return;closed=true;placeholder.replaceWith(source);if(wasDetails)source.open=wasOpen;dialog.remove();window.scrollTo({top:scroll,behavior:'instant'});oldFocus?.focus({preventScroll:true});}
  close.onclick=()=>{dialog.close();done();};dialog.addEventListener('close',done,{once:true});
 }
 const menus=()=>[...document.querySelectorAll('.view-settings,.user-menu')];
 function closePopover(target,restoreFocus=false){
  const menu=target?.matches?.('.view-settings,.user-menu')?target:target?.closest?.('.view-settings,.user-menu');
  if(!menu?.open)return;menu.open=false;if(restoreFocus)menu.querySelector('summary')?.focus({preventScroll:true});
 }
 function closeOthers(except){menus().forEach(menu=>{if(menu!==except)closePopover(menu);});}
 document.addEventListener('pointerdown',e=>{menus().forEach(menu=>{if(!menu.contains(e.target))closePopover(menu);});},true);
 document.addEventListener('click',e=>{
  const close=e.target.closest('[data-close-appearance],[data-close-popover]');
  if(close){e.preventDefault();closePopover(close,true);return;}
  const trigger=e.target.closest('.view-settings>summary,.user-menu>summary');
  if(trigger){e.preventDefault();const menu=trigger.parentElement;const opening=!menu.open;closeOthers(menu);menu.open=opening;return;}
  // Keyboard/assistive clicks may have no pointerdown. Never move outside focus.
  menus().forEach(menu=>{if(!menu.contains(e.target))closePopover(menu);});
 });
 document.addEventListener('keydown',e=>{
  if(e.key!=='Escape')return;
  const menu=menus().find(x=>x.open);if(!menu)return;
  e.preventDefault();e.stopImmediatePropagation();closePopover(menu,true);
 },true);
 document.addEventListener('toggle',e=>{if(e.target.matches?.('.view-settings,.user-menu')&&e.target.open)closeOthers(e.target);},true);
 window.addEventListener('hashchange',()=>closeOthers(null));
 document.addEventListener('toggle',e=>{const d=e.target;if(d.dataset?.uiSection)openState.set(d.dataset.uiSection,d.open);},true);
 document.addEventListener('invalid',e=>{if(e.target.closest('#studio-form,#scenario-form,#company-form'))revealError(e.target);},true);
 document.addEventListener('input',e=>{e.target.removeAttribute('aria-invalid');e.target.setCustomValidity?.('');e.target.parentElement?.querySelector('.ui-field-error')?.remove();});
 document.addEventListener('click',e=>{const button=e.target.closest('[data-expand-target]');if(button)expand(button.dataset.expandTarget,button.dataset.expandTitle||t('expand'));});
 return {afterRender,disclosure,openAncestors,revealError,t,expand,closePopover};
})();
