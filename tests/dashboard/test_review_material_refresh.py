"""A26: material-citation failures on sanitized data, never a captured provider reply."""
import copy
import json
import unittest
import httpx
from backend.app.dashboard import review_service
from tests.dashboard.test_review_evidence_failure import ReviewEvidenceFailure as Base

class MaterialRefresh(unittest.TestCase):
    setUp=Base.setUp
    client=Base.client
    attempt=Base.attempt
    fixture=Base.fixture
    wire=Base.wire
    provider=Base.provider
    envelope=Base.envelope
    def test_historical_material_selection_and_failed_refresh_retains_success(self):
        sid,s=self.fixture();s['company_snapshot']['limitations']='Diagnose: 90 EUR.\nReparatur erst nach Angebot und Zustimmung. Keine Terminzusage.';self.store.save_session(s);ctx=self.w.context(s)
        # Today's profile must not supply evidence for the saved attempt.
        current=self.store.get_company();current['limitations']='Today only: free repair and guaranteed appointment.';self.store.save_company(current)
        wire=self.wire(s);wire['claim_checks']=[{'statement':'Diagnose kostet 90 EUR.','verdict':'supported','observation':'Durch die gespeicherten Bedingungen belegt.','evidence':[{'message_id':review_service.message_ids(s)[5]}],'material_evidence':[{'path':'/company/limitations'}]}]
        def handler(request):
            body=json.loads(request.content);field=body['text']['format']['schema']['$defs']['historical_source']
            self.assertEqual(field['required'],['path']);self.assertIn('/company/limitations',field['properties']['path']['enum']);self.assertEqual(body['max_output_tokens'],3500)
            return httpx.Response(200,json=self.envelope(wire))
        p=self.provider(handler);endpoint='/api/learning/sessions/'+sid+'/analysis';good=self.a.post(endpoint,json={}).json()['analysis'];self.assertEqual(good['status'],'ready');self.assertEqual(p.request_count,1)
        canonical=copy.deepcopy(good['result']);canonical.pop('sections');self.assertEqual(canonical['claim_checks'][0]['material_evidence'][0]['quote'],s['company_snapshot']['limitations'])
        # Same material-validation family as production; exact discarded response is unavailable.
        for refs,reason in [([{'path':'/company/limitations','quote':'Diagnose: 59 EUR. Unbelegte Behauptung.'}],'material_quote_mismatch'),([], 'material_required')]:
            bad=copy.deepcopy(canonical);bad['claim_checks'][0]['material_evidence']=refs
            with self.assertRaises(review_service.ReviewValidationError) as err:review_service.validate(bad,s,ctx)
            self.assertEqual(err.exception.reason,reason);self.assertEqual(err.exception.stage,'material_evidence_validation');self.assertTrue(err.exception.path.startswith('claim_checks/0/material_evidence'))
        bad=copy.deepcopy(wire);bad['claim_checks'][0]['material_evidence'][0]['path']='/SENSITIVE-invalid-source'
        self.provider(lambda request:httpx.Response(200,json=self.envelope(bad)))
        retained=self.a.post(endpoint,json={'restart':True}).json()['analysis'];self.assertEqual(retained['status'],'ready');self.assertEqual(retained['attempt_status'],'error');self.assertEqual(retained['result'],good['result']);self.assertNotIn('diagnostics',retained)
        diagnostic=self.w.get('analysis',sid+':learner')['diagnostics'];self.assertEqual(diagnostic['stage'],'material_evidence_validation');self.assertEqual(diagnostic['validation_reason'],'material_unknown_path');self.assertEqual(diagnostic['validation_path'],'claim_checks/0/material_evidence/0/path');self.assertNotIn('SENSITIVE',json.dumps(diagnostic))
        self.assertEqual(self.store.get_session(sid),s);self.assertEqual(self.m.get('/api/mentor/reviews').json()['sessions'],[])
        # No unsolicited quote, transcript source, or missing proof is silently accepted.
        for ref in [{'path':'/company/limitations','quote':s['company_snapshot']['limitations']},{'path':'/transcript/5/text'}]:
            bad=copy.deepcopy(wire);bad['claim_checks'][0]['material_evidence']=[ref]
            with self.assertRaises(review_service.ReviewValidationError):review_service.bind_evidence(bad,s,ctx)
    def test_citation_cleanup_preserves_evidence_and_saved_prose(self):
        _,s=self.fixture();ids=review_service.message_ids(s)
        raw={'summary':f'Belegt ({ids[0]}, msg_missing, {ids[3]}). Bereits formatiert ([1], , [4]).', 'stages':[{'observation':'Beobachtung','evidence':[{'message_id':ids[0],'quote':s['messages'][0]['text']}]}]};before=copy.deepcopy(raw)
        projected=review_service.display_review_result(raw,s);self.assertEqual(projected['summary'],'Belegt ([1], [4]). Bereits formatiert ([1], [4]).');self.assertEqual(projected['stages'],raw['stages']);self.assertEqual(raw,before)
