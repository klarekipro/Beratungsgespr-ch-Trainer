'use strict';
// Actual shared recorder + mentor adapter, with synthetic media/timers/network only.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const labels=JSON.parse(fs.readFileSync('frontend/locales/en.json','utf8'));
let authStatus=200,authUser={id:'mentor',role:'mentor_admin'},csrf='synthetic-csrf';
let clock=0,next=1,permission='granted',latePermission,fetchResolve,holdFetch=false,requests=[],micRequests=0,streams=[],recorders=[];
const timeouts=new Map(),intervals=new Map(),docEvents={},windowEvents={};
class Event {constructor(type){this.type=type;}}
class Recorder {
 static isTypeSupported(){return true;}
 constructor(stream){this.stream=stream;this.state='inactive';recorders.push(this);}
 start(){this.state='recording';}
 stop(){this.state='inactive';this.ondataavailable?.({data:new Blob(['synthetic-audio'])});this.onstop?.();}
}
function media(){const track={stops:0,stop(){this.stops++;}};const s={getTracks:()=>[track],track};streams.push(s);return s;}
const button=()=>({hidden:false,disabled:false}),buttons=Object.fromEntries(['start','stop','cancel'].map(k=>['learning-voice-'+k,button()])),save=button(),publish=button();
const field={id:'review-note',style:{},scrollHeight:68,scrollTop:0,getClientRects:()=>[{}],value:'Typed feedback.',focus(){},dispatchEvent(e){e.target=this;for(const fn of docEvents[e.type]||[])fn(e);}};
const status={textContent:'',setAttribute(k,v){this[k]=v;}},timer={hidden:true,textContent:''},language={value:'en'};
const form={querySelector:selector=>buttons[selector.match(/data-action="([^"]+)/)?.[1]],querySelectorAll:()=>[save,publish]};
const nodes={'review-note':field,'review-form':form,'mentor-feedback-language':language,'mentor-voice-status':status,'mentor-voice-timer':timer};
const state={route:{role:'mentor',view:'review'},session:{id:'qa',review_status:'submitted',mode:'simple_actor'},noteDrafts:{}};
const context={console,Blob,AbortController,Event,Uint8Array,Date:{now:()=>clock},setTimeout:(fn,ms)=>{const id=next++;timeouts.set(id,{fn,ms});return id;},clearTimeout:id=>timeouts.delete(id),setInterval:(fn,ms)=>{const id=next++;intervals.set(id,{fn,ms});return id;},clearInterval:id=>intervals.delete(id),
 navigator:{mediaDevices:{getUserMedia:async()=>{micRequests++;if(permission==='late')return new Promise(r=>{latePermission=r;});if(permission!=='granted')throw {name:permission};return media();}}},MediaRecorder:Recorder,
 fetch:async(url,opts)=>{if(url==='/api/auth/me')return {ok:authStatus===200,json:async()=>({user:authUser,csrf})};requests.push({url,opts});if(holdFetch)return new Promise(r=>{fetchResolve=r;});return {ok:true,json:async()=>({text:'Dictated continuation.'})};},
 window:{MediaRecorder:Recorder,TRAINER_AUTH:{user:{id:'mentor',role:'mentor_admin',locale:'en'},csrf:'synthetic-csrf'},TrainerI18n:{t:k=>labels[k]||k},TrainerUI:{t:k=>k},createCompanyReference:()=>({}),matchMedia:()=>({matches:false,addEventListener(){}}),addEventListener:(name,fn)=>(windowEvents[name]??=[]).push(fn),scrollY:0,scrollTo(){},confirm:()=>true},
 document:{body:{dataset:{},style:{}},documentElement:{dataset:{},style:{}},getElementById:id=>nodes[id]||null,querySelector:s=>s==='.mentor32-page'?{querySelectorAll:()=>[]}:null,addEventListener:(name,fn)=>(docEvents[name]??=[]).push(fn)},localStorage:{getItem:()=>null}};
vm.createContext(context);vm.runInContext(fs.readFileSync('frontend/voice.js','utf8'),context);vm.runInContext(fs.readFileSync('frontend/learning.js','utf8'),context);
const learning=context.window.createLearning({state,esc:String,api:()=>{throw Error('No automatic persistence');},render(){},toast(){}}),voice=context.window.TrainerVoice;
const flush=async()=>{for(let i=0;i<40;i++)await Promise.resolve();};
(async()=>{
 learning.mentorAfterRender();assert.equal(field.style.height,'68px');field.scrollHeight=500;for(const fn of windowEvents.resize||[])fn();assert.equal(field.style.height,'240px');field.scrollHeight=68;for(const fn of windowEvents.resize||[])fn();assert.equal(field.style.height,'68px');assert.equal(micRequests,0);assert.equal(requests.length,0);
 await learning.startMentorVoice();assert.equal(voice.phase(),'recording');assert.equal(buttons['learning-voice-stop'].hidden,false);assert.equal(publish.disabled,true);
 clock=5000;for(const {fn} of intervals.values())fn();assert.equal(timer.textContent,'00:05 / 01:00');
 field.value='Typed while recording.';voice.stop();await flush();assert.equal(field.value,'Typed while recording.\nDictated continuation.');assert.ok(streams.at(-1).track.stops>0);assert.equal(voice.phase(),'ready');assert.equal(publish.disabled,false);assert.equal(state.learningDrafts.qa.note,field.value);
 assert.equal(requests[0].url,'/api/transcriptions?format=webm&language=en');assert.equal(requests[0].opts.method,'POST');
 await learning.startMentorVoice();const limit=[...timeouts.values()].find(t=>t.ms===60000);assert.ok(limit);clock=65000;for(const {fn} of intervals.values())fn();assert.equal(timer.textContent,'01:00 / 01:00');limit.fn();await flush();assert.equal(recorders.at(-1).state,'inactive');assert.ok(streams.at(-1).track.stops>0);
 for(const name of ['NotAllowedError','NotFoundError','NotReadableError']){permission=name;const before=field.value;await learning.startMentorVoice();assert.equal(voice.phase(),'error');assert.equal(status.role,'alert');assert.equal(field.value,before);assert.ok(status.textContent);}
 permission='late';const asking=learning.startMentorVoice();assert.equal(voice.phase(),'asking');await flush();learning.cancelMentorVoice();const late=media();latePermission(late);await asking;assert.ok(late.track.stops>0);assert.equal(voice.phase(),'idle');
 permission='granted';await learning.startMentorVoice();const beforeLeave=requests.length;learning.selectMentorTab('ai');await flush();assert.ok(streams.at(-1).track.stops>0);assert.equal(requests.length,beforeLeave);
 holdFetch=true;await learning.startMentorVoice();voice.stop();await flush();assert.equal(voice.phase(),'transcribing');const before=field.value;learning.cancelMentorVoice();assert.equal(requests.at(-1).opts.signal.aborted,true);fetchResolve({ok:true,json:async()=>({text:'Late result must not insert.'})});await flush();assert.equal(field.value,before);
 holdFetch=false;await learning.startMentorVoice();for(const fn of windowEvents.pagehide||[])fn();await flush();assert.ok(streams.at(-1).track.stops>0);assert.equal(voice.phase(),'idle');
 field.value='X'.repeat(5990);await learning.startMentorVoice();voice.stop();await flush();assert.equal(field.value,'X'.repeat(5990));
 context.window.MediaRecorder=null;const beforeUnsupported=micRequests;await learning.startMentorVoice();assert.equal(voice.phase(),'error');assert.equal(micRequests,beforeUnsupported);context.window.MediaRecorder=Recorder;
 // Session loss and account switches must be blocked before any paid request.
 field.value='Unsaved mentor feedback';let count=requests.length,mics=micRequests;
 authStatus=401;await learning.startMentorVoice();assert.equal(micRequests,mics);assert.equal(requests.length,count);assert.equal(field.value,'Unsaved mentor feedback');
 authStatus=200;authUser={id:'employee',role:'employee'};await learning.startMentorVoice();assert.equal(micRequests,mics);assert.equal(requests.length,count);
 authUser={id:'mentor',role:'mentor_admin'};csrf='refreshed-csrf';await learning.startMentorVoice();authUser={id:'employee',role:'employee'};voice.stop();await flush();assert.equal(requests.length,count);assert.equal(field.value,'Unsaved mentor feedback');
 authUser={id:'mentor',role:'mentor_admin'};await learning.startMentorVoice();voice.stop();await flush();assert.equal(requests.at(-1).opts.headers['X-CSRF-Token'],'refreshed-csrf');assert.equal(requests.length,count+1);
 state.session.review_status='reviewed';const beforePublished=micRequests;await learning.startMentorVoice();assert.equal(micRequests,beforePublished);assert.ok(requests.every(r=>r.url.startsWith('/api/transcriptions?')));
 console.log('A33 voice: no auto start; real shared recorder start/stop/60s, permission errors, append latest typed text, late permission/result cancellation, navigation cleanup, published guard — OK');
})().catch(e=>{console.error(e);process.exitCode=1;});
