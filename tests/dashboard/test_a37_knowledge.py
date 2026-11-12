"""A37 non-paid checks. Synthetic temporary database only."""
import copy
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from backend.app.dashboard.auth import COOKIE
from backend.app.dashboard.company_reference import REFERENCES, canonical_company, initial_materials, reference_for
from backend.app.dashboard.server import create_app
from backend.app.dashboard.simple_actor import dossier
from backend.app.dashboard.workflow import Workflow
from scripts.prepare_a37_knowledge import prepare, publish, read_current


class KnowledgeUpdate(unittest.TestCase):
    def test_localized_learner_reference_new_snapshot_and_immutable_history(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict('os.environ', {'OPENAI_API_KEY': 'synthetic-not-real', 'TRAINER_AUDIT_DIR': ''}):
            path = Path(tmp)/'test.sqlite3'
            # Any unexpected provider use fails rather than reaching the network.
            def forbidden_provider(mode):
                raise AssertionError('No provider call allowed')
            app = create_app(path, provider_factory=forbidden_provider)
            store = app.state.store
            workflow = Workflow(store)
            company = canonical_company(); company['revision'] = 4
            store.save_company(company)
            materials = initial_materials({'id': 'synthetic-before'})
            workflow.put('materials', 'current', materials)
            workflow.put('material_version', materials['id'], materials)
            auth = app.state.auth
            learner = auth.create_user('a37-learner', 'Demo', 'A37-test-password', role='employee', temporary=False)
            token, csrf = auth.issue(learner['id'])
            with TestClient(app, headers={'Origin':'http://testserver', 'X-CSRF-Token':csrf}, cookies={COOKIE:token}) as client:
                def start():
                    scenario = client.get('/api/scenarios').json()['scenarios'][0]
                    response = client.post('/api/sessions', json={'scenario_id':scenario['id'],'mode':'simple_actor','client_profile_id':scenario['personas'][0]['id']})
                    self.assertEqual(response.status_code, 200, response.text)
                    return store.get_session(response.json()['session']['id'])
                old = start()
                old_snapshot = copy.deepcopy(workflow.context(old))
                workflow.put('published_review', 'historical', {'note':'Unchanged feedback'})
                workflow.put('certificate', 'historical', {'status':'issued','recipient_full_name':'Анна Müller','pdf':'immutable-demo'})
                with closing(sqlite3.connect(path)) as connection, connection:
                    protected = connection.execute("SELECT * FROM learning_records WHERE kind IN ('published_review','certificate')").fetchall()
                plan = prepare(company, materials)
                publish(path, plan, Path(tmp)/'before.sqlite3')
                for language in ('de','en','ru'):
                    auth.set_locale(learner['id'], language)
                    response = client.get('/api/company-reference')
                    self.assertEqual(response.status_code, 200)
                    reference = response.json()['reference']
                    self.assertEqual(reference['version'], 'lindenhaus-a37-v1')
                    for value in ('beratung@lindenhaus.example','https://lindenhaus.example','09:00–18:00','10:00–14:00'):
                        self.assertIn(value, reference['about'])
                        self.assertIn(value, reference['documents'][0]['text'])
                    for key in ('products','services','terms'):
                        self.assertEqual(reference[key], REFERENCES[language][key])
                auth.set_locale(learner['id'], 'de')
                new = start()
                self.assertIn('beratung@lindenhaus.example', new['company_snapshot']['description'])
                self.assertEqual(workflow.context(new)['materials']['id'], plan['materials']['id'])
                self.assertEqual(store.get_session(old['id']), old)
                self.assertEqual(workflow.context(old), old_snapshot)
                own = json.dumps(dossier(new), ensure_ascii=False)
                for private in ('beratung@lindenhaus.example','lindenhaus.example','company_snapshot','rubric','services'):
                    self.assertNotIn(private, own)
                # Current GET still enforces authentication and mentor write permission.
                self.assertEqual(client.post('/api/mentor/company-documents/apply', json={}).status_code, 403)
                changed = copy.deepcopy(plan['company']); changed['description'] += ' Owner edit'
                self.assertIsNone(reference_for(plan['materials'], changed, 'de'))
                publish(path, plan, Path(tmp)/'before-rollback.sqlite3', rollback=True)
                self.assertEqual(store.get_company(), company)
                self.assertEqual(workflow.get('materials','current'), materials)
                self.assertEqual(workflow.context(new)['materials']['id'], plan['materials']['id'])
                self.assertEqual(workflow.get('material_version',plan['materials']['id']),plan['materials'])
                with closing(sqlite3.connect(path)) as connection, connection:
                    self.assertEqual(connection.execute("SELECT * FROM learning_records WHERE kind IN ('published_review','certificate')").fetchall(), protected)
            with TestClient(app) as anonymous:
                self.assertEqual(anonymous.get('/api/company-reference').status_code, 401)

    def test_conflicts_and_tampering_fail_closed(self):
        company = canonical_company(); materials = initial_materials(None)
        edited = copy.deepcopy(company); edited['description'] += ' Author change'
        with self.assertRaises(ValueError): prepare(edited, materials)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'test.sqlite3'
            with closing(sqlite3.connect(path)) as connection, connection:
                connection.execute('CREATE TABLE documents(kind TEXT,id TEXT,data TEXT,PRIMARY KEY(kind,id))')
                connection.execute('CREATE TABLE learning_records(kind TEXT,id TEXT,data TEXT,PRIMARY KEY(kind,id))')
                connection.execute('INSERT INTO documents VALUES (?,?,?)',('company','main',json.dumps(company)))
                connection.execute('INSERT INTO learning_records VALUES (?,?,?)',('materials','current',json.dumps(materials)))
            plan = prepare(company, materials)
            corrupt = copy.deepcopy(plan); corrupt['company']['services'][0]['conditions'] = 'Free'
            with self.assertRaises(ValueError): publish(path, corrupt, Path(tmp)/'tampered.sqlite3')
            publish(path, plan, Path(tmp)/'first.sqlite3')
            with self.assertRaises(ValueError): publish(path, plan, Path(tmp)/'repeated.sqlite3')
            with closing(sqlite3.connect(path)) as connection, connection:
                self.assertEqual(read_current(connection), (plan['company'],plan['materials']))
                self.assertEqual(connection.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
