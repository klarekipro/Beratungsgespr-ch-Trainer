# Shared Repository Plan — owner decision required

## Решение и границы

Создание отдельного приватного совместного репозитория и перенос кода **BLOCKED до отдельного подтверждения владельца**. Оригинал остаётся без изменений, с существующими ветками, историей и Releases. Зеркало, новый repository, invites и перенос ключей не выполнялись.

Нужно согласовать owner/name, участников и возможные дополнительные Team seats, исходный SHA, лицензию и разрешённые материалы. Полная история переносится только после проверки всех выбранных достижимых commits; --mirror/--all не применяются. Если история содержит исключаемые материалы, владелец отдельно выбирает очищенную производную историю или snapshot с честным provenance. История оригинала сохраняется в любом случае; Releases и медиа требуют отдельного отбора.

Из общей поставки исключаются рабочие SQLite/сессии, беседы, приватные экспорты, audit/runtime/backups, credentials/demo accounts, секреты, дубли checkout и непроверенные архивы/персональные материалы. Синтетические тестовые аккаунты создаются только во временных БД; действующие общие пароли не поставляются.

23.11.2026, Europe/Berlin. MISSION 06. Source: `klarekipro/Beratungsgespr-ch-Trainer`, audited main `332a4f4d7f919fc570d9e8d44de2d9be326e7677`. Working branch: `codex/mission-06-cloudflare-readiness`. Planning/audit only; no push, merge, deployment, data transfer, new remote repository, cloud resource or secret transmission.

Status: **BLOCKED for repository creation/code transfer until separate owner confirmation.** This document is a plan, not authorization to mirror, fork, change visibility or invite collaborators. Original public Trainer, all existing branches/tags and GitHub Releases remain unchanged.

## Verified starting point

Original: klarekipro/Beratungsgespr-ch-Trainer, public, default main 332a4f4d7f91, application version 0.15.3. Three releases v0.15.3/v0.16.0/v0.17.0 have 19 attached assets in total; media release version is not an app runtime version. Release binaries/media were not downloaded or privacy/licence-cleared in this mission.

Current source tree has 561 tracked files, no tracked runtime paths or SQLite/database files, and only .env.example among dotenv files. One tracked archive still needs a separate content/privacy review before redistribution. Gitleaks PASS across published history is not PII/copyright clearance. No first-party LICENSE file was found.

The confirmed organization is klareki-lab, active admin membership and Team plan. Existing paid seats do not prove an additional colleague is free: verify actual member/outside-collaborator billing before inviting anyone. Personal-repo collaboration is another ownership option, but plan/enforcement/billing must be checked separately rather than assumed.

## Approval packet before any external creation

Owner chooses exact private owner/name, maintainers/collaborators, source commit, history strategy, internal licensing terms and approved data/media list. Record written approval covering code transfer and any incremental seat/resource costs. Do not use shared passwords or forward an existing OpenAI key.

Suggested name only: `beratungstrainer-pilot` under the confirmed owner. Availability is not checked and no repository was created. Explicitly require private visibility at creation; do not change the original repository's visibility.

## Preserve provenance without a mirror

1. Preserve the original repository as the authoritative archive, including original authors, commits, tags, releases and asset references. No force-push, deletion or rewriting there.
2. Preferred history-preserving option after approval: select an explicitly reviewed source branch and its reachable history, with an allowlist of refs. Audit that history for secrets, personal data, local snapshots and third-party rights **before** transfer. Push only owner-approved refs to the new private repository; never use --mirror/--all or automatically transfer hidden branches.
3. If historical commits contain excluded material, stop that option. Owner may instead approve a separately sanitized derived history or a clean source snapshot with a provenance manifest. Keep authorship and notices; record original-to-derived commit mapping when history is filtered, or clearly disclose that a snapshot does not reproduce Git history. Never claim complete history preservation for a squashed snapshot.
4. GitHub Releases are not recreated just by pushing Git tags. Inventory metadata/assets, choose which release assets are licensed/sanitized, and migrate only those explicitly approved. Keep original release URLs as provenance when assets are intentionally not copied. No automatic mass attachment download/upload.

## Allowlist / exclusions

Candidate allowlist: reviewed backend/frontend/scripts needed for pilot, approved synthetic scenarios/profiles/materials, dependency pins/lock, synthetic tests, security config and operating docs. Retain notices and original Git authorship; author metadata is a provenance requirement to review explicitly, not customer data to scrub indiscriminately.

Exclude working SQLite/WAL/SHM, conversations, private feedback/certificates/exports, auth session/user stores, real or default/demo account credentials, API keys, cookies, Keychain helpers' private support files, runtime/audit/logs/backups, .venv/node_modules, installation tokens, local receipts, duplicate workspaces, raw screenshots/archives/media not approved for transfer, and documents containing personal information. Reusable fictitious teaching content needs owner/licence review too; a README saying demo does not grant copying rights.

Synthetic tests may generate isolated accounts at runtime. They must never ship working demo accounts, shared static passwords or copied password hashes in the deployed pilot. Bootstrap actual named accounts through a separate owner process after deployment approval.

## Acceptance of the later transfer

Before first push: selected-file diff, current-tree and full selected-history secret scans, ownership/license review, PII/media review, signed-off ref/asset manifest and archive inspection. After creation/transfer: verify private visibility, exact refs/source hashes, access list, no accidental Actions/deployment trigger, and a fresh synthetic test run. Mark missing/uncleared items NOT VERIFIED or BLOCKED; do not create a broad scanner exclusion to make transfer green.

Use the already-paid Team capabilities where applicable for required checks/reviews, verify actual entitlement and configure only with owner authorization. No paid private CodeQL/GitHub security add-on is assumed. Keep CI tokens read-only and production secrets out of PR jobs.

## Ownership decisions still open

Private owner/name; colleague identities/roles and seat budget; preservation of full reviewed history versus sanitized derivation; first-party internal license and third-party/media rights; permitted teaching data and retention; model/account budget. These decisions do not require or authorize changing the existing public repository.
