"""Synthetic pilot boundaries; no VPS, Tunnel, live DB or paid API call."""
import asyncio
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from deploy.pilot.asgi import MAX_BODY, PilotBoundary
from deploy.pilot.backup import snapshot, restore_drill
from deploy.pilot.run import storage_preflight


class PilotDeploymentTests(unittest.TestCase):
    def test_wal_online_backup_and_isolated_restore_preserve_unicode_and_blobs(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);source=p/'source.sqlite3'
            with sqlite3.connect(source) as db:
                db.execute('PRAGMA journal_mode=WAL')
                db.execute('CREATE TABLE example(id INTEGER PRIMARY KEY, text TEXT, pdf BLOB)')
                db.execute('INSERT INTO example VALUES(?,?,?)',(1,'ÄÖÜ / Привет / 客户 / 0012',b'%PDF-synthetic'))
                db.commit()
                backup=p/'backup.sqlite3';receipt=snapshot(source,backup)
                self.assertEqual(receipt['tables']['example']['rows'],1)
                # Changes after the snapshot must remain in the live source, not be overwritten by restore.
                db.execute('INSERT INTO example VALUES(2,?,?)',('newer conversation',b'synthetic'));db.commit()
                result=restore_drill(backup,p/'restore-test')
                self.assertEqual(result['status'],'PASS')
                self.assertEqual(db.execute('SELECT COUNT(*) FROM example').fetchone()[0],2)
            with sqlite3.connect(p/'restore-test/trainer.sqlite3') as restored:
                self.assertEqual(restored.execute('SELECT text,pdf FROM example').fetchone(),('ÄÖÜ / Привет / 客户 / 0012',b'%PDF-synthetic'))
            with self.assertRaises(RuntimeError):restore_drill(backup,p/'restore-test')
            with self.assertRaises(RuntimeError):snapshot(source,source)

    def test_corrupt_backup_receipt_never_restores_over_existing_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);db=p/'x.sqlite3'
            with sqlite3.connect(db) as c:c.execute('CREATE TABLE x(a)')
            target=p/'backup.sqlite3';snapshot(db,target)
            target.write_bytes(b'corrupt synthetic fixture')
            with self.assertRaises(RuntimeError):restore_drill(target,p/'separate-drill')
            self.assertTrue(db.exists())

    def test_startup_rejects_shared_uncapped_storage(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'.trainer-pilot-storage.json').write_text('{"project":"klareki-trainer-pilot"}')
            with self.assertRaises(RuntimeError):storage_preflight(tmp)

    def test_boundary_rejects_chunked_oversized_body_before_application(self):
        reached=[];sent=[]
        async def app(scope,receive,send):reached.append(True)
        chunks=iter([{'type':'http.request','body':b'x'*MAX_BODY,'more_body':True},
                     {'type':'http.request','body':b'x','more_body':False}])
        async def receive():return next(chunks)
        async def send(message):sent.append(message)
        asyncio.run(PilotBoundary(app,'unused','synthetic')({'type':'http','path':'/api/upload','method':'POST'},receive,send))
        self.assertEqual(sent[0]['status'],413);self.assertFalse(reached)

    def test_health_is_loopback_only_and_discloses_no_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'x.sqlite3'
            with sqlite3.connect(p) as c:c.execute('CREATE TABLE x(a)')
            async def app(*args):raise AssertionError('Health must not call application/AI')
            async def receive():raise AssertionError('Health does not need a body')
            for ip,expected in [('127.0.0.1',200),('192.0.2.1',404)]:
                sent=[]
                async def send(message):sent.append(message)
                asyncio.run(PilotBoundary(app,p,'a'*40)({'type':'http','path':'/__pilot_health','method':'GET','client':(ip,1)},receive,send))
                self.assertEqual(sent[0]['status'],expected)
                self.assertNotIn('data_path',str(sent));self.assertNotIn('api_key',str(sent))

    def test_https_proxy_trust_does_not_accept_untrusted_forwarded_headers(self):
        from fastapi.testclient import TestClient
        from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
        from backend.app.dashboard.server import create_app
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ,{'TRAINER_REMOTE_HTTPS':'1','TRAINER_ALLOWED_HOSTS':'pilot.example.invalid','OPENAI_API_KEY':''}):
            app=ProxyHeadersMiddleware(create_app(Path(tmp)/'dashboard/trainer.sqlite3'),trusted_hosts=['127.0.0.1'])
            for ip,expected in [('127.0.0.1',303),('192.0.2.1',426)]:
                with TestClient(app,base_url='http://pilot.example.invalid',client=(ip,1234)) as c:
                    r=c.get('/mentor',headers={'X-Forwarded-Proto':'https'},follow_redirects=False)
                    self.assertEqual(r.status_code,expected)


if __name__=='__main__':unittest.main()
