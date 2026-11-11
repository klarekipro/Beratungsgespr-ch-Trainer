"""Private bounded failure bundles. Never exposed through HTTP or ordinary logs."""
import hashlib
import json
import os
import stat
import time
from pathlib import Path
from uuid import uuid4

MAX_BYTES=512*1024
MAX_FILES=5
MAX_AGE=7*24*60*60

def retain_failure(database,session,context,instructions,schema,data,wire,model_text,diagnostics,secret=''):
    if wire is None and not model_text:return {'capture_status':'no_response'}
    def redact(value):
        if isinstance(value,str):return value.replace(secret,'[REDACTED]') if len(secret)>=8 else value
        if isinstance(value,list):return [redact(x) for x in value]
        if isinstance(value,dict):return {k:redact(v) for k,v in value.items()}
        return value
    try:
        bundle={'format':'review_failure_v1','captured_at':time.time(),'session':session,'context':context,
                'instructions':instructions,'schema':schema,'payload':data,'wire_result':wire,
                'model_text':model_text,'diagnostics':diagnostics,
                'processor_sha256':hashlib.sha256(Path(__file__).with_name('review_service.py').read_bytes()).hexdigest()}
        content=json.dumps(redact(bundle),ensure_ascii=False).encode()
        if len(content)>MAX_BYTES:return {'capture_status':'oversize'}
        directory=Path(database).parent/'review_failures'
        if directory.is_symlink():return {'capture_status':'unsafe_directory'}
        directory.mkdir(mode=0o700,exist_ok=True);directory.chmod(0o700)
        files=sorted((p for p in directory.glob('*.json') if not p.is_symlink()),key=lambda p:p.stat().st_mtime)
        for p in list(files):
            if time.time()-p.stat().st_mtime>MAX_AGE:p.unlink();files.remove(p)
        while len(files)>=MAX_FILES:files.pop(0).unlink()
        identifier=uuid4().hex;path=directory/(identifier+'.json')
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'wb') as stream:stream.write(content)
        return {'capture_status':'retained','capture_id':identifier}
    except (OSError,ValueError,TypeError):return {'capture_status':'write_failed'}

def replay(path):
    """No provider, auth, server import or database writes. Reads only an owner-private bundle."""
    from . import review_service
    path=Path(path);info=path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_mode&0o077 or info.st_size>MAX_BYTES:raise ValueError('unsafe_bundle')
    bundle=json.loads(path.read_text())
    if bundle.get('format')!='review_failure_v1':raise ValueError('unknown_bundle')
    if bundle.get('processor_sha256')!=hashlib.sha256(Path(__file__).with_name('review_service.py').read_bytes()).hexdigest():raise ValueError('processor_changed')
    wire=bundle.get('wire_result')
    if wire is None:wire=json.loads(bundle['model_text'])
    return review_service.validate(review_service.bind_evidence(wire,bundle['session'],bundle['context']),bundle['session'],bundle['context'])
