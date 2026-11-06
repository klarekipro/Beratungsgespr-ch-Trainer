# Research handoff — Pluggable Conversational AI Engine
Date: 2026-11-06
Status: PROPOSAL ONLY — NOT APPROVED / NOT IMPLEMENTED
Owner decision: pending
Branch: research/conversation-engine-options-2026-11
Base: main
Repository: klarekipro/Beratungsgespr-ch-Trainer

## 0. Read this first, Astra
This is an isolated exploratory proposal. Read this document together with `README.md`, `docs/PROJECT_HANDOFF_FOR_ASTRA.md`, `docs/ARCHITECTURE.md`, `docs/KNOWN_ISSUES.md`, `docs/PROJECT_STATUS.md`, and the original product PDF under `docs/product/`. Do not treat this research as approved scope, completed implementation, or evidence of a working integration. Do not merge into main. Do not deploy, run paid APIs, install third-party code, change existing tests, or alter the original PoC without separate explicit owner approval. First report findings and ask for an architectural decision.

## 1. What the owner actually wants
Find a **ready-made conversational AI engine** that can be attached as a separate service/module over HTTP API or SDK, much like the existing OpenAI integration. It should serve as the *conversational brain* for realistic German client role-play: maintain coherent multi-turn conversation, ask clarifying questions, show believable personality and appropriate initiative, remember the conversation, and obey our own client profile and scenario.

The owner does **not** want to rebuild Replika, adopt a whole UI, create a separate dashboard, or prioritize avatars. Current UI is text input (speech-to-text already produces text); voice output/live voice is a possible future option, not an MVP dependency. We want the conversational capability, not another application.

Our application owns the scenario, profile, hidden facts, disclosure policy, persistent truth and evaluation. A conversation engine may generate natural language, but must not own authorization of secrets, independently mutate canonical facts, or be trusted as a source of truth. Existing PostgreSQL or another application-owned store should persist sessions, turn logs, permitted disclosures and evaluation events; any provider memory is optional and untrusted.

## 2. Existing architecture — preserve
`User turn -> Director -> deterministic Policy/State -> allowed-only context -> Actor -> event log -> Evaluation`.
Director classifies the current question; Policy/State alone owns secret card and disclosure; Actor receives only public facts, currently permitted disclosures, visible history, and permitted reaction state; Evaluation scores what was *actually spoken*, not merely permitted. Existing contracts live in `backend/app/`. Current backend and frontend are not production implementations.

PoC MISSION 00.2: 148 successful API calls, Director 74/74 classification, 20/20 basic, no premature A/B/C disclosure in tested cases; CONDITIONAL PASS due to 12 unsupported heating symptoms and one unsupported discovery-time claim. MISSION 02: 32 requests/29 responses; first Actor revision failed grounding/role; final revision not accepted because timeouts/503 prevented complete evaluation. Do not declare grounding solved or modify gold standards to manufacture PASS. Existing research archive and Director remain immutable unless separately authorized.

## 3. Conceptual integration
Define a narrow `ConversationProvider` abstraction (proposal, not implemented):
- `start_session(public_profile, allowed_facts, persona_state, config) -> provider_session_id`
- `reply(provider_session_id, user_turn, allowed_context, visible_history, persona_state) -> candidate_text + metadata`
- `close_session(provider_session_id)`
- optional provider health/capabilities.
The actual interface may differ after research. Backend must independently record application session ID, scenario version, current disclosure set, user turn, provider/model version, candidate response, accepted response, validation decision, latency, usage and cost when available. Do not allow direct arbitrary DB writes from the provider. Provider must not receive hidden facts, rubric, Director rationale or other learners' data.

Critical: a stateful provider may RETAIN previously seen data. New session per scenario/run; explicit memory-reset/deletion semantics; only pass facts allowed for this session; ensure context is not contaminated by other sessions. A provider's autonomous memory is not authoritative. Prefer disable/restrict autonomous tools and memory writes in first trial. Response validation/guarding should be designed, but no claim of perfect semantic fact validation.

## 4. Candidates to verify from primary docs and current repositories
1. **Baseline: existing OpenAI API + our Actor** — minimal moving parts, maximum control; currently suffers factual-grounding issues; use as a controlled baseline, not a presumed inferior option. https://platform.openai.com/docs
2. **Letta (formerly MemGPT)** — open-source stateful agent/server with memory, API, possible OpenAI-compatible endpoint in some versions/configurations. Verify exact current repository, deployment mode, endpoint compatibility, session behavior, memory autonomy, licensing, authentication and resource costs. https://github.com/letta-ai/letta ; https://docs.letta.com
3. **Convai** — managed character conversational API, profiles/personas and voice. Verify actual text-only endpoint, API access tier, session isolation, ability to supply dynamic allowed context on each turn, privacy, German quality, costs, data retention and vendor lock-in. https://docs.convai.com/
4. **Rasa CALM** — controlled conversational flows, but possibly optimized for business task assistants rather than realistic client roleplay. Verify current edition/licensing and whether it adds value over our Director/Policy. https://rasa.com/calm
5. Secondary exploratory options: ProjectBEA, Shikigami Protocol, SillyTavern, ConversationSimulator, LettuceAI, Pipecat, LiveKit Agents, Open-LLM-VTuber. Distinguish standalone conversational services from frontends, character editors, voice pipelines, and SDKs. Do not claim they are interchangeable or suitable without verification.

The discussion previously favored Letta as first *research* candidate and Convai as a managed benchmark; this is **not** a technical acceptance. Claims about Letta's exact OpenAI-compatible endpoints, Convai pricing/API tiers, licenses and self-hosting must be reverified from current official sources. No candidate has been benchmarked in this project.

## 5. Test design — no execution without approval
Use the **same Herr Krüger scenario**, identical visible profile, allowed facts, German learner questions and Policy decisions for every candidate. Hidden facts: A unsuccessful prior 1,200 EUR repair and fear of recurrence; B maximum budget 8,000 EUR; C wife/bookkeeper co-decides. Generic oven-malfunction question does not open A. No heating symptom or discovery time is defined. Do not quietly enrich facts to justify hallucinations.

Two evaluation phases:
A. **Stateless, equal-context comparison**: naturalness, German conversational quality, role adherence, grounded factual claims, non-disclosure, initiative, latency, token/interaction costs.
B. **Stateful memory comparison**: coherent multi-turn context, correct recall, memory reset, no cross-session leakage, no hidden-fact contamination, pressure reactions and disclosure consistency.

Use deterministic policy decisions, frozen prompts/questions, identical scoring rubrics and independent human semantic review of actual outputs. Log model/version/parameters and repeat runs. Evaluate refusal/helpful-assistant role drift, fabricated facts, paraphrased leaks, incomplete verbal disclosure, low-confidence branch, prompt injection, and memory contamination. Do not interpret `temperature=0` as deterministic or `allowed_after` as fact spoken. Mark inconclusive if API unavailable. No synthetic responses presented as real API test evidence.

## 6. Decisions and guardrails
- Must-have: natural German conversation **and** strict external scenario control.
- Keep existing Director / Policy / Actor / Evaluation boundaries.
- Keep scenario truth in our DB, not in vendor memory.
- Provider can propose responses and optional state changes; our backend validates/commits.
- No provider access to full hidden card, internal rubric, secrets or arbitrary database write.
- GDPR/privacy review before real user data, especially external SaaS, retention, EU processing and deletion.
- Verify open-source license compatibility (including AGPL obligations), dependencies, security and maintenance.
- Voice/STT/TTS, 3D avatar, multi-user B2B, long-term learner memory and new dashboard concepts are **future possibilities**, not a prerequisite for the eight-day graduation MVP.
- No merge, deployments, API spend or code modifications without owner approval.

## 7. Deliverables Astra should prepare (research only)
1. Current-state map based on actual repository files, clearly distinguishing implemented vs planned.
2. Verified provider matrix: type (LLM / orchestrator / character engine / UI / voice), API contract, state/session, memory controls, self-host, license, cost, latency expectations, German support, GDPR/data location, integration effort, maturity.
3. Architecture recommendation: simplest feasible adapter and where to enforce scenario policy, persistence, session isolation and response validation.
4. Explicit comparison of baseline OpenAI Actor vs Letta vs Convai; justify excluding/including other candidates.
5. Small reversible proof-of-concept plan with tests, acceptance criteria, rollback and resource budget, **not execution**.
6. Open questions for the owner, including dashboard scope and whether provider memory should be disabled initially.
7. Clear verdict: ADOPT / EXPERIMENT / DEFER / REJECT per candidate with confidence and evidence URLs.

## 8. Review and disposal
This entire document exists only on `research/conversation-engine-options-2026-11`. No PR or merge is required to read it. If rejected, delete the research branch; the main branch remains unchanged. Before deletion, confirm no desired research artifacts are referenced only from the branch.
