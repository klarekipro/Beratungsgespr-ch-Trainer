"use strict";
window.TrainerVoice=(()=>{
 let recorder=null,stream=null,timer=null,chunks=[],cancelled=false,controller=null,callbacks=null,asking=false,sequence=0;
 const release=()=>{clearTimeout(timer);stream?.getTracks().forEach(t=>t.stop());stream=null;};
 async function start(options){
  if(recorder?.state==="recording"||asking||controller)return;
  callbacks=options;cancelled=false;asking=true;const generation=++sequence;
  if(!navigator.mediaDevices?.getUserMedia||!window.MediaRecorder){asking=false;options.error("Диктовка в этом браузере недоступна. Используйте текстовый ввод.");return;}
  const mime=["audio/webm;codecs=opus","audio/mp4","audio/webm"].find(x=>MediaRecorder.isTypeSupported(x));
  if(!mime){asking=false;options.error("Нет поддерживаемого формата записи. Используйте актуальный Chrome или Safari.");return;}
  options.status("Запрашиваем доступ к микрофону…");
  try {
   const media=await navigator.mediaDevices.getUserMedia({audio:true,video:false});
   if(generation!==sequence||cancelled){media.getTracks().forEach(t=>t.stop());return;}
   asking=false;stream=media;chunks=[];recorder=new MediaRecorder(stream,{mimeType:mime});
   recorder.ondataavailable=event=>{if(event.data.size)chunks.push(event.data);if(chunks.reduce((sum,b)=>sum+b.size,0)>4*1024*1024){cancel();options.error("Запись превысила 4 МБ. Сделайте более короткую запись.");}};
   recorder.onerror=()=>{cancel();options.error("Ошибка записи. Набранный текст сохранён.");};
   recorder.onstop=async()=>{
    if(cancelled||generation!==sequence){media.getTracks().forEach(t=>t.stop());return;}
    release();
    const blob=new Blob(chunks,{type:mime});chunks=[];recorder=null;
    if(!blob.size||blob.size>4*1024*1024){options.error("Пустая или слишком большая запись.");return;}
    const pending=new AbortController();controller=pending;options.status("Распознаём речь…");
    try {
     const format=mime.includes("mp4")?"mp4":"webm";
     const r=await fetch(`/api/transcriptions?format=${format}&language=${encodeURIComponent(options.language)}`,{method:"POST",credentials:"same-origin",headers:{"Content-Type":mime,"X-CSRF-Token":window.TRAINER_AUTH.csrf},body:blob,signal:pending.signal});
     const data=await r.json();if(!r.ok)throw new Error(data.error?.message||"Не удалось распознать запись.");
     if(!cancelled&&generation===sequence){options.text(data.text);options.status("Текст добавлен. Проверьте его и нажмите «Отправить».");}
    }catch(e){if(e.name!=="AbortError")options.error(e.message||"Не удалось распознать запись. Текст сохранён.");}
    finally{if(controller===pending)controller=null;}
   };
   recorder.start(500);timer=setTimeout(stop,59000);options.status("Идёт запись · до 60 секунд. Нажмите «Остановить».");
  }catch(e){if(generation!==sequence)return;asking=false;release();options.error(e.name==="NotAllowedError"?"Доступ к микрофону запрещён. Разрешите его в настройках браузера или используйте текст.":"Микрофон недоступен. Набранный текст сохранён.");}
 }
 function stop(){if(recorder?.state==="recording")recorder.stop();}
 function cancel(){cancelled=true;sequence++;asking=false;controller?.abort();if(recorder?.state==="recording")recorder.stop();release();chunks=[];callbacks?.status("");}
 window.addEventListener("pagehide",cancel);
 return {start,stop,cancel,busy:()=>asking||recorder?.state==="recording"||!!controller};
})();
