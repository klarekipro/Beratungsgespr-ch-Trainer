"use strict";
/* Shared, portalled menus for the employee's appearance, account and locale. */
window.TrainerHeaderMenus=(()=>{
 let active=null,serial=0;
 const t=k=>window.TrainerI18n.t(k);
 const glyph=name=>{
  const paths={sun:'<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/>',moon:'<path d="M20 14A9 9 0 0 1 10 4a9 9 0 1 0 10 10Z"/>',system:'<rect x="3" y="4" width="18" height="13" rx="2"/><path d="M8 21h8m-4-4v4"/>',user:'<circle cx="12" cy="8" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/>',language:'<path d="M3 5h12M9 2v3m-4 0c0 6 5 10 9 12M13 5c0 4-4 9-10 12m11 4 4-12 4 12m-7-3h6"/>',lock:'<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',logout:'<path d="M10 4H4v16h6m-1-8h12m-4-4 4 4-4 4"/>',check:'<path d="m5 12 4 4L19 6"/>',chevron:'<path d="m7 10 5 5 5-5"/>'};
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name]||paths.system}</svg>`;
 };
 function close(restore=false){
  if(!active)return;const {popup,trigger}=active;popup.hidden=true;trigger.setAttribute('aria-expanded','false');active=null;
  if(restore&&trigger.isConnected)trigger.focus({preventScroll:true});
 }
 function position(){
  if(!active)return;const {popup,trigger}=active;if(!trigger.isConnected){close();return;}
  const pad=8,gap=6,r=trigger.getBoundingClientRect(),width=window.innerWidth,height=window.innerHeight;
  popup.style.maxWidth=Math.max(0,width-pad*2)+'px';popup.style.maxHeight='none';
  const box=popup.getBoundingClientRect(),below=height-pad-r.bottom-gap,above=r.top-pad-gap;
  const upwards=box.height>below&&above>below,space=Math.max(0,Math.min(height-pad*2,upwards?above:below));
  popup.style.maxHeight=space+'px';
  const h=Math.min(box.height,space),left=Math.max(pad,Math.min(r.right-box.width,width-pad-box.width));
  popup.style.left=left+'px';popup.style.top=Math.max(pad,Math.min(upwards?r.top-gap-h:r.bottom+gap,height-pad-h))+'px';
  popup.dataset.direction=upwards?'up':'down';
 }
 function create({kind,label,name=label,icon,items,choose}){
  const host=document.createElement('div');host.className='employee-menu'+(kind==='language'?' language-bar':'');host.dataset.kind=kind;
  const trigger=document.createElement('button');trigger.type='button';trigger.className='employee-menu-trigger';trigger.id='employee-menu-trigger-'+(++serial);trigger.title=label;trigger.setAttribute('aria-label',name);trigger.setAttribute('aria-haspopup','menu');trigger.setAttribute('aria-expanded','false');
  const symbol=document.createElement('span');symbol.className='employee-menu-icon';symbol.innerHTML=glyph(icon);
  const caption=document.createElement('span');caption.className='employee-menu-label';caption.textContent=label;
  const caret=document.createElement('span');caret.className='employee-menu-caret';caret.innerHTML=glyph('chevron');trigger.append(symbol,caption,caret);host.append(trigger);
  const popup=document.createElement('div');popup.className='employee-menu-popup';popup.id='employee-menu-popup-'+serial;popup.hidden=true;popup.setAttribute('role','menu');popup.setAttribute('aria-labelledby',trigger.id);trigger.setAttribute('aria-controls',popup.id);
  function open(edge){
   if(active?.trigger===trigger){close(true);return;}
   close();popup.replaceChildren();
   for(const item of items()){
    const button=document.createElement('button');button.type='button';button.className='employee-menu-item';button.tabIndex=-1;
    button.setAttribute('role',item.radio?'menuitemradio':'menuitem');if(item.radio)button.setAttribute('aria-checked',String(!!item.selected));
    button.dataset.value=item.value;if(item.action)button.dataset.action=item.action;
    const symbol=document.createElement('span');symbol.className='employee-menu-icon';symbol.innerHTML=glyph(item.icon);
    const text=document.createElement('span');text.className='employee-menu-label';text.textContent=item.label;
    const check=document.createElement('span');check.className='employee-menu-check';if(item.selected)check.innerHTML=glyph('check');button.append(symbol,text,check);
    button.addEventListener('click',()=>{close(true);if(!item.action)choose?.(item.value);});popup.append(button);
   }
   // Portal avoids clipping and transformed containing blocks in the conversation drawer.
   document.getElementById('app').append(popup);popup.hidden=false;trigger.setAttribute('aria-expanded','true');active={popup,trigger};position();
   const buttons=[...popup.querySelectorAll('button')],selected=popup.querySelector('[aria-checked="true"]');
   (edge==='last'?buttons.at(-1):edge==='first'?buttons[0]:selected||buttons[0])?.focus({preventScroll:true});
  }
  trigger.addEventListener('click',()=>open());
  trigger.addEventListener('keydown',event=>{
   if(['Enter',' ','ArrowDown','ArrowUp'].includes(event.key)){event.preventDefault();open(event.key==='ArrowDown'?'first':event.key==='ArrowUp'?'last':undefined);}
  });
  popup.addEventListener('keydown',event=>{
   const buttons=[...popup.querySelectorAll('button')],i=buttons.indexOf(document.activeElement);
   if(['ArrowDown','ArrowUp','Home','End'].includes(event.key)){
    event.preventDefault();const index=event.key==='Home'?0:event.key==='End'?buttons.length-1:(i+(event.key==='ArrowDown'?1:buttons.length-1))%buttons.length;buttons[index]?.focus({preventScroll:true});
   }else if(['Enter',' '].includes(event.key)){event.preventDefault();document.activeElement.click();}
   else if(event.key==='Tab')close(true);
  });
  return host;
 }
 function mount(learning){
  if(window.TRAINER_AUTH?.user.role!=='employee')return;
  close();document.querySelectorAll('.employee-menu-popup').forEach(p=>p.remove());
  const actions=document.querySelector('.topbar-actions');if(!actions)return;
  actions.classList.add('employee-header-controls');
  const appearance=actions.querySelector('.view-settings');
  if(appearance)appearance.replaceWith(create({kind:'theme',label:t('appearance18.title'),icon:'system',items:()=>['light','dark','system'].map(value=>({value,label:t('appearance18.'+value),icon:{light:'sun',dark:'moon',system:'system'}[value],radio:true,selected:learning.theme()===value})),choose:learning.setTheme}));
  const profile=actions.querySelector('.user-menu');
  if(profile)profile.replaceWith(create({kind:'profile',label:window.TRAINER_AUTH.user.display_name,icon:'user',items:()=>[{value:'password',action:'own-password',label:t('header18.password'),icon:'lock'},{value:'logout',action:'logout',label:t('dashboard.text_047'),icon:'logout'}]}));
  const language=actions.querySelector('.language-bar');
  if(language)language.replaceWith(create({kind:'language',name:t('settings.language')+': '+{de:'Deutsch',en:'English',ru:'Русский'}[window.TrainerI18n.locale],label:{de:'Deutsch',en:'English',ru:'Русский'}[window.TrainerI18n.locale],icon:'language',items:()=>Object.entries({de:'Deutsch',en:'English',ru:'Русский'}).map(([value,label])=>({value,label,icon:'language',radio:true,selected:window.TrainerI18n.locale===value})),choose:value=>window.TrainerI18n.selectLocale(value)}));
 }
 const outside=event=>{if(active&&!active.popup.contains(event.target)&&!active.trigger.contains(event.target))close();};
 document.addEventListener('pointerdown',outside,true);document.addEventListener('click',outside,true);
 document.addEventListener('keydown',event=>{if(event.key==='Escape'&&active){event.preventDefault();event.stopImmediatePropagation();close(true);}},true);
 window.addEventListener('resize',position);document.addEventListener('scroll',event=>{if(active&&!active.popup.contains(event.target))position();},true);
 window.addEventListener('hashchange',()=>close());
 return {mount,close};
})();
