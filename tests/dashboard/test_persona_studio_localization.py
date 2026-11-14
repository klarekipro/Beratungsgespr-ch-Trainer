"""One non-paid boundary check; synthetic SQLite only, no live persona publication."""
import copy
import unittest
from backend.app.dashboard.simple_actor import dossier
from backend.app.dashboard.workflow import Workflow
from tests.dashboard import test_learning_workflow as helpers

class PersonaStudioLocalization(unittest.TestCase):
    setUp=helpers.WorkflowChecks.setUp
    tearDown=helpers.WorkflowChecks.tearDown
    client=helpers.WorkflowChecks.client

    def test_ui_locale_is_read_only_for_profiles_and_actor_snapshots(self):
        response=self.a.post('/api/sessions',json={'scenario_id':'oven_no_fit','mode':'simple_actor','client_profile_id':'decisive_oven','training_language':'de'})
        self.assertEqual(response.status_code,200,response.text)
        sid=response.json()['session']['id'];store=self.app.state.store;workflow=Workflow(store)
        original=copy.deepcopy(store.get_session(sid));snapshot=copy.deepcopy(workflow.context(original));own=dossier(original)
        profiles=self.m.get('/api/mentor/client-profiles').json()['profiles']
        workflow.put('published_review','historic',{'note':'Historical feedback'})
        workflow.put('certificate','historic',{'status':'issued','pdf':'unchanged synthetic snapshot'})
        for language in ['de','en','ru','de']:
            self.assertEqual(self.m.put('/api/auth/preferences',json={'locale':language}).status_code,200)
            self.assertEqual(self.m.get('/api/mentor/client-profiles').json()['profiles'],profiles)
            self.assertEqual(store.get_session(sid),original)
            self.assertEqual(workflow.context(original),snapshot)
            self.assertEqual(dossier(store.get_session(sid)),own)
        self.assertEqual(original['scenario_snapshot']['language'],'de')
        self.assertNotIn('company_snapshot',own);self.assertNotIn('services',own);self.assertNotIn('rubric',own)
        # Existing versioned save accepts an explicit author language; never automatic.
        authored=copy.deepcopy(next(p for p in profiles if p['id']=='decisive_oven'))
        authored['content_language']='en';authored['persona']['character']='Authored English behavior, no translation requested.'
        saved=self.m.put('/api/mentor/client-profiles/'+authored['id'],json=authored)
        self.assertEqual(saved.status_code,200,saved.text)
        self.assertEqual(saved.json()['profile']['version'],authored['version']+1)
        self.assertEqual(saved.json()['profile']['content_language'],'en')
        self.assertEqual(store.get_session(sid),original)
        self.assertEqual(workflow.get('published_review','historic'),{'note':'Historical feedback'})
        self.assertEqual(workflow.get('certificate','historic'),{'status':'issued','pdf':'unchanged synthetic snapshot'})
        self.assertEqual(self.a.get('/api/mentor/client-profiles').status_code,403)
