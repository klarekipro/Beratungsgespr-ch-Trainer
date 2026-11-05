# Functional dashboard prototype — implementation contract

2026-11-05. Implements the owner's authorization to build the mentor and learner interfaces. A01/A01.1 remain the design history. This is a local single-owner prototype with two workspaces, not multi-user authentication or a proven teaching system. Existing research and historical tests are preserved.

## Runtime

Python/FastAPI serves `frontend/index.html`, `frontend/app.js`, `frontend/styles.css` from the same origin. SQLite stores companies, scenarios and sessions as versioned JSON snapshots; a repository boundary permits a later PostgreSQL adapter. OpenAI uses the Responses API via server-side HTTP, no API key in browser. Scenario mode is deterministic and explicitly labelled, never a silent fallback from OpenAI. Website text can be pasted into a reviewed company profile; no arbitrary URL fetch is implemented.

## Shared document types

Company: `{id, revision, name, description, source_url, services:[{id,title,description,conditions}], limitations, reviewed}`. `source_url` is optional provenance, not a command to fetch. Seed company is fictional. Service IDs use lowercase ASCII identifiers. `no_fit` is a reserved outcome.

Scenario: `{id, revision, company_id, title, customer_name, public_brief, opening, language:"ru"|"de", facts:[{id,stage:"needs"|"capabilities",label,value,status:"known"|"undecided"|"does_not_know"|"refuses_to_disclose"|"not_applicable",keywords:[str],required:bool}], allowed_outcomes:[service_id|"no_fit"], question_hints:[str]}`. All required facts need explicit value/status. `keywords` supports the limited scenario-mode matcher, not proof of free-language comprehension. `public_brief` and opening alone are learner-visible before discussion; private facts and allowed outcomes never appear in catalogue responses.

State: `{phase:"needs"|"capabilities"|"proposal"|"completed",discovered:[fact_id],needs_confirmed:bool,capabilities_confirmed:bool,events:[{type,turn,detail}],outcome:str|null}`. Turn IDs start at 1 for learner turns. Messages: `{role:"customer"|"learner",text,at,turn}`. Session: `{id,scenario_id,company_snapshot,scenario_snapshot,mode:"demo"|"openai",created_at,updated_at,status:"active"|"finished",review_status:"not_submitted"|"submitted"|"reviewed",review_note,reviewed_at,version,state,messages,receipts:{request_id:...},live_attempts}`. Snapshots cannot change after creation.

Learner session view: `{id,scenario_id,title,customer_name,mode,created_at,updated_at,status,review_status,review_note,version,phase,turn_count,messages,company,report?}`. No private snapshots, discovered IDs, internal events or answer key during an active session. `report` appears only after finish. Mentor review can access a finished submitted session and its report, but does not inspect unsubmitted learner sessions.

Report: `{status:"complete"|"incomplete",summary,stages:[{id,label,confirmed}],findings:[{type,turn,detail}],facts:[{label,stage,status,discovered,value}],outcome,limitations:[str]}`. Preserve distinction between scenario mode, real API use, incomplete data, and pedagogical validation. Mark early offers even if the learner later corrects course. No percentage score is fabricated.

## HTTP API (JSON, same origin)

Errors: `{error:{code,message}}` with appropriate non-2xx HTTP status. No provider body, key or stack trace is exposed. Requests have bounded text/list sizes.

- `GET /api/status` → `{version,storage:"sqlite",access_mode:"local_workspaces",ai:{configured,model,live_enabled},limits:{max_turns,max_live_attempts},roles:["mentor","learner"]}`. Configured needs both a key and model. No API call on load.
- `GET /api/company` → `{company}` (public, reviewed capabilities available to learners).
- `PUT /api/mentor/company` with Company → `{company}`. Increments revision; no mutation of old snapshots.
- `GET /api/scenarios` → `{scenarios:[{id,title,customer_name,public_brief,language,company_name}]}`.
- `GET /api/mentor/scenarios` → `{scenarios:[Scenario]}`.
- `POST /api/mentor/scenarios` with Scenario (id optional/empty for new) → `{scenario}`; validate against company capabilities. Update uses same ID, increments revision.
- `DELETE /api/mentor/scenarios/{id}` → `{deleted:true}`; existing sessions keep snapshots.
- `GET /api/sessions` → `{sessions:[{id,scenario_id,title,customer_name,mode,created_at,updated_at,status,review_status,phase,turn_count}]}`.
- `POST /api/sessions` with `{scenario_id,mode}` → `{session: LearnerView}`.
- `GET /api/sessions/{id}` → `{session: LearnerView}`.
- `POST /api/sessions/{id}/messages` with `{text,kind:"message"|"summary"|"proposal",request_id,version}` → `{session: LearnerView}`. `kind` guides interpretation but cannot override early-proposal detection. Idempotency on request_id; conflict on stale version or reused ID with another payload. A provider error commits no dialogue/state progress and does not fall back to demo.
- `POST /api/sessions/{id}/finish` → `{session: LearnerView}`. Can finish incomplete; finished session is immutable except submission/review.
- `POST /api/sessions/{id}/submit` → `{session: LearnerView}`. Finished only. Adds to mentor review queue, sends no email.
- `GET /api/sessions/{id}/export.txt` / `export.pdf` / `export.json` → download, finished only. Includes dialogue, mode, dated snapshots/revisions, stage evidence and limitations.
- `GET /api/mentor/reviews` → `{sessions:[summary plus report,review_note]}`. Only submitted/reviewed sessions.
- `GET /api/mentor/reviews/{id}` → `{session: LearnerView}`; only submitted/reviewed.
- `POST /api/mentor/reviews/{id}` with `{note}` → `{session: LearnerView}`; mark reviewed.

Mentor endpoints require `X-Workspace-Role: mentor`. This is an interface boundary in a localhost-only single-owner app, not authorization for multiple users. Do not expose it to an untrusted network. Later real users require authentication/ownership checks, not just PostgreSQL. Mutations with a foreign Origin are rejected; no permissive CORS.

## Engine boundary

`backend/app/dashboard/engine.py`: async `process_turn(session:dict, text:str, kind:str, provider, turn:int) -> dict` returns a new session dict containing updated `state` and appended learner/customer `messages`; must not mutate the input on failure. `build_report(session:dict) -> dict` returns Report. Provider selected explicitly by server, not by untrusted request internals.

`backend/app/dashboard/providers.py`: `DemoProvider` and `OpenAIProvider(api_key,model,timeout=30)`. Engine calls async `provider.interpret(session,text,kind) -> dict` with `{act:"question"|"summary"|"proposal"|"other",fact_ids:[str],summary_ok:bool,summary_evidence:[{fact_id,quote}],proposal_outcome:str|null,proposal_ok:bool,source_quote:str,uncertain:bool}`. The engine validates IDs, quotes and before-state. Model never writes state. OpenAI receives field labels for unrevealed facts, only disclosed values for summaries, current phase and visible transcript. Company capabilities are allowed context. Private outcome key is not used as an instruction to force a sale. Caller refuses malformed responses.

Actor replies use authored fact values and controlled reactions. No freely generated facts. N/C close only when required applicable facts have been discovered and the learner's summary has valid evidence for them; unsupported/contradictory/uncertain summaries do not close. A correction alone does not close a stage. Proposal requires both prior confirmations, allowed scenario outcome and an existing company service (or no_fit). A question about repair preferences is distinct from offering repair. An actual diagnostic visit is also an offer. Only successfully completed turns append messages. `DemoProvider` is a narrow matcher with disclosed limitations; it does not claim AI semantic reliability.

`backend/app/dashboard/seeds.py`: exports `SEED_COMPANY:dict`, `SEED_SCENARIOS:list[dict]`, `DEMO_WALKTHROUGH:list[dict]` (scenario_id, turns with text/kind) for reproducible technical checks. At least 3 fictional variants including unknown budget and no_fit. Provide natural Russian question examples and exact workable summary examples for scenario mode; identify them as a guided technical example.

## Acceptance boundaries

Check real HTTP persistence, private-field filtering, draft edits/snapshot isolation, early proposal, summary gates, unknown budget, justified no_fit, malformed provider response, upstream failure without fake progress, duplicate/stale requests, exports and internal review. Browser-check both workspaces and responsive dialogue. Real OpenAI calls require server configuration and an intentional user conversation; no key exists in this execution environment and no paid evaluation is claimed.
