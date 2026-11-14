"use strict";
// Display-only, exact-source localization. Never transforms authored/changed records.
window.TrainerPersonaLocalization=(()=>{
 const clone=x=>JSON.parse(JSON.stringify(x));let catalog=null;const builtin=new Map();
 const stable=x=>Array.isArray(x)?'['+x.map(stable).join(',')+']':x&&typeof x==='object'?'{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+stable(x[k])).join(',')+'}':JSON.stringify(x);
 function canonical(profile){const p=clone(profile);delete p.available;delete p.content_language;p.persona.characteristics??=[];p.scenario.additional_information??=[];return stable(p);}
 async function load(profiles){
  if(!catalog){const r=await fetch('/static/persona_localization.json',{cache:'no-cache',credentials:'same-origin'});if(!r.ok)throw new Error('Persona localization unavailable');catalog=await r.json();}
  builtin.clear();
  await Promise.all(profiles.map(async p=>{const value=canonical(p),bytes=new TextEncoder().encode(value),hash=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(x=>x.toString(16).padStart(2,'0')).join('');if(catalog.fingerprints[p.id]===hash)builtin.set(p.id,value);}));
 }
 function known(p){return builtin.get(p.id)===canonical(p);}
 function text(value,language){if(!value)return value;const entry=catalog?.texts[value];if(!entry||!Object.hasOwn(entry,language))throw new Error('Incomplete built-in persona localization');return entry[language];}
 function view(source,language){
  const p=clone(source);if(!known(source))return {profile:p,builtin:false,language:p.content_language||'unknown'};
  for(const key of ['name','character','speech_style','stranger_attitude','doubt_behavior','question_style','decision_style','pressure_reaction','repeat_question_reaction','additional_behavior'])p.persona[key]=text(p.persona[key],language);
  p.persona.typical_expressions=p.persona.typical_expressions.map(v=>text(v,language));
  const s=p.scenario.source_scenario;
  for(const key of ['title','customer_name','public_brief','opening'])s[key]=text(s[key],language);
  p.scenario.initial_situation=text(p.scenario.initial_situation,language);
  for(const f of s.facts)for(const k of ['label','value'])f[k]=text(f[k],language);
  for(const f of Object.values(p.scenario.open_questions))for(const k of ['label','value'])f[k]=text(f[k],language);
  // IDs, versions, fact statuses, training-language codes and Actor data stay intact.
  return {profile:p,builtin:true,language};
 }
 function label(p,language){return known(p)?text(p.persona.name,language):p.persona.name;}
 return {load,view,label,known,canonical};
})();
