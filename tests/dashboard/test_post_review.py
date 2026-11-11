"""Bounded private-review contract checks. Synthetic transcript, no paid provider."""
import asyncio
import copy
import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app.dashboard.server import create_app
from backend.app.dashboard.auth import COOKIE
from backend.app.dashboard import review_service
from backend.app.dashboard.providers import OpenAIProvider,ProviderError

class Analyst:
    request_count=0
    def __init__(self):self.calls=[];self.bad=False;self.slow=False;self.entered=threading.Event()
    async def _request_json(self,instructions,data,*args,**kwargs):
        self.calls.append(copy.deepcopy(data));self.entered.set()
        if self.slow:await asyncio.sleep(.2)
        refs=data['transcript'];result={'summary':'Уточнены потребности.','actual_outcome':'Следующий шаг обсуждается, заказ не подтверждён.','strengths':['Учтена сообщённая клиентом потребность.'],'gaps':['Срок требует уточнения.'],'next_attempt':['Подтвердить следующий шаг.'],'stages':[{'key':key,'status':'evidence_found','observation':'Предварительное наблюдение.','evidence':[{'message_id':refs[i]['message_id'],'quote':refs[i]['text']} for i in [0,5]]} for key in review_service.STAGES]}
        result['claim_checks']=[]
        result['recommendation']={'action':'repeat_scenario','explanation':'Practise clarifying the open conditions in a new training attempt.','priorities':['Clarify conditions before making a promise.'],'finding_refs':[{'section':'gaps','index':0}],'evidence':[{'message_id':refs[0]['message_id'],'quote':refs[0]['text']}]}
        if self.bad:result['stages'][0]['evidence'][0]['quote']='Invented quote'
        return result
class PostReview(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        env=patch.dict('os.environ',{'OPENAI_API_KEY':'offline-fixture','TRAINER_AUDIT_DIR':''});env.start();self.addCleanup(env.stop)
        self.app=create_app(Path(self.tmp.name)/'copy.sqlite3');self.store=self.app.state.store;self.auth=self.app.state.auth;self.w=self.app.state.workflow
        self.users=[self.auth.create_user('review-'+name,name,'Synthetic password 42',role='mentor_admin' if name=='mentor' else 'employee',temporary=False) for name in ['mentor','alice','bob']]
        self.m,self.a,self.b=[self.client(u) for u in self.users];self.analyst=Analyst();self.app.state.analysis_provider=self.analyst
    def client(self,u):
        token,csrf=self.auth.issue(u['id']);c=TestClient(self.app,headers={'Origin':'http://testserver','X-CSRF-Token':csrf},cookies={COOKIE:token});c.__enter__();self.addCleanup(c.__exit__,None,None,None);return c
    def attempt(self,language='ru'):
        r=self.a.post('/api/sessions',json={'scenario_id':'oven_no_fit','mode':'simple_actor','client_profile_id':'decisive_oven','training_language':language});self.assertEqual(r.status_code,200,r.text);sid=r.json()['session']['id'];s=self.store.get_session(sid)
        for i in range(1,51):s['messages'].append({'role':'learner' if i%2 else 'customer','text':f'Message {i}: Mixed original текст unverändert.','turn':(i+1)//2,'at':s['created_at']})
        self.store.save_session(s);self.a.post('/api/sessions/'+sid+'/finish');return sid
    def test_private_finish_failure_explicit_submission_and_publication(self):
        sid=self.attempt();before=copy.deepcopy(self.store.get_session(sid));snapshot=copy.deepcopy(self.w.get('snapshot',sid));self.analyst.bad=True
        r=self.a.post('/api/learning/sessions/'+sid+'/analysis',json={});self.assertEqual(r.json()['analysis']['status'],'error');self.assertEqual(r.json()['analysis']['error'],'ai_invalid_response');self.assertNotIn('diagnostics',r.json()['analysis']);self.assertNotIn('completed_at',r.json()['analysis'])
        self.assertEqual(self.store.get_session(sid),before);self.assertEqual(self.w.get('snapshot',sid),snapshot)
        for endpoint in ['/api/mentor/reviews','/api/sessions','/api/mentor/employees/'+self.users[1]['id']+'/sessions']:self.assertEqual(self.m.get(endpoint).json()['sessions'],[])
        self.assertEqual(self.m.get('/api/mentor/overview').json()['pending'],0);self.assertEqual(self.m.get('/api/mentor/reviews/'+sid).status_code,404);self.assertEqual(self.m.get('/api/sessions/'+sid).status_code,404)
        for _ in range(2):self.assertEqual(self.a.post('/api/sessions/'+sid+'/submit').status_code,200)
        self.assertEqual(len(self.m.get('/api/mentor/reviews').json()['sessions']),1);self.assertEqual(self.m.get('/api/mentor/overview').json()['pending'],1)
        self.assertEqual(self.m.post('/api/mentor/reviews/'+sid,json={'note':'Reviewed once, feedback for Alice.'}).status_code,200)
        self.assertEqual(self.a.get('/api/sessions/'+sid).json()['session']['published_review']['note'],'Reviewed once, feedback for Alice.')
        self.assertEqual(self.b.get('/api/sessions/'+sid).status_code,404);self.assertEqual(self.b.get('/api/learning/results').json()['reviews'],[])
        self.assertEqual(self.store.get_session(sid)['messages'],before['messages']);self.assertEqual(len(before['messages']),51)
    def test_valid_evidence_retry_preserves_success_and_deduplicates(self):
        sid=self.attempt();endpoint='/api/learning/sessions/'+sid+'/analysis';self.analyst.slow=True
        with ThreadPoolExecutor(2) as pool:
            first=pool.submit(self.a.post,endpoint,json={'restart':True});self.assertTrue(self.analyst.entered.wait(2));second=pool.submit(self.a.post,endpoint,json={'restart':True});one=first.result();two=second.result()
        self.assertEqual(one.json(),two.json());self.assertEqual(len(self.analyst.calls),1);self.assertEqual(one.json()['analysis']['status'],'ready')
        result=one.json()['analysis']['result'];stored=self.store.get_session(sid);ids=review_service.message_ids(stored);self.assertEqual(result['stages'][0]['evidence'][1]['message_id'],ids[5])
        self.analyst.slow=False;self.analyst.bad=True;failed=self.a.post(endpoint,json={'restart':True}).json()['analysis'];self.assertEqual(failed['status'],'ready');self.assertEqual(failed['attempt_status'],'error');self.assertEqual(failed['result'],result)
        for _ in range(2):self.a.get('/api/sessions/'+sid)
        self.assertEqual(len(self.analyst.calls),2);self.assertEqual(self.store.get_session(sid)['review_status'],'not_submitted')
        invalid=copy.deepcopy(result);invalid.pop('sections');invalid['stages'][0]['evidence'][0]['message_id']='nonexistent'
        with self.assertRaises(ValueError):review_service.validate(invalid,stored)
    def test_compact_snapshot_context_and_local_guard_without_network(self):
        sid=self.attempt();s=self.store.get_session(sid);ctx=self.w.context(s);ctx['materials']={'id':'old-snapshot','products':[{'id':'old-item','name':'Saved item','price_eur':7}],'translations':{'de':{'copied':'X'*150000}},'markdown':'X'*150000}
        old={'guidance':ctx,'transcript':s['messages']};provider=OpenAIProvider('offline-fixture','fixture')
        with self.assertRaises(ProviderError) as error:asyncio.run(provider._request_json('fixture',old,{},'fixture'))
        self.assertEqual(error.exception.code,'ai_context_limit');self.assertEqual(provider.request_count,0)
        data=review_service.payload(s,ctx,'learner','ru');self.assertLess(len(json.dumps(data,ensure_ascii=False)),65000);self.assertEqual(data['saved_materials']['products'][0]['price_eur'],7);self.assertNotIn('translations',json.dumps(data));self.assertNotIn('hidden_dossier',data);self.assertEqual(len(data['transcript']),51)
        self.assertEqual(review_service.localized('DE: Ziel EN: Goal RU: Цель','ru'),'Цель')
    def test_exports_training_language_independent_of_ui(self):
        for language,label in [('ru','Разбор консультации'),('de','Gesprächsauswertung'),('en','Consultation review')]:
            sid=self.attempt(language);response=self.a.get('/api/sessions/'+sid+'/export.txt?language='+('en' if language!='en' else 'ru'));self.assertTrue(response.text.startswith(label));self.assertIn('Message 50: Mixed original текст unverändert.',response.text)
            self.assertEqual(len(self.a.get('/api/sessions/'+sid+'/export.json').json()['messages']),51)
        self.assertTrue(self.a.get('/api/sessions/'+sid+'/export.pdf?language=ru').content.startswith(b'%PDF'))
