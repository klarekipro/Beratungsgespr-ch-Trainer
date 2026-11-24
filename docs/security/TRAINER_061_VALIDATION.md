# MISSION 06.1 — validation, 24.11.2026

## Confirmed local results

- PASS: finish keeps the conversation private; only explicit submit grants assigned mentor access. Other learners retain404. Production finish/submit logic unchanged.
- PASS: owner-required published mentor commercial outcome and company-fit labels in TXT/PDF, DE/EN/RU; source records unchanged. Mac bounded suite20 PASS; paid calls0, network attempts0, temporary synthetic SQLite only.
- PASS: Semgrep CE9 local JS/Python rules,68/68 first-party source units,0 findings; positive and negative scanner fixtures PASS. Limited CE patterns do not constitute complete interfile application assurance.
- PASS: actionlint1.7.12 and offline zizmor1.33.1,0 findings. Gitleaks final publication snapshot50 files,0 findings; full published-history validation is separately reported by hosted CI.
- PASS: Compose configuration and actual pinned cloudflared ingress validation using synthetic .invalid host/audience. No Tunnel was created or connected.
- PASS: separate online WAL backup/restore with Unicode and BLOB values, corruption/no-overwrite checks; live database untouched. Off-host encrypted restore remains NOT VERIFIED.
- FAIL: candidate native dependency graph254 components; Python advisory matches0, Debian495 matches:371 UNKNOWN,120 INFO,4 LOW. Unknown severity remains blocking; no suppression or fictitious green gate. Custom SQLite3.54.1 is separately pinned and tested; Debian sqlite findings do not attest that custom library.

Linux exposed a real font-path compatibility defect: Debian installs Liberation Sans under `truetype/liberation`, not `liberation2`. Correcting only container font configuration makes the unchanged one-page Unicode/long-name certificate regression PASS. No certificate sizing or safe rejection was weakened. Final complete Linux suite at source `8c876f4e65175f0d6473bdd2e63880840f5e3161`: **20/20 PASS**, network attempts0, paid calls0, no live data. Source image is pinned to that actual SHA. Hosted results are recorded separately after execution.

Two pre-existing frontend microphone fixtures omitted the current auth/me preflight identity/CSRF contract. Updated mocks model read-only auth calls separately from the paid transcription POST; an added changed-account regression prohibits microphone capture and POST. Application voice code unchanged. Local builtin Node suite6 PASS.

## Runtime and infrastructure limits

VPS metadata was checked read-only; seven pre-existing containers remained running, Docker CPU/memory/swap controls are supported. Private resource measurements remain outside this public repository. No image build/pull/up/restart or data/secret transfer was performed on the VPS. Main, original Mac worktree/database/port8100 and Cloudflare resources remain unchanged.

Normal pilot activation is BLOCKED pending native advisory triage, dedicated capped persistent filesystem, peak resource admission, actual Access/JWT no-bypass acceptance, encrypted off-host restore, approved AI model/budget and separate owner deployment authorization. Shared repository creation/transfer is not part of this change.

## Hosted evidence

[Security run45350122011](https://github.com/klarekipro/Beratungsgespr-ch-Trainer/actions/runs/45350122011), job138294184319 completed on24.11.2026. PR source `8c876f4e65175f0d6473bdd2e63880840f5e3161`, base `332a4f4d7f919fc570d9e8d44de2d9be326e7677`; actual tested temporary PR merge SHA `eca581cee49eb742d44d17dd42ce6c68d0ead6fd`. This is a test merge ref, not a merge into main.

| Check | Actual hosted result |
|---|---|
| Gitleaks published branch/tag history | PASS,0 findings |
| Semgrep CE | PASS,0 findings |
| OSV native candidate graph | FAIL,495 matches;371 UNKNOWN remain blocking |
| actionlint/zizmor | PASS,0 findings |
| Native offline app/PDF/privacy tests + Node frontend tests | PASS |
| Scanner qualification fixtures | PASS |
| Overall Security Gate | FAIL |

Sanitized receipts were cached successfully even with the gate failing. Reports are job summaries, no uploaded source/log/credential artifacts. The one advisory schedule becomes automatic only after owner-approved main adoption; it has not been claimed as an active daily production monitor. No manual advisory run is added merely to repeat this same graph.

## Local container lifecycle

Actual source8c876f4 test image `sha256:3bf6a69508ccbe046ce5db3520b87677494a6461e650dbaa01a6adf3b909a413`,985725801 bytes (test target; not a production transfer size guarantee). In a new local synthetic container/volume: healthcheck CLI PASS; no host ports/network; SIGTERM produced `Application shutdown complete` and exit143; restart preserved Unicode synthetic row and SQLite integrity. Uvicorn0.52.1 intentionally raises the received signal after graceful shutdown;143 alone is not a SIGKILL or proof of failed cleanup. Both log and restored data were checked. Test resources alone were removed.

Production entrypoint rejected an ordinary uncapped volume even with a correct pilot marker. The local ASGI lifecycle probe explicitly invoked Uvicorn only on its synthetic volume, without adding a production bypass flag. Actual capped VPS storage remains NOT VERIFIED. Native VPS automatic Docker healthcheck timing remains NOT VERIFIED; the emulated Mac run showed tight healthcheck timeouts, so CLI readiness is not claimed as native timing qualification.
