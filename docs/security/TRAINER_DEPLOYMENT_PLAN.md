## MISSION 06.1 — актуальное дополнение, 24.11.2026

Подготовлены действительные Docker/CI adapters и исправленный privacy contract в той же working branch. [Pilot runbook](TRAINER_PILOT_RUNBOOK.md), [Access plan](TRAINER_ACCESS_PLAN.md), [Python Security CI](TRAINER_SECURITY_CI.md), [read-only VPS admission](TRAINER_VPS_PREFLIGHT.md) определяют текущие условия. Ни публикации, ни перенос данных/секретов, ни изменение working infrastructure не выполнялись. Native advisories и непроверенные activation gates не выданы за PASS. Ниже сохранена историческая MISSION06 оценка.

---

# Trainer Deployment Plan — minimal approved next steps

## Минимальный порядок реализации

1. Исправить устаревшее ожидание privacy-теста: finish остаётся приватным, submit открывает беседу наставнику.
2. Зафиксировать native Linux Python dependency lock/SBOM, ffprobe/Poppler и Unicode-шрифты; сохранить Actor и бизнес-логику.
3. Зафиксировать утверждённый SHA существующего проекта и отдельную synthetic pilot SQLite. Private shared repo — независимая опция для совместной разработки после разрешения, не обязательное условие доступа к самому пилоту.
4. Добавить отдельный native launcher: один процесс, постоянный private volume, точный source SHA и серверный secret manager вместо переноса macOS Keychain.
5. После отдельного разрешения настроить один hostname, Access с проверкой JWT на origin, закрытый origin, Secure cookies, точный allowed host и доверенный HTTPS proxy.
6. Подтвердить нужные tests, квоты/model availability, backup/restore на staging; затем получить отдельное разрешение на pilot deploy.

Владелец подтвердил уже оплаченный VPS/сервер. Используем его как основной target без создания нового сервера; до реализации проверяем ОС/архитектуру, ресурсы, изоляцию и backup без передачи секретов. Linux/Python profile ниже предварительный до сверки с фактическим хостом.

В этой миссии выполнены аудит, документация и локальная проверка примеров. **Merge, deployment, новые ресурсы, перенос данных/секретов не выполнялись.** Пилот ещё не активирован. Конкретные изменения и критерии приёмки приведены ниже.

23.11.2026, Europe/Berlin. MISSION 06. Source: `klarekipro/Beratungsgespr-ch-Trainer`, audited main `332a4f4d7f919fc570d9e8d44de2d9be326e7677`. Working branch: `codex/mission-06-cloudflare-readiness`. Planning/audit only; no push, merge, deployment, data transfer, new remote repository, cloud resource or secret transmission.

Selected proposal: **B**, one native FastAPI process on the **owner-confirmed already-paid VPS/server**, serving current frontend/API behind one Cloudflare-protected hostname. No remote host inspection/login was performed; verify OS/architecture/capacity before treating the provisional Linux profile as applicable. No Kubernetes, second API service, D1 migration, new database server, new GitHub repo or separate Pages/CORS setup is needed just to run the first small pilot. App users need named Access/app accounts, not GitHub development seats.

## Ordered implementation plan

| Step | Concrete change / acceptance | Current state |
|---|---|---|
| 1: stabilize the test contract | Update tests/functional/test_portals.py:148 to assert private-before-submit and mentor-visible-after-submit. Preserve existing auth/CSRF/ownership behavior. Run the failed test and explicit submission/privacy cases, no paid AI | Existing test **FAIL**, diagnosis confirmed; no app/test source fix applied in this planning mission |
| 2: reproducible native environment | Verify the existing VPS OS/architecture, spare capacity, persistent disk and isolation, then produce the matching reviewed Python 3.14 transitive/hash lock and SBOM (provisional target: Linux), retain six direct pins until compatibility/advisories justify changes; install only reviewed binary wheels in an isolated build. Package ffprobe, Poppler and licensed DejaVu fonts. Do not move the Mac venv | **BLOCKED** pending approved runtime/build preparation |
| 3: source/ownership | Owner approves the pilot source SHA and permitted teaching content from the existing project. A new private development repo is a separate optional workstream under SHARED_REPOSITORY_PLAN.md, not required just to use the app | Source/deployment approval pending; no new repo/mirror/transfer |
| 4: pilot launcher | Add a separate native/pilot launcher or service unit; do not alter the macOS Keychain launcher. One Uvicorn worker, explicit immutable build SHA, dedicated unprivileged user, private persistent data directory and separate temp/log paths | Proposed only |
| 5: edge configuration | Owner approves one hostname, named-user Access rules and Tunnel. Validate application tokens at cloudflared or a reviewed origin verifier; origin reachable only through the intended proxy. Keep existing app accounts and CSRF | **NOT VERIFIED**; no cloud resources/policies created |
| 6: HTTPS/proxy acceptance | TRAINER_REMOTE_HTTPS=1; exact TRAINER_ALLOWED_HOSTS; trusted forwarded scheme/client source restricted to the actual proxy IP. Same hostname for frontend and /api; no-store for authenticated/API/export routes, no edge-cache override | Native HTTPS unit case PASS; actual Cloudflare path **NOT VERIFIED** |
| 7: secrets and AI budget | Owner injects a separate project-scoped server secret outside Git/browser/CI reports. Agree request/token/dictation/concurrency caps and actual quota/spend alert/stop behavior. Confirm pinned Deprecated model availability or separately approve a tested model transition | **NOT VERIFIED**; no key read/moved and no paid probe |
| 8: fresh synthetic staging | Empty isolated SQLite, named synthetic users, published teaching fixtures only. Run login/reset/deactivate/CSRF/logout/expiry, cross-user exports, finish→submit privacy, PDF Unicode, upload limits and mocked AI contract | Narrow local checks recorded; full pilot acceptance **NOT VERIFIED** |
| 9: backup/rollback acceptance | SQLite backup API snapshot, encrypted off-host copy and restore to a separate staging path; verify counts/integrity and access controls. Save source/config/dependency hashes without secrets | Restore **NOT VERIFIED**, no working data copied |
| 10: owner pilot release | Review exact tested SHA and all mandatory results, approve time window/users/budget, then separately deploy and observe. No auto production deploy on security PR/main merge | **BLOCKED** until prior gates and explicit deployment approval |

## Pilot environment contract (not an installed configuration)

Use a dedicated persistent path such as `/srv/beratungstrainer-pilot/data`, never the current Mac runtime/dashboard. Example non-secret settings: TRAINER_DATA_DIR, TRAINER_REMOTE_HTTPS=1, exact TRAINER_ALLOWED_HOSTS, capped TRAINER_MAX_TURNS/MAX_LIVE_ATTEMPTS and explicit font paths. The values must be chosen for the approved pilot; no actual hostname or token is generated here.

The existing `scripts/serve_dashboard.py` binds 127.0.0.1 and starts one worker. Keep that isolation for a same-host Tunnel. Remote scheme handling must be explicitly validated: a tunnel's HTTP origin must still give the application the true external HTTPS scheme through a trusted proxy, or its strict HTTPS/Origin checks will reject valid requests. Do not fix this by removing HTTPS or CSRF.

Use cloudflared Protect with Access / verified JWT validation. Reject missing/invalid tokens and alternate-origin routes; an email header is insufficient. No Access bypass rule for public status/static/export paths. Keep media dictation within existing byte/duration/concurrency bounds and verify forward/proxy timeouts against the current 45-second AI timeout.

Existing process-local locks/rate counters imply one process for pilot. Before scaling, measure write contention, API latency and spend with synthetic traffic in a separately authorized test. Do not horizontally replicate the SQLite file or use KV for authoritative auth/session transactions.

## Data, backup and rollback

Start with fresh synthetic pilot records, not the owner's existing conversations/users. Preserve frozen snapshots and separate employee finish, explicit submit, mentor review and certificate issuance. No automatic certificate issuance or historical data rewriting.

Back up SQLite through its backup API; copying only the main DB while WAL is active is not sufficient. Proposed RPO/RTO are targets in feasibility, not proof. Keep encrypted copies and encryption material separate; restore-test outside the live path. Code rollback uses a previously verified compatible release; restoring an old database over new conversations requires a separate owner decision and a fresh safety copy.

Historical DATA-001 missing legacy artifacts stay open in the original project's register. Their recovery is a different task and is not silently made a prerequisite for a new synthetic-data-only pilot.

## Release gate and CI

CODE CHANGE → SELECTIVE SECURITY CHECKS → OFFLINE TESTS → OWNER APPROVAL → BACKUP → EXPLICIT DEPLOY → POST-DEPLOY CHECK.

PASS requires complete executed or matching-valid-reused mandatory results. FAIL blocks; BLOCKED and NOT VERIFIED never become green via skipping. A future main-context security run must identify the actual tested SHA; no such run or deployment is claimed now.

Do not install a workflow which publishes on every main push. Deployment remains an explicit owner operation, separate from the read-only security workflow. The proposed CI templates are inactive reference files and require a tested Trainer/profile adapter before activation; no fake runner or success stub is supplied.

## Least-cost sequence

Fix the stale test and lock the native environment first; only then approve host/Access/shared-repo steps. Reuse the already-paid VPS confirmed by the owner. Verify its capacity and compatibility first; no additional VM is planned. Only if it is unsuitable should a separate owner-approved alternative/cost estimate be prepared. Use the eligible free Access tier, no optional D1/R2 service for B, and a small separately capped AI budget. Do not create cloud resources just to prove syntax.

## Required decisions

Owner has confirmed the paid host; OS/capacity/uptime and any incremental services still need verification. Owner approves source transfer/target rights, named users/retention, pilot hostname/Access, AI model availability/budget and a backup/restore window. Until those gates are evidenced, the result is a prepared plan with **BLOCKED pilot activation**, not a finished cloud deployment.

References: [FastAPI proxy trust](https://fastapi.tiangolo.com/advanced/behind-a-proxy/), [Cloudflare origin token validation](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/self-hosted-public-app/), [feasibility/costs](TRAINER_CLOUDFLARE_FEASIBILITY.md), [security audit](TRAINER_SECURITY_AUDIT.md), [shared repo plan](SHARED_REPOSITORY_PLAN.md).
