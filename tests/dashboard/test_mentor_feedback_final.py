"""A33: immutable publication and the existing transcription route on temporary SQLite."""
import copy
import unittest
from unittest.mock import AsyncMock,patch
from fastapi.testclient import TestClient
from tests.dashboard import test_learning_workflow as helpers

class MentorFeedbackFinal(unittest.TestCase):
    setUp=helpers.WorkflowChecks.setUp
    client=helpers.WorkflowChecks.client
    attempt=helpers.WorkflowChecks.attempt

    def test_published_feedback_is_immutable_and_identical_retry_is_idempotent(self):
        sid=self.attempt();self.a.post('/api/sessions/'+sid+'/submit')
        workflow=self.app.state.workflow
        snapshot=copy.deepcopy(workflow.context(self.app.state.store.get_session(sid)))
        assessment={'stages':{'needs':'completed','capabilities':'partial','proposal':'partial'},'commercial_outcome':'deferred_decision','company_fit':'uncertain'}
        draft={'note':'A33 explicit mentor feedback.','assessment':assessment,'goal':'partly','observations':'Keep historical observations.'}
        endpoint='/api/mentor/reviews/'+sid
        self.assertEqual(self.m.put('/api/mentor/learning/reviews/'+sid+'/draft',json=draft).status_code,200)
        self.assertIsNone(self.a.get('/api/sessions/'+sid).json()['session']['published_review'])
        body={'note':draft['note'],'assessment':assessment}
        first=self.m.post(endpoint,json=body);self.assertEqual(first.status_code,200,first.text)
        published=copy.deepcopy(workflow.get('published_review',sid));stored=copy.deepcopy(self.app.state.store.get_session(sid));old_draft=copy.deepcopy(workflow.get('decision_draft',sid))
        retry=self.m.post(endpoint,json=body);self.assertEqual(retry.status_code,200,retry.text)
        self.assertEqual(retry.json()['session']['published_review'],first.json()['session']['published_review'])
        self.assertEqual(self.m.post(endpoint,json={**body,'note':'Attempted silent overwrite.'}).status_code,409)
        changed=copy.deepcopy(body);changed['assessment']['stages']['needs']='not_completed'
        self.assertEqual(self.m.post(endpoint,json=changed).status_code,409)
        self.assertEqual(self.m.put('/api/mentor/learning/reviews/'+sid+'/draft',json={**draft,'observations':''}).status_code,409)
        self.assertEqual(workflow.get('published_review',sid),published)
        self.assertEqual(workflow.get('decision_draft',sid),old_draft)
        self.assertEqual(self.app.state.store.get_session(sid),stored)
        self.assertEqual(workflow.context(stored),snapshot)
        learner=self.a.get('/api/sessions/'+sid).json()['session']
        self.assertEqual(learner['review_status'],'reviewed');self.assertEqual(learner['published_review']['note'],body['note'])
        self.assertNotIn('decision_draft',learner);self.assertNotIn('mentor_analysis',learner)
        for format in ('pdf','txt','json'):self.assertEqual(self.a.get('/api/sessions/'+sid+'/export.'+format).status_code,200)
        self.assertEqual(len(workflow.all('published_review')),1);self.assertEqual(workflow.all('certificate'),[]);self.assertEqual(self.analyst.calls,[])

    def test_existing_transcription_is_available_to_authenticated_mentor_and_employee(self):
        with patch('backend.app.dashboard.server.transcribe',new=AsyncMock(return_value={'text':'Editable feedback dictation.'})) as transcribe:
            for client in (self.m,self.a):
                result=client.post('/api/transcriptions?format=webm&language=de',content=b'synthetic-audio',headers={'Content-Type':'audio/webm'})
                self.assertEqual(result.status_code,200,result.text);self.assertEqual(result.json()['text'],'Editable feedback dictation.')
            self.assertEqual(transcribe.await_count,2)
            self.assertEqual(transcribe.call_args.args[1:3],('webm','de'))
            with TestClient(self.app) as anonymous:
                self.assertEqual(anonymous.post('/api/transcriptions',content=b'synthetic').status_code,401)
            token,_=self.auth.issue(self.users[0]['id'])
            with TestClient(self.app,cookies={helpers.COOKIE:token},headers={'Origin':'http://testserver'}) as no_csrf:
                self.assertEqual(no_csrf.post('/api/transcriptions',content=b'synthetic').status_code,403)
            self.assertEqual(transcribe.await_count,2)
        self.assertEqual(self.app.state.workflow.all('published_review'),[])
