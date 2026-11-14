"""Explicit local-owner password recovery. Never invoked by public HTTP API."""
from pathlib import Path
import getpass
import os
import sys
import sqlite3
from datetime import datetime
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app.dashboard.store import SQLiteStore
from backend.app.dashboard.auth import AuthStore, normalize_login

def main():
    root=Path(__file__).resolve().parents[1]
    data=Path(os.environ.get('TRAINER_DATA_DIR',str(root/'runtime/dashboard')))/'trainer.sqlite3'
    auth=AuthStore(SQLiteStore(data))
    try:username=normalize_login(input('Mentor login / Логин наставника: '))
    except Exception:raise SystemExit('Invalid login. Nothing changed / Ничего не изменено.') from None
    with auth.store.connection() as c:
        row=c.execute("SELECT id FROM users WHERE username=? AND role='mentor_admin' AND active=1",(username,)).fetchone()
    if not row:raise SystemExit('Active mentor not found. Nothing changed / Активный наставник не найден.')
    print('This resets ONLY this mentor password and signs out all its sessions. History and other accounts remain. / Сбросит пароль и завершит сеансы только этого наставника.')
    if input('Confirm by typing / Для подтверждения введите RESET '+username+': ')!='RESET '+username:
        raise SystemExit('Cancelled. Nothing changed / Отмена. Ничего не изменено.')
    print('Password input is invisible (no dots). Type and press Enter. / Ввод невидим, без звёздочек.')
    first=getpass.getpass('New password (12–128) / Новый пароль: ')
    second=getpass.getpass('Repeat / Повторите: ')
    if first!=second:raise SystemExit('Passwords differ. Nothing changed / Пароли не совпали.')
    from backend.app.dashboard.auth import password_ok
    try:password_ok(first)
    except Exception:raise SystemExit('Use 12–128 characters. Nothing changed / Нужно 12–128 символов.') from None
    backup=data.parent.parent/'recovery';backup.mkdir(mode=0o700,exist_ok=True)
    target=backup/('before-mentor-recovery-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.sqlite3')
    with sqlite3.connect(data) as source, sqlite3.connect(target) as dest:source.backup(dest)
    target.chmod(0o600)
    auth.reset(row[0],first,temporary=False);del first,second
    print('Password reset. Sign in at http://127.0.0.1:8100/mentor / Пароль сброшен. История сохранена.')

if __name__=='__main__':main()
