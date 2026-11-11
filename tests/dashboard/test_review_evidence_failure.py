"""Observed DE evidence-failure branch; sanitized data and mocked HTTP only."""
import asyncio
import copy
import json
from pathlib import Path
import unittest
import httpx
from backend.app.dashboard import review_service
from backend.app.dashboard.review_provider import ReviewProvider
from tests.dashboard.test_post_review import PostReview as BaseFixture

class ReviewEvidenceFailure(unittest.TestCase):
    setUp=BaseFixture.setUp
    client=BaseFixture.client
    attempt=BaseFixture.attempt
    def fixture(self):
        sid=self.attempt('de');session=self.store.get_session(sid);data=json.loads((Path(__file__).parent/'fixtures/review_de_multiline.json').read_text())
        session['messages']=[{**m,'turn':(i+1)//2,'at':session['created_at']} for i,m in enumerate(data['messages'])];session['scenario_snapshot']['title']='Waschmaschine — Prüfversuch';self.store.save_session(session);return sid,session
    def wire(self,session):
        ids=review_service.message_ids(session);evidence=[{'message_id':ids[5]}]
        return {'summary':'Bedingungen wurden besprochen.','actual_outcome':'Kein Auftrag bestätigt.','strengths':['Bedarf aufgegriffen.'],'gaps':['Bedingungen noch offen.'],'next_attempt':['Im neuen Versuch Bedingungen vor einer Zusage prüfen.'],'stages':[{'key':k,'status':'evidence_found','observation':'Vorläufige Beobachtung.','evidence':copy.deepcopy(evidence)} for k in review_service.STAGES],'claim_checks':[],'recommendation':{'action':'repeat_scenario','explanation':'Offene Bedingungen in einem neuen Training prüfen.','priorities':['Vor Zusagen die gespeicherten Bedingungen prüfen.'],'finding_refs':[{'section':'gaps','index':0}],'evidence':copy.deepcopy(evidence)}}
    def provider(self,handler):
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler));self.addCleanup(lambda:asyncio.run(client.aclose()))
        provider=ReviewProvider('offline-fixture','fixture',client=client);self.app.state.analysis_provider=provider;return provider
    def envelope(self,result,status='completed'):
        return {'status':status,'usage':{'input_tokens':123,'output_tokens':456,'total_tokens':579},'output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(result,ensure_ascii=False)}]}]}
    def test_17_messages_strict_selection_binds_exact_saved_text(self):
        sid,session=self.fixture();wire=self.wire(session);ctx=self.w.context(session)
        canonical=review_service.bind_evidence(wire,session)
        paraphrased=copy.deepcopy(canonical);paraphrased['stages'][0]['evidence'][0]['quote']=session['messages'][5]['text'].replace('\n',' ')
        with self.assertRaises(review_service.ReviewValidationError) as old_branch:review_service.validate(paraphrased,session,ctx)
        self.assertEqual(old_branch.exception.reason,'quote_mismatch')
        # An unsolicited model quote is rejected, not silently normalized or accepted.
        wire_quote=copy.deepcopy(wire);wire_quote['stages'][0]['evidence'][0]['quote']=paraphrased['stages'][0]['evidence'][0]['quote']
        with self.assertRaises(review_service.ReviewValidationError):review_service.bind_evidence(wire_quote,session)
        def handler(request):
            payload=json.loads(request.content);data=json.loads(payload['input'][1]['content']);self.assertEqual(len(data['transcript']),17)
            ev=payload['text']['format']['schema']['$defs']['transcript_reference'];self.assertEqual(ev['required'],['message_id']);self.assertEqual(ev['properties']['message_id']['enum'],review_service.message_ids(session));self.assertEqual(payload['max_output_tokens'],3500)
            return httpx.Response(200,json=self.envelope(wire))
        provider=self.provider(handler);response=self.a.post('/api/learning/sessions/'+sid+'/analysis',json={}).json()['analysis'];self.assertEqual(response['status'],'ready');self.assertEqual(provider.request_count,1)
        self.assertEqual(response['result']['stages'][0]['evidence'][0]['quote'],session['messages'][5]['text']);self.assertNotIn('diagnostics',response)
        stored=self.w.get('analysis',sid+':learner');self.assertEqual(stored['diagnostics']['provider_status'],'completed');self.assertEqual(stored['diagnostics']['usage']['output_tokens'],456)
        self.assertEqual(self.store.get_session(sid),session);self.assertEqual(self.m.get('/api/mentor/reviews').json()['sessions'],[])
        # Later invalid references preserve the successful result and disclose no raw response.
        bad=copy.deepcopy(wire);bad['stages'][0]['evidence'][0]['message_id']='SENSITIVE-invalid-id'
        self.provider(lambda request:httpx.Response(200,json=self.envelope(bad)))
        failed=self.a.post('/api/learning/sessions/'+sid+'/analysis',json={'restart':True}).json()['analysis'];self.assertEqual(failed['status'],'ready');self.assertEqual(failed['attempt_status'],'error');self.assertEqual(failed['result'],response['result']);diagnostics=self.w.get('analysis',sid+':learner')['diagnostics'];self.assertEqual(diagnostics['validation_reason'],'unknown_message_id');self.assertEqual(diagnostics['validation_path'],'stages/0/evidence/0');self.assertNotIn('SENSITIVE',json.dumps(diagnostics))
    def test_diagnostics_separate_transport_parsing_schema_and_incompleteness(self):
        sid,session=self.fixture();wire=self.wire(session)
        cases=[('http',503,None,'provider_http','ai_unavailable'),('schema_rejected',400,{'error':{'message':'SENSITIVE-provider-message','code':'invalid_json_schema','type':'invalid_request_error','param':'text.format.schema'}},'provider_http','ai_request_rejected'),('timeout',None,None,'provider_timeout','ai_timeout'),('envelope',200,'SENSITIVE-bad-json','provider_envelope_parse','ai_invalid_response'),('model_json',200,{'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'SENSITIVE-bad-json'}]}]},'model_json_parse','ai_invalid_response'),('incomplete',200,{'status':'incomplete','incomplete_details':{'reason':'max_output_tokens'},'usage':{'output_tokens':3500}},'provider_incomplete','ai_incomplete'),('schema',200,self.envelope({}),'schema_validation','ai_invalid_response')]
        for name,status,body,stage,category in cases:
            with self.subTest(name=name):
                def handler(request):
                    if name=='timeout':raise httpx.ReadTimeout('SENSITIVE-timeout',request=request)
                    if isinstance(body,str):return httpx.Response(status,text=body)
                    return httpx.Response(status,json=body or {})
                provider=self.provider(handler);public=self.a.post('/api/learning/sessions/'+sid+'/analysis',json={'restart':True}).json()['analysis'];self.assertEqual(public['status'],'error');self.assertNotIn('result',public);self.assertNotIn('diagnostics',public)
                diagnostics=self.w.get('analysis',sid+':learner')['diagnostics'];self.assertEqual(diagnostics['stage'],stage);self.assertEqual(diagnostics['category'],category);self.assertEqual(provider.request_count,1);self.assertNotIn('SENSITIVE',json.dumps(diagnostics))
                if name=='schema_rejected':self.assertEqual(diagnostics['provider_error_code'],'invalid_json_schema')
        self.assertEqual(self.store.get_session(sid),session)
