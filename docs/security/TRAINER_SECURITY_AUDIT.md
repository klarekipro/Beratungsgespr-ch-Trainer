## MISSION 06.1 — актуальное дополнение, 24.11.2026

Подготовлены действительные Docker/CI adapters и исправленный privacy contract в той же working branch. [Pilot runbook](TRAINER_PILOT_RUNBOOK.md), [Access plan](TRAINER_ACCESS_PLAN.md), [Python Security CI](TRAINER_SECURITY_CI.md), [read-only VPS admission](TRAINER_VPS_PREFLIGHT.md) определяют текущие условия. Ни публикации, ни перенос данных/секретов, ни изменение working infrastructure не выполнялись. Native advisories и непроверенные activation gates не выданы за PASS. Ниже сохранена историческая MISSION06 оценка.

---

# Trainer Security Audit — facts before implementation

## Результат для владельца

Аудит завершён; **совместный cloud-пилот пока BLOCKED**. Trainer — публичный исходный репозиторий; работающая установка остаётся локальной 0.15.3. Точная организация — **klareki-lab**, доступ admin, план Team. В 19 доступных репозиториях выполнена read-only инвентаризация; подробный внутренний список сохранён локально вне Git. Существующий исторический npm audit учтён.

Фактически: Gitleaks PASS для 16 опубликованных корней истории; OSV PASS для 24 установленных Python-пакетов; ограниченный Semgrep PASS для 60 исходных единиц. Из трёх текущих security-тестов два PASS, один FAIL: он ошибочно ожидает доступ наставника после finish без submit. Дополнительный тест подтвердил правильный контракт приватности; отдельные PDF/Unicode и mocked AI-wire проверки PASS. Рабочая БД не использовалась, платных AI-вызовов нет.

Владелец подтвердил оплаченный VPS/сервер; ОС, ресурсы, изоляция и backup хоста пока не проверялись. Перед пилотом нужны исправление ожидания теста, соответствующий целевому хосту transitive/hash lock, проверенная настройка HTTPS/Access/proxy, отдельное хранилище и restore-проверка. Модель snapshot помечена Deprecated; её доступность не проверялась платным вызовом и модель не заменялась. Ни лицензия на перенос всего проекта/медиа, ни полная PII-проверка истории не сертифицированы.

23.11.2026, Europe/Berlin. MISSION 06. Source: `klarekipro/Beratungsgespr-ch-Trainer`, audited main `332a4f4d7f919fc570d9e8d44de2d9be326e7677`. Working branch: `codex/mission-06-cloudflare-readiness`. Planning/audit only; no push, merge, deployment, data transfer, new remote repository, cloud resource or secret transmission.

Pilot release verdict: **BLOCKED** pending the concrete gates below. This is not a claim that the localhost application is publicly deployed or that the identified test failure is an access-control vulnerability.

## Verified source and account scope

- Original repository is currently **public**, not private. README explicitly describes published code/video, not a public hosted application. Visibility was not changed. Older handoff statements about PRIVATE are historical.
- Exact organization is **klareki-lab** (Organization ID 281544158). `klarekilub` returns 404 through the available API. Authenticated identity is klarekipro; org membership is active/admin, and accessible project metadata reports admin permissions.
- Organization **Team** plan is verified. Included Actions balance/overage budget and incremental collaborator-seat billing are **NOT VERIFIED**; do not inherit sergjuri's Free restrictions or billing receipt.
- 19 accessible repositories inspected read-only: 10 personal + 9 organization, 11 private + 8 public. Full internal inventory and API evidence are kept outside this public-repository worktree in the local mission evidence directory; private project names and billing details are not exported into these documents.
- Audited source main is 332a4f4d7f91. The live local checkout remains on its own branch/HEAD 28e2a6688794; backend/frontend/scripts/tests/requirements have no tracked differences between those two source commits. Publication metadata/release materials differ.
- Running localhost instance: GET `/api/status` confirms **0.15.3-persona-localization**, SQLite, role portals, simple_actor, configured/live-enabled flags, max_turns=30 and max_live_attempts=30. It does not prove successful model availability. Unauthenticated status correctly omits runtime details and sends no-store. Loaded process commit was not queried with privileged tokens.
- Listener remains 127.0.0.1:8100. Working DB was not opened, copied, migrated or tested. All new test DBs were temporary/synthetic.

## Current architecture

FastAPI `create_app` in backend/app/dashboard/server.py:89; static first-party frontend is served from the **same origin** by FastAPI at /static and role portal routes. There is no JavaScript build/package manifest and no remote frontend code import found in the runtime frontend. Do not add npm installation/audit as if this were a Node app.

SQLiteStore (store.py:27–52) uses a real filesystem, WAL, foreign keys, per-connection transactions and 10-second busy timeout. Auth, users, token hashes, CSRF values, session ownership, documents, profile/material snapshots, feedback and certificate metadata share durable SQLite. Imported source content is retained in versioned records, including encoded original document bytes. Backend generation returns PDF/TXT/JSON; transient audio/PDF extraction uses temporary files.

The native process uses one Uvicorn worker. Per-session asyncio locks and transcription limits are process-local: do not scale by adding workers/replicas without changing coordination and testing SQLite contention. Startup creates/schema-checks storage and can seed/upgrade exact built-in records; importing server is not a read-only operation unless TRAINER_DATA_DIR is isolated.

## Auth/session/API protections actually found

| Control | Evidence / result |
|---|---|
| Password hashing | Argon2id via argon2-cffi, time_cost=3, memory_cost=65536 KiB, parallelism=2; password length 12–128 |
| Sessions | Random 32-byte URL-safe tokens, only token hashes stored, eight-hour lifetime, revoke on reset/deactivation/logout |
| Cookies | HttpOnly, SameSite=Strict; Secure and HTTPS enforcement enabled by TRAINER_REMOTE_HTTPS=1 |
| CSRF | Exact same-origin scheme/host plus constant-time X-CSRF-Token comparison for authenticated unsafe API methods |
| Role/ownership | Employee/mentor checks, cross-user 404; no X-Workspace-Role impersonation accepted |
| Privacy contract | finish does not expose a conversation to mentor; explicit submit is required |
| Input/headers | Pydantic validation, bounded request bodies, TrustedHost allowlist; CSP, nosniff, Referrer-Policy, no-store for portals/API |
| Rate controls | Login thresholds and bounded dictation; not an aggregate account-level spend cap |
| AI isolation | Current simple_actor uses server-side HTTP; mocked-wire test confirms one Responses call, store=false, no previous_response_id or verifier. Actor/model/prompts were not changed |

Local defaults are not a remote deployment configuration. HTTPS forwarding, exact allowed hostname, Access token validation, cache bypass and origin isolation still require pilot configuration and acceptance.

## Dependencies and actual checks

Direct pins: FastAPI 0.141.1, Uvicorn 0.52.1, Pydantic 2.13.4, HTTPX 0.28.1, ReportLab 4.4.9, argon2-cffi 25.1.0. Existing CPython is 3.14.7, with 24 installed packages including Starlette 1.10.0, Pillow 13.0.0, pydantic_core 2.46.4 and argon2-cffi-bindings 26.1.0. The six direct pins do **not** constitute a transitive/hash lock for Linux.

| Check | Actual result | Limits |
|---|---|---|
| Existing Gitleaks 8.30.1 | **PASS**, zero findings across 16 published branch/tag history roots | Default rules; no new ignores/exceptions; compressed release/media assets and PII clearance not certified |
| Existing OSV Scanner 2.7.1 | **PASS**, all 24 installed-environment packages checked, zero known findings | Installed macOS snapshot only; not an approved Linux/Pyodide resolution; only package metadata sent to OSV |
| Existing Semgrep CE 1.186.0 | **PASS**, 60/60 real backend/frontend/scripts source units scanned, zero findings | Six reviewed local JS/Python rules; offline container; not complete interfile/auth proof |
| Existing focused security regression | **FAIL**, 3 executed: 2 passed, one IndexError | Failed mixed privacy test expects mentor history before submit; no failed result relabelled |
| Targeted privacy-contract follow-up | **PASS** | Synthetic finish/private → submit/visible sequence; does not override failed existing regression |
| Native PDF/Unicode/font smoke | **PASS** | Separate synthetic layout/font test; local native environment only |
| Mocked AI wire contract | **PASS** | No network/API call; does not establish live model availability or training quality |
| Hosted Trainer security workflows | **NOT VERIFIED / not installed** | None found on Trainer; no hosted jobs triggered in this mission |

All checks used existing tools/venv/images. Network audit hooks observed zero outgoing attempts in app tests; no paid AI calls. No production database test or restore was performed.

## Findings and release gates

| ID | Severity / status | Concrete finding and action |
|---|---|---|
| TEST-001 | Medium / **FAIL** | tests/functional/test_portals.py:148 expects an unsubmitted finished conversation in mentor history. server.py:235–241 and :634–637 intentionally require submit. Update the test to assert private-before-submit and visible-after-submit; do not weaken the filter or exclude the test. Current exact regression remains required until fixed |
| DEP-001 | Medium / **BLOCKED for reproducible deployment** | No full transitive/hash lock or Linux resolution. Produce reviewed Python 3.14 Linux wheel hashes/SBOM, then verify that exact environment; do not copy the macOS venv |
| EDGE-001 | High release gate / **NOT VERIFIED** | No verified pilot hostname, Access policy/JWT validation, restricted origin/proxy configuration or multi-user staging acceptance. Current listener is localhost; this is not evidence of a current public exposure |
| AI-001 | Medium / **NOT VERIFIED** | Pinned gpt-4.1-mini-2025-04-14 is marked Deprecated in current official model documentation. Confirm approved account availability/transition before live pilot; no automatic model substitution or paid probe |
| DATA-001 | Medium / **NOT VERIFIED** | First-party LICENSE absent; media/release rights and personal-data clearance for copying not certified. Historical missing legacy raw archives are recorded by old handoffs, not re-audited or repaired here |
| OPS-001 | Medium / **NOT VERIFIED** | Off-host encrypted backup/restore drill, Linux fonts/ffprobe/Poppler packaging, quotas/budgets and pilot uptime are not established |
| WORKER-001 | Architecture / **BLOCKED as a direct lift-and-shift** | Persistent local SQLite, OS subprocesses, native crypto/package compatibility and thread-dependent paths require adaptation for Workers. See feasibility comparison |

## Existing Klare KI workflows — avoid duplication

Trainer has zero registered workflows and no Dependabot config; CodeQL default setup explicitly reports not-configured. Standard .gitleaks/.semgrep/Sonar/pre-commit/OSV config paths were not found on inspected default branches.

The organization inventory also found an existing historical `npm audit` in public WBS-Universal-AI-Project-Manager frontend QA, plus build/import/QA workflows. Four registered workflows missing from default branches were resolved against their last-run feature commits rather than falsely treated as absent. Preserve/review that npm audit coverage before choosing a dependency scanner. Default-branch metadata alone is not a statement about every active feature branch or external security service.

External GitHub Apps/Sonar installations and full non-Trainer source audits are **NOT VERIFIED**. The local evidence inventory is the per-repo source of truth for later owner-approved activation; no scanner was installed across those repositories.

## References

- [FastAPI proxy handling](https://fastapi.tiangolo.com/advanced/behind-a-proxy/).
- [Pinned model status/pricing](https://developers.openai.com/api/docs/models/gpt-4.1-mini).
- Cloudflare runtime/storage sources and exact alternatives: [feasibility](TRAINER_CLOUDFLARE_FEASIBILITY.md).
- Concrete changes, release order and owner decisions: [deployment plan](TRAINER_DEPLOYMENT_PLAN.md).
