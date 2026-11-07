"""One-time local administrator setup; no public registration route or default password."""
from pathlib import Path
import getpass
import os
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app.dashboard.store import SQLiteStore
from backend.app.dashboard.auth import AuthStore
if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    data=Path(os.environ.get('TRAINER_DATA_DIR',str(root/'runtime/dashboard')))/'trainer.sqlite3'
    auth=AuthStore(SQLiteStore(data))
    if auth.has_mentor():raise SystemExit('Наставник уже создан. Войдите в /mentor. Для восстановления обратитесь к владельцу локальной установки.')
    username=input('Ваш уникальный логин (латиница): ').strip()
    display=input('Ваше имя: ').strip()
    print('Ввод пароля скрыт: символы и звёздочки не отображаются. Введите пароль и нажмите Enter. Автозаполнения браузера в Terminal нет.')
    first=getpass.getpass('Пароль (12–128 символов, ввод скрыт): ')
    second=getpass.getpass('Повторите пароль: ')
    if first!=second:raise SystemExit('Пароли не совпали. Ничего не создано.')
    try:auth.create_user(username,display or username,first,role='mentor_admin',temporary=False,bootstrap=True)
    except Exception:raise SystemExit('Наставник не создан. Проверьте формат логина и длину пароля; открытые значения не выводятся.') from None
    del first,second
    print('Наставник создан. Откройте http://127.0.0.1:8100/mentor')
