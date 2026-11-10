"""Explicit, guarded A17 material upgrade; never run automatically on server start."""
import argparse,copy,json,sqlite3,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app.dashboard.company_reference import SOURCE_COMPANY, canonical_company, initial_materials
from backend.app.dashboard.store import SQLiteStore
from backend.app.dashboard.workflow import Workflow

def apply(path):
    store=SQLiteStore(path);w=Workflow(store);old=store.get_company();m=w.get('materials','current')
    if old==canonical_company() and (m or {}).get('reference_version')=='lindenhaus-a17-v1':return m
    if old!=SOURCE_COMPANY:raise RuntimeError('Company differs from approved source. Review manually; no changes applied.')
    if len((m or {}).get('products',[]))!=18:raise RuntimeError('Expected approved 18-product material source')
    fresh=initial_materials(m);company=canonical_company()
    with store.connection() as c:
        c.execute('BEGIN IMMEDIATE')
        for kind,key,data in [('material_version',fresh['id'],fresh),('materials','current',fresh)]:
            c.execute('INSERT INTO learning_records VALUES (?,?,?) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data',(kind,key,json.dumps(data,ensure_ascii=False)))
        c.execute("UPDATE documents SET data=? WHERE kind='company' AND id=?",(json.dumps(company,ensure_ascii=False),'main'))
    return fresh
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('database',type=Path);args=p.parse_args();m=apply(args.database);print('A17 material version:',m['id'])
