"use strict";
/* One capture stream per attempt. Presentation subscribes without owning capture. */
window.TrainerVoice=(()=>{
 const t=k=>window.TrainerI18n.t('dictation18.'+k);
 let recorder=null,stream=null,limitTimer=null,tick=null,raf=null,context=null,analyser=null,controller=null,sequence=0;
 let state={phase:'idle',status:'',elapsed:0,level:0,meterAvailable:false,language:null},callbacks=null;
 const listeners=new Set(),busy=()=>['asking','recording','transcribing'].includes(state.phase);
 const snapshot=()=>({...state,remaining:Math.max(0,60-state.elapsed)});
 function emit(){for(const listener of listeners){try{listener(snapshot());}catch(e){console.error('Voice presentation update failed');}}}
 function status(phase,key){state.phase=phase;state.status=key?t(key):'';callbacks?.status(state.status);emit();}
 function release(){
  clearTimeout(limitTimer);clearInterval(tick);limitTimer=tick=null;
  if(raf!==null&&typeof cancelAnimationFrame==='function')cancelAnimationFrame(raf);raf=null;
  try{analyser?.disconnect();}catch(_){}analyser=null;
  const previous=context;context=null;if(previous)try{previous.close()?.catch(()=>{});}catch(_){}
  stream?.getTracks().forEach(track=>track.stop());stream=null;state.level=0;state.meterAvailable=false;
 }
 function fail(key,generation){if(generation!==sequence)return;release();recorder=null;controller=null;status('error',key);callbacks?.error(state.status);}
 function meter(media,generation){
  const Audio=window.AudioContext||window.webkitAudioContext;
  if(!Audio||typeof requestAnimationFrame!=='function')return;
  try{
   context=new Audio();const source=context.createMediaStreamSource(media);analyser=context.createAnalyser();analyser.fftSize=256;source.connect(analyser);
   // Deliberately no connection to destination: microphone is never played back.
   const samples=new Uint8Array(analyser.fftSize);let last=0;
   const read=now=>{if(generation!==sequence||state.phase!=='recording'||!analyser)return;
    if(now-last>=80){last=now;try{analyser.getByteTimeDomainData(samples);let sum=0;for(const n of samples)sum+=((n-128)/128)**2;
     const rms=Math.sqrt(sum/samples.length);state.level=Math.max(0,Math.min(1,(20*Math.log10(Math.max(rms,1e-6))+60)/60));state.meterAvailable=context?.state==='running';emit();
    }catch(_){state.level=0;state.meterAvailable=false;emit();}}
    raf=requestAnimationFrame(read);
   };
   context.resume()?.catch(()=>{});raf=requestAnimationFrame(read);
  }catch(_){try{context?.close()?.catch(()=>{});}catch(_){}context=analyser=null;state.meterAvailable=false;}
 }
 // Read-only preflight: never send audio under another tab's account or retry a paid POST.
 async function session(generation,identity){
  const r=await fetch('/api/auth/me',{credentials:'same-origin',cache:'no-store'});
  const data=await r.json();
  if(generation!==sequence)return false;
  if(!r.ok)throw new Error(t('session_required'));
  if(data.user?.id!==identity.id||data.user?.role!==identity.role)throw new Error(t('session_changed'));
  window.TRAINER_AUTH.csrf=data.csrf;
  return true;
 }
 async function start(options){
  if(busy())return;
  const generation=++sequence;callbacks=options;state={phase:'asking',status:'',elapsed:0,level:0,meterAvailable:false,language:options.language};
  status('asking','permission');
  if(!navigator.mediaDevices?.getUserMedia||!window.MediaRecorder){fail('unsupported',generation);return;}
  let mime;try{mime=['audio/webm;codecs=opus','audio/mp4','audio/webm'].find(x=>MediaRecorder.isTypeSupported(x));}catch(_){fail('unsupported',generation);return;}
  if(!mime){fail('format',generation);return;}
  const identity={id:window.TRAINER_AUTH.user.id,role:window.TRAINER_AUTH.user.role};
  try{if(!await session(generation,identity))return;}catch(e){if(generation===sequence){state.phase='error';state.status=e.message||t('transcription_error');options.error(state.status);emit();}return;}
  try{
   const media=await navigator.mediaDevices.getUserMedia({audio:true,video:false});
   if(generation!==sequence){media.getTracks().forEach(track=>track.stop());return;}
   stream=media;const parts=[];let size=0;const capture=new MediaRecorder(media,{mimeType:mime});recorder=capture;
   capture.ondataavailable=e=>{if(generation!==sequence)return;if(e.data.size){parts.push(e.data);size+=e.data.size;}if(size>4*1024*1024){cancel();status('error','size');options.error(state.status);}};
   capture.onerror=()=>{if(generation!==sequence)return;cancel();status('error','record_error');options.error(state.status);};
   capture.onstop=async()=>{
    if(generation!==sequence){media.getTracks().forEach(track=>track.stop());return;}
    release();recorder=null;status('transcribing','transcribing');
    const blob=new Blob(parts,{type:mime});if(!blob.size||blob.size>4*1024*1024){fail('empty',generation);return;}
    const pending=new AbortController();controller=pending;
    try{
     if(!await session(generation,identity))return;
     const format=mime.includes('mp4')?'mp4':'webm';
     const r=await fetch(`/api/transcriptions?format=${format}&language=${encodeURIComponent(state.language)}`,{method:'POST',credentials:'same-origin',headers:{'Content-Type':mime,'X-CSRF-Token':window.TRAINER_AUTH.csrf},body:blob,signal:pending.signal});
     const data=await r.json();if(generation!==sequence)return;
     if(!r.ok)throw new Error(['AUTH_REQUIRED','CSRF_FAILED'].includes(data.error?.code)?t('session_required'):window.TrainerI18n.error(data.error)||t('transcription_error'));
     if(typeof data.text!=='string'||!data.text.trim())throw new Error(t('empty_text'));
     if(!await session(generation,identity))return;
     controller=null;options.text(data.text);status('ready','ready');
    }catch(e){if(generation===sequence&&e.name!=='AbortError'){controller=null;state.phase='error';state.status=e.message||t('transcription_error');options.error(state.status);emit();}}
    finally{if(controller===pending)controller=null;}
   };
   capture.start(500);status('recording','recording');const began=Date.now();
   tick=setInterval(()=>{if(generation!==sequence||state.phase!=='recording')return;state.elapsed=Math.min(60,Math.floor((Date.now()-began)/1000));emit();},250);
   meter(media,generation);limitTimer=setTimeout(stop,60000);
  }catch(e){if(generation!==sequence)return;fail(e.name==='NotAllowedError'?'denied':e.name==='NotFoundError'?'no_device':e.name==='NotReadableError'?'device_busy':'record_error',generation);}
 }
 function stop(){if(state.phase!=='recording'||recorder?.state!=='recording')return;status('transcribing','transcribing');try{recorder.stop();release();}catch(_){const gen=sequence;fail('record_error',gen);}}
 function cancel(){sequence++;controller?.abort();controller=null;const old=recorder;recorder=null;release();if(old?.state==='recording')try{old.stop();}catch(_){}state={phase:'idle',status:'',elapsed:0,level:0,meterAvailable:false,language:null};callbacks?.status('');emit();}
 window.addEventListener('pagehide',cancel);
 return {start,stop,cancel,busy,phase:()=>state.phase,status:()=>state.status,snapshot,subscribe:fn=>{listeners.add(fn);fn(snapshot());return ()=>listeners.delete(fn);}};
})();
