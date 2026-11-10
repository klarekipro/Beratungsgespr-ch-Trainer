"use strict";
/* Active learner conversation only. Server actions remain in app.js / voice.js. */
window.createConversationScreen=({state,esc:E,icon,draftFor,learning,date,time,languageName,modeLabel})=>{
 const $=s=>document.querySelector(s), t=k=>window.TrainerI18n.t('conversation18.'+k), D=n=>window.TrainerI18n.t('dashboard.text_'+n);
 const sessions=new Map();let current=null,data=null,voiceUnsubscribe=null;
 const ui=()=>sessions.get(current);
 const locale=()=>window.TrainerI18n.locale;
 const money=p=>p===null||p===undefined||p===''?window.TrainerI18n.t('company17.unknown'):new Intl.NumberFormat(locale(),{style:'currency',currency:'EUR'}).format(Number(p));
 const article=p=>p.article||(!p.id?.startsWith('item_')?p.id:'');
 function capture(){
  const log=$('#chat-messages');if(!log||!ui())return;
  if(log.clientHeight){
   const top=log.getBoundingClientRect().top;
   const el=[...log.querySelectorAll('[data-conversation-index]')].find(e=>e.getBoundingClientRect().bottom>top+1);
   ui().anchor=log.scrollHeight-log.scrollTop-log.clientHeight<5?{bottom:true}:el?{index:el.dataset.conversationIndex,offset:el.getBoundingClientRect().top-top}:null;
  }
  const pane=$('#kc-pane');if(pane)ui().scroll[key()]=pane.scrollTop;
  const field=$('#message-text');if(field){ui().focus=document.activeElement===field?{start:field.selectionStart,end:field.selectionEnd}:null;}
 }
 function restore(){
  const log=$('#chat-messages'),a=ui()?.anchor;if(!log||!a||!log.clientHeight)return;
  if(a.bottom){log.scrollTop=log.scrollHeight;return;}
  const el=log.querySelector(`[data-conversation-index="${Number(a.index)}"]`);
  if(el)log.scrollTop+=el.getBoundingClientRect().top-log.getBoundingClientRect().top-a.offset;
 }
 function keepReading(change){capture();change();restore();}
 function grow(){const f=$('#message-text');if(!f)return;const log=$('#chat-messages'),end=log&&log.scrollHeight-log.scrollTop-log.clientHeight<5;f.style.height='auto';f.style.height=Math.min(f.scrollHeight,200)+'px';if(end)log.scrollTop=log.scrollHeight;}
 function syncVoice(v=window.TrainerVoice.snapshot()){
  if(!$('#kc-app'))return;
  const busy=window.TrainerVoice.busy(),phase=v.phase,d=draftFor(current),V=k=>window.TrainerI18n.t('dictation18.'+k);
  const send=$('.kc-app .send-btn');if(send)send.disabled=busy||d.sending||!$('#message-text')?.value.trim();
  const start=$('.kc-app [data-action="voice-start"]'),stop=$('.kc-app [data-action="voice-stop"]'),cancel=$('.kc-app [data-action="voice-cancel"]');
  if(start){start.hidden=busy;start.disabled=busy||d.sending;}
  if(stop)stop.hidden=phase!=='recording';if(cancel)cancel.hidden=!busy;
  const language=$('#voice-language');if(language)language.disabled=busy;
  const status=$('#voice-status');if(status){if(status.textContent!==v.status)status.textContent=v.status;status.dataset.tone=phase==='recording'?'rec':phase==='error'?'warn':'';}
  const timer=$('#voice-timer');if(timer){timer.hidden=phase!=='recording';timer.textContent=`0:${String(v.elapsed).padStart(2,'0')} / 1:00`;if(v.elapsed>=60)timer.textContent='1:00 / 1:00';}
  const meter=$('#voice-meter');if(meter){meter.hidden=phase!=='recording'||!v.meterAvailable;meter.querySelectorAll('i').forEach((bar,i)=>{bar.style.height=(3+v.level*[10,18,24,29,24,18,10][i])+'px';});}
  const unavailable=$('#voice-meter-unavailable');if(unavailable){unavailable.hidden=phase!=='recording'||v.meterAvailable;unavailable.textContent=V('meter_unavailable');}
  const flag=$('#kc-draft-flag');if(flag)flag.hidden=!$('#message-text')?.value.trim();
 }
 const key=()=>ui().tab+(ui().tab==='products'?':'+ui().view:'');
 const tabLabels=()=>({products:window.TrainerI18n.t('company17.products'),services:t('services'),terms:t('terms'),about:t('company'),documents:window.TrainerI18n.t('company17.documents')});
 function notice(p){return p?.original_language?`<p class="kc-cap">${E(window.TrainerI18n.t('company17.original_language'))}: ${E(p.original_language.toUpperCase())}${p.original_language!==locale()?' · '+E(window.TrainerI18n.t('company17.missing_translation')):''}</p>`:'';}
 /* Occurrences are retained: imported free text or duplicate labels must not disappear in a Map. */
 function features(text){const counts=new Map();return String(text||'').split(';').map(x=>x.trim()).filter(Boolean).map(x=>{const i=x.indexOf(':'),label=i<0?t('feature'):x.slice(0,i).trim(),n=counts.get(label)||0;counts.set(label,n+1);return {key:JSON.stringify([label,n]),label,value:i<0?x:x.slice(i+1).trim()};});}
 const empty=()=>E(window.TrainerI18n.t('company17.unknown'));
 function products(){
  if(!data.products?.length)return `<p class="kc-empty">${E(window.TrainerI18n.t('company17.empty_products'))}</p>`;
  const u=ui(),picked=(data.products||[]).find(p=>p.id===u.picked[0]);
  const q=u.query.toLocaleLowerCase(),cats=[...new Set(data.products.map(p=>p.category))];let count=0;
  const rows=data.products.map(p=>{
   const shown=[p.name,p.category,article(p),p.features].join(' ').toLocaleLowerCase().includes(q)&&(!u.category||p.category===u.category);if(shown)count++;
   const on=u.picked.includes(p.id),blocked=!on&&(u.picked.length>=3||picked&&p.category!==picked.category);
   return `<li class="kc-product" ${shown?'':'hidden'}><details data-product="${E(p.id)}" ${u.open.has(p.id)?'open':''}><summary><span class="kc-p-name">${E(p.name)}</span><span class="kc-p-price">${money(p.price_eur)}</span><span class="kc-p-meta">${E(p.category)}${article(p)?' · '+E(article(p)):''}</span><span class="kc-p-feat">${E(p.features)}</span><span class="kc-product-open">${E(t('view_product'))}${icon('chevron')}</span></summary><div class="kc-p-detail">${notice(p)}<dl class="kc-dl">${features(p.features).map(f=>`<dt>${E(f.label)}</dt><dd>${E(f.value)}</dd>`).join('')}${['price_includes','availability','promotion','valid_until'].map(k=>`<dt>${E(t(k))}</dt><dd>${p[k]?E(p[k]):empty()}</dd>`).join('')}</dl></div></details><label class="kc-pick-label"><input type="checkbox" class="kc-pick" data-pick="${E(p.id)}" aria-label="${E(t('pick'))}: ${E(p.name)}" ${on?'checked':''} ${blocked?'disabled':''} title="${E(t('compare_rule'))}"><span>${E(t('pick'))}</span></label></li>`;
  }).join('');
  return `<p class="kc-cap">${E(t('compare_rule'))}</p><div class="kc-filters"><input type="search" id="kc-q" aria-label="${E(t('search'))}" placeholder="${E(t('search'))}" value="${E(u.query)}"><select id="kc-cat" class="kc-select" aria-label="${E(window.TrainerI18n.t('company17.category'))}"><option value="">${E(window.TrainerI18n.t('company17.all'))}</option>${cats.map(c=>`<option ${c===u.category?'selected':''}>${E(c)}</option>`).join('')}</select><span class="kc-count" id="kc-n" aria-live="polite">${count}</span></div><p class="kc-cap" id="kc-no-products" ${count?'hidden':''}>${E(t('no_results'))}</p><ul class="kc-products">${rows}</ul>${u.picked.length?`<div class="kc-comparebar"><span role="status">${E(t(u.picked.length===1?'compare_one':'compare_rule'))}</span><button type="button" class="kc-btn" data-kc="clear">${E(t('clear'))}</button><button type="button" class="kc-btn kc-btn--primary" data-kc="compare" ${u.picked.length<2?'disabled':''}>${E(t('compare'))} (${u.picked.length})</button></div>`:''}`;
 }
 function compare(){
  const ps=ui().picked.map(id=>data.products.find(p=>p.id===id)).filter(Boolean),maps=ps.map(p=>new Map(features(p.features).map(f=>[f.key,f]))),labels=new Map();
  maps.forEach(m=>m.forEach((f,k)=>labels.set(k,f.label)));
  const row=(label,values)=>`<tr><th scope="row">${E(label)}</th>${values.map(v=>`<td>${v}</td>`).join('')}</tr>`;
  return `<button type="button" class="kc-btn kc-btn--text" data-kc="list">${icon('back')}${E(t('back_products'))}</button><div class="kc-tablewrap"><table class="kc-compare"><thead><tr><th scope="col">${E(t('feature'))}</th>${ps.map(p=>`<th scope="col">${E(p.name)}<small>${E(article(p))}</small></th>`).join('')}</tr></thead><tbody>${row(window.TrainerI18n.t('company17.price'),ps.map(p=>money(p.price_eur)))}${[...labels].map(([k,label])=>row(label,maps.map(m=>m.has(k)?E(m.get(k).value):empty()))).join('')}${['price_includes','availability','promotion','valid_until'].map(k=>row(t(k),ps.map(p=>p[k]?E(p[k]):empty()))).join('')}</tbody></table></div><p class="kc-cap">${E(t('no_service_sum'))}</p><button type="button" class="kc-btn kc-btn--text" data-kc-tab="services">${E(t('services'))}</button>`;
 }
 function services(){return `<ul class="kc-rows">${(data.services||[]).map(s=>`<li class="kc-service"><strong>${E(s.title||s.name)}</strong><span class="kc-p-price">${money(s.price_eur)}</span><span class="kc-inc">${E(s.id==='repair'?window.TrainerI18n.t('company17.repair_scope'):s.description)}</span>${notice(s)}<details><summary>${E(window.TrainerI18n.t('company17.more'))}</summary><p>${E(s.conditions||'')||empty()}</p></details></li>`).join('')}</ul>`;}
 function paneHTML(){
  if(!data)return `<p>${E(window.TrainerI18n.t('learning.no_materials'))}</p>`;
  const u=ui(),noticeKey={about:'description',products:'products',services:'services',terms:'terms',documents:'policy'}[u.tab];
  const warning=data.notices?.[noticeKey]?`<p class="kc-cap">${E(data.notices[noticeKey])}</p>`:'';
  let content='';
  if(u.tab==='products')content=u.view==='compare'?compare():products();
  else if(u.tab==='services')content=services();
  else if(u.tab==='terms')content=(data.terms||[]).map(([title,text])=>`<details class="kc-acc"><summary>${E(title)}</summary><p class="kc-prose">${E(text)}</p></details>`).join('');
  else if(u.tab==='about')content=`<h3>${E(data.name)}</h3><p>${E(data.about)}</p><p class="kc-cap">${E(window.TrainerI18n.t('company17.fictional'))}</p>`;
  else content=(data.documents||[]).map(d=>`<details class="kc-acc"><summary>${E(d.title)}</summary>${d.notice?`<p class="kc-cap">${E(d.notice)}</p>`:''}${d.source_id?`<a class="kc-btn" target="_blank" rel="noopener" href="/api/company-documents/${encodeURIComponent(d.source_id)}/original">${E(window.TrainerI18n.t('company17.original'))}</a>`:''}<div class="kc-prose">${E(d.text)}</div></details>`).join('')+`<button class="kc-btn" data-kc-tab="services">${E(t('services'))} · CSV</button><button class="kc-btn" data-kc-tab="products">${E(tabLabels().products)} · CSV</button>`;
  return (data.no_catalogue?`<p class="kc-cap">${E(window.TrainerI18n.t('learning.no_materials'))}</p>`:'')+warning+content;
 }
 function renderPane(){const pane=$('#kc-pane');if(!pane)return;pane.innerHTML=paneHTML();pane.scrollTop=ui().scroll[key()]||0;document.querySelectorAll('[data-kc-tab]').forEach(b=>{if(b.getAttribute('role')==='tab'){const active=b.dataset.kcTab===ui().tab;b.setAttribute('aria-selected',String(active));b.tabIndex=active?0:-1;}});$('#kc-pane')?.setAttribute('aria-labelledby','kc-tab-'+ui().tab);}
 function switchPane(change){
  const pane=$('#kc-pane'),active=document.activeElement,focused=active?.dataset?.pick?{pick:active.dataset.pick}:['kc-q','kc-cat'].includes(active?.id)?{id:active.id}:null;
  if(pane)ui().scroll[key()]=pane.scrollTop;change();renderPane();
  window.TrainerHeaderMenus?.enhanceSelects();
  const next=focused?.pick?[...document.querySelectorAll('[data-pick]')].find(el=>el.dataset.pick===focused.pick):focused?.id?document.getElementById(focused.id):null;
  next?.focus({preventScroll:true});
 }
 function setPanel(open){keepReading(()=>{ui().panel=open;$('#kc-app').dataset.panel=open?'open':'closed';$('#kc-panel').hidden=!open;$('#kc-grip').hidden=!open;document.querySelectorAll('[data-kc="panel"]').forEach(b=>b.setAttribute('aria-expanded',String(open)));$('[data-kc="talk"]').setAttribute('aria-pressed',String(!open));$('[data-kc="reference"]').setAttribute('aria-pressed',String(open));});}
 function setWidth(width){keepReading(()=>{ui().width=Math.round(Math.max(420,Math.min(760,width)));$('#kc-app').style.setProperty('--kc-panel',ui().width+'px');});}
 function page(s){
  current=s.id;if(!sessions.has(current))sessions.set(current,{panel:false,guide:false,tab:'products',view:'list',query:'',category:'',picked:[],open:new Set(),scroll:{},width:560,anchor:{bottom:true},voiceLanguage:s.training_language||'de'});
  const u=ui(),d=draftFor(s.id),limit=state.status?.limits?.max_turns||30,complete=s.phase==='completed',exhausted=s.turn_count>=limit;
  data=learning.referenceData(s.learning_context?.materials,s.company);u.picked=u.picked.filter(id=>data?.products?.some(p=>p.id===id));if(u.picked.length<2)u.view='list';
  const btn=(action,label,cls='')=>`<button type="button" class="kc-bar-btn ${cls}" data-kc="${action}" aria-expanded="${action==='panel'?u.panel:u.guide}" aria-controls="${action==='panel'?'kc-panel':'kc-guide'}">${E(label)}</button>`;
  const finish=`<button class="kc-bar-btn" type="button" aria-label="${E(D(complete?'169':'170'))}" data-action="finish" ${d.sending?'disabled':''}>${icon('clipboard')}<span class="kc-finish-label">${E(D(complete?'169':'170'))}</span><span class="kc-sr">${E(D(complete?'169':'170'))}</span></button>`;
  const saved=window.TrainerI18n.t('chat.saved_notice',{name:s.selection?.persona_label||D('001'),personaVersion:s.selection?.persona_version||s.client_profile?.persona_version||'—',scenarioVersion:s.selection?.scenario_revision||s.client_profile?.source_revision||'—',id:s.id});
  const composer=complete||exhausted?`<div class="kc-composer"><div class="kc-col kc-end"><h3>${E(D(complete?'175':'176'))}</h3><p>${E(D(complete?'177':'178'))}</p><button class="kc-btn kc-btn--primary" data-action="finish">${E(D('169'))}</button></div></div>`:`<form class="kc-composer" id="message-form"><div class="kc-col kc-composer-grid"><div class="kc-who"><strong>${E(t('your_reply'))}</strong><span>${E(t('draft'))}</span></div><div><div class="kc-field"><label class="kc-sr" for="message-text">${E(D('185'))}</label><textarea id="message-text" name="message" rows="1" maxlength="6000" required placeholder="${E(D(d.kind==='summary'?'179':d.kind==='proposal'?'180':'181'))}" ${d.sending?'disabled':''}>${E(d.text)}</textarea><div class="kc-tools"><button type="button" class="kc-btn voice-mic" data-action="voice-start" title="${E(window.TrainerI18n.t('dictation18.start'))}" aria-label="${E(window.TrainerI18n.t('dictation18.start'))}">${icon('mic')}</button><button type="button" class="kc-btn kc-btn--rec voice-stop" data-action="voice-stop" hidden title="${E(window.TrainerI18n.t('dictation18.stop'))}" aria-label="${E(window.TrainerI18n.t('dictation18.stop'))}"><span aria-hidden="true">■</span></button><button type="button" class="kc-btn voice-cancel" data-action="voice-cancel" hidden title="${E(window.TrainerI18n.t('dictation18.cancel'))}" aria-label="${E(window.TrainerI18n.t('dictation18.cancel'))}"><span aria-hidden="true">×</span></button><label class="kc-sr" for="voice-language">${E(D('191'))}</label><select id="voice-language" class="kc-select">${['de','en','ru'].map(l=>`<option value="${l}" ${u.voiceLanguage===l?'selected':''}>${E(languageName(l))}</option>`).join('')}</select><span id="voice-meter" class="voice-meter" role="img" aria-label="${E(window.TrainerI18n.t('dictation18.meter'))}" hidden>${'<i></i>'.repeat(7)}</span><span id="voice-timer" class="voice-timer" role="timer" aria-live="off" aria-label="${E(window.TrainerI18n.t('dictation18.duration'))}" hidden></span><span id="voice-meter-unavailable" class="kc-cap" hidden></span><span id="voice-status" class="kc-status" role="status"></span><span class="kc-keys"><kbd>Ctrl / Cmd</kbd> + <kbd>Enter</kbd></span><button type="submit" class="kc-btn kc-btn--primary send-btn" aria-label="${E(D('186'))}" ${d.sending||!d.text.trim()?'disabled':''}>${E(t('send'))}${icon('arrow')}</button></div></div><div class="kc-foot"><span>${E(D('193'))}</span><span>${E(D('183'))} · ${s.turn_count}/${limit}</span></div>${d.error?`<div class="notice error" role="alert"><p>${E(d.error)}</p><button type="button" class="kc-btn" data-action="retry-message">${E(D('184'))}</button></div>`:''}</div></div></form>`;
  return `<div class="kc-app" id="kc-app" data-panel="${u.panel?'open':'closed'}"><header class="kc-bar"><button class="kc-bar-btn kc-bar-btn--icon menu-btn" data-action="menu" aria-label="${E(D('043'))}" aria-controls="sidebar" aria-expanded="${state.menu}">${icon('menu')}</button><a class="kc-brand" href="#learner/practice"><span class="kc-brand-mark">K<span>·</span></span><span class="kc-brand-text">klare ki</span></a><a class="kc-bar-btn kc-bar-btn--plain" href="#learner/practice" aria-label="${E(D('206'))}">${icon('back')}<span class="kc-back-label">${E(D('206'))}</span></a><div class="kc-title"><div class="kc-title-row"><h1>${E(s.customer_name)}</h1><span class="kc-pill">${E(modeLabel(s.mode))}</span></div><p>${E(s.title)} · ${E(window.TrainerI18n.t('training.language'))}: ${E(languageName(s.training_language))}</p></div>${btn('guide',t('guide'),'kc-bar-btn--plain')}${btn('panel',t('catalogue'))}${finish}</header><div class="kc-switch" role="group" aria-label="${E(t('view'))}"><button type="button" data-kc="talk" aria-pressed="${!u.panel}">${E(t('conversation'))} <small id="kc-draft-flag" ${d.text.trim()?'':'hidden'}>· ${E(t('draft'))}</small></button><button type="button" data-kc="reference" aria-pressed="${u.panel}">${E(t('catalogue'))}</button></div><div class="kc-guide" id="kc-guide" ${u.guide?'':'hidden'}><ol>${['needs','capabilities','proposal'].map((_,i)=>`<li><span class="kc-num">${i+1}</span><span><b>${E(D(['039','040','041'][i]))}</b>${E(D(['637','639','641'][i]))}</span></li>`).join('')}</ol></div><div class="kc-body"><section class="kc-talk" aria-label="${E(D('207'))}"><div class="kc-log" id="chat-messages" role="log" aria-label="${E(D('208'))}" aria-live="polite" aria-relevant="additions" tabindex="0"><div class="kc-col"><p class="kc-note">${E(saved)}</p>${s.mode==='demo'?`<p class="notice amber">${E(D('092'))} ${E(D('093'))}</p>`:''}<div class="kc-date">${E(date(s.created_at))}</div>${s.messages.map((m,i)=>`<article class="kc-turn ${m.role==='learner'?'kc-turn--me':''}" data-conversation-index="${i}"><div class="kc-who"><strong>${E(m.role==='learner'?D('168'):s.customer_name)}</strong><span>${E(m.role==='learner'?t('employee'):modeLabel(s.mode))} · <time datetime="${E(m.at)}">${E(time(m.at))}</time></span></div><p>${E(m.text)}</p></article>`).join('')}${d.sending?`<article class="kc-turn"><div class="kc-who"><strong>${E(s.customer_name)}</strong><span>${E(D('171'))}</span></div><p role="status">${E(D('173'))} <span class="kc-typing"><i></i><i></i><i></i></span></p></article>`:''}</div></div>${composer}</section><button type="button" class="kc-grip" id="kc-grip" aria-label="${E(t('resize'))}" ${u.panel?'':'hidden'}></button><aside class="kc-panel" id="kc-panel" aria-labelledby="kc-panel-title" ${u.panel?'':'hidden'}><div class="kc-panel-head"><div><h2 id="kc-panel-title">${E(t('catalogue'))}</h2><p>${E(data?.name||s.company?.name||'')} · ${E(window.TrainerI18n.t('learning.saved_materials'))}</p></div><button class="kc-x" data-kc="panel" aria-label="${E(t('close_panel'))}">${icon('close')}</button></div><div class="kc-tabs" role="tablist" aria-label="${E(t('sections'))}">${Object.entries(tabLabels()).map(([k,label])=>`<button type="button" role="tab" id="kc-tab-${k}" aria-controls="kc-pane" data-kc-tab="${k}" aria-selected="${k===u.tab}" tabindex="${k===u.tab?0:-1}">${E(label)}</button>`).join('')}</div><div class="kc-pane" id="kc-pane" role="tabpanel" tabindex="0"></div></aside></div></div>`;
 }
 function afterRender(active){
  voiceUnsubscribe?.();voiceUnsubscribe=null;if(!active)return;
  drawer(state.menu,false);
  $('#kc-app').style.setProperty('--kc-panel',ui().width+'px');
  renderPane();syncVoice();
  voiceUnsubscribe=window.TrainerVoice.subscribe(syncVoice);grow();
  requestAnimationFrame(()=>{restore();const f=$('#message-text'),focus=ui()?.focus;if(f&&focus){f.focus({preventScroll:true});f.setSelectionRange(focus.start,focus.end);}});
  const grip=$('#kc-grip');grip.onpointerdown=e=>{e.preventDefault();grip.setPointerCapture(e.pointerId);const sx=e.clientX,sw=$('#kc-panel').getBoundingClientRect().width;const move=ev=>setWidth(sw+sx-ev.clientX),up=()=>{grip.removeEventListener('pointermove',move);grip.removeEventListener('pointerup',up);grip.removeEventListener('pointercancel',up);};grip.addEventListener('pointermove',move);grip.addEventListener('pointerup',up);grip.addEventListener('pointercancel',up);};
 }
 function drawer(open,focus=true){
  if(!$('#kc-app'))return;
  const side=$('#sidebar');side.inert=!open;side.setAttribute('aria-hidden',String(!open));$('#main-content').inert=open;
  if(focus)(open?side.querySelector('.conversation-drawer-close'):$('#kc-app .menu-btn'))?.focus({preventScroll:true});
 }
 document.addEventListener('click',e=>{
  const button=e.target.closest('[data-kc],[data-kc-tab]');if(!button||!$('#kc-app')||button.disabled)return;
  if(button.dataset.kcTab){switchPane(()=>{ui().tab=button.dataset.kcTab;if(button.getAttribute('role')!=='tab'&&ui().tab==='products')ui().view='list';});return;}
  const action=button.dataset.kc;
  if(action==='panel')setPanel(!ui().panel);if(action==='talk')setPanel(false);if(action==='reference')setPanel(true);
  if(action==='guide')keepReading(()=>{ui().guide=!ui().guide;$('#kc-guide').hidden=!ui().guide;button.setAttribute('aria-expanded',String(ui().guide));});
  if(action==='clear')switchPane(()=>{ui().picked=[];ui().view='list';});
  if(action==='compare'&&ui().picked.length>=2&&ui().picked.length<=3)switchPane(()=>{ui().view='compare';});if(action==='list')switchPane(()=>{ui().view='list';});
 });
 document.addEventListener('input',e=>{
  if(!$('#kc-app'))return;
  if(e.target.id==='message-text'){grow();syncVoice();}
  if(e.target.id==='kc-q'){
   ui().query=e.target.value;const q=ui().query.toLocaleLowerCase();let n=0;
   document.querySelectorAll('.kc-product').forEach((el,i)=>{const p=data.products[i];el.hidden=![p.name,p.category,article(p),p.features].join(' ').toLocaleLowerCase().includes(q)||Boolean(ui().category&&p.category!==ui().category);if(!el.hidden)n++;});$('#kc-n').textContent=n;$('#kc-no-products').hidden=!!n;
  }
 });
 document.addEventListener('change',e=>{
  if(!$('#kc-app'))return;
  if(e.target.id==='voice-language')ui().voiceLanguage=e.target.value;
  if(e.target.id==='kc-cat')switchPane(()=>{ui().category=e.target.value;});
  if(e.target.dataset.pick){const id=e.target.dataset.pick;switchPane(()=>{ui().picked=e.target.checked?[...ui().picked,id]:ui().picked.filter(x=>x!==id);});}
 });
 document.addEventListener('toggle',e=>{if(e.target.dataset?.product&&ui()){const id=e.target.dataset.product;if(e.target.open)ui().open.add(id);else ui().open.delete(id);}},true);
 document.addEventListener('keydown',e=>{
  if(!$('#kc-app'))return;
  if(state.menu&&e.key==='Tab'){
   const items=[...$('#sidebar').querySelectorAll('a,button,summary,select,input')].filter(el=>!el.disabled&&el.getClientRects().length),first=items[0],last=items.at(-1);
   if(e.shiftKey&&document.activeElement===first){e.preventDefault();last?.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first?.focus();}
  }
  if(e.target.id==='kc-grip'&&['ArrowLeft','ArrowRight'].includes(e.key)){e.preventDefault();setWidth($('#kc-panel').getBoundingClientRect().width+(e.key==='ArrowLeft'?40:-40));}
  if(e.target.closest('.kc-tabs')&&['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){
   e.preventDefault();const keys=Object.keys(tabLabels()),i=keys.indexOf(ui().tab),next=e.key==='Home'?0:e.key==='End'?keys.length-1:(i+(e.key==='ArrowRight'?1:keys.length-1))%keys.length;switchPane(()=>{ui().tab=keys[next];});$('#kc-tab-'+ui().tab).focus();
  }
 });
 let resizePending=false;
 document.addEventListener('scroll',e=>{if(e.target.id==='chat-messages'&&!resizePending)capture();},true);
 window.addEventListener('resize',()=>{if($('#kc-app')){resizePending=true;requestAnimationFrame(()=>{restore();resizePending=false;});}});
 return {page,capture,afterRender,syncVoice,drawer};
};
