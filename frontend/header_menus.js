"use strict";
/* One popup controller for header actions and select controls throughout the app. */
window.TrainerHeaderMenus=(()=>{
 let active=null,serial=0;
 const controls=new Map();
 const t=k=>window.TrainerI18n.t(k);
 const glyph=name=>{
  const paths={sun:'<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/>',moon:'<path d="M20 14A9 9 0 0 1 10 4a9 9 0 1 0 10 10Z"/>',system:'<rect x="3" y="4" width="18" height="13" rx="2"/><path d="M8 21h8m-4-4v4"/>',user:'<circle cx="12" cy="8" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/>',language:'<path d="M3 5h12M9 2v3m-4 0c0 6 5 10 9 12M13 5c0 4-4 9-10 12m11 4 4-12 4 12m-7-3h6"/>',lock:'<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',logout:'<path d="M10 4H4v16h6m-1-8h12m-4-4 4 4-4 4"/>',check:'<path d="m5 12 4 4L19 6"/>',chevron:'<path d="m7 10 5 5 5-5"/>'};
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name]||''}</svg>`;
 };
 function close(restore=false){
  if(!active)return;
  const {popup,trigger}=active;popup.hidden=true;trigger.setAttribute('aria-expanded','false');active=null;
  if(restore&&trigger.isConnected)trigger.focus({preventScroll:true});
 }
 function position(){
  if(!active)return;
  const {popup,trigger}=active;if(!trigger.isConnected||trigger.disabled){close();return;}
  const pad=8,gap=6,r=trigger.getBoundingClientRect(),width=window.innerWidth,height=window.innerHeight;
  const panel=trigger.closest('.kc-panel')?.getBoundingClientRect();
  const leftEdge=Math.max(pad,panel?panel.left+pad:pad),rightEdge=Math.min(width-pad,panel?panel.right-pad:width-pad),room=Math.max(0,rightEdge-leftEdge);
  popup.style.maxWidth=room+'px';popup.style.minWidth=Math.min(room,Math.max(200,popup.dataset.kind==='select'?r.width:0))+'px';popup.style.maxHeight='none';
  const box=popup.getBoundingClientRect(),wanted=Math.min(box.height,360),below=height-pad-r.bottom-gap,above=r.top-pad-gap;
  const upwards=wanted>below&&above>below,space=Math.max(0,Math.min(height-pad*2,upwards?above:below,360));
  popup.style.maxHeight=space+'px';
  const h=Math.min(box.height,space),left=Math.max(leftEdge,Math.min(r.right-box.width,rightEdge-box.width));
  popup.style.left=left+'px';popup.style.top=Math.max(pad,Math.min(upwards?r.top-gap-h:r.bottom+gap,height-pad-h))+'px';popup.dataset.direction=upwards?'up':'down';
 }
 function create({kind,label,name=label,icon,items,choose}){
  const host=document.createElement('div');host.className='employee-menu'+(kind==='language'?' language-bar':'');host.dataset.kind=kind;
  const trigger=document.createElement('button');trigger.type='button';trigger.className='employee-menu-trigger';trigger.id='employee-menu-trigger-'+(++serial);trigger.title=label;trigger.setAttribute('aria-label',name);trigger.setAttribute('aria-haspopup',kind==='select'?'listbox':'menu');trigger.setAttribute('aria-expanded','false');
  if(icon){const symbol=document.createElement('span');symbol.className='employee-menu-icon';symbol.innerHTML=glyph(icon);trigger.append(symbol);}
  const caption=document.createElement('span');caption.className='employee-menu-label';caption.textContent=label;
  const caret=document.createElement('span');caret.className='employee-menu-caret';caret.innerHTML=glyph('chevron');trigger.append(caption,caret);host.append(trigger);
  const popup=document.createElement('div');popup.className='employee-menu-popup';popup.dataset.kind=kind;popup.id='employee-menu-popup-'+serial;popup.hidden=true;popup.setAttribute('role',kind==='select'?'listbox':'menu');popup.setAttribute('aria-labelledby',trigger.id);trigger.setAttribute('aria-controls',popup.id);
  const buttons=()=>[...popup.querySelectorAll('button:not(:disabled):not([hidden])')];
  function focus(button){
   button?.focus({preventScroll:true});if(!button)return;
   if(button.offsetTop<popup.scrollTop)popup.scrollTop=button.offsetTop;
   else if(button.offsetTop+button.offsetHeight>popup.scrollTop+popup.clientHeight)popup.scrollTop=button.offsetTop+button.offsetHeight-popup.clientHeight;
  }
  function open(edge){
   if(trigger.disabled)return;
   if(active?.trigger===trigger){close(true);return;}
   close();popup.replaceChildren();
   popup.setAttribute('role',kind==='select'?'listbox':'menu');trigger.setAttribute('aria-haspopup',kind==='select'?'listbox':'menu');
   const entries=items();
   // Keep the accepted employee menus unchanged. Large mentor lists retain
   // every option and gain an explicit filter in the same shared popup.
   let filter=null,optionHost=popup;
   if(kind==='select'&&window.TRAINER_AUTH?.user.role==='mentor_admin'&&entries.length>=10){
    filter=document.createElement('input');filter.type='search';filter.className='employee-menu-search';
    filter.setAttribute('aria-label',t('mentor19.search_options'));filter.placeholder=t('mentor19.search_options');
    const empty=document.createElement('p');empty.className='employee-menu-empty';empty.textContent=t('mentor19.no_options');empty.hidden=true;
    filter.addEventListener('input',()=>{
     const query=filter.value.trim().toLocaleLowerCase();
     popup.querySelectorAll('[role=option]').forEach(option=>option.hidden=!option.textContent.toLocaleLowerCase().includes(query));
     empty.hidden=!!popup.querySelector('[role=option]:not([hidden])');popup.scrollTop=0;
    });
    optionHost=document.createElement('div');optionHost.id=popup.id+'-options';optionHost.setAttribute('role','listbox');optionHost.setAttribute('aria-labelledby',trigger.id);
    filter.setAttribute('aria-controls',optionHost.id);popup.setAttribute('role','dialog');trigger.setAttribute('aria-haspopup','dialog');
    popup.append(filter,empty,optionHost);
   }
   for(const item of entries){
    const button=document.createElement('button');button.type='button';button.className='employee-menu-item';button.tabIndex=-1;button.disabled=!!item.disabled;
    button.setAttribute('role',kind==='select'?'option':item.radio?'menuitemradio':'menuitem');
    if(kind==='select'||item.radio)button.setAttribute(kind==='select'?'aria-selected':'aria-checked',String(!!item.selected));
    button.dataset.value=item.value;if(item.action)button.dataset.action=item.action;
    if(item.icon){const symbol=document.createElement('span');symbol.className='employee-menu-icon';symbol.innerHTML=glyph(item.icon);button.append(symbol);}
    const text=document.createElement('span');text.className='employee-menu-label';text.textContent=item.label;
    const check=document.createElement('span');check.className='employee-menu-check';if(item.selected)check.innerHTML=glyph('check');button.append(text,check);
    button.addEventListener('click',()=>{close(true);if(!item.action)choose?.(item.value);});optionHost.append(button);
   }
   // A portal escapes scrolling panel clipping; modal readers keep their own top layer.
   (trigger.closest('dialog')||document.getElementById('app')||document.body).append(popup);popup.hidden=false;trigger.setAttribute('aria-expanded','true');active={popup,trigger};position();
   const list=buttons(),selected=popup.querySelector('[aria-checked="true"]:not(:disabled),[aria-selected="true"]:not(:disabled)');
   if(filter&&!edge)filter.focus({preventScroll:true});
   else focus(edge==='last'?list.at(-1):edge==='first'?list[0]:selected||list[0]);
  }
  trigger.addEventListener('click',()=>open());
  trigger.addEventListener('keydown',event=>{
   if(['Enter',' ','ArrowDown','ArrowUp'].includes(event.key)){event.preventDefault();open(event.key==='ArrowDown'?'first':event.key==='ArrowUp'?'last':undefined);}
  });
  let search='',searchedAt=0;
  popup.addEventListener('keydown',event=>{
   const list=buttons(),i=list.indexOf(document.activeElement);
   if(event.target.matches('input')){
    if(['ArrowDown','ArrowUp'].includes(event.key)){event.preventDefault();focus(event.key==='ArrowDown'?list[0]:list.at(-1));}
    else if(event.key==='Enter'){event.preventDefault();list[0]?.click();}
    else if(event.key==='Tab')close(true);
    return;
   }
   if(['ArrowDown','ArrowUp','Home','End'].includes(event.key)){
    event.preventDefault();focus(list[event.key==='Home'?0:event.key==='End'?list.length-1:(i+(event.key==='ArrowDown'?1:list.length-1))%list.length]);
   }else if(['Enter',' '].includes(event.key)){event.preventDefault();document.activeElement.click();}
   else if(event.key==='Tab')close(true);
   else if(event.key.length===1&&!event.ctrlKey&&!event.metaKey&&!event.altKey){
    event.preventDefault();const now=Date.now();search=(now-searchedAt<700?search:'')+event.key.toLocaleLowerCase();searchedAt=now;
    focus(list.find(button=>button.textContent.trim().toLocaleLowerCase().startsWith(search)));
   }
  });
  return host;
 }
 function syncSelect(select){
  const entry=controls.get(select);if(!entry)return;
  const {host,trigger,caption,labels}=entry,option=select.selectedOptions[0],text=option?.label||'';
  if(caption.textContent!==text)caption.textContent=text;
  const label=select.getAttribute('aria-label')||labels.map(el=>{const copy=el.cloneNode(true);copy.querySelectorAll('select,.employee-menu').forEach(n=>n.remove());return copy.textContent.trim();}).filter(Boolean).join(' ')||select.title||text;
  const name=label===text?text:label+': '+text;
  if(trigger.getAttribute('aria-label')!==name)trigger.setAttribute('aria-label',name);
  if(trigger.title!==text)trigger.title=text;
  const disabled=select.matches(':disabled');if(trigger.disabled!==disabled)trigger.disabled=disabled;
  for(const attr of ['aria-describedby','aria-invalid']){
   const value=select.getAttribute(attr);if(value!==trigger.getAttribute(attr)){if(value===null)trigger.removeAttribute(attr);else trigger.setAttribute(attr,value);}
  }
  if(active?.trigger===trigger&&disabled)close();
  host.classList.toggle('is-invalid',select.getAttribute('aria-invalid')==='true');
 }
 function enhanceSelects(){
  for(const [select,{host}] of controls)if(!select.isConnected){host.remove();controls.delete(select);}
  document.querySelectorAll('select:not([multiple])').forEach(select=>{
   if(!controls.has(select)){
    if(select.hidden)return;
    const labels=[...select.labels];
    const host=create({kind:'select',label:'',items:()=>[...select.options].map((option,index)=>({value:String(index),label:option.label,selected:option.selected,disabled:option.disabled||option.parentElement.disabled})),choose:index=>{
     if(select.selectedIndex===Number(index))return;
     select.selectedIndex=Number(index);syncSelect(select);
     select.dispatchEvent(new Event('input',{bubbles:true}));select.dispatchEvent(new Event('change',{bubbles:true}));
     if(!trigger.isConnected&&document.activeElement===document.body){enhanceSelects();controls.get(document.getElementById(select.id))?.trigger.focus({preventScroll:true});}
    }});
    host.classList.add('app-select');host.dataset.selectId=select.id;
    const trigger=host.querySelector('button'),caption=host.querySelector('.employee-menu-label');
    controls.set(select,{host,trigger,caption,labels});select.after(host);select.hidden=true;select.tabIndex=-1;select.setAttribute('aria-hidden','true');
    // Existing validation/focus paths and form payloads still use the original select.
    select.focus=options=>trigger.focus(options);
    select.addEventListener('invalid',event=>{event.preventDefault();select.setAttribute('aria-invalid','true');syncSelect(select);window.TrainerUI?.openAncestors(trigger);trigger.focus();});
    for(const label of labels)label.addEventListener('click',event=>{if(!event.target.closest('button,input,textarea,a,select'))trigger.focus();});
   }
   syncSelect(select);
  });
  document.querySelectorAll('.editor-more:not([data-shared-menu])').forEach(original=>{
   const actions=[...original.querySelectorAll('.editor-more-actions>button,.editor-more-actions>label')];
   const host=create({kind:'actions',label:original.querySelector('summary').textContent,items:()=>actions.map((button,index)=>({value:String(index),label:button.textContent.trim(),disabled:button.matches(':disabled')})),choose:index=>{
    const action=actions[Number(index)];(action.querySelector('input[type="file"]')||action).click();
   }});
   original.dataset.sharedMenu='';original.hidden=true;original.after(host);
  });
  if(active&&!active.trigger.isConnected)close();
  document.querySelectorAll('.employee-menu-popup').forEach(p=>{if(!document.getElementById(p.getAttribute('aria-labelledby')))p.remove();});
 }
 function mount(learning){
  close();document.querySelectorAll('.employee-menu-popup').forEach(p=>p.remove());
  const actions=document.querySelector('.topbar-actions');if(!actions)return;
  actions.classList.add('employee-header-controls');
  const appearance=actions.querySelector('.view-settings');
  if(appearance)appearance.replaceWith(create({kind:'theme',label:t('appearance18.title'),icon:'system',items:()=>['light','dark','system'].map(value=>({value,label:t('appearance18.'+value),icon:{light:'sun',dark:'moon',system:'system'}[value],radio:true,selected:learning.theme()===value})),choose:learning.setTheme}));
  const profile=actions.querySelector('.user-menu');
  if(profile)profile.replaceWith(create({kind:'profile',label:window.TRAINER_AUTH.user.display_name,icon:'user',items:()=>[{value:'password',action:'own-password',label:t('header18.password'),icon:'lock'},{value:'logout',action:'logout',label:t('dashboard.text_047'),icon:'logout'}]}));
  const language=actions.querySelector('.language-bar');
  if(language)language.replaceWith(create({kind:'language',name:t('settings.language')+': '+{de:'Deutsch',en:'English',ru:'Русский'}[window.TrainerI18n.locale],label:{de:'Deutsch',en:'English',ru:'Русский'}[window.TrainerI18n.locale],icon:'language',items:()=>Object.entries({de:'Deutsch',en:'English',ru:'Русский'}).map(([value,label])=>({value,label,icon:'language',radio:true,selected:window.TrainerI18n.locale===value})),choose:value=>window.TrainerI18n.selectLocale(value)}));
  enhanceSelects();
 }
 const outside=event=>{if(active&&!active.popup.contains(event.target)&&!active.trigger.contains(event.target))close();};
 document.addEventListener('pointerdown',event=>{document.documentElement.dataset.inputModality='pointer';outside(event);},true);document.addEventListener('click',outside,true);
 document.addEventListener('keydown',event=>{if(!event.ctrlKey&&!event.metaKey&&!event.altKey)document.documentElement.dataset.inputModality='keyboard';if(event.key==='Escape'&&active){event.preventDefault();event.stopImmediatePropagation();close(true);}},true);
 document.addEventListener('change',event=>{if(event.target.tagName==='SELECT')syncSelect(event.target);});
 document.addEventListener('reset',()=>queueMicrotask(enhanceSelects),true);
 window.addEventListener('resize',position);document.addEventListener('scroll',event=>{if(active&&!active.popup.contains(event.target))position();},true);
 window.addEventListener('hashchange',()=>close());
 const observer=new MutationObserver(records=>{
  const relevant=records.some(r=>r.target.matches?.('select,option,optgroup')||r.type==='attributes'&&r.target.querySelector?.('select')||[...r.addedNodes,...r.removedNodes].some(n=>n.nodeType===1&&(n.matches('select,.editor-more')||n.querySelector('select,.editor-more'))));
  if(relevant)enhanceSelects();else if(active&&!active.trigger.isConnected)close();
 });
 observer.observe(document.documentElement,{subtree:true,childList:true,attributes:true,attributeFilter:['disabled','hidden','selected','label','value','aria-invalid','aria-describedby']});
 enhanceSelects();
 return {mount,close,enhanceSelects,syncSelect};
})();
