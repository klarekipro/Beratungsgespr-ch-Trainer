"""Focused calibration contracts: controlled reviews, no provider network calls."""
import copy
import json
import unittest
from backend.app.dashboard import review_service
from tests.dashboard.test_post_review import PostReview as BaseFixture

class ReviewCalibration(unittest.TestCase):
    setUp=BaseFixture.setUp
    client=BaseFixture.client
    attempt=BaseFixture.attempt
    def run_case(self,flaw=False,repeat=False):
        sid=self.attempt('de');session=self.store.get_session(sid)
        session['company_snapshot']['limitations']='Diagnosis: 90 EUR. Repair prices, success rates, warranty terms, service partners and appointment availability are not provided. Repair requires a quotation and explicit consent.'
        texts=[('customer','Meine Waschmaschine stoppt. Ich möchte eine Einschätzung vor einer Entscheidung.'),('learner','Ohne Diagnose kann ich keine Reparaturpreise, Erfolgsquoten, Garantie oder Termine zusagen. Die Diagnose kostet 90 EUR; Reparatur erst nach Angebot und Zustimmung.'),('customer','Die 90 EUR sind für mich in Ordnung. Ich möchte noch keine Diagnose beauftragen.'),('learner','Noch kein Auftrag und kein Termin. Sie melden sich mit den Modellangaben. Auf Wiedersehen.'),('customer','Ich melde mich mit den Angaben. Auf Wiedersehen.'),('learner','Vielen Dank, auf Wiedersehen.'),('customer','Ich melde mich mit den Angaben. Auf Wiedersehen.')]
        if flaw:texts[1]=('learner','Die Diagnose kostet 90 EUR plus 59 EUR; Reparaturerfolg und ein Jahr Garantie sind garantiert.')
        session['messages']=[{'role':role,'text':text,'turn':(i+1)//2,'at':session['created_at']} for i,(role,text) in enumerate(texts)];self.store.save_session(session)
        before=copy.deepcopy(session);captured=[]
        async def provider(instructions,data,*args,**kwargs):
            captured.append(data);self.assertIn('Truthfully declining to invent',instructions);self.assertIn('possible customer-simulation issues',instructions);self.assertIn('NOT authorization to order the diagnosis',instructions);self.assertIn('specific achievable alternative',instructions)
            evidence=[{'message_id':data['transcript'][1]['message_id']}]
            gaps=['Unsupported surcharge and repair guarantee; check the saved conditions before promising them.'] if flaw else []
            return {'summary':'Company information is limited. Repeated customer closing statements without new information may be a simulation issue; motive unknown.','actual_outcome':'Price accepted, but diagnosis explicitly not ordered; a voluntary next step without a booking.','strengths':['The diagnostic fee was clearly communicated.'],'gaps':gaps,'next_attempt':['In a new attempt, distinguish the documented diagnostic fee from unsupported promises.'] if flaw else [],'stages':[{'key':k,'status':'evidence_found','observation':'A preliminary observation, with no invented motive.','evidence':copy.deepcopy(evidence)} for k in review_service.STAGES],'claim_checks':[{'statement':'Surcharge and warranty guarantee','verdict':'unsupported','observation':'Not established by the saved conditions.','evidence':copy.deepcopy(evidence),'material_evidence':[]}] if flaw else [],'recommendation':{'action':'repeat_scenario' if repeat else 'submit_to_mentor','explanation':'Practise correcting the evidenced unsupported promises.' if repeat else 'The objective is substantially met; seek the mentor’s final feedback.','priorities':['Check saved conditions before making a promise.'] if repeat else [],'finding_refs':[{'section':'gaps' if repeat else 'strengths','index':0}],'evidence':copy.deepcopy(evidence)}}
        self.app.state.analysis_provider=type('Controlled',(),{'_request_json':staticmethod(provider)})()
        result=self.a.post('/api/learning/sessions/'+sid+'/analysis',json={}).json()['analysis'];self.assertEqual(len(captured),1);self.assertEqual(self.store.get_session(sid),before);self.assertEqual(self.m.get('/api/mentor/reviews').json()['sessions'],[])
        return sid,result
    def test_truthful_uncertainty_and_no_invented_gaps(self):
        sid,a=self.run_case();self.assertEqual(a['status'],'ready');self.assertEqual(a['result']['gaps'],[]);self.assertEqual(a['result']['next_attempt'],[]);self.assertEqual(a['result']['recommendation']['action'],'submit_to_mentor')
        self.assertIn('simulation issue',a['result']['summary']);self.assertEqual(self.store.get_session(sid)['review_status'],'not_submitted')
    def test_unsupported_promises_are_still_a_substantive_gap(self):
        _,a=self.run_case(flaw=True,repeat=True);self.assertEqual(a['status'],'ready');self.assertEqual(a['result']['claim_checks'][0]['verdict'],'unsupported');self.assertEqual(a['result']['recommendation']['action'],'repeat_scenario')
    def test_repeat_requires_a_demonstrated_gap_reference(self):
        sid,a=self.run_case();raw=copy.deepcopy(self.w.get('analysis',sid+':learner')['result']);raw.pop('sections');raw['recommendation']['action']='repeat_scenario'
        with self.assertRaisesRegex(ValueError,'repeat requires demonstrated gap'):review_service.validate(raw,self.store.get_session(sid),self.w.context(self.store.get_session(sid)))
    def test_successful_no_order_prose_hides_ids_without_rewriting_evidence(self):
        sid,a=self.run_case();stored=self.w.get('analysis',sid+':learner');mid=stored['result']['stages'][0]['evidence'][0]['message_id'];stored['result']['summary']+=' ('+mid+').';stored['result']['recommendation']['explanation']+=' '+mid;stored['result']['sections'][0]['text']=stored['result']['summary'];self.w.put('analysis',sid+':learner',stored)
        # All generated prose fields are projected, but exact evidence/source quotations stay intact.
        sample=copy.deepcopy(stored['result'])
        for key in ('strengths','gaps','next_attempt'):sample[key]=['Text '+mid]
        sample['stages'][0]['observation']='Text '+mid
        sample['claim_checks']=[{'statement':'Text '+mid,'observation':'Text '+mid,'evidence':copy.deepcopy(sample['stages'][0]['evidence']),'material_evidence':[{'path':'/company/limitations','quote':'Original '+mid}]}]
        sample['recommendation']['priorities']=['Text '+mid];original=copy.deepcopy(sample);projected=review_service.display_review_result(sample,self.store.get_session(sid))
        for key in ('strengths','gaps','next_attempt'):self.assertNotIn(mid,str(projected[key]))
        self.assertNotIn(mid,projected['stages'][0]['observation']);self.assertNotIn(mid,projected['claim_checks'][0]['statement']);self.assertNotIn(mid,projected['claim_checks'][0]['observation']);self.assertNotIn(mid,str(projected['recommendation']['priorities']));self.assertEqual(projected['claim_checks'][0]['material_evidence'],original['claim_checks'][0]['material_evidence']);self.assertEqual(sample,original)
        self.app.state.analysis_provider=None
        public=self.a.get('/api/sessions/'+sid).json()['session']['analysis']['result'];self.assertNotIn(mid,public['summary']);self.assertIn('[2]',public['summary']);self.assertNotIn(mid,public['recommendation']['explanation']);self.assertEqual(public['stages'][0]['evidence'][0],stored['result']['stages'][0]['evidence'][0]);self.assertEqual(self.w.get('analysis',sid+':learner'),stored)
        txt=self.a.get('/api/sessions/'+sid+'/export.txt').text;self.assertNotIn(mid,txt);self.assertIn('Keine wesentlichen Lernlücken festgestellt.',txt);self.assertIn('diagnosis explicitly not ordered',txt)
