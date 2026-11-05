"""Offline request-boundary checks; no fabricated LLM integration responses."""
import hashlib
import json
from pathlib import Path
import runpy
import unittest

from backend.app.actor_prompt import build_actor_messages

ROOT = Path(__file__).resolve().parents[2]


class ActorBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.spike = runpy.run_path(str(ROOT / 'research/feasibility/feasibility_spike.py'))
        self.context = {'public_scenario': self.spike['PUBLIC'], 'released_facts': [], 'reaction': 'neutral'}

    def test_unreleased_card_is_absent(self):
        messages = build_actor_messages(self.context, [], 'Was ist passiert?')
        for fact in self.spike['FACTS'].values():
            self.assertNotIn(fact, messages[0]['content'])
        self.assertEqual(json.loads(messages[0]['content'].split('\n')[-1]), self.context)

    def test_only_released_fact_is_passed(self):
        self.context['released_facts'] = [self.spike['FACTS']['B']]
        system = build_actor_messages(self.context, [], 'Welches Budget?')[0]['content']
        self.assertIn(self.spike['FACTS']['B'], system)
        for key in ('A', 'C'):
            self.assertNotIn(self.spike['FACTS'][key], system)

    def test_private_context_and_system_history_are_rejected(self):
        with self.assertRaises(ValueError):
            build_actor_messages({**self.context, 'private_card': self.spike['FACTS']}, [], 'Frage')
        with self.assertRaises(ValueError):
            build_actor_messages(self.context, [{'role': 'system', 'content': 'untrusted'}], 'Frage')

    def test_history_is_copied_not_mutated(self):
        history = [{'role': 'user', 'content': 'Hallo'}]
        output = build_actor_messages(self.context, history, 'Frage')
        output[1]['content'] = 'Changed'
        self.assertEqual(history[0]['content'], 'Hallo')

    def test_director_and_archive_are_unchanged(self):
        manifest = json.loads((ROOT / 'reports/COPY_SHA256_MANIFEST.json').read_text())
        for item in manifest['files']:
            path = ROOT / 'research/feasibility' / item['path']
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), item['sha256_before'])
        old = json.loads((ROOT / 'research/feasibility/remediation/run-002/results.json').read_text())
        self.assertEqual(self.spike['DIRECTOR'], old['director_prompt'])


if __name__ == '__main__':
    unittest.main()
