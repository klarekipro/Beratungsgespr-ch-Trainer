"""Offline contracts for natural customer responses; no live model quality claim.

Responses are explicitly supplied by these tests through MockTransport. They
exercise evidence boundaries, independent review and failure handling, not whether
a real model will choose the same conversational wording or semantic judgement.
"""

from __future__ import annotations

import json
import unittest
from copy import deepcopy

import httpx

from backend.app.dashboard.providers import OpenAIProvider, ProviderError


def response_body(value):
    return {"status": "completed", "output": [{"type": "message", "role": "assistant",
            "content": [{"type": "output_text", "text": json.dumps(value, ensure_ascii=False)}]}]}


def fact(identifier, label, value, status="known"):
    return {"id": identifier, "label": label, "value": value, "status": status}


def context():
    return {
        "language": "ru", "customer_name": "Учебный клиент",
        "opening": "Добрый день. Ищу, кто сможет заняться моей печью.",
        "learner_text": "Что вы имеете в виду?", "response_intent": "answer_question",
        "visible_history": [{"role": "customer", "text": "Добрый день. Ищу, кто сможет заняться моей печью."}],
        "authorized_facts": [fact("goal", "Оборудование и задача", "Нужен ремонт промышленной газовой печи.")],
        "must_address_fact_ids": ["goal"],
        "company": {"name": "Учебная компания", "services": [{"id": "repair", "title": "Ремонт",
                    "description": "Ремонт бытовых электрических печей.", "conditions": "После сметы и согласования."}],
                    "limitations": "Промышленные и газовые печи не обслуживаются."},
    }


def candidate(reply="Я ищу мастера, который сможет отремонтировать промышленную газовую печь.", ids=None):
    return {"reply": reply, "used_fact_ids": ["goal"] if ids is None else ids, "scenario_gap": False}


def review(ids=None, **changes):
    value = {"grounded": True, "in_role": True, "consistent_with_intent": True,
             "addressed_fact_ids": ["goal"] if ids is None else ids, "unsupported_quotes": []}
    value.update(changes)
    return value


def interpretation_session():
    c = context()
    public_fact = {**c["authorized_facts"][0], "stage": "needs", "keywords": ["хотите"], "required": True}
    hidden_fact = {**fact("budget", "Бюджет", "PRIVATE_BUDGET_VALUE_7321"),
                   "stage": "capabilities", "keywords": ["бюджет"], "required": True}
    return {
        "scenario_snapshot": {"language": "ru", "facts": [public_fact, hidden_fact],
                              "allowed_outcomes": ["PRIVATE_OUTCOME_KEY"]},
        "company_snapshot": deepcopy(c["company"]),
        "state": {"phase": "needs", "discovered": [], "needs_confirmed": False, "capabilities_confirmed": False},
        "messages": deepcopy(c["visible_history"]),
    }


class NaturalCustomerProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_customer_cannot_interview_employee_about_using_own_appliance(self):
        # Regression from the live A04 check: the separate model review had
        # accepted this role reversal. Reject it before that review can approve it.
        calls = []

        async def handler(request):
            calls.append(request)
            return httpx.Response(200, json=response_body(candidate(
                "Печь перестала включаться, правильно? Вы давно уже не пользуетесь ею после этого?"
            )))

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAIProvider("fake", "configured-model", client=client)
            with self.assertRaises(ProviderError) as caught:
                await provider.respond(context())
        self.assertEqual(caught.exception.code, "ai_actor_role_violation")
        self.assertEqual(len(calls), 1)

    async def test_interpret_actor_and_independent_review_use_three_bounded_requests(self):
        decision = {"act": "question", "fact_ids": ["goal"], "summary_ok": False,
                    "summary_evidence": [], "proposal_outcome": None, "proposal_ok": False,
                    "source_quote": "Что вы имеете в виду?", "uncertain": False}
        answers = [decision, candidate(), review()]
        requests = []

        async def handler(request):
            requests.append(request)
            return httpx.Response(200, json=response_body(answers[len(requests) - 1]))

        source = interpretation_session()
        source_before = deepcopy(source)
        c = context()
        # Defensive filtering must discard accidental extra caller context too.
        c["scenario_snapshot"] = {"hidden": "PRIVATE_FULL_CARD"}
        c["allowed_outcomes"] = ["PRIVATE_OUTCOME_KEY"]
        c["authorized_facts"][0]["stage"] = "PRIVATE_STAGE_EXTRA"
        c["company"]["description"] = "PRIVATE_UNNEEDED_DESCRIPTION"
        original = deepcopy(c)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAIProvider("synthetic-key-not-used-externally", "configured-model", client=client)
            interpreted = await provider.interpret(source, c["learner_text"], "message")
            result = await provider.respond(c)
        self.assertEqual(interpreted["fact_ids"], ["goal"])
        self.assertEqual(result, {"reply": answers[1]["reply"], "verified_fact_ids": ["goal"]})
        self.assertEqual(provider.request_count, 3)
        self.assertEqual(source, source_before)
        self.assertEqual(c, original)
        payloads = [json.loads(r.content) for r in requests]
        self.assertEqual([p["text"]["format"]["name"] for p in payloads],
                         ["consultation_decision", "customer_reply", "customer_reply_review"])
        for req, payload in zip(requests, payloads):
            self.assertEqual(str(req.url), "https://api.openai.com/v1/responses")
            self.assertFalse(payload["store"])
            self.assertTrue(payload["text"]["format"]["strict"])
            for secret in ("PRIVATE_BUDGET_VALUE_7321", "PRIVATE_FULL_CARD", "PRIVATE_OUTCOME_KEY",
                           "PRIVATE_STAGE_EXTRA", "PRIVATE_UNNEEDED_DESCRIPTION", "synthetic-key-not-used-externally"):
                self.assertNotIn(secret, req.content.decode())
        interpretation_data = json.loads(payloads[0]["input"][1]["content"])
        self.assertEqual(interpretation_data["disclosed_facts"], [])
        actor_data = json.loads(payloads[1]["input"][1]["content"])
        verifier_data = json.loads(payloads[2]["input"][1]["content"])
        self.assertEqual(actor_data["must_address_fact_ids"], ["goal"])
        self.assertEqual(verifier_data["context"], actor_data)
        self.assertEqual(verifier_data["reply"], result["reply"])
        self.assertNotIn("used_fact_ids", verifier_data)
        self.assertNotIn("scenario_gap", verifier_data)
        self.assertNotIn("used_fact_ids", verifier_data["context"])
        self.assertNotEqual(payloads[1]["input"][0]["content"], payloads[2]["input"][0]["content"])

    async def test_compound_question_can_answer_authored_unknowns_and_symptoms(self):
        c = context()
        c["learner_text"] = "Скажите, пожалуйста, номер, мощность и что с печью произошло."
        c["authorized_facts"] = [
            fact("identification", "Номер и мощность", "Номер модели и мощность не помню.", "does_not_know"),
            fact("symptoms", "Что произошло", "Печь не запускается."),
        ]
        c["must_address_fact_ids"] = ["identification", "symptoms"]
        answer = candidate("Модель и мощность я сейчас не помню. А проблема в том, что печь не запускается.",
                           ["identification", "symptoms"])
        outputs = [answer, review(["identification", "symptoms"])]
        requests = []

        async def handler(request):
            requests.append(request)
            return httpx.Response(200, json=response_body(outputs[len(requests) - 1]))

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAIProvider("fake", "configured-model", client=client)
            result = await provider.respond(c)
        self.assertEqual(result["reply"], answer["reply"])
        self.assertEqual(set(result["verified_fact_ids"]), {"identification", "symptoms"})
        self.assertEqual(provider.request_count, 2)

    async def test_fragment_question_can_use_preceding_exchange_and_explicit_unknown_cause(self):
        c = context()
        c["learner_text"] = "Причину поломки"
        c["visible_history"] += [{"role": "learner", "text": "Вы знаете, что произошло?"},
                                 {"role": "customer", "text": "Вы спрашиваете про симптомы или причину?"}]
        c["authorized_facts"] = [fact("cause", "Известна ли причина", "Причину неисправности не знаю.", "does_not_know")]
        c["must_address_fact_ids"] = ["cause"]
        answer = candidate("А, причину. Нет, почему она сломалась, я не знаю.", ["cause"])
        outputs = [answer, review(["cause"])]
        requests = []

        async def handler(request):
            requests.append(request)
            return httpx.Response(200, json=response_body(outputs[len(requests) - 1]))

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAIProvider("fake", "configured-model", client=client)
            result = await provider.respond(c)
        sent = json.loads(json.loads(requests[0].content)["input"][1]["content"])
        self.assertEqual(sent["learner_text"], "Причину поломки")
        self.assertEqual(sent["visible_history"][-1]["text"], c["visible_history"][-1]["text"])
        self.assertEqual(result["reply"], answer["reply"])

    async def test_absent_author_fact_returns_a_scenario_gap_not_customer_ignorance(self):
        c = context()
        c["learner_text"] = "Какой у печи серийный номер?"
        c["must_address_fact_ids"] = []
        original = deepcopy(c)
        requests = []

        async def handler(request):
            requests.append(request)
            return httpx.Response(200, json=response_body({"reply": "", "used_fact_ids": [], "scenario_gap": True}))

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAIProvider("fake", "configured-model", client=client)
            with self.assertRaises(ProviderError) as error:
                await provider.respond(c)
        self.assertEqual(error.exception.code, "scenario_missing_context")
        self.assertIn("не ошибка ученика", error.exception.message)
        self.assertEqual(provider.request_count, 1)
        self.assertEqual(len(requests), 1)
        self.assertEqual(c, original)

    async def test_independent_review_rejects_invented_claims_despite_actor_self_report(self):
        for text in ("У меня промышленная газовая печь, сгорела плата управления.",
                     "Номер моей промышленной газовой печи — 88442."):
            with self.subTest(reply=text):
                outputs = [candidate(text), review(grounded=False, unsupported_quotes=[text])]
                requests = []

                async def handler(request):
                    requests.append(request)
                    return httpx.Response(200, json=response_body(outputs[len(requests) - 1]))

                async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                    provider = OpenAIProvider("fake", "configured-model", client=client)
                    with self.assertRaises(ProviderError) as error:
                        await provider.respond(context())
                self.assertEqual(error.exception.code, "ai_actor_not_grounded")
                self.assertNotIn(text, str(error.exception))
                self.assertEqual(provider.request_count, 2)
                self.assertEqual(len(requests), 2)

    async def test_omitted_new_fact_cannot_be_credited_from_actor_claimed_ids(self):
        c = context()
        c["authorized_facts"].append(fact("symptoms", "Что произошло", "Печь не запускается."))
        c["must_address_fact_ids"] = ["goal", "symptoms"]
        outputs = [candidate(ids=["goal", "symptoms"]), review(["goal"])]
        requests = []

        async def handler(request):
            requests.append(request)
            return httpx.Response(200, json=response_body(outputs[len(requests) - 1]))

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAIProvider("fake", "configured-model", client=client)
            with self.assertRaises(ProviderError) as error:
                await provider.respond(c)
        self.assertEqual(error.exception.code, "ai_actor_omitted_fact")
        self.assertEqual(provider.request_count, 2)

    async def test_customer_cannot_announce_teaching_stages_even_if_a_review_would_pass(self):
        outputs = [candidate("Первый этап пройден. Теперь можем обсудить мои возможности и ограничения."), review()]
        requests = []

        async def handler(request):
            requests.append(request)
            return httpx.Response(200, json=response_body(outputs[len(requests) - 1]))

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAIProvider("fake", "configured-model", client=client)
            with self.assertRaises(ProviderError) as error:
                await provider.respond(context())
        self.assertEqual(error.exception.code, "ai_actor_role_violation")
        self.assertEqual(provider.request_count, 1)

    async def test_accepting_a_premature_offer_is_rejected_by_intent_review(self):
        c = context()
        c["response_intent"] = "premature_offer"
        c["must_address_fact_ids"] = []
        outputs = [candidate("Да, оформляйте заказ и списывайте деньги.", []),
                   review([], consistent_with_intent=False)]
        requests = []

        async def handler(request):
            requests.append(request)
            return httpx.Response(200, json=response_body(outputs[len(requests) - 1]))

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAIProvider("fake", "configured-model", client=client)
            with self.assertRaises(ProviderError) as error:
                await provider.respond(c)
        self.assertEqual(error.exception.code, "ai_actor_not_grounded")
        self.assertEqual(provider.request_count, 2)

    async def test_malformed_review_is_rejected_instead_of_promoting_the_reply(self):
        invalid_reviews = [
            review(grounded="true"),
            review(["hidden_fact"]),
            review(["goal", "goal"]),
            review(unsupported_quotes=["quote absent from actual reply"]),
        ]
        for invalid in invalid_reviews:
            with self.subTest(review=invalid):
                outputs = [candidate(), invalid]
                requests = []

                async def handler(request):
                    requests.append(request)
                    return httpx.Response(200, json=response_body(outputs[len(requests) - 1]))

                async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                    provider = OpenAIProvider("fake", "configured-model", client=client)
                    with self.assertRaises(ProviderError) as error:
                        await provider.respond(context())
                self.assertEqual(error.exception.code, "ai_actor_invalid_review")
                self.assertEqual(provider.request_count, 2)

    async def test_actor_timeout_is_counted_once_without_retry_or_canned_reply(self):
        requests = []

        async def handler(request):
            requests.append(request)
            raise httpx.ReadTimeout("PRIVATE_TRANSPORT_DETAIL", request=request)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAIProvider("fake", "configured-model", client=client)
            with self.assertRaises(ProviderError) as error:
                await provider.respond(context())
        self.assertEqual(error.exception.code, "ai_timeout")
        self.assertNotIn("PRIVATE_TRANSPORT_DETAIL", str(error.exception))
        self.assertEqual(provider.request_count, 1)
        self.assertEqual(len(requests), 1)

    async def test_verifier_rate_limit_discards_candidate_and_counts_both_requests(self):
        requests = []

        async def handler(request):
            requests.append(request)
            if len(requests) == 1:
                return httpx.Response(200, json=response_body(candidate()))
            return httpx.Response(429, json={"error": {"message": "PRIVATE_QUOTA_DETAIL"}})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAIProvider("fake", "configured-model", client=client)
            with self.assertRaises(ProviderError) as error:
                await provider.respond(context())
        self.assertEqual(error.exception.code, "ai_rate_limited")
        self.assertNotIn("PRIVATE_QUOTA_DETAIL", str(error.exception))
        self.assertEqual(provider.request_count, 2)
        self.assertEqual(len(requests), 2)

    async def test_greeting_uses_no_fact_claim_and_never_sends_an_empty_enum(self):
        c = context()
        c.update(learner_text="Здравствуйте!", response_intent="clarify", authorized_facts=[], must_address_fact_ids=[])
        outputs = [candidate("Здравствуйте!", []), review([])]
        requests = []

        async def handler(request):
            requests.append(request)
            return httpx.Response(200, json=response_body(outputs[len(requests) - 1]))

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAIProvider("fake", "configured-model", client=client)
            result = await provider.respond(c)
        self.assertEqual(result, {"reply": "Здравствуйте!", "verified_fact_ids": []})
        for request in requests:
            self.assertNotIn('"enum": []', request.content.decode())
        self.assertEqual(provider.request_count, 2)


if __name__ == "__main__":
    unittest.main()
