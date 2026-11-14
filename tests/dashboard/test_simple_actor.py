"""Five technical checks, not a psychological quality evaluation. No paid calls."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import httpx
from fastapi.testclient import TestClient
from backend.app.dashboard.client_profiles import load_profiles, ProfileField
from backend.app.dashboard.server import create_app
from backend.app.dashboard.simple_actor import SimpleActorProvider
from backend.app.dashboard.seeds import SEED_SCENARIOS

MENTOR={'X-Workspace-Role':'mentor'}

class StubActor:
    def __init__(self):self.request_count=0;self.trace=[];self.reply='Причину поломки я пока не знаю.';self.context=None
    async def customer_reply(self,context):
        self.request_count+=1;self.context=copy.deepcopy(context)
        return {'speaker_role':'customer','customer_id':context['customer_dossier']['customer_id'],'reply':self.reply}

class SimpleActorSmoke(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.env=patch.dict(os.environ,{'OPENAI_API_KEY':'synthetic-not-a-real-key','TRAINER_AUDIT_DIR':''});self.env.start();self.addCleanup(self.env.stop)
        self.actor=StubActor();self.app=create_app(Path(self.temp.name)/'db.sqlite3',provider_factory=lambda mode:self.actor)
        self.client=TestClient(self.app);self.client.__enter__();self.addCleanup(self.client.__exit__,None,None,None)
    def start(self,profile='analytical_oven'):
        r=self.client.post('/api/sessions',json={'scenario_id':'oven_no_fit','mode':'simple_actor','client_profile_id':profile});self.assertEqual(r.status_code,200,r.text);return r.json()['session']
    def send(self,s,text):
        return self.client.post('/api/sessions/'+s['id']+'/messages',json={'text':text,'kind':'message','version':s['version'],'request_id':'test-request-123'})
    def test_profiles_preserve_source_and_unknown_is_not_missing(self):
        profiles=load_profiles();self.assertEqual(len(profiles),5)
        self.assertEqual(profiles[0]['scenario']['source_scenario'],next(x for x in SEED_SCENARIOS if x['id']=='oven_no_fit'))
        self.assertNotEqual(ProfileField(status='customer_unknown').model_dump(),ProfileField(status='author_missing').model_dump())
        for p in profiles:self.assertEqual(p['persona']['approval'],'technical_draft')
    def test_selection_one_actor_context_and_no_model_learning_credit(self):
        s=self.start();self.assertEqual(s['client_profile']['persona_id'],'analytical')
        before=copy.deepcopy(self.app.state.store.get_session(s['id'])['state']);r=self.send(s,'А причину знаете?');self.assertEqual(r.status_code,200,r.text)
        after=r.json()['session'];self.assertEqual(after['api_requests'],1);self.assertEqual(after['natural_customer_turns'],1)
        own=self.actor.context['customer_dossier'];self.assertNotIn('company_snapshot',own)
        alltext=json.dumps(self.actor.context,ensure_ascii=False);self.assertNotIn('services',alltext);self.assertNotIn('rubric',alltext)
        self.assertEqual(before,self.app.state.store.get_session(s['id'])['state'])
        self.assertEqual(after['phase'],'needs');self.assertEqual(own['persona']['id'],'analytical')
    def test_obvious_critical_errors_block_without_saving_or_progress(self):
        for text in ['Мы ремонтируем только бытовые электрические печи.','Мой бюджет 15 000 евро.','Я согласен на ремонт.','Моя печь электрическая.','Меня зовут Пётр.','Мощность печи 150 кВт.']:
            s=self.start();before=self.app.state.store.get_session(s['id']);self.actor.reply=text
            r=self.send(s,'Мы готовы починить вашу печь');self.assertEqual(r.status_code,502,r.text)
            after=self.app.state.store.get_session(s['id'])
            for k in ['state','messages','version','receipts']:self.assertEqual(before[k],after[k])
            self.assertEqual(after['live_requests'],1);self.assertTrue(after['system_issues'])
    def test_single_responses_request_no_storage_or_verifier(self):
        captured=[]
        def transport(request):
            self.assertEqual(str(request.url),'https://api.openai.com/v1/responses');captured.append(json.loads(request.content))
            return httpx.Response(200,json={'status':'completed','usage':{'input_tokens':20,'output_tokens':10,'total_tokens':30},'output':[{'type':'message','content':[{'type':'output_text','text':json.dumps({'speaker_role':'customer','customer_id':'cautious_oven','reply':'Я пока не знаю причину.'})}]}]})
        import asyncio
        async def call():
            async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as c:
                provider=SimpleActorProvider('synthetic-key','gpt-4.1-mini-2025-04-14',client=c)
                await provider.customer_reply({'customer_dossier':{'customer_id':'cautious_oven'},'history':[],'current_employee_utterance':'Причина?'})
                self.assertEqual(provider.request_count,1)
        asyncio.run(call());self.assertEqual(len(captured),1);self.assertIs(captured[0]['store'],False)
        self.assertNotIn('previous_response_id',captured[0]);self.assertEqual(captured[0]['text']['format']['name'],'simple_customer_reply')
    def test_save_reopen_export_and_ordered_manual_review(self):
        s=self.start();r=self.send(s,'Причина?');self.assertEqual(r.status_code,200)
        s=r.json()['session'];sid=s['id'];self.assertEqual(self.client.get('/api/sessions/'+sid).json()['session'],s)
        self.client.post('/api/sessions/'+sid+'/finish');self.client.post('/api/sessions/'+sid+'/submit')
        path='/api/mentor/reviews/'+sid
        self.assertEqual(self.client.post(path,headers=MENTOR,json={'note':'Проверено','needs_confirmed':False,'capabilities_confirmed':True}).status_code,422)
        reviewed=self.client.post(path,headers=MENTOR,json={'note':'Содержательный разбор владельца','needs_confirmed':True,'capabilities_confirmed':True,'outcome':'no_fit'})
        self.assertEqual(reviewed.status_code,200);self.assertEqual(reviewed.json()['session']['phase'],'completed')
        for ext in ['txt','json','pdf']:
            r=self.client.get('/api/sessions/'+sid+'/export.'+ext);self.assertEqual(r.status_code,200)
            if ext=='pdf':self.assertTrue(r.content.startswith(b'%PDF'))
            if ext=='txt':self.assertIn('simple_actor',r.text);self.assertIn('Причину поломки я пока не знаю.',r.text)
