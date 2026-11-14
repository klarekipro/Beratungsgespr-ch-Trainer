"""Explicit employee archive and reviewed deletion of explicitly marked test data."""
import hashlib
import json
import time
from .auth import fail, normalize_login, password_ok, PH, CURRENT_USER, public_user, employee_state, record_employee_transition
from argon2.exceptions import VerificationError, InvalidHashError
from .models import InputModel
from pydantic import Field

class Confirm(InputModel):
    confirm: bool
class TestMark(Confirm):
    is_test: bool
class DeleteEmployee(Confirm):
    username: str
    fingerprint: str = Field(min_length=64,max_length=64)

class EmployeeLifecycle:
    def __init__(self,auth):self.auth=auth;self.store=auth.store
    def employee(self,uid):
        u=self.auth.user(uid)
        if not u or u['role']!='employee':fail('NOT_FOUND','Employee not found',404)
        return u
    def archive(self,uid,author):
        self.employee(uid)
        with self.store.connection() as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute('SELECT u.active,l.archived_at FROM users u LEFT JOIN employee_lifecycle l ON l.user_id=u.id WHERE u.id=?',(uid,)).fetchone()
            if not row:fail('NOT_FOUND','Employee not found',404)
            previous=employee_state(*row)
            c.execute('INSERT OR IGNORE INTO employee_lifecycle(user_id) VALUES (?)',(uid,))
            c.execute('UPDATE employee_lifecycle SET archived_at=COALESCE(archived_at,?),archived_by=? WHERE user_id=?',(time.time(),author,uid))
            c.execute('UPDATE users SET active=0 WHERE id=?',(uid,))
            record_employee_transition(c,uid,previous,'archived',author)
            c.execute('DELETE FROM auth_sessions WHERE user_id=?',(uid,))
        return public_user(self.auth.user(uid))
    def mark(self,uid,is_test,author):
        self.employee(uid)
        with self.store.connection() as c:
            c.execute('INSERT OR IGNORE INTO employee_lifecycle(user_id) VALUES (?)',(uid,))
            c.execute('UPDATE employee_lifecycle SET is_test=?,marked_by=? WHERE user_id=?',(int(is_test),author,uid))
        return public_user(self.auth.user(uid))
    def restore(self,uid,password,username=None):
        """IT-only local procedure: retain identity, replace credentials, revoke every session."""
        self.employee(uid);password_ok(password);hashed=PH.hash(password)
        with self.store.connection() as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute('SELECT username,password_hash FROM users WHERE id=?',(uid,)).fetchone()
            archived=c.execute('SELECT archived_at FROM employee_lifecycle WHERE user_id=?',(uid,)).fetchone()
            if not archived or archived[0] is None:fail('INVALID_INPUT','Employee is not archived',409)
            try:same_password=PH.verify(row[1],password)
            except (VerificationError,InvalidHashError):same_password=False
            if same_password:fail('PASSWORD_POLICY','Restoration requires a new password',422)
            login=normalize_login(username or row[0])
            if c.execute('SELECT 1 FROM users WHERE username=? AND id<>?',(login,uid)).fetchone():fail('LOGIN_UNAVAILABLE','Login conflict',409)
            c.execute('UPDATE users SET username=?,password_hash=?,active=1,must_change_password=1 WHERE id=?',(login,hashed,uid))
            c.execute('UPDATE employee_lifecycle SET archived_at=NULL,restored_at=? WHERE user_id=?',(time.time(),uid))
            record_employee_transition(c,uid,'archived','active','it-local')
            c.execute('DELETE FROM auth_sessions WHERE user_id=?',(uid,))
        return public_user(self.auth.user(uid))
    def _plan(self,c,uid):
        user=c.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
        life=c.execute('SELECT * FROM employee_lifecycle WHERE user_id=?',(uid,)).fetchone()
        if not user or user[4]!='employee':fail('NOT_FOUND','Employee not found',404)
        owned={r[0] for r in c.execute('SELECT session_id FROM training_owners WHERE employee_id=?',(uid,))}
        documents=[]
        for kind,key,text in c.execute('SELECT kind,id,data FROM documents'):
            v=json.loads(text)
            if kind=='session' and (key in owned or v.get('employee_id')==uid):owned.add(key);documents.append((kind,key,text))
        learning=list(c.execute('SELECT kind,id,data FROM learning_records'));selected=[];certs=set();analysis=[]
        for kind,key,text in learning:
            v=json.loads(text)
            if v.get('employee_id')==uid or v.get('session_id') in owned or key in owned or any(key.startswith(s+':') for s in owned) or kind in ('ui_preferences','review_read') and key==uid or set(v.get('basis',[]))&owned:
                if v.get('employee_id') not in (None,uid):fail('VERSION_CONFLICT','Cross-employee references require IT review',409)
                selected.append((kind,key,text))
                if kind=='certificate':certs.add(key)
                if kind=='analysis':analysis.append(v)
        # Legacy history has no session_id. Only exact equality is a reliable link.
        unbound=0
        for kind,key,text in learning:
            if (kind,key,text) in selected:continue
            v=json.loads(text)
            if v.get('certificate_id') in certs or kind=='analysis_history' and v in analysis:selected.append((kind,key,text))
            elif kind=='analysis_history' and not v.get('session_id'):unbound+=1
        owners=list(c.execute('SELECT session_id,employee_id FROM training_owners WHERE employee_id=?',(uid,)))
        sessions=list(c.execute('SELECT * FROM auth_sessions WHERE user_id=?',(uid,)))
        prefs=list(c.execute('SELECT * FROM user_preferences WHERE user_id=?',(uid,)))
        counts={'conversations':len(documents),'learning_records':len(selected),'certificates':len(certs),'ownerships':len(owners),'access_sessions':len(sessions),'preferences':len(prefs),'unattributed_history_retained':unbound}
        usage=list(c.execute('SELECT * FROM transcription_usage WHERE user_id=?',(uid,))) if c.execute("SELECT 1 FROM sqlite_master WHERE name='transcription_usage'").fetchone() else []
        counts['transcription_usage']=len(usage)
        fingerprint=hashlib.sha256(json.dumps([user,life,documents,selected,owners,sessions,prefs,usage],sort_keys=True).encode()).hexdigest()
        return counts,fingerprint,documents,selected
    def preview(self,uid):
        self.employee(uid)
        with self.store.connection() as c:
            counts,fingerprint,_,_=self._plan(c,uid)
        return {'counts':counts,'fingerprint':fingerprint}
    def delete(self,uid,value):
        self.employee(uid)
        with self.store.connection() as c:
            c.execute('BEGIN IMMEDIATE')
            u=c.execute('SELECT username FROM users WHERE id=?',(uid,)).fetchone()
            life=c.execute('SELECT is_test FROM employee_lifecycle WHERE user_id=?',(uid,)).fetchone()
            if not life or not life[0] or not value.confirm or value.username!=u[0]:fail('INVALID_INPUT','Explicit test marking and login confirmation required',422)
            counts,fingerprint,docs,learning=self._plan(c,uid)
            if fingerprint!=value.fingerprint:fail('VERSION_CONFLICT','Related data changed; preview again',409)
            c.executemany('DELETE FROM documents WHERE kind=? AND id=?',[(k,i) for k,i,_ in docs])
            c.executemany('DELETE FROM learning_records WHERE kind=? AND id=?',[(k,i) for k,i,_ in learning])
            for table,col in [('auth_sessions','user_id'),('training_owners','employee_id'),('user_preferences','user_id'),('employee_lifecycle','user_id')]:c.execute(f'DELETE FROM {table} WHERE {col}=?',(uid,))
            if c.execute("SELECT 1 FROM sqlite_master WHERE name='transcription_usage'").fetchone():c.execute('DELETE FROM transcription_usage WHERE user_id=?',(uid,))
            c.execute('DELETE FROM users WHERE id=?',(uid,))
        return {'deleted':True,'counts':counts}

def attach_employee_lifecycle(app,auth):
    service=EmployeeLifecycle(auth);app.state.employee_lifecycle=service
    @app.post('/api/mentor/employees/{uid}/archive')
    def archive(uid:str,value:Confirm):
        if not value.confirm:fail('INVALID_INPUT','Confirmation required',422)
        return {'employee':service.archive(uid,CURRENT_USER.get()['id'])}
    @app.post('/api/mentor/employees/{uid}/test-status')
    def test_status(uid:str,value:TestMark):
        if not value.confirm:fail('INVALID_INPUT','Confirmation required',422)
        return {'employee':service.mark(uid,value.is_test,CURRENT_USER.get()['id'])}
    @app.get('/api/mentor/employees/{uid}/deletion-preview')
    def preview(uid:str):return service.preview(uid)
    @app.delete('/api/mentor/employees/{uid}')
    def delete(uid:str,value:DeleteEmployee):return service.delete(uid,value)
