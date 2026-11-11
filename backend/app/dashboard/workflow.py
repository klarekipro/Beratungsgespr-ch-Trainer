"""A15: independent learning records, immutable material versions and certificates.

No migration rewrites historical documents. All new state lives in its own table.
"""
import csv
import io
import json
import hashlib
import logging
from . import review_service
from datetime import datetime, timezone
from uuid import uuid4
from typing import Literal
from pydantic import Field
from fastapi import Depends, HTTPException
from fastapi.responses import Response
from .models import InputModel
from .auth import CURRENT_USER, require_mentor
from .review_provider import ReviewProvider

DEFAULT_GUIDANCE = {
    'goal': 'Bedarf verstehen, Möglichkeiten und Grenzen prüfen, einen begründeten nächsten Schritt vereinbaren.',
    'conditions': 'Freiwillig genannte Bedürfnisse zählen. Keine Pflichtformulierungen, Fragezählung oder Punkte.',
    'outcomes': 'Auftrag bestätigt; vorläufig vereinbart; Angebot zur Prüfung; Entscheidung vertagt; begründete Absage; kein nächster Schritt.',
    'review_notes': 'Lernqualität und Geschäftsergebnis getrennt beurteilen. Zusagen anhand der gespeicherten Materialien prüfen.'}

def stamp(): return datetime.now(timezone.utc).isoformat()
def reject(message, code=422): raise HTTPException(code, detail={'code':'INVALID_INPUT','message':message})

class AnalysisRequest(InputModel):
    restart: bool = False
    audience: Literal['learner','mentor'] = 'learner'
class Guidance(InputModel):
    goal: str = Field(min_length=1,max_length=3000)
    conditions: str = Field(default='',max_length=4000)
    outcomes: str = Field(default='',max_length=3000)
    review_notes: str = Field(default='',max_length=4000)
class ImportRequest(InputModel):
    markdown: str = Field(max_length=30000)
    csv: str = Field(max_length=100000)
class ApplyRequest(InputModel):
    preview_id: str = Field(max_length=80)
class CertificateRequest(InputModel):
    session_id: str = Field(max_length=80)
    print_name: str = Field(min_length=1,max_length=120)
    topic: str = Field(min_length=1,max_length=240)
    basis: list[str] = Field(min_length=1,max_length=30)
    comment: str = Field(default='',max_length=3000)
    replaces: str | None = None
class IssueRequest(InputModel):
    confirm: bool
class DecisionDraft(InputModel):
    note: str = Field(default='',max_length=6000)
    assessment: dict = Field(default_factory=dict)
    goal: Literal['not_reviewed','achieved','partly','not_achieved'] = 'not_reviewed'
    observations: str = Field(default='',max_length=6000)

class Workflow:
    def __init__(self, store):
        self.store=store
        with store.connection() as c:
            c.execute('CREATE TABLE IF NOT EXISTS learning_records (kind TEXT NOT NULL,id TEXT NOT NULL,data TEXT NOT NULL,PRIMARY KEY(kind,id))')
            c.execute("INSERT OR IGNORE INTO metadata VALUES ('learning_schema_version','1')")
    def get(self, kind, key):
        with self.store.connection() as c:
            r=c.execute('SELECT data FROM learning_records WHERE kind=? AND id=?',(kind,key)).fetchone()
            return json.loads(r[0]) if r else None
    def put(self,kind,key,value):
        with self.store.connection() as c:
            c.execute('INSERT INTO learning_records VALUES (?,?,?) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data',(kind,key,json.dumps(value,ensure_ascii=False)))
    def publish_review(self,session,expected,record):
        from .store import VersionConflict
        with self.store.connection() as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute("SELECT data FROM documents WHERE kind='session' AND id=?",(session['id'],)).fetchone()
            if not row or json.loads(row[0])['version']!=expected:raise VersionConflict('Session changed')
            c.execute("UPDATE documents SET data=? WHERE kind='session' AND id=?",(json.dumps(session,ensure_ascii=False),session['id']))
            c.execute("INSERT INTO learning_records VALUES ('published_review',?,?) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data",(session['id'],json.dumps(record,ensure_ascii=False)))
    def all(self,kind):
        with self.store.connection() as c:
            return [json.loads(r[0]) for r in c.execute('SELECT data FROM learning_records WHERE kind=? ORDER BY id',(kind,))]
    def snapshot(self,scenario_id):
        return {'guidance': self.get('guidance',scenario_id) or DEFAULT_GUIDANCE,
                'materials': self.get('materials','current'), 'captured_at':stamp(), 'source':'attempt_snapshot'}
    def context(self,s):
        return self.get('snapshot',s['id']) or {'guidance':DEFAULT_GUIDANCE,'materials':None,'source':'legacy_fallback_not_original','captured_at':None}
    def published(self,s,auth):
        record=self.get('published_review',s['id'])
        if record:return record
        if s.get('review_status')=='reviewed' and s.get('review_note'):
            author=auth.user(s.get('reviewed_by')) if s.get('reviewed_by') else None
            return {'session_id':s['id'],'employee_id':auth.owner(s['id']),
                    'mentor_id':s.get('reviewed_by'),'mentor_name':author['display_name'] if author else 'Mentor',
                    'published_at':s.get('reviewed_at') or s['updated_at'],'note':s['review_note'],
                    'assessment':s.get('mentor_assessment'),'goal':'not_reviewed','observations':'','legacy_review':True}
        return None
    def enrich(self,v,s,auth):
        v['learning_context']=self.context(s)
        v['analysis']=review_service.public_analysis(self.get('analysis',s['id']+':learner'),CURRENT_USER.get() and CURRENT_USER.get()['role']=='mentor_admin')
        v['review_heading']=review_service.heading(s,self.context(s))
        v['review_message_ids']=review_service.message_ids(s)
        v['published_review']=self.published(s,auth)
        u=auth.user(auth.owner(s['id']))
        v['employee_name']=u['display_name'] if u else 'Archiv'
        if CURRENT_USER.get() and CURRENT_USER.get()['role']=='mentor_admin':
            v['mentor_analysis']=self.get('analysis',s['id']+':mentor') or {'status':'not_run'}
            v['decision_draft']=self.get('decision_draft',s['id'])
        return v

def attach_workflow(app,w,auth,get_session,lock,api_key,model,summary):
    app.state.workflow=w
    mentor=[Depends(require_mentor)]
    @app.get('/api/learning/results')
    async def results():
        u=CURRENT_USER.get()
        return {'reviews':[r for s in w.store.list_sessions() if (u['role']=='mentor_admin' or auth.owner(s['id'])==u['id']) and (r:=w.published(s,auth))],
                'certificates':[r for r in w.all('certificate') if (u['role']=='mentor_admin' or r['employee_id']==u['id']) and r['status']!='draft']}

    @app.post('/api/learning/sessions/{sid}/analysis')
    async def analyze(sid:str,value:AnalysisRequest):
        s=get_session(sid);u=CURRENT_USER.get()
        if s['status']!='finished': reject('Finish first',409)
        if value.audience=='mentor' and u['role']!='mentor_admin':reject('Forbidden',403)
        arriving=stamp()
        async with lock('analysis:'+sid+':'+value.audience):
            key=sid+':'+value.audience;old=w.get('analysis',key)
            # A click waiting behind an in-flight request must reuse its outcome.
            if old and (not value.restart or (old.get('completed_at') or '')>=arriving):return {'analysis':review_service.public_analysis(old,u['role']=='mentor_admin')}
            started=stamp();ctx=w.context(s)
            record={'session_id':sid,'status':'running','started_at':started,'audience':value.audience,'language':u.get('locale','de'),'context_source':ctx.get('source','legacy_fallback_not_original')}
            if old and old.get('result'):record['result']=old['result']
            w.put('analysis',key,record)
            provider=None;phase='request_construction';data=None
            try:
                data=review_service.payload(s,ctx,value.audience,u.get('locale','de'))
                custom=getattr(app.state,'analysis_provider',None)
                if not api_key and not custom:raise RuntimeError('AI unavailable')
                provider=custom or ReviewProvider(api_key,model,timeout=45)
                phase='provider_request'
                result=await provider._request_json(review_service.SYSTEM,data,review_service.request_schema(s),'consultation_review',max_output_tokens=3500)
                phase='schema_validation'
                result=review_service.bind_evidence(result,s)
                phase='semantic_validation'
                record.update(status='ready',result=review_service.validate(result,s,ctx))
            except Exception as exc:
                category=getattr(exc,'code',None) or ('ai_invalid_response' if isinstance(exc,(ValueError,KeyError,TypeError)) else 'ai_unavailable')
                allowed={'ai_context_limit','ai_timeout','ai_unavailable','ai_rate_limited','ai_access_denied','ai_not_configured','ai_invalid_response','ai_incomplete','ai_request_rejected','ai_refusal'}
                if category not in allowed:category='ai_unavailable'
                record.update(status='error',error=category)
                transport=dict(getattr(provider,'review_diagnostics',{}) or {})
                stage=getattr(exc,'stage',None) or (transport.get('stage',phase) if phase=='provider_request' else phase)
                if category=='ai_timeout':stage='provider_timeout'
                elif category=='ai_context_limit':stage='request_construction'
                elif category=='ai_incomplete':stage='provider_incomplete'
                record['diagnostics']={**transport,'stage':stage,'validation_reason':getattr(exc,'reason',None) or (str(exc) if isinstance(exc,ValueError) and str(exc) in {'structure','text type','list type','stage type','stage structure','evidence structure','review text','review list','stages','duplicate message IDs','observation','missing evidence','evidence','advice structure','advice text','advice evidence','material evidence','claim checks','claim verdict','advice action','advice priorities','advice findings'} else None),'validation_path':getattr(exc,'path',None),'category':category,'exception_type':type(exc).__name__,'payload_characters':len(json.dumps(data,ensure_ascii=False)) if data is not None else 0,'request_count':getattr(provider,'request_count',0),'message_count':len(s['messages']),'evidence_contract':'message_selection_v1'}
                logging.getLogger(__name__).warning('review_failed session=%s audience=%s diagnostics=%s',sid,value.audience,json.dumps(record['diagnostics'],ensure_ascii=True,sort_keys=True))
            if record['status']=='ready':record['diagnostics']={**dict(getattr(provider,'review_diagnostics',{}) or {}),'stage':'persisted','payload_characters':len(json.dumps(data,ensure_ascii=False)) if data is not None else 0,'request_count':getattr(provider,'request_count',0),'message_count':len(s['messages']),'evidence_contract':'message_selection_v1'}
            record['completed_at']=stamp()
            w.put('analysis_history',uuid4().hex,record)
            if record['status']=='error' and old and old.get('result'):
                record={**old,'status':'ready','attempt_status':'error','last_error':record['error'],'completed_at':record['completed_at'],'diagnostics':record['diagnostics']}
            w.put('analysis',key,record)
            return {'analysis':review_service.public_analysis(record,u['role']=='mentor_admin')}

    @app.get('/api/mentor/learning/guidance/{sid}',dependencies=mentor)
    async def guidance(sid:str):return {'guidance':w.get('guidance',sid) or DEFAULT_GUIDANCE}
    @app.put('/api/mentor/learning/guidance/{sid}',dependencies=mentor)
    async def save_guidance(sid:str,value:Guidance):
        if not w.store.get_scenario(sid):reject('Unknown scenario',404)
        w.put('guidance',sid,value.model_dump());return {'guidance':value.model_dump()}
    @app.put('/api/mentor/learning/reviews/{sid}/draft',dependencies=mentor)
    async def draft(sid:str,value:DecisionDraft):
        get_session(sid);r={**value.model_dump(),'saved_at':stamp(),'author':CURRENT_USER.get()['id']}
        w.put('decision_draft',sid,r);return r

    @app.get('/api/learning/materials')
    async def current_materials():return {'materials':w.get('materials','current')}
    @app.post('/api/mentor/learning/materials/preview',dependencies=mentor)
    async def preview(value:ImportRequest):
        errors=[];products=[]
        reader=csv.DictReader(io.StringIO(value.csv.lstrip('\ufeff')))
        required={'id','category','name','features','price_eur','price_includes','availability','promotion','valid_until'}
        if not required.issubset(reader.fieldnames or []):errors.append('CSV: '+', '.join(sorted(required)))
        else:
            for n,row in enumerate(reader,2):
                if n>202:errors.append('Maximum 200 products');break
                row={k:(v or '').strip() for k,v in row.items() if k in required}
                try:
                    price=float(row['price_eur'])
                    if not 0<=price<=1000000 or not row['id'] or not row['name']:raise ValueError()
                    if row['valid_until']:__import__('datetime').date.fromisoformat(row['valid_until'])
                    if any(p['id']==row['id'] for p in products):raise ValueError()
                    products.append(row)
                except (ValueError,KeyError):errors.append(f'CSV row {n}: invalid ID, price, date or duplicate')
        if not value.markdown.strip():errors.append('Markdown required')
        sections={}
        heading='profile';chunks=[]
        for line in value.markdown.splitlines():
            if line.startswith('## '):
                sections[heading]='\n'.join(chunks).strip();heading=line[3:].strip();chunks=[]
            else:chunks.append(line)
        sections[heading]='\n'.join(chunks).strip()
        result={'id':uuid4().hex,'sections':sections,'markdown':value.markdown,'products':products,'errors':errors,'author':CURRENT_USER.get()['id'],'created_at':stamp(), 'base_version':(w.get('materials','current') or {}).get('id')}
        w.put('import_preview',result['id'],result);return {'preview':result}
    @app.post('/api/mentor/learning/materials/apply',dependencies=mentor)
    async def apply(value:ApplyRequest):
        async with lock('materials'):
            r=w.get('import_preview',value.preview_id)
            if not r or r['author']!=CURRENT_USER.get()['id'] or r['errors']:reject('Invalid preview')
            if r.get('applied'):return {'materials':w.get('material_version',r['id'])}
            if r['base_version']!=(w.get('materials','current') or {}).get('id'):reject('Preview outdated',409)
            r.update(applied=True,applied_at=stamp(),training_only=True)
            w.put('material_version',r['id'],r);w.put('materials','current',r);w.put('import_preview',r['id'],r)
            return {'materials':r}

    def certificate(cid):
        r=w.get('certificate',cid);u=CURRENT_USER.get()
        if not r or (u['role']!='mentor_admin' and (r['employee_id']!=u['id'] or r['status']=='draft')):reject('Not found',404)
        return r
    @app.post('/api/mentor/learning/certificates/preview',dependencies=mentor)
    async def preview_certificate(value:CertificateRequest):
        s=get_session(value.session_id);owner=auth.owner(s['id'])
        if not owner or s['status']!='finished':reject('Completed owned session required')
        if s['id'] not in value.basis or len(set(value.basis))!=len(value.basis):reject('Invalid basis')
        for sid in value.basis:
            b=get_session(sid)
            if auth.owner(sid)!=owner or b['status']!='finished':reject('Basis must belong to this employee')
        if value.replaces and certificate(value.replaces)['employee_id']!=owner:reject('Recipient mismatch')
        u=CURRENT_USER.get();r={**value.model_dump(),'id':uuid4().hex,'employee_id':owner,'status':'draft','created_at':stamp(),'mentor_id':u['id'],'mentor_name':u['display_name']}
        w.put('certificate',r['id'],r);return {'certificate':r}
    @app.post('/api/mentor/learning/certificates/{cid}/issue',dependencies=mentor)
    async def issue(cid:str,value:IssueRequest):
        async with lock('certificates'):
            r=certificate(cid)
            if not value.confirm:reject('Explicit confirmation required')
            if r['status']!='draft':return {'certificate':r}
            if r['mentor_id']!=CURRENT_USER.get()['id']:reject('Author mismatch',403)
            # Content idempotency also covers accidentally opening a second preview.
            for existing in w.all('certificate'):
                if existing['status']=='issued' and not r.get('replaces') and all(existing.get(k)==r.get(k) for k in ['employee_id','print_name','topic','basis','comment','mentor_id']):
                    return {'certificate':existing}
            r.update(status='issued',issued_at=stamp(),number='KKI-'+datetime.now().strftime('%Y')+'-'+r['id'][:12].upper())
            if r.get('replaces'):
                old=certificate(r['replaces']);old.update(status='replaced',replaced_by=cid);w.put('certificate',old['id'],old)
            w.put('certificate',cid,r);w.put('certificate_event',uuid4().hex,{'certificate_id':cid,'status':'issued','at':stamp(),'author':CURRENT_USER.get()['id']})
            return {'certificate':r}
    @app.post('/api/mentor/learning/certificates/{cid}/revoke',dependencies=mentor)
    async def revoke(cid:str):
        async with lock('certificates'):
            r=certificate(cid)
            if r['status']=='issued':
                r.update(status='revoked',revoked_at=stamp(),revoked_by=CURRENT_USER.get()['id']);w.put('certificate',cid,r)
                w.put('certificate_event',uuid4().hex,{'certificate_id':cid,'status':'revoked','at':stamp(),'author':CURRENT_USER.get()['id']})
            return {'certificate':r}
    @app.get('/api/learning/certificates/{cid}.pdf')
    async def pdf(cid:str,language:Literal['de','en','ru']='de'):
        from .learning_exports import certificate_pdf
        r=certificate(cid)
        return Response(certificate_pdf(r,language),media_type='application/pdf',headers={'Content-Disposition':f'inline; filename="certificate-{cid[:12]}.pdf"'})
