"""Bounded functional/security smoke. No network, microphone or paid AI calls."""
import copy
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app.dashboard.server import create_app
from backend.app.dashboard.auth import token_hash,COOKIE,AuthStore

class Actor:
    def __init__(self):self.request_count=0;self.trace=[]
    async def customer_reply(self,ctx):
        self.request_count+=1
        return {'speaker_role':'customer','customer_id':ctx['customer_dossier']['customer_id'],'reply':'Причину неисправности я пока не знаю.'}

class PortalSmoke(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.env=patch.dict(os.environ,{'OPENAI_API_KEY':'synthetic-no-network-key','TRAINER_AUDIT_DIR':''});self.env.start();self.addCleanup(self.env.stop)
        self.app=create_app(Path(self.temp.name)/'dashboard/trainer.sqlite3',provider_factory=lambda mode:Actor());self.auth=self.app.state.auth
        self.mentor=self.auth.create_user('mentor-fixture','Наставник',' Synthetic mentor 42 ',role='mentor_admin',temporary=False,bootstrap=True)
        self.clients=[]
        self.m,self.mc=self.login('mentor-fixture',' Synthetic mentor 42 ','mentor')
    def client(self):
        c=TestClient(self.app);c.__enter__();c.headers['Origin']='http://testserver';self.clients.append(c);self.addCleanup(c.__exit__,None,None,None);return c
    def login(self,user,pw,portal='learner'):
        c=self.client();r=c.post('/api/auth/login',json={'username':user,'password':pw,'portal':portal});self.assertEqual(r.status_code,200,r.text)
        csrf=r.json()['csrf'];c.headers['X-CSRF-Token']=csrf;return c,csrf
    def employee(self,name):
        r=self.m.post('/api/mentor/employees',json={'username':name,'display_name':name,'temporary_password':'Temporary fixture 42'});self.assertEqual(r.status_code,200,r.text)
        u=r.json()['employee'];c,csrf=self.login(name,'Temporary fixture 42')
        self.assertEqual(c.get('/api/sessions').status_code,423)
        r=c.post('/api/auth/password',json={'current_password':'Temporary fixture 42','new_password':'Permanent fixture 43'});self.assertEqual(r.status_code,200,r.text)
        c.headers['X-CSRF-Token']=r.json()['csrf'];return c,u
    def training(self,c):
        r=c.post('/api/sessions',json={'scenario_id':'oven_no_fit','mode':'simple_actor','client_profile_id':'decisive_oven'});self.assertEqual(r.status_code,200,r.text);return r.json()['session']
    def test_locale_preferences_do_not_modify_training_or_access(self):
        c,u=self.employee('locale-fixture')
        self.assertEqual(c.get('/api/auth/me').json()['user']['locale'],'de')
        session=self.training(c);sid=session['id'];before=copy.deepcopy(self.app.state.store.get_session(sid))
        for locale in ['de','en','ru']:
            self.assertEqual(c.put('/api/auth/preferences',json={'locale':locale}).status_code,200)
            self.assertEqual(c.get('/api/auth/me').json()['user']['locale'],locale)
            self.assertEqual(before,self.app.state.store.get_session(sid))
        self.assertEqual(c.put('/api/auth/preferences',json={'locale':'xx'}).status_code,422)
        self.assertEqual(c.put('/api/auth/preferences',json={'locale':'en','user_id':self.mentor['id']}).status_code,422)
        self.assertEqual(c.put('/api/auth/preferences',json={'locale':'en'},headers={'X-CSRF-Token':'wrong'}).status_code,403)
        self.assertEqual(self.m.get('/api/auth/me').json()['user']['locale'],'de')
        c.post('/api/auth/logout')
        c,_=self.login('locale-fixture','Permanent fixture 43')
        self.assertEqual(c.get('/api/auth/me').json()['user']['locale'],'ru')
        self.assertEqual(c.post('/api/sessions/'+sid+'/messages',json={'text':'Что случилось?','kind':'message','version':1,'request_id':'locale-smoke-turn'}).status_code,200)
        after=self.app.state.store.get_session(sid)
        for key in ['scenario_snapshot','client_profile_snapshot','company_snapshot','state']:self.assertEqual(before[key],after[key])
        c.post('/api/sessions/'+sid+'/finish')
        self.assertTrue(c.get('/api/sessions/'+sid+'/export.pdf').content.startswith(b'%PDF'))
        root=Path(__file__).resolve().parents[2]/'frontend/locales'
        # Require complete dictionaries and every referenced source key, without testing AI psychology.
        dictionaries={lang:json.loads((root/(lang+'.json')).read_text()) for lang in ['de','en','ru']}
        self.assertEqual(set(dictionaries['de']),set(dictionaries['en']));self.assertEqual(set(dictionaries['de']),set(dictionaries['ru']))
        import re
        for source in (root.parent).glob('*.js'):
            for key in re.findall(r"(?:\.t|data-i18n)=?\(?[\"']([a-z]+\.[a-z_0-9.]+)",source.read_text()):self.assertIn(key,dictionaries['de'])

    def test_independent_pairs_preserve_facts_and_frozen_versions(self):
        c,u=self.employee('pair-fixture')
        legacy=self.app.state.store.get_scenario('oven_replacement')
        for fact in legacy['facts']:fact.pop('material',None)
        self.app.state.store.save_scenario(legacy)
        catalogue=c.get('/api/scenarios').json()['scenarios']
        self.assertEqual(len(catalogue),3)
        saved=[]
        for case in catalogue:
            self.assertEqual({p['id'] for p in case['personas']},{'decisive_oven','indecisive_oven'})
            for persona in case['personas']:
                r=c.post('/api/sessions',json={'scenario_id':case['id'],'mode':'simple_actor','client_profile_id':persona['id']})
                self.assertEqual(r.status_code,200,r.text)
                session=self.app.state.store.get_session(r.json()['session']['id'])
                original=self.app.state.store.get_scenario(case['id'])
                self.assertEqual(session['scenario_snapshot'],original)
                self.assertEqual(session['client_profile_snapshot']['scenario']['source_scenario'],original)
                self.assertEqual(session['client_profile_snapshot']['persona'],self.app.state.store._get('client_profile',persona['id'])['persona'])
                self.assertEqual(self.auth.owner(session['id']),u['id'])
                saved.append(copy.deepcopy(session))
        sid=catalogue[0]['id'];path='/api/mentor/scenarios/'+sid+'/personas'
        self.assertEqual(c.put(path,json={'revision':0,'profile_ids':[]}).status_code,403)
        self.assertEqual(self.m.put(path,json={'revision':0,'profile_ids':[]}).status_code,200)
        self.assertEqual(c.post('/api/sessions',json={'scenario_id':sid,'mode':'simple_actor','client_profile_id':'decisive_oven'}).status_code,422)
        self.assertEqual(self.m.put(path,json={'revision':0,'profile_ids':[]}).status_code,409)
        for old in saved:self.assertEqual(old,self.app.state.store.get_session(old['id']))

    def test_real_login_reset_deactivation_and_no_header_impersonation(self):
        c,u=self.employee('first-fixture')
        self.assertEqual(c.get('/api/mentor/employees',headers={'X-Workspace-Role':'mentor'}).status_code,403)
        self.assertEqual(self.client().post('/api/auth/login',json={'username':'first-fixture','password':'incorrect','portal':'learner'}).status_code,401)
        self.assertEqual(self.m.post('/api/mentor/employees',json={'username':'intruder','display_name':'x','temporary_password':'Something long 42','role':'mentor_admin'}).status_code,422)
        r=self.m.post('/api/mentor/employees/'+u['id']+'/password',json={'temporary_password':'Another temporary 44'});self.assertEqual(r.status_code,200)
        self.assertEqual(c.get('/api/auth/me').status_code,401)
        c,_=self.login('first-fixture','Another temporary 44');self.assertTrue(c.get('/api/auth/me').json()['user']['must_change_password'])
        self.assertEqual(self.m.patch('/api/mentor/employees/'+u['id'],json={'active':False}).status_code,200)
        self.assertEqual(c.get('/api/auth/me').status_code,401)
        self.assertEqual(self.auth.user(u['id'])['active'],0)
    def test_cross_employee_all_paths_and_redacted_exports(self):
        a,ua=self.employee('employee-alpha');b,ub=self.employee('employee-beta');s=self.training(a);sid=s['id']
        payload={'text':'Что случилось?','version':1,'kind':'message','request_id':'portal-smoke-request'}
        self.assertEqual(a.post('/api/sessions/'+sid+'/messages',json=payload).status_code,200)
        for suffix in ['', '/export.pdf','/export.json','/export.txt']:
            self.assertEqual(b.get('/api/sessions/'+sid+suffix).status_code,404)
        for suffix,body in [('/messages',payload),('/finish',{}),('/submit',{})]:self.assertEqual(b.post('/api/sessions/'+sid+suffix,json=body).status_code,404)
        self.assertFalse(b.get('/api/sessions').json()['sessions'])
        self.assertEqual(self.app.state.auth.owner(sid),ua['id'])
        self.assertEqual(a.post('/api/sessions',json={'scenario_id':'oven_no_fit','mode':'simple_actor','client_profile_id':'decisive_oven','employee_id':ub['id']}).status_code,422)
        self.assertEqual(a.post('/api/sessions/'+sid+'/finish').status_code,200)
        data=a.get('/api/sessions/'+sid).json()['session'];self.assertNotIn('facts',data['report']);self.assertNotIn('assessment_outcomes',data['report'])
        export=a.get('/api/sessions/'+sid+'/export.json');self.assertEqual(export.status_code,200)
        text=export.text
        for forbidden in ['client_profile_snapshot','authorized_facts','disclosure_conditions','scenario_snapshot','password_hash','persona_name','approval','psychological_type']:self.assertNotIn(forbidden,text)
        self.assertNotIn('Прежняя сервисная фирма прекратила',a.get('/api/sessions/'+sid+'/export.txt').text)
        self.assertTrue(a.get('/api/sessions/'+sid+'/export.pdf').content.startswith(b'%PDF'))
        self.assertEqual(self.m.get('/api/mentor/employees/'+ua['id']+'/sessions').json()['sessions'][0]['id'],sid)
    def test_csrf_logout_expiry_rate_and_cookie_flags(self):
        c,u=self.employee('security-fixture')
        r=c.get('/api/auth/me');token=c.cookies.get(COOKIE)
        bad=c.post('/api/auth/logout',headers={'X-CSRF-Token':'invalid'});self.assertEqual(bad.status_code,403)
        self.assertEqual(c.post('/api/auth/logout',headers={'Origin':'http://evil.invalid'}).status_code,403)
        self.assertEqual(c.post('/api/auth/logout').status_code,200)
        replay=self.client();replay.cookies.set(COOKIE,token);self.assertEqual(replay.get('/api/sessions').status_code,401)
        c,_=self.login('security-fixture','Permanent fixture 43');token=c.cookies.get(COOKIE)
        with self.app.state.store.connection() as db:db.execute('UPDATE auth_sessions SET expires_at=? WHERE token_hash=?',(time.time()-1,token_hash(token)))
        self.assertEqual(c.get('/api/auth/me').status_code,401)
        with patch.dict(os.environ,{'TRAINER_REMOTE_HTTPS':'1'}):
            secure_app=create_app(Path(self.temp.name)/'dashboard/trainer.sqlite3')
            with TestClient(secure_app,base_url='https://testserver') as tls:
                tls.headers['Origin']='https://testserver'
                tls_login=tls.post('/api/auth/login',json={'username':'mentor-fixture','password':' Synthetic mentor 42 ','portal':'mentor'})
                self.assertEqual(tls_login.status_code,200);self.assertIn('secure',tls_login.headers['set-cookie'].lower())
            with TestClient(secure_app) as insecure:self.assertEqual(insecure.get('/mentor').status_code,426)
        raw=self.client();r=raw.post('/api/auth/login',json={'username':'security-fixture','password':'Permanent fixture 43','portal':'learner'})
        cookie=r.headers['set-cookie'].lower();self.assertIn('httponly',cookie);self.assertIn('samesite=strict',cookie);self.assertNotIn('secure;',cookie)
        attacker=self.client()
        for _ in range(5):attacker.post('/api/auth/login',json={'username':'absent-fixture','password':'bad','portal':'learner'})
        self.assertEqual(attacker.post('/api/auth/login',json={'username':'absent-fixture','password':'bad','portal':'learner'}).status_code,429)
    def test_profile_versions_snapshot_and_manual_review(self):
        c,u=self.employee('profile-fixture');s=self.training(c);sid=s['id']
        old=copy.deepcopy(self.app.state.store.get_session(sid)['client_profile_snapshot'])
        profile=next(p for p in self.m.get('/api/mentor/client-profiles').json()['profiles'] if p['id']=='decisive_oven');profile['persona']['character']='Решителен, но спокойно задаёт уточнения.'
        r=self.m.put('/api/mentor/client-profiles/decisive_oven',json=profile);self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['profile']['version'],2)
        self.assertEqual(old,self.app.state.store.get_session(sid)['client_profile_snapshot'])
        self.assertEqual(self.training(c)['client_profile']['version'],2)
        c.post('/api/sessions/'+sid+'/finish')
        path='/api/mentor/reviews/'+sid
        self.assertEqual(self.m.post(path,json={'note':'Проверка','needs_confirmed':False,'capabilities_confirmed':True}).status_code,422)
        r=self.m.post(path,json={'note':'Проверено наставником','needs_confirmed':True,'capabilities_confirmed':True,'outcome':'no_fit'});self.assertEqual(r.status_code,200)
        self.assertEqual(c.get('/api/sessions/'+sid).json()['session']['review_note'],'Проверено наставником')
    def test_migration_archives_old_data_and_critical_quantities(self):
        legacy={'id':'legacy-archive','mode':'demo','version':1,'updated_at':'2026','employee_id':None}
        self.app.state.store._put('session',legacy['id'],legacy)
        AuthStore(self.app.state.store);AuthStore(self.app.state.store)
        self.assertIsNone(self.auth.owner(legacy['id']))
        c,u=self.employee('archive-fixture');self.assertFalse(self.auth.visible(legacy['id'],self.auth.user(u['id'])));self.assertTrue(self.auth.visible(legacy['id'],self.auth.user(self.mentor['id'])))
        from backend.app.dashboard.simple_actor import dossier,validate_reply
        from backend.app.dashboard.providers import ProviderError
        s=self.training(c);saved=self.app.state.store.get_session(s['id']);own=dossier(saved)
        for text in ['Площадь помещения около 50 квадратных метров.','Объём печи 0,5 кубических метра.','Обслуживание проводится раз в год.']:
            with self.assertRaises(ProviderError):validate_reply({'speaker_role':'customer','customer_id':own['customer_id'],'reply':text},own,saved)

        # A different approved case must not inherit the gas-case type rejection.
        from backend.app.dashboard.seeds import SEED_SCENARIOS
        switched=copy.deepcopy(saved);sc=copy.deepcopy(next(x for x in SEED_SCENARIOS if x['id']=='oven_uncertain'))
        switched['scenario_snapshot']=sc;switched['client_profile_snapshot']['scenario']['source_scenario']=sc
        switched['client_profile_snapshot']['scenario']['disclosure_conditions']={f['id']:'available' for f in sc['facts']}
        ctx=dossier(switched)
        self.assertEqual(validate_reply({'speaker_role':'customer','customer_id':ctx['customer_id'],'reply':'Моя печь бытовая электрическая.'},ctx,switched),'Моя печь бытовая электрическая.')
        with self.assertRaises(ProviderError):validate_reply({'speaker_role':'customer','customer_id':ctx['customer_id'],'reply':'У меня промышленная газовая печь.'},ctx,switched)
        with self.assertRaises(ProviderError):validate_reply({'speaker_role':'customer','customer_id':own['customer_id'],'reply':'Моя печь электрическая.'},own,saved)
