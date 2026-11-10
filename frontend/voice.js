"use strict";
window.TrainerVoice=(()=>{
 let lastStatus="";
 let recorder=null,stream=null,timer=null,chunks=[],cancelled=false,controller=null,callbacks=null,asking=false,sequence=0;
 const release=()=>{clearTimeout(timer);stream?.getTracks().forEach(t=>t.stop());stream=null;};
 async function start(options){
  if(recorder?.state==="recording"||asking||controller)return;
  const report=options.status,failure=options.error;options={...options,status:text=>{lastStatus=text;report(text);},error:text=>{lastStatus=text;failure(text);}};
  callbacks=options;cancelled=false;asking=true;const generation=++sequence;
  if(!navigator.mediaDevices?.getUserMedia||!window.MediaRecorder){asking=false;options.error(window.TrainerI18n.t("voice.text_603"));return;}
  const mime=["audio/webm;codecs=opus","audio/mp4","audio/webm"].find(x=>MediaRecorder.isTypeSupported(x));
  if(!mime){asking=false;options.error(window.TrainerI18n.t("voice.text_604"));return;}
  options.status(window.TrainerI18n.t("voice.text_605"));
  try {
   const media=await navigator.mediaDevices.getUserMedia({audio:true,video:false});
   if(generation!==sequence||cancelled){media.getTracks().forEach(t=>t.stop());return;}
   asking=false;stream=media;chunks=[];recorder=new MediaRecorder(stream,{mimeType:mime});
   recorder.ondataavailable=event=>{if(event.data.size)chunks.push(event.data);if(chunks.reduce((sum,b)=>sum+b.size,0)>4*1024*1024){cancel();options.error(window.TrainerI18n.t("voice.text_606"));}};
   recorder.onerror=()=>{cancel();options.error(window.TrainerI18n.t("voice.text_607"));};
   recorder.onstop=async()=>{
    if(cancelled||generation!==sequence){media.getTracks().forEach(t=>t.stop());return;}
    release();
    const blob=new Blob(chunks,{type:mime});chunks=[];recorder=null;
    if(!blob.size||blob.size>4*1024*1024){options.error(window.TrainerI18n.t("voice.text_608"));return;}
    const pending=new AbortController();controller=pending;options.status(window.TrainerI18n.t("voice.text_609"));
    try {
     const format=mime.includes("mp4")?"mp4":"webm";
     const r=await fetch(`/api/transcriptions?format=${format}&language=${encodeURIComponent(options.language)}`,{method:"POST",credentials:"same-origin",headers:{"Content-Type":mime,"X-CSRF-Token":window.TRAINER_AUTH.csrf},body:blob,signal:pending.signal});
     const data=await r.json();if(!r.ok)throw new Error(window.TrainerI18n.error(data.error)||window.TrainerI18n.t("voice.text_610"));
     if(!cancelled&&generation===sequence){options.text(data.text);options.status(window.TrainerI18n.t("voice.text_611"));}
    }catch(e){if(e.name!=="AbortError")options.error(e.message||window.TrainerI18n.t("voice.text_612"));}
    finally{if(controller===pending)controller=null;}
   };
   recorder.start(500);timer=setTimeout(stop,59000);options.status(window.TrainerI18n.t("voice.text_613"));
  }catch(e){if(generation!==sequence)return;asking=false;release();options.error(e.name==="NotAllowedError"?window.TrainerI18n.t("voice.text_614"):window.TrainerI18n.t("voice.text_615"));}
 }
 function stop(){if(recorder?.state==="recording")recorder.stop();}
 function cancel(){cancelled=true;sequence++;asking=false;controller?.abort();if(recorder?.state==="recording")recorder.stop();release();chunks=[];callbacks?.status("");}
 window.addEventListener("pagehide",cancel);
 return {start,stop,cancel,status:()=>lastStatus,phase:()=>asking?"asking":recorder?.state==="recording"?"recording":controller?"transcribing":"idle",busy:()=>asking||recorder?.state==="recording"||!!controller};
})();
