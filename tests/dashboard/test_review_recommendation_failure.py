"""A27: sanitized reproduction of the observed reason, not the lost real response."""
import copy
import json
import unittest
from pathlib import Path
import httpx
from tests.dashboard.test_review_evidence_failure import ReviewEvidenceFailure as Base

class RecommendationFailure(unittest.TestCase):
    setUp=Base.setUp
    client=Base.client
    attempt=Base.attempt
    fixture=Base.fixture
    wire=Base.wire
    provider=Base.provider
    envelope=Base.envelope
    def rejected(self,s):
        patch=json.loads((Path(__file__).parent/'fixtures/review_repeat_without_gap.json').read_text())
        from backend.app.dashboard.review_service import message_ids
        patch['recommendation']['evidence'][0]['message_id']=message_ids(s)[5]
        wire=self.wire(s);wire.update(patch);return wire
    def test_reproduces_recommendation_rejection_through_pipeline(self):
        sid,s=self.fixture();endpoint='/api/learning/sessions/'+sid+'/analysis'
        self.provider(lambda request:httpx.Response(200,json=self.envelope(self.wire(s))))
        good=self.a.post(endpoint,json={}).json()['analysis'];self.assertEqual(good['status'],'ready')
        bad=self.rejected(s);p=self.provider(lambda request:httpx.Response(200,json=self.envelope(bad)))
        failed=self.a.post(endpoint,json={'restart':True}).json()['analysis'];self.assertEqual(p.request_count,1);self.assertEqual(failed['attempt_status'],'error');self.assertEqual(failed['result'],good['result'])
        diagnostic=self.w.get('analysis',sid+':learner')['diagnostics'];self.assertEqual(diagnostic['validation_reason'],'repeat requires demonstrated gap');self.assertEqual(diagnostic['stage'],'recommendation_validation');self.assertEqual(diagnostic['validation_path'],'recommendation/finding_refs')
        from backend.app.dashboard import review_diagnostics,review_service
        self.assertEqual(diagnostic['capture_status'],'retained');self.assertNotIn('capture_id',failed)
        bundle=self.store.path.parent/'review_failures'/(diagnostic['capture_id']+'.json')
        saved=json.loads(bundle.read_text());self.assertEqual(saved['wire_result'],bad);self.assertEqual(saved['session'],s);self.assertEqual(saved['payload']['transcript'][5]['text'],s['messages'][5]['text']);self.assertNotIn('offline-fixture',bundle.read_text());self.assertEqual(bundle.stat().st_mode&0o777,0o600);self.assertEqual(bundle.parent.stat().st_mode&0o777,0o700)
        with self.assertRaises(review_service.ReviewValidationError) as replayed:review_diagnostics.replay(bundle)
        self.assertEqual(replayed.exception.reason,diagnostic['validation_reason']);self.assertEqual(replayed.exception.path,diagnostic['validation_path'])
        schema=saved['schema']['properties']['recommendation'];self.assertEqual(len(schema['anyOf']),2)
        repeat,other=schema['anyOf'];self.assertEqual(repeat['properties']['action']['enum'],['repeat_scenario']);self.assertEqual(repeat['properties']['finding_refs']['items']['properties']['section']['enum'],['gaps']);self.assertEqual(repeat['properties']['finding_refs']['minItems'],1);self.assertNotIn('repeat_scenario',other['properties']['action']['enum'])
        self.assertEqual(self.store.get_session(sid),s);self.assertEqual(self.m.get('/api/mentor/reviews').json()['sessions'],[])

    def test_valid_repeat_and_nonrepeat_pass_single_call_pipeline(self):
        sid,s=self.fixture();wire=self.wire(s);endpoint='/api/learning/sessions/'+sid+'/analysis'
        p=self.provider(lambda request:httpx.Response(200,json=self.envelope(wire)))
        self.assertEqual(self.a.post(endpoint,json={}).json()['analysis']['status'],'ready');self.assertEqual(p.request_count,1)
        wire=self.rejected(s);wire['recommendation']['action']='submit_to_mentor'
        p=self.provider(lambda request:httpx.Response(200,json=self.envelope(wire)))
        result=self.a.post(endpoint,json={'restart':True}).json()['analysis'];self.assertEqual(result['status'],'ready');self.assertNotIn('attempt_status',result);self.assertEqual(p.request_count,1)
        self.assertFalse((self.store.path.parent/'review_failures').exists());self.assertEqual(self.store.get_session(sid),s)

    def test_failure_capture_bounds_and_redaction(self):
        from backend.app.dashboard.review_diagnostics import retain_failure,MAX_BYTES,MAX_FILES
        s={'id':'synthetic','messages':[]};folder=self.store.path.parent/'review_failures'
        for _ in range(MAX_FILES+1):
            capture=retain_failure(self.store.path,s,{},'instruction',{}, {},{'summary':'secret-sentinel'},None,{},'secret-sentinel')
            self.assertEqual(capture['capture_status'],'retained')
        self.assertEqual(len(list(folder.glob('*.json'))),MAX_FILES)
        for file in folder.glob('*.json'):self.assertNotIn('secret-sentinel',file.read_text());self.assertIn('[REDACTED]',file.read_text())
        large=retain_failure(self.store.path,s,{},'',{}, {},{'summary':'x'*MAX_BYTES},None,{})
        self.assertEqual(large['capture_status'],'oversize');self.assertEqual(len(list(folder.glob('*.json'))),MAX_FILES)

    def test_model_json_failure_is_captured_without_http_headers(self):
        sid,s=self.fixture()
        body={'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'not-json offline-fixture'}]}]}
        self.provider(lambda request:httpx.Response(200,json=body))
        failed=self.a.post('/api/learning/sessions/'+sid+'/analysis',json={}).json()['analysis'];self.assertEqual(failed['status'],'error');self.assertNotIn('diagnostics',failed)
        d=self.w.get('analysis',sid+':learner')['diagnostics'];self.assertEqual(d['stage'],'model_json_parse');self.assertEqual(d['capture_status'],'retained')
        file=self.store.path.parent/'review_failures'/(d['capture_id']+'.json');bundle=json.loads(file.read_text());self.assertIsNone(bundle['wire_result']);self.assertEqual(bundle['model_text'],'not-json [REDACTED]');self.assertNotIn('Authorization',file.read_text());self.assertEqual(bundle['diagnostics']['request_started_at'],d['request_started_at'])
