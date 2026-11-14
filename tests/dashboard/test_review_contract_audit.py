"""A29: sanitized captured shape, full handler and legacy historical-source presentation."""
import copy
import json
import unittest
from pathlib import Path
import httpx
from backend.app.dashboard import review_service,review_contract
from tests.dashboard.test_review_evidence_failure import ReviewEvidenceFailure as Base

class ContractAudit(unittest.TestCase):
    setUp=Base.setUp
    client=Base.client
    attempt=Base.attempt
    fixture=Base.fixture
    wire=Base.wire
    provider=Base.provider
    envelope=Base.envelope
    def test_captured_shape_rejected_and_proper_policy_evidence_saved(self):
        sid,s=self.fixture();endpoint='/api/learning/sessions/'+sid+'/analysis';s['company_snapshot']['limitations']='Termine müssen gesondert bestätigt werden.';self.store.save_session(s)
        wire=self.wire(s);self.provider(lambda r:httpx.Response(200,json=self.envelope(wire)));good=self.a.post(endpoint,json={}).json()['analysis'];self.assertEqual(good['status'],'ready')
        bad=copy.deepcopy(wire);claim=json.loads((Path(__file__).parent/'fixtures/review_policy_missing_source.json').read_text());claim['evidence']=copy.deepcopy(wire['stages'][0]['evidence']);bad['claim_checks']=[copy.deepcopy(claim) for _ in range(3)]
        # First two claims are communication observations; third reproduces the captured failure.
        for c in bad['claim_checks'][:2]:c['verdict']='communicated'
        def handler(request):
            p=json.loads(request.content);self.assertIs(p['text']['format']['strict'],True)
            b=p['text']['format']['schema']['properties']['claim_checks']['items']['anyOf'];self.assertEqual(b[0]['properties']['material_evidence']['minItems'],1);self.assertEqual(b[1]['properties']['material_evidence']['minItems'],0)
            return httpx.Response(200,json=self.envelope(bad))
        p=self.provider(handler);failed=self.a.post(endpoint,json={'restart':True}).json()['analysis'];self.assertEqual(p.request_count,1);self.assertEqual(failed['result'],good['result']);self.assertEqual(failed['attempt_status'],'error');d=self.w.get('analysis',sid+':learner')['diagnostics'];self.assertEqual(d['validation_reason'],'material_required');self.assertEqual(d['validation_path'],'claim_checks/2/material_evidence');self.assertTrue(d['request_strict'])
        # Independently authored supported contract: booking outcome is separate from policy.
        valid=copy.deepcopy(wire);valid['actual_outcome']='Kein Termin vereinbart.';valid['claim_checks']=[{'statement':'Termine sind gesondert zu bestätigen.','verdict':'supported','observation':'Diese Bedingung steht im historischen Material.','evidence':copy.deepcopy(claim['evidence']),'material_evidence':[{'path':'/company/limitations'}]}]
        self.provider(lambda r:httpx.Response(200,json=self.envelope(valid)));saved=self.a.post(endpoint,json={'restart':True}).json()['analysis'];self.assertEqual(saved['status'],'ready');self.assertNotIn('attempt_status',saved);self.assertEqual(saved['result']['claim_checks'][0]['material_evidence'][0]['quote'],s['company_snapshot']['limitations']);self.assertEqual(self.store.get_session(sid),s);self.assertEqual(self.m.get('/api/mentor/reviews').json()['sessions'],[])
    def test_structural_and_reference_mutations_through_handler(self):
        sid,s=self.fixture();wire=self.wire(s);endpoint='/api/learning/sessions/'+sid+'/analysis';self.provider(lambda r:httpx.Response(200,json=self.envelope(wire)));old=self.a.post(endpoint,json={}).json()['analysis']['result']
        mutations=[
            ('required',lambda x:x.pop('summary'),'result'),
            ('extra',lambda x:x.update(unexpected=True),'result'),
            ('enum',lambda x:x['stages'][0].update(status='passed'),'stages/0/status'),
            ('length',lambda x:x.update(summary='X'*4001),'summary'),
            ('blank',lambda x:x.update(summary='   '),'summary'),
            ('count',lambda x:x['recommendation'].update(priorities=['a','b','c']),'recommendation/priorities'),
            ('stage proof',lambda x:x['stages'][0].update(evidence=[]),'stages/0/evidence'),
            ('message id',lambda x:x['stages'][0]['evidence'][0].update(message_id='unknown'),'stages/0/evidence/0'),
            ('duplicate stage',lambda x:x['stages'][1].update(key='needs'),'stages'),
            ('finding index',lambda x:x['recommendation']['finding_refs'][0].update(index=1),'recommendation/finding_refs/0/index'),
            ('repeat scope',lambda x:x['recommendation']['finding_refs'][0].update(section='strengths'),'recommendation/finding_refs'),
        ]
        for name,change,path in mutations:
            with self.subTest(name=name):
                bad=copy.deepcopy(wire);change(bad);self.provider(lambda r:httpx.Response(200,json=self.envelope(bad)));response=self.a.post(endpoint,json={'restart':True}).json()['analysis'];self.assertEqual(response['attempt_status'],'error');self.assertEqual(response['result'],old);self.assertEqual(self.w.get('analysis',sid+':learner')['diagnostics']['validation_path'],path)
    def test_short_scalar_sources_and_legacy_quotes_in_api_and_export(self):
        sid,s=self.fixture();s['company_snapshot']['limitations']='90 EUR';self.store.save_session(s);ctx=self.w.context(s);ctx['materials']={'markdown':'Legacy saved document, not today’s profile.','products':[{'price_eur':90}]};self.w.put('snapshot',sid,ctx)
        wire=self.wire(s);ev=copy.deepcopy(wire['stages'][0]['evidence']);wire['claim_checks']=[{'statement':'Dokumentierter Preis.','verdict':'supported','observation':'Historischer Wert.','evidence':ev,'material_evidence':[{'path':'/company/limitations'},{'path':'/saved_materials/products/0/price_eur'}]}]
        self.provider(lambda r:httpx.Response(200,json=self.envelope(wire)));a=self.a.post('/api/learning/sessions/'+sid+'/analysis',json={}).json()['analysis'];self.assertEqual(a['status'],'ready');self.assertEqual([x['quote'] for x in a['result']['claim_checks'][0]['material_evidence']],['90 EUR','90'])
        old=self.w.get('analysis',sid+':learner');old['result']['claim_checks'][0]['material_evidence']=[{'path':'/saved_materials/markdown'},{'path':'/company/limitations','quote':'90 EUR'},{'path':'/company/missing'}];self.w.put('analysis',sid+':learner',old)
        current=self.store.get_company();current['limitations']='Today only, never substitute.';self.store.save_company(current)
        for client in (self.a,):
            public=client.get('/api/sessions/'+sid).json()['session']['analysis'];quotes=[x['quote'] for x in public['result']['claim_checks'][0]['material_evidence']];self.assertEqual(quotes,['Legacy saved document, not today’s profile.','90 EUR','']);self.assertNotIn('diagnostics',public) if client is self.a else None
        txt=self.a.get('/api/sessions/'+sid+'/export.txt').text;self.assertIn('Legacy saved document, not today’s profile.',txt);self.assertIn('90 EUR',txt);self.assertIn('Die historische Quelle ist nicht gespeichert',txt);self.assertNotIn('Today only',txt);self.assertEqual(self.w.get('analysis',sid+':learner'),old)
        self.assertEqual(self.store.get_session(sid),s)
        self.assertEqual(self.m.get('/api/sessions/'+sid).status_code,404)
