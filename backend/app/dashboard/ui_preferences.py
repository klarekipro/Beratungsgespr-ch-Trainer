"""Presentation preferences and review read receipts; training data is untouched."""
from typing import Literal
from fastapi import HTTPException
from .models import InputModel
from .auth import CURRENT_USER

class ViewPreferences(InputModel):
    theme: Literal['light','dark','system'] = 'system'
    layout: Literal['auto','side','stack'] = 'auto'
    density: Literal['normal','compact'] = 'normal'

class ReadReceipt(InputModel):
    session_id: str
    published_at: str

def attach_ui_preferences(app,workflow,auth):
    @app.get('/api/ui/preferences')
    async def preferences():
        return {'preferences':workflow.get('ui_preferences',CURRENT_USER.get()['id'])}

    @app.put('/api/ui/preferences')
    async def save_preferences(value:ViewPreferences):
        record=value.model_dump()
        workflow.put('ui_preferences',CURRENT_USER.get()['id'],record)
        return {'preferences':record}

    @app.get('/api/ui/reviews/read')
    async def receipts():
        return {'read':workflow.get('review_read',CURRENT_USER.get()['id']) or {}}

    @app.post('/api/ui/reviews/read')
    async def mark_read(value:ReadReceipt):
        user=CURRENT_USER.get();session=workflow.store.get_session(value.session_id)
        if not session or user['role']!='employee' or auth.owner(value.session_id)!=user['id']:
            raise HTTPException(404)
        review=workflow.published(session,auth)
        if not review or review['published_at']!=value.published_at:
            raise HTTPException(409)
        # Store only a reference/version, never copy or rewrite the feedback.
        with workflow.store.connection() as c:
            import json
            c.execute('BEGIN IMMEDIATE')
            row=c.execute("SELECT data FROM learning_records WHERE kind='review_read' AND id=?",(user['id'],)).fetchone()
            record=json.loads(row[0]) if row else {}
            record[value.session_id]=value.published_at
            c.execute("INSERT INTO learning_records VALUES ('review_read',?,?) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data",(user['id'],json.dumps(record)))
        return {'read':record}
