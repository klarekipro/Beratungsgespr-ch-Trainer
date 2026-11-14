const {test}=require('node:test');
const assert=require('node:assert/strict');
const {readFileSync}=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const root=path.resolve(__dirname,'../..');

test('comparison retains imported IDs, unknown prices, repeated labels and escaped free text',()=>{
 const handlers={},pane={innerHTML:'',scrollTop:0,setAttribute(){}},app={};
 const document={addEventListener:(name,fn)=>handlers[name]=fn,querySelector:s=>s==='#kc-app'?app:s==='#kc-pane'?pane:null,querySelectorAll:()=>[]};
 const snapshot={name:'Fixture',products:[
  {id:'item_first',article:'',name:'First',category:'Same',price_eur:null,features:'Note: A; Note: B; first free; <script>free</script>'},
  {id:'item_second',name:'Second',category:'Same',price_eur:12,features:'Note: C'}
 ],services:[],terms:[],documents:[]};
 const window={TrainerI18n:{locale:'de',t:k=>k==='company17.unknown'?'UNKNOWN':k},addEventListener(){}};
 vm.runInNewContext(readFileSync(path.join(root,'frontend/conversation.js'),'utf8'),{window,document,Intl,Map,Set});
 const escape=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const screen=window.createConversationScreen({state:{status:{limits:{max_turns:30}}},esc:escape,icon:()=>'',draftFor:()=>({text:''}),learning:{referenceData:()=>snapshot},date:()=>'',time:()=>'',languageName:x=>x,modeLabel:()=>''});
 const html=screen.page({id:'fixture',phase:'needs',messages:[],turn_count:0,company:{},training_language:'de'});
 assert.match(html,/kc-app/);
 for(const id of ['item_first','item_second'])handlers.change({target:{dataset:{pick:id},checked:true}});
 handlers.click({target:{closest:()=>({dataset:{kc:'compare'}})}});
 assert.match(pane.innerHTML,/UNKNOWN/);
 assert.doesNotMatch(pane.innerHTML,/>0,00\s*€/);
 assert.match(pane.innerHTML,/>A<\/td>/);
 assert.match(pane.innerHTML,/>B<\/td>/);
 assert.match(pane.innerHTML,/first free/);
 assert.match(pane.innerHTML,/&lt;script&gt;free&lt;\/script&gt;/);
 assert.doesNotMatch(pane.innerHTML,/<script>/);
 assert.doesNotMatch(pane.innerHTML,/item_first|item_second/);
 snapshot.services=[{id:'repair',title:'Repair',description:'Description is not a price',price_eur:null,conditions:'Quote first'}];
 handlers.click({target:{closest:()=>({dataset:{kcTab:'services'},getAttribute:()=>null})}});
 assert.match(pane.innerHTML,/kc-p-price">UNKNOWN<\/span>/);
 assert.doesNotMatch(pane.innerHTML,/kc-p-price">Description/);
});

test('real voice adapter exposes pending/recording/transcription and discards cancelled results',async()=>{
 let releaseMedia,releaseResponse,received='',calls=[];
 const track={stop(){}};
 class Recorder{
  static isTypeSupported(){return true;}
  constructor(){this.state='inactive';}
  start(){this.state='recording';}
  stop(){this.state='inactive';this.ondataavailable({data:new Blob(['fixture'])});this.onstop();}
 }
 const window={MediaRecorder:Recorder,TRAINER_AUTH:{csrf:'fixture'},TrainerI18n:{t:k=>k},addEventListener(){}};
 const context={window,MediaRecorder:Recorder,Blob,AbortController,console,navigator:{mediaDevices:{getUserMedia:()=>new Promise(r=>releaseMedia=r)}},setTimeout:()=>1,clearTimeout(){},setInterval:()=>1,clearInterval(){},fetch:(url,options)=>{calls.push({url,options});return new Promise(r=>releaseResponse=r);}};
 vm.runInNewContext(readFileSync(path.join(root,'frontend/voice.js'),'utf8'),context);
 const voice=window.TrainerVoice;
 const start=voice.start({language:'en',status(){},error:e=>assert.fail(e),text:s=>received+=s});
 assert.equal(voice.phase(),'asking');assert.equal(voice.busy(),true);
 releaseMedia({getTracks:()=>[track]});await start;
 assert.equal(voice.phase(),'recording');voice.stop();
 assert.equal(voice.phase(),'transcribing');
 assert.match(calls[0].url,/^\/api\/transcriptions\?.*language=en/);
 releaseResponse({ok:true,json:async()=>({text:'dictated text'})});
 await new Promise(r=>setImmediate(r));
 assert.equal(received,'dictated text');assert.equal(voice.busy(),false);
 const again=voice.start({language:'de',status(){},error:e=>assert.fail(e),text:s=>received+=s});
 releaseMedia({getTracks:()=>[track]});await again;voice.stop();voice.cancel();
 assert.equal(calls[1].options.signal.aborted,true);
 releaseResponse({ok:true,json:async()=>({text:'must not be inserted'})});
 await new Promise(r=>setImmediate(r));
 assert.equal(received,'dictated text');assert.equal(voice.busy(),false);assert.equal(voice.status(),'');
 assert.equal(calls.length,2);assert.ok(calls.every(c=>c.url.startsWith('/api/transcriptions?')));
});

test('dictation uses the existing stream for real-level analysis, cleans up and stops at 60 seconds only once',async()=>{
 let frame,timeout,delay,stopped=0,closed=0,requested=0,transcriptions=0;
 let response;
 class Recorder{static isTypeSupported(){return true;}constructor(){this.state='inactive';}start(){this.state='recording';}stop(){this.state='inactive';this.ondataavailable({data:new Blob(['fixture'])});this.onstop();}}
 const media={getTracks:()=>[{stop(){stopped++;}}]};
 class Audio{constructor(){this.state='running';}createMediaStreamSource(m){assert.equal(m,media);return {connect(){}};}createAnalyser(){return {fftSize:256,getByteTimeDomainData(a){a.fill(150);},disconnect(){}};}resume(){return Promise.resolve();}close(){closed++;return Promise.resolve();}}
 const window={MediaRecorder:Recorder,AudioContext:Audio,TRAINER_AUTH:{csrf:'fixture'},TrainerI18n:{t:k=>k},addEventListener(){}};
 vm.runInNewContext(readFileSync(path.join(root,'frontend/voice.js'),'utf8'),{window,MediaRecorder:Recorder,Blob,AbortController,Uint8Array,Date,console,navigator:{mediaDevices:{getUserMedia:async()=>{requested++;return media;}}},setTimeout:(fn,ms)=>{timeout=fn;delay=ms;return 1;},clearTimeout(){},setInterval:()=>1,clearInterval(){},requestAnimationFrame:fn=>{frame=fn;return 1;},cancelAnimationFrame(){},fetch:()=>{transcriptions++;return new Promise(r=>response=r);}});
 const v=window.TrainerVoice;let text='existing draft';
 await v.start({language:'de',status(){},error:e=>assert.fail(e),text:s=>text+='\n'+s});
 frame(100);assert.ok(v.snapshot().level>0);assert.equal(v.snapshot().meterAvailable,true);assert.equal(requested,1);assert.equal(delay,60000);
 timeout();timeout();assert.equal(transcriptions,1);assert.equal(stopped,1);assert.equal(closed,1);assert.equal(v.phase(),'transcribing');
 v.cancel();response({ok:true,json:async()=>({text:'late text'})});await new Promise(r=>setImmediate(r));assert.equal(text,'existing draft');assert.equal(v.busy(),false);
});
