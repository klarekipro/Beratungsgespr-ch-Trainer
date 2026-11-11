"use strict";
window.createLearning = ({state,api,esc,render,toast}) => {
 const t=k=>window.TrainerI18n.t('learning.'+k), E=esc;
 let results={reviews:[],certificates:[]},history=[],materials=null,guidance=null,preview=null,cert=null,busy=false;
 const locale=()=>window.TRAINER_AUTH.user.locale||'de';
 const options=(xs,v)=>xs.map(x=>`<option value="${x}" ${v===x?'selected':''}>${t(x)}</option>`).join('');
 const field=(id,label,value='',rows=3)=>`<label for="${id}">${t(label)}</label><textarea id="${id}" rows="${rows}">${E(value)}</textarea>`;
 const T=window.TrainerUI.t;
 const reference=window.createCompanyReference({state,api,esc});
 let read={},preferences=null;
 const storageKey=k=>'trainer.'+window.TRAINER_AUTH.user.id+'.'+k;
 const current=k=>preferences?.[k]||localStorage.getItem(storageKey(k))||localStorage.getItem('learning.'+k)||(k==='layout'?'auto':'normal');
 const appearance=k=>window.TrainerI18n.t('appearance18.'+k);
 const theme=()=>preferences?.theme||localStorage.getItem(storageKey('theme'))||'system';
 let themeWrites=Promise.resolve(),confirmedPreferences=null,themeRevision=0;
 async function setTheme(next){
  if(!['light','dark','system'].includes(next))return;
  const revision=++themeRevision;preferences={...(preferences||{}),theme:next};applyView();
  const payload={layout:preferences.layout||'auto',density:preferences.density||'normal',theme:next};
  const write=themeWrites.then(()=>api('/api/ui/preferences',{method:'PUT',body:payload}));themeWrites=write.catch(()=>{});
  try{const result=await write;confirmedPreferences=result.preferences||payload;localStorage.setItem(storageKey('theme'),next);}
  catch(error){if(revision===themeRevision){preferences=confirmedPreferences;applyView();}toast(error.message,true);}
 }
 const systemDark=window.matchMedia('(prefers-color-scheme: dark)');
 const buttons=()=>`<details class="view-settings"><summary class="btn small-btn">${appearance('title')}</summary><div class="view-settings-panel"><button type="button" class="btn appearance-close" data-close-appearance aria-label="${appearance('close')}" title="${appearance('close')}">×</button><label for="learning-theme">${appearance('title')}</label><select id="learning-theme">${['light','dark','system'].map(v=>`<option value="${v}" ${theme()===v?'selected':''}>${appearance(v)}</option>`).join('')}</select></div></details>`;
 function applyView(){
  const selected=theme();document.documentElement.dataset.theme=selected==='system'?(systemDark.matches?'dark':'light'):selected;
  document.documentElement.style.colorScheme=document.documentElement.dataset.theme;
  document.body.dataset.learningLayout='auto';document.body.dataset.learningDensity='normal';
 }
 if(systemDark.addEventListener)systemDark.addEventListener('change',applyView);else systemDark.addListener(applyView);
 applyView();
 const unread=()=>results.reviews.filter(r=>read[r.session_id]!==r.published_at);
 const isNew=id=>unread().some(r=>r.session_id===id);
 const notification=()=>state.route.role==='learner'&&unread().length?`<a class="btn small-btn new-feedback" href="#learner/history/new">${T('new_reviews')} <strong>${unread().length}</strong></a>`:'';
 const certificates=()=>certificateList(window.TRAINER_AUTH.user.id)||`<section class="card card-pad">${t('none')}</section>`;
 const certificateCount=()=>results.certificates.filter(c=>c.employee_id===window.TRAINER_AUTH.user.id).length;
 async function markRead(){const r=state.session?.published_review;if(state.route.role==='learner'&&r&&isNew(r.session_id)){read=(await api('/api/ui/reviews/read',{method:'POST',body:{session_id:r.session_id,published_at:r.published_at}})).read;const badge=document.querySelector('.new-feedback');if(badge)badge.outerHTML=notification();}}
 async function load(){
  const [r,receipts,prefs]=await Promise.all([api('/api/learning/results'),api('/api/ui/reviews/read'),api('/api/ui/preferences')]);results=r;read=receipts.read;preferences=prefs.preferences;confirmedPreferences=preferences;history=[];applyView();
  const s=state.session;
  if(state.route.view==='review'&&s?.employee_id)history=(await api('/api/mentor/employees/'+encodeURIComponent(s.employee_id)+'/sessions')).sessions;
  if(state.route.view==='company'){materials=(await api('/api/learning/materials')).materials;await reference.load();}
  if(state.route.view==='scenario'&&state.route.id!=='new')guidance=(await api('/api/mentor/learning/guidance/'+encodeURIComponent(state.route.id))).guidance;
 }
 const certificateList=uid=>results.certificates.filter(c=>!uid||c.employee_id===uid).map(c=>`<div class="learning-result"><strong>${E(c.topic)}</strong> · ${E(c.number)} · ${t(c.status)}<p>${E(c.print_name)} · ${E(c.mentor_name)} · ${E(c.issued_at?.slice(0,10))}</p><a class="btn" target="_blank" rel="noopener" href="/api/learning/certificates/${E(c.id)}.pdf?language=${locale()}">PDF · ${t('print')}</a>${state.route.role==='mentor'&&c.status==='issued'?`<button class="btn" data-action="learning-revoke" data-id="${E(c.id)}">${t('revoke')}</button><button class="btn" data-action="learning-replace" data-id="${E(c.id)}">${t('replace')}</button>`:''}</div>`).join('');
 const R=k=>window.TrainerI18n.t('review22.'+k);
 function employeeReport(s){
  const h=s.review_heading||{company:s.company.name,title:s.title,customer:s.customer_name,objective:'',language:s.training_language};
  const a=s.analysis||{status:'not_run'},result=a.result,ready=!!result,processing=busy||a.status==='running';
  const stageKeys=['needs','capabilities','proposal'];
  const stageHTML=stageKeys.map(key=>{const stage=result?.stages?.find(x=>x.key===key);return `<section class="review22-stage"><div class="review22-stage-heading"><h3>${R(key)}</h3><span class="pill">${R(stage?.status||'not_analysed')}</span></div>${stage?`<p>${E(stage.observation)}</p>${stage.evidence.length?`<button type="button" class="text-link" data-action="learning-review-evidence" data-evidence="${E(JSON.stringify(stage.evidence.map(x=>x.message_id)))}">${R('view')}</button>`:''}`:`<p class="caption">${R(a.status==='error'?'stages_error':'stages_not_started')}</p>`}</section>`;}).join('');
  const lists=result?.summary?`<p>${E(result.summary)}</p><p><strong>${R('actual_outcome')}:</strong> ${E(result.actual_outcome)}</p>${['strengths','gaps','next_attempt'].map(k=>`<h3>${R(k)}</h3><ul>${result[k].map(x=>`<li>${E(x)}</li>`).join('')}</ul>`).join('')}`:(result?.sections||[]).map(x=>`<h3>${E(x.title)}</h3><p>${E(x.text)}</p>`).join('');
  const savedFindings=(s.report?.findings||[]).filter(f=>window.TrainerPresentation.publicNotes([f.detail]).length);
  const retained=savedFindings.length?`<h3>${R('saved_observations')}</h3><ul>${savedFindings.map(f=>`<li>${E(window.TrainerI18n.systemText(f.detail))}</li>`).join('')}</ul>`:'';
  const feedback=s.published_review;
  return `<div class="review22-page"><header class="card card-pad review22-heading"><p class="eyebrow">${E(h.company)}</p><h1>${E(h.title)}</h1><p>${E(h.customer)} · ${R('training_language')}: ${E(String(h.language||'').toUpperCase())}</p><p class="review22-objective"><strong>${R('objective')}:</strong> ${E(h.objective||R('objective_missing'))}</p>${h.fallback&&h.objective?`<p class="caption">${R('objective_fallback')}</p>`:''}${h.context_source==='legacy_fallback_not_original'?`<p class="caption">${t('legacy')}</p>`:''}</header><section class="review22-status notice ${s.review_status==='submitted'?'amber':'neutral'}" role="status"><strong>${R(feedback?'status_reviewed':'status_'+s.review_status)}</strong>${s.review_status==='not_submitted'&&!feedback?`<p class="caption gap-top">${R('keep_private')}</p>`:''}</section><section class="card card-pad" id="learning-analysis"><h2>${R('preliminary')}</h2><p class="caption">${R('notice')}</p><p role="status">${R(processing?'running':ready?'ready':a.status==='error'?'failed':'not_started')}</p>${!processing&&(a.status==='error'||a.attempt_status==='error')?`<p role="alert">${R(a.error==='ai_context_limit'?'context_error':a.attempt_status==='error'?'regeneration_error':'error')}</p>`:''}${lists}${retained}<button type="button" class="btn small-btn" data-action="learning-analysis" ${processing?'disabled':''}>${R(ready?'regenerate':a.status==='error'?'retry':'analyze')}</button></section><section class="card card-pad"><h2>${R('stages')}</h2>${ready?stageHTML:`<p>${R('not_analysed')}. ${R(a.status==='error'?'stages_error':'stages_not_started')}</p>`}</section><section class="card card-pad review22-actions"><div class="actions"><button type="button" class="btn" data-action="repeat" data-id="${E(s.scenario_id)}" data-mode="${E(s.mode)}" ${state.starting?'disabled':''}>${R('repeat')}</button>${s.review_status==='not_submitted'&&!feedback?`<button type="button" class="btn primary" data-action="submit-review" ${state.saving?'disabled':''}>${R(state.saving?'sending':'send')}</button>`:`<span class="pill green" role="status">${R(feedback?'status_reviewed':'status_submitted')}</span>`}<button type="button" class="btn" data-action="learning-review-viewer">${R('view_conversation')}</button></div></section><a class="text-link" href="#learner/practice">${R('choose_other')}</a>${feedback?`<section id="learning-published-review" class="card card-pad"><h2>${R('mentor_feedback')}</h2><p>${E(feedback.mentor_name)}</p><p class="review-note">${E(feedback.note)}</p>${feedback.observations?`<p>${E(feedback.observations)}</p>`:''}${feedback.assessment?`<h3>${R('mentor_stages')}</h3>${stageKeys.map(k=>`<p><strong>${R(k)}:</strong> ${window.TrainerI18n.t('review.rating.'+(feedback.assessment.stages?.[k]||'not_reviewed'))}</p>`).join('')}<p><strong>${R('actual_outcome')}:</strong> ${window.TrainerI18n.t(feedback.assessment.commercial_outcome?'review.outcome.'+feedback.assessment.commercial_outcome:'review.unset')}</p>`:''}</section>`:''}<a class="text-link" href="#learner/history/all">${R('my_conversations')}</a></div>`;
 }
 function openReviewViewer(s,evidence=[]){
  if(document.querySelector('.review22-viewer[open]'))return;
  const focus=document.activeElement,dialog=document.createElement('dialog');dialog.className='review22-viewer';dialog.setAttribute('aria-label',R('view_conversation'));
  const ids=s.review_message_ids||s.messages.map((_,i)=>String(i));
  dialog.innerHTML=`<header><h2>${R('view_conversation')} <small>(${s.messages.length})</small></h2><nav aria-label="${R('exports')}">${['pdf','txt','json'].map(format=>`<button type="button" class="btn small-btn" data-viewer-export="${format}">${format.toUpperCase()}</button>`).join('')}</nav><button type="button" class="btn small-btn" data-viewer-close>${R('close')}</button></header><div class="review22-viewer-body"><div class="review22-evidence-nav" ${evidence.length?'':'hidden'}>${evidence.map((mid,i)=>`<button type="button" class="btn small-btn" data-evidence-id="${E(mid)}">${R('evidence')} ${i+1}</button>`).join('')}</div><div class="review22-transcript">${s.messages.map((msg,i)=>`<article tabindex="-1" data-review-message="${E(ids[i])}" class="review22-message ${msg.role==='learner'?'learner':''}"><strong>${t(msg.role==='learner'?'employee':'customer')} · ${i+1}</strong><p>${E(msg.text)}</p></article>`).join('')}</div><details class="review22-historical"><summary>${R('saved_reference')}</summary><p>${E(s.company.description)}</p>${s.company.services.map(x=>`<h3>${E(x.title)}</h3><p>${E(x.description)}</p><p>${E(x.conditions)}</p>`).join('')}<p>${E(s.company.limitations)}</p></details><p class="caption">${R('export_language')}: ${E(String(s.training_language||'').toUpperCase())}</p></div>`;
  // The saved company is sufficient for the secondary reference; never load current data.
  document.body.append(dialog);dialog.showModal();dialog.querySelector('[data-viewer-close]').focus();
  const reveal=id=>{const el=[...dialog.querySelectorAll('[data-review-message]')].find(x=>x.dataset.reviewMessage===id);if(!el)return;el.scrollIntoView({block:'center',behavior:'instant'});el.focus({preventScroll:true});el.classList.add('learning-highlight');setTimeout(()=>el.classList.remove('learning-highlight'),3500);};
  dialog.addEventListener('click',async e=>{const b=e.target.closest('button');if(!b)return;if(b.hasAttribute('data-viewer-close'))dialog.close();if(b.dataset.evidenceId)reveal(b.dataset.evidenceId);if(b.dataset.viewerExport){const format=b.dataset.viewerExport;b.disabled=true;try{const response=await fetch('/api/sessions/'+encodeURIComponent(s.id)+'/export.'+format+'?language='+encodeURIComponent(s.training_language),{credentials:'same-origin'});if(!response.ok)throw new Error('export');const blob=await response.blob(),url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download='consultation-'+s.id.slice(0,12)+'.'+format;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),10000);}catch(_){toast(R('export_error'),true);}finally{b.disabled=false;}}});
  const leave=()=>dialog.close();window.addEventListener('hashchange',leave);
  dialog.addEventListener('close',()=>{window.removeEventListener('hashchange',leave);dialog.remove();if(focus?.isConnected)focus.focus({preventScroll:true});},{once:true});
  if(evidence.length)requestAnimationFrame(()=>reveal(evidence[0]));
 }
 function analysis(s,mentor){
  const a=mentor?s.mentor_analysis:s.analysis;
  return `<section id="learning-analysis" class="card card-pad report-section"><button type="button" class="btn small-btn reader-expand" data-expand-target="#learning-analysis" data-expand-title="${E(t(mentor?'mentor_ai':'preliminary'))}">${T('expand')}</button><h2>${t(mentor?'mentor_ai':'preliminary')}</h2><p>${t('ai_notice')}</p><p>${t(a?.status||'not_run')} ${E(a?.completed_at||'')}</p>${a?.result?.sections.map(x=>`<h3>${E(x.title)}</h3><p>${E(x.text)}</p><div class="actions">${x.messages.map(i=>`<button class="text-link" data-action="learning-message" data-index="${i}">[${i+1}] ${t(s.messages[i]?.role==='learner'?'employee':'customer')}</button>`).join('')}</div>`).join('')||''}<button class="btn" data-action="learning-analysis" ${busy?'disabled':''}>${t(a?.status&&a.status!=='not_run'?'rerun':'analyze')}</button></section>`;
 }
 function report(s,mentor){
  const ctx=s.learning_context||{},r=s.published_review,d=state.learningDrafts?.[s.id]||s.decision_draft||{};
  return `<section class="card card-pad report-section"><strong>${E(s.employee_name)} · ${E(s.title)}</strong><p>${t('goal')}: ${E(ctx.guidance?.goal)}</p>${ctx.source==='legacy_fallback_not_original'?`<p class="notice amber">${t('legacy')}</p>`:''}</section>${analysis(s,mentor)}${r?`<section id="learning-published-review" class="card card-pad report-section"><button type="button" class="btn small-btn reader-expand" data-expand-target="#learning-published-review" data-expand-title="${E(t('feedback'))}">${T('expand')}</button><h2>${t('feedback')}</h2><strong>${E(r.mentor_name)} · ${E(r.published_at.slice(0,10))}</strong><p><strong>${t('goal')}:</strong> ${t(r.goal||'not_reviewed')}</p><p><strong>${window.TrainerI18n.t('review.commercial')}:</strong> ${window.TrainerI18n.t(r.assessment?.commercial_outcome?'review.outcome.'+r.assessment.commercial_outcome:'review.unset')}</p><p>${E(r.observations)}</p><div class="review-note">${E(r.note)}</div></section>`:''}${mentor?`<details class="card card-pad report-section"><summary>${t('employee_history')} · ${E(s.employee_name)}</summary>${history.map(x=>`<p><a href="#mentor/review/${E(x.id)}">${E(x.title)} · ${E(x.created_at.slice(0,16))}</a> · ${t(x.review_status)}</p>`).join('')}</details><section class="card card-pad report-section"><h2>${t('decision')}</h2><label>${t('goal')}<select id="learning-goal">${options(['not_reviewed','achieved','partly','not_achieved'],d.goal||'not_reviewed')}</select></label>${field('learning-observations','observations',d.observations)}<button class="btn" data-action="learning-save-draft">${t('save_draft')}</button><span id="learning-draft-status"></span><p>${t('draft_notice')}</p></section><section class="card card-pad report-section"><button class="btn primary" data-action="learning-certificate">${t('issue_certificate')}</button>${certificateList(s.employee_id)}</section>`:''}${materialPanel(ctx.materials,true)}`;
 }
 function materialPanel(m,snapshot=false){
  const ref=reference.snapshot(m,snapshot?state.session?.company:null);if(ref)return ref;
  return `<details class="card card-pad report-section ${snapshot?'reference-snapshot':''}"><summary>${t(snapshot?'saved_materials':'materials')}${snapshot?`<small>${t('saved_materials_hint')}</small>`:''}</summary>${m?`<p class="caption">${window.TrainerI18n.t('company17.original_language')}: ${E(m.original_language?.toUpperCase()||'?')} · ${window.TrainerI18n.t('company17.missing_translation')}</p><label>${t('search')}<input type="search" id="learning-product-search"></label><div id="learning-products">${m.products.map(p=>`<div class="learning-product learning-search-item"><strong>${E(p.id)} · ${E(p.name)} · ${E(p.price_eur)} €</strong><p>${E(p.category)} · ${E(p.features)}</p><p>${E(p.price_includes)} · ${E(p.availability)} · ${E(p.promotion)} · ${E(p.valid_until)}</p></div>`).join('')}</div><div class="learning-markdown">${m.markdown.split(/\n\n+/).map(x=>`<p class="learning-search-item">${E(x)}</p>`).join('')}</div>`:`<p>${t('no_materials')}</p>`}</details>`;
 }
 function importer(){return reference.importer();}
 function guidanceEditor(){if(state.route.id==='new')return `<p>${t('save_scenario_first')}</p>`;return `<section class="card card-pad report-section"><h2>${t('guidance')}</h2>${['goal','conditions','outcomes','review_notes'].map(k=>field('learning-guide-'+k,k,guidance?.[k]||'')).join('')}<button class="btn" data-action="learning-save-guidance">${t('save')}</button></section>`;}
 function draftValue(){const s=state.session;return {note:document.getElementById('review-note')?.value||state.noteDrafts[s.id]||s.review_note||'',assessment:state.assessmentDrafts?.[s.id]||{},goal:document.getElementById('learning-goal')?.value||'not_reviewed',observations:document.getElementById('learning-observations')?.value||''};}
 async function saveDraft(){const d=draftValue();await api('/api/mentor/learning/reviews/'+state.session.id+'/draft',{method:'PUT',body:d});state.learningDrafts??={};state.learningDrafts[state.session.id]=d;return d;}
 function certificateDialog(replacement=null){
  cert=null;const previous=replacement?results.certificates.find(x=>x.id===replacement):null;const s=state.session,dialog=document.getElementById('confirm-dialog');
  dialog.innerHTML=`<h2>${t('issue_certificate')}</h2><p>${E(s.employee_name)}</p><form id="learning-certificate-form"><label>${t('print_name')}<input id="learning-cert-name" value="${E(previous?.print_name||s.employee_name)}" maxlength="120" required></label><label>${t('topic')}<input id="learning-cert-topic" value="${E(previous?.topic||'')}" maxlength="240" required></label><fieldset><legend>${t('basis')}</legend>${history.filter(x=>x.status==='finished').map(x=>`<label><input type="checkbox" name="learning-basis" value="${E(x.id)}" ${x.id===s.id?'checked disabled':''}>${E(x.title)} · ${E(x.created_at.slice(0,16))}</label>`).join('')}</fieldset>${field('learning-cert-comment','comment')}<button class="btn" type="submit">${t('preview')}</button></form><div id="learning-cert-preview"></div><button class="btn" id="learning-cert-close">${t('close')}</button>`;
  dialog.showModal();document.getElementById('learning-cert-close').onclick=()=>dialog.close();
  document.getElementById('learning-certificate-form').onsubmit=async e=>{e.preventDefault();try{
   const body={session_id:s.id,print_name:document.getElementById('learning-cert-name').value,topic:document.getElementById('learning-cert-topic').value,basis:[...document.querySelectorAll('[name=learning-basis]:checked')].map(x=>x.value),comment:document.getElementById('learning-cert-comment').value,replaces:replacement};
   const r=await api('/api/mentor/learning/certificates/preview',{method:'POST',body});cert=r.certificate;
   document.getElementById('learning-cert-preview').innerHTML=`<h3>${E(cert.print_name)}</h3><p>${E(cert.topic)}</p><p>${E(cert.comment)}</p><p>${E(cert.mentor_name)} · ${E(cert.created_at.slice(0,10))}</p><a class="btn" target="_blank" href="/api/learning/certificates/${cert.id}.pdf?language=${locale()}">PDF · ${t('preview')}</a><button id="learning-cert-confirm" class="btn primary">${t('confirm_issue')}</button>`;
   document.getElementById('learning-cert-confirm').onclick=async()=>{try{const r=await api('/api/mentor/learning/certificates/'+cert.id+'/issue',{method:'POST',body:{confirm:true}});document.getElementById('learning-cert-preview').textContent=t(r.certificate.status)+' · '+r.certificate.number;await load();}catch(e){toast(e.message,true);}};
  }catch(e){toast(e.message,true);}};
 }
 async function handle(action,target){
  if(!action.startsWith('learning-'))return false;
  const s=state.session;
  if(action==='learning-review-viewer'){openReviewViewer(s);return true;}
  if(action==='learning-review-evidence'){openReviewViewer(s,JSON.parse(target.dataset.evidence));return true;}
  if(action==='learning-analysis'){if(busy)return true;busy=true;render();try{const audience=state.route.role==='mentor'?'mentor':'learner';const a=audience==='mentor'?s.mentor_analysis:s.analysis;const r=await api('/api/learning/sessions/'+s.id+'/analysis',{method:'POST',body:{audience,restart:a?.status!=='not_run'}});if(audience==='mentor')s.mentor_analysis=r.analysis;else s.analysis=r.analysis;}catch(_){toast(R('error'),true);}finally{busy=false;render();}}
  if(action==='learning-message'){document.querySelector('.ui-reader[open]>header button')?.click();const d=document.getElementById('report-transcript');d.open=true;const el=d.querySelector(`[data-message-index="${Number(target.dataset.index)}"]`);el?.scrollIntoView({behavior:'smooth',block:'center'});el?.classList.add('learning-highlight');}
  if(action==='learning-save-draft'){await saveDraft();document.getElementById('learning-draft-status').textContent=t('saved');}
  if(action==='learning-certificate')certificateDialog();
  if(action==='learning-replace')certificateDialog(target.dataset.id);
  if(action==='learning-revoke'){await api('/api/mentor/learning/certificates/'+target.dataset.id+'/revoke',{method:'POST'});await load();render();}
  if(action==='learning-preview'){
   const r=await api('/api/mentor/learning/materials/preview',{method:'POST',body:{markdown:document.getElementById('learning-markdown').value,csv:document.getElementById('learning-csv').value}});preview=r.preview;
   document.getElementById('learning-import-preview').innerHTML=`<p>${preview.products.length} ${t('products')}</p><p>${E(preview.errors.join('; '))}</p>${materialPanel(preview)}${preview.errors.length?'':`<button class="btn primary" data-action="learning-apply">${t('confirm_apply')}</button>`}`;
  }
  if(action==='learning-apply'){const r=await api('/api/mentor/learning/materials/apply',{method:'POST',body:{preview_id:preview.id}});materials=r.materials;toast(t('saved'));await load();render();}
  if(action==='learning-save-guidance'){const body=Object.fromEntries(['goal','conditions','outcomes','review_notes'].map(k=>[k,document.getElementById('learning-guide-'+k).value]));guidance=(await api('/api/mentor/learning/guidance/'+state.route.id,{method:'PUT',body})).guidance;toast(t('saved'));}
  return true;
 }
 document.addEventListener('change',async e=>{
  if(e.target.id==='learning-theme'){
   const control=e.target;control.disabled=true;window.TrainerUI.closePopover(control,true);
   try{await setTheme(control.value);control.value=theme();}finally{control.disabled=false;}
  }
  if(['learning-md-file','learning-csv-file'].includes(e.target.id)&&e.target.files[0]){const text=await e.target.files[0].text();document.getElementById(e.target.id==='learning-md-file'?'learning-markdown':'learning-csv').value=text;}
 });
 document.addEventListener('input',e=>{
  if(e.target.id==='learning-product-search'){const q=e.target.value.toLowerCase();document.querySelectorAll('.learning-search-item').forEach(x=>x.hidden=!x.textContent.toLowerCase().includes(q));}
  if(['learning-observations','learning-goal','review-note'].includes(e.target.id)&&state.session){state.learningDrafts??={};state.learningDrafts[state.session.id]=draftValue();}
 });
 return {load,report,employeeReport,referencePage:reference.page,referenceData:reference.snapshotData,materialPanel,importer,guidanceEditor,handle,saveDraft,buttons,theme,setTheme,notification,certificates,certificateCount,isNew,markRead};
};
