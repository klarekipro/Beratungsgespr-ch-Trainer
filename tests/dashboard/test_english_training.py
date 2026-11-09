"""Focused A14.1 checks; temporary database and no external API calls."""
import copy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from backend.app.dashboard.auth import COOKIE
from backend.app.dashboard.materials import SOURCE, localized_scenario
from backend.app.dashboard.models import Scenario
from backend.app.dashboard.server import create_app


class Actor:
    request_count = 0
    trace = []

    async def customer_reply(self, context):
        self.context = copy.deepcopy(context)
        self.request_count += 1
        return {'speaker_role': 'customer',
                'customer_id': context['customer_dossier']['customer_id'],
                'reply': 'I do not know the cause of the fault yet.'}


class EnglishTraining(unittest.TestCase):
    def test_languages_snapshots_actor_and_reopen(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'OPENAI_API_KEY': 'synthetic-key'}):
            actor = Actor()
            path = Path(directory) / 'test.sqlite3'
            app = create_app(path, provider_factory=lambda mode: actor)
            user = app.state.auth.create_user('a141-test', 'A14.1', 'A141-test-password!', temporary=False)
            token, csrf = app.state.auth.issue(user['id'])
            headers = {'Origin': 'http://testserver', 'X-CSRF-Token': csrf}
            with TestClient(app, headers=headers, cookies={COOKIE: token}) as client:
                materials = client.get('/api/materials').json()
                for item in materials['scenarios'].values():
                    self.assertEqual(item['training_languages'], ['de', 'en', 'ru'])
                for source in SOURCE['scenarios']:
                    for language in ('en', 'de', 'ru'):
                        r = client.post('/api/sessions', json={'scenario_id': source['id'], 'mode': 'simple_actor',
                            'client_profile_id': 'decisive_oven', 'training_language': language})
                        self.assertEqual(r.status_code, 200, r.text)
                        session = r.json()['session']
                        saved = app.state.store.get_session(session['id'])
                        snapshot = saved['scenario_snapshot']
                        Scenario.model_validate(snapshot)
                        self.assertEqual(snapshot['language'], language)
                        self.assertEqual(saved['client_profile_snapshot']['scenario']['source_scenario'], snapshot)
                        self.assertEqual(saved['client_profile_snapshot']['persona']['character'],
                                         app.state.persona_service.get('decisive_oven')['persona']['character'])
                        for original, translated in zip(source['facts'], snapshot['facts']):
                            for field in ('id', 'status', 'stage', 'required', 'material'):
                                self.assertEqual(original.get(field, True), translated.get(field, True))
                        if language == 'en' and source['id'] == 'oven_uncertain':
                            r = client.post('/api/sessions/' + session['id'] + '/messages', json={
                                'text': 'Do you know the cause?', 'kind': 'message',
                                'version': session['version'], 'request_id': 'a141-english-check'})
                            self.assertEqual(r.status_code, 200, r.text)
                            self.assertEqual(actor.context['customer_dossier']['language'], 'en')
                            english = r.json()['session']
                edited = copy.deepcopy(SOURCE['scenarios'][0]); edited['opening'] = 'Mentor edit'
                self.assertEqual(localized_scenario(edited, 'en'), edited)
            reopened = create_app(path, provider_factory=lambda mode: actor)
            with TestClient(reopened, cookies={COOKIE: token}) as client:
                self.assertEqual(client.get('/api/sessions/' + english['id']).json()['session'], english)

    def test_english_dictation_uses_existing_provider_fields(self):
        import asyncio
        import httpx
        from backend.app.dashboard.transcription import transcribe
        captured = []
        class Client:
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
            async def post(self, url, **kwargs):
                captured.append(kwargs['data'])
                return httpx.Response(200, json={'text': 'What type of oven is it?'})
        with patch('backend.app.dashboard.transcription.check_audio', return_value=2), patch(
                'backend.app.dashboard.transcription.httpx.AsyncClient', return_value=Client()):
            for model in ('gpt-transcribe', 'whisper-1'):
                result = asyncio.run(transcribe(b'audio', 'wav', 'en', 'synthetic-key', model))
                self.assertEqual(result['text'], 'What type of oven is it?')
        self.assertEqual(captured[0]['languages[]'], 'en')
        self.assertEqual(captured[1]['language'], 'en')
