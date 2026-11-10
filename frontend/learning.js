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
 const buttons=()=>`<details class="view-settings"><summary class="btn small-btn">${T('view')}</summary><div class="view-settings-panel"><label>${t('layout')} <select id="learning-layout">${['auto','side','stack'].map(v=>`<option value="${v}" ${current('layout')===v?'selected':''}>${v==='auto'?T('auto'):t(v)}</option>`).join('')}</select></label><label>${t('density')} <select id="learning-density">${options(['normal','compact'],current('density'))}</select></label></div></details>`;
 function applyView(){document.body.dataset.learningLayout=current('layout');document.body.dataset.learningDensity=current('density');}
 applyView();
 const unread=()=>results.reviews.filter(r=>read[r.session_id]!==r.published_at);
 const isNew=id=>unread().some(r=>r.session_id===id);
 const notification=()=>state.route.role==='learner'&&unread().length?`<a class="btn small-btn new-feedback" href="#learner/history/new">${T('new_reviews')} <strong>${unread().length}</strong></a>`:'';
 const certificates=()=>certificateList(window.TRAINER_AUTH.user.id)||`<section class="card card-pad">${t('none')}</section>`;
 const certificateCount=()=>results.certificates.filter(c=>c.employee_id===window.TRAINER_AUTH.user.id).length;
 async function markRead(){const r=state.session?.published_review;if(state.route.role==='learner'&&r&&isNew(r.session_id)){read=(await api('/api/ui/reviews/read',{method:'POST',body:{session_id:r.session_id,published_at:r.published_at}})).read;const badge=document.querySelector('.new-feedback');if(badge)badge.outerHTML=notification();}}
 async function load(){
  const [r,receipts,prefs]=await Promise.all([api('/api/learning/results'),api('/api/ui/reviews/read'),api('/api/ui/preferences')]);results=r;read=receipts.read;preferences=prefs.preferences;history=[];applyView();
  const s=state.session;
  if(state.route.view==='review'&&s?.employee_id)history=(await api('/api/mentor/employees/'+encodeURIComponent(s.employee_id)+'/sessions')).sessions;
  if(state.route.view==='company'){materials=(await api('/api/learning/materials')).materials;await reference.load();}
  if(state.route.view==='scenario'&&state.route.id!=='new')guidance=(await api('/api/mentor/learning/guidance/'+encodeURIComponent(state.route.id))).guidance;
 }
 const certificateList=uid=>results.certificates.filter(c=>!uid||c.employee_id===uid).map(c=>`<div class="learning-result"><strong>${E(c.topic)}</strong> · ${E(c.number)} · ${t(c.status)}<p>${E(c.print_name)} · ${E(c.mentor_name)} · ${E(c.issued_at?.slice(0,10))}</p><a class="btn" target="_blank" rel="noopener" href="/api/learning/certificates/${E(c.id)}.pdf?language=${locale()}">PDF · ${t('print')}</a>${state.route.role==='mentor'&&c.status==='issued'?`<button class="btn" data-action="learning-revoke" data-id="${E(c.id)}">${t('revoke')}</button><button class="btn" data-action="learning-replace" data-id="${E(c.id)}">${t('replace')}</button>`:''}</div>`).join('');
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
  return `<details class="card card-pad report-section"><summary>${t(snapshot?'saved_materials':'materials')} · ${E(m?.id||'—')}</summary>${m?`<p class="caption">${window.TrainerI18n.t('company17.original_language')}: ${E(m.original_language?.toUpperCase()||'?')} · ${window.TrainerI18n.t('company17.missing_translation')}</p><label>${t('search')}<input type="search" id="learning-product-search"></label><div id="learning-products">${m.products.map(p=>`<div class="learning-product learning-search-item"><strong>${E(p.id)} · ${E(p.name)} · ${E(p.price_eur)} €</strong><p>${E(p.category)} · ${E(p.features)}</p><p>${E(p.price_includes)} · ${E(p.availability)} · ${E(p.promotion)} · ${E(p.valid_until)}</p></div>`).join('')}</div><div class="learning-markdown">${m.markdown.split(/\n\n+/).map(x=>`<p class="learning-search-item">${E(x)}</p>`).join('')}</div>`:`<p>${t('no_materials')}</p>`}</details>`;
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
  if(action==='learning-analysis'){busy=true;render();try{const audience=state.route.role==='mentor'?'mentor':'learner';const a=audience==='mentor'?s.mentor_analysis:s.analysis;const r=await api('/api/learning/sessions/'+s.id+'/analysis',{method:'POST',body:{audience,restart:a?.status!=='not_run'}});if(audience==='mentor')s.mentor_analysis=r.analysis;else s.analysis=r.analysis;}finally{busy=false;render();}}
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
  if(['learning-layout','learning-density'].includes(e.target.id)){e.target.closest('.view-settings').open=false;const key=e.target.id==='learning-layout'?'layout':'density';const previous={layout:current('layout'),density:current('density')};const next={...previous,[key]:e.target.value};const controls=[...document.querySelectorAll('#learning-layout,#learning-density')];controls.forEach(el=>el.disabled=true);preferences=next;applyView();try{await api('/api/ui/preferences',{method:'PUT',body:next});localStorage.setItem(storageKey(key),next[key]);}catch(error){preferences=previous;applyView();toast(error.message,true);e.target.value=current(key);}finally{controls.forEach(el=>el.disabled=false);}}
  if(['learning-md-file','learning-csv-file'].includes(e.target.id)&&e.target.files[0]){const text=await e.target.files[0].text();document.getElementById(e.target.id==='learning-md-file'?'learning-markdown':'learning-csv').value=text;}
 });
 document.addEventListener('input',e=>{
  if(e.target.id==='learning-product-search'){const q=e.target.value.toLowerCase();document.querySelectorAll('.learning-search-item').forEach(x=>x.hidden=!x.textContent.toLowerCase().includes(q));}
  if(['learning-observations','learning-goal','review-note'].includes(e.target.id)&&state.session){state.learningDrafts??={};state.learningDrafts[state.session.id]=draftValue();}
 });
 return {load,report,referencePage:reference.page,referenceData:reference.snapshotData,materialPanel,importer,guidanceEditor,handle,saveDraft,buttons,notification,certificates,certificateCount,isNew,markRead};
};
