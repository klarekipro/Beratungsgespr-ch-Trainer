"""SQLite online snapshot + isolated restore drill. Never replaces an existing database."""
import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile


def connect_readonly(path, immutable=False):
    path = Path(path).resolve(strict=True)
    return sqlite3.connect(path.as_uri()+'?mode=ro'+('&immutable=1' if immutable else ''), uri=True, timeout=10)


def signature(db):
    if db.execute('PRAGMA integrity_check').fetchall() != [('ok',)] or db.execute('PRAGMA foreign_key_check').fetchall():
        raise RuntimeError('Database integrity/foreign key check failed')
    result = {}
    for (name,) in db.execute("SELECT name FROM sqlite_schema WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
        # Names come from SQLite metadata; double-quote escaping prevents identifier injection.
        rows = []
        for row in db.execute('SELECT * FROM "'+name.replace('"','""')+'"'):
            encoded = json.dumps([{'bytes_sha256':hashlib.sha256(v).hexdigest()} if isinstance(v,bytes) else v for v in row],
                                 ensure_ascii=False, separators=(',',':')).encode()
            rows.append(hashlib.sha256(encoded).digest())
        result[name] = {'rows':len(rows),'content_sha256':hashlib.sha256(b''.join(sorted(rows))).hexdigest()}
    return result


def file_sha(path):
    with open(path,'rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()


def snapshot(source, target):
    source, target = Path(source).resolve(strict=True), Path(target).resolve()
    if source == target or target.exists() or target.is_symlink():
        raise RuntimeError('Refusing to overwrite a database or backup')
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.umask(0o077)
    fd = os.open(target, os.O_CREAT|os.O_EXCL|os.O_WRONLY, 0o600)
    os.close(fd)
    try:
        with closing(connect_readonly(source)) as original, closing(sqlite3.connect(target)) as copy:
            original.backup(copy, pages=256, sleep=0.05)
            copy.execute("PRAGMA journal_mode=DELETE")
            result = signature(copy)
        with open(target, 'rb') as f:
            os.fsync(f.fileno())
    except Exception:
        target.unlink(missing_ok=True)
        raise
    receipt = {'schema':1,'backup_sha256':file_sha(target),'tables':result}
    target.with_suffix(target.suffix+'.receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt


def restore_drill(backup, destination):
    backup, destination = Path(backup).resolve(strict=True), Path(destination).resolve()
    if destination.exists() or destination.is_symlink() or destination == backup:
        raise RuntimeError('Restore drill requires a NEW isolated directory; live replacement is unsupported')
    destination.mkdir(mode=0o700, parents=False)
    receipt = json.loads(backup.with_suffix(backup.suffix+'.receipt.json').read_text())
    if file_sha(backup) != receipt['backup_sha256']:
        raise RuntimeError('Backup checksum mismatch')
    with closing(connect_readonly(backup, immutable=True)) as source, closing(sqlite3.connect(destination/'trainer.sqlite3')) as target:
        source.backup(target)
        actual = signature(target)
    if actual != receipt['tables']:
        raise RuntimeError('Restore content differs from backup receipt')
    return {'status':'PASS','integrity':'ok','table_counts':{k:v['rows'] for k,v in actual.items()},'live_replacement':False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('operation',choices=('snapshot','restore-test'))
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--destination',type=Path,required=True)
    a = p.parse_args()
    value = snapshot(a.source,a.destination) if a.operation=='snapshot' else restore_drill(a.source,a.destination)
    # Actual receipts remain private. CLI emits no source contents or conversation-derived hashes.
    print(json.dumps({'status':'PASS','operation':a.operation,'live_replacement':False}))


if __name__=='__main__':
    main()
