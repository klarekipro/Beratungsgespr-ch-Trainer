"""Targeted employee-state checks on an isolated disposable database; no AI calls."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app.dashboard.server import create_app
from backend.app.dashboard.auth import COOKIE

class EmployeeParticipation(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        env=patch.dict('os.environ',{'OPENAI_API_KEY':'','TRAINER_AUDIT_DIR':''});env.start();self.addCleanup(env.stop)
        self.app=create_app(Path(self.tmp.name)/'copy.sqlite3');self.auth=self.app.state.auth;self.store=self.app.state.store
        self.mentor=self.auth.create_user('qa-mentor','Mentor','Synthetic mentor 42',role='mentor_admin',temporary=False)
        self.employee=self.auth.create_user('qa-person','Same Name','Synthetic employee 42',temporary=False);self.uid=self.employee['id']
        token,csrf=self.auth.issue(self.mentor['id']);self.c=TestClient(self.app,headers={'Origin':'http://testserver','X-CSRF-Token':csrf},cookies={COOKIE:token});self.c.__enter__();self.addCleanup(self.c.__exit__,None,None,None)
    def change(self,active):
        r=self.c.patch('/api/mentor/employees/'+self.uid,json={'active':active});self.assertEqual(r.status_code,200,r.text);return r.json()['employee']
    def test_pause_reactivate_reset_and_transition_log(self):
        token,csrf=self.auth.issue(self.uid);before=copy.deepcopy(self.auth.user(self.uid))
        with TestClient(self.app,headers={'Origin':'http://testserver','X-CSRF-Token':csrf},cookies={COOKIE:token}) as employee_client:
            self.assertEqual(employee_client.patch('/api/mentor/employees/'+self.uid,json={'active':False}).status_code,403)
        self.assertFalse(self.change(False)['active']);self.assertIsNone(self.auth.resolve(token)[0])
        self.assertEqual(self.c.post('/api/auth/login',json={'username':before['username'],'password':'Synthetic employee 42','portal':'learner'}).status_code,401)
        self.assertTrue(self.change(True)['active']);self.assertIsNone(self.auth.resolve(token)[0]);self.assertEqual(self.auth.user(self.uid)['password_hash'],before['password_hash'])
        user=self.auth.authenticate(before['username'],'Synthetic employee 42','qa-ip','learner');self.assertEqual(user['id'],self.uid)
        self.change(True)  # Idempotent assignment must not create a fictitious transition.
        with self.store.connection() as c:
            rows=c.execute('SELECT employee_id,previous_state,new_state,changed_at,actor_id FROM employee_state_events ORDER BY changed_at').fetchall()
        self.assertEqual([(r[1],r[2]) for r in rows],[('active','inactive'),('inactive','active')]);self.assertTrue(all(r[0]==self.uid and r[3]>0 and r[4]==self.mentor['id'] for r in rows));self.assertNotIn('Synthetic',json.dumps(rows));self.assertNotIn(token,json.dumps(rows))
        token,_=self.auth.issue(self.uid)
        r=self.c.post('/api/mentor/employees/'+self.uid+'/password',json={'temporary_password':'New synthetic password 43'});self.assertEqual(r.status_code,200,r.text);self.assertIsNone(self.auth.resolve(token)[0]);self.assertTrue(self.auth.user(self.uid)['must_change_password']);self.assertEqual(self.auth.authenticate(before['username'],'New synthetic password 43','qa-ip','learner')['id'],self.uid)
    def test_archive_preserves_records_metadata_and_blocks_activation(self):
        session={'id':'qa-owned','employee_id':self.uid,'messages':[{'text':'Original utterance'}],'status':'finished','version':1};self.store.save_session(session)
        self.app.state.workflow.put('snapshot','qa-owned',{'materials':{'id':'historical','text':'Original snapshot'}})
        self.app.state.workflow.put('published','qa-owned',{'employee_id':self.uid,'text':'Published feedback'})
        self.app.state.workflow.put('certificate','qa-cert',{'employee_id':self.uid,'basis':['qa-owned'],'status':'issued'})
        self.assertTrue(self.auth.user(self.uid)['active'])  # Finished conversation/certificate does not pause participation.
        self.app.state.employee_lifecycle.mark(self.uid,True,self.mentor['id'])
        with self.store.connection() as c:
            original={t:c.execute('SELECT * FROM '+t+' ORDER BY 1,2').fetchall() for t in ['documents','learning_records','training_owners']}
        token,_=self.auth.issue(self.uid);r=self.c.post('/api/mentor/employees/'+self.uid+'/archive',json={'confirm':True});self.assertEqual(r.status_code,200,r.text);self.assertIsNone(self.auth.resolve(token)[0]);self.assertTrue(r.json()['employee']['is_test'])
        self.assertEqual(self.c.patch('/api/mentor/employees/'+self.uid,json={'active':True}).status_code,409)
        self.assertEqual(self.c.patch('/api/mentor/employees/'+self.uid,json={'active':False}).status_code,409)
        self.assertEqual(self.c.post('/api/mentor/employees/'+self.uid+'/password',json={'temporary_password':'New synthetic password 43'}).status_code,409)
        self.assertEqual(self.c.get('/api/mentor/employees').json()['employees'],[]);self.assertEqual(self.c.get('/api/mentor/employees?archived=true').json()['employees'][0]['id'],self.uid)
        self.assertEqual(self.c.post('/api/mentor/employees/'+self.uid+'/archive',json={'confirm':True}).status_code,200)
        with self.store.connection() as c:
            for t,rows in original.items():self.assertEqual(c.execute('SELECT * FROM '+t+' ORDER BY 1,2').fetchall(),rows)
            events=c.execute('SELECT previous_state,new_state,actor_id FROM employee_state_events').fetchall()
        self.assertEqual(events,[('active','archived',self.mentor['id'])])
