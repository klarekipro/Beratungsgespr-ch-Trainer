"""HTTP acceptance for the local dashboard; no network or paid model calls.

These tests exercise the real API and SQLite repository with a temporary database.
They do not establish model quality, educational effectiveness, or multi-user auth.
"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.dashboard.server import create_app


MENTOR = {"X-Workspace-Role": "mentor"}
PRIVATE_KEYS = {
    "scenario_snapshot", "company_snapshot", "facts", "allowed_outcomes",
    "discovered", "state", "events", "receipts", "live_attempts",
}


def object_keys(value):
    if isinstance(value, dict):
        yield from value.keys()
        for child in value.values():
            yield from object_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from object_keys(child)


def string_values(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from string_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from string_values(child)


class FailingProvider:
    """Deliberate synthetic upstream failure; it never sends an HTTP request."""

    def __init__(self):
        self.calls = 0

    async def interpret(self, session, text, kind):
        self.calls += 1
        raise RuntimeError("SYNTHETIC_UPSTREAM_DEBUG_DO_NOT_RETURN")


class DashboardHTTPTests(unittest.TestCase):
    def setUp(self):
        # Even a developer who has a real key must not use it in this suite.
        self.environment = patch.dict(os.environ, {"OPENAI_API_KEY": ""})
        self.environment.start()
        self.temp = tempfile.TemporaryDirectory(prefix="consultation-http-")
        self.database = Path(self.temp.name) / "dashboard.sqlite3"
        self.clients = []
        self.client = self.new_client()

    def tearDown(self):
        while self.clients:
            self.close_client(self.clients[-1])
        self.temp.cleanup()
        self.environment.stop()

    def new_client(self, provider_factory=None):
        app = create_app(data_path=self.database, provider_factory=provider_factory)
        client = TestClient(app, raise_server_exceptions=False)
        client.__enter__()
        self.clients.append(client)
        return client

    def close_client(self, client):
        if client in self.clients:
            self.clients.remove(client)
            client.__exit__(None, None, None)

    def ok(self, response):
        self.assertIn(response.status_code, (200, 201), response.text)
        return response.json()

    def error(self, response, statuses):
        self.assertIn(response.status_code, statuses, response.text)
        body = response.json()
        self.assertIsInstance(body.get("error"), dict, body)
        self.assertIsInstance(body["error"].get("code"), str, body)
        self.assertIsInstance(body["error"].get("message"), str, body)
        self.assertNotIn("Traceback", response.text)
        return body

    def scenarios(self, mentor=False, client=None):
        client = client or self.client
        path = "/api/mentor/scenarios" if mentor else "/api/scenarios"
        return self.ok(client.get(path, headers=MENTOR if mentor else {}))["scenarios"]

    def start(self, scenario_id=None, mode="demo", client=None):
        client = client or self.client
        scenario_id = scenario_id or self.scenarios(client=client)[0]["id"]
        return self.ok(client.post("/api/sessions", json={
            "scenario_id": scenario_id, "mode": mode,
        }))["session"]

    def turn(self, session, text="Что для вас сейчас самое важное?", kind="message",
             request_id=None, client=None):
        client = client or self.client
        body = {
            "text": text, "kind": kind,
            "request_id": request_id or str(uuid4()), "version": session["version"],
        }
        return client.post(f"/api/sessions/{session['id']}/messages", json=body)

    def finish(self, session, client=None):
        client = client or self.client
        return self.ok(client.post(f"/api/sessions/{session['id']}/finish"))["session"]

    def test_status_discloses_local_demo_and_missing_key_without_calling_provider(self):
        failing = FailingProvider()
        client = self.new_client(lambda mode: failing)
        body = self.ok(client.get("/api/status"))
        self.assertEqual(body["storage"], "sqlite")
        self.assertEqual(body["access_mode"], "local_workspaces")
        self.assertCountEqual(body["roles"], ["mentor", "learner"])
        self.assertFalse(body["ai"]["configured"])
        self.assertFalse(body["ai"]["live_enabled"])
        self.assertGreater(body["limits"]["max_turns"], 0)
        self.assertNotIn("api_key", json.dumps(body).lower())
        self.assertEqual(failing.calls, 0)

    def test_private_card_never_appears_in_catalogue_active_session_or_history(self):
        authored = copy.deepcopy(self.scenarios(mentor=True)[0])
        authored["id"] = "privacy_acceptance"
        marker = "Уникальное скрытое обстоятельство privacy_acceptance_721."
        authored["facts"][0]["value"] = marker
        self.ok(self.client.post("/api/mentor/scenarios", json=authored, headers=MENTOR))
        for response in (
            self.client.get("/api/scenarios"),
            self.client.post("/api/sessions", json={
                "scenario_id": authored["id"], "mode": "demo",
            }),
            self.client.get("/api/sessions"),
        ):
            body = self.ok(response)
            self.assertNotIn(marker, json.dumps(body, ensure_ascii=False))
            self.assertFalse(PRIVATE_KEYS.intersection(object_keys(body)), body)
            self.assertNotIn("report", set(object_keys(body)))
        sessions = self.ok(self.client.get("/api/sessions"))["sessions"]
        active = self.ok(self.client.get(f"/api/sessions/{sessions[0]['id']}"))["session"]
        self.assertFalse(PRIVATE_KEYS.intersection(object_keys(active)), active)
        self.assertNotIn(marker, json.dumps(active, ensure_ascii=False))

    def test_mentor_interface_header_is_required_but_is_not_claimed_as_authentication(self):
        self.error(self.client.get("/api/mentor/scenarios"), {403})
        self.error(self.client.get("/api/mentor/scenarios", headers={
            "X-Workspace-Role": "learner",
        }), {403})
        self.assertGreaterEqual(len(self.scenarios(mentor=True)), 3)
        company = self.ok(self.client.get("/api/company"))["company"]
        self.error(self.client.put("/api/mentor/company", json=company), {403})
        self.error(self.client.get("/api/mentor/reviews"), {403})

    def test_missing_key_rejects_openai_session_instead_of_falling_back_to_demo(self):
        response = self.client.post("/api/sessions", json={
            "scenario_id": self.scenarios()[0]["id"], "mode": "openai",
        })
        self.error(response, {400, 409, 503})
        self.assertEqual(self.ok(self.client.get("/api/sessions"))["sessions"], [])

    def test_unknown_mode_and_unfilled_or_invalid_scenario_are_rejected(self):
        self.error(self.client.post("/api/sessions", json={
            "scenario_id": self.scenarios()[0]["id"], "mode": "automatic",
        }), {400, 422})
        original = self.scenarios(mentor=True)[0]
        for mutation in ("empty_value", "duplicate_id", "unknown_outcome", "unknown_status"):
            with self.subTest(mutation=mutation):
                draft = copy.deepcopy(original)
                draft["id"] = "invalid_acceptance"
                if mutation == "empty_value":
                    draft["facts"][0]["value"] = ""
                    draft["facts"][0]["required"] = True
                elif mutation == "duplicate_id":
                    draft["facts"].append(copy.deepcopy(draft["facts"][0]))
                elif mutation == "unknown_outcome":
                    draft["allowed_outcomes"] = ["service_that_does_not_exist"]
                else:
                    draft["facts"][0]["status"] = "author_did_not_fill_it"
                self.error(self.client.post("/api/mentor/scenarios", json=draft,
                                            headers=MENTOR), {400, 422})
        self.assertNotIn("invalid_acceptance", {c["id"] for c in self.scenarios()})
        # Every accepted explicit scenario ID must also be usable to start a session.
        for invalid_id in ("-case", "_case"):
            with self.subTest(scenario_id=invalid_id):
                draft = copy.deepcopy(original)
                draft["id"] = invalid_id
                self.error(self.client.post("/api/mentor/scenarios", json=draft,
                                            headers=MENTOR), {400, 422})
                self.assertNotIn(invalid_id, {c["id"] for c in self.scenarios()})

    def test_unreviewed_company_cannot_start_a_training(self):
        company = self.ok(self.client.get("/api/company"))["company"]
        company["reviewed"] = False
        self.ok(self.client.put("/api/mentor/company", json=company, headers=MENTOR))
        self.error(self.client.post("/api/sessions", json={
            "scenario_id": self.scenarios()[0]["id"], "mode": "demo",
        }), {400, 409, 422})
        self.assertEqual(self.ok(self.client.get("/api/sessions"))["sessions"], [])

    def test_edits_and_deletion_do_not_rewrite_existing_session_snapshots(self):
        authored = copy.deepcopy(self.scenarios(mentor=True)[0])
        authored["id"] = "snapshot_acceptance"
        old_value = "Первое скрытое значение snapshot_acceptance."
        new_value = "Второе скрытое значение snapshot_acceptance."
        authored["facts"][0]["value"] = old_value
        saved = self.ok(self.client.post("/api/mentor/scenarios", json=authored,
                                        headers=MENTOR))["scenario"]
        old_session = self.start(saved["id"])
        old_company = copy.deepcopy(old_session["company"])
        company = self.ok(self.client.get("/api/company"))["company"]
        company["name"] = "Изменённая учебная компания"
        company["description"] += " Изменение только будущих тренировок."
        updated_company = self.ok(self.client.put("/api/mentor/company", json=company,
                                                 headers=MENTOR))["company"]
        self.assertGreater(updated_company["revision"], old_company["revision"])
        saved["title"] = "Изменённая карточка"
        saved["facts"][0]["value"] = new_value
        updated_scenario = self.ok(self.client.post("/api/mentor/scenarios", json=saved,
                                                  headers=MENTOR))["scenario"]
        self.assertGreater(updated_scenario["revision"], saved["revision"])
        future_session = self.start(saved["id"])
        self.assertEqual(future_session["company"]["name"], updated_company["name"])
        self.ok(self.client.delete(f"/api/mentor/scenarios/{saved['id']}", headers=MENTOR))
        self.assertNotIn(saved["id"], {c["id"] for c in self.scenarios()})
        preserved = self.ok(self.client.get(f"/api/sessions/{old_session['id']}"))["session"]
        self.assertEqual(preserved["company"], old_company)
        self.assertEqual(preserved["title"], old_session["title"])
        old_finished = self.finish(old_session)
        future_finished = self.finish(future_session)
        self.assertIn(old_value, set(string_values(old_finished["report"])))
        self.assertNotIn(new_value, set(string_values(old_finished["report"])))
        self.assertIn(new_value, set(string_values(future_finished["report"])))

    def test_duplicate_delivery_does_not_create_turn_and_conflicts_do_not_mutate(self):
        session = self.start()
        request_id = str(uuid4())
        first = self.ok(self.turn(session, request_id=request_id))["session"]
        self.assertEqual(first["turn_count"], session["turn_count"] + 1)
        self.assertEqual(len(first["messages"]), len(session["messages"]) + 2)
        second = self.ok(self.turn(session, request_id=request_id))["session"]
        self.assertEqual(second, first)
        self.error(self.turn(session, text="Другой текст с прежним request_id",
                             request_id=request_id), {409})
        self.error(self.turn(session, text="Новый запрос с устаревшей версией"), {409})
        current = self.ok(self.client.get(f"/api/sessions/{session['id']}"))["session"]
        self.assertEqual(current, first)

    def test_provider_error_is_sanitized_and_does_not_create_fake_progress(self):
        failing = FailingProvider()
        # Exercise the live-mode HTTP path with an injected, non-network provider.
        # This placeholder is not a credential and is never used for HTTP auth.
        with patch.dict(os.environ, {"OPENAI_API_KEY": "synthetic-test-placeholder"}):
            client = self.new_client(lambda mode: failing)
        before = self.start(client=client, mode="openai")
        response = self.turn(before, client=client)
        self.error(response, {500, 502, 503, 504})
        self.assertNotIn("SYNTHETIC_UPSTREAM_DEBUG_DO_NOT_RETURN", response.text)
        after = self.ok(client.get(f"/api/sessions/{before['id']}"))["session"]
        for field in ("messages", "phase", "turn_count", "version", "status", "mode"):
            self.assertEqual(after[field], before[field], field)
        self.assertEqual(failing.calls, 1)

    def test_early_offer_disguised_as_summary_is_preserved_in_final_review(self):
        before = self.start("oven_uncertain")
        after = self.ok(self.turn(before, text="Предлагаю сразу купить новую печь.",
                                  kind="summary"))["session"]
        self.assertEqual(after["phase"], "needs")
        self.assertEqual(after["turn_count"], 1)
        report = self.finish(after)["report"]
        self.assertEqual(report["status"], "incomplete")
        self.assertIsNone(report["outcome"])
        early = [event for event in report["findings"] if event["type"] == "early_proposal"]
        self.assertEqual(len(early), 1)
        self.assertEqual(early[0]["turn"], 1)
        self.assertFalse(report["stages"][0]["confirmed"])
        self.assertFalse(report["stages"][1]["confirmed"])

    def test_sqlite_survives_a_new_app_instance(self):
        session = self.start()
        session = self.ok(self.turn(session))["session"]
        company = self.ok(self.client.get("/api/company"))["company"]
        company["name"] = "Сохранённая учебная компания"
        company = self.ok(self.client.put("/api/mentor/company", json=company,
                                         headers=MENTOR))["company"]
        # Removed seed cards must not silently reappear on the next startup.
        self.ok(self.client.delete(f"/api/mentor/scenarios/{session['scenario_id']}",
                                   headers=MENTOR))
        self.close_client(self.client)
        restarted = self.new_client()
        actual = self.ok(restarted.get(f"/api/sessions/{session['id']}"))["session"]
        self.assertEqual(actual, session)
        self.assertEqual(self.ok(restarted.get("/api/company"))["company"], company)
        self.assertNotIn(session["scenario_id"],
                         {s["id"] for s in self.scenarios(client=restarted)})
        self.assertTrue(self.database.is_file())

    def test_finish_incomplete_exports_dialogue_and_prevents_further_turns(self):
        session = self.start()
        utterance = "Что привело вас к нам сегодня?"
        session = self.ok(self.turn(session, text=utterance))["session"]
        for extension in ("txt", "pdf", "json"):
            with self.subTest(before_finish=extension):
                self.error(self.client.get(f"/api/sessions/{session['id']}/export.{extension}"),
                           {403, 409})
        finished = self.finish(session)
        self.assertEqual(finished["status"], "finished")
        self.assertEqual(finished["report"]["status"], "incomplete")
        self.assertFalse(all(s["confirmed"] for s in finished["report"]["stages"]))
        self.assertTrue(finished["report"]["limitations"])
        self.error(self.turn(finished), {409})
        for extension, content_type in (("txt", "text/plain"), ("pdf", "application/pdf"),
                                        ("json", "application/json")):
            with self.subTest(after_finish=extension):
                response = self.client.get(f"/api/sessions/{session['id']}/export.{extension}")
                self.assertEqual(response.status_code, 200, response.text[:200])
                self.assertIn(content_type, response.headers["content-type"])
                self.assertIn("attachment", response.headers.get("content-disposition", ""))
                if extension == "txt":
                    self.assertIn(utterance, response.text)
                    self.assertIn(finished["customer_name"], response.text)
                    self.assertIn("Техническая проверка" if finished["mode"] == "demo"
                                  else "OpenAI", response.text)
                elif extension == "json":
                    values = set(string_values(response.json()))
                    self.assertIn(utterance, values)
                    self.assertIn(finished["mode"], values)
                else:
                    self.assertTrue(response.content.startswith(b"%PDF-"))
                    self.assertIn(b"%%EOF", response.content[-128:])
                    self.assertGreater(len(response.content), 2000)
        after = self.ok(self.client.get(f"/api/sessions/{session['id']}"))["session"]
        self.assertEqual(after["messages"], finished["messages"])

    def test_submission_is_explicit_and_only_submitted_sessions_are_reviewable(self):
        session = self.start()
        review_path = f"/api/mentor/reviews/{session['id']}"
        self.error(self.client.post(f"/api/sessions/{session['id']}/submit"), {409})
        self.error(self.client.get(review_path, headers=MENTOR), {403, 404, 409})
        self.finish(session)
        self.assertEqual(self.ok(self.client.get("/api/mentor/reviews", headers=MENTOR))
                         ["sessions"], [])
        self.error(self.client.get(review_path, headers=MENTOR), {403, 404, 409})
        self.error(self.client.post(review_path, json={"note": "Не отправлено."},
                                   headers=MENTOR), {403, 404, 409})
        submitted = self.ok(self.client.post(f"/api/sessions/{session['id']}/submit"))["session"]
        self.assertEqual(submitted["review_status"], "submitted")
        queue = self.ok(self.client.get("/api/mentor/reviews", headers=MENTOR))["sessions"]
        self.assertEqual([s["id"] for s in queue], [session["id"]])
        self.assertIn("report", self.ok(self.client.get(review_path, headers=MENTOR))["session"])
        note = "Сначала выясните желаемый результат и проверьте понимание у клиента."
        reviewed = self.ok(self.client.post(review_path, json={"note": note},
                                           headers=MENTOR))["session"]
        self.assertEqual(reviewed["review_status"], "reviewed")
        learner = self.ok(self.client.get(f"/api/sessions/{session['id']}"))["session"]
        self.assertEqual(learner["review_note"], note)
        self.assertEqual(learner["review_status"], "reviewed")

    def test_foreign_origin_cannot_create_sessions_or_change_company(self):
        company = self.ok(self.client.get("/api/company"))["company"]
        scenario_id = self.scenarios()[0]["id"]
        for origin in ("https://untrusted.invalid", "null"):
            with self.subTest(origin=origin):
                self.error(self.client.post("/api/sessions", json={
                    "scenario_id": scenario_id, "mode": "demo",
                }, headers={"Origin": origin}), {403})
                changed = dict(company, name="Недопустимое изменение")
                self.error(self.client.put("/api/mentor/company", json=changed,
                                           headers={**MENTOR, "Origin": origin}), {403})
        self.assertEqual(self.ok(self.client.get("/api/company"))["company"], company)
        self.assertEqual(self.ok(self.client.get("/api/sessions"))["sessions"], [])
        response = self.client.post("/api/sessions", json={
            "scenario_id": scenario_id, "mode": "demo",
        }, headers={"Origin": "http://testserver"})
        self.ok(response)
        self.assertNotEqual(response.headers.get("access-control-allow-origin"), "*")

    def test_invalid_messages_are_bounded_and_cannot_advance_session(self):
        before = self.start()
        for text in ("", " " * 20, "вопрос " * 2000):
            with self.subTest(length=len(text)):
                self.error(self.turn(before, text=text), {400, 413, 422})
        after = self.ok(self.client.get(f"/api/sessions/{before['id']}"))["session"]
        self.assertEqual(after["messages"], before["messages"])
        self.assertEqual(after["version"], before["version"])

    def test_seeded_walkthroughs_reach_grounded_completion_including_no_fit(self):
        from backend.app.dashboard.seeds import DEMO_WALKTHROUGH
        self.assertGreaterEqual(len(DEMO_WALKTHROUGH), 3)
        outcomes = []
        for example in DEMO_WALKTHROUGH:
            with self.subTest(scenario_id=example["scenario_id"]):
                session = self.start(example["scenario_id"])
                for turn in example["turns"]:
                    session = self.ok(self.turn(session, text=turn["text"],
                                                kind=turn.get("kind", "message")))["session"]
                self.assertEqual(session["phase"], "completed")
                finished = self.finish(session)
                report = finished["report"]
                self.assertEqual(report["status"], "complete")
                self.assertTrue(all(stage["confirmed"] for stage in report["stages"]))
                self.assertTrue(report["limitations"])
                outcomes.append(report["outcome"])
        self.assertIn("no_fit", outcomes)


if __name__ == "__main__":
    unittest.main()
