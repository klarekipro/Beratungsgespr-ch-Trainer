"""A28: sanitized shape of captured three-priority response; original remains private."""
import copy
import json
import unittest
from pathlib import Path
import httpx
from tests.dashboard.test_review_evidence_failure import ReviewEvidenceFailure as Base

class PriorityContract(unittest.TestCase):
    setUp=Base.setUp
    client=Base.client
    attempt=Base.attempt
    fixture=Base.fixture
    wire=Base.wire
    provider=Base.provider
    envelope=Base.envelope
    def test_three_priorities_rejected_and_valid_contract_saved_through_handler(self):
        sid,s=self.fixture();endpoint='/api/learning/sessions/'+sid+'/analysis';wire=self.wire(s)
        self.provider(lambda request:httpx.Response(200,json=self.envelope(wire)))
        good=self.a.post(endpoint,json={}).json()['analysis'];self.assertEqual(good['status'],'ready')
        bad=copy.deepcopy(wire);patch=json.loads((Path(__file__).parent/'fixtures/review_three_priorities.json').read_text());bad['recommendation'].update(patch);original=copy.deepcopy(bad)
        def handle(request):
            payload=json.loads(request.content);self.assertIn('never three',payload['input'][0]['content']);self.assertEqual(payload['max_output_tokens'],3500)
            for branch in payload['text']['format']['schema']['properties']['recommendation']['anyOf']:
                field=branch['properties']['priorities'];self.assertEqual(field['minItems'],0);self.assertEqual(field['maxItems'],2);self.assertEqual(field['items']['maxLength'],300)
            return httpx.Response(200,json=self.envelope(bad))
        p=self.provider(handle);result=self.a.post(endpoint,json={'restart':True}).json()['analysis'];self.assertEqual(p.request_count,1);self.assertEqual(result['attempt_status'],'error');self.assertEqual(result['result'],good['result']);d=self.w.get('analysis',sid+':learner')['diagnostics'];self.assertEqual(d['stage'],'recommendation_validation');self.assertEqual(d['validation_reason'],'advice priorities');self.assertEqual(d['validation_path'],'recommendation/priorities');self.assertEqual(bad,original)
        # Independent valid fixture, never a server-side truncation or rewritten real response.
        valid=copy.deepcopy(bad);valid['recommendation']['priorities']=['Bekannte Bedingungen präzise benennen.','Fehlende Angaben ausdrücklich offenlassen.']
        p=self.provider(lambda request:httpx.Response(200,json=self.envelope(valid)))
        result=self.a.post(endpoint,json={'restart':True}).json()['analysis'];self.assertEqual(p.request_count,1);self.assertEqual(result['status'],'ready');self.assertNotIn('attempt_status',result);self.assertEqual(result['result']['recommendation'],{**valid['recommendation'],'evidence':good['result']['recommendation']['evidence']});self.assertEqual(result['result']['recommendation']['action'],'submit_to_mentor')
        self.assertEqual(self.store.get_session(sid),s);self.assertEqual(self.m.get('/api/mentor/reviews').json()['sessions'],[])
    def test_limits_align_for_remaining_bounded_fields(self):
        from backend.app.dashboard import review_service
        _,s=self.fixture();schema=review_service.request_schema(s,self.w.context(s));p=schema['properties']
        for key in ('summary','actual_outcome'):self.assertEqual(p[key]['maxLength'],4000)
        for key in ('strengths','gaps','next_attempt'):self.assertEqual(p[key]['maxItems'],8);self.assertEqual(p[key]['items']['maxLength'],2000)
        self.assertEqual(p['strengths']['minItems'],1);self.assertEqual(p['gaps']['minItems'],0);self.assertEqual(p['next_attempt']['minItems'],0)
        self.assertEqual(p['stages']['minItems'],3);self.assertEqual(p['stages']['maxItems'],3);stage=p['stages']['items']['anyOf'][0]['properties'];self.assertEqual(stage['observation']['maxLength'],3000);self.assertEqual(stage['evidence']['maxItems'],12)
        claim=p['claim_checks']['items']['anyOf'][0]['properties'];self.assertEqual(p['claim_checks']['maxItems'],8);self.assertEqual(claim['statement']['maxLength'],600);self.assertEqual(claim['observation']['maxLength'],1200);self.assertEqual(claim['material_evidence']['maxItems'],3)
        for field in [claim,*[b['properties'] for b in p['recommendation']['anyOf']]]:self.assertEqual(field['evidence']['minItems'],1);self.assertEqual(field['evidence']['maxItems'],4)
        for b in p['recommendation']['anyOf']:self.assertEqual(b['properties']['explanation']['maxLength'],600);self.assertEqual(b['properties']['finding_refs']['maxItems'],4)
