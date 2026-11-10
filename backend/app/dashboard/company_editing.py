"""Atomically version current company/materials without rewriting attempt snapshots."""
from copy import deepcopy
import json
import re
from uuid import uuid4
from .auth import fail
from .workflow import stamp

def current_services(company,materials):
    imported=materials.get('import_items',{}).get('services',{})
    result=[]
    for s in company['services']:
        match=re.search(r'(\d+(?:[.,]\d+)?)\s*(?:EUR|€)',s['conditions'],re.I)
        price=float(match[1].replace(',','.')) if match else None
        result.append({**deepcopy(imported.get(s['id'],{})),**s,'name':s['title'],'price_eur':price,'original_language':materials.get('source_languages',{}).get('services','de')})
    return result

def publish_company_edit(store,w,previous,record):
    current=w.get('materials','current') or {}
    if record==previous:return previous
    new=deepcopy(current);new.update(id=uuid4().hex,base_version=current.get('id'),created_at=stamp(),applied=True,translation_status='needs_update')
    new.pop('translations',None);new.pop('reference_version',None)
    new['services']=current_services(record,new)
    new.setdefault('import_items',{})['services']={s['id']:s for s in new['services']}
    # Retain originals and prior versions. Superseded policy text is not active policy.
    if record['limitations']!=previous['limitations']:
        for d in new.get('documents',[]):
            if d['purpose'] in ('terms','policy'):d['active']=False
        new.setdefault('documents',[]).append({'purpose':'terms','name':'Company policy','text':record['limitations'],'language':new.get('source_languages',{}).get('terms','de'),'active':True})
    new['markdown']=record['description']+'\n\n'+record['limitations'];new['sections']={}
    record=deepcopy(record);record['revision']=previous['revision']+1
    with store.connection() as c:
        c.execute('BEGIN IMMEDIATE')
        row=c.execute("SELECT data FROM documents WHERE kind='company' AND id='main'").fetchone()
        material=c.execute("SELECT data FROM learning_records WHERE kind='materials' AND id='current'").fetchone()
        if not row or json.loads(row[0])!=previous or (json.loads(material[0]).get('id') if material else None)!=current.get('id'):fail('VERSION_CONFLICT','Company changed; reload',409)
        c.execute("UPDATE documents SET data=? WHERE kind='company' AND id='main'",(json.dumps(record,ensure_ascii=False),))
        for kind,key,data in [('materials','current',new),('material_version',new['id'],new)]:c.execute('INSERT INTO learning_records VALUES (?,?,?) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data',(kind,key,json.dumps(data,ensure_ascii=False)))
    return record
