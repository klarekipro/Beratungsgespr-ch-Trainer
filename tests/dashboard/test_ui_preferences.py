"""One focused UI metadata test; no paid dialogue or analysis."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app.dashboard.server import create_app
from backend.app.dashboard.auth import COOKIE

class UIRecords(unittest.TestCase):
    def test_read_receipts_and_view_preferences_are_scoped_and_do_not_change_training(self):
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{'OPENAI_API_KEY':'test-no-network'}):
            app=create_app(Path(directory)/'trainer.sqlite3');a=app.state.auth
            users=[a.create_user('ui-'+name,name,'UI-test-password',role='mentor_admin' if name=='mentor' else 'employee',temporary=False) for name in ['mentor','employee','other']]
            def client(user):
                token,csrf=a.issue(user['id'])
                return TestClient(app,headers={'Origin':'http://testserver','X-CSRF-Token':csrf},cookies={COOKIE:token})
            with client(users[0]) as mentor,client(users[1]) as learner,client(users[2]) as other:
                r=learner.post('/api/sessions',json={'scenario_id':'oven_no_fit','mode':'simple_actor','client_profile_id':'decisive_oven'});self.assertEqual(r.status_code,200,r.text);sid=r.json()['session']['id']
                learner.post('/api/sessions/'+sid+'/finish');learner.post('/api/sessions/'+sid+'/submit')
                r=mentor.post('/api/mentor/reviews/'+sid,json={'note':'UI metadata fixture'});self.assertEqual(r.status_code,200,r.text)
                published=r.json()['session']['published_review'];before=app.state.store.get_session(sid)
                receipt={'session_id':sid,'published_at':published['published_at']}
                self.assertEqual(other.post('/api/ui/reviews/read',json=receipt).status_code,404)
                self.assertEqual(mentor.post('/api/ui/reviews/read',json=receipt).status_code,404)
                self.assertEqual(learner.post('/api/ui/reviews/read',json={**receipt,'published_at':'old'}).status_code,409)
                self.assertEqual(learner.post('/api/ui/reviews/read',json=receipt).status_code,200)
                self.assertEqual(other.get('/api/ui/reviews/read').json()['read'],{})
                prefs={'layout':'stack','density':'compact'}
                self.assertEqual(learner.put('/api/ui/preferences',json=prefs).status_code,200)
                self.assertIsNone(other.get('/api/ui/preferences').json()['preferences'])
                self.assertEqual(learner.put('/api/ui/preferences',json={'layout':'invalid'}).status_code,422)
                with client(users[1]) as reopened:
                    self.assertEqual(reopened.get('/api/ui/preferences').json()['preferences'],prefs)
                    self.assertEqual(reopened.get('/api/ui/reviews/read').json()['read'][sid],published['published_at'])
                self.assertEqual(app.state.store.get_session(sid),before)
