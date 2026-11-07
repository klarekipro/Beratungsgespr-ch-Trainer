"""Local users and revocable server sessions. No bearer tokens in browser storage."""
from contextvars import ContextVar
import hashlib
import re
import secrets
import time
from uuid import uuid4
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import Field, ConfigDict
from typing import Literal
from .models import InputModel

CURRENT_USER=ContextVar('trainer_user',default=None)
COOKIE='trainer_session'
LIFETIME=8*3600
PH=PasswordHasher(time_cost=3,memory_cost=65536,parallelism=2)
DUMMY_HASH=PH.hash(secrets.token_urlsafe(32))

def fail(code,message,status=400):raise HTTPException(status_code=status,detail={'code':code,'message':message})
def public_user(u):return {**{k:u[k] for k in ['id','username','display_name','role']},'active':bool(u['active']),'must_change_password':bool(u['must_change_password']),'locale':u.get('locale','de')}
def password_ok(p):
    if not isinstance(p,str) or not 12<=len(p)<=128:fail('PASSWORD_POLICY','Пароль должен содержать от 12 до 128 символов.',422)
def normalize_login(v):
    v=v.strip().lower()
    if not re.fullmatch(r'[a-z0-9][a-z0-9._-]{2,63}',v):fail('LOGIN_FORMAT','Логин: 3–64 латинских символа, цифры, точка, дефис или подчёркивание.',422)
    return v

def require_mentor(request:Request):
    if not getattr(request.state,'user',None) or request.state.user['role']!='mentor_admin':fail('FORBIDDEN','Доступ запрещён.',403)

def token_hash(token):return hashlib.sha256(token.encode()).hexdigest()

class AuthInput(InputModel):
    model_config=ConfigDict(extra="forbid",str_strip_whitespace=False)

class Login(AuthInput):
    locale: Literal['de','en','ru'] | None = None
    username:str=Field(min_length=1,max_length=64)
    password:str=Field(min_length=1,max_length=128)
    portal:str=Field(pattern=r'^(mentor|learner)$')
class NewEmployee(AuthInput):
    username:str=Field(min_length=3,max_length=64)
    display_name:str=Field(min_length=1,max_length=120)
    temporary_password:str=Field(min_length=12,max_length=128)
class ResetPassword(AuthInput):
    temporary_password:str=Field(min_length=12,max_length=128)
class AccountState(InputModel):
    active:bool
class LocalePreference(InputModel):
    locale: Literal['de','en','ru']

class PasswordChange(AuthInput):
    current_password:str=Field(min_length=1,max_length=128)
    new_password:str=Field(min_length=12,max_length=128)

class AuthStore:
    def __init__(self,store):
        self.store=store
        with store.connection() as c:
            c.execute('CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, username TEXT NOT NULL UNIQUE, display_name TEXT NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN (\'mentor_admin\',\'employee\')), active INTEGER NOT NULL, must_change_password INTEGER NOT NULL, created_at REAL NOT NULL)')
            c.execute("CREATE TABLE IF NOT EXISTS user_preferences (user_id TEXT PRIMARY KEY REFERENCES users(id),locale TEXT NOT NULL CHECK(locale IN ('de','en','ru')))")
            c.execute('CREATE TABLE IF NOT EXISTS auth_sessions (token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), csrf TEXT NOT NULL, created_at REAL NOT NULL, expires_at REAL NOT NULL)')
            c.execute('CREATE INDEX IF NOT EXISTS auth_user ON auth_sessions(user_id)')
            c.execute('CREATE TABLE IF NOT EXISTS login_limits (key TEXT PRIMARY KEY, failures INTEGER NOT NULL, window_start REAL NOT NULL)')
            c.execute('CREATE TABLE IF NOT EXISTS training_owners (session_id TEXT PRIMARY KEY, employee_id TEXT REFERENCES users(id))')
            c.execute("INSERT OR IGNORE INTO training_owners SELECT id,NULL FROM documents WHERE kind='session'")
            c.execute("INSERT OR REPLACE INTO metadata VALUES ('auth_schema_version','1')")
    def user(self,uid):
        with self.store.connection() as c:
            c.row_factory=__import__('sqlite3').Row;r=c.execute("SELECT u.*,COALESCE(p.locale,'de') AS locale FROM users u LEFT JOIN user_preferences p ON p.user_id=u.id WHERE u.id=?",(uid,)).fetchone()
            return dict(r) if r else None
    def set_locale(self,uid,locale):
        if locale not in {'de','en','ru'}:fail('INVALID_LOCALE','Неподдерживаемый язык.',422)
        with self.store.connection() as c:
            c.execute('INSERT INTO user_preferences VALUES (?,?) ON CONFLICT(user_id) DO UPDATE SET locale=excluded.locale',(uid,locale))
    def users(self):
        with self.store.connection() as c:
            c.row_factory=__import__('sqlite3').Row
            return [public_user(dict(r)) for r in c.execute("SELECT * FROM users WHERE role='employee' ORDER BY created_at DESC")]
    def has_mentor(self):
        with self.store.connection() as c:return bool(c.execute("SELECT 1 FROM users WHERE role='mentor_admin' AND active=1").fetchone())
    def create_user(self,username,display_name,password,*,role='employee',temporary=True,bootstrap=False):
        username=normalize_login(username);password_ok(password);hashed=PH.hash(password);uid=uuid4().hex
        with self.store.connection() as c:
            c.execute('BEGIN IMMEDIATE')
            if bootstrap and c.execute("SELECT 1 FROM users WHERE role='mentor_admin' AND active=1").fetchone():fail('ALREADY_CONFIGURED','Первоначальный наставник уже создан.',409)
            if c.execute('SELECT 1 FROM users WHERE username=?',(username,)).fetchone():fail('LOGIN_UNAVAILABLE','Этот логин недоступен.',409)
            c.execute('INSERT INTO users VALUES (?,?,?,?,?,?,?,?)',(uid,username,display_name,hashed,role,1,int(temporary),time.time()))
        return public_user(self.user(uid))
    def owner(self,sid):
        with self.store.connection() as c:
            r=c.execute('SELECT employee_id FROM training_owners WHERE session_id=?',(sid,)).fetchone();return r[0] if r else None
    def visible(self,sid,u):return u is not None and (u['role']=='mentor_admin' or self.owner(sid)==u['id'])
    def revoke(self,uid):
        with self.store.connection() as c:c.execute('DELETE FROM auth_sessions WHERE user_id=?',(uid,))
    def reset(self,uid,password,temporary=True):
        password_ok(password);hashed=PH.hash(password)
        with self.store.connection() as c:
            c.execute('UPDATE users SET password_hash=?,must_change_password=? WHERE id=?',(hashed,int(temporary),uid));c.execute('DELETE FROM auth_sessions WHERE user_id=?',(uid,))
    def active(self,uid,active):
        with self.store.connection() as c:
            c.execute('UPDATE users SET active=? WHERE id=?',(int(active),uid));c.execute('DELETE FROM auth_sessions WHERE user_id=?',(uid,))
    def authenticate(self,username,password,ip,portal):
        stamp=time.time();username=username.strip().lower();keys=[token_hash(ip+'\0'+username),token_hash('ip:'+ip)]
        with self.store.connection() as c:
            for key,maximum in zip(keys,[5,30]):
                r=c.execute('SELECT failures,window_start FROM login_limits WHERE key=?',(key,)).fetchone()
                if r and stamp-r[1]<900 and r[0]>=maximum:fail('LOGIN_LIMIT','Вход временно ограничен. Попробуйте позже.',429)
            c.row_factory=__import__('sqlite3').Row;r=c.execute('SELECT * FROM users WHERE username=?',(username,)).fetchone();u=dict(r) if r else None
        try:valid=PH.verify(u['password_hash'] if u else DUMMY_HASH,password)
        except (VerificationError,InvalidHashError):valid=False
        if not valid or not u or not u['active'] or (u['role']=='mentor_admin')!=(portal=='mentor'):
            with self.store.connection() as c:
                for key in keys:c.execute('INSERT INTO login_limits VALUES (?,1,?) ON CONFLICT(key) DO UPDATE SET failures=CASE WHEN ?-window_start>=900 THEN 1 ELSE failures+1 END,window_start=CASE WHEN ?-window_start>=900 THEN ? ELSE window_start END',(key,stamp,stamp,stamp,stamp))
            fail('INVALID_CREDENTIALS','Не удалось войти. Проверьте реквизиты.',401)
        with self.store.connection() as c:
            c.execute('DELETE FROM login_limits WHERE key=?',(keys[0],))
            if PH.check_needs_rehash(u['password_hash']):c.execute('UPDATE users SET password_hash=? WHERE id=?',(PH.hash(password),u['id']))
        return self.user(u['id'])
    def issue(self,uid):
        token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(32);stamp=time.time()
        with self.store.connection() as c:
            c.execute('DELETE FROM auth_sessions WHERE expires_at<?',(stamp,))
            c.execute('INSERT INTO auth_sessions VALUES (?,?,?,?,?)',(token_hash(token),uid,csrf,stamp,stamp+LIFETIME))
        return token,csrf
    def resolve(self,token):
        if not token or len(token)>100:return None,None
        with self.store.connection() as c:
            r=c.execute('SELECT user_id,csrf FROM auth_sessions WHERE token_hash=? AND expires_at>?',(token_hash(token),time.time())).fetchone()
        u=self.user(r[0]) if r else None
        return (u,r[1]) if u and u['active'] else (None,None)
    def logout(self,token):
        with self.store.connection() as c:c.execute('DELETE FROM auth_sessions WHERE token_hash=?',(token_hash(token or ''),))

def attach_auth(app,auth,secure=False):
    router=APIRouter()
    def session_response(u):
        token,csrf=auth.issue(u['id']);response=JSONResponse({'user':public_user(u),'csrf':csrf})
        response.set_cookie(COOKIE,token,max_age=LIFETIME,httponly=True,secure=secure,samesite='strict',path='/')
        return response
    @router.get('/api/auth/bootstrap-status')
    async def bootstrap_status():return {'configured':auth.has_mentor()}
    @router.post('/api/auth/login')
    def login(value:Login,request:Request):
        user=auth.authenticate(value.username,value.password,request.client.host if request.client else 'unknown',value.portal)
        if value.locale is not None:auth.set_locale(user['id'],value.locale)
        return session_response(auth.user(user['id']))
    @router.get('/api/auth/me')
    async def me(request:Request):
        if not request.state.user:fail('AUTH_REQUIRED','Войдите в свой кабинет.',401)
        return {'user':public_user(request.state.user),'csrf':request.state.csrf}
    @router.put('/api/auth/preferences')
    async def preferences(value:LocalePreference,request:Request):
        auth.set_locale(request.state.user['id'],value.locale)
        return {'locale':value.locale}
    @router.post('/api/auth/logout')
    async def logout(request:Request):
        auth.logout(request.cookies.get(COOKIE));r=JSONResponse({'ok':True});r.delete_cookie(COOKIE,path='/',secure=secure,httponly=True,samesite='strict');return r
    @router.post('/api/auth/password')
    def change_password(value:PasswordChange,request:Request):
        u=request.state.user
        try:PH.verify(u['password_hash'],value.current_password)
        except (VerificationError,InvalidHashError):fail('PASSWORD_CHANGE_FAILED','Пароль не изменён. Проверьте текущий пароль.',400)
        if value.current_password==value.new_password:fail('PASSWORD_POLICY','Выберите новый пароль.',422)
        auth.reset(u['id'],value.new_password,temporary=False);return session_response(auth.user(u['id']))
    @router.get('/api/mentor/employees')
    async def employees():return {'employees':auth.users()}
    @router.post('/api/mentor/employees')
    def create(value:NewEmployee):return {'employee':auth.create_user(value.username,value.display_name,value.temporary_password)}
    def employee(uid):
        u=auth.user(uid)
        if not u or u['role']!='employee':fail('NOT_FOUND','Сотрудник не найден.',404)
        return u
    @router.post('/api/mentor/employees/{uid}/password')
    def reset(uid:str,value:ResetPassword):employee(uid);auth.reset(uid,value.temporary_password);return {'ok':True}
    @router.patch('/api/mentor/employees/{uid}')
    def active(uid:str,value:AccountState):employee(uid);auth.active(uid,value.active);return {'employee':public_user(auth.user(uid))}
    app.include_router(router)
