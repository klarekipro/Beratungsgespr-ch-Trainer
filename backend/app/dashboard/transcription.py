"""Bounded, authenticated dictation. Transient audio is erased before API return."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import httpx
from .auth import fail
MAX_BYTES=4*1024*1024
MAX_SECONDS=60

def probe_path():
    return shutil.which('ffprobe') or next((str(p) for p in [Path('/opt/homebrew/bin/ffprobe'),Path('/usr/local/bin/ffprobe')] if p.exists()),None)

def check_audio(data,kind):
    if kind not in {'webm','mp4','wav'}:fail('AUDIO_FORMAT','Поддерживаются WebM, MP4 и WAV.',415)
    good=(kind=='webm' and data[:4]==b'\x1aE\xdf\xa3' or kind=='mp4' and data[4:8]==b'ftyp' or kind=='wav' and data[:4]==b'RIFF' and data[8:12]==b'WAVE')
    if not good:fail('AUDIO_FORMAT','Запись не соответствует заявленному формату.',415)
    if not probe_path():fail('AUDIO_PROBE_MISSING','Для проверки длительности нужен ffprobe. Используйте текстовый ввод.',503)
    # mkstemp gives mode 0600; source has no filename supplied by the browser.
    fd,path=tempfile.mkstemp(suffix='.'+kind,prefix='trainer-dictation-')
    try:
        with os.fdopen(fd,'wb') as f:f.write(data)
        result=subprocess.run([probe_path(),'-v','error','-protocol_whitelist','file,pipe','-format_whitelist','matroska,webm,mov,wav','-select_streams','a:0','-read_intervals','%+61','-show_entries','packet=pts_time,duration_time','-of','csv=p=0',path],capture_output=True,timeout=8)
        if result.returncode:fail('AUDIO_INVALID','Не удалось прочитать запись.',422)
        durations=[]
        for line in result.stdout.decode(errors='replace').splitlines():
            try:
                parts=line.split(',');durations.append(float(parts[0])+float(parts[1]))
            except (ValueError,IndexError):continue
        if not durations or max(durations)<=0:fail('AUDIO_EMPTY','В записи не найдена звуковая дорожка.',422)
        if max(durations)>MAX_SECONDS+0.2:fail('AUDIO_TOO_LONG','Запись ограничена 60 секундами.',413)
        return max(durations)
    except subprocess.TimeoutExpired:fail('AUDIO_INVALID','Проверка записи заняла слишком много времени.',422)
    finally:Path(path).unlink(missing_ok=True)

async def transcribe(data,kind,language,key,model,on_request=None,on_error=None):
    if language not in {'ru','de'}:fail('AUDIO_LANGUAGE','Выберите русский или немецкий язык.',422)
    if not data or len(data)>MAX_BYTES:fail('AUDIO_SIZE','Максимальный размер записи — 4 МБ.',413)
    import asyncio
    duration=await asyncio.to_thread(check_audio,data,kind)
    if not key:fail('AI_NOT_CONFIGURED','OpenAI не настроен.',409)
    fields={'model':model}
    if model=='gpt-transcribe':fields['languages[]']=language
    else:fields.update(language=language,response_format='json')
    try:
        async with httpx.AsyncClient(timeout=45,follow_redirects=False,trust_env=False) as client:
            if on_request:on_request()
            r=await client.post('https://api.openai.com/v1/audio/transcriptions',headers={'Authorization':'Bearer '+key},data=fields,files={'file':('dictation.'+kind,data,{'webm':'audio/webm','mp4':'audio/mp4','wav':'audio/wav'}[kind])})
    except httpx.RequestError as exc:
        if on_error:on_error('transport',type(exc).__name__)
        fail('TRANSCRIPTION_UNAVAILABLE','Не удалось распознать запись. Набранный текст сохранён; попробуйте ещё раз.',502)
    if r.status_code!=200:
        if on_error:on_error('http',r.status_code)
        fail('TRANSCRIPTION_UNAVAILABLE','API транскрибации недоступен. Текст сохранён; проверьте доступ к модели.',502)
    try:text=r.json()['text']
    except (ValueError,KeyError,TypeError):fail('TRANSCRIPTION_INVALID','Сервис не вернул текст.',502)
    if not isinstance(text,str) or not text.strip() or len(text)>6000:fail('TRANSCRIPTION_INVALID','Не удалось получить допустимый текст записи.',422)
    return {'text':text.strip(),'duration_seconds':round(duration,2),'model':model,'api_requests':1}
