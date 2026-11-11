"""Focused A39/A34 certificate layout, full-name snapshot and permissions checks."""
import copy
import subprocess
import unittest
from unittest.mock import patch
from . import test_learning_workflow as helpers
from backend.app.dashboard.certificate_design import render_certificate,CertificateLayoutError
from backend.app.dashboard.learning_exports import certificate_pdf


def pdf_text(data):
    return subprocess.check_output(['pdftotext','-layout','-','-'],input=data).decode()

class CertificateDesign(unittest.TestCase):
    setUp=helpers.WorkflowChecks.setUp
    tearDown=helpers.WorkflowChecks.tearDown
    attempt=helpers.WorkflowChecks.attempt
    client=helpers.WorkflowChecks.client

    def test_preview_issue_name_snapshot_access_and_legacy(self):
        sid=self.attempt();self.a.post('/api/sessions/'+sid+'/submit')
        # No AI review or published feedback is required; issuing is an independent decision.
        body={'session_id':sid,'print_name':'Marta Müller-Шевченко','topic':'Strukturierte Kundenberatung','basis':[sid],'comment':'Klar und respektvoll.','language':'de'}
        before=copy.deepcopy(self.app.state.workflow.store.get_session(sid))
        r=self.m.post('/api/mentor/learning/certificates/preview',json=body);self.assertEqual(r.status_code,200,r.text)
        draft=r.json()['certificate'];cid=draft['id'];url='/api/learning/certificates/'+cid+'.pdf'
        self.assertEqual(draft['recipient_full_name'],body['print_name']);self.assertNotIn('pdf_snapshots',draft)
        response=self.m.get(url);self.assertIn("frame-ancestors 'self'",response.headers['content-security-policy']);self.assertIn("frame-ancestors 'none'",self.m.get('/mentor').headers['content-security-policy']);preview=pdf_text(response.content);self.assertIn('ENTWURF',preview);self.assertNotIn('KKI-2026',preview);self.assertNotIn(sid,preview)
        self.assertEqual(self.a.get(url).status_code,404);self.assertEqual(self.b.get(url).status_code,404)
        self.assertEqual(self.a.post('/api/mentor/learning/certificates/'+cid+'/issue',json={'confirm':True}).status_code,403)
        self.assertEqual(self.m.post('/api/mentor/learning/certificates/'+cid+'/issue',json={'confirm':False}).status_code,422)
        issued=self.m.post('/api/mentor/learning/certificates/'+cid+'/issue',json={'confirm':True}).json()['certificate']
        self.assertEqual(issued['status'],'issued');self.assertNotIn('pdf_snapshots',issued)
        data=self.a.get(url+'?language=ru').content;text=pdf_text(data)
        self.assertIn(body['print_name'],text);self.assertIn('ZERTIFIKAT',text);self.assertNotIn('СЕРТИФИКАТ',text);self.assertNotIn('MUSTER',text);self.assertIn(issued['number'],text);self.assertNotIn(sid,text)
        self.assertEqual(self.b.get(url).status_code,404)
        with self.app.state.workflow.store.connection() as c:c.execute('UPDATE users SET display_name=? WHERE id=?',('Different account name',self.users[1]['id']))
        with patch('backend.app.dashboard.certificate_design.render_certificate',side_effect=AssertionError('Issued PDF must use frozen bytes')):
            self.assertEqual(self.a.get(url).content,data)
        self.assertEqual(self.app.state.workflow.get('certificate',cid)['recipient_full_name'],body['print_name'])
        retry=self.m.post('/api/mentor/learning/certificates/'+cid+'/issue',json={'confirm':True}).json()['certificate'];self.assertEqual(retry,issued)
        # A single account/display name cannot pass final issuance; no guessed surname.
        invalid=self.m.post('/api/mentor/learning/certificates/preview',json={**body,'print_name':'Alex'}).json()['certificate']
        self.assertEqual(self.m.post('/api/mentor/learning/certificates/'+invalid['id']+'/issue',json={'confirm':True}).status_code,422)
        count=len(self.app.state.workflow.all('certificate'))
        rejected=self.m.post('/api/mentor/learning/certificates/preview',json={**body,'comment':'Long commendation '*175})
        self.assertEqual(rejected.status_code,422);self.assertEqual(len(self.app.state.workflow.all('certificate')),count)
        # Legacy issued record stays byte-for-byte in storage and uses the old framing.
        old={**draft,'id':'legacy-certificate','status':'issued','number':'KKI-LEGACY','print_name':'Historical Name'}
        for key in ['design_version','recipient_full_name','language']:old.pop(key,None)
        self.app.state.workflow.put('certificate',old['id'],old)
        self.assertIn('Historical Name',pdf_text(self.m.get('/api/learning/certificates/legacy-certificate.pdf').content))
        self.assertEqual(self.app.state.workflow.get('certificate',old['id']),old)
        self.m.post('/api/mentor/learning/certificates/'+cid+'/revoke')
        record=self.app.state.workflow.get('certificate',cid);self.assertIn('issued',record['pdf_snapshots']);self.assertIn('revoked',record['pdf_snapshots'])
        self.assertIn('WIDERRUFEN',pdf_text(self.a.get(url).content))
        self.assertEqual(self.app.state.workflow.store.get_session(sid),before)

    def test_unicode_layout_one_page_fonts_and_safe_failure(self):
        base={'status':'draft','print_name':'Özlem Ірина Müller-Шевченко','recipient_full_name':'Özlem Ірина Müller-Шевченко','topic':'Strukturierte Kundenberatung','mentor_name':'Sergii Mentor','created_at':'2026-11-11T12:00:00+00:00','comment':'Індивідуальна відзнака · ÄÖÜ ß'}
        for language in ['de','en','ru']:
            data=render_certificate({**base,'language':language});text=pdf_text(data)
            self.assertIn(base['recipient_full_name'],text);self.assertIn(base['comment'],text)
            info=subprocess.check_output(['pdfinfo','-'],input=data).decode()
            self.assertRegex(info,r'Pages:\s+1');self.assertIn('841.89 x 595.276',info)
            fonts=subprocess.check_output(['pdffonts','-'],input=data).decode();self.assertIn('TrueType',fonts);self.assertRegex(fonts,r'yes\s+yes\s+yes')
        long={**base,'print_name':('Müller Шевченко '*8)[:120],'recipient_full_name':('Müller Шевченко '*8)[:120],'topic':('Strukturierte Kundenberatung '*9)[:240],'mentor_name':('Sergii Mentor '*9)[:120]}
        self.assertTrue(render_certificate(long).startswith(b'%PDF'))
        with self.assertRaises(CertificateLayoutError):render_certificate({**base,'comment':'X '*1500})
