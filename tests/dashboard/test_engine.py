"""Offline engine/transport contract checks, never real AI quality claims."""

import json
import unittest
from copy import deepcopy

import httpx

from backend.app.dashboard.engine import build_report, initial_state, process_turn
from backend.app.dashboard.providers import DemoProvider, OpenAIProvider, ProviderError
from backend.app.dashboard.seeds import DEMO_WALKTHROUGH, SEED_COMPANY, SEED_SCENARIOS


def new_session(index=0, mode="demo"):
    scenario = deepcopy(SEED_SCENARIOS[index])
    return {
        "id": "test_session", "scenario_id": scenario["id"], "status": "active", "mode": mode,
        "state": initial_state(), "company_snapshot": deepcopy(SEED_COMPANY), "scenario_snapshot": scenario,
        "messages": [{"role": "customer", "text": scenario["opening"], "at": "2026-11-05T00:00:00Z", "turn": 0}],
        "version": 0, "receipts": {}, "live_attempts": 0,
    }


def decision(**changes):
    value = {
        "act": "other", "fact_ids": [], "summary_ok": False, "summary_evidence": [],
        "proposal_outcome": None, "proposal_ok": False, "source_quote": "", "uncertain": False,
    }
    value.update(changes)
    return value


class FixedProvider:
    def __init__(self, result):
        self.result = result

    async def interpret(self, session, text, kind):
        return deepcopy(self.result)


async def route(index=0, omit_offer=False):
    session = new_session(index)
    turns = DEMO_WALKTHROUGH[index]["turns"]
    if omit_offer:
        turns = turns[:-1]
    for number, turn in enumerate(turns, 1):
        session = await process_turn(session, turn["text"], turn["kind"], DemoProvider(), number)
    return session


def summary_position(phase, index=0):
    positions = [number for number, turn in enumerate(DEMO_WALKTHROUGH[index]["turns"])
                 if turn["kind"] == "summary"]
    return positions[0 if phase == "needs" else 1]


class ConsultationEngineTests(unittest.IsolatedAsyncioTestCase):
    async def test_all_authored_routes_finish_with_distinct_grounded_outcomes(self):
        outcomes = []
        for index in range(3):
            with self.subTest(scenario=SEED_SCENARIOS[index]["id"]):
                session = await route(index)
                report = build_report(session)
                self.assertEqual(session["state"]["phase"], "completed")
                self.assertEqual(report["status"], "complete")
                self.assertTrue(all(stage["confirmed"] for stage in report["stages"]))
                self.assertIn("без вызова AI", report["limitations"][0])
                self.assertEqual(len(session["messages"]), 1 + len(DEMO_WALKTHROUGH[index]["turns"]) * 2)
                outcomes.append(session["state"]["outcome"])
        self.assertEqual(outcomes, ["diagnosis", "replacement", "no_fit"])

    async def test_early_offer_is_found_inside_question_even_with_message_kind(self):
        session = new_session()
        result = await process_turn(session, "Какой у вас бюджет? Предлагаю сразу новую печь.", "message", DemoProvider(), 1)
        self.assertEqual(result["state"]["phase"], "needs")
        self.assertEqual(result["state"]["discovered"], [])
        self.assertEqual(result["state"]["events"][-1]["type"], "early_proposal")
        self.assertEqual(session["state"]["events"], [])

    async def test_proposal_disguised_as_summary_cannot_skip_the_gate(self):
        result = await process_turn(new_session(), "Предлагаю диагностику электрической печи.", "summary", DemoProvider(), 1)
        self.assertEqual(result["state"]["events"][-1]["type"], "early_proposal")
        self.assertFalse(result["state"]["needs_confirmed"])

    async def test_preference_question_is_not_an_offer(self):
        result = await process_turn(new_session(), "Вы хотите ремонт или замену?", "message", DemoProvider(), 1)
        self.assertIn("goal", result["state"]["discovered"])
        self.assertNotIn("early_proposal", [e["type"] for e in result["state"]["events"]])
        self.assertIn("пока не выбраны", result["messages"][-1]["text"])

    async def test_discovery_alone_never_confirms_needs_or_capabilities(self):
        session = new_session()
        questions = [turn for turn in DEMO_WALKTHROUGH[0]["turns"] if turn["kind"] == "message"]
        for number, turn in enumerate(questions, 1):
            session = await process_turn(session, turn["text"], turn["kind"], DemoProvider(), number)
        required = {f["id"] for f in SEED_SCENARIOS[0]["facts"] if f["required"]}
        self.assertTrue(required.issubset(session["state"]["discovered"]))
        self.assertFalse(session["state"]["needs_confirmed"])
        self.assertFalse(session["state"]["capabilities_confirmed"])
        session = await process_turn(session, DEMO_WALKTHROUGH[0]["turns"][-1]["text"], "proposal", DemoProvider(), len(questions) + 1)
        self.assertEqual(session["state"]["events"][-1]["type"], "early_proposal")

    async def test_correct_guess_without_discovery_is_not_confirmed_or_disclosed(self):
        summary_at = summary_position("needs")
        text = DEMO_WALKTHROUGH[0]["turns"][summary_at]["text"]
        result = await process_turn(new_session(), text, "summary", DemoProvider(), 1)
        self.assertFalse(result["state"]["needs_confirmed"])
        self.assertEqual(result["state"]["discovered"], [])
        for fact in SEED_SCENARIOS[0]["facts"]:
            self.assertNotIn(fact["value"], result["messages"][-1]["text"])

        # The diagnostic action requires a supported equipment type. Knowing the
        # other needs must not allow an unasked guess about that type to close N.
        equipment = next(fact for fact in SEED_SCENARIOS[0]["facts"] if fact["id"] == "equipment")
        self.assertTrue(equipment["required"])
        partial = new_session()
        questions = [turn for turn in DEMO_WALKTHROUGH[0]["turns"][:summary_at]
                     if "типа ваша печь" not in turn["text"]]
        for number, turn in enumerate(questions, 1):
            partial = await process_turn(partial, turn["text"], turn["kind"], DemoProvider(), number)
        self.assertNotIn("equipment", partial["state"]["discovered"])
        partial = await process_turn(partial, text, "summary", DemoProvider(), len(questions) + 1)
        self.assertFalse(partial["state"]["needs_confirmed"])
        self.assertNotIn(equipment["value"], partial["messages"][-1]["text"])

    async def test_wrong_budget_summary_is_corrected_without_closing_stage(self):
        session = new_session()
        summary_at = summary_position("capabilities")
        for number, turn in enumerate(DEMO_WALKTHROUGH[0]["turns"][:summary_at], 1):
            session = await process_turn(session, turn["text"], turn["kind"], DemoProvider(), number)
        false_summary = DEMO_WALKTHROUGH[0]["turns"][summary_at]["text"].replace(
            "Бюджет пока не определён. Сначала нужна оценка стоимости.", "Бюджет не ограничен, можно покупать любую печь.")
        corrected = await process_turn(session, false_summary, "summary", DemoProvider(), summary_at + 1)
        self.assertEqual(corrected["state"]["phase"], "capabilities")
        self.assertFalse(corrected["state"]["capabilities_confirmed"])
        self.assertIn("Бюджет пока не определён", corrected["messages"][-1]["text"])
        correct = DEMO_WALKTHROUGH[0]["turns"][summary_at]
        fixed = await process_turn(corrected, correct["text"], correct["kind"], DemoProvider(), summary_at + 2)
        self.assertEqual(fixed["state"]["phase"], "proposal")
        self.assertTrue(fixed["state"]["capabilities_confirmed"])
        self.assertNotIn("8 000", json.dumps(fixed["messages"], ensure_ascii=False))

    async def test_added_negation_or_extra_claim_does_not_pass_demo_summary(self):
        session = new_session()
        summary_at = summary_position("needs")
        for number, turn in enumerate(DEMO_WALKTHROUGH[0]["turns"][:summary_at], 1):
            session = await process_turn(session, turn["text"], turn["kind"], DemoProvider(), number)
        good = DEMO_WALKTHROUGH[0]["turns"][summary_at]["text"]
        for bad in (good.replace("Важно понять", "Не важно понять"), good + " Вы уже согласны купить новую печь."):
            with self.subTest(text=bad):
                result = await process_turn(session, bad, "summary", DemoProvider(), summary_at + 1)
                self.assertFalse(result["state"]["needs_confirmed"])
                self.assertEqual(result["state"]["events"][-1]["type"], "summary_not_confirmed")

    async def test_early_capability_answer_is_kept_and_sequence_noted(self):
        session = await process_turn(new_session(), "Какой у вас бюджет?", "message", DemoProvider(), 1)
        self.assertIn("budget", session["state"]["discovered"])
        self.assertIn("capabilities_before_needs", [e["type"] for e in session["state"]["events"]])
        for number, turn in enumerate(DEMO_WALKTHROUGH[0]["turns"][:summary_position("needs") + 1], 2):
            session = await process_turn(session, turn["text"], turn["kind"], DemoProvider(), number)
        self.assertEqual(session["state"]["phase"], "capabilities")
        self.assertIn("budget", session["state"]["discovered"])
        self.assertFalse(session["state"]["capabilities_confirmed"])

    async def test_complete_stages_do_not_authorize_wrong_action_or_omitted_conditions(self):
        ready = await route(0, omit_offer=True)
        for proposal in (
            "Предлагаю ремонт электрической печи. " + SEED_COMPANY["services"][1]["conditions"],
            "Предлагаю диагностику электрической печи.",
            DEMO_WALKTHROUGH[0]["turns"][-1]["text"].replace("90 €", "900 €"),
        ):
            with self.subTest(proposal=proposal):
                result = await process_turn(ready, proposal, "proposal", DemoProvider(), len(DEMO_WALKTHROUGH[0]["turns"]))
                self.assertEqual(result["state"]["phase"], "proposal")
                self.assertIsNone(result["state"]["outcome"])
                self.assertEqual(result["state"]["events"][-1]["type"], "proposal_not_grounded")

    async def test_new_material_fact_invalidates_previous_confirmation(self):
        session = new_session()
        session["scenario_snapshot"]["facts"].append({
            "id": "access", "stage": "capabilities", "label": "Условия доступа к оборудованию",
            "value": "Доступ к печи возможен только по выходным.", "status": "known",
            "keywords": ["доступ"], "required": False,
        })
        for number, turn in enumerate(DEMO_WALKTHROUGH[0]["turns"][:-1], 1):
            session = await process_turn(session, turn["text"], turn["kind"], DemoProvider(), number)
        self.assertEqual(session["state"]["phase"], "proposal")
        next_turn = len(DEMO_WALKTHROUGH[0]["turns"])
        session = await process_turn(session, "Когда возможен доступ к печи?", "message", DemoProvider(), next_turn)
        self.assertFalse(session["state"]["capabilities_confirmed"])
        self.assertEqual(session["state"]["phase"], "capabilities")
        self.assertIn("confirmation_reopened", [event["type"] for event in session["state"]["events"]])
        old_summary = DEMO_WALKTHROUGH[0]["turns"][summary_position("capabilities")]["text"]
        session = await process_turn(session, old_summary, "summary", DemoProvider(), next_turn + 1)
        self.assertFalse(session["state"]["capabilities_confirmed"])

    async def test_forged_quote_and_unknown_id_are_rejected_without_progress(self):
        for forged in (
            decision(act="question", fact_ids=["budget"], source_quote="I did not say this"),
            decision(act="question", fact_ids=["invented_secret"], source_quote="Бюджет?"),
            decision(act="summary", summary_ok=True,
                     summary_evidence=[{"fact_id": "budget", "quote": "Бюджет?"}], source_quote="Бюджет?"),
            decision(act="question", fact_ids=["budget"], source_quote="Бюджет?", uncertain=0),
            decision(act=["question"], fact_ids=["budget"], source_quote="Бюджет?"),
        ):
            with self.subTest(forged=forged):
                session = new_session()
                saved = deepcopy(session)
                with self.assertRaises(ProviderError):
                    await process_turn(session, "Бюджет?", "message", FixedProvider(forged), 1)
                self.assertEqual(session, saved)

    async def test_provider_cannot_mutate_session_even_when_it_raises(self):
        class BrokenProvider:
            async def interpret(self, session, text, kind):
                session["state"]["phase"] = "completed"
                session["scenario_snapshot"]["facts"] = []
                raise ProviderError("ai_timeout", "Timeout")
        session = new_session()
        saved = deepcopy(session)
        with self.assertRaises(ProviderError):
            await process_turn(session, "Какой бюджет?", "message", BrokenProvider(), 1)
        self.assertEqual(session, saved)

    async def test_uncertain_interpretation_neither_reveals_nor_confirms(self):
        result = await process_turn(new_session(), "А это?", "message", FixedProvider(
            decision(act="question", fact_ids=["budget"], source_quote="А это?", uncertain=True)), 1)
        self.assertEqual(result["state"]["discovered"], [])
        self.assertFalse(result["state"]["needs_confirmed"])
        self.assertEqual(result["state"]["events"][-1]["type"], "interpretation_uncertain")

    async def test_missing_author_value_is_scenario_error_not_unknown_customer(self):
        session = new_session()
        session["scenario_snapshot"]["facts"][0]["value"] = ""
        with self.assertRaises(ProviderError) as error:
            await process_turn(session, "Что вам нужно?", "message", DemoProvider(), 1)
        self.assertEqual(error.exception.code, "scenario_invalid")
        self.assertEqual(len(session["messages"]), 1)

    async def test_recovery_does_not_erase_early_offer_from_report(self):
        session = await process_turn(new_session(), "Предлагаю новую печь.", "message", DemoProvider(), 1)
        for number, turn in enumerate(DEMO_WALKTHROUGH[0]["turns"], 2):
            session = await process_turn(session, turn["text"], turn["kind"], DemoProvider(), number)
        report = build_report(session)
        self.assertEqual(report["status"], "complete")
        self.assertIn("early_proposal", [finding["type"] for finding in report["findings"]])
        self.assertIn("Раннее предложение", report["summary"])


def response_body(value):
    return {"status": "completed", "output": [{"type": "message", "role": "assistant",
            "content": [{"type": "output_text", "text": json.dumps(value, ensure_ascii=False)}]}]}


class ResponsesTransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_request_contains_only_disclosed_values_and_uses_strict_responses_schema(self):
        requests = []
        async def handler(request):
            requests.append(request)
            return httpx.Response(200, json=response_body(decision(
                act="question", fact_ids=["budget"], source_quote="Какой у вас бюджет?")))
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAIProvider("test-not-a-real-secret", "gpt-4.1-mini-2025-04-14", client=client)
            original = new_session(mode="openai")
            result = await provider.interpret(original, "Какой у вас бюджет?", "message")
        self.assertEqual(len(requests), 1)
        request = requests[0]
        payload = json.loads(request.content)
        self.assertEqual(str(request.url), "https://api.openai.com/v1/responses")
        self.assertFalse(payload["store"])
        self.assertEqual(payload["text"]["format"]["type"], "json_schema")
        self.assertTrue(payload["text"]["format"]["strict"])
        data = json.loads(payload["input"][1]["content"])
        self.assertEqual(data["disclosed_facts"], [])
        self.assertNotIn("allowed_outcomes", payload["input"][1]["content"])
        for fact in original["scenario_snapshot"]["facts"]:
            self.assertNotIn(fact["value"], request.content.decode())
        self.assertEqual(result["fact_ids"], ["budget"])
        self.assertNotIn("test-not-a-real-secret", request.content.decode())

    async def test_rate_limit_does_not_retry_or_leak_upstream_body(self):
        calls = []
        async def handler(request):
            calls.append(request)
            return httpx.Response(429, json={"error": {"message": "PRIVATE-UPSTREAM-DATA"}})
        original = new_session(mode="openai")
        snapshot = deepcopy(original)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with self.assertRaises(ProviderError) as error:
                await process_turn(original, "Какой бюджет?", "message",
                                   OpenAIProvider("fake", "configured-model", client=client), 1)
        self.assertEqual(error.exception.code, "ai_rate_limited")
        self.assertNotIn("PRIVATE-UPSTREAM-DATA", str(error.exception))
        self.assertEqual(len(calls), 1)
        self.assertEqual(original, snapshot)

    async def test_incomplete_refusal_bad_json_and_timeout_cannot_create_progress(self):
        cases = [
            ({"status": "incomplete", "output": []}, "ai_incomplete"),
            ({"status": "completed", "output": [{"type": "message", "content": [{"type": "refusal", "refusal": "private text"}]}]}, "ai_refusal"),
            ({"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": "not JSON"}]}]}, "ai_invalid_response"),
            (None, "ai_timeout"),
        ]
        for body, expected in cases:
            with self.subTest(expected=expected):
                async def handler(request, body=body):
                    if body is None:
                        raise httpx.ReadTimeout("raw provider details", request=request)
                    return httpx.Response(200, json=body)
                original = new_session(mode="openai")
                snapshot = deepcopy(original)
                async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                    with self.assertRaises(ProviderError) as error:
                        await process_turn(original, "Какой бюджет?", "message",
                                           OpenAIProvider("fake", "configured-model", client=client), 1)
                self.assertEqual(error.exception.code, expected)
                self.assertEqual(original, snapshot)
                self.assertNotIn("raw provider details", str(error.exception))

    async def test_provider_200_with_fabricated_evidence_is_still_rejected(self):
        async def handler(request):
            return httpx.Response(200, json=response_body(decision(
                act="summary", summary_ok=True, source_quote="Правильно?",
                summary_evidence=[{"fact_id": "budget", "quote": "Клиент готов заплатить"}])))
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with self.assertRaises(ProviderError) as error:
                await process_turn(new_session(mode="openai"), "Правильно?", "summary",
                                   OpenAIProvider("fake", "configured-model", client=client), 1)
        self.assertEqual(error.exception.code, "ai_invalid_evidence")


if __name__ == "__main__":
    unittest.main()
