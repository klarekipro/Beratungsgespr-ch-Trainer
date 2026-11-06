"""Evidence-gated state with authored demo replies and a grounded live customer.

Deterministic transitions do not prove the semantic correctness of an LLM decision.
The provider cannot write state. Live wording is checked against authored facts. Every session uses its
immutable company/scenario snapshots, independently of subsequent mentor edits.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone

from .providers import ProviderError
from .customer_actor import ActorContractError, validate_customer_reply
from .response_planning import normalize_targets, build_response_plan, is_price_statement


_STAGES = ("needs", "capabilities")
_STATUSES = {"known", "undecided", "does_not_know", "refuses_to_disclose", "not_applicable"}
_DECISION_KEYS = {
    "act", "fact_ids", "summary_ok", "summary_evidence", "proposal_outcome",
    "proposal_ok", "source_quote", "uncertain",
}


def initial_state() -> dict:
    return {
        "phase": "needs", "discovered": [], "needs_confirmed": False,
        "capabilities_confirmed": False, "events": [], "outcome": None,
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _scenario_facts(session: dict) -> dict:
    """Reject incomplete author data instead of inventing customer ignorance."""
    facts = session["scenario_snapshot"].get("facts")
    if not isinstance(facts, list) or not facts:
        raise ProviderError("scenario_invalid", "В сценарии отсутствуют обязательные сведения клиента.")
    result = {}
    for fact in facts:
        if (not isinstance(fact, dict) or not isinstance(fact.get("id"), str)
                or not fact["id"] or fact["id"] in result
                or fact.get("stage") not in _STAGES or not isinstance(fact.get("status"), str)
                or fact["status"] not in _STATUSES
                or type(fact.get("required")) is not bool
                or type(fact.get("material", True)) is not bool
                or (fact.get("required") and not fact.get("material", True))
                or not isinstance(fact.get("value"), str) or not fact["value"].strip()
                or not isinstance(fact.get("label"), str) or not fact["label"].strip()
                or not isinstance(fact.get("keywords"), list)
                or any(not isinstance(keyword, str) for keyword in fact["keywords"])):
            raise ProviderError("scenario_invalid", "Карточка клиента неполна. Наставнику нужно проверить значения и статусы фактов.")
        result[fact["id"]] = fact
    for stage in _STAGES:
        if not any(f["stage"] == stage and f["required"] and f["status"] != "not_applicable" for f in facts):
            raise ProviderError("scenario_invalid", "Для каждого этапа нужен хотя бы один существенный критерий выяснения.")
    return result


def _validate_decision(decision: dict, session: dict, text: str, facts: dict) -> dict:
    def invalid(message="Результат распознавания не прошёл проверку. Ход не засчитан."):
        raise ProviderError("ai_invalid_evidence", message)

    if not isinstance(decision, dict) or set(decision) not in (_DECISION_KEYS, _DECISION_KEYS | {"question_targets"}):
        invalid()
    if not isinstance(decision["act"], str) or decision["act"] not in {"question", "summary", "proposal", "other"}:
        invalid()
    for name in ("summary_ok", "proposal_ok", "uncertain"):
        if type(decision[name]) is not bool:
            invalid()
    ids = decision["fact_ids"]
    if (not isinstance(ids, list) or any(not isinstance(i, str) or i not in facts for i in ids)
            or len(ids) != len(set(ids))):
        invalid()
    if decision["act"] != "question" and ids:
        invalid()
    quote = decision["source_quote"]
    if not isinstance(quote, str) or (quote and quote not in text):
        invalid()
    if decision["act"] != "other" and not decision["uncertain"] and not quote.strip():
        invalid()
    evidence = decision["summary_evidence"]
    if not isinstance(evidence, list):
        invalid()
    seen = set()
    discovered = set(session["state"]["discovered"])
    for item in evidence:
        if (not isinstance(item, dict) or set(item) != {"fact_id", "quote"}
                or not isinstance(item["fact_id"], str) or item["fact_id"] not in discovered
                or item["fact_id"] not in facts or item["fact_id"] in seen
                or not isinstance(item["quote"], str) or not item["quote"].strip()
                or item["quote"] not in text):
            invalid("Цитаты смысловой проверки не подтверждены исходной репликой. Ход не засчитан.")
        seen.add(item["fact_id"])
    if decision["act"] != "summary" and (evidence or decision["summary_ok"]):
        invalid()
    outcome = decision["proposal_outcome"]
    outcomes = {service["id"] for service in session["company_snapshot"]["services"]} | {"no_fit"}
    if outcome is not None and (not isinstance(outcome, str) or outcome not in outcomes):
        invalid()
    if decision["act"] != "proposal" and (outcome is not None or decision["proposal_ok"]):
        invalid()
    return decision


_REPLIES = {
    "ru": {
        "uncertain": "Не уверен, что правильно понял ваш вопрос. Можете сформулировать его иначе?",
        "clarify": "Уточните, пожалуйста, что именно вы хотели бы узнать.",
        "early": "Пока я не готов обсуждать конкретное предложение. Сначала давайте уточним мою задачу и условия.",
        "needs_confirmed": "Да, вы правильно поняли, что мне нужно. Теперь можем обсудить мои возможности и ограничения.",
        "capabilities_confirmed": "Да, условия и ограничения вы поняли правильно. Теперь я готов выслушать обоснованное предложение.",
        "missing": "Пока такой итог делать рано. Пожалуйста, продолжим выяснять мою ситуацию.",
        "summary_incomplete": "В итоговом понимании ещё не всё учтено. Пожалуйста, уточните резюме того, что мы обсудили.",
        "correction": "Я бы уточнил так: ",
        "summary_done": "Наше понимание уже согласовано. Какой итоговый шаг вы предлагаете с учётом этих условий?",
        "offer_not_fit": "Это предложение пока не соответствует всем обсуждённым условиям. Пожалуйста, уточните, что вы можете обоснованно предложить.",
        "offer_accepted": "Спасибо, теперь предложение понятно и связано с моей ситуацией. До любых работ или заказа нужно отдельно согласовать условия.",
        "no_fit_accepted": "Спасибо за честное объяснение. Теперь я понимаю, почему ваша компания не может выполнить эту задачу.",
    },
    "de": {
        "uncertain": "Ich bin nicht sicher, ob ich Ihre Frage richtig verstanden habe. Können Sie sie anders formulieren?",
        "clarify": "Was genau möchten Sie wissen?",
        "early": "Für einen konkreten Vorschlag ist es mir noch zu früh. Klären wir bitte zuerst mein Anliegen und meine Möglichkeiten.",
        "needs_confirmed": "Ja, Sie haben mein Anliegen richtig verstanden. Jetzt können wir meine Möglichkeiten und Einschränkungen besprechen.",
        "capabilities_confirmed": "Ja, Sie haben meine Bedingungen richtig verstanden. Jetzt höre ich mir gern einen begründeten Vorschlag an.",
        "missing": "Für diese Zusammenfassung ist es noch zu früh. Klären wir bitte meine Situation weiter.",
        "summary_incomplete": "Die Zusammenfassung berücksichtigt noch nicht alles. Können Sie unser bisheriges Gespräch genauer zusammenfassen?",
        "correction": "Ich würde es so präzisieren: ",
        "summary_done": "Unser Verständnis ist bereits abgestimmt. Welchen nächsten Schritt schlagen Sie unter diesen Bedingungen vor?",
        "offer_not_fit": "Dieser Vorschlag passt noch nicht zu allen besprochenen Bedingungen. Bitte präzisieren Sie, was Sie begründet anbieten können.",
        "offer_accepted": "Danke, der Vorschlag ist jetzt verständlich und passt zu meiner Situation. Vor Arbeiten oder einer Bestellung müssen wir die Bedingungen gesondert vereinbaren.",
        "no_fit_accepted": "Danke für die ehrliche Erklärung. Jetzt verstehe ich, warum Ihr Unternehmen diese Aufgabe nicht übernehmen kann.",
    },
}


def _event(state: dict, event_type: str, turn: int, detail: str) -> None:
    state["events"].append({"type": event_type, "turn": turn, "detail": detail})


async def process_turn(session: dict, text: str, kind: str, provider, turn: int) -> dict:
    """Return a new session only after valid interpretation; never mutate input.

    The HTTP layer owns optimistic versioning, request receipts and live attempt
    counting. This function owns state/messages/updated_at only.
    """
    if session.get("status") != "active" or session["state"]["phase"] == "completed":
        raise ValueError("consultation_not_active")
    if not isinstance(text, str) or not text.strip() or len(text) > 6000:
        raise ValueError("invalid_message")
    if kind not in {"message", "summary", "proposal"} or type(turn) is not int or turn < 1:
        raise ValueError("invalid_turn")
    facts = _scenario_facts(session)
    # Even a custom provider cannot mutate the caller's snapshots or journal.
    decision = await provider.interpret(deepcopy(session), text, kind)
    decision = _validate_decision(decision, session, text, facts)
    if "question_targets" in decision:
        try:
            original_targets = deepcopy(decision["question_targets"])
            decision["question_targets"] = normalize_targets(decision, text, facts)
            trace = getattr(provider, "trace", None)
            if isinstance(trace,list) and original_targets != decision["question_targets"]:
                trace.append({"kind":"plan_normalization", "original_targets":original_targets,
                              "current_targets":deepcopy(decision["question_targets"])})
        except ValueError:
            raise ProviderError("ai_invalid_evidence", "Не удалось определить тему вопроса. Ход не засчитан.") from None
        if decision["act"] == "question":
            decision["fact_ids"] = list(dict.fromkeys(i for t in decision["question_targets"] for i in t["fact_ids"]))
    updated = deepcopy(session)
    state = updated["state"]
    replies = _REPLIES.get(session["scenario_snapshot"].get("language"), _REPLIES["ru"])
    before_needs = bool(state["needs_confirmed"])
    before_capabilities = bool(state["capabilities_confirmed"])
    act = decision["act"]
    response_intent = "clarify"
    must_address = []

    if decision["uncertain"]:
        response_intent = "uncertain"
        reply = replies["uncertain"]
        _event(state, "interpretation_uncertain", turn, "Смысл реплики неоднозначен. Этап не изменён; отрицательная оценка не начисляется.")
    elif session["mode"] == "openai" and act == "other" and is_price_statement(text):
        response_intent = "discuss_price"
        reply = ""  # Live wording is generated below; no fallback template.
        _event(state, "price_claim", turn, "Продавец назвал стоимость; клиенту не приписаны бюджет или согласие на оплату.")
    elif act == "proposal":
        if not (before_needs and before_capabilities):
            response_intent = "premature_offer"
            reply = replies["early"]
            _event(state, "early_proposal", turn,
                   "Предложение сделано до подтверждения потребностей и возможностей. "
                   "Ответ, который мог бы появиться позже, не делает его своевременным.")
        else:
            outcome = decision["proposal_outcome"]
            permitted = outcome in session["scenario_snapshot"].get("allowed_outcomes", [])
            if outcome and permitted and decision["proposal_ok"]:
                state["outcome"] = outcome
                state["phase"] = "completed"
                reply = replies["no_fit_accepted"] if outcome == "no_fit" else replies["offer_accepted"]
                response_intent = "no_fit_accepted" if outcome == "no_fit" else "proposal_accepted"
                title = "честное объяснение невозможности помочь" if outcome == "no_fit" else next(
                    service["title"] for service in session["company_snapshot"]["services"] if service["id"] == outcome)
                _event(state, "grounded_outcome", turn, "После обоих этапов обоснован итог: " + title + ".")
            else:
                response_intent = "proposal_not_grounded"
                reply = replies["offer_not_fit"]
                _event(state, "proposal_not_grounded", turn,
                       "Первые этапы подтверждены, но пригодность действия или его условия не подтверждены. Сделка не засчитана.")
    elif act == "summary":
        phase = state["phase"]
        if phase not in _STAGES:
            response_intent = "summary_already_confirmed"
            reply = replies["summary_done"]
        else:
            required = {fact_id for fact_id, fact in facts.items()
                        if fact["stage"] == phase and fact["required"] and fact["status"] != "not_applicable"}
            discovered = set(state["discovered"])
            discussed = {fact_id for fact_id in discovered
                         if facts[fact_id]["stage"] == phase and facts[fact_id].get("material", True)
                         and facts[fact_id]["status"] != "not_applicable"}
            evidence = {item["fact_id"] for item in decision["summary_evidence"]}
            if not required.issubset(discovered):
                response_intent = "summary_missing"
                reply = replies["missing"]
                _event(state, "summary_before_discovery", turn,
                       "Резюме предложено до выяснения существенных сведений текущего этапа.")
            elif not decision["summary_ok"]:
                response_intent = "correct_summary"
                # Repeat only facts already disclosed. The correction alone never
                # closes a phase; the learner must submit an accurate summary.
                correction = " ".join(fact["value"] for fact in facts.values()
                                       if fact["id"] in discovered and fact["stage"] == phase)
                reply = replies["correction"] + correction
                _event(state, "summary_not_confirmed", turn,
                       "Резюме не подтверждено. Клиент уточнил уже сообщённые сведения; необходимо новое корректное резюме.")
            elif not discussed.issubset(evidence):
                response_intent = "summary_incomplete"
                reply = replies["summary_incomplete"]
                _event(state, "summary_incomplete", turn,
                       "В резюме не подтверждены все существенные обсуждённые сведения текущего этапа.")
            elif phase == "needs":
                response_intent = "confirm_needs_summary"
                state["needs_confirmed"] = True
                state["capabilities_confirmed"] = False
                state["phase"] = "capabilities"
                reply = replies["needs_confirmed"]
                _event(state, "needs_confirmed", turn, "Потребности выяснены, резюмированы учеником и подтверждены клиентом.")
            elif before_needs:
                response_intent = "confirm_capabilities_summary"
                state["capabilities_confirmed"] = True
                state["phase"] = "proposal"
                reply = replies["capabilities_confirmed"]
                _event(state, "capabilities_confirmed", turn,
                       "Возможности и ограничения резюмированы и подтверждены, включая явно установленные неизвестности.")
            else:
                response_intent = "summary_missing"
                reply = replies["missing"]
                _event(state, "summary_before_discovery", turn, "Сначала необходимо подтвердить потребности.")
    elif act == "question" and decision["fact_ids"]:
        response_intent = "answer_question"
        ids = decision["fact_ids"]
        must_address = list(ids)
        new_ids = [fact_id for fact_id in ids if fact_id not in state["discovered"]]
        if not before_needs and any(facts[fact_id]["stage"] == "capabilities" for fact_id in new_ids):
            _event(state, "capabilities_before_needs", turn,
                   "Возможности обсуждались до подтверждения потребностей. Полезные сведения сохранены; порядок закрытия этапов не изменён.")
        if before_needs and any(facts[fact_id]["stage"] == "needs" and facts[fact_id].get("material", True) for fact_id in new_ids):
            state["needs_confirmed"] = False
            state["capabilities_confirmed"] = False
            state["phase"] = "needs"
            state["outcome"] = None
            _event(state, "confirmation_reopened", turn,
                   "Появились новые сведения о потребностях. Прежнее резюме нужно актуализировать.")
        elif before_capabilities and any(facts[fact_id]["stage"] == "capabilities" and facts[fact_id].get("material", True) for fact_id in new_ids):
            state["capabilities_confirmed"] = False
            state["phase"] = "capabilities"
            state["outcome"] = None
            _event(state, "confirmation_reopened", turn,
                   "Появились новые ограничения. Прежнее резюме возможностей нужно актуализировать.")
        for fact_id in new_ids:
            state["discovered"].append(fact_id)
            _event(state, "fact_discovered", turn, "Выяснено: " + facts[fact_id]["label"] + ".")
        reply = " ".join(facts[fact_id]["value"] for fact_id in ids)
    else:
        reply = replies["clarify"]
        _event(state, "clarification_requested", turn,
               "Распознаватель не сопоставил реплику со сведениями карточки. Это ограничение распознавания, не доказанная ошибка ученика.")

    response_source = "authored_demo"
    if session["mode"] == "openai":
        responder = getattr(provider, "respond", None)
        if not callable(responder):
            raise ProviderError("ai_actor_unavailable", "Разговорная роль клиента недоступна. Технический ответ не подставлялся.")
        # No hidden answers, outcome key, phase, counters or evaluator prose go
        # to the customer. Newly disclosed facts remain provisional until the
        # independently checked answer actually expresses every selected fact.
        allowed_ids = set(state["discovered"])
        context = {
            "language": session["scenario_snapshot"].get("language", "ru"),
            "customer_name": session["scenario_snapshot"]["customer_name"],
            "opening": session["scenario_snapshot"]["opening"],
            "learner_text": text,
            "visible_history": [{"role": m["role"], "text": m["text"]} for m in session["messages"][-20:]],
            "authorized_facts": [{key: f[key] for key in ("id", "label", "value", "status")}
                                 for f in facts.values() if f["id"] in allowed_ids],
            "must_address_fact_ids": must_address,
            "response_intent": response_intent,
        }
        context["response_plan"] = build_response_plan(session, decision, text, response_intent, context["authorized_facts"])
        answer = await responder(deepcopy(context))
        if (not isinstance(answer, dict) or set(answer) != {"reply", "verified_fact_ids"}
                or not isinstance(answer["reply"], str) or not answer["reply"].strip()
                or len(answer["reply"]) > 1800
                or not isinstance(answer["verified_fact_ids"], list)
                or any(not isinstance(i, str) or i not in allowed_ids for i in answer["verified_fact_ids"])
                or not set(must_address).issubset(answer["verified_fact_ids"])):
            raise ProviderError("ai_actor_invalid", "Ответ клиента не прошёл проверку. Ход не засчитан.")
        reply = answer["reply"].strip()
        # Mandatory at the state boundary, including custom provider adapters.
        try:
            validate_customer_reply(reply, context)
        except ActorContractError as exc:
            raise ProviderError(exc.code, exc.message) from None
        response_source = "openai_actor_verified"
        updated.setdefault("response_plans", []).append({"turn": turn, "plan": deepcopy(context["response_plan"])})

    now = _utc_now()
    updated["messages"].extend([
        {"role": "learner", "text": text, "at": now, "turn": turn},
        {"role": "customer", "text": reply, "at": now, "turn": turn, "source": response_source},
    ])
    updated["updated_at"] = now
    return updated


def build_report(session: dict) -> dict:
    """Explain observed state with evidence references, never a fabricated score."""
    state = session["state"]
    complete = (state["phase"] == "completed" and state["needs_confirmed"]
                and state["capabilities_confirmed"] and bool(state["outcome"]))
    summary = ("Консультация завершена по правилам этого учебного сценария. Итог предложен после подтверждения обоих этапов."
               if complete else "Попытка завершена до подтверждённого обоснованного итога. Ниже видно, какие этапы и сведения удалось пройти.")
    if any(event["type"] == "early_proposal" for event in state["events"]):
        summary += " Раннее предложение было зафиксировано и остаётся частью разбора, даже если дальнейший ход исправлен."
    limitations = [
        "Завершение сценария не доказывает освоение навыка; содержание и обоснованность консультации должен рассмотреть наставник.",
        "Карточки компании и клиента закреплены в начале попытки. Последующие правки наставника эту попытку не меняют.",
        "Учебное завершение не означает реальную сделку, согласие на оплату или заказ услуги.",
    ]
    if session["mode"] == "demo":
        summary = "Техническая проверка без AI. По этой попытке нельзя оценивать навык свободной консультации. " + summary
        limitations.insert(0, "Технический сценарный режим: ограниченное сопоставление формулировок без вызова AI. Нераспознанный вопрос не является доказанной ошибкой ученика.")
    else:
        natural_turns = sum(m.get("source") == "openai_actor_verified" for m in session["messages"])
        legacy_turns = sum(m["role"] == "customer" and m.get("turn", 0) > 0 and not m.get("source") for m in session["messages"])
        if natural_turns:
            limitations.insert(0, f"Разговорных ответов OpenAI с отдельной смысловой проверкой: {natural_turns}. Проверка моделью тоже может ошибаться; надёжность и учебный эффект требуют живой оценки.")
        else:
            limitations.insert(0, "В этой попытке нет сохранённых ответов новой разговорной роли OpenAI. Наличие ключа само по себе не подтверждает использование модели.")
        if legacy_turns:
            limitations.append(f"Ответов прежней версии с готовыми фразами: {legacy_turns}. Они не переименованы в разговорные AI-ответы.")
        if "live_requests" in session:
            label = "Попыток обращения к API" if session.get("api_count_complete") else "Учтённых попыток API с обновления (ранние обращения неизвестны)"
            limitations.append(f"{label}: {session['live_requests']}; сюда входят и обращения, завершившиеся ошибкой. Это не расчёт стоимости.")
    if session.get("system_issues"):
        limitations.append("В беседе были ограничения сценария или ошибки системы. Они перечислены отдельно и не считаются ошибками ученика.")
    if any(event["type"] == "interpretation_uncertain" for event in state["events"]):
        limitations.append("В разговоре были неопределённые интерпретации. Эти ходы не продвигали этапы и не трактуются как доказанная ошибка ученика.")
    discovered = set(state["discovered"])
    return {
        "status": "complete" if complete else "incomplete",
        "summary": summary,
        "stages": [
            {"id": "needs", "label": "Потребности", "confirmed": bool(state["needs_confirmed"])},
            {"id": "capabilities", "label": "Возможности и ограничения", "confirmed": bool(state["capabilities_confirmed"])},
            {"id": "proposal", "label": "Обоснованное итоговое предложение", "confirmed": bool(complete)},
        ],
        "findings": ([deepcopy(event) for event in state["events"] if event["type"] != "fact_discovered"]
                     + [deepcopy(issue) for issue in session.get("system_issues", [])]),
        "facts": [{"label": fact["label"], "stage": fact["stage"], "status": fact["status"],
                   "discovered": fact["id"] in discovered, "value": fact["value"]}
                  for fact in session["scenario_snapshot"]["facts"]],
        "outcome": state["outcome"],
        "limitations": limitations,
    }
