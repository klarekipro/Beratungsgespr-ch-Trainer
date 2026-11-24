# Python Security CI — MISSION 06.1

Реальный adapter `tools/security/run.py` переиспользует checksummed tools и проверку receipts из sergjuri baseline. JS/npm-specific runtime checks удалены: Python lock/SBOM и Linux tests заменяют npm lock/test harness. Browser frontend проверяется собственными builtin Node tests и применимыми JS SAST rules; npm packages/audit не выдумываются.

## Обязательные checks

| Check | Охват |
|---|---|
| Gitleaks | Полная опубликованная Git history, включая удалённые значения; defaults + database-string rule; никаких legacy allowlists/exceptions sergjuri |
| Semgrep CE | Actual backend/frontend/management/deployment/CI source; local rules, metrics off, container network none. Research/report archives не deployed runtime; ограниченные правила не являются полным interfile proof |
| OSV | Transitive Python wheels, base pip и Debian source-package graph из actual pinned runtime-deps image; источник/hash SBOM проверяются. Separate pip-audit не дублируется |
| Workflow checks | actionlint + offline zizmor, все действующие workflow definitions; SHA-pinned Actions, read-only token; ShellCheck/pyflakes не заявлены установленными |
| Offline tests | Native Linux FastAPI auth/privacy/finish→submit, exports, PDF/Unicode DE/EN/RU, Argon2, SQLite WAL backup/restore, proxy/body/health, mocked OpenAI wire + builtin frontend tests |
| Scanner selftests | Positive/negative fixtures, cache/report status, suite-specific Debian classification; отсутствующие/ошибочные результаты не превращаются в PASS |

Direct Python pins должны совпадать с native lock; SBOM/checksums/полнота компонентов проверяются. Генерация: собрать reviewed `runtime-deps`, затем `python3 tools/security/update_sbom.py --image LOCAL_REVIEWED_IMAGE`. Инструмент не pull/push образа и не читает VPS. Native custom SQLite3.54.1 проверяется отдельно по source checksum/версии/compatibility; Debian package assessment не сертифицирует изменённую upstream library.

## События и стоимость

`security.yml`: PR opened/synchronize/reopened/ready_for_review и manual dispatch; concurrency отменяет старый run того же PR. Planner вычисляет inputs/tool/profile/engine hashes; исполняются только missing/changed/expired checks, остальные используют первоначальные receipts с исходным временем и SHA. Reuse FAIL сохраняет FAIL; skipped/BLOCKED/NOT VERIFIED не reusable PASS. Возраст до7 дней, advisory knowledge обновляется в текущий UTC день. Изменение самого engine требует новой квалификации, не фиктивного reuse.

Полных daily/weekly SAST/secrets/tests/workflow scans нет. Один `advisories.yml` ежедневно07:17 Europe/Berlin и вручную делает **только OSV**. Неизменённый код всё равно получает новые advisories. До первого deployment проверяется явно обозначенный candidate graph, а не выдуманная установленная версия.

`.security/deployed.json` сейчас `NOT DEPLOYED`, active[]. После отдельного owner-approved pilot release сохранить active runtime SBOM и checksum в `.security/deployed/` и добавить reviewed manifest entry `{sbom, sbom_sha256}`. Сохранять прежние **активные** graphs при продвижении нового candidate, не заменять deployed graph будущим непубликованным lock. Одинаковые SBOM hashes deduplicated. Никаких hostname/user/secret/data в manifest; publication этого metadata владелец утверждает отдельно. Непроверенная deployment coverage остаётся NOT VERIFIED.

Используется public исходный repo и standard ubuntu-24.04 runner; compute этого класса free. Нет self-hosted runner на VPS, larger runner, deploy job, registry push или cloud credentials. Reports выводятся в бесплатный job summary; artifacts не создаются. Cache только маленьких sanitized receipts, не binaries/images/source/данные. При переходе в private klareki-lab бюджет проверяется заново; нынешняя public-модель не является разрешением платного перерасхода. [GitHub billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions).

## Findings и release

Нормализованная HIGH/CRITICAL и UNKNOWN блокируют dependency gate; lower findings остаются видимыми. Для Debian используется только оценка **совпадающего package/suite**: unimportant → informational, low → LOW; not-yet-assigned остаётся blocking UNKNOWN. Никаких придуманных CVSS scores или blanket suppressions. Debian объясняет контекст этих отметок в [security tracker guide](https://security-team.debian.org/security_tracker.html).

Текущий candidate image после обновления base имеет495 native advisory matches:371 not-yet-assigned,120 unimportant,4 low; Python graph без advisory matches. Это не495 доказанных эксплуатируемых дефектов. Неоценённые совпадения требуют контекстной проверки upstream/fix/reachability/версии образа и остаются FAIL; наличие Access или ограничения CPU не дают автоматического исключения.

FAIL: оставить PR Draft, исследовать report/rule/package/test, исправить в reviewed branch. BLOCKED/NOT VERIFIED: восстановить доступ/tool/config/coverage, а не рисовать success. Никакого auto-fix/merge. Main branch protection/required checks не менялись; workflow mandatory gate не равен установленному GitHub merge enforcement. Deployment — отдельное решение владельца, с точным source/image, backup/restore и Access acceptance. Source/main merge ничего не публикует в этом CI.
