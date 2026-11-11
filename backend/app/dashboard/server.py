"""Local dashboard API. Launch one process, bound to loopback, via serve_dashboard.py."""
import asyncio
import copy
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import secrets
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from pydantic import Field
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .engine import build_report, process_turn
from .auth import AuthStore, attach_auth, require_mentor, CURRENT_USER, COOKIE
from .persona_service import PersonaService
from .transcription import transcribe, MAX_BYTES, probe_path
from .client_profiles import load_profiles, public_profile, ClientProfile
from .simple_actor import SimpleActorProvider, process_simple_turn
from . import customer_actor, response_planning, simple_actor
from .exports import export_pdf, export_text
from .models import Company, MessageInput, ReviewInput, Scenario, SessionStart, ScenarioPersonas
from .providers import DemoProvider, OpenAIProvider, ProviderError
from .seeds import PREVIOUS_BUILTIN_SHA256, SEED_COMPANY, SEED_SCENARIOS
from .materials import builtin_scenario, localized_scenario, localized_company, persona_label, public_materials
from .store import SQLiteStore, VersionConflict
from .workflow import Workflow, attach_workflow

ROOT = Path(__file__).resolve().parents[3]
VERSION = "0.15.0-certificate-design"


def now():
    return datetime.now(timezone.utc).isoformat()


def fail(code, message, status=400):
    raise HTTPException(status_code=status, detail={"code": code, "message": message})


mentor = require_mentor

def visible_profile(p):
    value=public_profile(p)
    if not CURRENT_USER.get() or CURRENT_USER.get()['role']!='mentor_admin':
        for key in ['persona_id','persona_name','approval']:
            value.pop(key,None)
    return value


def summary(session):
    scenario = session["scenario_snapshot"]
    return {
        "id": session["id"], "scenario_id": session["scenario_id"],
        "title": scenario["title"], "customer_name": scenario["customer_name"],
        "training_language": scenario["language"],
        "selection":session.get("selection_snapshot"), "employee_id":session.get("employee_id"), "archived":not bool(session.get("employee_id")), "mode": session["mode"], "client_profile": visible_profile(session["client_profile_snapshot"]) if session.get("client_profile_snapshot") else None, "created_at": session["created_at"],
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
                   "natural_customer_turns": sum(m.get("source") in {"openai_actor_verified", "openai_simple_actor"} for m in session["messages"])})
    if session["status"] == "finished":
        report = copy.deepcopy(build_report(session) if session["mode"] == "simple_actor" else session.get("report") or build_report(session))
        if not CURRENT_USER.get() or CURRENT_USER.get()["role"] != "mentor_admin":
            report.pop("facts",None)
            report.pop("assessment_outcomes",None)
        result["report"] = report
    return result


def create_app(data_path: Path | None = None, provider_factory=None):
    app = FastAPI(title="Klare KI · Consultation Studio", version=VERSION, docs_url=None, redoc_url=None, openapi_url=None)
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
               "response_planning_sha256": hashlib.sha256(Path(response_planning.__file__).read_bytes()).hexdigest(),
               "simple_actor_module":str(Path(simple_actor.__file__).resolve()),
               "simple_actor_sha256":hashlib.sha256(Path(simple_actor.__file__).read_bytes()).hexdigest()}
    auth_source=Path(sys.modules[AuthStore.__module__].__file__).resolve()
    runtime.update(auth_module=str(auth_source),auth_sha256=hashlib.sha256(auth_source.read_bytes()).hexdigest())
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
    workflow = Workflow(store)
    auth = AuthStore(store)
    app.state.auth = auth
    secure_cookies = os.environ.get("TRAINER_REMOTE_HTTPS") == "1"
    attach_auth(app,auth,secure=secure_cookies)
    from .employee_lifecycle import attach_employee_lifecycle
    attach_employee_lifecycle(app,auth)
    local_token_path = Path(db_path).parent.parent / "installation-token"
    local_token = local_token_path.read_text().strip() if local_token_path.is_file() else None
    app.state.store = store
    app.state.locks = {}
    persona_service = PersonaService(store,load_profiles(overrides=Path(db_path).parent.parent / "client_profiles"))
    app.state.persona_service = persona_service
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    model = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini-2025-04-14").strip()
    live_configured = bool(api_key and model)
    max_turns = min(60, max(5, int(os.environ.get("TRAINER_MAX_TURNS", "30"))))
    max_live_attempts = min(100, max(1, int(os.environ.get("TRAINER_MAX_LIVE_ATTEMPTS", "30"))))

    def provider(mode):
        if provider_factory:
            return provider_factory(mode)
        if mode == "simple_actor":
            return SimpleActorProvider(api_key=api_key, model=model,timeout=45)
        return OpenAIProvider(api_key=api_key, model=model) if mode == "openai" else DemoProvider()

    allowed_hosts = ["localhost", "127.0.0.1", "[::1]", "testserver"]
    allowed_hosts += [v.strip() for v in os.environ.get("TRAINER_ALLOWED_HOSTS", "").split(",") if v.strip() and v.strip() != "*"]
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

    ui_catalogues={lang:json.loads((ROOT/'frontend/locales'/f'{lang}.json').read_text()) for lang in ('de','en','ru')}
    def ui_error(request,code):
        u=getattr(request.state,'user',None)
        locale=u.get('locale','de') if u else request.headers.get('x-ui-locale','de')
        messages=ui_catalogues.get(locale,ui_catalogues['de'])
        return messages.get('errors.'+code,ui_catalogues['de'].get('errors.'+code,messages['errors.REQUEST_FAILED']))

    @app.middleware("http")
    async def local_boundary(request: Request, call_next):
        path=request.url.path
        user,csrf=auth.resolve(request.cookies.get(COOKIE))
        request.state.user=user;request.state.csrf=csrf
        public_api=path in {"/api/status","/api/auth/login","/api/auth/bootstrap-status"}
        unsafe=request.method in {"POST","PUT","PATCH","DELETE"}
        def deny(code,message,status):
            response=JSONResponse({"error":{"code":code,"message":ui_error(request,code)}},status_code=status)
            response.headers["Cache-Control"]="no-store"
            return response
        if secure_cookies and request.url.scheme!="https" and path!="/api/status":
            return deny("HTTPS_REQUIRED","Для удалённого доступа обязателен HTTPS.",426)
        if path.startswith("/api/") and not public_api:
            if not user:return deny("AUTH_REQUIRED","Войдите в свой кабинет.",401)
            if path.startswith("/api/mentor/") and user["role"]!="mentor_admin":
                return deny("FORBIDDEN","Доступ запрещён.",403)
            if user["must_change_password"] and path not in {"/api/auth/me","/api/auth/password","/api/auth/logout","/api/auth/preferences"}:
                return deny("PASSWORD_CHANGE_REQUIRED","Сначала измените временный пароль.",423)
            if unsafe and path.startswith("/api/sessions") and user["role"]!="employee":
                return deny("EMPLOYEE_REQUIRED","Тренировки создаются в кабинете сотрудника.",403)
            if path=="/api/transcriptions" and user["role"] not in {"employee","mentor_admin"}:
                return deny("EMPLOYEE_REQUIRED","Диктовка доступна сотруднику.",403)
        if unsafe:
            origin=request.headers.get("origin","")
            parsed=urlsplit(origin)
            if parsed.scheme!=request.url.scheme or parsed.netloc!=request.url.netloc or parsed.path not in ("","/"):
                return deny("FOREIGN_ORIGIN","Запрос должен исходить из этого приложения.",403)
            if path!="/api/auth/login" and path.startswith("/api/"):
                if not csrf or not secrets.compare_digest(request.headers.get("x-csrf-token",""),csrf):
                    return deny("CSRF_FAILED","Обновите страницу и повторите действие.",403)
            limit=MAX_BYTES if path=="/api/transcriptions" else 262144
            try:size=int(request.headers.get("content-length","0"))
            except ValueError:size=limit+1
            if size>limit:return deny("BODY_TOO_LARGE","Слишком большой запрос.",413)
            body=bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body)>limit:return deny("BODY_TOO_LARGE","Слишком большой запрос.",413)
            request._body=bytes(body)
        token=CURRENT_USER.set(user)
        try:response=await call_next(request)
        finally:CURRENT_USER.reset(token)
        response.headers["X-Content-Type-Options"]="nosniff"
        response.headers["Referrer-Policy"]="no-referrer"
        response.headers["Content-Security-Policy"]="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; media-src 'self' blob:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        # Authenticated certificate PDFs alone may be previewed by this same-origin app.
        if path.startswith('/api/learning/certificates/') and path.endswith('.pdf'):
            response.headers['Content-Security-Policy']=response.headers['Content-Security-Policy'].replace("frame-ancestors 'none'", "frame-ancestors 'self'")
        response.headers["Permissions-Policy"]="microphone=(self), camera=(), geolocation=()"
        if path.startswith("/api/") or path in {"/","/login","/mentor","/learner"}:response.headers["Cache-Control"]="no-store"
        if path.startswith('/static/'):
            response.headers['Cache-Control'] = 'no-cache, max-age=0, must-revalidate'
        if path.startswith('/static/') or path in {'/', '/login', '/mentor', '/learner'}:
            response.headers['X-Trainer-Frontend-Revision'] = frontend_revision
        return response

    @app.exception_handler(HTTPException)
    async def http_error(request, error):
        detail = error.detail if isinstance(error.detail, dict) else {"code": "REQUEST_FAILED", "message": str(error.detail)}
        return JSONResponse({"error": {**detail,"message":ui_error(request,detail.get("code","REQUEST_FAILED"))}}, status_code=error.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        return JSONResponse({"error": {"code": "INVALID_INPUT", "message": ui_error(request,"INVALID_INPUT"), "fields":[list(e["loc"]) for e in error.errors()]}}, status_code=422)

    @app.exception_handler(VersionConflict)
    async def conflict_error(request, error):
        return JSONResponse({"error": {"code": "VERSION_CONFLICT", "message": ui_error(request,"VERSION_CONFLICT")}}, status_code=409)

    @app.exception_handler(sqlite3.Error)
    async def storage_error(request, error):
        return JSONResponse({"error": {"code": "STORAGE_UNAVAILABLE", "message": ui_error(request,"STORAGE_UNAVAILABLE")}}, status_code=503)

    def shared_with_mentor(session):
        return session.get('review_status') in ('submitted','reviewed') or workflow.get('published_review',session['id']) is not None

    def get_session(sid):
        session = store.get_session(sid)
        if not session or not auth.visible(sid,CURRENT_USER.get()) or (CURRENT_USER.get()['role']=='mentor_admin' and not shared_with_mentor(session)):
            fail("SESSION_NOT_FOUND", "Беседа не найдена.", 404)
        return session

    def lock(sid):
        return app.state.locks.setdefault(sid, asyncio.Lock())

    def session_view(session):
        return workflow.enrich(learner_view(session),session,auth)

    attach_workflow(app,workflow,auth,get_session,lock,api_key,model,summary)
    from .ui_preferences import attach_ui_preferences
    attach_ui_preferences(app,workflow,auth)
    from .company_reference import attach_company_reference
    attach_company_reference(app,workflow,store,lock)

    def valid_outcomes(scenario, company):
        if scenario["company_id"] != company["id"]:
            fail("COMPANY_MISMATCH", "Сценарий должен относиться к текущей компании.", 422)
        available = {s["id"] for s in company["services"]} | {"no_fit"}
        if not set(scenario["allowed_outcomes"]).issubset(available):
            fail("INVALID_OUTCOME", "В сценарии указана услуга, которой нет в карточке компании.", 422)

    @app.get("/api/status")
    async def status(request:Request):
        result = {"version": VERSION, "storage": "sqlite", "access_mode": "role_portals", "runtime": runtime,
                "ai": {"configured": live_configured, "live_enabled": live_configured, "model": model,
                       "customer_mode": "simple_actor", "max_requests_per_turn": 1,
                       "modes": {"simple_actor": {"max_requests_per_turn": 1, "llm_verifier": False}, "openai": {"legacy": True, "max_requests_per_turn": 5}}},
                "limits": {"max_turns": max_turns, "max_live_attempts": max_live_attempts}, "roles": ["mentor_admin", "employee"]}
        result["ai"]["transcription"]={"configured":bool(api_key and probe_path()),"model":os.environ.get("OPENAI_TRANSCRIPTION_MODEL","gpt-transcribe"),"max_seconds":60,"max_bytes":MAX_BYTES}
        privileged=bool(request.state.user and request.state.user["role"]=="mentor_admin") or bool(local_token and secrets.compare_digest(request.headers.get("x-trainer-local-token",""),local_token))
        if not privileged:result.pop("runtime",None)
        return result

    @app.get("/api/client-profiles")
    async def profiles():
        return {"profiles":[visible_profile(p) for p in persona_service.all() if p.get("available",True)]}

    from .models import InputModel
    class ProfileImport(InputModel):
        json_text: str = Field(max_length=200000)
    @app.post('/api/mentor/client-profiles/import-check',dependencies=[Depends(mentor)])
    async def import_profile(value:ProfileImport):
        def pairs(items):
            result={}
            for key,item in items:
                if key in result:raise ValueError('Duplicate JSON key: '+key)
                result[key]=item
            return result
        try:profile=ClientProfile.model_validate(json.loads(value.json_text,object_pairs_hook=pairs)).model_dump()
        except ValueError:fail('INVALID_INPUT','Duplicate keys, invalid field IDs or references in profile',422)
        return {'profile':profile}

    @app.get("/api/mentor/client-profiles/schema", dependencies=[Depends(mentor)])
    async def profile_schema():
        return ClientProfile.model_json_schema()

    @app.get("/api/mentor/client-profiles", dependencies=[Depends(mentor)])
    async def mentor_profiles():
        return {"profiles": persona_service.all()}

    @app.get("/api/materials")
    async def materials():
        language = (CURRENT_USER.get() or {}).get("locale", "de")
        return public_materials(store, persona_service.all(), language)

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
        for profile in persona_service.all():
            valid_outcomes(profile["scenario"]["source_scenario"],record)
        from .company_editing import publish_company_edit
        record = publish_company_edit(store,workflow,previous,record)
        return {"company": record}

    @app.get("/api/scenarios")
    async def scenarios():
        return {'scenarios':[{**{k:sc[k] for k in ('id','title','customer_name','public_brief','language','revision')},
            'company_name':store.get_company()['name'],'personas':persona_service.choices(sc['id'])}
            for sc in store.list_scenarios() if persona_service.choices(sc['id'])]}

    @app.get('/api/mentor/scenario-personas', dependencies=[Depends(mentor)])
    async def scenario_personas():
        return {'assignments':[persona_service.assignment(sc['id']) for sc in store.list_scenarios()],
                'profiles':[{'id':p['id'],'name':p['persona']['name'],'version':p['version'],'available':p.get('available',True)} for p in persona_service.all()]}

    @app.put('/api/mentor/scenarios/{sid}/personas', dependencies=[Depends(mentor)])
    async def assign_personas(sid: str,value: ScenarioPersonas):
        return {'assignment':persona_service.assign(sid,value)}

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
        return {"sessions": [{**summary(s),"analysis_status":(workflow.get("analysis",s["id"]+":learner") or {}).get("status","not_run")} for s in store.list_sessions() if auth.visible(s["id"],CURRENT_USER.get()) and (CURRENT_USER.get()["role"]!="mentor_admin" or shared_with_mentor(s))]}

    @app.post("/api/sessions")
    async def start(value: SessionStart):
        if value.mode!="simple_actor":
            fail("MODE_UNAVAILABLE","Для новых тренировок используется simple_actor.",422)
        if value.mode in {"openai", "simple_actor"} and not live_configured:
            fail("AI_NOT_CONFIGURED", "OpenAI ещё не подключён. Запустите сервер с API-ключом или выберите сценарный режим.", 409)
        selected_profile = None
        if value.mode == "simple_actor":
            selected_profile = persona_service.compose_pair(value.scenario_id,value.client_profile_id)
            scenario = copy.deepcopy(selected_profile['scenario']['source_scenario'])
        else:
            if value.client_profile_id is not None:
                fail("PROFILE_MODE_MISMATCH", "Профили используются в simple_actor.", 422)
            scenario = store.get_scenario(value.scenario_id)
        if not scenario:
            fail("SCENARIO_NOT_FOUND", "Сценарий не найден.", 404)
        comp = store.get_company()
        if not comp["reviewed"]:
            fail("COMPANY_NOT_REVIEWED", "Наставнику нужно проверить и подтвердить карточку компании.", 409)
        valid_outcomes(scenario, comp)
        language = value.training_language or scenario['language']
        if language != scenario['language'] and not builtin_scenario(scenario):
            fail('TRAINING_LANGUAGE_UNAVAILABLE', 'Для изменённого задания используйте его авторский язык.', 422)
        scenario = localized_scenario(scenario, language)
        comp = localized_company(comp, language)
        if selected_profile:
            selected_profile['scenario']['source_scenario'] = copy.deepcopy(scenario)
            selected_profile['scenario']['initial_situation'] = scenario['opening']
            selected_profile['persona']['name'] = persona_label(selected_profile, language)
        ts = now()
        session = {"employee_id": CURRENT_USER.get()["id"], "id": uuid4().hex, "scenario_id": scenario["id"], "scenario_snapshot": copy.deepcopy(scenario),
                   "company_snapshot": copy.deepcopy(comp), "mode": value.mode, "created_at": ts, "updated_at": ts,
                   "status": "active", "review_status": "not_submitted", "review_note": "", "reviewed_at": None,
                   "version": 1, "state": {"phase": "needs", "discovered": [], "needs_confirmed": False,
                   "capabilities_confirmed": False, "events": [], "outcome": None},
                   "messages": [{"role": "customer", "text": scenario["opening"], "at": ts, "turn": 0}],
                   "receipts": {}, "live_attempts": 0, "live_requests": 0, "api_count_complete": True, "system_issues": []}
        if selected_profile:
            session["client_profile_snapshot"] = copy.deepcopy(selected_profile)
            session["content_observations"] = []
            session['selection_snapshot']={'scenario_id':scenario['id'],'scenario_revision':scenario['revision'],
                'profile_id':selected_profile['id'],'profile_version':selected_profile['version'],
                'persona_version':selected_profile['persona']['version'],'persona_label':selected_profile['persona']['name'],
                'training_language':language,'materials_version':1}
        workflow.put("snapshot",session["id"],workflow.snapshot(session["scenario_id"]))
        store.save_session(session)
        return {"session": session_view(session)}

    @app.get("/api/sessions/{sid}")
    async def show_session(sid: str):
        return {"session": session_view(get_session(sid))}

    @app.post("/api/sessions/{sid}/messages")
    async def message(sid: str, value: MessageInput):
        async with lock(sid):
            session = get_session(sid)
            fingerprint = hashlib.sha256(json.dumps({"text": value.text, "kind": value.kind}, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
            receipt = session.get("receipts", {}).get(value.request_id)
            if receipt:
                if receipt["fingerprint"] != fingerprint:
                    fail("IDEMPOTENCY_CONFLICT", "Этот идентификатор уже использован для другой реплики.", 409)
                return {"session": session_view(session)}
            if session["status"] != "active" or session["state"]["phase"] == "completed":
                fail("SESSION_CLOSED", "Диалог завершён. Откройте разбор или начните новую попытку.", 409)
            if session["version"] != value.version:
                fail("VERSION_CONFLICT", "Беседа обновилась. Загрузите её заново.", 409)
            turn = summary(session)["turn_count"] + 1
            if turn > max_turns:
                fail("TURN_LIMIT", "Достигнут лимит беседы. Завершите её и откройте разбор.", 409)
            if session["mode"] in {"openai", "simple_actor"}:
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
                processor = process_simple_turn if session["mode"] == "simple_actor" else process_turn
                updated = await processor(session, value.text, "message" if session["mode"]=="simple_actor" else value.kind, current_provider, turn)
            except ProviderError as exc:
                # Fixed safe message; no provider payload / user content / secrets.
                code = getattr(exc, "code", "AI_UNAVAILABLE")
                error_code = code
                if code != "scenario_missing_context":
                    infrastructure = {"ai_timeout", "ai_unavailable", "ai_rate_limited", "ai_access_denied", "ai_request_rejected", "ai_not_configured"}
                    category = ("infrastructure_error" if code in infrastructure else
                                "actor_response_error" if code.startswith("ai_actor_") or session["mode"]=="simple_actor" else "director_response_error")
                    session.setdefault("system_issues", []).append({"type":category, "code":code, "turn":turn,
                        "detail":"Ответ системы не получен или не прошёл проверку. Это не ошибка ученика; ход не засчитан."})
                    session["system_issues"] = session["system_issues"][-30:]
                if code == "scenario_missing_context":
                    issue = {"type": "scenario_missing_context", "turn": turn,
                             "detail": "В карточке не хватило сведений для ответа. Ход не засчитан; это ограничение сценария, не ошибка ученика."}
                    session.setdefault("system_issues", []).append(issue)
                    session["system_issues"] = session["system_issues"][-30:]
                    fail(code, "В карточке нет данных для ответа на этот вопрос. Это ограничение сценария, а не ошибка ученика. Наставнику нужно дополнить карточку.", 422)
                message = ("Соединение с AI временно недоступно. Реплика не засчитана; текст сохранён. Повторите отправку позже." if code in {"ai_timeout","ai_unavailable","ai_rate_limited","ai_access_denied","ai_request_rejected"} else "Ответ клиента не прошёл локальную проверку и не показан. Это технический отказ, не оценка вашей реплики. Можно повторить отправку.")
                fail(code, message, 502)
            except (ValueError, TypeError, KeyError, RuntimeError):
                error_code = "INVALID_AI_RESPONSE"
                fail("INVALID_AI_RESPONSE", "Ответ системы не прошёл проверку. Ход не засчитан; повторите отправку.", 502)
            finally:
                if session["mode"] in {"openai", "simple_actor"}:
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
            return {"session": session_view(updated)}

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
            return {"session": session_view(session)}

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
            return {"session": session_view(session)}

    def exportable(sid):
        session = get_session(sid)
        if session["status"] != "finished" and CURRENT_USER.get()["role"]!="mentor_admin":
            fail("FINISH_REQUIRED", "Полная расшифровка с разбором доступна после завершения.", 409)
        if CURRENT_USER.get()["role"]!="mentor_admin":
            session=copy.deepcopy(session)
            session["report"]=session_view(session)["report"]
            session["scenario_snapshot"]["facts"]=[]
            session["restricted_export"]=True
        if session["mode"] == "simple_actor":
            session=copy.deepcopy(session)
            # Use the same role-redacted report as the dashboard. Never rewrite the stored historical result.
            session["report"]=session_view(session)["report"]
        session=copy.deepcopy(session)
        session["learning"]=session_view(session)
        return session

    def download(data, kind, sid, content_type):
        return Response(data, media_type=content_type, headers={"Content-Disposition": f'attachment; filename="consultation-{sid[:12]}.{kind}"'})

    @app.get("/api/sessions/{sid}/export.txt")
    async def text_export(sid: str, language: str = "de"):
        from .learning_exports import report_text
        session=exportable(sid)
        if CURRENT_USER.get()["role"]!="mentor_admin":language=session["scenario_snapshot"]["language"]
        return download(report_text(session, language), "txt", sid, "text/plain; charset=utf-8")

    @app.get("/api/sessions/{sid}/export.json")
    async def json_export(sid: str):
        session = exportable(sid)
        clean = (session_view(session) if CURRENT_USER.get()["role"]!="mentor_admin" else {k:v for k,v in session.items() if k not in {"receipts"}})
        return download(json.dumps(clean, ensure_ascii=False, indent=2), "json", sid, "application/json; charset=utf-8")

    @app.get("/api/sessions/{sid}/export.pdf")
    async def pdf_export(sid: str, language: str = "de"):
        session = exportable(sid)
        if CURRENT_USER.get()["role"]!="mentor_admin":language=session["scenario_snapshot"]["language"]
        try:
            from .learning_exports import report_pdf
            pdf = await asyncio.to_thread(report_pdf, session, language)
        except (RuntimeError, ImportError):
            fail("PDF_UNAVAILABLE", "Для PDF нужен шрифт с кириллицей. Сохраните TXT или установите шрифты по инструкции запуска.", 503)
        return download(pdf, "pdf", sid, "application/pdf")

    @app.get("/api/mentor/reviews", dependencies=[Depends(mentor)])
    async def reviews():
        result=[]
        for record in store.list_sessions():
            if not shared_with_mentor(record):continue
            owner=auth.owner(record["id"]);u=auth.user(owner) if owner else None
            result.append({**summary(record),"employee_name":u["display_name"] if u else "Архив A09 без владельца","employee_id":owner,"archived":owner is None})
        return {"sessions":result}

    def submitted(sid):
        session = get_session(sid)
        if session["status"] != "finished" or session["review_status"] == "not_submitted":
            fail("REVIEW_NOT_SUBMITTED", "Эта беседа ещё не передана наставнику.", 404)
        return session

    @app.get("/api/mentor/reviews/{sid}", dependencies=[Depends(mentor)])
    async def review_view(sid: str):
        return {"session": session_view(get_session(sid))}

    @app.post("/api/mentor/reviews/{sid}", dependencies=[Depends(mentor)])
    async def review(sid: str, value: ReviewInput):
        async with lock(sid):
            session = submitted(sid)
            # Published feedback is immutable. An identical retry returns the original receipt.
            if session.get('review_status')=='reviewed' or workflow.published(session,auth):
                same_assessment=value.assessment is None or value.assessment.model_dump()==session.get('mentor_assessment')
                legacy_change=any(x is not None for x in (value.needs_confirmed,value.capabilities_confirmed,value.outcome))
                if value.note==session.get('review_note') and same_assessment and not legacy_change:
                    return {"session":session_view(session)}
                fail('REVIEW_ALREADY_PUBLISHED','Published feedback is read-only.',409)
            previous = session["version"]
            if session["mode"] == "simple_actor" and (value.needs_confirmed is not None or value.capabilities_confirmed is not None or value.outcome is not None):
                needs = value.needs_confirmed is True
                capabilities = value.capabilities_confirmed is True
                if capabilities and not needs or value.outcome and not (needs and capabilities):
                    fail("STAGE_ORDER", "Сначала подтвердите потребности, затем возможности, затем обоснованный итог.", 422)
                if value.outcome and value.outcome not in session["scenario_snapshot"]["allowed_outcomes"]:
                    fail("INVALID_OUTCOME", "Итог не разрешён сценарием.", 422)
                state=session["state"]
                state.update(needs_confirmed=needs, capabilities_confirmed=capabilities, outcome=value.outcome,
                             phase="completed" if value.outcome else "proposal" if capabilities else "capabilities" if needs else "needs")
                state["events"].append({"type":"owner_assessment","turn":0,"detail":"Этапы и итог отмечены наставником после содержательного разбора, не моделью."})
                session["report"] = build_report(session)
            if value.assessment is not None:
                if session["mode"] != "simple_actor":
                    fail("INVALID_OUTCOME", "Эта оценка предназначена для Simple Actor.", 422)
                session["mentor_assessment"] = value.assessment.model_dump()
            elif value.needs_confirmed is not None or value.capabilities_confirmed is not None or value.outcome is not None:
                # Explicit legacy reassessment replaces a previous independent one.
                session.pop("mentor_assessment", None)
            session.update(reviewed_by=CURRENT_USER.get()["id"], review_note=value.note, reviewed_at=now(), review_status="reviewed", updated_at=now(), version=previous + 1)
            session["report"] = build_report(session)
            user=CURRENT_USER.get()
            draft=workflow.get('decision_draft',sid) or {}
            workflow.publish_review(session,previous,{'session_id':sid,'employee_id':auth.owner(sid),
                'mentor_id':user['id'],'mentor_name':user['display_name'],'published_at':session['reviewed_at'],
                'note':value.note,'assessment':session.get('mentor_assessment'),'goal':draft.get('goal','not_reviewed'),
                'observations':draft.get('observations','')})
            return {"session": session_view(session)}

    @app.get("/api/mentor/employees/{uid}/sessions",dependencies=[Depends(mentor)])
    async def employee_history(uid:str):
        if not auth.user(uid):fail("NOT_FOUND","Сотрудник не найден.",404)
        return {"sessions":[summary(s) for s in store.list_sessions() if auth.owner(s["id"])==uid and shared_with_mentor(s)]}

    @app.get("/api/mentor/overview",dependencies=[Depends(mentor)])
    async def overview():
        all_sessions=[s for s in store.list_sessions() if shared_with_mentor(s)]
        return {"employees":len(auth.users()),"trainings":len(all_sessions),"pending":sum(s["review_status"]=="submitted" for s in all_sessions),"recent":[summary(s) for s in all_sessions if s["status"]=="finished"][:6]}

    @app.post("/api/mentor/client-profiles/validate",dependencies=[Depends(mentor)])
    async def validate_profile(value:ClientProfile):
        valid_outcomes(value.scenario.source_scenario.model_dump(),store.get_company())
        return {"profile":value.model_dump()}

    @app.post("/api/mentor/client-profiles",dependencies=[Depends(mentor)])
    async def create_profile(value:ClientProfile):
        valid_outcomes(value.scenario.source_scenario.model_dump(),store.get_company())
        return {"profile":persona_service.save(value.model_dump(),create=True)}

    @app.put("/api/mentor/client-profiles/{pid}",dependencies=[Depends(mentor)])
    async def save_profile(pid:str,value:ClientProfile):
        if value.id!=pid:fail("PROFILE_ID_IMMUTABLE","ID профиля менять нельзя.",422)
        valid_outcomes(value.scenario.source_scenario.model_dump(),store.get_company())
        return {"profile":persona_service.save(value.model_dump())}

    @app.get("/api/mentor/client-profiles/{pid}/versions",dependencies=[Depends(mentor)])
    async def profile_versions(pid:str):
        return {"versions":[p for p in store._list("client_profile_version") if p["id"]==pid]}

    @app.get("/api/mentor/reviews/{sid}/diagnostics",dependencies=[Depends(mentor)])
    async def diagnostics(sid:str):
        record=get_session(sid)
        entries=[]
        if audit_dir:
            for path in sorted(audit_dir.glob(sid+"-*.json")):
                try:a=json.loads(path.read_text())
                except (ValueError,OSError):continue
                if a.get("error_code"):
                    entries.append({"turn":a.get("turn"),"code":a["error_code"],"api_requests":a.get("api_requests"),"upstream":[{k:v for k,v in t.items() if k in {"category","status","exception_type"}} for t in a.get("trace",[]) if t.get("kind")=="upstream_error"]})
        return {"issues":record.get("system_issues",[]),"attempts":entries}

    @app.get("/api/mentor/transcription-diagnostics",dependencies=[Depends(mentor)])
    async def transcription_diagnostics():
        return {"errors":store._list("transcription_diagnostic")[-100:]}

    transcription_gate=asyncio.Semaphore(2)
    transcription_attempts={}
    @app.post("/api/transcriptions")
    async def dictation(request:Request,language:str="ru",format:str="webm"):
        import time
        uid=request.state.user["id"];stamp=time.time()
        recent=[t for t in transcription_attempts.get(uid,[]) if stamp-t<60]
        if len(recent)>=6:fail("TRANSCRIPTION_LIMIT","Не более шести записей в минуту.",429)
        transcription_attempts[uid]=recent+[stamp]
        model=os.environ.get("OPENAI_TRANSCRIPTION_MODEL","gpt-transcribe")
        def count_request():
            with store.connection() as con:
                con.execute("CREATE TABLE IF NOT EXISTS transcription_usage (user_id TEXT NOT NULL,created_at REAL NOT NULL,model TEXT NOT NULL,api_requests INTEGER NOT NULL)")
                con.execute("INSERT INTO transcription_usage VALUES (?,?,?,?)",(uid,stamp,model,1))
        def dictation_error(category,detail):
            store._put("transcription_diagnostic",uuid4().hex,{"employee_id":uid,"at":stamp,"model":model,"category":category,"detail":detail})
        async with transcription_gate:
            result=await transcribe(await request.body(),format,language,api_key,model,count_request,dictation_error)
        return result

    frontend = ROOT / "frontend"

    # One content fingerprint for the complete frontend, captured with this process.
    # Fresh HTML changes URLs even when an older browser cache entry is still fresh.
    frontend_files = [frontend / name for name in (
        'index.html', 'login.html', 'app.js', 'boot.js', 'i18n.js', 'login.js',
        'mentor_studio.js', 'voice.js', 'ui_organization.js', 'learning.js', 'company_reference.js', 'styles.css', 'portals.css', 'conversation.js', 'conversation.css', 'appearance.css', 'header_menus.js', 'header_menus.css', 'presentation.js',
        'locales/de.json', 'locales/en.json', 'locales/ru.json')]
    frontend_revision = hashlib.sha256(b''.join(
        p.relative_to(frontend).as_posix().encode() + b'\0' + p.read_bytes() + b'\0'
        for p in frontend_files)).hexdigest()[:16]
    runtime['frontend_revision'] = frontend_revision

    def frontend_page(name):
        html = (frontend / name).read_text()
        import re
        html = re.sub(r'((?:src|href)="/static/[^"?]+)(")',
                      lambda m: m[1] + '?v=' + frontend_revision + m[2], html)
        html = html.replace('</head>', '<meta name="trainer-frontend-revision" content="'
                            + frontend_revision + '"></head>')
        return HTMLResponse(html)

    @app.get("/")
    async def index():
        u=CURRENT_USER.get()
        return RedirectResponse("/mentor" if u and u["role"]=="mentor_admin" else "/learner" if u else "/login",status_code=303)

    @app.get("/favicon.ico")
    async def favicon():return Response(status_code=204)

    @app.get("/login")
    async def login_page():return frontend_page("login.html")

    @app.get("/mentor")
    @app.get("/learner")
    async def portal(request:Request):
        u=CURRENT_USER.get()
        if not u:return RedirectResponse("/login?portal="+("mentor" if request.url.path=="/mentor" else "learner"),status_code=303)
        expected="/mentor" if u["role"]=="mentor_admin" else "/learner"
        if request.url.path!=expected:
            requested="mentor" if request.url.path=="/mentor" else "learner"
            return RedirectResponse("/login?portal="+requested+"&reason=role",status_code=303)
        return frontend_page("index.html")

    app.mount("/static", StaticFiles(directory=frontend), name="static")
    return app


app = create_app()
