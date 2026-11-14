"""A35: saved learner documents, owner isolation and no provider/record mutation."""
import copy
import json
from pathlib import Path
import unittest
from tests.dashboard import test_learning_workflow as helpers

class LearnerReviewDocuments(unittest.TestCase):
    setUp=helpers.WorkflowChecks.setUp
    client=helpers.WorkflowChecks.client
    attempt=helpers.WorkflowChecks.attempt

    def test_exports_select_only_learner_analysis_and_published_feedback(self):
        sid=self.attempt();self.a.post('/api/sessions/'+sid+'/submit')
        self.a.post('/api/learning/sessions/'+sid+'/analysis',json={})
        w=self.app.state.workflow;learner=w.get('analysis',sid+':learner')
        private=copy.deepcopy(learner);private['result']['summary']='PRIVATE MENTOR ANALYSIS MUST NOT LEAK';private['result']['sections'][0]['text']=private['result']['summary'];w.put('analysis',sid+':mentor',private)
        draft={'note':'PRIVATE DRAFT MUST NOT LEAK','goal':'partly','observations':'Historical published observation.'}
        self.m.put('/api/mentor/learning/reviews/'+sid+'/draft',json=draft)
        self.assertEqual(self.a.get(f'/api/learning/sessions/{sid}/feedback-export.txt').status_code,404)
        assessment={'stages':{'needs':'completed','capabilities':'partial','proposal':'partial'},'commercial_outcome':'deferred_decision','company_fit':'uncertain'}
        self.m.post('/api/mentor/reviews/'+sid,json={'note':'PUBLISHED HUMAN FEEDBACK','assessment':assessment})
        before=copy.deepcopy(self.app.state.store.get_session(sid));records=copy.deepcopy(w.all('analysis'));publication=copy.deepcopy(w.get('published_review',sid));context=copy.deepcopy(w.context(before));calls=len(self.analyst.calls)
        for language in ('de','en','ru'):
            for kind in ('analysis','feedback'):
                for format in ('pdf','txt'):
                    url=f'/api/learning/sessions/{sid}/{kind}-export.{format}?language={language}'
                    result=self.a.get(url);self.assertEqual(result.status_code,200)
                    self.assertIn('no-store',result.headers['Cache-Control']);self.assertIn('attachment',result.headers['Content-Disposition'])
                    if format=='pdf':self.assertTrue(result.content.startswith(b'%PDF'))
                    else:
                        self.assertNotIn('PRIVATE MENTOR ANALYSIS',result.text);self.assertNotIn('PRIVATE DRAFT',result.text)
                        if kind=='analysis':self.assertIn('No order confirmed.',result.text);self.assertNotIn('PUBLISHED HUMAN FEEDBACK',result.text)
                        else:
                            self.assertIn('PUBLISHED HUMAN FEEDBACK',result.text);self.assertIn('Historical published observation.',result.text)
                            labels=json.loads((Path(__file__).resolve().parents[2]/'frontend/locales'/f'{language}.json').read_text())
                            self.assertLess(result.text.index(labels['review22.needs']),result.text.index('PUBLISHED HUMAN FEEDBACK'))
                            self.assertLess(result.text.index(labels['review.commercial']),result.text.index('PUBLISHED HUMAN FEEDBACK'))
                    self.assertEqual(self.b.get(url).status_code,404)
        query=self.a.get(f'/api/learning/sessions/{sid}/analysis-export.txt?audience=mentor').text
        self.assertNotIn('PRIVATE MENTOR ANALYSIS',query)
        self.assertEqual(self.a.get(f'/api/mentor/learning/reviews/{sid}/analysis-export.txt').status_code,403)
        self.assertEqual(self.app.state.store.get_session(sid),before);self.assertEqual(w.all('analysis'),records);self.assertEqual(w.get('published_review',sid),publication);self.assertEqual(w.context(before),context);self.assertEqual(len(self.analyst.calls),calls);self.assertEqual(w.all('review_read'),[])

    def test_legacy_failed_refresh_is_exported_without_backfill_or_private_fallback(self):
        sid=self.attempt();self.a.post('/api/learning/sessions/'+sid+'/analysis',json={});w=self.app.state.workflow
        record=w.get('analysis',sid+':learner');record['result'].pop('recommendation');record['attempt_status']='error';w.put('analysis',sid+':learner',record)
        before=copy.deepcopy(record);calls=len(self.analyst.calls)
        for format in ('txt','pdf'):self.assertEqual(self.a.get(f'/api/learning/sessions/{sid}/analysis-export.{format}').status_code,200)
        self.assertEqual(w.get('analysis',sid+':learner'),before);self.assertEqual(len(self.analyst.calls),calls)
        self.assertEqual(self.a.get(f'/api/learning/sessions/{sid}/analysis-export.json').status_code,404)
        missing=self.attempt();w.put('analysis',missing+':mentor',copy.deepcopy(record))
        self.assertEqual(self.a.get(f'/api/learning/sessions/{missing}/analysis-export.txt').status_code,404)
        self.assertEqual(self.a.get(f'/api/learning/sessions/{missing}/feedback-export.txt').status_code,404)
