"use strict";
window.createLearning = ({state,api,esc,render,toast,icon=()=>''}) => {
 const t=k=>window.TrainerI18n.t('learning.'+k), E=esc;
 let results={reviews:[],certificates:[]},history=[],materials=null,guidance=null,preview=null,busy=false;
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
 const certificateList=uid=>results.certificates.filter(c=>!uid||c.employee_id===uid).map(c=>`<div class="learning-result"><strong>${E(c.topic)}</strong> · ${E(c.number)} · ${t(c.status)}<p>${E(c.print_name)} · ${E(c.issuer_full_name||c.mentor_name)} · ${E(c.issued_at?.slice(0,10))}</p><a class="btn" target="_blank" rel="noopener" href="/api/learning/certificates/${E(c.id)}.pdf?language=${E(c.language||locale())}">PDF · ${t('print')}</a>${state.route.role==='mentor'&&c.status==='issued'?`<button class="btn" data-action="learning-revoke" data-id="${E(c.id)}">${t('revoke')}</button><button class="btn" data-action="learning-replace" data-id="${E(c.id)}">${t('replace')}</button>`:''}</div>`).join('');
 const R=k=>window.TrainerI18n.t('review22.'+k);
 const L=k=>window.TrainerI18n.t('review23.'+k);
 const S=k=>window.TrainerI18n.t('learner35.'+k);
 const learnerViews=new Map();
 function learnerView(s){
  if(!learnerViews.has(s.id))learnerViews.set(s.id,{tab:s.published_review?'feedback':'analysis',scroll:{}});
  return learnerViews.get(s.id);
 }
 function selectLearnerTab(tab,focus=false){
  if(!['analysis','evidence','feedback'].includes(tab))return;
  const page=document.querySelector('.learner35-page');if(!page)return;
  const view=learnerView(state.session);view.scroll[view.tab]=window.scrollY;view.tab=tab;
  page.querySelectorAll('[role="tab"]').forEach(b=>{const selected=b.dataset.learnerTab===tab;b.setAttribute('aria-selected',String(selected));b.tabIndex=selected?0:-1;if(selected&&focus)b.focus({preventScroll:true});});
  page.querySelectorAll('[role="tabpanel"]').forEach(panel=>{panel.hidden=panel.dataset.learnerPanel!==tab;});
  if(tab==='decision')fitMentorFeedback();
  window.scrollTo({top:view.scroll[tab]||0,behavior:'instant'});
 }
 function learnerNextStep(s){
  const advice=s.analysis?.result?.recommendation,feedback=s.published_review;
  let action;
  if(feedback)action=`<button type="button" class="btn primary" data-action="learning-learner-document" data-document="feedback">${S('open_feedback')}</button>`;
  else if(s.review_status==='submitted')action=`<span class="pill amber">${N('awaiting')}</span>`;
  else action=`<button type="button" class="btn primary" data-action="submit-review" ${state.saving?'disabled':''}>${R(state.saving?'sending':'send')}</button>`;
  const practice=advice?.action==='repeat'&&!feedback?`<button type="button" class="btn" data-action="repeat" data-id="${E(s.scenario_id)}" data-mode="${E(s.mode)}">${R('repeat')}</button>`:
   advice?.action==='try_another_scenario'&&!feedback?`<a class="btn" href="#learner/practice">${R('choose_other')}</a>`:'';
  return `<section class="card card-pad learner35-next"><h2>${L('title')}</h2>
   ${advice?`<p><strong>${L(advice.action)}</strong></p><p class="learner35-preview">${E(advice.explanation)}</p><p class="caption">${L('advisory')}</p>`:`<p class="caption">${S(s.analysis?.result?'legacy_step':'no_ai_step')}</p>`}
   <div class="actions">${action}${practice}</div></section>`;
 }
 function employeeReport(s,{messageHTML}={}){
  documentMessageHTML=messageHTML||((m,session)=>`<article class="review22-message" data-message-index="${session.messages.indexOf(m)}"><strong>${t(m.role==='learner'?'employee':'customer')}</strong><p>${E(m.text)}</p></article>`);
  const h=s.review_heading||{company:s.company.name,title:s.title,customer:s.customer_name,objective:'',language:s.training_language};
  const a=s.analysis||{status:'not_run'},ready=!!a.result,processing=busy||a.status==='running',feedback=s.published_review,view=learnerView(s);
  const summary=a.result?.summary||a.result?.sections?.find(x=>x.title==='summary')?.text||'';
  const tab=(key,label)=>`<button type="button" role="tab" id="learner35-tab-${key}" aria-controls="learner35-panel-${key}" aria-selected="${view.tab===key}" tabindex="${view.tab===key?0:-1}" data-learner-tab="${key}">${label}</button>`;
  const panel=(key,body)=>`<section role="tabpanel" id="learner35-panel-${key}" aria-labelledby="learner35-tab-${key}" data-learner-panel="${key}" ${view.tab===key?'':'hidden'}>${body}</section>`;
  const ai=`<section id="learning-analysis" class="card card-pad" aria-busy="${!!processing}"><h2>${R('preliminary')}</h2><p role="status">${R(processing?'running':ready?(a.attempt_status==='error'?'previous_analysis':'ready'):a.status==='error'?'failed':'not_started')}</p>
   ${summary?`<p class="learner35-preview">${E(summary)}</p>`:''}
   ${ready?`<button type="button" class="btn" data-action="learning-learner-document" data-document="ai">${S('open_ai')}</button><details class="learner35-more"><summary>${R('regenerate')}</summary><p class="caption">${M('paid_warning')}</p><button type="button" class="btn small-btn" data-action="learning-analysis" ${processing?'disabled':''}>${R('regenerate')}</button></details>`:
   `<p class="caption">${R('notice')}</p>${a.status==='error'?`<p role="alert">${R(a.error==='ai_context_limit'?'context_error':'error')}</p>`:''}<button type="button" class="btn" data-action="learning-analysis" ${processing?'disabled':''}>${R(a.status==='error'?'retry':'analyze')}</button>`}</section>${learnerNextStep(s)}`;
  const evidence=`<section class="card card-pad"><h2>${S('evidence_tab')}</h2><div class="mentor32-documents">
   <button type="button" class="btn" data-action="learning-learner-document" data-document="transcript">${N('open_transcript')} · ${s.messages.length}</button>
   <button type="button" class="btn" data-action="learning-learner-document" data-document="stages">${N('open_stages')}</button>
   <button type="button" class="btn" data-action="learning-learner-document" data-document="snapshot">${P('open_conditions')}</button></div></section>`;
  const mentor=feedback?`${publishedMentorResult(s,false,R('mentor_stages'))}<section class="card card-pad learner35-note-entry"><h2>${R('mentor_feedback')}</h2><button type="button" class="btn primary" data-action="learning-learner-document" data-document="feedback">${S('open_feedback')}</button></section>`:
   `<section class="card card-pad"><h2>${R('mentor_feedback')}</h2><p>${S(s.review_status==='submitted'?'feedback_waiting':'feedback_private')}</p>${s.review_status==='not_submitted'?`<button type="button" class="btn primary" data-action="submit-review" ${state.saving?'disabled':''}>${R(state.saving?'sending':'send')}</button>`:''}</section>`;
  return `<div class="learner35-page"><a class="back-link" href="#learner/history/all">← ${R('my_conversations')}</a><header class="card card-pad learner35-heading"><p class="eyebrow">${E(h.company)}</p><h1>${E(h.title)}</h1><p class="caption">${E(h.customer)} · ${R('training_language')}: ${E(String(h.language||'').toUpperCase())}</p><p><strong>${R('objective')}:</strong> ${E(h.objective||R('objective_missing'))}</p><span class="pill ${feedback?'green':s.review_status==='submitted'?'amber':''}">${feedback?N('reviewed'):s.review_status==='submitted'?N('awaiting'):R('status_not_submitted')}</span></header>
   <div class="mentor32-tabs" role="tablist" aria-label="${S('result_tabs')}">${tab('analysis',S('analysis_tab'))}${tab('evidence',S('evidence_tab'))}${tab('feedback',R('mentor_feedback'))}</div>
   ${panel('analysis',ai)}${panel('evidence',evidence)}${panel('feedback',mentor)}
   <div class="learner35-secondary"><button type="button" class="btn small-btn" data-action="repeat" data-id="${E(s.scenario_id)}" data-mode="${E(s.mode)}" ${state.starting?'disabled':''}>${R('repeat')}</button><a class="text-link" href="#learner/practice">${R('choose_other')}</a></div></div>`;
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
 let documentMessageHTML=null;
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
  if(tab==='decision')fitMentorFeedback();
  window.scrollTo({top:view.scroll[tab]||0,behavior:'instant'});
 }
 function mentorStageDocument(s,audience='mentor'){
  const stages=(audience==='learner'?s.analysis:s.mentor_analysis)?.result?.stages||[];
  return stages.length?stages.map(x=>`<article class="review22-stage"><h2>${R(x.key)}</h2><p class="caption">${R(x.status)}</p><p>${E(x.observation)}</p>${mentorEvidence(x.evidence,s)}</article>`).join(''):
   `<p>${audience==='learner'?R('stages_not_started'):M('no_stage_analysis')}</p>${(audience==='learner'?[]:s.report?.stages||[]).map(x=>`<p><strong>${E(window.TrainerI18n.systemText(x.label))}:</strong> ${E(window.TrainerI18n.t('review.rating.'+(x.rating||'not_reviewed')))}</p>`).join('')}`;
 }
 function mentorAIDocument(s,audience='mentor'){
  const analysis=audience==='learner'?s.analysis:s.mentor_analysis,r=analysis?.result;if(!r)return `<p>${R('not_started')}</p>`;
  const labels={summary:M('summary'),actual_outcome:R('actual_outcome'),strengths:R('strengths'),gaps:R('gaps'),next_attempt:R('next_attempt')};
  const sectionText=x=>x.text||(x.title==='gaps'?window.TrainerI18n.t('review25.no_gaps'):x.title==='next_attempt'?window.TrainerI18n.t('review25.no_required_changes'):'');
  const sections=r.sections||Object.keys(labels).filter(k=>r[k]).map(k=>({title:k,text:Array.isArray(r[k])?r[k].join('\n'):r[k]}));
  return `<p class="caption">${audience==='learner'?R('notice'):M('private_ai')}</p>${analysis.attempt_status==='error'?`<p class="notice amber">${R('previous_analysis')}</p>`:''}
   ${sections.map(x=>`<h2>${E(labels[x.title]||x.title)}</h2><p class="mentor32-document-text">${E(sectionText(x))}</p>${(x.messages||[]).map(i=>`<button type="button" class="text-link" data-doc-message="${Number(i)}">${R('view')} · ${Number(i)+1}</button>`).join('')}`).join('')}
   ${r.recommendation?`<h2>${L('title')}</h2><p><strong>${L(r.recommendation.action)}</strong></p><p>${E(r.recommendation.explanation)}</p><ul>${(r.recommendation.priorities||[]).map(x=>`<li>${E(x)}</li>`).join('')}</ul>${mentorEvidence(r.recommendation.evidence,s)}<p class="caption">${L('advisory')}</p>`:''}
   ${(r.claim_checks||[]).length?`<h2>${L('conditions')}</h2>${r.claim_checks.map(c=>`<article><h3>${E(c.statement)}</h3><p>${L('verdict_'+c.verdict)}</p><p>${E(c.observation)}</p>${mentorEvidence(c.evidence,s)}${(c.material_evidence||[]).map(x=>`<blockquote>${E(x.quote||L('source_missing'))}</blockquote>`).join('')}</article>`).join('')}`:''}
   <h2>${R('stages')}</h2>${mentorStageDocument(s,audience)}${audience==='learner'?learnerSavedFindings(s):''}`;
 }
 function learnerSavedFindings(s){
  const findings=(s.report?.findings||[]).filter(f=>window.TrainerPresentation.publicNotes([f.detail]).length);
  return findings.length?`<h2>${R('saved_observations')}</h2><ul>${findings.map(f=>`<li>${E(window.TrainerI18n.systemText(f.detail))}</li>`).join('')}</ul>`:'';
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
  documentMessageHTML=messageHTML;
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
   <label for="review-note">${M('feedback')}</label><div class="mentor37-field"><textarea id="review-note" class="review-textarea" rows="2" maxlength="6000" placeholder="${E(P('feedback_placeholder'))}" aria-describedby="mentor-voice-hint" required>${E(state.noteDrafts[s.id]??d.note??s.review_note??'')}</textarea>
   ${mentorVoiceControls(s)}</div>
   <p id="mentor-voice-hint" class="caption">${E(P('dictation_hint'))}</p><p id="mentor-voice-status" role="status" aria-live="polite"></p>
   <div class="actions gap-top"><button type="button" class="btn" data-action="learning-save-draft">${state.draftSaving?M('saving'):M('save_draft')}</button><button type="submit" class="btn primary">${state.saving?M('saving'):M('publish')}</button></div>
   <p id="learning-draft-status" role="status" aria-live="polite">${state.draftSavedFor===s.id||d.saved_at&&(!r||d.saved_at>r.published_at)?M('draft_saved'):''}</p></fieldset></form></section>
   `;
  return `<div class="mentor32-page"><a class="back-link" href="#mentor/reviews">← ${window.TrainerI18n.t('dashboard.text_408')}</a>
   <header class="card card-pad mentor32-heading"><p class="eyebrow">${E(s.employee_name)} · ${E(s.customer_name)}</p><h1>${E(s.title)}</h1><p class="mentor32-objective"><strong>${t('goal')}:</strong> ${E(localizedGoal(ctx.guidance?.goal)||R('objective_missing'))}</p><p class="caption">${R('training_language')}: ${E(String(s.training_language||'').toUpperCase())} · ${E(s.created_at?.slice(0,16).replace('T',' '))}</p><span class="mentor32-status ${reviewed?'reviewed':'awaiting'}"><span aria-hidden="true">${reviewed?'✓':'◷'}</span> ${N(reviewed?'reviewed':'awaiting')}</span>${ctx.source==='legacy_fallback_not_original'?`<p class="caption">${t('legacy')}</p>`:''}</header>
   <div class="mentor32-tabs" role="tablist" aria-label="${M('workflow')}">${tab('ai',M('ai'))}${tab('evidence',N('evidence_tab'))}${tab('decision',M('decision'))}</div>
   ${panel('ai',mentorAI(s))}${panel('evidence',evidence)}${panel('decision',decision)}
   <div class="mentor33-secondary"><button type="button" class="btn small-btn" data-action="learning-certificate">${P('certificates')}</button></div></div>`;
 }
 function publishedMentorResult(s,includeNote=true,title=P('published'),showObservations=false){
  const r=s.published_review||{},when=r.published_at||s.reviewed_at||'',date=new Date(when),timestamp=Number.isNaN(date.getTime())?when:date.toLocaleString(locale()),a=r.assessment||s.report?.assessment||{},rating=k=>window.TrainerI18n.t('review.rating.'+(a.stages?.[k]||'not_reviewed'));
  return `<section ${includeNote?'id="learning-published-review"':''} class="card card-pad mentor33-published"><h2>${title}</h2><p class="caption">${E(r.mentor_name||window.TrainerI18n.t('dashboard.text_033'))} · <time datetime="${E(when)}">${E(timestamp)}</time></p>
   <dl><dt>${M('goal_outcome')}</dt><dd>${t(r.goal||'not_reviewed')}</dd>${['needs','capabilities','proposal'].map(k=>`<dt>${R(k)}</dt><dd>${rating(k)}</dd>`).join('')}
   <dt>${window.TrainerI18n.t('review.commercial')}</dt><dd>${window.TrainerI18n.t(a.commercial_outcome?'review.outcome.'+a.commercial_outcome:'review.unset')}</dd>
   <dt>${window.TrainerI18n.t('review.company_fit')}</dt><dd>${window.TrainerI18n.t('review.fit.'+(a.company_fit||'not_checked'))}</dd></dl>
   ${includeNote?`<h3>${M('feedback')}</h3><p class="review-note" data-feedback-text>${E(r.note||s.review_note||'')}</p>${showObservations&&r.observations?`<p class="caption">${E(r.observations)}</p>`:''}`:''}</section>`;
 }
 function mentorVoiceControls(s){
  const language=mentorView(s).voiceLanguage||locale();
  return `<div class="mentor33-voice"><button type="button" class="btn voice-mic" data-action="learning-voice-start" title="${E(V('start'))}" aria-label="${E(V('start'))}">${icon('mic')}</button><button type="button" class="btn kc-btn--rec voice-stop" data-action="learning-voice-stop" hidden title="${E(V('stop'))}" aria-label="${E(V('stop'))}"><span aria-hidden="true">■</span></button><button type="button" class="btn voice-cancel" data-action="learning-voice-cancel" hidden title="${E(V('cancel'))}" aria-label="${E(V('cancel'))}"><span aria-hidden="true">×</span></button>
   <label class="sr-only" for="mentor-feedback-language">${P('dictation_language')}</label><select id="mentor-feedback-language">${['de','en','ru'].map(l=>`<option value="${l}" ${language===l?'selected':''}>${{de:'Deutsch',en:'English',ru:'Русский'}[l]}</option>`).join('')}</select>
   <span id="mentor-voice-meter" class="voice-meter" role="img" aria-label="${E(V('meter'))}" hidden>${'<i></i>'.repeat(7)}</span>
   <span id="mentor-voice-timer" class="voice-timer" role="timer" aria-live="off" hidden></span></div>`;
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
  const meter=document.getElementById('mentor-voice-meter');if(meter){meter.hidden=phase!=='recording'||!v.meterAvailable;meter.querySelectorAll('i').forEach((bar,i)=>{bar.style.height=(3+v.level*[10,18,24,29,24,18,10][i])+'px';});}
  const language=document.getElementById('mentor-feedback-language');if(language)language.disabled=working||state.saving||state.draftSaving;
  form.querySelectorAll('[data-action="learning-save-draft"],[type="submit"]').forEach(b=>{b.disabled=!!(working||state.saving||state.draftSaving);});
 }
 function fitMentorFeedback(){
  const field=document.getElementById('review-note');
  if(!field?.style||!field.getClientRects().length)return;
  const scroll=field.scrollTop;field.style.height='auto';
  field.style.height=Math.max(68,Math.min(240,field.scrollHeight))+'px';
  field.scrollTop=scroll;
 }
 window.addEventListener('resize',fitMentorFeedback);
 function mentorAfterRender(){
  mentorVoiceUnsubscribe?.();mentorVoiceUnsubscribe=null;
  if(state.route.role!=='mentor'||state.route.view!=='review'||!document.getElementById('review-form')){cancelMentorVoice();return;}
  fitMentorFeedback();mentorVoiceUnsubscribe=window.TrainerVoice.subscribe(syncMentorVoice);
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
 function documentExportURL(s,kind,format,audience='mentor'){
  const root=kind==='feedback'?'/api/learning/sessions/'+encodeURIComponent(s.id)+'/feedback-export.':kind==='ai'?(audience==='learner'?'/api/learning/sessions/':'/api/mentor/learning/reviews/')+encodeURIComponent(s.id)+'/analysis-export.':'/api/sessions/'+encodeURIComponent(s.id)+'/export.';
  return root+format+'?language='+encodeURIComponent(locale());
 }
 async function downloadMentorDocument(s,kind,format,audience='mentor'){
  if(!['ai','transcript','feedback'].includes(kind)||!['pdf','txt','json'].includes(format)||kind!=='transcript'&&format==='json'||kind==='feedback'&&audience!=='learner')return;
  const response=await fetch(documentExportURL(s,kind,format,audience),{credentials:'same-origin'});
  if(!response.ok)throw new Error(R('export_error'));
  const url=URL.createObjectURL(await response.blob()),link=document.createElement('a');link.href=url;link.download=(kind==='feedback'?'mentor-feedback':kind==='ai'?(audience==='learner'?'learner-analysis':'mentor-review'):'consultation')+'.'+format;
  document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),10000);
 }
 function openMentorDocument(s,kind,audience='mentor',initialIndex){
  if(!['ai','transcript','stages','snapshot','feedback'].includes(kind)||kind==='feedback'&&(audience!=='learner'||!s.published_review)||document.querySelector('.mentor32-viewer[open]'))return;
  cancelMentorVoice();rememberMentorDraft();
  const oldFocus=document.activeElement,scroll=window.scrollY,dialog=document.createElement('dialog'),positions={};
  const previousOverflow=document.body.style.overflow;let current=kind,closed=false,readObserver=null;
  const titles={ai:audience==='learner'?R('preliminary'):N('open_ai'),transcript:R('view_conversation'),stages:R('stages'),snapshot:R('saved_reference'),feedback:R('mentor_feedback')};
  dialog.className='mentor32-viewer'+(audience==='learner'?' learner35-viewer':'');dialog.setAttribute('aria-label',titles[kind]);
  dialog.innerHTML=`<header><h2></h2><div class="actions"></div><button type="button" class="btn" data-document-close>${R('close')}</button></header><div class="mentor32-viewer-body" tabindex="0"></div>`;
  const body=dialog.querySelector('.mentor32-viewer-body'),title=dialog.querySelector('h2'),actions=dialog.querySelector('header .actions');
  function show(next,index){
   readObserver?.disconnect();positions[current]=body.scrollTop;current=next;title.textContent=titles[next];dialog.setAttribute('aria-label',titles[next]);
   actions.innerHTML=(['ai','transcript','feedback'].includes(next)?['pdf','txt',...(next==='transcript'?['json']:[])].map(f=>`<button type="button" class="btn small-btn" data-document-export="${f}">${f.toUpperCase()}</button>`).join(''):'')+
    (next==='transcript'?`<button type="button" class="btn small-btn" data-document-kind="snapshot">${R('saved_reference')}</button>`:next==='snapshot'?`<button type="button" class="btn small-btn" data-document-kind="transcript">${R('view_conversation')}</button>`:'');
   body.innerHTML=next==='feedback'?publishedMentorResult(s,true,R('mentor_stages'),true):next==='ai'?mentorAIDocument(s,audience):next==='stages'?mentorStageDocument(s,audience):next==='snapshot'?materialPanel(s.learning_context?.materials,true):`<div class="transcript">${s.messages.map(m=>documentMessageHTML(m,s,true)).join('')}</div>`;
   if(next==='snapshot')body.querySelectorAll('details').forEach(d=>{d.open=true;});
   body.scrollTop=positions[next]||0;
   if(next==='feedback'&&audience==='learner'){
    const note=body.querySelector('[data-feedback-text]');
    if(note){readObserver=new IntersectionObserver(entries=>{if(state.session?.id===s.id&&entries.some(e=>e.isIntersecting)){markRead().catch(e=>toast(e.message,true));readObserver.disconnect();}},{root:body,threshold:0.01});readObserver.observe(note);}
   }
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
   if(b.dataset.documentExport){b.disabled=true;try{await downloadMentorDocument(s,current,b.dataset.documentExport,audience);}catch(error){toast(error.message,true);}finally{b.disabled=false;}}
  });
  const leave=()=>dialog.close();
  function done(){
   if(closed)return;closed=true;readObserver?.disconnect();cancelMentorVoice();window.removeEventListener('hashchange',leave);dialog.remove();document.body.style.overflow=previousOverflow;
   if(state.session?.id===s.id&&state.route.view===(audience==='learner'?'session':'review')){
    window.scrollTo({top:scroll,behavior:'instant'});
    const focus=oldFocus?.isConnected?oldFocus:document.querySelector(`[data-document="${kind}"]`);focus?.focus({preventScroll:true});
   }
  }
  dialog.addEventListener('close',done,{once:true});window.addEventListener('hashchange',leave);
  document.body.append(dialog);document.body.style.overflow='hidden';dialog.showModal();show(kind,initialIndex);dialog.querySelector('[data-document-close]').focus();
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
  cancelMentorVoice();let cert=null;const previous=replacement?results.certificates.find(x=>x.id===replacement):null;const s=state.session,dialog=document.getElementById('confirm-dialog');
  dialog.classList.add('certificate39-dialog');dialog.addEventListener('close',()=>dialog.classList.remove('certificate39-dialog'),{once:true});
  dialog.innerHTML=`<div id="certificate39-intro"><h2>${t('issue_certificate')}</h2><p>${E(s.employee_name)}</p><p class="caption">${P('certificate_scope')}</p></div><form id="learning-certificate-form"><label>${P('certificate_full_name')}<input id="learning-cert-name" value="${E(previous?.recipient_full_name||'')}" maxlength="120" autocomplete="off" required></label><p class="caption">${P('certificate_name_hint')}</p><label>${P('certificate_issuer_name')}<input id="learning-cert-issuer" value="${E(previous?.mentor_id===window.TRAINER_AUTH.user.id?previous.issuer_full_name||'':'')}" maxlength="120" autocomplete="off" required></label><p class="caption">${P('certificate_issuer_hint')}</p><label>${t('topic')}<input id="learning-cert-topic" value="${E(previous?.topic||({de:'Strukturierte Kundenberatung',en:'Structured customer consultation',ru:'Структурированное консультирование клиентов'}[previous?.language||'de']))}" maxlength="240" required></label><fieldset><legend>${t('basis')}</legend>${history.filter(x=>x.status==='finished').map(x=>`<label><input type="checkbox" name="learning-basis" value="${E(x.id)}" ${x.id===s.id?'checked disabled':''}>${E(x.title)} · ${E(x.created_at.slice(0,16))}</label>`).join('')}</fieldset>${field('learning-cert-comment','comment')}<p class="caption">${P('certificate_comment_hint')}</p><label for="learning-cert-language">${P('certificate_language')}</label><select id="learning-cert-language">${['de','en','ru'].map(l=>`<option value="${l}" ${(previous?.language||'de')===l?'selected':''}>${{de:'Deutsch',en:'English',ru:'Русский'}[l]}</option>`).join('')}</select><button class="btn" type="submit">${t('preview')}</button></form><div id="learning-cert-preview"></div><button class="btn" id="learning-cert-close">${t('close')}</button>`;
  if(!dialog.open)dialog.showModal();document.getElementById('learning-cert-close').onclick=()=>dialog.close();
  dialog.onclick=async e=>{const b=e.target.closest('[data-action]');if(!b||!['learning-revoke','learning-replace'].includes(b.dataset.action))return;try{await handle(b.dataset.action,b);if(b.dataset.action==='learning-revoke')certificateDialog();}catch(error){toast(error.message,true);}};
  const form=document.getElementById('learning-certificate-form'),previewNode=document.getElementById('learning-cert-preview');let previewing=false;
  const showPDF=record=>{
   form.hidden=true;document.getElementById('certificate39-intro').hidden=true;dialog.scrollTop=0;
   const url='/api/learning/certificates/'+encodeURIComponent(record.id)+'.pdf?language='+encodeURIComponent(record.language||locale());
   previewNode.innerHTML=`<h3>${t(record.status)}</h3><iframe class="certificate39-preview" title="${E(t('preview'))}" src="${url}#view=Fit"></iframe><div class="actions"><a class="btn" target="_blank" rel="noopener" href="${url}">PDF · ${t('print')}</a></div>`;
  };
  const invalidate=()=>{if(cert){cert=null;previewNode.textContent=P('certificate_preview_stale');}};
  form.addEventListener('input',invalidate);form.addEventListener('change',invalidate);
  form.onsubmit=async e=>{e.preventDefault();if(previewing)return;previewing=true;
   const inputs=[...form.querySelectorAll('input,textarea,select,button')],disabled=inputs.map(x=>x.disabled);
   try{
    const body={session_id:s.id,print_name:document.getElementById('learning-cert-name').value,issuer_full_name:document.getElementById('learning-cert-issuer').value,topic:document.getElementById('learning-cert-topic').value,basis:[...document.querySelectorAll('[name=learning-basis]:checked')].map(x=>x.value),comment:document.getElementById('learning-cert-comment').value,language:document.getElementById('learning-cert-language').value,replaces:replacement};
    inputs.forEach(x=>x.disabled=true);cert=null;previewNode.textContent=t('saving');
    const r=await api('/api/mentor/learning/certificates/preview',{method:'POST',body});
    if(!dialog.open||!form.isConnected)return;cert=r.certificate;showPDF(cert);
    previewNode.insertAdjacentHTML('beforeend',`<p class="caption">${P('certificate_confirm')}</p>`);
    previewNode.querySelector('.actions').insertAdjacentHTML('beforeend',`<button type="button" id="learning-cert-edit" class="btn">${P('certificate_edit')}</button><button type="button" id="learning-cert-confirm" class="btn primary">${t('confirm_issue')}</button>`);
    document.getElementById('learning-cert-edit').onclick=()=>{cert=null;previewNode.innerHTML='';form.hidden=false;document.getElementById('certificate39-intro').hidden=false;document.getElementById('learning-cert-name').focus();};
    document.getElementById('learning-cert-confirm').onclick=async e=>{
     if(!cert)return;const button=e.currentTarget;button.disabled=true;
     try{const r=await api('/api/mentor/learning/certificates/'+cert.id+'/issue',{method:'POST',body:{confirm:true}});if(!dialog.open||!form.isConnected)return;cert=r.certificate;form.hidden=true;showPDF(cert);await load();}
     catch(error){button.disabled=false;toast(error.message,true);}
    };
   }catch(error){cert=null;previewNode.textContent=error.message;toast(error.message,true);}
   finally{inputs.forEach((x,i)=>x.disabled=disabled[i]);previewing=false;}
  };
 }
 async function handle(action,target){
  if(!action.startsWith('learning-'))return false;
  const s=state.session;
  if(action==='learning-voice-start'){await startMentorVoice();return true;}
  if(action==='learning-voice-stop'){window.TrainerVoice.stop();return true;}
  if(action==='learning-voice-cancel'){cancelMentorVoice();return true;}
  if(action==='learning-review-viewer'){openMentorDocument(s,'transcript','learner');return true;}
  if(action==='learning-review-evidence'){const ids=s.review_message_ids||[];openMentorDocument(s,'transcript','learner',ids.indexOf(JSON.parse(target.dataset.evidence)[0]));return true;}
  if(action==='learning-learner-document'){openMentorDocument(s,target.dataset.document,'learner');return true;}
  if(action==='learning-mentor-document'){openMentorDocument(s,target.dataset.document);return true;}
  if(action==='learning-analysis'){if(busy)return true;const previous=state.route.role==='mentor'?s.mentor_analysis:s.analysis;if(previous?.status&&previous.status!=='not_run'&&!window.confirm(M('paid_warning')))return true;if(state.route.role==='mentor'){state.learningDrafts??={};state.learningDrafts[s.id]=draftValue();}busy=true;render();try{const audience=state.route.role==='mentor'?'mentor':'learner';const a=audience==='mentor'?s.mentor_analysis:s.analysis;const r=await api('/api/learning/sessions/'+s.id+'/analysis',{method:'POST',body:{audience,restart:a?.status!=='not_run'}});if(audience==='mentor')s.mentor_analysis=r.analysis;else s.analysis=r.analysis;}catch(_){toast(R('error'),true);}finally{busy=false;render();}}
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
 document.addEventListener('click',e=>{const tab=e.target.closest('[data-mentor-tab]');if(tab)selectMentorTab(tab.dataset.mentorTab);const learner=e.target.closest('[data-learner-tab]');if(learner)selectLearnerTab(learner.dataset.learnerTab);});
 document.addEventListener('keydown',e=>{
  const learner=e.target.closest('[data-learner-tab]');if(learner&&['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){e.preventDefault();const keys=['analysis','evidence','feedback'],i=keys.indexOf(learner.dataset.learnerTab);selectLearnerTab(keys[e.key==='Home'?0:e.key==='End'?2:(i+(e.key==='ArrowRight'?1:2))%3],true);return;}
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
  if(e.target.id==='review-note')fitMentorFeedback();
  if(e.target.id==='learning-product-search'){const q=e.target.value.toLowerCase();document.querySelectorAll('.learning-search-item').forEach(x=>x.hidden=!x.textContent.toLowerCase().includes(q));}
  if((['learning-observations','learning-goal','review-note'].includes(e.target.id)||e.target.id.startsWith('review-'))&&state.session){state.learningDrafts??={};state.learningDrafts[state.session.id]=draftValue();state.draftSavedFor=null;const status=document.getElementById('learning-draft-status');if(status)status.textContent=M('draft_changed');}
 });
 return {load,mentorAfterRender,cancelMentorVoice,mentorVoiceBusy,startMentorVoice,mentorReport,learnerNextStep,mentorAIDocument,mentorStageDocument,localizedGoal,selectLearnerTab,selectMentorTab,documentExportURL,downloadMentorDocument,employeeReport,referencePage:reference.page,referenceData:reference.snapshotData,materialPanel,importer,guidanceEditor,handle,saveDraft,buttons,theme,setTheme,notification,certificates,certificateCount,isNew,markRead};
};
