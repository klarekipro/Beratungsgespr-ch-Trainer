'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const dict=Object.fromEntries(['de','en','ru'].map(l=>[l,JSON.parse(fs.readFileSync('frontend/locales/'+l+'.json'))]));let language='ru';const requests=[],events={};
const result={summary:'Saved learner summary.',actual_outcome:'No booking.',strengths:['FULL LEARNER DETAIL'],gaps:[],next_attempt:[],sections:[{title:'summary',text:'Saved learner summary.'},{title:'strengths',text:'FULL LEARNER DETAIL'}],stages:[{key:'needs',status:'evidence_found',observation:'LEARNER STAGE',evidence:[{message_id:'m1',quote:'Historical quote.'}]}]};
const s={id:'qa',company:{name:'Saved company',services:[]},title:'Saved attempt',training_language:'de',scenario_id:'qa-scenario',mode:'simple_actor',review_status:'reviewed',messages:[{role:'learner',text:'Historical quote.'}],review_message_ids:['m1'],report:{findings:[]},analysis:{status:'ready',attempt_status:'error',result},mentor_analysis:{result:{summary:'PRIVATE MENTOR SENTINEL',stages:[{observation:'PRIVATE MENTOR STAGE'}]}},published_review:{mentor_name:'Mentor',published_at:'2026-11-11T12:00:00+00:00',goal:'partly',note:'PUBLISHED HUMAN TEXT',assessment:{stages:{needs:'completed',capabilities:'partial',proposal:'partial'},commercial_outcome:'deferred_decision',company_fit:'uncertain'}}};
const state={session:s,route:{role:'learner',view:'session'},noteDrafts:{}};
const tabs=['analysis','evidence','feedback'].map(k=>({dataset:{learnerTab:k},setAttribute(){},focus(){}})),panels=tabs.map(t=>({dataset:{learnerPanel:t.dataset.learnerTab}})),page={querySelectorAll:sel=>sel==='[role="tab"]'?tabs:panels};
const context={window:{addEventListener(){},TRAINER_AUTH:{user:{id:'learner',get locale(){return language;}}},TrainerI18n:{t:k=>dict[language][k]||k,systemText:s=>s},TrainerPresentation:{publicNotes:s=>s},TrainerUI:{t:k=>k},createCompanyReference:()=>({snapshot:()=>'<p>Historical snapshot</p>'}),matchMedia:()=>({matches:false,addEventListener(){}}),scrollY:0,scrollTo:({top})=>context.window.scrollY=top,confirm:()=>false},document:{body:{dataset:{}},documentElement:{dataset:{},style:{}},addEventListener:(n,f)=>(events[n]??=[]).push(f),getElementById:()=>null,querySelector:sel=>sel==='.learner35-page'?page:null},localStorage:{getItem:()=>null},setTimeout};
vm.createContext(context);vm.runInContext(fs.readFileSync('frontend/learning.js','utf8'),context);
const learning=context.window.createLearning({state,api:async(...args)=>{requests.push(args);return {};},esc:s=>String(s??'').replaceAll('<','&lt;'),render(){},toast(){}});
(async()=>{
 const frozen=JSON.stringify(s);
 for(language of ['de','en','ru']){
  const html=learning.employeeReport(s);
  assert.equal((html.match(/role="tabpanel"/g)||[]).length,3);assert.ok(!html.includes('review22-actions'));assert.ok(!html.includes('PUBLISHED HUMAN TEXT'));assert.ok(!html.includes('FULL LEARNER DETAIL'));assert.ok(html.includes(dict[language]['review22.mentor_stages']));assert.ok(html.includes('data-document="feedback"'));
  const document=learning.mentorAIDocument(s,'learner');assert.ok(document.includes('FULL LEARNER DETAIL'));assert.ok(!document.includes('PRIVATE MENTOR'));assert.ok(learning.mentorStageDocument(s,'learner').includes('LEARNER STAGE'));
 }
 language='en';assert.ok(learning.learnerNextStep(s).includes(dict.en['learner35.legacy_step']));assert.ok(learning.learnerNextStep(s).includes('data-document="feedback"'));
 learning.selectLearnerTab('analysis');context.window.scrollY=250;learning.selectLearnerTab('evidence');learning.selectLearnerTab('analysis');assert.equal(context.window.scrollY,250);assert.equal(requests.length,0);assert.equal(JSON.stringify(s),frozen);
 assert.ok(learning.documentExportURL(s,'ai','pdf','learner').startsWith('/api/learning/sessions/qa/analysis-export.pdf'));assert.ok(learning.documentExportURL(s,'feedback','txt','learner').includes('/feedback-export.txt'));
 delete s.published_review;s.review_status='not_submitted';assert.ok(learning.learnerNextStep(s).includes('data-action="submit-review"'));
 s.review_status='submitted';assert.ok(!learning.learnerNextStep(s).includes('data-action="submit-review"'));assert.ok(learning.learnerNextStep(s).includes(dict.en['mentorNav.awaiting']));
 s.review_status='not_submitted';s.analysis.result.recommendation={action:'repeat',explanation:'Saved advice.',priorities:[]};assert.ok(learning.learnerNextStep(s).includes('data-action="repeat"'));s.analysis.result.recommendation.action='try_another_scenario';assert.ok(learning.learnerNextStep(s).includes('href="#learner/practice"'));
 await learning.handle('learning-analysis',{});assert.equal(requests.length,0);
 console.log('A35 learner: compact tabs, separate full documents, mentor grades before optional text, audience isolation, legacy/current next actions, no automatic API/paid/read calls — OK');
})().catch(e=>{console.error(e);process.exitCode=1;});
