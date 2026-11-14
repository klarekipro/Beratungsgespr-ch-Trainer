#!/usr/bin/env python3
"""macOS operational lifecycle. Stdlib only; does not change consultation policy."""
from __future__ import annotations
import argparse
import ast
import contextlib
import fcntl
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import secrets
import sqlite3
import subprocess
import sys
import tempfile
import time
from urllib.error import URLError
from urllib.request import urlopen, Request
import uuid

TRUSTED_URL = 'https://github.com/klarekipro/Beratungsgespr-ch-Trainer.git'
SERVICE = 'pro.klareki.beratungstrainer.openai'
BASE_RELEASE = '28a70f1fd8628dcb4679e9b19c85d6f95cf6110e'
ROOT = Path(__file__).resolve().parents[1]
SUPPORT = Path.home() / 'Library/Application Support/KlareKITrainer'

class OperationError(RuntimeError):
    pass

def run(args, *, cwd=None, input=None, timeout=300):
    return subprocess.run([str(a) for a in args], cwd=cwd, input=input,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)

def git(root, *args):
    result = run(['git', '-C', root, *args])
    if result.returncode:
        raise OperationError('Ошибка Git. Проверьте репозиторий, выбранный SHA и доступ к GitHub.')
    return result.stdout.decode().strip()

@contextlib.contextmanager
def operation_lock(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as stream:
        deadline = time.monotonic() + 120
        while True:
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise OperationError('Другая операция ещё выполняется. Повторите позже.')
                time.sleep(.2)
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)

class Keychain:
    def __init__(self, source=ROOT / 'scripts/mac_keychain.c', support=SUPPORT):
        self.source, self.support = source, support

    def helper(self):
        cache = self.support / 'keychain'
        cache.mkdir(parents=True, exist_ok=True, mode=0o700)
        binary, stamp = cache / 'keychain-helper', cache / 'source.sha256'
        digest = hashlib.sha256(self.source.read_bytes()).hexdigest()
        if not binary.exists() or not stamp.exists() or stamp.read_text() != digest:
            temporary = cache / ('build-' + uuid.uuid4().hex)
            result = run(['xcrun', 'clang', '-framework', 'Security', '-framework', 'CoreFoundation', self.source, '-o', temporary])
            if result.returncode:
                raise OperationError('Не удалось собрать Keychain helper. Установите Apple Command Line Tools: xcode-select --install.')
            temporary.chmod(0o700)
            temporary.replace(binary)
            stamp.write_text(digest)
        return binary

    def get(self):
        result = run([self.helper(), 'get'])
        if result.returncode == 44:
            return None
        if result.returncode:
            raise OperationError('Нет доступа к Keychain. Разблокируйте Связку ключей и разрешите доступ helper. Секрет не выводился.')
        return result.stdout

    def set(self, secret):
        if run([self.helper(), 'set'], input=secret).returncode:
            raise OperationError('Keychain не сохранил ключ. Проверьте доступ к Связке ключей.')

    def delete(self):
        if run([self.helper(), 'delete']).returncode:
            raise OperationError('Keychain не удалил ключ. Проверьте доступ к Связке ключей.')

    def prompt(self):
        if not sys.stdin.isatty():
            raise OperationError('Первый запуск: откройте START_TRAINER.command из Finder и введите ключ в скрытый запрос.')
        secret = getpass.getpass('OpenAI API key (скрыто; сохраняется только в macOS Keychain): ').strip().encode()
        if not secret or len(secret) > 8192 or b'\n' in secret:
            raise OperationError('Ключ не введён или имеет неверный формат.')
        self.set(secret)
        return secret

def listener_pid(port):
    result = run(['/usr/sbin/lsof', '-nP', '-t', f'-iTCP:{port}', '-sTCP:LISTEN'])
    pids = set(result.stdout.decode().split())
    if len(pids) > 1:
        raise OperationError('Порт занят несколькими процессами. Автоматическая остановка запрещена.')
    return int(next(iter(pids))) if pids else None

def process_identity(pid):
    cwd = run(['/usr/sbin/lsof', '-a', '-p', str(pid), '-d', 'cwd', '-Fn']).stdout.decode()
    folder = next((line[1:] for line in cwd.splitlines() if line.startswith('n')), '')
    command = run(['/bin/ps', '-p', str(pid), '-o', 'command=']).stdout.decode().strip()
    started = run(['/bin/ps', '-p', str(pid), '-o', 'lstart=']).stdout.decode().strip()
    return folder, command, started

class Installation:
    def __init__(self, root=ROOT, port=8100, support=SUPPORT, keychain=None, base_release=BASE_RELEASE):
        self.root = Path(root).resolve()
        self.port, self.support = port, Path(support)
        self.children = {}
        self.base_release = base_release
        self.runtime = self.root / 'runtime'
        self.runtime.mkdir(exist_ok=True, mode=0o700)
        token_file=self.runtime/'installation-token'
        if not token_file.exists():
            try:
                with os.fdopen(os.open(token_file,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600),'w') as f:f.write(secrets.token_urlsafe(32))
            except FileExistsError:pass
        self.local_token=token_file.read_text().strip()
        self.keychain = keychain or Keychain(self.root / 'scripts/mac_keychain.c', self.support)
        self.url = f'http://127.0.0.1:{port}'

    def head(self):
        return git(self.root, 'rev-parse', 'HEAD')

    def status(self):
        try:
            with urlopen(Request(self.url + '/api/status',headers={'X-Trainer-Local-Token':self.local_token}), timeout=2) as response:
                return json.load(response)
        except (OSError, ValueError, URLError):
            return None

    def owned(self, pid):
        folder, command, started = process_identity(pid)
        return (Path(folder).resolve() == self.root and any(name in command for name in ('serve_dashboard.py', 'run_installed_dashboard.py'))
                and ('Python' in command or 'python' in command) and bool(started))

    def stop(self):
        pid = listener_pid(self.port)
        if not pid:
            return
        identity = process_identity(pid)
        if not self.owned(pid):
            raise OperationError(f'Порт {self.port} занят посторонним процессом PID {pid}. Он не остановлен.')
        if listener_pid(self.port) != pid or process_identity(pid) != identity:
            raise OperationError('Процесс изменился во время проверки. Остановка отменена.')
        os.kill(pid, signal.SIGTERM)
        deadline = time.monotonic() + 10
        while listener_pid(self.port) == pid and time.monotonic() < deadline:
            time.sleep(.15)
        if listener_pid(self.port) == pid:
            raise OperationError('Сервер не завершился. Принудительная остановка не выполнялась.')
        child = self.children.pop(pid, None)
        if child:
            child.wait(timeout=10)

    def healthy(self, status, expected_pid=None, require_ai=True):
        if not isinstance(status, dict):
            return False
        rt = status.get('runtime', {})
        expected = self.root / 'backend/app/dashboard/server.py'
        expected_version = None
        for node in ast.parse(expected.read_text()).body:
            if isinstance(node, ast.Assign) and any(isinstance(t,ast.Name) and t.id == 'VERSION' for t in node.targets):
                expected_version = ast.literal_eval(node.value)
        return (status.get('version') == expected_version and rt.get('python') == str(self.root / '.venv/bin/python')
                and rt.get('data_path') == str(self.runtime / 'dashboard/trainer.sqlite3')
                and rt.get('git_commit') == self.head() and rt.get('server_module') == str(expected)
                and rt.get('customer_actor_module') == str(expected.with_name('customer_actor.py'))
                and rt.get('customer_actor_sha256') == hashlib.sha256(expected.with_name('customer_actor.py').read_bytes()).hexdigest()
                and rt.get('response_planning_sha256') == hashlib.sha256(expected.with_name('response_planning.py').read_bytes()).hexdigest()
                and (not expected.with_name('simple_actor.py').exists() or rt.get('simple_actor_sha256')==hashlib.sha256(expected.with_name('simple_actor.py').read_bytes()).hexdigest())
                and (not expected.with_name('auth.py').exists() or rt.get('auth_sha256')==hashlib.sha256(expected.with_name('auth.py').read_bytes()).hexdigest())
                and (expected_pid is None or rt.get('pid') == expected_pid)
                and (not require_ai or status.get('ai', {}).get('configured') is True))

    def ensure_environment(self, root=None):
        root = Path(root or self.root)
        venv, requirements = root / '.venv', root / 'requirements-dashboard.txt'
        if venv.is_symlink():
            raise OperationError('.venv не должен ссылаться на чужое окружение.')
        python = venv / 'bin/python'
        if not python.exists():
            result = run([sys.executable, '-m', 'venv', venv])
            if result.returncode:
                raise OperationError('Не удалось создать .venv. Проверьте установку Python 3.10+.')
        probe = ('import importlib.metadata as m,json,sys; '
                 'print(json.dumps({"prefix":sys.prefix,"versions":{d.metadata["Name"].lower():d.version for d in m.distributions()}}))')
        result = run([python, '-c', probe])
        if result.returncode:
            raise OperationError('Python в .venv не работает. Окружение не удалялось.')
        installed = json.loads(result.stdout)
        if Path(installed['prefix']).resolve() != venv.resolve():
            raise OperationError('Python использует другое окружение. Запуск отменён.')
        pins = {}
        for line in requirements.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            match = re.fullmatch(r'([A-Za-z0-9_.-]+)==([^\s]+)', line)
            if not match:
                raise OperationError('Неподдерживаемая запись requirements: нужны проверяемые package==version.')
            pins[match[1].lower()] = match[2]
        if any(installed['versions'].get(name) != version for name, version in pins.items()):
            print('Устанавливаю зависимости для выбранной версии…', flush=True)
            result = run([python, '-m', 'pip', 'install', '-r', requirements])
            log = self.runtime / 'logs'; log.mkdir(exist_ok=True)
            (log / 'dependencies.log').write_bytes(result.stdout + result.stderr)
            if result.returncode:
                raise OperationError('Зависимости не установлены. Подробности: runtime/logs/dependencies.log.')
        return python

    def start(self, *, browser=True, secret=None, prompt=True):
        current = self.status()
        pid = listener_pid(self.port)
        if pid and self.owned(pid) and self.healthy(current, expected_pid=pid):
            print(f'Тренажёр уже работает: {self.url}\nSHA: {self.head()}', flush=True)
            if browser:
                run(['/usr/bin/open', self.url])
            return current
        if pid and not self.owned(pid):
            raise OperationError(f'Порт {self.port} занят посторонним PID {pid}. Он не остановлен.')
        python = self.ensure_environment()
        if secret is None:
            secret = self.keychain.get()
        if not secret:
            if not prompt:
                raise OperationError('Ключ отсутствует в Keychain. Выполните первый запуск из Finder.')
            secret = self.keychain.prompt()
        # Only after preflight + safe credential acquisition do we stop stale code.
        self.stop()
        logs = self.runtime / 'logs'; logs.mkdir(exist_ok=True)
        data = self.runtime / 'dashboard'; data.mkdir(exist_ok=True)
        env = os.environ.copy(); env.pop('OPENAI_API_KEY', None)
        env['TRAINER_AUDIT_DIR'] = str(self.runtime / 'audit')
        with (logs / 'server.log').open('ab') as log:
            process = subprocess.Popen([python, self.root / 'scripts/run_installed_dashboard.py',
                '--openai', '--port', str(self.port), '--data-dir', data], cwd=self.root,
                env=env, stdin=subprocess.PIPE, stdout=log, stderr=log, start_new_session=True)
        self.children[process.pid] = process
        try:
            process.stdin.write(secret + b'\n'); process.stdin.close()
        finally:
            del secret
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            status = self.status()
            if self.healthy(status, expected_pid=process.pid):
                (self.runtime / 'running.json').write_text(json.dumps({'pid':process.pid,'commit':self.head(),'url':self.url}))
                print(f'Готово: {self.url}\nSHA: {self.head()}\nМодуль: {status["runtime"]["server_module"]}', flush=True)
                if browser:
                    run(['/usr/bin/open', self.url])
                return status
            if process.poll() is not None:
                break
            time.sleep(.2)
        # The child is ours; never stop a different listener on a port race.
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
        raise OperationError('Сервер не прошёл проверку SHA/модуля/API. Смотрите runtime/logs/server.log.')

    def resolve_release(self, spec):
        if git(self.root, 'remote', 'get-url', 'origin') != TRUSTED_URL:
            raise OperationError('origin не совпадает с доверенным приватным репозиторием. Обновление отменено.')
        if spec.get('repository') != TRUSTED_URL or not re.fullmatch('[0-9a-f]{40}', str(spec.get('commit', ''))):
            raise OperationError('Укажите доверенный repository и полный проверенный commit SHA.')
        target = spec['commit']
        if spec.get('source') == 'github':
            # Exact SHA only. No implicit main, latest, branch movement or fallback.
            result = run(['git', '-c', 'credential.helper=', '-c', 'credential.helper=!gh auth git-credential',
                          '-C', self.root, 'fetch', '--no-tags', TRUSTED_URL, target])
            if result.returncode:
                raise OperationError('Выбранный commit недоступен в GitHub. Локальные непропушенные версии требуют явно указанного bundle; main не использовался.')
            if git(self.root, 'rev-parse', 'FETCH_HEAD') != target:
                raise OperationError('Полученный SHA не совпал с выбранным.')
        elif spec.get('source') == 'bundle':
            bundle = Path(spec.get('path', '')).expanduser()
            if not bundle.is_file() or hashlib.sha256(bundle.read_bytes()).hexdigest() != spec.get('sha256'):
                raise OperationError('Bundle отсутствует или контрольная сумма изменилась.')
            if run(['git', '-C', self.root, 'bundle', 'verify', bundle]).returncode:
                raise OperationError('Git bundle не прошёл проверку.')
            # Fetch named refs; then require the exact pinned commit to exist.
            result = run(['git', '-C', self.root, 'fetch', '--no-tags', bundle,
                          'refs/heads/*:refs/trainer/bundle/*'])
            if result.returncode:
                raise OperationError('Не удалось получить выбранный локальный release bundle.')
        else:
            raise OperationError('Источник должен быть явно задан: github или bundle.')
        if spec.get('source') == 'bundle':
            advertised = run(['git','bundle','list-heads',bundle]).stdout.decode().splitlines()
            tips = [line.split()[0] for line in advertised if line.split()]
            if not any(run(['git','-C',self.root,'merge-base','--is-ancestor',target,tip]).returncode == 0 for tip in tips):
                raise OperationError('Выбранный commit не принадлежит указанному bundle.')
        if run(['git','-C',self.root,'merge-base','--is-ancestor',self.base_release,target]).returncode:
            raise OperationError('Выбранная версия не является A06 или её последующей версией.')
        if git(self.root, 'rev-parse', target + '^{commit}') != target:
            raise OperationError('Commit не найден в проверенном источнике.')
        return target

    def check_auth_compatibility(self,target):
        database=self.runtime/'dashboard/trainer.sqlite3'
        if not database.exists():return
        with sqlite3.connect(database) as con:
            has_users=con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='users'").fetchone()
            populated=bool(has_users and con.execute('SELECT 1 FROM users LIMIT 1').fetchone())
        if populated and run(['git','-C',self.root,'cat-file','-e',target+':backend/app/dashboard/auth.py']).returncode:
            raise OperationError('Откат к версии без авторизации запрещён после создания учётных записей. Сохранены резервные копии; выберите совместимый защищённый commit.')

    def check_clean(self):
        if git(self.root, 'status', '--porcelain'):
            raise OperationError('Есть несохранённые изменения или уникальные untracked-файлы. Сохраните их; автоматический reset/clean запрещён.')

    def check_collisions(self, target):
        current = set(git(self.root, 'ls-files', '-z').split('\0'))
        target_files = git(self.root, 'ls-tree', '-r', '--name-only', '-z', target).split('\0')
        if any(name and name not in current and (self.root / name).exists() for name in target_files):
            raise OperationError('Новая версия пересекается с локальным файлом, включая ignored. Сохраните его отдельно; файл не перезаписывался.')

    def prepare_release(self, target):
        self.support.mkdir(parents=True, exist_ok=True, mode=0o700)
        stage = self.support / 'staging' / uuid.uuid4().hex
        stage.parent.mkdir(exist_ok=True)
        git(self.root, 'worktree', 'add', '--detach', str(stage), target)
        try:
            for rel in ['START_TRAINER.command','STOP_TRAINER.command','UPDATE_TRAINER.command',
                        'scripts/local_installation.py','scripts/run_installed_dashboard.py']:
                if not (stage / rel).is_file():
                    raise OperationError('В выбранной версии нет operational launcher A07. Основная установка не переключалась.')
            python = self.ensure_environment(stage)
            env = os.environ.copy(); env['OPENAI_API_KEY'] = ''; env.pop('TRAINER_AUDIT_DIR', None)
            tests = subprocess.run(([python, 'scripts/release_smoke.py'] if (stage/'scripts/release_smoke.py').is_file() else [python, '-m', 'unittest', 'discover', '-s', 'tests/dashboard', '-q']),
                                   cwd=stage, env=env, capture_output=True, timeout=300)
            node = shutil.which('node')
            if not node:
                candidates = list((Path.home() / '.nvm/versions/node').glob('*/bin/node'))
                node = str(sorted(candidates)[-1]) if candidates else None
            js = run([node, '--check', stage / 'frontend/app.js']) if node else None
            logs = self.runtime / 'logs'; logs.mkdir(exist_ok=True)
            (logs / 'update-tests.log').write_bytes(tests.stdout + tests.stderr + (js.stdout + js.stderr if js else b'Node.js missing'))
            if tests.returncode or js is None or js.returncode:
                raise OperationError('Предварительные тесты обновления не прошли. Текущий сервер не останавливался; смотрите runtime/logs/update-tests.log.')
        finally:
            # Only this newly created staging worktree is disposable.
            result = run(['git','-C',self.root,'worktree','remove','--force',stage])
            if result.returncode:
                raise OperationError('Не удалось убрать временный staging worktree. Основная версия не переключалась.')

    def snapshot(self, target):
        stamp = time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6]
        backup = self.support / 'rollback' / stamp
        backup.mkdir(parents=True, mode=0o700)
        previous = self.head()
        git(self.root, 'update-ref', 'refs/trainer/rollback/' + stamp, previous)
        if (self.root / '.venv').exists():
            shutil.copytree(self.root / '.venv', backup / 'venv', symlinks=True)
        database = self.runtime / 'dashboard/trainer.sqlite3'
        if database.exists():
            src, dst = sqlite3.connect(database), sqlite3.connect(backup / 'trainer.sqlite3')
            try:
                src.backup(dst); dst.commit()
                if dst.execute('pragma integrity_check').fetchone()[0] != 'ok':
                    raise OperationError('Резервная SQLite-копия не прошла проверку.')
            finally:
                dst.close(); src.close()
        record = {'previous_sha':previous,'target_sha':target,'backup':str(backup)}
        (backup / 'release.json').write_text(json.dumps(record, indent=2))
        return record

    def restore(self, record, *, secret, browser=False, restore_data=True):
        if not restore_data:self.check_auth_compatibility(record['previous_sha'])
        self.stop()
        git(self.root, 'checkout', '--no-overwrite-ignore', '--detach', record['previous_sha'])
        backup = Path(record['backup'])
        if (backup / 'venv').exists():
            if (self.root / '.venv').exists():
                (self.root / '.venv').rename(backup / ('failed-venv-' + uuid.uuid4().hex[:6]))
            shutil.copytree(backup / 'venv', self.root / '.venv', symlinks=True)
        database = self.runtime / 'dashboard/trainer.sqlite3'
        if restore_data and database.exists():
            database.rename(backup / ('failed-data-' + uuid.uuid4().hex[:6] + '.sqlite3'))
        # Stop is complete, so move any WAL sidecars aside before restore.
        for suffix in (['-wal','-shm'] if restore_data else []):
            side = Path(str(database) + suffix)
            if side.exists():
                side.rename(backup / (uuid.uuid4().hex + suffix))
        if restore_data and (backup / 'trainer.sqlite3').exists():
            database.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup / 'trainer.sqlite3', database)
        return self.start(browser=browser, secret=secret, prompt=False)

    def update(self, spec, *, browser=True):
        self.check_clean()
        target = self.resolve_release(spec)
        if target == self.head():
            print('Выбранная проверенная версия уже установлена: ' + target)
            return self.start(browser=browser)
        self.check_collisions(target)
        self.check_auth_compatibility(target)
        self.prepare_release(target)
        # Obtain a usable key before stopping the previous working process.
        secret = self.keychain.get() or self.keychain.prompt()
        self.check_clean()
        self.check_collisions(target)
        record = self.snapshot(target)
        self.stop()
        try:
            git(self.root, 'checkout', '--no-overwrite-ignore', '--detach', target)
            self.ensure_environment()
            status = self.start(browser=browser, secret=secret, prompt=False)
        except Exception as error:
            try:
                restored = self.restore(record, secret=secret, browser=False)
            except Exception:
                raise OperationError('Обновление не удалось; автоматический запуск отката тоже не прошёл. Исходники и копия данных сохранены: ' + record['backup']) from None
            (self.runtime / 'last-update.json').write_text(json.dumps({**record,'outcome':'rolled_back'},indent=2))
            raise OperationError('Обновление не прошло проверку. Предыдущая версия автоматически восстановлена и запущена: ' + record['previous_sha']) from None
        (self.runtime / 'last-update.json').write_text(json.dumps({**record,'outcome':'installed'},indent=2))
        return status

    def rollback(self, *, browser=True):
        self.check_clean()
        journal = self.runtime / 'last-update.json'
        if not journal.exists():
            raise OperationError('Нет сохранённого обновления для отката.')
        record = json.loads(journal.read_text())
        if self.head() != record['target_sha']:
            raise OperationError('HEAD изменился после обновления. Автоматический откат отменён.')
        self.check_collisions(record['previous_sha'])
        secret = self.keychain.get() or self.keychain.prompt()
        result = self.restore(record, secret=secret, browser=browser, restore_data=False)
        journal.write_text(json.dumps({**record,'outcome':'manual_rollback'},indent=2))
        return result


def main():
    parser = argparse.ArgumentParser(description='Klare KI — управление локальной установкой')
    parser.add_argument('action', choices=['start','stop','update','key','setup-key','diagnose'])
    parser.add_argument('--target-file', type=Path)
    parser.add_argument('--commit', help='Полный SHA, который должен быть доступен в доверенном GitHub')
    parser.add_argument('--rollback', action='store_true')
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    app = Installation()
    try:
        with operation_lock(app.runtime / 'installation.lock'):
            if args.action == 'start':
                app.start(browser=not args.no_browser)
            elif args.action == 'stop':
                app.stop(); print('Тренажёр остановлен; посторонние процессы не затрагивались.')
            elif args.action == 'diagnose':
                print(json.dumps({'head':app.head(),'status':app.status()},ensure_ascii=False,indent=2))
            elif args.action == 'setup-key':
                if app.keychain.get():
                    print('Ключ уже доступен в Keychain.')
                else:
                    app.keychain.prompt(); print('Ключ сохранён в macOS Keychain. Серверы не изменялись.')
            elif args.action == 'key':
                print('1 — заменить ключ; 2 — удалить ключ и остановить сервер; 3 — проверить наличие')
                choice = input('Выбор: ').strip()
                if choice == '1':
                    secret = app.keychain.prompt(); app.stop(); app.start(secret=secret)
                elif choice == '2':
                    app.keychain.delete(); app.stop(); print('Ключ удалён из Keychain; сервер остановлен.')
                elif choice == '3':
                    print('Ключ есть в Keychain.' if app.keychain.get() else 'Ключ отсутствует.')
                else:
                    raise OperationError('Операция отменена.')
            elif args.rollback:
                app.rollback(browser=not args.no_browser)
            else:
                target_file = args.target_file or app.runtime / 'update-target.json'
                if args.commit:
                    spec = {'source':'github','repository':TRUSTED_URL,'commit':args.commit}
                elif target_file.exists():
                    spec = json.loads(target_file.read_text())
                elif sys.stdin.isatty():
                    target = input('Введите полный SHA опубликованной версии GitHub (main автоматически не используется): ').strip()
                    spec = {'source':'github','repository':TRUSTED_URL,'commit':target}
                else:
                    raise OperationError('Целевая версия не задана. Укажите runtime/update-target.json или --commit <SHA>.')
                app.update(spec, browser=not args.no_browser)
        return 0
    except (OperationError, OSError, ValueError, subprocess.SubprocessError) as error:
        # Only fixed operational messages; never log subprocess environment/output.
        if isinstance(error, OperationError):
            print('ОШИБКА: ' + str(error), file=sys.stderr)
        else:
            print('ОШИБКА: операция не завершена. Версия и резервные копии не удалялись. Проверьте доступ к файлам и повторите.', file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
