"""Operational acceptance with real temporary Git repos and isolated HTTP processes.

No real OpenAI key, Keychain entry or production port is used in this test module.
The miniature HTTP fixture tests release/rollback mechanics, not AI behavior.
"""
from pathlib import Path
import importlib.util
from contextlib import closing
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('trainer_ops',ROOT/'scripts/local_installation.py')
ops=importlib.util.module_from_spec(spec);spec.loader.exec_module(ops)

class FakeKeychain:
    def __init__(self):self.calls=0
    def get(self):self.calls+=1;return b'synthetic-no-network-key'
    def prompt(self):raise AssertionError('Unexpected credential prompt')

SERVER=r'''
import argparse,os,json,subprocess,hashlib,sys
from pathlib import Path
from http.server import HTTPServer,BaseHTTPRequestHandler
p=argparse.ArgumentParser();p.add_argument('--port',type=int);p.add_argument('--openai',action='store_true');p.add_argument('--data-dir');a=p.parse_args()
root=Path(__file__).resolve().parents[1]
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
rt={'python':sys.executable,'data_path':str(Path(a.data_dir)/'trainer.sqlite3'),'pid':os.getpid(),'git_commit':head,'server_module':str(root/'backend/app/dashboard/server.py'),
'customer_actor_module':str(root/'backend/app/dashboard/customer_actor.py'),
'customer_actor_sha256':hashlib.sha256((root/'backend/app/dashboard/customer_actor.py').read_bytes()).hexdigest(),
'response_planning_sha256':hashlib.sha256((root/'backend/app/dashboard/response_planning.py').read_bytes()).hexdigest()}
class H(BaseHTTPRequestHandler):
 def do_GET(self):
  self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps({'version':'fixture','runtime':rt,'ai':{'configured':bool(os.getenv('OPENAI_API_KEY'))}}).encode())
 def log_message(self,*args):pass
HTTPServer(('127.0.0.1',a.port),H).serve_forever()
'''

class LocalInstallationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='trainer-ops-test-');self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name);self.root=self.base/'project';self.root.mkdir()
        for folder in ['scripts','backend/app/dashboard','frontend','tests/dashboard']:(self.root/folder).mkdir(parents=True)
        (self.root/'.gitignore').write_text('.venv/\nruntime/\n__pycache__/\nfuture-user-data.txt\n')
        (self.root/'scripts/serve_dashboard.py').write_text(SERVER)
        shutil.copy2(ROOT/'scripts/run_installed_dashboard.py',self.root/'scripts/run_installed_dashboard.py')
        (self.root/'scripts/local_installation.py').write_text('# fixture control-plane file\n')
        for name in ['START_TRAINER.command','STOP_TRAINER.command','UPDATE_TRAINER.command']:(self.root/name).write_text('# fixture entry point\n')
        for name in ['server','customer_actor','response_planning']:(self.root/f'backend/app/dashboard/{name}.py').write_text("VERSION = 'fixture'\n" if name=='server' else '# fixture source\n')
        (self.root/'requirements-dashboard.txt').write_text('# stdlib fixture only\n')
        (self.root/'frontend/app.js').write_text('const fixture = true;\n')
        (self.root/'tests/dashboard/test_fixture.py').write_text('import unittest\nclass Fixture(unittest.TestCase):\n def test_release_marker(self): self.assertTrue(True)\n')
        self.shell(['git','init','-b','local-test']);self.shell(['git','config','user.email','test@local.invalid']);self.shell(['git','config','user.name','Local Test'])
        self.shell(['git','remote','add','origin',ops.TRUSTED_URL]);self.shell(['git','add','.']);self.shell(['git','commit','-m','fixture base'])
        self.previous=self.shell(['git','rev-parse','HEAD'])
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));self.port=sock.getsockname()[1]
        self.keychain=FakeKeychain();self.app=ops.Installation(self.root,self.port,self.base/'support',self.keychain,base_release=self.previous)
        self.addCleanup(self.safe_stop)

    def shell(self,args):
        return subprocess.check_output(args,cwd=self.root,stderr=subprocess.DEVNULL,text=True).strip()
    def safe_stop(self):
        try:self.app.stop()
        except ops.OperationError:pass
    def target(self, *, broken=False, tests_fail=False):
        (self.root/'release-marker.txt').write_text('safe release\n')
        if broken:(self.root/'scripts/serve_dashboard.py').write_text("raise SystemExit('synthetic startup failure')\n")
        if tests_fail:(self.root/'tests/dashboard/test_fixture.py').write_text('import unittest\nclass Broken(unittest.TestCase):\n def test_failed_preflight(self): self.fail("intentional preflight rejection")\n')
        self.shell(['git','add','.']);self.shell(['git','commit','-m','fixture candidate'])
        target=self.shell(['git','rev-parse','HEAD']);bundle=self.base/'release.bundle'
        self.shell(['git','bundle','create',str(bundle),'--all']);self.shell(['git','checkout','--detach',self.previous])
        import hashlib
        return {'source':'bundle','repository':ops.TRUSTED_URL,'commit':target,'path':str(bundle),'sha256':hashlib.sha256(bundle.read_bytes()).hexdigest()}

    def test_repeated_start_reuses_one_pid_and_does_not_request_key_twice(self):
        first=self.app.start(browser=False);second=self.app.start(browser=False)
        self.assertEqual(first['runtime']['pid'],second['runtime']['pid']);self.assertEqual(self.keychain.calls,1)
        self.assertEqual(first['runtime']['git_commit'],self.previous)

    def test_foreign_port_process_is_never_stopped(self):
        process=subprocess.Popen([sys.executable,'-m','http.server',str(self.port),'--bind','127.0.0.1'],cwd=self.base,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            for _ in range(100):
                if ops.listener_pid(self.port):break
                time.sleep(.05)
            with self.assertRaises(ops.OperationError):self.app.stop()
            with self.assertRaises(ops.OperationError):self.app.start(browser=False)
            self.assertIsNone(process.poll());self.assertEqual(self.keychain.calls,0)
        finally:process.terminate();process.wait(timeout=10)

    def test_dirty_tree_aborts_update_without_stopping_server(self):
        spec=self.target();running=self.app.start(browser=False)
        (self.root/'frontend/app.js').write_text('const uniqueWork = 1;\n')
        with self.assertRaisesRegex(ops.OperationError,'несохранённые'):self.app.update(spec,browser=False)
        self.assertEqual(self.app.status()['runtime']['pid'],running['runtime']['pid'])
        self.assertIn('uniqueWork',(self.root/'frontend/app.js').read_text())

    def test_preflight_failure_keeps_old_process_and_commit(self):
        spec=self.target(tests_fail=True);running=self.app.start(browser=False)
        with self.assertRaisesRegex(ops.OperationError,'Предварительные'):self.app.update(spec,browser=False)
        self.assertEqual(self.app.head(),self.previous);self.assertEqual(self.app.status()['runtime']['pid'],running['runtime']['pid'])

    def test_successful_update_and_manual_rollback_preserve_conversations(self):
        spec=self.target();self.app.start(browser=False)
        db=self.root/'runtime/dashboard/trainer.sqlite3'
        with closing(sqlite3.connect(db)) as c:c.execute('create table evidence(value text)');c.execute("insert into evidence values ('before')");c.commit()
        updated=self.app.update(spec,browser=False);self.assertEqual(updated['runtime']['git_commit'],spec['commit'])
        with closing(sqlite3.connect(db)) as c:c.execute("insert into evidence values ('after')");c.commit()
        restored=self.app.rollback(browser=False);self.assertEqual(restored['runtime']['git_commit'],self.previous)
        with closing(sqlite3.connect(db)) as c:self.assertEqual(c.execute('select count(*) from evidence').fetchone()[0],2)

    def test_failed_candidate_start_automatically_restores_previous_working_server(self):
        spec=self.target(broken=True);self.app.start(browser=False)
        with self.assertRaisesRegex(ops.OperationError,'автоматически восстановлена'):self.app.update(spec,browser=False)
        self.assertEqual(self.app.head(),self.previous);self.assertTrue(self.app.healthy(self.app.status()))
        self.assertEqual(json.loads((self.root/'runtime/last-update.json').read_text())['outcome'],'rolled_back')

    def test_checksum_and_untrusted_origin_are_rejected(self):
        spec=self.target();bad={**spec,'sha256':'0'*64}
        with self.assertRaises(ops.OperationError):self.app.resolve_release(bad)
        self.shell(['git','remote','set-url','origin','https://example.invalid/not-this-project.git'])
        with self.assertRaises(ops.OperationError):self.app.resolve_release(spec)

    def test_existing_correct_environment_does_not_install_dependencies(self):
        first=self.app.ensure_environment()
        marker=first.stat().st_mtime_ns
        second=self.app.ensure_environment()
        self.assertEqual(first,second);self.assertEqual(first.stat().st_mtime_ns,marker)
        self.assertFalse((self.root/'runtime/logs/dependencies.log').exists())


    def test_ignored_user_file_collision_is_rejected_before_stop(self):
        (self.root/'future-user-data.txt').write_text('release content')
        self.shell(['git','add','-f','future-user-data.txt'])
        self.shell(['git','commit','-m','candidate tracks previously ignored path'])
        target=self.shell(['git','rev-parse','HEAD']);bundle=self.base/'collision.bundle'
        self.shell(['git','bundle','create',str(bundle),'--all']);self.shell(['git','checkout','--detach',self.previous])
        (self.root/'future-user-data.txt').write_text('unique user content')
        import hashlib
        spec={'source':'bundle','repository':ops.TRUSTED_URL,'commit':target,'path':str(bundle),'sha256':hashlib.sha256(bundle.read_bytes()).hexdigest()}
        running=self.app.start(browser=False)
        with self.assertRaisesRegex(ops.OperationError,'локальным файлом'):
            self.app.update(spec,browser=False)
        self.assertEqual((self.root/'future-user-data.txt').read_text(),'unique user content')
        self.assertEqual(self.app.status()['runtime']['pid'],running['runtime']['pid'])
