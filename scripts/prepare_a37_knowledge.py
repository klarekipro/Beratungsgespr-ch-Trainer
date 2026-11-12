"""Explicit offline A37 preparation / approved publication. Never called at startup.

Preparation opens the database read-only. Apply/rollback require an explicit flag,
create a SQLite backup first, and update only the company and material pointers.
"""
import argparse
import copy
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import sys
from datetime import datetime, timezone
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.dashboard.company_reference import (
    REFERENCES, KNOWLEDGE, canonical_company, company_digest, knowledge_company,
)
from backend.app.dashboard.models import Company


def read_current(connection):
    def read(table, kind, key):
        row = connection.execute(f'SELECT data FROM {table} WHERE kind=? AND id=?', (kind, key)).fetchone()
        if not row:
            raise ValueError('Required company/material record missing')
        return json.loads(row[0])
    return read('documents', 'company', 'main'), read('learning_records', 'materials', 'current')


def prepare(company, materials, *, version=None, timestamp=None):
    baseline = canonical_company()
    baseline['revision'] = company['revision']
    if company != baseline or materials.get('reference_version') != 'lindenhaus-a17-v1' or materials.get('translations') != REFERENCES:
        raise ValueError('Company/materials differ from audited A17 baseline; review changes manually')
    if materials.get('products') != REFERENCES['de']['products']:
        raise ValueError('Catalog differs from approved source')
    target = knowledge_company()
    target['revision'] = company['revision'] + 1
    target = Company.model_validate(target).model_dump()
    fresh = copy.deepcopy(materials)
    stamp = timestamp or datetime.now(timezone.utc).isoformat()
    fresh.update(id=version or uuid4().hex, base_version=materials['id'], created_at=stamp,
                 applied_at=stamp, reference_version=KNOWLEDGE['version'],
                 reference_company_sha256=company_digest(target))
    for language, reference in fresh['translations'].items():
        reference['version'] = KNOWLEDGE['version']
        reference['about'] += '\n\n' + KNOWLEDGE['additions'][language]
        reference['documents'][0]['text'] += '\n\n' + KNOWLEDGE['additions'][language]
    fresh['markdown'] = '\n\n'.join(doc['text'] for doc in fresh['translations']['de']['documents'])
    return {'version': KNOWLEDGE['version'], 'status': 'prepared_not_activated',
            'before_company': copy.deepcopy(company), 'before_materials': copy.deepcopy(materials),
            'company': target, 'materials': fresh}


def validate(plan):
    rebuilt = prepare(plan['before_company'], plan['before_materials'],
                      version=plan['materials']['id'], timestamp=plan['materials']['created_at'])
    if rebuilt != plan or plan['materials']['id'] == plan['before_materials']['id']:
        raise ValueError('Plan differs from reviewed package; prepare again')


def readonly(path):
    return closing(sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True))


def publish(path, plan, backup, *, rollback=False):
    validate(plan)
    # Exclusive file creation prevents overwriting an earlier backup.
    backup = Path(backup)
    fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(fd)
    with readonly(path) as source, closing(sqlite3.connect(backup)) as destination:
        source.backup(destination)
        if destination.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Backup integrity check failed')
    expected = (plan['company'], plan['materials']) if rollback else (plan['before_company'], plan['before_materials'])
    target = (plan['before_company'], plan['before_materials']) if rollback else (plan['company'], plan['materials'])
    # No schema creation, session updates, account updates, or historical rewrites.
    with closing(sqlite3.connect(path, timeout=10)) as connection, connection:
        connection.execute('BEGIN IMMEDIATE')
        if read_current(connection) != expected:
            raise ValueError('Current version changed; no changes applied')
        if not rollback:
            connection.execute('INSERT INTO learning_records VALUES (?,?,?)',
                               ('material_version', plan['materials']['id'], json.dumps(plan['materials'], ensure_ascii=False)))
        connection.execute("UPDATE documents SET data=? WHERE kind='company' AND id='main'", (json.dumps(target[0], ensure_ascii=False),))
        connection.execute("UPDATE learning_records SET data=? WHERE kind='materials' AND id='current'", (json.dumps(target[1], ensure_ascii=False),))
    # Rollback retains the A37 material_version for any attempts captured meanwhile.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('database', type=Path)
    parser.add_argument('plan', type=Path)
    parser.add_argument('--action', choices=['prepare', 'apply', 'rollback'], default='prepare')
    parser.add_argument('--owner-authorized', action='store_true')
    parser.add_argument('--backup', type=Path)
    args = parser.parse_args()
    if args.action == 'prepare':
        with readonly(args.database) as connection:
            connection.execute('BEGIN')
            plan = prepare(*read_current(connection))
        fd = os.open(args.plan, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as output:
            json.dump(plan, output, ensure_ascii=False, indent=2)
        print('PREPARED, NOT ACTIVATED:', plan['materials']['id'])
    else:
        if not args.owner_authorized or not args.backup:
            parser.error('Owner authorization and a new backup path are required')
        publish(args.database, json.loads(args.plan.read_text()), args.backup, rollback=args.action == 'rollback')
        print(args.action.upper(), 'completed; historical records retained')


if __name__ == '__main__':
    main()
