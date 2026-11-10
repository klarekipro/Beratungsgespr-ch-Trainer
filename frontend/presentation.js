"use strict";
/* Display helpers only: never rewrite stored documents or exported data. */
window.TrainerPresentation=(()=>{
 function documentTitle(value,fallback=window.TrainerI18n.t('clean.document')){
  const leaf=String(value||'').split(/[\\/]/).pop()||'';
  if(!leaf.trim())return fallback;
  if(/(?:[a-f0-9]{16,}|\bSHA[-_]?256\b|_[vV]\d+(?:[_ .]|$)|_A\d+_Import|\d{8}[_-]\d{6})/i.test(leaf))return fallback;
  return leaf.replace(/\.(?:md|markdown|txt|csv|xlsx|pdf|json)$/i,'').replace(/^\d{1,3}[_-](?=\D)/,'').replace(/_+/g,' ').replace(/\s+/g,' ').trim()||fallback;
 }
 function publicNotes(items){
  return (items||[]).filter(item=>!/(?:simple_actor|OpenAI|LLM[- ]?Verifier|\bAPI\b|Responses|Ответов прежней версии|Технический сценарный режим|Traceback|SHA[-_]?256|git_commit|\/Users\/|\/private\/)/i.test(String(item)));
 }
 return {documentTitle,publicNotes};
})();
