"""Versioned company reference and bounded local document import. No translation calls."""
import base64
import copy
import csv
import hashlib
import io
import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from xml.etree import ElementTree as ET
from typing import Literal
from fastapi import Depends, HTTPException
from fastapi.responses import Response
from pydantic import Field
from .auth import CURRENT_USER, require_mentor
from .models import InputModel, Company

ROOT = Path(__file__).resolve().parents[3] / 'materials/lindenhaus'
REFERENCES = {lang: json.loads((ROOT/f'reference.{lang}.json').read_text()) for lang in ('de','en','ru')}
SOURCE_COMPANY = json.loads((ROOT/'company-card.json').read_text())
KNOWLEDGE = json.loads((ROOT/'company-knowledge.a37.json').read_text())

def company_digest(record):
    return hashlib.sha256(json.dumps(record,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def knowledge_company(language='de'):
    """Expected A37 profile; original A17 sources and historical snapshots stay intact."""
    result=canonical_company()
    result['description']=REFERENCES.get(language,REFERENCES['de'])['about']+'\n\n'+KNOWLEDGE['additions'].get(language,KNOWLEDGE['additions']['de'])
    return result

def now(): return datetime.now(timezone.utc).isoformat()
def reject(message, status=422): raise HTTPException(status, detail={'code':'INVALID_INPUT','message':message})
def service_record(s,language):
    label={'de':'Preis','en':'Price','ru':'Цена'}[language]
    price_text=f"{label}: {s['price_eur']} EUR. " if s['price_eur'] is not None else s['description']+'. '
    return {k:s[k] for k in ('id','title','description')} | {'conditions':price_text+s['conditions']}

def canonical_company():
    d=REFERENCES['de']; c=copy.deepcopy(SOURCE_COMPANY)
    c.update(revision=c['revision']+1,name=d['name'],description=d['about'])
    c['services']=[service_record(s,'de') for s in d['services']]
    # Preserve all commercial restrictions for dialogue snapshots.
    c['limitations']='\n\n'.join(v for _,v in d['terms'])
    # Company contract is bounded: the full policy remains in the material snapshot.
    if len(c['limitations'])>5000:c['limitations']=SOURCE_COMPANY['limitations']
    return Company.model_validate(c).model_dump()

def localized_company(record, language):
    expected=knowledge_company(); expected['revision']=record.get('revision')
    added=record==expected
    if not added and record not in (SOURCE_COMPANY,canonical_company()):return None
    d=REFERENCES.get(language,REFERENCES['de']); result=copy.deepcopy(record)
    result.update(name=d['name'],description=d['about'],services=[service_record(s,language) for s in d['services']])
    if added:result['description']=knowledge_company(language)['description']
    # Full approved policy in the chosen language, never claim a German translation.
    result['limitations']='\n\n'.join(v for _,v in d['terms'])
    return result

def initial_materials(previous):
    r=copy.deepcopy(previous or {})
    r.update(id=uuid4().hex,base_version=(previous or {}).get('id'),created_at=now(),applied=True,applied_at=now(),training_only=True,reference_version='lindenhaus-a17-v1',translations=copy.deepcopy(REFERENCES),original_language='de',source_languages={k:'de' for k in ('description','products','services','policy','terms')},original={'name':'company.de.md','text':(ROOT/'company.de.md').read_text()},products=copy.deepcopy(REFERENCES['de']['products']),markdown='\n\n'.join(x['text'] for x in REFERENCES['de']['documents']),errors=[])
    return r

def reference_for(materials, company, language):
    bound=bool(materials and materials.get('reference_version')==KNOWLEDGE['version'] and materials.get('reference_company_sha256')==company_digest(company))
    if materials and materials.get('translations') and (company==canonical_company() or bound):
        return copy.deepcopy(materials['translations'].get(language) or materials['translations']['de'])
    return None

class ExtractRequest(InputModel):
    name: str = Field(min_length=1,max_length=240)
    content: str = Field(max_length=14000000)
class PreviewRequest(InputModel):
    mode: Literal['merge','replace'] = 'merge'
    source_id: str = Field(max_length=80)
    purpose: Literal['description','products','services','policy','terms','document']
    language: Literal['de','en','ru']
    company_name: str = Field(default='',max_length=240)
    mapping: dict[str,str] = Field(default_factory=dict,max_length=20)
    text: str = Field(default='',max_length=30000)
    rows: list[dict] = Field(default_factory=list,max_length=200)

FIELDS=['id','name','price_eur','unit','description','conditions','category','features','price_includes','availability','promotion','valid_until']
ALIASES={'name':['name','title','название','наименование','bezeichnung','leistung','produkt','modell','услуга','товар'], 'price_eur':['price_eur','price','preis','цена','preis eur'], 'unit':['unit','einheit','единица'], 'description':['description','beschreibung','описание','enthalten','что включено'], 'conditions':['conditions','bedingungen','условия'], 'category':['category','kategorie','категория'], 'features':['features','merkmale','характеристики'], 'id':['id','артикул','sku','produkt-id','service-id']}

def extract(name, raw):
    ext=Path(name).suffix.lower(); rows=[]; text='';warnings=[]
    if ext in ('.txt','.md','.markdown','.csv'):
        try:text=raw.decode('utf-8-sig')
        except UnicodeDecodeError:reject('UTF-8 required / Требуется UTF-8 / UTF-8 erforderlich')
        if ext=='.csv':
            try:dialect=csv.Sniffer().sniff(text[:8192],delimiters=',;\t')
            except csv.Error:dialect=csv.excel
            reader=csv.DictReader(io.StringIO(text),dialect=dialect)
            rows=list(reader)
            if any(None in r for r in rows):reject('CSV: inconsistent columns / Несогласованные столбцы')
        elif ext in ('.md','.markdown','.txt'):
            # A single ordinary pipe table is unambiguous; retain surrounding text in the source.
            tables=[];lines=text.splitlines()
            for i,line in enumerate(lines[:-1]):
                if '|' in line and re.fullmatch(r'[\s|:\-]+',lines[i+1]) and '-' in lines[i+1]:
                    header=[v.strip() for v in line.strip().strip('|').split('|')];data=[]
                    for data_line in lines[i+2:]:
                        if '|' not in data_line or not data_line.strip():break
                        values=[v.strip() for v in data_line.strip().strip('|').split('|')]
                        if len(values)!=len(header):reject('Markdown table: inconsistent columns')
                        data.append(dict(zip(header,values)))
                    tables.append(data)
            if len(tables)==1:rows=tables[0]
            elif len(tables)>1:warnings.append('Multiple Markdown tables: import the required table separately / Импортируйте нужную таблицу отдельно')
    elif ext=='.xlsx':
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                if sum(i.file_size for i in z.infolist())>20000000:reject('XLSX too large')
                ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                strings=[]
                if 'xl/sharedStrings.xml' in z.namelist():strings=[''.join(e.itertext()) for e in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si',ns)]
                book=ET.fromstring(z.read('xl/workbook.xml')); sheets=book.findall('m:sheets/m:sheet',ns)
                if len(sheets)!=1:reject('XLSX: export the required sheet as a separate workbook / Сохраните нужный лист отдельной книгой')
                relid=sheets[0].get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
                rels=ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
                target=next(r.get('Target') for r in rels if r.get('Id')==relid)
                path=target.lstrip('/') if target.startswith('/') else 'xl/'+target
                matrix=[]
                for row in ET.fromstring(z.read(path)).findall('m:sheetData/m:row',ns):
                    cells={}
                    for cell in row.findall('m:c',ns):
                        ref=cell.get('r','A1'); idx=0
                        for ch in re.match('[A-Z]+',ref)[0]:idx=idx*26+ord(ch)-64
                        if idx>50:reject('Maximum 50 columns')
                        v=cell.find('m:v',ns); value=v.text if v is not None and v.text else ''
                        if cell.find('m:f',ns) is not None and not value:reject('XLSX formula has no cached result; save calculated values first')
                        if cell.get('t')=='s':value=strings[int(value)]
                        if cell.get('t')=='inlineStr':value=''.join(cell.find('m:is',ns).itertext())
                        cells[idx-1]=value
                    if cells:matrix.append([cells.get(i,'') for i in range(max(cells)+1)])
                if not matrix:reject('Empty XLSX / Пустая таблица')
                headers=matrix[0]
                if len(set(headers))!=len(headers) or any(not h for h in headers):reject('Unique nonempty headers required')
                rows=[dict(zip(headers,r+['']*(len(headers)-len(r)))) for r in matrix[1:]]
                text='\n'.join('\t'.join(map(str,r)) for r in matrix)
        except (zipfile.BadZipFile,ET.ParseError,KeyError,StopIteration,ValueError,IndexError):reject('Unreadable XLSX / Не удалось прочитать XLSX')
    elif ext=='.pdf':
        binary=shutil.which('pdftotext')
        if not binary:reject('Text PDF import requires local Poppler pdftotext / Нужен локальный Poppler pdftotext')
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'document.pdf';p.write_bytes(raw)
            try:r=subprocess.run([binary,'-layout',str(p),'-'],capture_output=True,timeout=15)
            except subprocess.TimeoutExpired:reject('PDF extraction timed out')
            if r.returncode:reject('Unreadable or protected PDF / PDF недоступен для чтения')
            text=r.stdout.decode('utf-8',errors='replace').strip()
        if len(re.sub(r'\s','',text))<10:reject('PDF has no readable text layer. OCR is not included. / Нет текстового слоя PDF. Распознавание сканов не поддерживается. / Kein lesbarer Text; OCR nicht verfügbar.')
        warnings.append('PDF: table columns are not detected; review and prepare a CSV/XLSX table / Столбцы PDF не распознаются: проверьте текст и подготовьте CSV/XLSX')
    else:reject('Supported: MD, TXT, CSV, XLSX (one sheet), text PDF')
    if not text.strip():reject('Empty document / Пустой документ')
    if len(rows)>200 or len(text)>100000:reject('Maximum 200 rows / 100000 characters')
    headers=list(rows[0]) if rows else []
    mapping={}
    for f in FIELDS:
        match=next((h for h in headers if h.strip().lower() in ALIASES.get(f,[f])),None)
        if match:mapping[f]=match
    return text,rows,headers,mapping,warnings

def price(value):
    value=str(value).strip()
    if not value:return None
    value=re.sub(r'\s|EUR|€','',value,flags=re.I).replace(',','.')
    try:p=float(value)
    except ValueError:raise ValueError('price')
    if not 0<=p<=1000000:raise ValueError('price')
    return int(p) if p.is_integer() else p

def editable_item(previous,current,purpose):
    if not previous:return {}
    prior=current.get('import_items',{}).get(purpose,{}).get(previous['id'],{})
    result={**copy.deepcopy(prior),**copy.deepcopy(previous)}
    result['name']=previous.get('title',previous.get('name',''))
    if purpose=='services':
        match=re.search(r'(\d+(?:[.,]\d+)?)\s*(?:EUR|€)',previous.get('conditions',''),re.I)
        result['price_eur']=price(match[1]) if match else None
        result['conditions']=re.sub(r'^(?:(?:Preis|Price|Цена)\s*:\s*)?\d+(?:[.,]\d+)?\s*(?:EUR|€)\.\s*','',previous.get('conditions',''),flags=re.I)
        result['conditions']=re.sub(r'^(?:Preis unbekannt|Price unknown|Цена неизвестна)\.\s*','',result['conditions'],flags=re.I)
    elif 'price_eur' in result:result['price_eur']=price(result['price_eur'])
    result.setdefault('original_language','de')
    result.setdefault('article',previous['id'] if purpose=='products' and not previous['id'].startswith('item_') else '')
    return result

def same_item(before,after):
    fields=set(FIELDS)|{'article','original_language','unmapped'}
    return all(before.get(k,{} if k=='unmapped' else '')==after.get(k,{} if k=='unmapped' else '') for k in fields)

def attach_company_reference(app,w,store,lock):
    mentor=[Depends(require_mentor)]
    @app.get('/api/company-reference')
    async def reference():
        lang=CURRENT_USER.get()['locale'];m=w.get('materials','current')
        return {'reference':reference_for(m,store.get_company(),lang),'materials':m}
    @app.post('/api/mentor/company-documents/extract',dependencies=mentor)
    async def extract_document(value:ExtractRequest):
        try:raw=base64.b64decode(value.content,validate=True)
        except ValueError:reject('Invalid file encoding')
        if len(raw)>10000000:reject('Maximum file size 10 MB')
        text,rows,headers,mapping,warnings=extract(value.name,raw)
        result=dict(id=uuid4().hex,name=Path(value.name).name,content=value.content,text=text,rows=rows,headers=headers,mapping=mapping,warnings=warnings,author=CURRENT_USER.get()['id'],created_at=now())
        w.put('company_source',result['id'],result)
        return {'source':result,'fields':FIELDS}
    @app.get('/api/company-documents/{sid}/original')
    async def original(sid:str):
        source=w.get('company_source',sid)
        # Employees may view only applied source documents.
        applied=(w.get('materials','current') or {}).get('documents',[])
        if not source or (CURRENT_USER.get()['role']!='mentor_admin' and not any(d.get('source_id')==sid for d in applied)):reject('Not found',404)
        return Response(base64.b64decode(source['content']),media_type={'.pdf':'application/pdf','.xlsx':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}.get(Path(source['name']).suffix.lower(),'text/plain; charset=utf-8'),headers={'Content-Disposition':"inline; filename*=UTF-8''"+__import__('urllib.parse',fromlist=['quote']).quote(source['name']),'X-Content-Type-Options':'nosniff'})
    @app.post('/api/mentor/company-documents/preview',dependencies=mentor)
    async def preview(value:PreviewRequest):
        source=w.get('company_source',value.source_id)
        if not source or source['author']!=CURRENT_USER.get()['id']:reject('Source not found')
        current=w.get('materials','current') or {}; company=store.get_company(); errors=[];warnings=list(source['warnings']);items=[];changes=[]
        is_table=value.purpose in ('products','services')
        if is_table:
            if not value.rows:errors.append('Table required: CSV or XLSX / Требуется таблица CSV или XLSX')
            if 'name' not in value.mapping:errors.append('Map name / Сопоставьте название')
            if 'price_eur' not in value.mapping:warnings.append('Price missing / Цена не указана')
            old=current.get('products',[]) if value.purpose=='products' else company['services']
            for n,row in enumerate(value.rows):
                mapped={f:str(row.get(col,'')).strip() for f,col in value.mapping.items() if f in FIELDS}
                name=mapped.get('name',''); given=mapped.get('id','')
                known=next((s['id'] for d in REFERENCES.values() for s in d['services'] if (s['title'].casefold()==name.casefold() or (given and s['source_id']==given)) and value.purpose=='services'),None)
                matches=[x for x in old if (given and (x['id']==given or x.get('article')==given)) or (not given and known and x['id']==known)]
                if len(matches)>1:errors.append(f'Row {n+1}: conflicting ID/article');continue
                previous=matches[0] if matches else None
                if given and known and previous and previous['id']!=known:errors.append(f'Row {n+1}: conflicting service ID');continue
                ident=previous['id'] if previous else ('item_'+hashlib.sha256((value.purpose+'|'+given).encode()).hexdigest()[:18] if given else 'item_'+uuid4().hex)
                if not given and not known:warnings.append(f'{name}: no reliable ID/article; creates a NEW record')
                if not name:errors.append(f'Row {n+1}: name required');continue
                if any(x['id']==ident for x in items):errors.append(f'Row {n+1}: duplicate ID/article / Повтор ID или артикула');continue
                baseline=editable_item(previous,current,value.purpose)
                try:p=price(mapped['price_eur']) if 'price_eur' in mapped else baseline.get('price_eur')
                except ValueError:p=None;errors.append(f'Row {n+1}: invalid price; leave blank for unknown / Неверная цена')
                if p is None:warnings.append(f'{name}: price unknown / Цена неизвестна')
                item={**(baseline if value.mode=='merge' else {}),**mapped,'id':ident,'name':name,'price_eur':p,'original_language':value.language,'article':given or (previous or {}).get('article','')}
                if value.purpose=='services':
                    item.update(title=name,description=mapped.get('description',mapped.get('features',baseline.get('description','—'))),conditions=mapped.get('conditions',baseline.get('conditions','')))
                    if not mapped.get('description'):warnings.append(f'{name}: description requires review / Проверьте описание')
                else:
                    for f in ['category','features','price_includes','availability','promotion','valid_until']:item.setdefault(f,'')
                    if not item['features']:item['features']=mapped.get('description','')
                    if not item['availability']:warnings.append(f'{name}: availability unknown / Доступность неизвестна')
                extras={k:v for k,v in row.items() if k not in value.mapping.values() and v}
                if extras:item['unmapped']=extras;warnings.append(f'{name}: unmapped columns / Несопоставленные столбцы: '+', '.join(extras))
                items.append(item)
                prior=baseline
                changes.append({'id':ident,'name':name,'article':given or (previous or {}).get('article',''),'action':'unchanged' if previous and same_item(prior,item) else 'updated' if previous else 'added'})
        elif not value.text.strip():errors.append('Text required / Требуется текст')
        removed=[]
        if is_table and value.mode=='replace':
            removed=[x for x in old if x['id'] not in {i['id'] for i in items}]
            changes.extend({'id':x['id'],'name':x.get('name',x.get('title','')),'article':x.get('article') or (x['id'] if not x['id'].startswith('item_') else ''),'action':'removed'} for x in removed)
            if value.purpose=='services':
                referenced={i for sc in store.list_scenarios() for i in sc['allowed_outcomes']}
                for p in store._list('client_profile'):referenced.update(p['scenario']['source_scenario']['allowed_outcomes'])
                if referenced&{x['id'] for x in removed}:errors.append('Referenced services cannot be removed. Review scenario/profile references separately; no automatic reassignment.')
        if value.purpose=='services' and len(({s['id'] for s in company['services']} if value.mode=='merge' else set())|{s['id'] for s in items})>20:errors.append('Maximum 20 services')
        if value.purpose in ('policy','terms'):
            active=[d['text'] for d in current.get('documents',[]) if d['purpose'] in ('policy','terms') and d.get('active',True) and not (value.mode=='replace' and d['purpose']==value.purpose)]
            if not active and value.mode=='merge':active=[company['limitations']]
            if len('\n\n'.join(active+[value.text]))>5000:errors.append('Combined policy exceeds 5000 characters; shorten it or choose replacement.')
        if not is_table:
            changes.append({'name':source['name'],'action':'updated' if value.purpose!='document' else 'added'})
        result=dict(id=uuid4().hex,author=CURRENT_USER.get()['id'],source_id=source['id'],source_name=source['name'],purpose=value.purpose,mode=value.mode,company_name=value.company_name,language=value.language,text=value.text,items=items,changes=changes,errors=errors,warnings=warnings,created_at=now(),base_version=current.get('id'),base_company=company)
        w.put('company_preview',result['id'],result);return {'preview':result}
    @app.post('/api/mentor/company-documents/apply',dependencies=mentor)
    async def apply(value:dict):
        async with lock('materials'):
            r=w.get('company_preview',value.get('preview_id',''))
            if not r or r['author']!=CURRENT_USER.get()['id'] or r['errors'] or value.get('confirm') is not True:reject('Reviewed preview and explicit confirmation required')
            if r.get('applied'):return {'materials':w.get('material_version',r['id'])}
            current=w.get('materials','current') or {};c=store.get_company()
            if current.get('id')!=r['base_version'] or c!=r['base_company']:reject('Preview outdated; preview again',409)
            new=copy.deepcopy(current);new.update(id=r['id'],base_version=current.get('id'),created_at=now(),applied=True,original_language=r['language'])
            # Any edit invalidates the pre-agreed bundle. Original and translations remain separate.
            new.pop('translations',None);new.pop('reference_version',None);new['translation_status']='needs_update'
            docs=copy.deepcopy(new.get('documents',[]))
            for d in docs:
                if d['purpose']==r['purpose'] and (r['purpose'] in ('products','services','description') or r.get('mode')=='replace'):d['active']=False
            source=w.get('company_source',r['source_id'])
            if r['purpose'] in ('policy','terms') and r.get('mode','merge')=='merge' and not any(d['purpose'] in ('policy','terms') and d.get('active',True) for d in docs):
                docs.append(dict(purpose='terms',language=current.get('source_languages',{}).get('terms','de'),name='Existing company policy',text=c['limitations'],active=True))
            docs.append(dict(purpose=r['purpose'],language=r['language'],source_id=r['source_id'],name=r['source_name'],active=True,text=r['text'] or source['text'],translations={}))
            new['documents']=docs
            new.setdefault('source_languages',{k:'de' for k in ('description','products','services','policy','terms')})[r['purpose']]=r['language']
            if r['items']:
                new.setdefault('import_items',{}).setdefault(r['purpose'],{}).update({s['id']:s for s in r['items']})
            if r['purpose'] in ('products','services'):
                if r['purpose']=='products':
                    existing={p['id']:p for p in new.get('products',[])} if r.get('mode','merge')=='merge' else {};existing.update({p['id']:p for p in r['items']});new['products']=list(existing.values())
                else:
                    existing={s['id']:s for s in c['services']} if r.get('mode','merge')=='merge' else {}
                    for s in r['items']:
                        cond=s['conditions'];p=s['price_eur']
                        cond=(f'{p} EUR. ' if p is not None else {'de':'Preis unbekannt. ','en':'Price unknown. ','ru':'Цена неизвестна. '}[r['language']])+cond
                        existing[s['id']]={k:s[k] for k in ('id','title','description')}|{'conditions':cond}
                    c['services']=list(existing.values())
                    from .company_editing import current_services
                    new['services']=current_services(c,new)
                    for item in new['services']:
                        authored=next((x for x in r['items'] if x['id']==item['id']),None)
                        if authored:item.update(authored)
                    new.setdefault('import_items',{})['services']={s['id']:s for s in new['services']}
            elif r['purpose']=='description':
                c['description']=r['text']
                if r.get('company_name'):c['name']=r['company_name']
            elif r['purpose'] in ('policy','terms'):
                # Latest complete source documents form the current profile policy.
                c['limitations']='\n\n'.join(d['text'] for d in docs if d['purpose'] in ('policy','terms') and d.get('active',True))
            new['markdown']=c['description']+'\n\n'+c['limitations']
            new['sections']={}
            c['revision']+=1;c['reviewed']=True
            try:c=Company.model_validate(c).model_dump()
            except ValueError:reject('Profile field too long; shorten the reviewed text / Сократите текст профиля')
            # One transaction publishes company and material pointers together.
            with store.connection() as con:
                con.execute('BEGIN IMMEDIATE')
                latest_company=con.execute("SELECT data FROM documents WHERE kind='company' AND id='main'").fetchone()
                latest_material=con.execute("SELECT data FROM learning_records WHERE kind='materials' AND id='current'").fetchone()
                if not latest_company or json.loads(latest_company[0])!=r['base_company'] or (json.loads(latest_material[0]).get('id') if latest_material else None)!=r['base_version']:reject('Preview outdated; preview again',409)
                for kind,key,data in [('materials','current',new),('material_version',new['id'],new),('company_preview',r['id'],r|{'applied':True})]:
                    con.execute('INSERT INTO learning_records VALUES (?,?,?) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data',(kind,key,json.dumps(data,ensure_ascii=False)))
                con.execute("UPDATE documents SET data=? WHERE kind='company' AND id=?",(json.dumps(c,ensure_ascii=False),'main'))
            return {'materials':new,'company':c}
