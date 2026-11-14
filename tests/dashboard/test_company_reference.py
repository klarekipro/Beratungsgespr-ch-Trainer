"""Focused A17 contracts: translations, local extraction and reviewed publication."""
import base64,copy,io,json,re,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app.dashboard.company_reference import REFERENCES,SOURCE_COMPANY,canonical_company,extract,initial_materials
from backend.app.dashboard.server import create_app
from backend.app.dashboard.workflow import Workflow
from backend.app.dashboard.auth import COOKIE

class CompanyReference(unittest.TestCase):
    def test_locales_preserve_prices_dimensions_and_service_links(self):
        source=list(__import__('csv').DictReader(io.StringIO(Path('materials/lindenhaus/products.csv').read_text())))
        for lang,d in REFERENCES.items():
            self.assertEqual(len(d['products']),18);self.assertEqual(len(d['services']),9)
            self.assertEqual([p['id'] for p in source],[p['id'] for p in d['products']])
            for old,new in zip(source,d['products']):
                self.assertEqual(old['price_eur'],new['price_eur'])
                self.assertEqual(re.findall(r'\d+(?:\.\d+)?',old['features']),re.findall(r'\d+(?:\.\d+)?',new['features']))
            self.assertTrue(all(str(s['price_eur'])+' EUR' in __import__('backend.app.dashboard.company_reference',fromlist=['service_record']).service_record(s,lang)['conditions'] for s in d['services'] if s['price_eur'] is not None))
            self.assertEqual([s['price_eur'] for s in d['services']],[49,99,129,69,59,29,59,90,None])
            self.assertEqual([s['id'] for s in d['services']],['lh_sv_01','replacement','lh_sv_03','lh_sv_04','lh_sv_05','lh_sv_06','lh_sv_07','diagnosis','repair'])
            self.assertEqual(re.findall(r'\d+(?:\.\d+)?',str(d['terms'])),re.findall(r'\d+(?:\.\d+)?',str(REFERENCES['de']['terms'])))
    def test_extraction_is_bounded_and_empty_pdf_is_not_success(self):
        self.assertEqual(extract('rules.txt','Правила предприятия'.encode())[0],'Правила предприятия')
        self.assertEqual(extract('prices.md',b'| Name | Preis |\n| --- | --- |\n| Lieferung | 49 |')[1],[{'Name':'Lieferung','Preis':'49'}])
        self.assertEqual(len(extract('prices.csv',b'Name;Preis\nLieferung;49\n')[1]),1)
        data=io.BytesIO()
        with zipfile.ZipFile(data,'w') as z:
            z.writestr('xl/workbook.xml','<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Prices" r:id="r1"/></sheets></workbook>')
            z.writestr('xl/_rels/workbook.xml.rels','<Relationships><Relationship Id="r1" Target="worksheets/sheet1.xml"/></Relationships>')
            z.writestr('xl/worksheets/sheet1.xml','<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row><c r="A1" t="inlineStr"><is><t>Name</t></is></c><c r="B1" t="inlineStr"><is><t>Preis</t></is></c></row><row><c r="A2" t="inlineStr"><is><t>Delivery</t></is></c><c r="B2"><v>49</v></c></row></sheetData></worksheet>')
        self.assertEqual(extract('prices.xlsx',data.getvalue())[1],[{'Name':'Delivery','Preis':'49'}])
        from reportlab.pdfgen.canvas import Canvas
        pdf=io.BytesIO();c=Canvas(pdf);c.drawString(20,800,'Lindenhaus service conditions');c.save()
        self.assertIn('Lindenhaus',extract('rules.pdf',pdf.getvalue())[0])
        blank=io.BytesIO();c=Canvas(blank);c.showPage();c.save()
        with self.assertRaises(__import__('fastapi').HTTPException):extract('scan.pdf',blank.getvalue())
    def test_reviewed_import_updates_company_and_preserves_old_snapshots(self):
        with tempfile.TemporaryDirectory() as tmp,patch.dict('os.environ',{'OPENAI_API_KEY':''}):
            app=create_app(Path(tmp)/'test.sqlite3');a=app.state.auth;store=app.state.store;w=Workflow(store)
            store.save_company(canonical_company());m=initial_materials({'id':'old','products':REFERENCES['de']['products']});w.put('materials','current',m)
            old_snapshot={'materials':copy.deepcopy(m),'company':copy.deepcopy(store.get_company())};w.put('snapshot','old-session',old_snapshot)
            u=a.create_user('a17-mentor','Mentor','A17-test-password',role='mentor_admin',temporary=False);token,csrf=a.issue(u['id'])
            with TestClient(app,headers={'Origin':'http://testserver','X-CSRF-Token':csrf},cookies={COOKIE:token}) as client:
                raw=b'Name,Preis,Description,Terms\nLieferung,49,Transport,Per order\nRepair,,Agreed scope,Quotation required\n'
                r=client.post('/api/mentor/company-documents/extract',json={'name':'prices.csv','content':base64.b64encode(raw).decode()});self.assertEqual(r.status_code,200,r.text);src=r.json()['source']
                body={'source_id':src['id'],'purpose':'services','language':'en','mapping':{'name':'Name','price_eur':'Preis','description':'Description','conditions':'Terms'},'rows':src['rows'],'text':''}
                p=client.post('/api/mentor/company-documents/preview',json=body).json()['preview'];self.assertFalse(p['errors']);self.assertEqual(p['items'][1]['price_eur'],None)
                self.assertEqual(store.get_company(),old_snapshot['company'])
                self.assertEqual(client.post('/api/mentor/company-documents/apply',json={'preview_id':p['id']}).status_code,422)
                r=client.post('/api/mentor/company-documents/apply',json={'preview_id':p['id'],'confirm':True});self.assertEqual(r.status_code,200,r.text)
                after=store.get_company();self.assertEqual(len(after['services']),9);self.assertEqual(next(s for s in after['services'] if s['id']=='lh_sv_01')['description'],'Transport')
                p2=client.post('/api/mentor/company-documents/preview',json=body).json()['preview'];self.assertTrue(all(c['action']=='unchanged' for c in p2['changes']))
                self.assertEqual(client.post('/api/mentor/company-documents/apply',json={'preview_id':p2['id'],'confirm':True}).status_code,200)
                self.assertEqual(len(store.get_company()['services']),9)
                self.assertEqual(w.get('snapshot','old-session'),old_snapshot)
                a.set_locale(u['id'],'ru');ref=client.get('/api/company-reference').json();self.assertIsNone(ref['reference']);self.assertEqual(ref['materials']['documents'][0]['language'],'en');self.assertEqual(ref['materials']['documents'][0]['translations'],{})
