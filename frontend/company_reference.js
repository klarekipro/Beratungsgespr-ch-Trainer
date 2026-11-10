"use strict";
window.createCompanyReference=({state,api,esc:E})=>{
 let current=null,source=null,preview=null;
 const language=()=>window.TRAINER_AUTH.user.locale||'de';
 const t=k=>window.TrainerI18n.t('company17.'+k);
 const purposeNames={description:'company_description',products:'product_catalogue',services:'service_prices',policy:'internal_rules',terms:'service_conditions'};
 const money=p=>p===null||p===undefined||p===''?t('unknown'):new Intl.NumberFormat(language(),{style:'currency',currency:'EUR'}).format(Number(p));
 async function load(){current=await api('/api/company-reference');}
 function productList(products){return `<div class="reference-products">${products.map(p=>`<details class="reference-product" data-category="${E(p.category)}"><summary><span><strong>${E(p.name)}</strong><small>${E(p.category)}${p.article||!p.id?.startsWith('item_')?' · '+E(p.article||p.id):''}</small></span><strong>${money(p.price_eur)}</strong><span class="product-difference">${E(p.features)}</span></summary><div class="reference-detail">${p.original_language?`<p class="caption">${t('original_language')}: ${E(p.original_language.toUpperCase())}${p.original_language!==language()?' · '+t('missing_translation'):''}</p>`:''}<p>${E(p.features)}</p><p>${E(p.price_includes)}</p><p>${E(p.availability||t('availability_unknown'))}</p><p>${E(p.promotion||'')}</p>${p.valid_until?`<p>${E(p.valid_until)}</p>`:''}</div></details>`).join('')}</div>`;}
 function servicesTable(services){return `<div class="table-wrap"><table class="data-table reference-table"><thead><tr><th>${t('service')}</th><th>${t('price')}</th><th>${t('included')}</th></tr></thead><tbody>${services.map(s=>`<tr><td>${E(s.title||s.name)}${s.original_language?`<small class="reference-language">${t('original_language')}: ${E(s.original_language.toUpperCase())}${s.original_language!==language()?' · '+t('missing_translation'):''}</small>`:''}</td><td>${money(s.price_eur)}</td><td>${E(s.id==='repair'?t('repair_scope'):s.description)}<details><summary>${t('more')}</summary><p>${E(s.conditions)}</p></details></td></tr>`).join('')}</tbody></table></div>`;}
 function docs(d){return `${d.documents.map(x=>`<details class="reference-document"><summary>${E(window.TrainerPresentation.documentTitle(x.title))}</summary>${x.notice?`<p class="caption">${E(x.notice)}</p>`:''}${x.source_id?`<a class="btn" target="_blank" rel="noopener" href="/api/company-documents/${E(x.source_id)}/original">${t('original')}</a>`:''}<div class="reference-prose">${E(x.text)}</div></details>`).join('')}<details class="reference-document"><summary>${t('service_prices')} · CSV</summary>${servicesTable(d.services)}</details><details class="reference-document"><summary>${t('product_catalogue')} · CSV</summary>${productList(d.products)}</details>`;}
 function body(d,key){
  const noticeKey={about:'description',products:'products',services:'services',terms:'terms',documents:'policy'}[key];
  const notice=d.notices?.[noticeKey]?`<p class="notice neutral">${E(d.notices[noticeKey])}</p>`:'';
  return notice+sectionBody(d,key);
 }
 function sectionBody(d,key){
  if(key==='about')return `<h2>${t('about')}</h2><p>${E(d.about)}</p><p class="caption">${t('fictional')}</p>`;
  if(key==='products'&&!d.products.length)return `<h2>${t('products')}</h2><p class="reference-empty">${t('empty_products')}</p>`;
  if(key==='products')return `<h2>${t('products')} <span class="caption">${d.products.length}</span></h2><div class="reference-filters"><label>${t('search')}<input type="search" class="reference-search" placeholder="${t('search')}"></label><label>${t('category')}<select class="reference-category"><option value="">${t('all')}</option>${[...new Set(d.products.map(p=>p.category))].map(c=>`<option>${E(c)}</option>`).join('')}</select></label></div><p class="caption reference-count" aria-live="polite">${d.products.length}</p>${productList(d.products)}`;
  if(key==='services')return `<h2>${t('service_prices')} <span class="caption">${d.services.length}</span></h2>${servicesTable(d.services)}`;
  if(key==='terms')return `<h2>${t('terms')}</h2>${d.terms.map(([title,text])=>`<details class="reference-document"><summary>${E(title)}</summary><p>${E(text)}</p></details>`).join('')}`;
  return `<h2>${t('documents')}</h2>${docs(d)}`;
 }
 let serial=0;const bundles=new Map();
 function reference(d,compact=false){const id=String(++serial);bundles.set(id,d);return `<section class="company-reference card card-pad ${compact?'reference-in-chat':''}" data-reference-id="${id}"><h1>${E(d.name)}</h1><p>${E(d.tagline||d.about)}</p><nav class="reference-nav" aria-label="${t('documents')}">${['about','products','services','terms','documents'].map((k,i)=>`<button type="button" class="btn ${i===0?'primary':''}" data-reference-tab="${k}" aria-pressed="${i===0}">${t(k)}</button>`).join('')}</nav><div class="reference-content">${body(d,'about')}</div></section>`;}
 function genericData(m,c){
  const oldItems=m?.import_items||{};
  const services=(c?.services||[]).map(s=>{
   const imported=oldItems.services?.[s.id],match=s.conditions.match(/(?:Preis|Price|Цена)?\s*:?\s*(\d+(?:[.,]\d+)?)\s*(?:EUR|€)/i);
   return {...s,price_eur:imported?imported.price_eur:(match?Number(match[1].replace(',','.')):null),original_language:imported?.original_language||'de'};
  });
  const langNotice=l=>`${t('original_language')}: ${l.toUpperCase()}${l!==language()?' · '+t('missing_translation'):''}`;
  const notices=Object.fromEntries(['description','products','services','policy','terms'].map(k=>[k,langNotice(m?.source_languages?.[k]||'de')]));
  const textDocs=(m?.documents||[]).map(d=>({title:window.TrainerPresentation.documentTitle(d.name,t(purposeNames[d.purpose])),text:d.text,notice:langNotice(d.language),source_id:d.source_id}));
  const conditions=(m?.documents||[]).filter(d=>['policy','terms'].includes(d.purpose));
  const d={name:c?.name||'',tagline:t('original_language')+': '+(m?.original_language||'de').toUpperCase(),about:c?.description||'',products:m?.products||[],services,terms:conditions.length?conditions.map(d=>[t(purposeNames[d.purpose])+' · '+langNotice(d.language),d.text]):[[t('terms'),c?.limitations||'']],documents:[{title:t('about'),text:c?.description||'',notice:notices.description},...textDocs],notices};
  return d;
 }
 function generic(m,c){return reference(genericData(m,c));}
 function snapshotData(m,c){return m?.translations?.[language()]||{...genericData(m,c),no_catalogue:!m};}

 function page(){return current?.reference?reference(current.reference):generic(current?.materials,state.company);}
 function snapshot(m,c){
  const d=m?.translations?.[language()];
  if(!d&&!c)return null;
  return `<details class="reference-snapshot card card-pad"><summary>${window.TrainerI18n.t('learning.saved_materials')}<small>${window.TrainerI18n.t('learning.saved_materials_hint')}</small></summary>${d?reference(d,true):generic(m,c)}</details>`;
 }

 function importer(){return `<details class="card card-pad report-section company-import"><summary>${window.TrainerI18n.t('learning.import')}</summary><p>MD / TXT · CSV / XLSX · PDF (text)</p><label>${t('purpose')}<select id="company-import-purpose">${Object.entries(purposeNames).map(([v,k])=>`<option value="${v}">${t(k)}</option>`).join('')}</select></label><label>${t('original_language')}<select id="company-import-language"><option value="de">Deutsch</option><option value="en">English</option><option value="ru">Русский</option></select></label><input id="company-import-file" type="file" accept=".md,.markdown,.txt,.csv,.xlsx,.pdf"><p role="status" id="company-import-status"></p><div id="company-import-work"></div></details>${page()}`;}
 function invalidate(){preview=null;document.getElementById('company-import-preview')?.replaceChildren();}
 function work(){const fields=['id','name','price_eur','unit','description','conditions','category','features','price_includes','availability','promotion','valid_until'];return `<a class="btn" target="_blank" rel="noopener" href="/api/company-documents/${E(source.id)}/original">${t('original')} · ${E(window.TrainerPresentation.documentTitle(source.name,t(purposeNames[document.getElementById('company-import-purpose').value])))}</a><details><summary>${window.TrainerI18n.t('clean.technical')}</summary><p>${E(source.name)}</p></details><details><summary>${t('original')}</summary><pre class="reference-prose">${E(source.text)}</pre></details><p>${E(source.warnings.join('\n'))}</p>${source.headers.length?`<h3>${t('mapping')}</h3><div class="import-mapping">${fields.map(f=>`<label>${E(({name:t('products')+' / '+t('service'),price_eur:t('price'),unit:t('unit'),description:t('description'),conditions:t('terms'),category:t('category'),features:t('features'),availability:t('availability'),price_includes:t('price_includes'),promotion:t('promotion'),valid_until:t('valid_until')})[f]||f)}<select data-map-field="${f}"><option value="">${t('unmapped')}</option>${source.headers.map(h=>`<option value="${E(h)}" ${source.mapping[f]===h?'selected':''}>${E(h)}</option>`).join('')}</select></label>`).join('')}</div><p>${t('edit')}</p><div class="table-wrap"><table class="data-table"><thead><tr>${source.headers.map(h=>`<th>${E(h)}</th>`).join('')}</tr></thead><tbody>${source.rows.map((r,i)=>`<tr>${source.headers.map(h=>`<td><input data-import-row="${i}" data-import-col="${E(h)}" value="${E(r[h]||'')}"></td>`).join('')}</tr>`).join('')}</tbody></table></div>`:`<label>${t('company_name')}<input id="company-import-name" value="${E(state.company?.name||'')}"></label><label>${t('edit')}<textarea id="company-import-text" rows="12">${E(source.text)}</textarea></label>`}<button type="button" class="btn primary" id="company-import-preview-button">${t('preview')}</button><div id="company-import-preview"></div>`;}
 document.addEventListener('click',async e=>{
  const tab=e.target.closest('[data-reference-tab]');if(tab){const container=tab.closest('[data-reference-id]'),d=bundles.get(container.dataset.referenceId);container.querySelector('.reference-content').innerHTML=body(d,tab.dataset.referenceTab);container.querySelectorAll('[data-reference-tab]').forEach(b=>{b.classList.toggle('primary',b===tab);b.setAttribute('aria-pressed',String(b===tab));});return;}
  if(e.target.id==='company-import-preview-button'){
   const mapping=Object.fromEntries([...document.querySelectorAll('[data-map-field]')].filter(s=>s.value).map(s=>[s.dataset.mapField,s.value]));const rows=structuredClone(source.rows);document.querySelectorAll('[data-import-row]').forEach(el=>rows[Number(el.dataset.importRow)][el.dataset.importCol]=el.value);
   try{preview=(await api('/api/mentor/company-documents/preview',{method:'POST',body:{source_id:source.id,company_name:document.getElementById('company-import-name')?.value||'',purpose:document.getElementById('company-import-purpose').value,language:document.getElementById('company-import-language').value,mapping,rows,text:document.getElementById('company-import-text')?.value||''}})).preview;
    document.getElementById('company-import-preview').innerHTML=`<h3>${t('preview')}</h3><p role="alert">${E(preview.errors.join('\n'))}</p><p>${t('review')}: ${E(preview.warnings.join('\n'))}</p><ul>${preview.changes.map(c=>`<li>${t(c.action)}: ${E(c.name)}</li>`).join('')}</ul><pre class="reference-prose">${E(preview.items.length?JSON.stringify(preview.items,null,2):preview.text)}</pre>${preview.errors.length?'':`<label><input type="checkbox" id="company-import-confirm">${t('confirm')}</label><button class="btn primary" id="company-import-apply">${t('apply')}</button>`}`;
   }catch(error){document.getElementById('company-import-status').textContent=error.message;}
  }
  if(e.target.id==='company-import-apply'){
   if(!document.getElementById('company-import-confirm').checked)return;
   e.target.disabled=true;try{await api('/api/mentor/company-documents/apply',{method:'POST',body:{preview_id:preview.id,confirm:true}});preview=null;location.reload();}catch(error){document.getElementById('company-import-status').textContent=error.message;e.target.disabled=false;}
  }
 });
 document.addEventListener('change',async e=>{
  if(e.target.id==='company-import-file'&&e.target.files[0]){const file=e.target.files[0];if(file.size>10000000){document.getElementById('company-import-status').textContent='Maximum 10 MB';return;}const status=document.getElementById('company-import-status');status.textContent=t('extracting');preview=null;source=null;document.getElementById('company-import-work').replaceChildren();try{const bytes=new Uint8Array(await file.arrayBuffer());let binary='';for(let i=0;i<bytes.length;i+=8192)binary+=String.fromCharCode(...bytes.subarray(i,i+8192));source=(await api('/api/mentor/company-documents/extract',{method:'POST',body:{name:file.name,content:btoa(binary)}})).source;document.getElementById('company-import-work').innerHTML=work();status.textContent='';}catch(error){status.textContent=error.message;}}
  if(e.target.matches('[data-map-field],#company-import-purpose,#company-import-language'))invalidate();
  if(e.target.matches('.reference-category'))filter(e.target);
 });
 function filter(el){const box=el.closest('.company-reference'),q=box.querySelector('.reference-search').value.toLocaleLowerCase(),category=box.querySelector('.reference-category').value;let n=0;box.querySelectorAll('.reference-content .reference-product').forEach(p=>{p.hidden=!(p.textContent.toLocaleLowerCase().includes(q)&&(!category||p.dataset.category===category));if(!p.hidden)n++;});box.querySelector('.reference-count').textContent=String(n);}
 document.addEventListener('input',e=>{if(e.target.matches('.reference-search'))filter(e.target);if(e.target.matches('[data-import-row],#company-import-text,#company-import-name'))invalidate();});
 return {load,page,snapshot,importer,snapshotData};
};
