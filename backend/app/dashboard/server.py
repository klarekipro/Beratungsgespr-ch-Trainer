"""Local dashboard API. Launch one process, bound to loopback, via serve_dashboard.py."""
import asyncio
import copy
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .engine import build_report, process_turn
from . import customer_actor, response_planning
from .exports import export_pdf, export_text
from .models import Company, MessageInput, ReviewInput, Scenario, SessionStart
from .providers import DemoProvider, OpenAIProvider, ProviderError
from .seeds import PREVIOUS_BUILTIN_SHA256, SEED_COMPANY, SEED_SCENARIOS
from .store import SQLiteStore, VersionConflict

ROOT = Path(__file__).resolve().parents[3]
VERSION = "0.3.0-semantic-planning"


def now():
    return datetime.now(timezone.utc).isoformat()


def fail(code, message, status=400):
    raise HTTPException(status_code=status, detail={"code": code, "message": message})


def mentor(x_workspace_role: str = Header(default="")):
    if x_workspace_role != "mentor":
        fail("MENTOR_WORKSPACE_REQUIRED", "Откройте рабочее место наставника.", 403)


def summary(session):
    scenario = session["scenario_snapshot"]
    return {
        "id": session["id"], "scenario_id": session["scenario_id"],
        "title": scenario["title"], "customer_name": scenario["customer_name"],
        "mode": session["mode"], "created_at": session["created_at"],
        "updated_at": session["updated_at"], "status": session["status"],
        "review_status": session["review_status"], "phase": session["state"]["phase"],
        "turn_count": sum(m["role"] == "learner" for m in session["messages"]),
    }


def learner_view(session):
    result = summary(session)
    result.update({"version": session["version"], "messages": session["messages"],
                   "company": session["company_snapshot"], "review_note": session.get("review_note", ""),
                   "api_requests": session.get("live_requests"),
                   "api_count_complete": session.get("api_count_complete", False),
                   "natural_customer_turns": sum(m.get("source") == "openai_actor_verified" for m in session["messages"])})
    if session["status"] == "finished":
        result["report"] = session.get("report") or build_report(session)
    return result


def create_app(data_path: Path | None = None, provider_factory=None):
    app = FastAPI(title="Klare KI · Consultation Studio", version=VERSION, docs_url=None, redoc_url=None)
    # Capture at import/startup, not on each request: a later checkout must not
    # make an old process claim it loaded the new revision.
    try:
        revision = subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True,
            stderr=subprocess.DEVNULL, timeout=2,
        ).strip()
    except (OSError, subprocess.SubprocessError):
        revision = None
    runtime = {"pid": os.getpid(), "python": sys.executable,
               "server_module": str(Path(__file__).resolve()), "git_commit": revision,
               "customer_actor_module": str(Path(customer_actor.__file__).resolve()),
               "customer_actor_sha256": hashlib.sha256(Path(customer_actor.__file__).read_bytes()).hexdigest(),
               "customer_context": "isolated_from_company_policy",
               "response_planning": "typed_targets_v1",
               "response_planning_module": str(Path(response_planning.__file__).resolve()),
               "response_planning_sha256": hashlib.sha256(Path(response_planning.__file__).read_bytes()).hexdigest()}
    db_path = data_path or Path(os.environ.get("TRAINER_DATA_DIR", str(ROOT / "runtime" / "dashboard"))) / "trainer.sqlite3"
    store = SQLiteStore(Path(db_path))
    runtime["data_path"] = str(Path(db_path).resolve())
    audit_dir = Path(os.environ["TRAINER_AUDIT_DIR"]).resolve() if os.environ.get("TRAINER_AUDIT_DIR") else None
    if audit_dir:
        audit_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    runtime["audit_enabled"] = bool(audit_dir)
    # Reject malformed seed cards as loudly as malformed author input.
    seed_company = Company.model_validate(SEED_COMPANY).model_dump()
    seed_scenarios = [Scenario.model_validate(s).model_dump() for s in SEED_SCENARIOS]
    store.seed(seed_company, seed_scenarios)
    store.upgrade_builtin_scenarios(PREVIOUS_BUILTIN_SHA256, seed_scenarios)
    app.state.store = store
    app.state.locks = {}
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    model = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini-2025-04-14").strip()
    live_configured = bool(api_key and model)
    max_turns = min(60, max(5, int(os.environ.get("TRAINER_MAX_TURNS", "30"))))
    max_live_attempts = min(100, max(1, int(os.environ.get("TRAINER_MAX_LIVE_ATTEMPTS", "30"))))

    def provider(mode):
        if provider_factory:
            return provider_factory(mode)
        return OpenAIProvider(api_key=api_key, model=model) if mode == "openai" else DemoProvider()

    allowed_hosts = ["localhost", "127.0.0.1", "[::1]", "testserver"]
    allowed_hosts += [v.strip() for v in os.environ.get("TRAINER_ALLOWED_HOSTS", "").split(",") if v.strip() and v.strip() != "*"]
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

    @app.middleware("http")
    async def local_boundary(request: Request, call_next):
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            origin = request.headers.get("origin")
            if origin:
                parsed = urlsplit(origin)
                if parsed.scheme != request.url.scheme or parsed.netloc != request.url.netloc or parsed.path not in ("", "/"):
                    return JSONResponse({"error": {"code": "FOREIGN_ORIGIN", "message": "Запрос должен исходить из этого приложения."}}, status_code=403)
            try:
                size = int(request.headers.get("content-length", "0"))
            except ValueError:
                size = 262145
            if size > 262144:
                return JSONResponse({"error": {"code": "BODY_TOO_LARGE", "message": "Слишком большой запрос."}}, status_code=413)
            # Also bound chunked requests, not only their optional Content-Length.
            body = await request.body()
            if len(body) > 262144:
                return JSONResponse({"error": {"code": "BODY_TOO_LARGE", "message": "Слишком большой запрос."}}, status_code=413)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(HTTPException)
    async def http_error(request, error):
        detail = error.detail if isinstance(error.detail, dict) else {"code": "REQUEST_FAILED", "message": str(error.detail)}
        return JSONResponse({"error": detail}, status_code=error.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        fields = ", ".join(".".join(str(x) for x in e["loc"][1:]) for e in error.errors()[:4])
        return JSONResponse({"error": {"code": "INVALID_INPUT", "message": "Проверьте обязательные поля и допустимые значения: " + fields}}, status_code=422)

    @app.exception_handler(VersionConflict)
    async def conflict_error(request, error):
        return JSONResponse({"error": {"code": "VERSION_CONFLICT", "message": "Беседа обновилась. Загрузите её заново."}}, status_code=409)

    @app.exception_handler(sqlite3.Error)
    async def storage_error(request, error):
        return JSONResponse({"error": {"code": "STORAGE_UNAVAILABLE", "message": "Не удалось сохранить данные. Повторите действие."}}, status_code=503)

    def get_session(sid):
        session = store.get_session(sid)
        if not session:
            fail("SESSION_NOT_FOUND", "Беседа не найдена.", 404)
        return session

    def lock(sid):
        return app.state.locks.setdefault(sid, asyncio.Lock())

    def valid_outcomes(scenario, company):
        if scenario["company_id"] != company["id"]:
            fail("COMPANY_MISMATCH", "Сценарий должен относиться к текущей компании.", 422)
        available = {s["id"] for s in company["services"]} | {"no_fit"}
        if not set(scenario["allowed_outcomes"]).issubset(available):
            fail("INVALID_OUTCOME", "В сценарии указана услуга, которой нет в карточке компании.", 422)

    @app.get("/api/status")
    async def status():
        return {"version": VERSION, "storage": "sqlite", "access_mode": "local_workspaces", "runtime": runtime,
                "ai": {"configured": live_configured, "live_enabled": live_configured, "model": model,
                       "customer_mode": "generated_and_checked", "max_requests_per_turn": 5},
                "limits": {"max_turns": max_turns, "max_live_attempts": max_live_attempts}, "roles": ["mentor", "learner"]}

    @app.get("/api/company")
    async def company():
        return {"company": store.get_company()}

    @app.put("/api/mentor/company", dependencies=[Depends(mentor)])
    async def save_company(value: Company):
        previous = store.get_company()
        if value.id != previous["id"]:
            fail("COMPANY_ID_IMMUTABLE", "ID компании менять нельзя.", 422)
        if value.revision != previous["revision"]:
            fail("VERSION_CONFLICT", "Карточка компании уже изменилась. Обновите её.", 409)
        record = value.model_dump()
        for scenario in store.list_scenarios():
            valid_outcomes(scenario, record)
        record["revision"] = previous["revision"] + 1
        store.save_company(record)
        return {"company": record}

    @app.get("/api/scenarios")
    async def scenarios():
        comp = store.get_company()
        return {"scenarios": [{**{k: s[k] for k in ("id", "title", "customer_name", "public_brief", "language")}, "company_name": comp["name"]} for s in store.list_scenarios()]}

    @app.get("/api/mentor/scenarios", dependencies=[Depends(mentor)])
    async def mentor_scenarios():
        return {"scenarios": store.list_scenarios()}

    @app.post("/api/mentor/scenarios", dependencies=[Depends(mentor)])
    async def save_scenario(value: Scenario):
        record = value.model_dump()
        valid_outcomes(record, store.get_company())
        previous = store.get_scenario(record["id"]) if record["id"] else None
        if previous and previous["revision"] != record["revision"]:
            fail("VERSION_CONFLICT", "Сценарий уже изменился. Обновите его.", 409)
        record["id"] = record["id"] or "case_" + uuid4().hex[:12]
        record["revision"] = previous["revision"] + 1 if previous else 1
        store.save_scenario(record)
        return {"scenario": record}

    @app.delete("/api/mentor/scenarios/{sid}", dependencies=[Depends(mentor)])
    async def delete_scenario(sid: str):
        if not store.delete_scenario(sid):
            fail("SCENARIO_NOT_FOUND", "Сценарий не найден.", 404)
        return {"deleted": True}

    @app.get("/api/sessions")
    async def sessions():
        return {"sessions": [summary(s) for s in store.list_sessions()]}

    @app.post("/api/sessions")
    async def start(value: SessionStart):
        if value.mode == "openai" and not live_configured:
            fail("AI_NOT_CONFIGURED", "OpenAI ещё не подключён. Запустите сервер с API-ключом или выберите сценарный режим.", 409)
        scenario = store.get_scenario(value.scenario_id)
        if not scenario:
            fail("SCENARIO_NOT_FOUND", "Сценарий не найден.", 404)
        comp = store.get_company()
        if not comp["reviewed"]:
            fail("COMPANY_NOT_REVIEWED", "Наставнику нужно проверить и подтвердить карточку компании.", 409)
        valid_outcomes(scenario, comp)
        ts = now()
        session = {"id": uuid4().hex, "scenario_id": scenario["id"], "scenario_snapshot": copy.deepcopy(scenario),
                   "company_snapshot": copy.deepcopy(comp), "mode": value.mode, "created_at": ts, "updated_at": ts,
                   "status": "active", "review_status": "not_submitted", "review_note": "", "reviewed_at": None,
                   "version": 1, "state": {"phase": "needs", "discovered": [], "needs_confirmed": False,
                   "capabilities_confirmed": False, "events": [], "outcome": None},
                   "messages": [{"role": "customer", "text": scenario["opening"], "at": ts, "turn": 0}],
                   "receipts": {}, "live_attempts": 0, "live_requests": 0, "api_count_complete": True, "system_issues": []}
        store.save_session(session)
        return {"session": learner_view(session)}

    @app.get("/api/sessions/{sid}")
    async def session_view(sid: str):
        return {"session": learner_view(get_session(sid))}

    @app.post("/api/sessions/{sid}/messages")
    async def message(sid: str, value: MessageInput):
        async with lock(sid):
            session = get_session(sid)
            fingerprint = hashlib.sha256(json.dumps({"text": value.text, "kind": value.kind}, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
            receipt = session.get("receipts", {}).get(value.request_id)
            if receipt:
                if receipt["fingerprint"] != fingerprint:
                    fail("IDEMPOTENCY_CONFLICT", "Этот идентификатор уже использован для другой реплики.", 409)
                return {"session": learner_view(session)}
            if session["status"] != "active" or session["state"]["phase"] == "completed":
                fail("SESSION_CLOSED", "Диалог завершён. Откройте разбор или начните новую попытку.", 409)
            if session["version"] != value.version:
                fail("VERSION_CONFLICT", "Беседа обновилась. Загрузите её заново.", 409)
            turn = summary(session)["turn_count"] + 1
            if turn > max_turns:
                fail("TURN_LIMIT", "Достигнут лимит беседы. Завершите её и откройте разбор.", 409)
            if session["mode"] == "openai":
                if not live_configured:
                    fail("AI_NOT_CONFIGURED", "Подключение OpenAI отсутствует. Текущая беседа не переключается в сценарный режим.", 409)
                if session.get("live_attempts", 0) >= max_live_attempts:
                    fail("AI_ATTEMPT_LIMIT", "Достигнут предел AI-попыток этой беседы. Завершите её и сохраните разбор.", 429)
                session["live_attempts"] = session.get("live_attempts", 0) + 1
                store.save_session(session, expected_version=session["version"])
            current_provider = None
            requests_before = 0
            error_code = None
            try:
                current_provider = provider(session["mode"])
                requests_before = getattr(current_provider, "request_count", 0)
                if type(requests_before) is not int:
                    requests_before = 0
                updated = await process_turn(session, value.text, value.kind, current_provider, turn)
            except ProviderError as exc:
                # Fixed safe message; no provider payload / user content / secrets.
                code = getattr(exc, "code", "AI_UNAVAILABLE")
                error_code = code
                if code != "scenario_missing_context":
                    infrastructure = {"ai_timeout", "ai_unavailable", "ai_rate_limited", "ai_access_denied", "ai_request_rejected", "ai_not_configured"}
                    category = ("infrastructure_error" if code in infrastructure else
                                "actor_response_error" if code.startswith("ai_actor_") else "director_response_error")
                    session.setdefault("system_issues", []).append({"type":category, "turn":turn,
                        "detail":"Ответ системы не получен или не прошёл проверку. Это не ошибка ученика; ход не засчитан."})
                    session["system_issues"] = session["system_issues"][-30:]
                if code == "scenario_missing_context":
                    issue = {"type": "scenario_missing_context", "turn": turn,
                             "detail": "В карточке не хватило сведений для ответа. Ход не засчитан; это ограничение сценария, не ошибка ученика."}
                    session.setdefault("system_issues", []).append(issue)
                    session["system_issues"] = session["system_issues"][-30:]
                    fail(code, "В карточке нет данных для ответа на этот вопрос. Это ограничение сценария, а не ошибка ученика. Наставнику нужно дополнить карточку.", 422)
                fail(code, "Не удалось получить проверенный ответ. Реплика не засчитана. Можно повторить отправку; сценарный режим не подставлялся.", 502)
            except (ValueError, TypeError, KeyError, RuntimeError):
                error_code = "INVALID_AI_RESPONSE"
                fail("INVALID_AI_RESPONSE", "Ответ системы не прошёл проверку. Ход не засчитан; повторите отправку.", 502)
            finally:
                if session["mode"] == "openai":
                    count = getattr(current_provider, "request_count", 0)
                    if type(count) is int:
                        count -= requests_before
                    if type(count) is not int or not 0 <= count <= 5:
                        count = 0
                    if audit_dir:
                        audit = {"session_id":sid, "request_id":value.request_id, "turn":turn,
                                 "input":value.text, "api_requests":count, "error_code":error_code,
                                 "trace":getattr(current_provider,"trace",[])}
                        path = audit_dir / f"{sid}-{value.request_id}-{uuid4().hex}.json"
                        with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as output:
                            json.dump(audit, output, ensure_ascii=False, indent=2)
                    session.setdefault("api_count_complete", False)
                    session["live_requests"] = session.get("live_requests", 0) + count
                    store.save_session(session, expected_version=session["version"])
            updated["live_requests"] = session.get("live_requests", 0)
            updated["api_count_complete"] = session.get("api_count_complete", False)
            updated["system_issues"] = copy.deepcopy(session.get("system_issues", []))
            updated["version"] = session["version"] + 1
            updated["updated_at"] = now()
            updated.setdefault("receipts", {})[value.request_id] = {"fingerprint": fingerprint, "version": updated["version"]}
            store.save_session(updated, expected_version=session["version"])
            return {"session": learner_view(updated)}

    @app.post("/api/sessions/{sid}/finish")
    async def finish(sid: str):
        async with lock(sid):
            session = get_session(sid)
            if session["status"] != "finished":
                previous = session["version"]
                session["status"] = "finished"
                session["updated_at"] = now()
                session["version"] += 1
                session["report"] = build_report(session)
                store.save_session(session, expected_version=previous)
            return {"session": learner_view(session)}

    @app.post("/api/sessions/{sid}/submit")
    async def submit(sid: str):
        async with lock(sid):
            session = get_session(sid)
            if session["status"] != "finished":
                fail("FINISH_REQUIRED", "Сначала завершите беседу.", 409)
            if session["review_status"] == "not_submitted":
                previous = session["version"]
                session["review_status"] = "submitted"
                session["submitted_at"] = now()
                session["updated_at"] = now()
                session["version"] += 1
                store.save_session(session, expected_version=previous)
            return {"session": learner_view(session)}

    def exportable(sid):
        session = get_session(sid)
        if session["status"] != "finished":
            fail("FINISH_REQUIRED", "Полная расшифровка с разбором доступна после завершения.", 409)
        return session

    def download(data, kind, sid, content_type):
        return Response(data, media_type=content_type, headers={"Content-Disposition": f'attachment; filename="consultation-{sid[:12]}.{kind}"'})

    @app.get("/api/sessions/{sid}/export.txt")
    async def text_export(sid: str):
        return download(export_text(exportable(sid)), "txt", sid, "text/plain; charset=utf-8")

    @app.get("/api/sessions/{sid}/export.json")
    async def json_export(sid: str):
        session = exportable(sid)
        clean = {k: v for k, v in session.items() if k not in {"receipts"}}
        return download(json.dumps(clean, ensure_ascii=False, indent=2), "json", sid, "application/json; charset=utf-8")

    @app.get("/api/sessions/{sid}/export.pdf")
    async def pdf_export(sid: str):
        session = exportable(sid)
        try:
            pdf = await asyncio.to_thread(export_pdf, session)
        except (RuntimeError, ImportError):
            fail("PDF_UNAVAILABLE", "Для PDF нужен шрифт с кириллицей. Сохраните TXT или установите шрифты по инструкции запуска.", 503)
        return download(pdf, "pdf", sid, "application/pdf")

    @app.get("/api/mentor/reviews", dependencies=[Depends(mentor)])
    async def reviews():
        return {"sessions": [{**summary(s), "report": s.get("report"), "review_note": s.get("review_note", "")} for s in store.list_sessions() if s["review_status"] in {"submitted", "reviewed"}]}

    def submitted(sid):
        session = get_session(sid)
        if session["status"] != "finished" or session["review_status"] not in {"submitted", "reviewed"}:
            fail("REVIEW_NOT_SUBMITTED", "Эта беседа ещё не передана наставнику.", 404)
        return session

    @app.get("/api/mentor/reviews/{sid}", dependencies=[Depends(mentor)])
    async def review_view(sid: str):
        return {"session": learner_view(submitted(sid))}

    @app.post("/api/mentor/reviews/{sid}", dependencies=[Depends(mentor)])
    async def review(sid: str, value: ReviewInput):
        async with lock(sid):
            session = submitted(sid)
            previous = session["version"]
            session.update(review_note=value.note, reviewed_at=now(), review_status="reviewed", updated_at=now(), version=previous + 1)
            store.save_session(session, expected_version=previous)
            return {"session": learner_view(session)}

    frontend = ROOT / "frontend"

    @app.get("/")
    async def index():
        return FileResponse(frontend / "index.html", headers={"Cache-Control": "no-cache"})

    app.mount("/static", StaticFiles(directory=frontend), name="static")
    return app


app = create_app()
