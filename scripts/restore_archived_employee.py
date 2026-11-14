#!/usr/bin/env python3
"""IT-only archive restoration. Uses current SQLite identity, never replays old tokens."""
from contextlib import closing
import argparse
import getpass
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app.dashboard.store import SQLiteStore
from backend.app.dashboard.auth import AuthStore
from backend.app.dashboard.employee_lifecycle import EmployeeLifecycle

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database',type=Path,required=True)
    parser.add_argument('--user-id',required=True)
    parser.add_argument('--username',help='Optional new login; conflict checked inside transaction')
    parser.add_argument('--confirm-user-id',required=True)
    args=parser.parse_args()
    if args.user_id!=args.confirm_user_id:parser.error('Confirmation must match user ID')
    database=args.database.resolve()
    if not database.is_file():parser.error('Existing database required')
    backup=database.parent/'backups'/('before-employee-restore-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.sqlite3');backup.parent.mkdir(exist_ok=True)
    with closing(sqlite3.connect(database.as_uri()+'?mode=ro',uri=True)) as src,closing(sqlite3.connect(backup)) as dst:src.backup(dst)
    backup.chmod(0o600)
    auth=AuthStore(SQLiteStore(database));lifecycle=EmployeeLifecycle(auth);user=lifecycle.employee(args.user_id)
    if not user.get('archived_at'):parser.error('Employee is not archived')
    print('Restore:',user['username'],'ID:',user['id'])
    password=getpass.getpass('New temporary password (not stored in command history): ')
    if password!=getpass.getpass('Repeat password: '):parser.error('Passwords differ')
    restored=lifecycle.restore(args.user_id,password,args.username)
    print('Restored:',restored['username'],'; first-login password change required. All old access sessions revoked.')
if __name__=='__main__':main()
