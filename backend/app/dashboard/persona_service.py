"""SQLite profile library and immutable revisions; sessions keep their own snapshots."""
from copy import deepcopy
import json
from .client_profiles import ClientProfile, public_profile, SessionModifiers
from .auth import fail

class PersonaService:
    def __init__(self,store,initial):
        self.store=store
        entries=list(initial)
        base=deepcopy(next(p for p in entries if p['persona']['id']=='analytical'))
        for id,name,character,decision in [
          ('decisive','Решительный клиент','Ясно формулирует потребность, спокойно и прямо уточняет условия. Решительность не означает согласия на неподтверждённое предложение.','Выбирает следующий шаг после выяснения фактов и условий.'),
          ('indecisive','Нерешительный клиент','Сомневается при недостатке информации, уточняет понятные альтернативы. Не придумывает обстоятельства или обещания.','Просит время обдумать и объяснить различия вариантов.')]:
            p=deepcopy(base);p['id']=id+'_oven';p['persona'].update(id=id,name=name,character=character,decision_style=decision,psychological_type=id,version=1)
            p['scenario']['persona_ids']=[id];p['available']=True
            for key,label in {'room_area':'Площадь помещения','oven_volume':'Объём печи','maintenance_frequency':'Периодичность обслуживания','production_use':'Производственный процесс и применение печи','gas_bills':'Счета за газ'}.items():
                p['scenario']['open_questions'][key]={'label':label,'status':'author_missing','value':''}
            entries.append(p)
        with store.connection() as c:
            for p in entries:
                if p['id'] in {'cautious_oven','urgent_oven','skeptical_oven','undecided_oven','analytical_oven'} and p['version']==1 and p['persona']['approval']=='technical_draft':p['available']=False
                p=ClientProfile.model_validate(p).model_dump()
                if not c.execute("SELECT 1 FROM documents WHERE kind='client_profile' AND id=?",(p['id'],)).fetchone():
                    data=json.dumps(p,ensure_ascii=False)
                    c.execute("INSERT INTO documents VALUES ('client_profile',?,?)",(p['id'],data))
                    c.execute("INSERT OR IGNORE INTO documents VALUES ('client_profile_version',?,?)",(p['id']+':v'+str(p['version']),data))
        self.upgrade_decisive()

    def upgrade_decisive(self):
        from pathlib import Path
        template=json.loads((Path(__file__).resolve().parents[3]/'profiles/personas/decisive.v2.json').read_text())
        with self.store.connection() as c:
            c.execute('BEGIN IMMEDIATE')
            if c.execute("SELECT 1 FROM metadata WHERE key='a13_decisive_v2'").fetchone():return
            row=c.execute("SELECT data FROM documents WHERE kind='client_profile' AND id='decisive_oven'").fetchone()
            if row:
                p=json.loads(row[0])
                # An owner edit takes precedence. Never silently overwrite it.
                expected={'character':'Ясно формулирует потребность, спокойно и прямо уточняет условия. Решительность не означает согласия на неподтверждённое предложение.',
                          'decision_style':'Выбирает следующий шаг после выяснения фактов и условий.'}
                safe=(p['version']==1 and p['persona']['version']==1 and all(p['persona'].get(k)==v for k,v in expected.items())
                      and p['persona'].get('additional_behavior','')=='')
                if safe:
                    c.execute("INSERT OR IGNORE INTO documents VALUES ('client_profile_version','decisive_oven:v1',?)",(row[0],))
                    p['version']=2;p['persona']=template
                    p=ClientProfile.model_validate(p).model_dump()
                    data=json.dumps(p,ensure_ascii=False)
                    c.execute("UPDATE documents SET data=? WHERE kind='client_profile' AND id='decisive_oven'",(data,))
                    c.execute("INSERT INTO documents VALUES ('client_profile_version','decisive_oven:v2',?)",(data,))
            c.execute("INSERT INTO metadata VALUES ('a13_decisive_v2','1')")

    def all(self):return self.store._list('client_profile')
    def get(self,id):return self.store._get('client_profile',id)
    def save(self,value,create=False):
        p=ClientProfile.model_validate(value).model_dump()
        with self.store.connection() as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute("SELECT data FROM documents WHERE kind='client_profile' AND id=?",(p['id'],)).fetchone()
            old=json.loads(row[0]) if row else None
            if create and old:fail('PROFILE_EXISTS','Такой ID уже существует. Выберите другой.',409)
            if not create and not old:fail('NOT_FOUND','Профиль не найден.',404)
            if old and p['version']!=old['version']:fail('VERSION_CONFLICT','Профиль изменился. Загрузите новую версию.',409)
            p['version']=old['version']+1 if old else 1
            for key in ['persona','scenario','modifiers']:
                if old:
                    a={k:v for k,v in p[key].items() if k!='version'};b={k:v for k,v in old[key].items() if k!='version'}
                    p[key]['version']=old[key]['version']+(a!=b)
            if old and p['scenario']['source_scenario']!=old['scenario']['source_scenario']:
                p['scenario']['source_scenario']['revision']=old['scenario']['source_scenario']['revision']+1
            text=json.dumps(p,ensure_ascii=False)
            c.execute("INSERT INTO documents VALUES ('client_profile',?,?) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data",(p['id'],text))
            c.execute("INSERT INTO documents VALUES ('client_profile_version',?,?)",(p['id']+':v'+str(p['version']),text))
        return p

    def assignment(self, sid):
        return self.store._get('scenario_personas',sid) or {'scenario_id':sid,'revision':0,'profile_ids':['decisive_oven','indecisive_oven']}

    def assign(self, sid, value):
        if not self.store.get_scenario(sid):fail('NOT_FOUND','Сценарий не найден.',404)
        if any(not self.get(pid) for pid in value.profile_ids):fail('NOT_FOUND','Персонаж не найден.',404)
        with self.store.connection() as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute("SELECT data FROM documents WHERE kind='scenario_personas' AND id=?",(sid,)).fetchone()
            old=json.loads(row[0]) if row else self.assignment(sid)
            if old['revision']!=value.revision:fail('VERSION_CONFLICT','Назначения изменились. Обновите страницу.',409)
            record={'scenario_id':sid,'revision':old['revision']+1,'profile_ids':list(dict.fromkeys(value.profile_ids))}
            c.execute("INSERT INTO documents VALUES ('scenario_personas',?,?) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data",(sid,json.dumps(record)))
        return record

    def choices(self,sid):
        ids=self.assignment(sid)['profile_ids']
        return [{'id':p['id'],'version':p['version'],'persona_version':p['persona']['version'],'name':p['persona']['name']} for p in self.all() if p['id'] in ids and p.get('available',True)]

    def compose_pair(self,sid,pid):
        p=deepcopy(self.get(pid));sc=deepcopy(self.store.get_scenario(sid))
        if not p or not sc or pid not in {x['id'] for x in self.choices(sid)}:
            fail('CLIENT_PROFILE_REQUIRED','Выберите доступный характер для этого сценария.',422)
        # Behavior is independent of scenario facts. Never borrow modifiers or
        # fact references from a different embedded legacy case.
        old=p['scenario'];same=old['source_scenario']['id']==sid
        ids={f['id'] for f in sc['facts']}
        p['scenario']={'id':sc['id'],'version':sc['revision'],'persona_ids':[p['persona']['id']],
            'source_scenario':sc,'initial_situation':sc['opening'],
            **{k:[i for i in old[k] if i in ids] if same else [] for k in ['reason_fact_ids','observation_fact_ids','need_fact_ids','financial_fact_ids','timing_fact_ids']},
            'open_questions':old['open_questions'] if same else {},
            'disclosure_conditions':{i:old['disclosure_conditions'].get(i,'available') if same else 'available' for i in ids},
            'critical_contradictions':['equipment_is_customer_owned','no_confirmed_repair_price','no_confirmed_booking']}
        if not same:p['modifiers']=SessionModifiers().model_dump()
        assembled=ClientProfile.model_validate(p).model_dump()
        # Validation fills optional schema defaults. Preserve the exact authored
        # source record (including absent optional fields) in the snapshot.
        assembled['scenario']['source_scenario']=sc
        return assembled
