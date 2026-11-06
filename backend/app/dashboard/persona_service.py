"""SQLite profile library and immutable revisions; sessions keep their own snapshots."""
from copy import deepcopy
import json
from .client_profiles import ClientProfile, public_profile
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
