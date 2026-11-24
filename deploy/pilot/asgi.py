"""Pilot boundary: bounded request bodies and a minimal internal readiness endpoint."""
import json
from contextlib import closing
import os
from pathlib import Path
import sqlite3

MAX_BODY = 6*1024*1024


async def reply(send, status, value):
    data = json.dumps(value).encode()
    await send({'type':'http.response.start','status':status,'headers':[
        (b'content-type',b'application/json'),(b'cache-control',b'no-store'),(b'content-length',str(len(data)).encode())]})
    await send({'type':'http.response.body','body':data})


class PilotBoundary:
    def __init__(self, app, database, revision):
        self.app, self.database, self.revision = app, Path(database), revision

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        if scope['path'] == '/__pilot_health':
            if scope['method'] != 'GET' or (scope.get('client') or ('',0))[0] != '127.0.0.1':
                return await reply(send, 404, {'status':'unavailable'})
            try:
                with closing(sqlite3.connect(self.database.resolve().as_uri()+'?mode=ro', uri=True, timeout=1)) as db:
                    db.execute('SELECT name FROM sqlite_schema LIMIT 1').fetchone()
                return await reply(send, 200, {'status':'ok','source_revision':self.revision,'sqlite':sqlite3.sqlite_version})
            except sqlite3.Error:
                return await reply(send, 503, {'status':'unavailable'})
        body = bytearray()
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            chunk = message.get('body', b'')
            if len(body)+len(chunk) > MAX_BODY:
                return await reply(send, 413, {'error':{'code':'PILOT_UPLOAD_LIMIT','message':'Request exceeds the 6 MiB pilot upload limit. No file was processed.'}})
            body.extend(chunk)
            if not message.get('more_body'):
                break
        delivered = False
        async def bounded_receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {'type':'http.request','body':bytes(body),'more_body':False}
            return await receive()
        return await self.app(scope, bounded_receive, send)


def create_app():
    # Environment is set by the entrypoint before importing server (which initializes SQLite).
    from backend.app.dashboard.server import app
    root = Path(__file__).resolve().parents[2]
    info = json.loads((root/'BUILD_INFO.json').read_text())
    return PilotBoundary(app, app.state.store.path, info['source_revision'])
