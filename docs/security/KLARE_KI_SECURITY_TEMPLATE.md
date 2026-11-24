## MISSION 06.1 — актуальное дополнение, 24.11.2026

Подготовлены действительные Docker/CI adapters и исправленный privacy contract в той же working branch. [Pilot runbook](TRAINER_PILOT_RUNBOOK.md), [Access plan](TRAINER_ACCESS_PLAN.md), [Python Security CI](TRAINER_SECURITY_CI.md), [read-only VPS admission](TRAINER_VPS_PREFLIGHT.md) определяют текущие условия. Ни публикации, ни перенос данных/секретов, ни изменение working infrastructure не выполнялись. Native advisories и непроверенные activation gates не выданы за PASS. Ниже сохранена историческая MISSION06 оценка.

---

# Klare KI Security Template — portable reference, not installed CI

## Что подготовлено

Подготовлен переносимый **контракт и два неактивных YAML-примера**: PR/manual Security и отдельный короткий advisory-only монитор. Добавлен профиль Trainer. YAML прошёл actionlint/zizmor; полноценный профильный адаптер и hosted CI **не установлены и NOT VERIFIED**. Не выдавать примеры за работающую систему.

Сохраняются проверенные механизмы sergjuri: запуск только соответствующих проверок, хеши реальных входов, повторное использование подтверждённых PASS и FAIL, отмена устаревших PR jobs, минимальные permissions, SHA/checksum pins, короткое хранение обезличенных отчётов. Пропуск, пустой dependency graph или отсутствующий адаптер не дают PASS. Существующие npm audit/мониторы не дублируются.

Для Trainer нужны Python lock/SBOM, Python/JS SAST и реальные security-тесты; npm-проверка без package.json не добавляется. До размещения в .github/workflows требуется завершить адаптер, исправить TEST-001, проверить бюджет соответствующего аккаунта и подтвердить реальный hosted запуск. Новых сервисов/репозиториев/платных сканеров не создаётся.

23.11.2026, Europe/Berlin. MISSION 06. Source: `klarekipro/Beratungsgespr-ch-Trainer`, audited main `332a4f4d7f919fc570d9e8d44de2d9be326e7677`. Working branch: `codex/mission-06-cloudflare-readiness`. Planning/audit only; no push, merge, deployment, data transfer, new remote repository, cloud resource or secret transmission.

Status: **prepared / hosted execution NOT VERIFIED**. These are inactive contract templates in docs, not .github/workflows. No scanner was reinstalled or enabled in any Klare KI repository. The existing sergjuri baseline is the verified behavioral reference; it is not copied as a universal app-specific runner.

## Discovery and migration rules

Read default and actual development branches, workflows, default security setup, lockfiles, runtime source roots and budget before activating anything. Trainer has no workflows/Dependabot and CodeQL default is not-configured. An existing WBS frontend QA npm audit on a feature branch was found; preserve or wrap its coverage rather than adding OSV over the same graph without a justified scope difference. A 404 YAML on main is not absence of that historical workflow.

Profiles from the 19-repo inventory: native Python/FastAPI; Node/TypeScript/Astro including nested lockfiles/monorepos; first-party browser JS without npm; shell/ops with a nested Node project; docs/media/unknown branches. Never classify a repo docs-only merely because default main lacks the app still being developed on another branch.

Full internal per-repo mapping stays in the local read-only evidence inventory outside the public worktree. This plan does not expose private repo names or require a cross-repository PAT.

## Stack-applicable checks

| Profile | Required coverage | Do not add blindly |
|---|---|---|
| Trainer/native Python | Gitleaks; local Python+real frontend Semgrep; OSV full locked Python runtime/test graph; actionlint/zizmor when workflow definitions are present; isolated auth/ownership/CSRF/export/mock-AI tests; runner safety fixtures | npm install/audit with no package.json; sergjuri runtime.json/SheetJS exceptions; paid live OpenAI tests |
| Node/TS/Astro | Gitleaks; applicable local JS/TS SAST; authoritative lockfile advisory check for every deployed package root; workflow checks; genuine existing offline tests | Duplicate npm audit and OSV with identical graph/policy; only scanning config while skipping real src/inline JS |
| Shell + nested app | Secrets/workflows plus nested Node graph; ShellCheck only when reviewed/available, otherwise explicit unverified shell coverage until addressed | Claiming Semgrep JS rules audited arbitrary shell code |
| Docs/media | Secrets and applicable workflow checks after verifying there is truly no runtime code/dependency graph | Fake zero-package dependency PASS; automatic approval of binary/media privacy/license |
| Unknown/unlocked graph | **BLOCKED** until source/profile/lock identity is known | Falling back to a green empty scan |

Inactive example files: [PR/manual workflow](templates/security.yml.example), [advisory-only workflow](templates/advisories.yml.example), [Trainer profile](templates/trainer-profile.json.example). They define a porting contract; tools/security/run.py is deliberately not installed by this planning task. Missing adapter/profile fails BLOCKED, never succeeds as a stub.

## Keep the proven baseline mechanics

Reuse reviewed versions: Gitleaks 8.30.1 MIT, OSV Scanner 2.7.1 Apache-2.0, Semgrep CE 1.186.0 LGPL-2.1, actionlint 1.7.12 MIT, zizmor 1.33.1 MIT; official SHA/checksum receipts and pinned Semgrep image from the existing baseline. No global/latest reinstall, SaaS upload, paid CodeQL assumption, Sonar subscription or platform token. Actual new local audit reused those binaries/images successfully.

External actions pinned to verified SHAs: checkout v7.0.1 `3d3c42e5aac5ba805825da76410c181273ba90b1`; cache v6.1.0 `55cc8345863c7cc4c66a329aec7e433d2d1c52a9`; upload-artifact v7.0.2 `cf430e030ddbb5b0abf93d22962f4752f3646cd9`. Only contents:read for normal CI. PR source executes without cloud keys/production data or privileged pull_request_target. Test/source containers are offline, capability-dropped and run as runner UID/GID; dependency acquisition is a separate reviewed preparation step.

The current sergjuri runner has app-specific paths/tests/runtime maps. Port them to an explicit profile adapter, retaining plan/smart/gate semantics and safety fixtures. Do not merely paste it into Trainer and report success. Required implementation deltas: complete Python locked-graph adapter, Python offline dependency environment, selected current tests (including TEST-001 until fixed), source roots, OS-tool/font smoke, advisory-only entrypoint, and profile-defined required checks. The reference workflow's --profile/advisories interface is a **future adapter contract**, not a claim the existing CLI already supports those flags.

## Events, receipts and status

PR events opened/synchronize/reopened/ready_for_review plus manual workflow_dispatch. Concurrency keyed by PR number/ref cancels superseded runs. No full-scanner schedule and no push-main deployment. A cheap planner/gate runs even when expensive work is reused; path-skipped jobs do not become security approval.

Per-check SHA-256 covers real inputs, profile/engine/rules/tool policy. Secrets include Git patch history, including added-then-deleted values; noop commits need not repeat scans. SAST hashes selected actual code and rules; dependency checks hash full lock/SBOM and knowledge freshness; tests hash code/test/build/fixture inputs; workflow checks hash definitions/policy. Changed scanner/profile engine invalidates related evidence.

Reuse only complete executed PASS **or FAIL** with exact input/tool/policy identity, original timestamp/commit/run ID and bounded age. Reject skipped, BLOCKED, missing, tampered, incomplete and expired receipts. Retain failing evidence rather than masking it. GitHub PR/manual trust scopes may be cold; a missing cache is not proof of security. These receipts are optimization within reviewed PRs, not independently signed attestations or protection against an author changing CI policy.

Only profile-required checks contribute to PASS. Inapplicable tools are omitted with a separately recorded scope reason, not relabelled PASS. Unknown applicability is BLOCKED. FAIL means a blocking finding/test failure; BLOCKED means access/tool/resource/coverage failure; NOT VERIFIED means absent/unconfirmed evidence. Every non-PASS mandatory gate returns nonzero. The Trainer's known failing regression remains FAIL until fixed, without an exclusion.

Cache only small redacted receipts, no binaries/secrets/customer data. Seven-day report artifacts; no redundant artifact on completely reused runs. Allowlist report fields (rule/file/line/severity/advisory/hash), no raw secret matches, snippets, learner conversations or provider payloads. Missing report or parse/coverage failure is never a clean scan.

## Separate advisory monitoring

Exactly one lightweight advisory owner per dependency graph, scheduled daily plus manual. It reads a versioned deployed-runtime SBOM and applicable locked test/tool graph with source/lock hashes, and performs only advisory lookups. New advisories must be checked even when source is unchanged; do not cache yesterday's threat knowledge indefinitely. No repeated tests/SAST/Gitleaks/actionlint/zizmor in the daily job.

If an equivalent scheduled monitor already exists, preserve it instead of adding another. The two sergjuri daily OSV/Access workflows remain untouched; do not remotely clone private code or introduce duplicate Cloudflare probes. A missing/out-of-date/unidentified deployed graph is BLOCKED, not an empty PASS. Dependency fixes return through normal PR checks; no auto-merge or production deploy.

## Python dependency and test contract

Six direct pins alone leave transitive resolution open. Prepare a reviewed Linux CPython 3.14 wheel/hash lock, verify exact graph identity, and run OSV against it. Reuse approved wheels/env when input hashes match. Do not execute arbitrary source builds/install scripts with credentials. For browser-only Trainer frontend use Node syntax/local tests where applicable, without inventing npm dependencies.

Import server only after setting an isolated TRAINER_DATA_DIR and blank/synthetic key, disabling private audit and blocking network. Never mount working SQLite/Keychain/cloud tokens. Include login/reset/deactivation, CSRF/expiry/cookies, cross-user read/write/export denial, finish→submit privacy, fonts/PDF and mocked API-wire tests. Existing legacy tests need classification/updates, not blanket deletion/suppression. No training-quality score or live AI acceptance is inferred from deterministic tests.

## Rollout with no new service

1. Review/repair Trainer test and lock; finish and locally validate its profile adapter and scanner fixtures.
2. Review inactive templates, actual account Actions quota, overage stop and host budget. The sergjuri billing receipt does not cover klarekipro/klareki-lab. Public repo free runners do not certify private org budget.
3. Owner authorizes explicit branch/PR activation; then verify a real hosted changed-input run and a matching-input reuse run before calling CI operational.
4. Adopt the same versioned, reviewed template bundle per approved repo/profile. Do not create a new central repository or GitHub App in this mission. Local template vendoring avoids public/private/cross-owner reusable-workflow access assumptions and PAT sprawl.
5. Consider a pinned reusable org workflow only after verifying caller visibility/access and owner approval. Preserve existing tests/dependency scans, and stagger advisory schedules rather than multiplying full runs.

Team entitlement is verified for the org; actual ruleset configuration/collaborator seat costs still require owner review. Trainer public main is unprotected. Do not claim required checks are enforced before the settings actually exist. Hosted integration, daily advisory implementation, lock generation and branch-rule activation are **NOT VERIFIED / not performed**, separate from the completed local audit and static template validation.

## Local reference validation

Both inactive workflow examples passed existing actionlint 1.7.12 core syntax/expressions and offline zizmor 1.33.1 with zero findings. The profile JSON parsed and retained TEST-001 as required. ShellCheck/pyflakes integrations were not installed or claimed. This static result does not validate the unimplemented profile/advisory adapter or hosted execution.
