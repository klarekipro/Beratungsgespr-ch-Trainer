"""A32: existing private analysis/draft/publication contracts on isolated SQLite."""
import copy
import unittest
from tests.dashboard import test_learning_workflow as helpers

class MentorReviewUX(unittest.TestCase):
    setUp=helpers.WorkflowChecks.setUp
    client=helpers.WorkflowChecks.client
    attempt=helpers.WorkflowChecks.attempt

    def test_saved_private_review_draft_publication_and_history(self):
        sid,private=self.attempt(),self.attempt()
        self.a.post('/api/sessions/'+sid+'/submit')
        self.m.post('/api/learning/sessions/'+sid+'/analysis',json={'audience':'mentor'})
        calls=len(self.analyst.calls)
        snapshot=copy.deepcopy(self.app.state.workflow.context(self.app.state.store.get_session(sid)))
        session_before=copy.deepcopy(self.app.state.store.get_session(sid))
        draft={'note':'A32 saved mentor feedback.','goal':'partly','observations':'Needs established; options remain open.',
               'assessment':{'stages':{'needs':'completed','capabilities':'partial','proposal':'partial'},'commercial_outcome':'deferred_decision','company_fit':'uncertain'}}
        self.assertEqual(self.m.put('/api/mentor/learning/reviews/'+sid+'/draft',json=draft).status_code,200)
        for _ in range(2):
            mentor=self.m.get('/api/mentor/reviews/'+sid).json()['session']
            learner=self.a.get('/api/sessions/'+sid).json()['session']
            self.assertEqual(mentor['mentor_analysis']['status'],'ready')
            self.assertEqual(mentor['decision_draft']['assessment'],draft['assessment'])
            self.assertNotIn('mentor_analysis',learner)
            self.assertNotIn('decision_draft',learner)
            self.assertIsNone(learner['published_review'])
        self.assertEqual(self.app.state.store.get_session(sid),session_before)
        self.assertEqual(len(self.analyst.calls),calls)
        for fmt in ('txt','json','pdf'):
            r=self.a.get('/api/sessions/'+sid+'/export.'+fmt)
            self.assertEqual(r.status_code,200)
            self.assertNotIn(draft['note'].encode(),r.content)
        history=self.m.get('/api/mentor/employees/'+self.users[1]['id']+'/sessions').json()['sessions']
        self.assertIn(sid,[x['id'] for x in history]);self.assertNotIn(private,[x['id'] for x in history])
        self.assertEqual(self.m.get('/api/mentor/reviews/'+private).status_code,404)
        self.assertEqual(self.m.post('/api/mentor/reviews/'+sid,json={'note':draft['note'],'assessment':draft['assessment']}).status_code,200)
        published=self.a.get('/api/sessions/'+sid).json()['session']['published_review']
        for key in ('goal','observations','note','assessment'):self.assertEqual(published[key],draft[key])
        self.assertEqual(self.app.state.workflow.context(self.app.state.store.get_session(sid)),snapshot)
        self.assertEqual(len(self.analyst.calls),calls)
        self.assertEqual(self.app.state.workflow.all('certificate'),[])

    def test_private_analysis_exports_are_read_only_and_mentor_only(self):
        sid,private,missing=self.attempt(),self.attempt(),self.attempt()
        self.a.post('/api/sessions/'+sid+'/submit');self.a.post('/api/sessions/'+missing+'/submit')
        self.m.post('/api/learning/sessions/'+sid+'/analysis',json={'audience':'mentor'})
        workflow=self.app.state.workflow
        retained=workflow.get('analysis',sid+':mentor');retained['attempt_status']='error'
        workflow.put('analysis',sid+':mentor',retained)
        workflow.put('analysis',private+':mentor',copy.deepcopy(retained))
        workflow.put('analysis',missing+':learner',copy.deepcopy(retained))
        calls=len(self.analyst.calls)
        before_session=copy.deepcopy(self.app.state.store.get_session(sid))
        before_records=copy.deepcopy(workflow.all('analysis'))
        before_context=copy.deepcopy(workflow.context(before_session))
        for language in ('de','en','ru'):
            for format in ('pdf','txt'):
                url=f'/api/mentor/learning/reviews/{sid}/analysis-export.{format}?language={language}'
                response=self.m.get(url);self.assertEqual(response.status_code,200,response.text if format=='txt' else '')
                self.assertIn('no-store',response.headers['Cache-Control'])
                self.assertIn('attachment',response.headers['Content-Disposition'])
                if format=='pdf':self.assertTrue(response.content.startswith(b'%PDF'))
                else:
                    self.assertIn('No order confirmed.',response.text)
                    self.assertIn('Customer supplied information.',response.text)
                    self.assertNotIn('review22.summary',response.text)
                self.assertEqual(self.a.get(url).status_code,403)
                self.assertEqual(self.b.get(url).status_code,403)
        for target in (private,missing):
            self.assertEqual(self.m.get(f'/api/mentor/learning/reviews/{target}/analysis-export.txt').status_code,404)
        self.assertEqual(self.m.get(f'/api/mentor/learning/reviews/{sid}/analysis-export.json').status_code,404)
        self.assertEqual(self.app.state.store.get_session(sid),before_session)
        self.assertEqual(workflow.all('analysis'),before_records)
        self.assertEqual(workflow.context(self.app.state.store.get_session(sid)),before_context)
        self.assertEqual(len(self.analyst.calls),calls)
        learner=self.a.get('/api/sessions/'+sid).json()['session']
        self.assertNotIn('mentor_analysis',learner);self.assertNotIn('decision_draft',learner)
