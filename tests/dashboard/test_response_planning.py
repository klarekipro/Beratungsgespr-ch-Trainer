"""A06 offline contracts: taxonomy, ownership, bounded repair and transaction safety.

Synthetic network results test the pipeline; they do not prove live model quality.
"""
import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import httpx
from fastapi.testclient import TestClient
from backend.app.dashboard.response_planning import normalize_targets, build_response_plan
from backend.app.dashboard.customer_actor import actor_context, validate_review, ActorContractError
from backend.app.dashboard.engine import process_turn
from backend.app.dashboard.providers import OpenAIProvider, ProviderError
from backend.app.dashboard.server import create_app
from test_engine import new_session, decision, response_body


def planned_context(target='maintenance_history', fact_ids=None, text='Когда был последний техосмотр?'):
    s=new_session(2,mode='openai')
    d=decision(act='question',fact_ids=fact_ids or [], source_quote=text)
    d['question_targets']=[{'target':target,'quote':text,'fact_ids':fact_ids or []}]
    facts=[f for f in s['scenario_snapshot']['facts'] if f['id'] in (fact_ids or [])]
    c={'language':'ru','customer_name':s['scenario_snapshot']['customer_name'],
       'opening':s['scenario_snapshot']['opening'],'learner_text':text,
       'visible_history':copy.deepcopy(s['messages']),'response_intent':'answer_question',
       'authorized_facts':[{k:f[k] for k in ['id','label','value','status']} for f in facts],
       'must_address_fact_ids':fact_ids or []}
    c['response_plan']=build_response_plan(s,d,text,c['response_intent'],c['authorized_facts'])
    return actor_context(c)


def candidate(c, reply='Точную дату последнего техосмотра сейчас назвать не могу.'):
    return {'reply':reply,'used_fact_ids':c['must_address_fact_ids'], 'scenario_gap':False,
            'speaker_role':'customer','customer_id':c['response_plan']['customer_id'],
            'addressed_targets':[t['id'] for t in c['response_plan']['question_targets']]}


def review(c, **changes):
    r={'grounded':True,'in_role':True,'consistent_with_intent':True,
       'addressed_fact_ids':c['must_address_fact_ids'],'unsupported_quotes':[],
       'role_ownership':True,'question_relevance':True,'conversation_consistency':True,
       'stage_consistency':True,'addressed_targets':[t['id'] for t in c['response_plan']['question_targets']],
       'observed_ownership':{'equipment_owner':'customer','repair_need':'not_mentioned','company_services':'not_mentioned'}}
    r.update(changes);return r


class ResponsePlanningTests(unittest.TestCase):
    def test_inspection_is_not_future_timing_even_when_director_maps_it_wrong(self):
        text='Какой номер и мощность? Когда был последний техосмотр?'
        d=decision(act='question',fact_ids=['identification','timing'],source_quote=text)
        d['question_targets']=[{'target':'equipment_identification','quote':'номер и мощность','fact_ids':['identification']},
            {'target':'visit_availability','quote':'Когда был последний техосмотр','fact_ids':['timing']}]
        facts={f['id']:f for f in new_session(2)['scenario_snapshot']['facts']}
        targets=normalize_targets(d,text,facts)
        self.assertEqual({t['target'] for t in targets},{'equipment_identification','maintenance_history'})
        self.assertNotIn('timing',[i for t in targets for i in t['fact_ids']])
        self.assertEqual(next(t['fact_ids'] for t in targets if t['target']=='maintenance_history'),[])

    def test_visit_availability_preserves_authored_timing(self):
        c=planned_context('visit_availability',['timing'],'Когда сможете принять мастера?')
        p=c['response_plan']
        self.assertEqual(p['question_targets'][0]['fact_ids'],['timing'])
        self.assertEqual(p['unknown_targets'],[])

    def test_absent_inspection_is_unconfirmed_not_invented_customer_ignorance(self):
        p=planned_context()['response_plan']
        self.assertEqual(p['unknown_targets'],[{'target_id':'q1','topic':'maintenance_history','reason':'not_provided'}])
        self.assertEqual(p['authorized_fact_ids'],[])
        self.assertFalse(p['stage_policy']['may_book_appointment'])

    def test_wrong_answer_target_cannot_be_approved_by_all_true_verifier(self):
        c=planned_context()
        with self.assertRaises(ActorContractError) as e:
            validate_review(review(c),c,'Могу ждать до двух недель.')
        self.assertEqual(e.exception.code,'ai_actor_wrong_target')

    def test_need_inversion_is_blocked_despite_all_true_verifier(self):
        c=planned_context('other',[], 'Мы как раз такая компания')
        for reply in ['Вам нужна помощь с печью.', 'Значит, вы ищете новую сервисную компанию.',
                      'Sie benötigen Hilfe mit dem Ofen.']:
            with self.subTest(reply=reply),self.assertRaises(ActorContractError):
                validate_review(review(c),c,reply)

    def test_normal_customer_speech_is_not_blocked(self):
        c=planned_context('other',[], 'Мы как раз такая компания')
        for reply in ['А вы можете помочь с печью?',
                      'Вы сказали: «Вам нужна помощь с печью». Да, именно так.', 'Können Sie mir mit dem Ofen helfen?',
                      'Мы пока не приняли решение.', 'Я ищу специализированную фирму.',
                      'Точную дату последнего осмотра сейчас назвать не могу.']:
            with self.subTest(reply=reply): validate_review(review(c),c,reply)

    def test_independent_observed_ownership_must_match_customer_not_plan_copy(self):
        c=planned_context()
        r=review(c);r['observed_ownership']['equipment_owner']='seller'
        with self.assertRaises(ActorContractError):validate_review(r,c,'Дата сейчас не подтверждена.')

    def test_relevance_and_consistency_rejections_are_distinct_from_employee_error(self):
        c=planned_context()
        for key in ['question_relevance','conversation_consistency','stage_consistency','role_ownership']:
            with self.subTest(key=key),self.assertRaises(ActorContractError):
                validate_review(review(c,**{key:False}),c,'Не могу сейчас назвать дату осмотра.')

    def test_tampered_plan_cannot_add_company_policy_or_authorized_facts(self):
        c=planned_context();c['response_plan']['fact_ownership']['company_services']='customer'
        with self.assertRaises(ActorContractError):actor_context(c)


class BoundedRegenerationTests(unittest.IsolatedAsyncioTestCase):
    async def run_provider(self, outputs, c):
        requests=[]
        async def handler(request):
            requests.append(json.loads(request.content))
            return httpx.Response(200,json=response_body(outputs[len(requests)-1]))
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider=OpenAIProvider('fake','configured-model',client=client)
            result=await provider.respond(c)
        return result,provider,requests

    async def test_one_semantic_regeneration_then_success_counts_all_four_calls(self):
        c=planned_context();bad=candidate(c);good=candidate(c)
        result,p,requests=await self.run_provider([bad,review(c,question_relevance=False),good,review(c)],c)
        self.assertEqual(p.request_count,4)
        self.assertEqual(result['reply'],good['reply'])
        data=json.loads(requests[2]['input'][1]['content'])
        self.assertEqual(data['generation_feedback']['error_type'],'ai_actor_semantic_rejection')
        self.assertIn('question_relevance',data['generation_feedback']['failed_checks'])
        self.assertNotIn('generation_feedback',json.loads(requests[3]['input'][1]['content'])['context'])

    async def test_local_role_failure_regenerates_before_verifier(self):
        c=planned_context()
        result,p,requests=await self.run_provider([candidate(c,'Вам нужна помощь с печью.'),candidate(c),review(c)],c)
        self.assertEqual(p.request_count,3)
        self.assertNotIn('Вам нужна помощь',result['reply'])
        self.assertEqual([r['text']['format']['name'] for r in requests],['customer_reply','customer_reply','customer_reply_review'])

    async def test_second_semantic_failure_stops_without_third_generation(self):
        c=planned_context();outputs=[candidate(c),review(c,grounded=False),candidate(c),review(c,grounded=False)]
        calls=[]
        async def handler(request):
            calls.append(request);return httpx.Response(200,json=response_body(outputs[len(calls)-1]))
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            p=OpenAIProvider('fake','configured-model',client=client)
            with self.assertRaises(ProviderError):await p.respond(c)
        self.assertEqual(len(calls),4)
        self.assertEqual(p.request_count,4)

    async def test_network_error_does_not_regenerate(self):
        calls=[]
        async def handler(request):
            calls.append(request);return httpx.Response(429,json={'error':{'message':'PRIVATE'}})
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            p=OpenAIProvider('fake','configured-model',client=client)
            with self.assertRaises(ProviderError) as e:await p.respond(planned_context())
        self.assertEqual(e.exception.code,'ai_rate_limited');self.assertEqual(len(calls),1)


class PlannedTurnHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.env=patch.dict(os.environ,{'OPENAI_API_KEY':'fake','OPENAI_MODEL':'fake',
            'TRAINER_AUDIT_DIR':str(Path(self.temp.name)/'audit')});self.env.start();self.addCleanup(self.env.stop)

    def test_three_employee_mistakes_are_valid_input_with_natural_nonacceptance(self):
        for text in ['Мы готовы починить вашу печь','Давайте запишем мастера на вторник','Ремонт стоит примерно 15 000 евро']:
            captured=[]
            class Provider:
                request_count=0
                async def interpret(self,session,text,kind):
                    self.request_count+=1
                    return {**decision(act='proposal',source_quote=text), 'question_targets':[]}
                async def respond(self,context):
                    self.request_count+=2;captured.append(context)
                    return {'reply':'Прежде чем соглашаться, хочу понять, как вы сможете помочь.', 'verified_fact_ids':[]}
            p=Provider()
            with TestClient(create_app(Path(self.temp.name)/'data.sqlite3',provider_factory=lambda mode:p)) as client:
                s=client.post('/api/sessions',json={'scenario_id':'oven_no_fit','mode':'openai'}).json()['session']
                r=client.post(f"/api/sessions/{s['id']}/messages",json={'text':text,'version':1,'request_id':'employee_mistake','kind':'message'})
                self.assertEqual(r.status_code,200,r.text)
                self.assertEqual(r.json()['session']['phase'],'needs')
                self.assertFalse(captured[0]['response_plan']['stage_policy']['may_accept_offer'])
                self.assertNotIn('company',captured[0])

    def test_five_real_requests_are_counted_and_audit_is_separate_from_consultation(self):
        calls=[]
        text='Когда был последний техосмотр?'
        c=planned_context()
        outputs=[{**decision(act='question',source_quote=text), 'question_targets':[{'target':'maintenance_history','quote':text,'fact_ids':[]}]},
                 candidate(c),review(c,question_relevance=False),candidate(c),review(c)]
        # Session-specific identity must be supplied by the actual actor request.
        async def handler(request):
            payload=json.loads(request.content);calls.append(payload);out=copy.deepcopy(outputs[len(calls)-1])
            if payload['text']['format']['name']=='customer_reply':
                data=json.loads(payload['input'][1]['content']);out['customer_id']=data['response_plan']['customer_id']
            return httpx.Response(200,json=response_body(out))
        with httpx.Client():
            provider=OpenAIProvider('fake','configured-model',client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
            with TestClient(create_app(Path(self.temp.name)/'five.sqlite3',provider_factory=lambda mode:provider)) as client:
                s=client.post('/api/sessions',json={'scenario_id':'oven_no_fit','mode':'openai'}).json()['session']
                r=client.post(f"/api/sessions/{s['id']}/messages",json={'text':text,'kind':'message','request_id':'five_requests','version':1})
                self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['session']['api_requests'],5)
                self.assertEqual(r.json()['session']['natural_customer_turns'],1)
                self.assertEqual(client.get('/api/status').json()['ai']['max_requests_per_turn'],5)
        files=list((Path(self.temp.name)/'audit').glob('*.json'));self.assertEqual(len(files),1)
        audit=json.loads(files[0].read_text());self.assertEqual(audit['api_requests'],5)
        self.assertTrue(any(t.get('kind')=='response_plan' for t in audit['trace']))
        self.assertEqual(files[0].stat().st_mode & 0o777,0o600)


    def test_repeated_actor_failure_keeps_state_and_records_system_not_learner_error(self):
        calls=[]
        async def handler(request):
            payload=json.loads(request.content);calls.append(payload)
            if len(calls)==1:
                out={**decision(act='question',source_quote='Когда был последний техосмотр?'),
                     'question_targets':[{'target':'maintenance_history','quote':'последний техосмотр','fact_ids':[]}]}
            else:
                data=json.loads(payload['input'][1]['content'])
                c=planned_context();c['response_plan']['customer_id']=data['response_plan']['customer_id']
                out=candidate(c,'Вам нужна помощь с печью.')
            return httpx.Response(200,json=response_body(out))
        provider=OpenAIProvider('fake','configured-model',client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
        app=create_app(Path(self.temp.name)/'reject.sqlite3',provider_factory=lambda mode:provider)
        with TestClient(app) as client:
            before=client.post('/api/sessions',json={'scenario_id':'oven_no_fit','mode':'openai'}).json()['session']
            raw_before=app.state.store.get_session(before['id'])
            r=client.post(f"/api/sessions/{before['id']}/messages",json={
                'text':'Когда был последний техосмотр?','kind':'message','request_id':'repeat_actor_failure','version':1})
            self.assertEqual(r.status_code,502,r.text)
            after=app.state.store.get_session(before['id'])
            for key in ['messages','state','version','receipts','updated_at']:
                self.assertEqual(raw_before[key],after[key])
            self.assertEqual(after['live_requests'],3)
            self.assertEqual(after['system_issues'][-1]['type'],'actor_response_error')
            self.assertEqual(len(calls),3)
            self.assertNotIn('Вам нужна помощь',json.dumps(after,ensure_ascii=False))
