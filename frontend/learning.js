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
 const L=k=>window.TrainerI18n.t('review23.'+k);
 const adviceEvidence=items=>items?.length?`<button type="button" class="text-link" data-action="learning-review-evidence" data-evidence="${E(JSON.stringify(items.map(x=>x.message_id)))}">${R('view')}</button>`:'';
 function learningRecommendation(result){
  const advice=result?.recommendation;
  if(!result)return '';
  return `<section class="card card-pad review23-recommendation"><h2>${L('title')}</h2>${advice?`<h3>${L(advice.action)}</h3><p>${E(advice.explanation)}</p>${advice.priorities.length?`<ul>${advice.priorities.map(p=>`<li>${E(p)}</li>`).join('')}</ul>`:''}${adviceEvidence(advice.evidence)}<p class="caption gap-top">${L('advisory')}</p>`:`<p class="caption">${L('legacy')}</p>`}</section>`;
 }
 function companyClaimChecks(result){
  if(!result?.claim_checks?.length)return '';
  return `<details><summary>${L('conditions')} · ${result.claim_checks.length}</summary>${result.claim_checks.map(c=>`<div class="review22-stage"><strong>${E(c.statement)}</strong><p class="caption">${L('verdict_'+c.verdict)}</p><p>${E(c.observation)}</p>${adviceEvidence(c.evidence)}${c.material_evidence.length?`<details><summary>${L('saved_basis')} · ${c.material_evidence.length}</summary>${c.material_evidence.map(x=>`<blockquote>${E(x.quote||L('source_missing'))}</blockquote>`).join('')}</details>`:''}</div>`).join('')}</details>`;
 }

 function employeeReport(s){
  const h=s.review_heading||{company:s.company.name,title:s.title,customer:s.customer_name,objective:'',language:s.training_language};
  const a=s.analysis||{status:'not_run'},result=a.result,ready=!!result,processing=busy||a.status==='running';
  const stageKeys=['needs','capabilities','proposal'];
  const stageHTML=stageKeys.map(key=>{const stage=result?.stages?.find(x=>x.key===key);return `<section class="review22-stage"><div class="review22-stage-heading"><h3>${R(key)}</h3><span class="pill">${R(stage?.status||'not_analysed')}</span></div>${stage?`<p>${E(stage.observation)}</p>${stage.evidence.length?`<button type="button" class="text-link" data-action="learning-review-evidence" data-evidence="${E(JSON.stringify(stage.evidence.map(x=>x.message_id)))}">${R('view')}</button>`:''}`:`<p class="caption">${R(a.status==='error'?'stages_error':'stages_not_started')}</p>`}</section>`;}).join('');
  const lists=result?.summary?`<p>${E(result.summary)}</p><p><strong>${R('actual_outcome')}:</strong> ${E(result.actual_outcome)}</p>${['strengths','gaps','next_attempt'].map(k=>`<h3>${k==='next_attempt'?L(result.recommendation?'training_priorities':'legacy_priorities'):R(k)}</h3>${result[k].length?`<ul>${result[k].map(x=>`<li>${E(x)}</li>`).join('')}</ul>`:`<p class="caption">${window.TrainerI18n.t(k==='gaps'?'review25.no_gaps':'review25.no_required_changes')}</p>`}`).join('')}`:(result?.sections||[]).map(x=>`<h3>${E(x.title)}</h3><p>${E(x.text)}</p>`).join('');
  const savedFindings=(s.report?.findings||[]).filter(f=>window.TrainerPresentation.publicNotes([f.detail]).length);
  const retained=savedFindings.length?`<h3>${R('saved_observations')}</h3><ul>${savedFindings.map(f=>`<li>${E(window.TrainerI18n.systemText(f.detail))}</li>`).join('')}</ul>`:'';
  const feedback=s.published_review;
  return `<div class="review22-page"><header class="card card-pad review22-heading"><p class="eyebrow">${E(h.company)}</p><h1>${E(h.title)}</h1><p>${E(h.customer)} · ${R('training_language')}: ${E(String(h.language||'').toUpperCase())}</p><p class="review22-objective"><strong>${R('objective')}:</strong> ${E(h.objective||R('objective_missing'))}</p>${h.fallback&&h.objective?`<p class="caption">${R('objective_fallback')}</p>`:''}${h.context_source==='legacy_fallback_not_original'?`<p class="caption">${t('legacy')}</p>`:''}</header><section class="review22-status notice ${s.review_status==='submitted'?'amber':'neutral'}" role="status"><strong>${R(feedback?'status_reviewed':'status_'+s.review_status)}</strong>${s.review_status==='not_submitted'&&!feedback?`<p class="caption gap-top">${R('keep_private')}</p>`:''}</section><section class="card card-pad" id="learning-analysis"><h2>${R('preliminary')}</h2><p class="caption">${R('notice')}</p><p role="status">${R(processing?'running':ready?(a.attempt_status==='error'?'previous_analysis':'ready'):a.status==='error'?'failed':'not_started')}</p>${!processing&&(a.status==='error'||a.attempt_status==='error')?`<p role="alert">${R(a.error==='ai_context_limit'?'context_error':a.attempt_status==='error'?'regeneration_error':'error')}</p>`:''}${lists}${companyClaimChecks(result)}${retained}<button type="button" class="btn small-btn" data-action="learning-analysis" ${processing?'disabled':''}>${R(ready?'regenerate':a.status==='error'?'retry':'analyze')}</button></section>${learningRecommendation(result)}<section class="card card-pad"><h2>${R('stages')}</h2>${ready?stageHTML:`<p>${R('not_analysed')}. ${R(a.status==='error'?'stages_error':'stages_not_started')}</p>`}</section><section class="card card-pad review22-actions"><div class="actions"><button type="button" class="btn" data-action="repeat" data-id="${E(s.scenario_id)}" data-mode="${E(s.mode)}" ${state.starting?'disabled':''}>${R('repeat')}</button>${s.review_status==='not_submitted'&&!feedback?`<button type="button" class="btn primary" data-action="submit-review" ${state.saving?'disabled':''}>${R(state.saving?'sending':'send')}</button>`:`<span class="pill green" role="status">${R(feedback?'status_reviewed':'status_submitted')}</span>`}<button type="button" class="btn" data-action="learning-review-viewer">${R('view_conversation')}</button></div></section><a class="text-link" href="#learner/practice">${R('choose_other')}</a>${feedback?`<section id="learning-published-review" class="card card-pad"><h2>${R('mentor_feedback')}</h2><p>${E(feedback.mentor_name)}</p><p class="review-note">${E(feedback.note)}</p>${feedback.observations?`<p>${E(feedback.observations)}</p>`:''}${feedback.assessment?`<h3>${R('mentor_stages')}</h3>${stageKeys.map(k=>`<p><strong>${R(k)}:</strong> ${window.TrainerI18n.t('review.rating.'+(feedback.assessment.stages?.[k]||'not_reviewed'))}</p>`).join('')}<p><strong>${R('actual_outcome')}:</strong> ${window.TrainerI18n.t(feedback.assessment.commercial_outcome?'review.outcome.'+feedback.assessment.commercial_outcome:'review.unset')}</p>`:''}</section>`:''}<a class="text-link" href="#learner/history/all">${R('my_conversations')}</a></div>`;
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
 // A32: the mentor page uses the existing draft and publication contracts.
 const M=k=>window.TrainerI18n.t('mentor32.'+k);
 function localizedGoal(value){
  if(value&&typeof value==='object')return value[locale()]||value.original||value.de||value.en||value.ru||Object.values(value)[0]||'';
  const text=String(value||''),parts=[...text.matchAll(/(?:^|\s)(DE|EN|RU):\s*/g)];
  if(!parts.length)return text;
  const entries=Object.fromEntries(parts.map((m,i)=>[m[1].toLowerCase(),text.slice(m.index+m[0].length,parts[i+1]?.index??text.length).trim()]));
  return entries[locale()]||entries.de||entries.en||entries.ru||'';
 }
 function mentorEvidence(items,s){
  const ids=s.review_message_ids||s.messages.map((_,i)=>String(i));
  return (items||[]).map(e=>{const i=ids.indexOf(e.message_id);return `<blockquote>${E(e.quote||'')}${i<0?'':`<button type="button" class="text-link" data-action="learning-message" data-index="${i}">${R('view')} · ${i+1}</button>`}</blockquote>`;}).join('');
 }
 const N=k=>window.TrainerI18n.t('mentorNav.'+k);
 const P=k=>window.TrainerI18n.t('mentor33.'+k),V=k=>window.TrainerI18n.t('dictation18.'+k);
 let mentorVoiceOwner=null,mentorVoiceUnsubscribe=null;
 const mentorViews=new Map();
 let mentorMessageHTML=null;
 function mentorView(s){
  if(!mentorViews.has(s.id))mentorViews.set(s.id,{tab:s.published_review||s.review_status==='reviewed'?'decision':'ai',scroll:{}});
  return mentorViews.get(s.id);
 }
 function rememberMentorDraft(){
  if(state.route.role!=='mentor'||!document.getElementById('review-form'))return;
  if(!state.learningDrafts?.[state.session.id]&&!state.noteDrafts[state.session.id]&&!state.assessmentDrafts?.[state.session.id])return;
  state.learningDrafts??={};state.learningDrafts[state.session.id]=draftValue();
 }
 function selectMentorTab(tab,focus=false){
  if(!['ai','evidence','decision'].includes(tab))return;
  const page=document.querySelector('.mentor32-page');if(!page)return;
  if(tab!=='decision')cancelMentorVoice();
  const view=mentorView(state.session);view.scroll[view.tab]=window.scrollY;
  view.tab=tab;
  page.querySelectorAll('[role="tab"]').forEach(button=>{
   const selected=button.dataset.mentorTab===tab;
   button.setAttribute('aria-selected',String(selected));button.tabIndex=selected?0:-1;
   if(selected&&focus)button.focus({preventScroll:true});
  });
  page.querySelectorAll('[role="tabpanel"]').forEach(panel=>{panel.hidden=panel.dataset.mentorPanel!==tab;});
  window.scrollTo({top:view.scroll[tab]||0,behavior:'instant'});
 }
 function mentorStageDocument(s){
  const stages=s.mentor_analysis?.result?.stages||[];
  return stages.length?stages.map(x=>`<article class="review22-stage"><h2>${R(x.key)}</h2><p class="caption">${R(x.status)}</p><p>${E(x.observation)}</p>${mentorEvidence(x.evidence,s)}</article>`).join(''):
   `<p>${M('no_stage_analysis')}</p>${(s.report?.stages||[]).map(x=>`<p><strong>${E(window.TrainerI18n.systemText(x.label))}:</strong> ${E(window.TrainerI18n.t('review.rating.'+(x.rating||'not_reviewed')))}</p>`).join('')}`;
 }
 function mentorAIDocument(s){
  const r=s.mentor_analysis?.result;if(!r)return `<p>${R('not_started')}</p>`;
  const labels={summary:M('summary'),actual_outcome:R('actual_outcome'),strengths:R('strengths'),gaps:R('gaps'),next_attempt:R('next_attempt')};
  const sections=r.sections||Object.keys(labels).filter(k=>r[k]).map(k=>({title:k,text:Array.isArray(r[k])?r[k].join('\n'):r[k]}));
  return `<p class="caption">${M('private_ai')}</p>${s.mentor_analysis.attempt_status==='error'?`<p class="notice amber">${R('previous_analysis')}</p>`:''}
   ${sections.map(x=>`<h2>${E(labels[x.title]||x.title)}</h2><p class="review-note">${E(x.text)}</p>${(x.messages||[]).map(i=>`<button type="button" class="text-link" data-doc-message="${Number(i)}">${R('view')} · ${Number(i)+1}</button>`).join('')}`).join('')}
   ${r.recommendation?`<h2>${L('title')}</h2><p><strong>${L(r.recommendation.action)}</strong></p><p>${E(r.recommendation.explanation)}</p><ul>${(r.recommendation.priorities||[]).map(x=>`<li>${E(x)}</li>`).join('')}</ul>${mentorEvidence(r.recommendation.evidence,s)}<p class="caption">${L('advisory')}</p>`:''}
   ${(r.claim_checks||[]).length?`<h2>${L('conditions')}</h2>${r.claim_checks.map(c=>`<article><h3>${E(c.statement)}</h3><p>${L('verdict_'+c.verdict)}</p><p>${E(c.observation)}</p>${mentorEvidence(c.evidence,s)}${(c.material_evidence||[]).map(x=>`<blockquote>${E(x.quote||L('source_missing'))}</blockquote>`).join('')}</article>`).join('')}`:''}
   <h2>${R('stages')}</h2>${mentorStageDocument(s)}`;
 }
 function mentorAI(s){
  const a=s.mentor_analysis||{status:'not_run'},r=a.result,running=busy||a.status==='running',initial=a.status==='not_run';
  const summary=r?.summary||r?.sections?.find(x=>x.title==='summary')?.text||'';
  return `<section id="learning-analysis" class="card card-pad" aria-busy="${!!running}"><h2>${M('ai')}</h2>
   <p role="status" aria-live="polite">${running?M('running'):R(r?(a.attempt_status==='error'?'previous_analysis':'ready'):a.status==='error'?'failed':'not_started')}</p>
   ${a.status==='error'||a.attempt_status==='error'?`<p role="alert">${R(r?'regeneration_error':'error')}</p>`:''}
   ${summary?`<p class="mentor32-summary">${E(summary)}</p>`:''}
   ${r?`<button type="button" class="btn" data-action="learning-mentor-document" data-document="ai">${N('open_ai')}</button>`:
    initial?`<p class="caption">${M('manual_ai')}</p><button type="button" class="btn" data-action="learning-analysis" ${running?'disabled':''}>${t('analyze')}</button>`:`<p class="caption">${running?'':P('retry_here')}</p>`}
   ${a.status!=='not_run'?`<details class="mentor33-reanalysis"><summary>${P('reanalysis')}</summary><p>${M('paid_warning')}</p><button type="button" class="btn small-btn" data-action="learning-analysis" ${running?'disabled':''}>${t('rerun')}</button></details>`:''}</section>`;
 }
 function mentorReport(s,{reviewControls,messageHTML}){
  mentorMessageHTML=messageHTML;
  const ctx=s.learning_context||{},r=s.published_review,d=state.learningDrafts?.[s.id]||s.decision_draft||r||{},report=s.report||{},view=mentorView(s);
  const disabled=s.review_status==='not_submitted'||state.saving||state.draftSaving;
  const reviewed=!!r||s.review_status==='reviewed';
  const tab=(key,title)=>`<button type="button" role="tab" id="mentor-tab-${key}" aria-controls="mentor-panel-${key}" aria-selected="${view.tab===key}" tabindex="${view.tab===key?0:-1}" data-mentor-tab="${key}">${title}</button>`;
  const panel=(key,content)=>`<section role="tabpanel" id="mentor-panel-${key}" aria-labelledby="mentor-tab-${key}" data-mentor-panel="${key}" ${view.tab===key?'':'hidden'}>${content}</section>`;
  const evidence=`<section class="card card-pad"><h2>${M('evidence')}</h2><div class="mentor32-documents">
   <button type="button" class="btn" data-action="learning-mentor-document" data-document="transcript">${N('open_transcript')} · ${s.messages.length}</button>
   <button type="button" class="btn" data-action="learning-mentor-document" data-document="stages">${N('open_stages')}</button>
   <button type="button" class="btn" data-action="learning-mentor-document" data-document="snapshot">${P('open_conditions')}</button></div></section>
   <section class="card card-pad mentor32-history"><h3>${t('employee_history')} · ${E(s.employee_name)}</h3><p class="caption">${M('attempts_notice')}</p><ul>${history.filter(x=>x.id!==s.id).map(x=>`<li><a href="#mentor/review/${E(x.id)}">${E(x.title)} · ${E(x.created_at.slice(0,16))}</a><span>${N(x.review_status==='reviewed'?'reviewed':'awaiting')}</span></li>`).join('')||`<li>${t('none')}</li>`}</ul></section>`;
  const decision=reviewed?publishedMentorResult(s):`<section id="mentor32-decision" class="card card-pad"><h2>${M('decision')}</h2>
   ${s.review_status==='not_submitted'?`<p>${t('history_readonly')}</p>`:''}
   <form id="review-form"><fieldset ${disabled?'disabled':''}><label for="learning-goal">${M('goal_outcome')}</label><select id="learning-goal">${options(['not_reviewed','achieved','partly','not_achieved'],d.goal||'not_reviewed')}</select>
   ${s.mode==='simple_actor'?reviewControls(s,report):''}
   <label for="review-note">${M('feedback')}</label><textarea id="review-note" class="review-textarea" rows="4" maxlength="6000" required>${E(state.noteDrafts[s.id]??d.note??s.review_note??'')}</textarea>
   ${mentorVoiceControls(s)}
   <div class="actions gap-top"><button type="button" class="btn" data-action="learning-save-draft">${state.draftSaving?M('saving'):M('save_draft')}</button><button type="submit" class="btn primary">${state.saving?M('saving'):M('publish')}</button></div>
   <p id="learning-draft-status" role="status" aria-live="polite">${state.draftSavedFor===s.id||d.saved_at&&(!r||d.saved_at>r.published_at)?M('draft_saved'):''}</p></fieldset></form></section>
   `;
  return `<div class="mentor32-page"><a class="back-link" href="#mentor/reviews">← ${window.TrainerI18n.t('dashboard.text_408')}</a>
   <header class="card card-pad mentor32-heading"><p class="eyebrow">${E(s.employee_name)} · ${E(s.customer_name)}</p><h1>${E(s.title)}</h1><p class="mentor32-objective"><strong>${t('goal')}:</strong> ${E(localizedGoal(ctx.guidance?.goal)||R('objective_missing'))}</p><p class="caption">${R('training_language')}: ${E(String(s.training_language||'').toUpperCase())} · ${E(s.created_at?.slice(0,16).replace('T',' '))}</p><span class="mentor32-status ${reviewed?'reviewed':'awaiting'}"><span aria-hidden="true">${reviewed?'✓':'◷'}</span> ${N(reviewed?'reviewed':'awaiting')}</span>${ctx.source==='legacy_fallback_not_original'?`<p class="caption">${t('legacy')}</p>`:''}</header>
   <div class="mentor32-tabs" role="tablist" aria-label="${M('workflow')}">${tab('ai',M('ai'))}${tab('evidence',N('evidence_tab'))}${tab('decision',M('decision'))}</div>
   ${panel('ai',mentorAI(s))}${panel('evidence',evidence)}${panel('decision',decision)}
   <div class="mentor33-secondary"><button type="button" class="btn small-btn" data-action="learning-certificate">${P('certificates')}</button></div></div>`;
 }
 function publishedMentorResult(s){
  const r=s.published_review||{},when=r.published_at||s.reviewed_at||'',date=new Date(when),timestamp=Number.isNaN(date.getTime())?when:date.toLocaleString(locale()),a=r.assessment||s.report?.assessment||{},rating=k=>window.TrainerI18n.t('review.rating.'+(a.stages?.[k]||'not_reviewed'));
  return `<section id="learning-published-review" class="card card-pad mentor33-published"><h2>${P('published')}</h2><p class="caption">${E(r.mentor_name||window.TrainerI18n.t('dashboard.text_033'))} · <time datetime="${E(when)}">${E(timestamp)}</time></p>
   <dl><dt>${M('goal_outcome')}</dt><dd>${t(r.goal||'not_reviewed')}</dd>${['needs','capabilities','proposal'].map(k=>`<dt>${R(k)}</dt><dd>${rating(k)}</dd>`).join('')}
   <dt>${window.TrainerI18n.t('review.commercial')}</dt><dd>${window.TrainerI18n.t(a.commercial_outcome?'review.outcome.'+a.commercial_outcome:'review.unset')}</dd>
   <dt>${window.TrainerI18n.t('review.company_fit')}</dt><dd>${window.TrainerI18n.t('review.fit.'+(a.company_fit||'not_checked'))}</dd></dl>
   <h3>${M('feedback')}</h3><p class="review-note">${E(r.note||s.review_note||'')}</p></section>`;
 }
 function mentorVoiceControls(s){
  const language=mentorView(s).voiceLanguage||locale();
  return `<div class="mentor33-voice"><button type="button" class="btn small-btn" data-action="learning-voice-start">${V('start')}</button><button type="button" class="btn small-btn" data-action="learning-voice-stop" hidden>${V('stop')}</button><button type="button" class="btn small-btn" data-action="learning-voice-cancel" hidden>${V('cancel')}</button>
   <label for="mentor-feedback-language">${P('dictation_language')}</label><select id="mentor-feedback-language">${['de','en','ru'].map(l=>`<option value="${l}" ${language===l?'selected':''}>${l.toUpperCase()}</option>`).join('')}</select>
   <span id="mentor-voice-timer" class="voice-timer" role="timer" aria-live="off" hidden></span><span id="mentor-voice-status" role="status" aria-live="polite"></span></div>`;
 }
 function mentorVoiceBusy(){return mentorVoiceOwner!==null&&!!window.TrainerVoice?.busy();}
 function cancelMentorVoice(){if(mentorVoiceOwner===null)return;mentorVoiceOwner=null;window.TrainerVoice.cancel();}
 function syncMentorVoice(v){
  const form=document.getElementById('review-form');if(!form)return;
  const active=mentorVoiceOwner===state.session?.id,phase=active?v.phase:'idle',working=['asking','recording','transcribing'].includes(phase);
  for(const action of ['start','stop','cancel']){
   const button=form.querySelector(`[data-action="learning-voice-${action}"]`);if(!button)continue;
   button.hidden=action==='start'?working:action==='stop'?phase!=='recording':!working;
   button.disabled=action==='start'&&(state.saving||state.draftSaving);
  }
  const status=document.getElementById('mentor-voice-status');if(status){status.textContent=active?v.status:'';status.setAttribute('role',phase==='error'?'alert':'status');}
  const timer=document.getElementById('mentor-voice-timer');if(timer){timer.hidden=phase!=='recording';timer.textContent=`${String(Math.floor(v.elapsed/60)).padStart(2,'0')}:${String(v.elapsed%60).padStart(2,'0')} / 01:00`;}
  const language=document.getElementById('mentor-feedback-language');if(language)language.disabled=working||state.saving||state.draftSaving;
  form.querySelectorAll('[data-action="learning-save-draft"],[type="submit"]').forEach(b=>{b.disabled=!!(working||state.saving||state.draftSaving);});
 }
 function mentorAfterRender(){
  mentorVoiceUnsubscribe?.();mentorVoiceUnsubscribe=null;
  if(state.route.role!=='mentor'||state.route.view!=='review'||!document.getElementById('review-form')){cancelMentorVoice();return;}
  mentorVoiceUnsubscribe=window.TrainerVoice.subscribe(syncMentorVoice);
 }
 async function startMentorVoice(){
  const s=state.session,field=document.getElementById('review-note');
  if(!field||s.published_review||s.review_status==='reviewed'||state.saving||state.draftSaving)return;
  if(window.TrainerVoice.busy())return;
  mentorVoiceOwner=s.id;
  await window.TrainerVoice.start({language:document.getElementById('mentor-feedback-language').value,status:()=>{},error:text=>toast(text,true),text:text=>{
   if(mentorVoiceOwner!==s.id||state.session?.id!==s.id||state.session.published_review||state.session.review_status==='reviewed')return;
   const field=document.getElementById('review-note');if(!field)return;
   const combined=(field.value?field.value+'\n':'')+text;
   if(combined.length>6000){toast(P('voice_too_long'),true);return;}
   field.value=combined;field.dispatchEvent(new Event('input',{bubbles:true}));field.focus({preventScroll:true});
  }});
 }
 function documentExportURL(s,kind,format){
  const root=kind==='ai'?'/api/mentor/learning/reviews/'+encodeURIComponent(s.id)+'/analysis-export.':'/api/sessions/'+encodeURIComponent(s.id)+'/export.';
  return root+format+'?language='+encodeURIComponent(locale());
 }
 async function downloadMentorDocument(s,kind,format){
  if(!['ai','transcript'].includes(kind)||!['pdf','txt','json'].includes(format)||kind==='ai'&&format==='json')return;
  const response=await fetch(documentExportURL(s,kind,format),{credentials:'same-origin'});
  if(!response.ok)throw new Error(R('export_error'));
  const url=URL.createObjectURL(await response.blob()),link=document.createElement('a');link.href=url;link.download=(kind==='ai'?'mentor-review':'consultation')+'.'+format;
  document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),10000);
 }
 function openMentorDocument(s,kind){
  if(!['ai','transcript','stages','snapshot'].includes(kind)||document.querySelector('.mentor32-viewer[open]'))return;
  cancelMentorVoice();rememberMentorDraft();
  const oldFocus=document.activeElement,scroll=window.scrollY,dialog=document.createElement('dialog'),positions={};
  const previousOverflow=document.body.style.overflow;let current=kind,closed=false;
  const titles={ai:N('open_ai'),transcript:R('view_conversation'),stages:R('stages'),snapshot:R('saved_reference')};
  dialog.className='mentor32-viewer';dialog.setAttribute('aria-label',titles[kind]);
  dialog.innerHTML=`<header><h2></h2><div class="actions"></div><button type="button" class="btn" data-document-close>${R('close')}</button></header><div class="mentor32-viewer-body" tabindex="0"></div>`;
  const body=dialog.querySelector('.mentor32-viewer-body'),title=dialog.querySelector('h2'),actions=dialog.querySelector('header .actions');
  function show(next,index){
   positions[current]=body.scrollTop;current=next;title.textContent=titles[next];dialog.setAttribute('aria-label',titles[next]);
   actions.innerHTML=(['ai','transcript'].includes(next)?['pdf','txt',...(next==='transcript'?['json']:[])].map(f=>`<button type="button" class="btn small-btn" data-document-export="${f}">${f.toUpperCase()}</button>`).join(''):'')+
    (next==='transcript'?`<button type="button" class="btn small-btn" data-document-kind="snapshot">${R('saved_reference')}</button>`:next==='snapshot'?`<button type="button" class="btn small-btn" data-document-kind="transcript">${R('view_conversation')}</button>`:'');
   body.innerHTML=next==='ai'?mentorAIDocument(s):next==='stages'?mentorStageDocument(s):next==='snapshot'?materialPanel(s.learning_context?.materials,true):`<div class="transcript">${s.messages.map(m=>mentorMessageHTML(m,s,true)).join('')}</div>`;
   if(next==='snapshot')body.querySelectorAll('details').forEach(d=>{d.open=true;});
   body.scrollTop=positions[next]||0;
   if(Number.isInteger(index)){
    const el=body.querySelector(`[data-message-index="${index}"]`);if(el){el.tabIndex=-1;el.scrollIntoView({block:'center',behavior:'instant'});el.focus({preventScroll:true});}
   }
  }
  dialog.addEventListener('click',async e=>{
   const b=e.target.closest('button');if(!b)return;
   if(b.hasAttribute('data-document-close'))dialog.close();
   if(b.dataset.documentKind)show(b.dataset.documentKind);
   const message=b.dataset.docMessage??(b.dataset.action==='learning-message'?b.dataset.index:undefined);
   if(message!==undefined)show('transcript',Number(message));
   if(b.dataset.documentExport){b.disabled=true;try{await downloadMentorDocument(s,current,b.dataset.documentExport);}catch(error){toast(error.message,true);}finally{b.disabled=false;}}
  });
  const leave=()=>dialog.close();
  function done(){
   if(closed)return;closed=true;cancelMentorVoice();window.removeEventListener('hashchange',leave);dialog.remove();document.body.style.overflow=previousOverflow;
   if(state.session?.id===s.id&&state.route.view==='review'){
    window.scrollTo({top:scroll,behavior:'instant'});
    const focus=oldFocus?.isConnected?oldFocus:document.querySelector(`[data-document="${kind}"]`);focus?.focus({preventScroll:true});
   }
  }
  dialog.addEventListener('close',done,{once:true});window.addEventListener('hashchange',leave);
  document.body.append(dialog);document.body.style.overflow='hidden';dialog.showModal();show(kind);dialog.querySelector('[data-document-close]').focus();
 }
 function materialPanel(m,snapshot=false){
  const ref=reference.snapshot(m,snapshot?state.session?.company:null);if(ref)return ref;
  return `<details class="card card-pad report-section ${snapshot?'reference-snapshot':''}"><summary>${t(snapshot?'saved_materials':'materials')}${snapshot?`<small>${t('saved_materials_hint')}</small>`:''}</summary>${m?`<p class="caption">${window.TrainerI18n.t('company17.original_language')}: ${E(m.original_language?.toUpperCase()||'?')} · ${window.TrainerI18n.t('company17.missing_translation')}</p><label>${t('search')}<input type="search" id="learning-product-search"></label><div id="learning-products">${m.products.map(p=>`<div class="learning-product learning-search-item"><strong>${E(p.id)} · ${E(p.name)} · ${E(p.price_eur)} €</strong><p>${E(p.category)} · ${E(p.features)}</p><p>${E(p.price_includes)} · ${E(p.availability)} · ${E(p.promotion)} · ${E(p.valid_until)}</p></div>`).join('')}</div><div class="learning-markdown">${m.markdown.split(/\n\n+/).map(x=>`<p class="learning-search-item">${E(x)}</p>`).join('')}</div>`:`<p>${t('no_materials')}</p>`}</details>`;
 }
 function importer(){return reference.importer();}
 function guidanceEditor(){if(state.route.id==='new')return `<p>${t('save_scenario_first')}</p>`;return `<section class="card card-pad report-section"><h2>${t('guidance')}</h2>${['goal','conditions','outcomes','review_notes'].map(k=>field('learning-guide-'+k,k,guidance?.[k]||'')).join('')}<button class="btn" data-action="learning-save-guidance">${t('save')}</button></section>`;}
 function draftValue(){
  const s=state.session,previous=state.learningDrafts?.[s.id]||s.decision_draft||s.published_review||{},value=id=>document.getElementById(id)?.value;
  const assessment=s.mode==='simple_actor'&&document.getElementById('review-needs')?{stages:Object.fromEntries(['needs','capabilities','proposal'].map(k=>[k,value('review-'+k)])),commercial_outcome:value('review-commercial')||null,company_fit:value('review-fit')}:previous.assessment||{};
  return {note:value('review-note')??state.noteDrafts[s.id]??previous.note??s.review_note??'',assessment,goal:value('learning-goal')??previous.goal??'not_reviewed',observations:value('learning-observations')??previous.observations??s.published_review?.observations??''};
 }
 async function saveDraft(){const s=state.session,d=draftValue();state.learningDrafts??={};state.learningDrafts[s.id]=d;await api('/api/mentor/learning/reviews/'+s.id+'/draft',{method:'PUT',body:d});return d;}
 function certificateDialog(replacement=null){
  cancelMentorVoice();cert=null;const previous=replacement?results.certificates.find(x=>x.id===replacement):null;const s=state.session,dialog=document.getElementById('confirm-dialog');
  dialog.innerHTML=`<h2>${t('issue_certificate')}</h2><p>${E(s.employee_name)}</p><form id="learning-certificate-form"><label>${t('print_name')}<input id="learning-cert-name" value="${E(previous?.print_name||s.employee_name)}" maxlength="120" required></label><label>${t('topic')}<input id="learning-cert-topic" value="${E(previous?.topic||'')}" maxlength="240" required></label><fieldset><legend>${t('basis')}</legend>${history.filter(x=>x.status==='finished').map(x=>`<label><input type="checkbox" name="learning-basis" value="${E(x.id)}" ${x.id===s.id?'checked disabled':''}>${E(x.title)} · ${E(x.created_at.slice(0,16))}</label>`).join('')}</fieldset>${field('learning-cert-comment','comment')}<button class="btn" type="submit">${t('preview')}</button></form><div id="learning-cert-preview"></div><button class="btn" id="learning-cert-close">${t('close')}</button>`;
  if(!dialog.open)dialog.showModal();document.getElementById('learning-cert-close').onclick=()=>dialog.close();
  dialog.onclick=async e=>{const b=e.target.closest('[data-action]');if(!b||!['learning-revoke','learning-replace'].includes(b.dataset.action))return;try{await handle(b.dataset.action,b);if(b.dataset.action==='learning-revoke')certificateDialog();}catch(error){toast(error.message,true);}};
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
  if(action==='learning-voice-start'){await startMentorVoice();return true;}
  if(action==='learning-voice-stop'){window.TrainerVoice.stop();return true;}
  if(action==='learning-voice-cancel'){cancelMentorVoice();return true;}
  if(action==='learning-review-viewer'){openReviewViewer(s);return true;}
  if(action==='learning-review-evidence'){openReviewViewer(s,JSON.parse(target.dataset.evidence));return true;}
  if(action==='learning-mentor-document'){openMentorDocument(s,target.dataset.document);return true;}
  if(action==='learning-analysis'){if(busy)return true;if(state.route.role==='mentor'){if(s.mentor_analysis?.status&&s.mentor_analysis.status!=='not_run'&&!window.confirm(M('paid_warning')))return true;state.learningDrafts??={};state.learningDrafts[s.id]=draftValue();}busy=true;render();try{const audience=state.route.role==='mentor'?'mentor':'learner';const a=audience==='mentor'?s.mentor_analysis:s.analysis;const r=await api('/api/learning/sessions/'+s.id+'/analysis',{method:'POST',body:{audience,restart:a?.status!=='not_run'}});if(audience==='mentor')s.mentor_analysis=r.analysis;else s.analysis=r.analysis;}catch(_){toast(R('error'),true);}finally{busy=false;render();}}
  if(action==='learning-message'){document.querySelector('.ui-reader[open]>header button')?.click();const d=document.getElementById('report-transcript');d.open=true;const el=d.querySelector(`[data-message-index="${Number(target.dataset.index)}"]`);el?.scrollIntoView({behavior:'smooth',block:'center'});el?.classList.add('learning-highlight');}
  if(action==='learning-save-draft'){if(mentorVoiceBusy()||s.published_review||s.review_status==='reviewed'||state.saving||state.draftSaving)return true;const pending=saveDraft();state.draftSaving=true;render();try{await pending;state.draftSavedFor=s.id;}finally{state.draftSaving=false;render();}}
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
 document.addEventListener('click',e=>{const tab=e.target.closest('[data-mentor-tab]');if(tab)selectMentorTab(tab.dataset.mentorTab);});
 document.addEventListener('keydown',e=>{
  const tab=e.target.closest('[data-mentor-tab]');if(!tab||!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;
  e.preventDefault();const keys=['ai','evidence','decision'],i=keys.indexOf(tab.dataset.mentorTab);
  selectMentorTab(keys[e.key==='Home'?0:e.key==='End'?2:(i+(e.key==='ArrowRight'?1:2))%3],true);
 });
 document.addEventListener('change',async e=>{
  if(e.target.id==='mentor-feedback-language'&&state.session)mentorView(state.session).voiceLanguage=e.target.value;
  if(e.target.id==='learning-theme'){
   const control=e.target;control.disabled=true;window.TrainerUI.closePopover(control,true);
   try{await setTheme(control.value);control.value=theme();}finally{control.disabled=false;}
  }
  if(['learning-md-file','learning-csv-file'].includes(e.target.id)&&e.target.files[0]){const text=await e.target.files[0].text();document.getElementById(e.target.id==='learning-md-file'?'learning-markdown':'learning-csv').value=text;}
 });
 document.addEventListener('input',e=>{
  if(e.target.id==='learning-product-search'){const q=e.target.value.toLowerCase();document.querySelectorAll('.learning-search-item').forEach(x=>x.hidden=!x.textContent.toLowerCase().includes(q));}
  if((['learning-observations','learning-goal','review-note'].includes(e.target.id)||e.target.id.startsWith('review-'))&&state.session){state.learningDrafts??={};state.learningDrafts[state.session.id]=draftValue();state.draftSavedFor=null;const status=document.getElementById('learning-draft-status');if(status)status.textContent=M('draft_changed');}
 });
 return {load,mentorAfterRender,cancelMentorVoice,mentorVoiceBusy,startMentorVoice,mentorReport,localizedGoal,selectMentorTab,documentExportURL,downloadMentorDocument,employeeReport,referencePage:reference.page,referenceData:reference.snapshotData,materialPanel,importer,guidanceEditor,handle,saveDraft,buttons,theme,setTheme,notification,certificates,certificateCount,isNew,markRead};
};
