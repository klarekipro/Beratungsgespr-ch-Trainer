# Functional dashboard prototype — implementation contract

2026-11-05. Current server version: `0.2.0-customer-dialogue`. The mentor and learner interfaces remain local workspaces of one owner; this is not multi-user authentication or a proven teaching system. A01/A01.1 and A02 remain the design and implementation history. The customer-dialogue update adds generated wording with a separate reply review, while Python retains control of discovery and stage transitions.

## Runtime and modes

Python/FastAPI serves `frontend/index.html`, `frontend/app.js` and `frontend/styles.css` from the same origin. SQLite stores company, scenario and session documents; a repository boundary permits a later PostgreSQL adapter. Website text can be pasted into a reviewed company profile. No arbitrary URL fetch is implemented.

`demo` is the explicitly labelled technical check without AI: a narrow keyword interpreter and authored customer replies. It does not assess free conversation. `openai` uses the server-side Responses API for interpretation, customer wording and an independent review of that wording. A normal successful live turn makes three sequential API requests, with no automatic retries or canned/demo fallback. No API key is sent to the browser, and opening the application or creating a session makes no AI request.

Every session creation must explicitly supply `mode: "demo" | "openai"`; there is no server default. Installing a key does not convert an existing session. Configuration status means that a key and model are present, not that the API or conversation quality has been verified.

## Shared document types

Company: `{id, revision, name, description, source_url, services:[{id,title,description,conditions}], limitations, reviewed}`. `source_url` is optional provenance, not a fetch command. The seed company is fictional. Identifiers begin with a lowercase ASCII letter or digit and continue with lowercase letters, digits, underscores or hyphens, up to 80 characters. `no_fit` is a reserved outcome, not a service ID.

Scenario: `{id, revision, company_id, title, customer_name, public_brief, opening, language:"ru"|"de", facts:[Fact], allowed_outcomes:[service_id|"no_fit"], question_hints:[str]}`. Scenario `id` may be omitted or empty on creation to request a generated ID. Catalogue responses include public metadata and `public_brief`; `opening` starts the session. Private fact values and allowed outcomes are not exposed through active learner views.

Fact: `{id,stage:"needs"|"capabilities",label,value,status:"known"|"undecided"|"does_not_know"|"refuses_to_disclose"|"not_applicable",keywords:[str],required:bool,material:bool}`. Every fact, including an optional fact, needs a nonempty authored value and explicit status. `keywords` is only for the limited demo matcher. Both `required` and `material` default to true; old snapshots without `material` are treated as material to preserve their previous policy.

| Fact policy | Effect |
|---|---|
| `required=true` | Must be discovered before its stage can close; requires `material=true` and a status other than `not_applicable`. Each stage needs at least one required fact. |
| `required=false, material=true` | Discovery is optional, but once discussed the fact must be reflected in the stage summary. A newly discovered material fact reopens an already confirmed relevant stage. |
| `required=false, material=false` | Descriptive detail may be answered without forcing repetition in the summary or reopening a confirmed stage. Any assertion the learner actually makes about it still has to be accurate. |

An absent author field is not evidence that the customer does not know the answer. Authored `does_not_know`, `undecided` and `refuses_to_disclose` are distinct valid states.

State: `{phase:"needs"|"capabilities"|"proposal"|"completed",discovered:[fact_id],needs_confirmed:bool,capabilities_confirmed:bool,events:[{type,turn,detail}],outcome:str|null}`. Learner turn numbers start at 1; the authored opening is turn 0.

Message: `{role:"customer"|"learner",text,at,turn,source?}`. New customer replies carry `source:"authored_demo"` or `source:"openai_actor_verified"`. The opening and legacy messages may lack `source`. The latter source means that the new pipeline completed its review; it is not a guarantee that the model's judgement is correct. Old messages are not relabelled as generated replies.

Session: `{id,scenario_id,company_snapshot,scenario_snapshot,mode,created_at,updated_at,status:"active"|"finished",review_status:"not_submitted"|"submitted"|"reviewed",review_note,reviewed_at,version,state,messages,receipts:{request_id:...},live_attempts,live_requests,api_count_complete,system_issues:[{type,turn,detail}]}`. Submission adds `submitted_at`; finishing saves `report`. Snapshots cannot change after creation. Legacy documents may omit newer metadata fields.

Learner session view: `{id,scenario_id,title,customer_name,mode,created_at,updated_at,status,review_status,review_note,version,phase,turn_count,messages,company,api_requests,api_count_complete,natural_customer_turns,report?}`. It excludes private snapshots, discovered IDs, internal events and the answer key during an active session. `report` appears after finish. Mentor review endpoints show only submitted/reviewed sessions.

Report: `{status:"complete"|"incomplete",summary,stages:[{id,label,confirmed}],findings:[{type,turn,detail}],facts:[{label,stage,status,discovered,value}],outcome,limitations:[str]}`. Findings include learning events other than individual `fact_discovered` events, plus recorded `system_issues`. Early offers remain visible after recovery. Demo limitations, generated versus legacy replies, partial request counts and authoring gaps are distinguished from evidence about the learner. No percentage score is fabricated. Previously saved finished reports remain historical records; exports also derive current mode/count labels from the session metadata.

## Request counts and legacy sessions

- `live_attempts` counts attempted live learner turns, including failures. `limits.max_live_attempts` limits these turns, not individual HTTP requests.
- `live_requests` counts initiated API requests observed by the current provider, including requests that fail. It is exposed as `LearnerView.api_requests`; before any new accounting, an old session can return `null`.
- `api_count_complete=true` is stored for new sessions, whose count starts at zero. Legacy sessions default to false and keep that value when resumed. Their new count is labelled as requests counted since the update; earlier calls remain unknown.
- `natural_customer_turns` counts messages with `source:"openai_actor_verified"`. A selected mode or configured key alone cannot increase it.

The server records the provider's request-count delta for each attempt. Request counts are not token totals or billing measurements. With the defaults, up to 30 live turn attempts can initiate up to 90 API requests. Duplicate delivery of a successfully recorded `request_id` returns the saved session without another API call.

## HTTP API (JSON, same origin)

Errors: `{error:{code,message}}` with a non-2xx HTTP status. No upstream response body, key or stack trace is exposed. Input text/list sizes are bounded; message text is limited to 6,000 characters. Validation errors, including an omitted session mode, return HTTP 422.

- `GET /api/status` → `{version,storage:"sqlite",access_mode:"local_workspaces",ai:{configured,model,live_enabled,customer_mode:"generated_and_checked",max_requests_per_turn:3},limits:{max_turns,max_live_attempts},roles:["mentor","learner"]}`. This is configuration/capability metadata, not a live connectivity test.
- `GET /api/company` → `{company}`.
- `PUT /api/mentor/company` with Company → `{company}`. Requires the current revision, increments it and preserves old session snapshots. An unreviewed company cannot start new training.
- `GET /api/scenarios` → `{scenarios:[{id,title,customer_name,public_brief,language,company_name}]}`.
- `GET /api/mentor/scenarios` → `{scenarios:[Scenario]}`.
- `POST /api/mentor/scenarios` with Scenario → `{scenario}`. Validates company/outcome compatibility; updates require the current revision and increment it.
- `DELETE /api/mentor/scenarios/{id}` → `{deleted:true}`. Existing sessions keep snapshots.
- `GET /api/sessions` → `{sessions:[{id,scenario_id,title,customer_name,mode,created_at,updated_at,status,review_status,phase,turn_count}]}`. List summaries do not include the detailed request counters.
- `POST /api/sessions` with `{scenario_id,mode:"demo"|"openai"}` → `{session: LearnerView}`. Both fields are required. Unconfigured OpenAI returns HTTP 409; the server does not choose demo instead.
- `GET /api/sessions/{id}` → `{session: LearnerView}`.
- `POST /api/sessions/{id}/messages` with `{text,kind:"message"|"summary"|"proposal",request_id,version}` → `{session: LearnerView}`. `kind` is a hint, not permission to bypass proposal detection. Successful delivery is idempotent on `request_id`; stale versions and reuse of an ID with different text/kind return HTTP 409.
- `POST /api/sessions/{id}/finish` → `{session: LearnerView}`. Can finish incomplete; no further conversation turns are accepted.
- `POST /api/sessions/{id}/submit` → `{session: LearnerView}`. Finished only. Adds the session to the internal mentor queue; sends no email.
- `GET /api/sessions/{id}/export.txt` / `export.pdf` / `export.json` → download, finished only. Includes dialogue, mode, request-accounting limits, snapshots/revisions and stage evidence. JSON excludes request receipts.
- `GET /api/mentor/reviews` → `{sessions:[summary plus report,review_note]}`. Only submitted/reviewed sessions.
- `GET /api/mentor/reviews/{id}` → `{session: LearnerView}`; only submitted/reviewed.
- `POST /api/mentor/reviews/{id}` with `{note}` → `{session: LearnerView}`; mark reviewed.

Mentor endpoints require `X-Workspace-Role: mentor`. This is a UI boundary in a localhost-only single-owner app, not authentication for multiple users. Later shared use needs real accounts and ownership checks, not just PostgreSQL. Foreign-Origin mutations are rejected; there is no permissive CORS.

## Interpretation, customer wording and review

`engine.py` exports async `process_turn(session,text,kind,provider,turn) -> dict` and `build_report(session) -> Report`. `process_turn` works on copies and returns state plus learner/customer messages only after the entire selected pipeline succeeds. Python alone applies transitions.

`providers.py` exposes `DemoProvider` and `OpenAIProvider(api_key,model,timeout=30,client=None)`. The optional client supports isolated transport tests. The timeout is per request. `provider.interpret(session,text,kind)` returns `{act:"question"|"summary"|"proposal"|"other",fact_ids:[str],summary_ok:bool,summary_evidence:[{fact_id,quote}],proposal_outcome:str|null,proposal_ok:bool,source_quote:str,uncertain:bool}`. Python validates IDs, exact evidence quotes and the prior state. The interpreter receives topic labels for unrevealed facts, already disclosed values, company capabilities and visible history. It does not receive the private outcome key or unrevealed fact values.

For `openai`, Python constructs a separate bounded customer context and calls `provider.respond(context) -> {reply,verified_fact_ids}`. Context fields are `{language,customer_name,opening,learner_text,visible_history,authorized_facts:[{id,label,value,status}],must_address_fact_ids,response_intent,company:{name,services,limitations}}`. Authorized facts consist of previously disclosed facts plus those selected for this answer. No full scenario, phase flags, scores or outcome key are passed to the Actor. The reaction intent remains private; customer speech must not announce stages or coach the employee.

`customer_actor.py` owns the Actor/review contracts:

1. Actor returns `{reply,used_fact_ids,scenario_gap}`. It may paraphrase authorized reality, but cannot invent facts or fill missing author fields with customer ignorance. Its IDs are only a self-report.
2. A separate verifier receives `{context,reply}`, without the Actor's self-reported IDs. It returns `{grounded,in_role,consistent_with_intent,addressed_fact_ids,unsupported_quotes}`. Local validation checks the structure, allowed IDs, exact unsupported-claim quotes, positive verdicts and complete coverage of `must_address_fact_ids`.
3. `respond()` returns only the reviewed reply and validated fact IDs. The engine also checks that all selected facts were expressed before saving their disclosure. No candidate reply is shown on failure.

Strict JSON schemas, `store:false`, bounded outputs and independent review reduce specific failure modes. They do not prove semantic correctness or naturalness; the verifier is also a model judgement.

## Stage policy and atomic failures

Needs/capabilities close only after every required applicable fact is discovered and a supported summary covers every discussed material fact of that stage. An accurate optional non-material detail may be omitted from a summary; a false assertion about it is still invalid. New material information reopens an already confirmed relevant stage. A correction or a question alone does not close a stage.

A proposal requires both prior confirmations, an allowed scenario outcome and a supported company service or `no_fit`. Asking whether the customer prefers repair is discovery; actually offering repair or a diagnostic visit is a proposal. Later answers cannot justify an earlier offer. The event remains in the report after recovery.

Interpretation, Actor and verifier failures commit no new dialogue, disclosure, stage confirmation or successful-turn receipt. The server can still persist the live attempt/request counters separately. Missing Actor capability in live mode is an error, never a canned reply.

When the Actor reports an absent author fact, `scenario_missing_context` returns HTTP 422 with an explicit explanation that the scenario lacks information and the learner is not at fault. The server stores a separate `{type:"scenario_missing_context",turn,detail}` in `system_issues`, retaining the latest 30 entries. These are added to the finished report; no fabricated customer answer is appended. Other provider/verification failures return a safe HTTP 502 response. The existing session mode never silently changes.

## Built-in scenarios and upgrade safety

`seeds.py` exports `SEED_COMPANY`, `SEED_SCENARIOS`, `DEMO_WALKTHROUGH` and `PREVIOUS_BUILTIN_SHA256`. The three cases are fictional; the walkthrough is a guided technical example, not an independent learner assessment. New optional technical details explicitly author symptoms, identification uncertainty and unknown causes rather than asking the model to invent them.

On startup, SQLite seeds a new database once. `upgrade_builtin_scenarios()` then upgrades only cards whose full canonical JSON SHA-256 matches a known shipped fingerprint and whose new revision is greater. In this update the known A02 `oven_uncertain` revision 2 and `oven_no_fit` revision 1 can become revisions 3 and 2. Mentor edits are preserved, deleted cards are not recreated, and existing session snapshots are never migrated. Older cards without `material` remain readable with the default-true compatibility policy.

## Acceptance boundaries

Local checks cover persistence, snapshot/privacy boundaries, explicit modes, stage gates, material details, partial legacy counts, actual disclosure after verified wording, scenario gaps, transport/Actor/verifier failures, duplicate delivery, export and the internal review queue. Mocked responses test these contracts; they do not establish that a real model interprets or acts naturally. A live review must separately check contextual clarification, compound questions, short follow-ups, stable uncertainty, factual grounding and an ordinary customer voice. No paid live evaluation is claimed by this contract.
