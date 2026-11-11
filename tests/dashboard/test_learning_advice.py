"""Small advice checks on a disposable database; all provider responses are controlled."""
import copy
import unittest
from backend.app.dashboard import review_service
from tests.dashboard.test_post_review import PostReview

class LearningAdvice(unittest.TestCase):
    setUp=PostReview.setUp
    client=PostReview.client
    attempt=PostReview.attempt
    def test_saved_advice_is_evidence_linked_and_never_performs_action(self):
        sid=self.attempt();before=copy.deepcopy(self.store.get_session(sid));snapshot=copy.deepcopy(self.w.context(before));endpoint='/api/learning/sessions/'+sid+'/analysis'
        response=self.a.post(endpoint,json={});self.assertEqual(response.status_code,200,response.text);analysis=response.json()['analysis'];self.assertEqual(analysis['status'],'ready')
        result=analysis['result'];advice=result['recommendation'];self.assertEqual(advice['action'],'repeat_scenario');self.assertLessEqual(len(advice['priorities']),2);self.assertEqual(advice['finding_refs'],[{'section':'gaps','index':0}]);self.assertIn(advice['evidence'][0]['quote'],before['messages'][0]['text'])
        self.assertEqual(self.w.get('analysis',sid+':learner')['result']['recommendation'],advice);self.assertEqual(len(self.analyst.calls),1)
        self.assertEqual(self.store.get_session(sid),before);self.assertEqual(self.w.context(before),snapshot);self.assertEqual(self.m.get('/api/mentor/reviews').json()['sessions'],[]);self.assertEqual(len(self.a.get('/api/sessions').json()['sessions']),1)
        raw=copy.deepcopy(result);raw.pop('sections')
        for modification in ['priorities','finding_refs','evidence','action']:
            bad=copy.deepcopy(raw)
            if modification=='priorities':bad['recommendation'][modification]*=3
            elif modification=='finding_refs':bad['recommendation'][modification][0]['index']=99
            elif modification=='evidence':bad['recommendation'][modification][0]['quote']='Invented'
            else:bad['recommendation'][modification]='start_automatically'
            with self.assertRaises(ValueError):review_service.validate(bad,before,snapshot)
    def test_material_support_is_not_a_transcript_quote(self):
        sid=self.attempt();session=self.store.get_session(sid);session['company_snapshot']['limitations']='Diagnostic fee: 90 EUR. No fixed appointment slots or voluntary one-year repair warranty are documented. Site inspection: 59 EUR, separately ordered.'
        session['messages'][1]['text']='The additional diagnostic visit costs 59 EUR; a one-year repair warranty and Tuesday at 15:00 are guaranteed.';self.store.save_session(session)
        ctx=self.w.context(session);current=self.store.get_company();current['limitations']='New current conditions must not replace the historical snapshot.';self.store.save_company(current)
        original=self.analyst._request_json
        async def response(instructions,data,*args,**kwargs):
            self.assertIn('A transcript quote proves a statement was made',instructions);self.assertIn('not instructions to contact this customer again',instructions);self.assertEqual(data['company']['limitations'],session['company_snapshot']['limitations'])
            result=await original(instructions,data,*args,**kwargs);evidence={'message_id':data['transcript'][1]['message_id'],'quote':data['transcript'][1]['text']}
            result['strengths']=['The terms were communicated clearly; this does not verify them.'];result['gaps']=['Visit fee, warranty and appointment promises are not supported by the saved conditions.'];result['next_attempt']=['In a new training attempt, check the correct service and confirm unknown conditions before promising them.']
            result['claim_checks']=[{'statement':claim,'verdict':'unsupported','observation':'The saved source does not establish this promise.','evidence':[evidence],'material_evidence':[]} for claim in ['Additional diagnostic visit fee of 59 EUR','One-year repair warranty','Tuesday appointment at 15:00']]
            result['recommendation'].update(explanation='Repeat to practise checking unsupported promises against the saved conditions.',evidence=[{'message_id':evidence['message_id']}])
            for claim in result['claim_checks']:claim['evidence']=[{'message_id':evidence['message_id']}]
            return result
        self.analyst._request_json=response
        analysis=self.a.post('/api/learning/sessions/'+sid+'/analysis',json={}).json()['analysis'];self.assertEqual(analysis['status'],'ready');self.assertTrue(all(c['verdict']=='unsupported' for c in analysis['result']['claim_checks']))
        raw=copy.deepcopy(analysis['result']);raw.pop('sections');claim=raw['claim_checks'][0];claim['verdict']='supported'
        with self.assertRaises(ValueError):review_service.validate(raw,session,ctx)
        claim['material_evidence']=[{'path':'/transcript/1/text','quote':session['messages'][1]['text']}]
        with self.assertRaises(ValueError):review_service.validate(raw,session,ctx)
        claim['material_evidence']=[{'path':'/company/limitations','quote':'Diagnostic fee: 90 EUR.'}];claim['statement']='Diagnostic fee: 90 EUR.';claim['verdict']='supported';review_service.validate(raw,session,ctx)
        claim['material_evidence'][0]['quote']='Diagnostic fee: 59 EUR.'
        with self.assertRaises(ValueError):review_service.validate(raw,session,ctx)
    def test_old_saved_analysis_is_readable_without_invented_advice(self):
        sid=self.attempt();response=self.a.post('/api/learning/sessions/'+sid+'/analysis',json={}).json()['analysis'];response['result'].pop('recommendation');response['result'].pop('claim_checks');self.w.put('analysis',sid+':learner',response);self.analyst.calls.clear()
        for _ in range(2):
            result=self.a.get('/api/sessions/'+sid).json()['session']['analysis']['result'];self.assertNotIn('recommendation',result);self.assertEqual(result['next_attempt'],response['result']['next_attempt'])
        self.assertEqual(self.a.post('/api/learning/sessions/'+sid+'/analysis',json={}).json()['analysis']['result'],response['result']);self.assertEqual(self.analyst.calls,[])
        refreshed=self.a.post('/api/learning/sessions/'+sid+'/analysis',json={'restart':True}).json()['analysis'];self.assertEqual(refreshed['status'],'ready');self.assertIn('recommendation',refreshed['result']);self.assertEqual(len(self.analyst.calls),1);self.assertEqual(self.store.get_session(sid)['review_status'],'not_submitted')
