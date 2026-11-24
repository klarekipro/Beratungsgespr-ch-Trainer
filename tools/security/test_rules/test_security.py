import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/'run.py'
spec=importlib.util.spec_from_file_location('jsc_security',SCRIPT)
R=importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)
TOOLS=Path(os.environ['JSC_SECURITY_TOOLS'])

class SecurityTests(unittest.TestCase):
    def test_report_drops_secret_snippet_and_messages(self):
        raw={'Secret':'NEVER-PUBLISH-THIS','Match':'NEVER-PUBLISH-THIS','message':'NEVER-PUBLISH-THIS',
             'RuleID':'synthetic-rule','File':'example.py','StartLine':3}
        safe=R.finding(raw['RuleID'],raw['File'],raw['StartLine'],'HIGH')
        self.assertNotIn('NEVER-PUBLISH-THIS',json.dumps(safe))
        self.assertEqual(set(safe),{'rule','file','line','severity','fingerprint'})

    def test_full_history_secret_positive_and_negative(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp)
            def git(*args):
                subprocess.run(['git','-c','core.hooksPath=/dev/null','-C',str(tmp),*args],check=True,capture_output=True)
            git('init','-q'); git('config','user.name','Synthetic fixture'); git('config','user.email','fixture@example.invalid')
            (tmp/'safe.txt').write_text('synthetic fixture\n')
            git('add','.'); git('commit','-qm','safe')
            report=tmp/'report.json'
            command=[str(R.tool(TOOLS,'gitleaks')),'git','--no-banner','--redact=100','--config',str(R.CONFIG/'gitleaks.toml'),
                     '--report-format','json','--report-path',str(report),str(tmp)]
            p=subprocess.run(command,capture_output=True)
            self.assertEqual(p.returncode,0)
            # Construct a non-functional synthetic credential at runtime; do not commit a fake token into this repo.
            (tmp/'leak.txt').write_text('postgres'+'ql://synthetic:long-'+'synthetic-fixture@db.example.invalid/test\n')
            git('add','leak.txt'); git('commit','-qm','synthetic positive')
            (tmp/'leak.txt').unlink(); git('add','-u'); git('commit','-qm','remove current file')
            p=subprocess.run(command,capture_output=True)
            self.assertEqual(p.returncode,1,'a removed historical credential must still be detected')
            self.assertTrue(any(x['RuleID']=='jsc-postgres-credential' for x in json.loads(report.read_text())))

    def test_sast_inline_positive_and_sanitized_negative(self):
        lock=R.read(R.CONFIG/'tools.lock.json')
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp); source=tmp/'source'; source.mkdir()
            (source/'positive.js').write_text('document.body.innerHTML = location.hash;\neval(location.search);\nconsole.error(env.NEON_URL);\nconst query = "SELECT " + userInput;\n')
            (source/'safe.js').write_text('document.body.textContent = location.hash;\nconst query = "SELECT " + "1";\n')
            (source/'positive.py').write_text('import subprocess\nsubprocess.run(user_input, shell=True)\neval(user_input)\n')
            p=R.docker(lock['images']['semgrep'],['semgrep','scan','--oss-only','--metrics=off','--disable-version-check','--strict','--error',
                '--json','--config','/config/semgrep.yml','--output','/report/result.json','/work'],
                [(source,'/work',False),(R.CONFIG,'/config',False),(tmp,'/report',True)],timeout=300)
            self.assertEqual(p.returncode,1)
            report=R.read(tmp/'result.json')
            self.assertFalse(report['errors'])
            paths={Path(x['path']).name for x in report['results']}
            self.assertIn('positive.js',paths); self.assertIn('positive.py',paths); self.assertNotIn('safe.js',paths)
            ids={x['check_id'].split('.')[-1] for x in report['results']}
            self.assertEqual(ids,{'jsc-python-shell-injection','jsc-python-code-evaluation','jsc-js-browser-input-to-html',
                                 'jsc-js-browser-input-to-eval','jsc-js-secret-logging','jsc-js-dynamic-sql'})

    def test_missing_check_cannot_pass_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(R.gate(Path(tmp)),'NOT VERIFIED')

    def test_unsafe_workflow_and_invalid_yaml_are_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp);p=tmp/'unsafe.yml'
            p.write_text('name: unsafe\non: pull_request_target\npermissions: write-all\njobs:\n  bad:\n    runs-on: ubuntu-24.04\n    steps:\n      - uses: actions/checkout@main\n        with:\n          ref: ${{ github.event.pull_request.head.sha }}\n')
            result=subprocess.run([str(R.tool(TOOLS,'zizmor')),'--offline','--strict-collection','--format=json',str(p)],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertTrue(json.loads(result.stdout))
            p.write_text('name: [invalid\n')
            result=subprocess.run([str(R.tool(TOOLS,'actionlint')),'-shellcheck=','-pyflakes=',str(p)],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)

    def test_receipts_reject_missing_stale_changed_and_blocked_results(self):
        import datetime as dt
        now=dt.datetime.now(dt.timezone.utc)
        receipt={'schema':2,'check':'tests','input_sha256':'abc','status':'FAIL','execution':'executed',
                 'commit':'synthetic','time':now.isoformat(),'findings':[]}
        self.assertTrue(R.reusable(receipt,'tests','abc',now))  # FAIL remains FAIL when reused.
        self.assertFalse(R.reusable(receipt,'tests','changed',now))
        self.assertFalse(R.reusable(dict(receipt,status='BLOCKED'),'tests','abc',now))
        self.assertFalse(R.reusable(dict(receipt,execution='skipped'),'tests','abc',now))
        self.assertFalse(R.reusable(dict(receipt,time=(now-dt.timedelta(days=8)).isoformat()),'tests','abc',now))

    def test_gate_distinguishes_failure_blocked_and_missing(self):
        ids=R.identities()
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp)
            for check in R.CHECKS:
                (tmp/(check+'.json')).write_text(json.dumps({'schema':2,'check':check,'status':'PASS','input_sha256':ids[check],'execution':'executed','commit':'synthetic','time':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),'findings':[]}))
            self.assertEqual(R.gate(tmp),'PASS')
            (tmp/'tests.json').write_text(json.dumps({'status':'BLOCKED','input_sha256':ids['tests']}))
            self.assertEqual(R.gate(tmp),'BLOCKED')
            (tmp/'secrets.json').write_text(json.dumps({'schema':2,'check':'secrets','status':'FAIL','input_sha256':ids['secrets'],'execution':'executed','commit':'synthetic','time':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),'findings':[]}))
            self.assertEqual(R.gate(tmp),'FAIL')

    def test_input_selection_ignores_docs_for_sast_tests_and_workflows(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp)
            for name,value in {'backend/app.js':'const safe = 1;', 'docs/guide.md':'first', '.github/workflows/ci.yml':'name: first',
                               'tools/security/run.py':'engine', '.security/tools.lock.json':'{}'}.items():
                p=tmp/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(value)
            subprocess.run(['git','init','-q',str(tmp)],check=True,capture_output=True)
            subprocess.run(['git','-C',str(tmp),'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','-c','core.hooksPath=/dev/null','commit','--allow-empty','-qm','synthetic fixture'],check=True,capture_output=True)
            original_root,original_config=R.ROOT,R.CONFIG
            try:
                R.ROOT,R.CONFIG=tmp,tmp/'.security'
                with patch.object(R,'execute',side_effect=lambda args,**kw: subprocess.run(args,cwd=tmp,capture_output=True,text=True)), patch.object(R,'tracked_sources',return_value=['backend/app.js','docs/guide.md','.github/workflows/ci.yml','tools/security/run.py','.security/tools.lock.json']):
                    before=R.identities()
                    (tmp/'docs/guide.md').write_text('changed documentation')
                    self.assertEqual(before,R.identities())
                    (tmp/'backend/app.js').write_text('const safe = 2;')
                    after=R.identities()
                    self.assertNotEqual(before['sast'],after['sast'])
                    self.assertEqual(before['workflows'],after['workflows'])
                    (tmp/'.github/workflows/ci.yml').write_text('name: changed')
                    self.assertNotEqual(after['workflows'],R.identities()['workflows'])
            finally:
                R.ROOT,R.CONFIG=original_root,original_config

    def test_container_uses_host_uid_and_private_mount_permissions(self):
        lock=R.read(R.CONFIG/'tools.lock.json')
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp);tmp.chmod(0o700)
            (tmp/'synthetic.txt').write_text('synthetic fixture')
            command=['python3','-c', 'import os,pathlib; assert os.geteuid()=='+str(os.getuid())+'; p=pathlib.Path("/work/synthetic.txt"); assert p.read_text()=="synthetic fixture"; pathlib.Path("/work/result.txt").write_text("PASS")']
            result=R.docker(lock['images']['semgrep'],command,[(tmp,'/work',True)])
            self.assertEqual(result.returncode,0,'private mounts must work without root capabilities')
            self.assertEqual((tmp/'result.txt').read_text(),'PASS')


if __name__=='__main__':
    unittest.main()
