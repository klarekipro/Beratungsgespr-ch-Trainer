'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const {execFileSync}=require('node:child_process'),{webcrypto}=require('node:crypto');
const profiles=JSON.parse(execFileSync('.venv/bin/python',['-c',`import tempfile,json
from pathlib import Path
from backend.app.dashboard.store import SQLiteStore
from backend.app.dashboard.client_profiles import load_profiles
from backend.app.dashboard.persona_service import PersonaService
with tempfile.TemporaryDirectory() as tmp:
 print(json.dumps(PersonaService(SQLiteStore(Path(tmp)/'seed.sqlite3'),load_profiles()).all(),ensure_ascii=False))`],{encoding:'utf8'}));
const catalog=JSON.parse(fs.readFileSync('frontend/persona_localization.json','utf8'));
const context={window:{},TextEncoder,crypto:webcrypto,fetch:async()=>({ok:true,json:async()=>catalog})};vm.createContext(context);vm.runInContext(fs.readFileSync('frontend/persona_localization.js','utf8'),context);
const clone=x=>JSON.parse(JSON.stringify(x)),L=context.window.TrainerPersonaLocalization;
(async()=>{
 const before=JSON.stringify(profiles);await L.load(profiles);assert.equal(profiles.length,7);
 for(const p of profiles){
  assert.equal(L.known(p),true,p.id);
  for(const language of ['de','en','ru']){
   const v=L.view(p,language);assert.equal(v.builtin,true);assert.equal(v.language,language);
   for(const k of ['id','version','available'])assert.equal(v.profile[k],p[k]);
   assert.equal(v.profile.persona.id,p.persona.id);assert.equal(v.profile.persona.version,p.persona.version);
   assert.equal(v.profile.scenario.source_scenario.language,p.scenario.source_scenario.language);
   assert.equal(v.profile.scenario.source_scenario.id,p.scenario.source_scenario.id);
   assert.equal(L.label(p,language),v.profile.persona.name);
   const displayed=[...['name','character','speech_style','stranger_attitude','doubt_behavior','question_style','decision_style','pressure_reaction','repeat_question_reaction','additional_behavior'].map(k=>v.profile.persona[k]),...v.profile.persona.typical_expressions,...['title','customer_name','public_brief','opening'].map(k=>v.profile.scenario.source_scenario[k]),...v.profile.scenario.source_scenario.facts.flatMap(f=>[f.label,f.value]),...Object.values(v.profile.scenario.open_questions).flatMap(f=>[f.label,f.value])].join(' ');
   if(language!=='ru')assert.ok(!/[А-Яа-яЁё]/u.test(displayed),p.id+' '+language);
   assert.equal(v.profile.scenario.source_scenario.allowed_outcomes.join(),p.scenario.source_scenario.allowed_outcomes.join());
  }
 }
 assert.equal(JSON.stringify(profiles),before,'Display does not rewrite source profiles');
 const edited=clone(profiles[0]);edited.persona.character='My authored English text';edited.content_language='en';
 for(const lang of ['de','ru']){assert.equal(L.view(edited,lang).builtin,false);assert.equal(JSON.stringify(L.view(edited,lang).profile),JSON.stringify(edited));assert.equal(L.view(edited,lang).language,'en');}
 const legacy=clone(profiles[1]);delete legacy.persona.characteristics;delete legacy.scenario.additional_information;assert.equal(L.known(legacy),true);
 const changedVersion=clone(profiles[0]);changedVersion.version++;assert.equal(L.known(changedVersion),false);
 // Execute the real locale selector: Studio handles unsaved edits without reload/confirm.
 let reloads=0,confirmations=0,transitions=0,preferences=0;const draft={text:'Ungespeicherte eigene Notiz'};
 const dictionaries=Object.fromEntries(['de','en','ru'].map(l=>[l,JSON.parse(fs.readFileSync('frontend/locales/'+l+'.json','utf8'))]));
 const i18nContext={window:{TRAINER_AUTH:{user:{locale:'de'},csrf:'synthetic'},TrainerHasUnsavedChanges:()=>true,TrainerCanChangeLocaleInPlace:()=>true,TrainerChangeLocaleInPlace:async()=>{transitions++;}},document:{documentElement:{},querySelectorAll:()=>[],getElementById:()=>({})},localStorage:{getItem:()=>null,setItem(){}},Intl,console,location:{reload(){reloads++;}},confirm:()=>{confirmations++;return false;},alert:()=>assert.fail('locale save failed'),fetch:async(url)=>{if(url==='/api/auth/preferences'){preferences++;return {ok:true};}return {ok:true,json:async()=>dictionaries[url.split('/').at(-1).replace('.json','')]};}};
 vm.createContext(i18nContext);vm.runInContext(fs.readFileSync('frontend/i18n.js','utf8'),i18nContext);await i18nContext.window.TrainerI18n.ready;
 for(const lang of ['en','ru','de'])await i18nContext.window.TrainerI18n.selectLocale(lang);
 assert.equal(reloads,0);assert.equal(confirmations,0);assert.equal(transitions,3);assert.equal(preferences,3);assert.equal(draft.text,'Ungespeicherte eigene Notiz');
 i18nContext.window.TrainerCanChangeLocaleInPlace=()=>false;await i18nContext.window.TrainerI18n.selectLocale('en');assert.equal(confirmations,1);assert.equal(preferences,3,'Other editors keep their existing unsaved-change guard');
 console.log('Persona Studio: 7 exact built-ins × DE/EN/RU, full displayed text, authored fallback, stable IDs/versions/training language; real in-place locale selector — PASS');
})().catch(e=>{console.error(e);process.exitCode=1;});
