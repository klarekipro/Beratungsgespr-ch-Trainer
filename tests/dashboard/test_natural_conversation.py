"""Integration regressions for the first user trial; all providers are synthetic."""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.dashboard.engine import build_report, process_turn
from backend.app.dashboard.exports import api_usage_label, mode_label
from backend.app.dashboard.providers import DemoProvider, ProviderError
from backend.app.dashboard.seeds import PREVIOUS_BUILTIN_SHA256, SEED_SCENARIOS
from backend.app.dashboard.server import create_app
from test_engine import decision, new_session, route, summary_position
from backend.app.dashboard.seeds import DEMO_WALKTHROUGH


class ConversationProvider:
    """Fake network stages used solely for transaction/state assertions."""
    def __init__(self, fact_ids=None, failure=None, omit_fact=False):
        self.fact_ids = fact_ids or ["goal"]
        self.failure = failure
        self.omit_fact = omit_fact
        self.request_count = 0
        self.contexts = []

    async def interpret(self, session, text, kind):
        self.request_count += 1
        return decision(act="question", fact_ids=self.fact_ids, source_quote=text)

    async def respond(self, context):
        self.request_count += 1
        self.contexts.append(copy.deepcopy(context))
        if self.failure:
            raise ProviderError(self.failure, "SYNTHETIC_NOT_FOR_USER")
        self.request_count += 1
        return {"reply": "Я ищу мастера для ремонта промышленной газовой печи.",
                "verified_fact_ids": [] if self.omit_fact else self.fact_ids}


class NaturalConversationStateTests(unittest.IsolatedAsyncioTestCase):
    async def test_live_customer_gets_only_authorized_facts_and_response_is_used(self):
        original = new_session(2, mode="openai")
        provider = ConversationProvider()
        updated = await process_turn(original, "Что вы имеете в виду?", "message", provider, 1)
        self.assertEqual(updated["state"]["discovered"], ["goal"])
        self.assertEqual(original["state"]["discovered"], [])
        self.assertEqual(updated["messages"][-1]["text"], "Я ищу мастера для ремонта промышленной газовой печи.")
        self.assertEqual(updated["messages"][-1]["source"], "openai_actor_verified")
        context = provider.contexts[0]
        self.assertEqual(context["must_address_fact_ids"], ["goal"])
        self.assertEqual([f["id"] for f in context["authorized_facts"]], ["goal"])
        for forbidden in ("state", "phase", "allowed_outcomes", "scenario_snapshot", "events"):
            self.assertNotIn(forbidden, context)
        encoded = json.dumps(context, ensure_ascii=False)
        for f in original["scenario_snapshot"]["facts"]:
            if f["id"] != "goal":
                self.assertNotIn(f["value"], encoded)

    async def test_unexpressed_planned_fact_cannot_be_marked_disclosed(self):
        original = new_session(2, mode="openai")
        snapshot = copy.deepcopy(original)
        with self.assertRaises(ProviderError):
            await process_turn(original, "Что вам нужно?", "message", ConversationProvider(omit_fact=True), 1)
        self.assertEqual(original, snapshot)

    async def test_missing_actor_never_falls_back_to_canned_customer_in_live_mode(self):
        from test_engine import FixedProvider
        original = new_session(2, mode="openai")
        with self.assertRaises(ProviderError) as caught:
            await process_turn(original, "Что вам нужно?", "message",
                               FixedProvider(decision(act="question", fact_ids=["goal"], source_quote="Что вам нужно?")), 1)
        self.assertEqual(caught.exception.code, "ai_actor_unavailable")
        self.assertEqual(len(original["messages"]), 1)

    async def test_optional_technical_details_do_not_force_summary_or_reopen(self):
        from test_engine import FixedProvider
        session = new_session(2)
        session = await process_turn(session, "Номер и мощность?", "message",
                                     FixedProvider(decision(act="question", fact_ids=["identification"], source_quote="Номер и мощность?")), 1)
        for n, turn in enumerate(DEMO_WALKTHROUGH[2]["turns"][:summary_position("needs", 2) + 1], 2):
            session = await process_turn(session, turn["text"], turn["kind"], DemoProvider(), n)
        self.assertTrue(session["state"]["needs_confirmed"])
        self.assertEqual(session["state"]["phase"], "capabilities")
        session = await process_turn(session, "Причину поломки", "message",
                                     FixedProvider(decision(act="question", fact_ids=["cause"], source_quote="Причину поломки")), 10)
        self.assertTrue(session["state"]["needs_confirmed"])
        self.assertEqual(session["state"]["phase"], "capabilities")
        self.assertNotIn("confirmation_reopened", [e["type"] for e in session["state"]["events"]])

    async def test_demo_report_never_assesses_free_conversation_skill(self):
        session = await process_turn(new_session(2), "Что вы имеете в виду?", "message", DemoProvider(), 1)
        report = build_report(session)
        self.assertIn("нельзя оценивать навык", report["summary"])
        self.assertIn("не доказанная ошибка ученика", report["findings"][0]["detail"])
        self.assertIn("без AI-вызовов", mode_label(session))

    async def test_seed_unknowns_are_explicit_author_data_not_runtime_invention(self):
        for index in (0, 2):
            facts = {f["id"]: f for f in SEED_SCENARIOS[index]["facts"]}
            self.assertEqual(facts["cause"]["status"], "does_not_know")
            self.assertEqual(facts["identification"]["status"], "does_not_know")
            self.assertFalse(facts["symptoms"]["required"])
            self.assertTrue(all(facts[k]["value"] for k in ("cause", "identification", "symptoms")))


class NaturalConversationHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="natural-customer-http-")
        self.path = Path(self.temp.name) / "trainer.sqlite3"
        self.env = patch.dict(os.environ, {"OPENAI_API_KEY": "synthetic-test-only", "OPENAI_MODEL": "synthetic-model"})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_success_counts_three_requests_and_duplicate_does_not_call_again(self):
        provider = ConversationProvider()
        with TestClient(create_app(self.path, provider_factory=lambda mode: provider)) as client:
            start = client.post("/api/sessions", json={"scenario_id": "oven_no_fit", "mode": "openai"}).json()["session"]
            payload = {"text": "Что вы имеете в виду?", "kind": "message", "request_id": "same_request", "version": start["version"]}
            result = client.post(f"/api/sessions/{start['id']}/messages", json=payload)
            self.assertEqual(result.status_code, 200, result.text)
            updated = result.json()["session"]
            self.assertEqual(updated["api_requests"], 3)
            self.assertEqual(updated["natural_customer_turns"], 1)
            duplicate = client.post(f"/api/sessions/{start['id']}/messages", json=payload)
            self.assertEqual(duplicate.json()["session"], updated)
            self.assertEqual(provider.request_count, 3)

    def test_scenario_gap_is_system_issue_without_fabricated_customer_message(self):
        provider = ConversationProvider(failure="scenario_missing_context")
        with TestClient(create_app(self.path, provider_factory=lambda mode: provider)) as client:
            start = client.post("/api/sessions", json={"scenario_id": "oven_no_fit", "mode": "openai"}).json()["session"]
            result = client.post(f"/api/sessions/{start['id']}/messages", json={
                "text": "Какой точный серийный номер?", "kind": "message", "request_id": "missing_context", "version": 1})
            self.assertEqual(result.status_code, 422, result.text)
            self.assertIn("не ошибка ученика", result.json()["error"]["message"])
            self.assertNotIn("SYNTHETIC_NOT_FOR_USER", result.text)
            after = client.get(f"/api/sessions/{start['id']}").json()["session"]
            self.assertEqual(after["messages"], start["messages"])
            self.assertEqual(after["version"], 1)
            self.assertEqual(after["phase"], "needs")
            self.assertEqual(after["api_requests"], 2)
            final = client.post(f"/api/sessions/{start['id']}/finish").json()["session"]
            self.assertIn("scenario_missing_context", [e["type"] for e in final["report"]["findings"]])

    def test_mode_must_be_explicit_and_key_does_not_convert_existing_demo(self):
        with TestClient(create_app(self.path)) as client:
            missing = client.post("/api/sessions", json={"scenario_id": "oven_no_fit"})
            self.assertEqual(missing.status_code, 422)
            demo = client.post("/api/sessions", json={"scenario_id": "oven_no_fit", "mode": "demo"}).json()["session"]
            self.assertEqual(client.get(f"/api/sessions/{demo['id']}").json()["session"]["mode"], "demo")
            self.assertEqual(demo["api_requests"], 0)

    def test_legacy_openai_counter_is_labelled_partial_after_update(self):
        provider = ConversationProvider()
        app = create_app(self.path, provider_factory=lambda mode: provider)
        with TestClient(app) as client:
            start = client.post("/api/sessions", json={"scenario_id": "oven_no_fit", "mode": "openai"}).json()["session"]
            legacy = app.state.store.get_session(start["id"])
            legacy.pop("live_requests")
            legacy.pop("api_count_complete")
            app.state.store.save_session(legacy)
            result = client.post(f"/api/sessions/{start['id']}/messages", json={
                "text": "Что вам нужно?", "kind": "message", "request_id": "legacy_counter", "version": 1})
            self.assertEqual(result.status_code, 200, result.text)
            self.assertEqual(result.json()["session"]["api_requests"], 3)
            self.assertFalse(result.json()["session"]["api_count_complete"])
            saved = app.state.store.get_session(start["id"])
            self.assertIn("ранние обращения неизвестны", api_usage_label(saved))

    def test_builtin_upgrade_preserves_snapshots_edited_cards_and_deletions(self):
        app = create_app(self.path)
        old = copy.deepcopy(SEED_SCENARIOS[2])
        old["facts"] = [f for f in old["facts"] if f["id"] not in {"symptoms", "identification", "cause"}]
        for fact in old["facts"]:
            fact.pop("material", None)
        old["revision"] = 1
        digest = hashlib.sha256(json.dumps(old, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        self.assertEqual(digest, PREVIOUS_BUILTIN_SHA256["oven_no_fit"])
        app.state.store.save_scenario(old)
        edited = copy.deepcopy(SEED_SCENARIOS[0])
        edited["facts"] = [f for f in edited["facts"] if f["id"] not in {"symptoms", "identification", "cause"}]
        for fact in edited["facts"]:
            fact.pop("material", None)
        edited["revision"] = 2
        edited["title"] = "Карточка, исправленная наставником"
        app.state.store.save_scenario(edited)
        app.state.store.delete_scenario("oven_replacement")
        with TestClient(app) as client:
            original = client.post("/api/sessions", json={"scenario_id": "oven_no_fit", "mode": "demo"}).json()["session"]
        refreshed = create_app(self.path)
        self.assertEqual(refreshed.state.store.get_scenario("oven_no_fit")["revision"], 2)
        self.assertEqual(refreshed.state.store.get_scenario("oven_uncertain"), edited)
        self.assertIsNone(refreshed.state.store.get_scenario("oven_replacement"))
        saved = refreshed.state.store.get_session(original["id"])
        self.assertEqual(saved["scenario_snapshot"], old)


if __name__ == "__main__":
    unittest.main()
