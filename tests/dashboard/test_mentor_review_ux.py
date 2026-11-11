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
