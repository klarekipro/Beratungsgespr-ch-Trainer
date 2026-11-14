const {test}=require('node:test');
const assert=require('node:assert/strict');
const {readFileSync}=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const window={TrainerI18n:{t:()=> 'Document'}};
vm.runInNewContext(readFileSync(path.resolve(__dirname,'../../frontend/presentation.js'),'utf8'),{window});
const {documentTitle,publicNotes}=window.TrainerPresentation;
test('document labels retain meaningful names and hide machine filenames without altering source metadata',()=>{
 const source=Object.freeze({name:'/private/tmp/Lindenhaus_A16_Import_v1_20261110_155000.md',source_id:'source-original',text:'Original contents'});
 assert.equal(documentTitle(source.name,'Company information'),'Company information');
 assert.equal(source.name,'/private/tmp/Lindenhaus_A16_Import_v1_20261110_155000.md');
 assert.equal(source.source_id,'source-original');
 assert.equal(documentTitle('02_Servicebedingungen_Lindenhaus.pdf'),'Servicebedingungen Lindenhaus');
 assert.equal(documentTitle('Warranty terms 2026'),'Warranty terms 2026');
 assert.equal(documentTitle('invoice_9b9f2321345abcde.pdf','Delivery terms'),'Delivery terms');
});
test('public report guidance retains useful caveats while implementation notes stay in the original array',()=>{
 const items=Object.freeze(['simple_actor: 2 ответов одного OpenAI Actor; LLM-Verifier нет.','Фактических API-запросов: 2;','Карточки компании и клиента закреплены в начале попытки.','В беседе были ограничения сценария или ошибки системы.','Технические ошибки не засчитываются как ошибки ученика.']);
 assert.deepEqual(Array.from(publicNotes(items)),Array.from(items.slice(2)));
 assert.equal(items.length,5);
});
