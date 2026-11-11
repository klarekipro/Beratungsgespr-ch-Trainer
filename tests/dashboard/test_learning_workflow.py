"""Three bounded workflow checks. No paid calls; all state is temporary."""
import copy
from contextlib import closing
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app.dashboard.server import create_app
from backend.app.dashboard.auth import COOKIE

class Actor:
    request_count=0
    trace=[]
    async def customer_reply(self,context):
        self.request_count+=1
        return {'speaker_role':'customer','customer_id':context['customer_dossier']['customer_id'],'reply':'Die genaue Ursache kenne ich nicht.'}

class Analyst:
    def __init__(self): self.calls=[];self.fail=False
    async def _request_json(self,instructions,data,*args,**kwargs):
        self.calls.append(copy.deepcopy(data))
        if self.fail:raise RuntimeError('provider offline')
        result={'claim_checks':[],'recommendation':{'action':'submit_to_mentor','explanation':'Ask the mentor to review the open conditions.','priorities':['Clarify conditions in a new training attempt.'],'finding_refs':[{'section':'gaps','index':0}],'evidence':[{'message_id':data['transcript'][0]['message_id'],'quote':data['transcript'][0]['text']}]},'summary':'No order confirmed.','actual_outcome':'A next step is open.','strengths':['Customer need acknowledged.'],'gaps':['Conditions still open.'],'next_attempt':['Clarify conditions.'],'stages':[{'key':key,'status':'evidence_found','observation':'Customer supplied information.','evidence':[{'message_id':data['transcript'][0]['message_id'],'quote':data['transcript'][0]['text']}]} for key in ['needs','capabilities','proposal']]}
        for item in [*result['stages'],result['recommendation']]:
            for evidence in item['evidence']:evidence.pop('quote')
        return result

class WorkflowChecks(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        env=patch.dict(os.environ,{'OPENAI_API_KEY':'test-no-network'});env.start();self.addCleanup(env.stop)
        self.path=Path(self.tmp.name)/'trainer.sqlite3';self.app=create_app(self.path,provider_factory=lambda mode:Actor());self.auth=self.app.state.auth
        self.users=[self.auth.create_user('learning-'+x,x,'test-password-123',role='mentor_admin' if x=='mentor' else 'employee',temporary=False) for x in ['mentor','alice','bob']]
        self.m,self.a,self.b=[self.client(u) for u in self.users]
        self.analyst=Analyst();self.app.state.analysis_provider=self.analyst
    def client(self,u):
        token,csrf=self.auth.issue(u['id']);c=TestClient(self.app,headers={'Origin':'http://testserver','X-CSRF-Token':csrf},cookies={COOKIE:token});c.__enter__();self.addCleanup(c.__exit__,None,None,None);return c
    def attempt(self):
        r=self.a.post('/api/sessions',json={'scenario_id':'oven_no_fit','mode':'simple_actor','client_profile_id':'decisive_oven','training_language':'de'});self.assertEqual(r.status_code,200,r.text)
        session=r.json()['session'];sid=session['id'];turn=self.a.post('/api/sessions/'+sid+'/messages',json={'text':'Welche Ursache ist bekannt?','kind':'message','request_id':'learning-check-'+sid,'version':session['version']});self.assertEqual(turn.status_code,200,turn.text);self.assertEqual(self.a.post('/api/sessions/'+sid+'/finish').status_code,200);return sid
    def test_selected_submission_publication_certificate_and_access(self):
        one,two=self.attempt(),self.attempt();self.assertEqual(len(self.a.get('/api/sessions').json()['sessions']),2)
        # Error is persistent and does not prevent submission/manual review.
        self.analyst.fail=True
        r=self.a.post('/api/learning/sessions/'+one+'/analysis',json={});self.assertEqual(r.json()['analysis']['status'],'error')
        self.assertEqual(self.a.post('/api/learning/sessions/'+one+'/analysis',json={}).json(),r.json());self.assertEqual(len(self.analyst.calls),1)
        for _ in range(2):self.assertEqual(self.a.post('/api/sessions/'+one+'/submit').status_code,200)
        queue=self.m.get('/api/mentor/reviews').json()['sessions'];self.assertEqual([s['id'] for s in queue if s['review_status']=='submitted'],[one])
        review={'note':'Good clarification; price still needs confirmation.','assessment':{'stages':{'needs':'completed','capabilities':'partial','proposal':'partial'},'commercial_outcome':'deferred_decision','company_fit':'uncertain'}}
        self.assertEqual(self.m.post('/api/mentor/reviews/'+two,json=review).status_code,404)
        self.assertEqual(len(self.m.get('/api/mentor/employees/'+self.users[1]['id']+'/sessions').json()['sessions']),1)
        draft={'note':review['note'],'goal':'partly','observations':'Needs clear; installation open.'}
        self.assertEqual(self.m.put('/api/mentor/learning/reviews/'+one+'/draft',json=draft).status_code,200)
        self.assertEqual(self.m.post('/api/mentor/reviews/'+one,json=review).status_code,200)
        other=self.client(self.users[1]);r=other.get('/api/sessions/'+one).json()['session'];self.assertEqual(r['published_review']['note'],review['note']);self.assertNotIn('decision_draft',r)
        self.assertEqual(self.a.post('/api/sessions/'+two+'/submit').status_code,200)  # Private attempts require explicit sharing before inclusion in mentor certificate basis.
        body={'session_id':one,'print_name':'Alice Weber','topic':'Beratung','basis':[one,two],'comment':'Two attempts considered.'}
        r=self.m.post('/api/mentor/learning/certificates/preview',json=body);self.assertEqual(r.status_code,200,r.text);cid=r.json()['certificate']['id']
        self.assertEqual(other.get('/api/learning/certificates/'+cid+'.pdf').status_code,404)
        self.assertEqual(self.m.post('/api/mentor/learning/certificates/'+cid+'/issue',json={'confirm':False}).status_code,422)
        issued=self.m.post('/api/mentor/learning/certificates/'+cid+'/issue',json={'confirm':True}).json();self.assertEqual(self.m.post('/api/mentor/learning/certificates/'+cid+'/issue',json={'confirm':True}).json(),issued)
        for lang in ['de','en','ru']:
            self.assertTrue(other.get('/api/learning/certificates/'+cid+'.pdf?language='+lang).content.startswith(b'%PDF'))
            txt=other.get('/api/sessions/'+one+'/export.txt?language='+lang).text;self.assertIn(review['note'],txt);self.assertNotIn('decision_draft',txt)
            self.assertTrue(other.get('/api/sessions/'+one+'/export.pdf?language='+lang).content.startswith(b'%PDF'))
        self.assertEqual(len(other.get('/api/learning/results').json()['certificates']),1)
        for url in ['/api/sessions/'+one,'/api/sessions/'+one+'/export.json','/api/learning/certificates/'+cid+'.pdf']:
            self.assertEqual(self.b.get(url).status_code,404)
        self.assertEqual(self.b.get('/api/learning/results').json(),{'reviews':[],'certificates':[]})
        self.assertEqual(self.b.post('/api/learning/sessions/'+one+'/analysis',json={}).status_code,404)
        self.assertEqual(self.a.post('/api/learning/sessions/'+one+'/analysis',json={'audience':'mentor'}).status_code,403)
        self.m.post('/api/mentor/learning/certificates/'+cid+'/revoke');self.assertEqual(other.get('/api/learning/results').json()['certificates'][0]['status'],'revoked')
    def test_analysis_privacy_and_cached_reopen(self):
        sid=self.attempt();r=self.a.post('/api/learning/sessions/'+sid+'/analysis',json={});self.assertEqual(r.json()['analysis']['status'],'ready')
        data=self.analyst.calls[0];self.assertNotIn('hidden_dossier',data);self.assertNotIn('facts',data);self.assertNotIn('facts',data['guidance'])
        self.a.get('/api/sessions/'+sid);self.a.get('/api/sessions/'+sid);self.assertEqual(len(self.analyst.calls),1)
        self.a.post('/api/sessions/'+sid+'/submit')
        self.m.post('/api/learning/sessions/'+sid+'/analysis',json={'audience':'mentor'});self.assertIn('hidden_dossier',self.analyst.calls[1])
        self.assertNotIn('mentor_analysis',self.a.get('/api/sessions/'+sid).json()['session'])
    def test_preview_snapshot_and_no_document_rewrites_on_reopen(self):
        root=Path(__file__).resolve().parents[2];payload={'markdown':(root/'materials/a15/company-template.md').read_text(),'csv':(root/'materials/a15/catalogue-template.csv').read_text()}
        sid=self.attempt();before=copy.deepcopy(self.app.state.store.get_session(sid))
        p=self.m.post('/api/mentor/learning/materials/preview',json=payload).json()['preview'];self.assertEqual(p['errors'],[]);self.assertEqual(len(p['products']),18)
        self.assertIsNone(self.a.get('/api/learning/materials').json()['materials'])
        self.m.post('/api/mentor/learning/materials/apply',json={'preview_id':p['id']});new=self.attempt()
        self.assertIsNone(self.a.get('/api/sessions/'+sid).json()['session']['learning_context']['materials'])
        self.assertEqual(self.a.get('/api/sessions/'+new).json()['session']['learning_context']['materials']['id'],p['id'])
        self.assertEqual(self.app.state.store.get_session(sid),before)
        bad=self.m.post('/api/mentor/learning/materials/preview',json={**payload,'csv':'bad'}).json()['preview'];self.assertTrue(bad['errors']);self.assertEqual(self.m.post('/api/mentor/learning/materials/apply',json={'preview_id':bad['id']}).status_code,422)
        with closing(sqlite3.connect(self.path)) as c: docs=c.execute('select * from documents order by kind,id').fetchall()
        create_app(self.path)
        with closing(sqlite3.connect(self.path)) as c:self.assertEqual(docs,c.execute('select * from documents order by kind,id').fetchall())
