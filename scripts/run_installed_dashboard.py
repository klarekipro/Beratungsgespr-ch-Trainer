"""Receive a Keychain secret on an anonymous pipe, then run the unchanged A06 CLI."""
import os
from pathlib import Path
import runpy
import sys

if sys.stdin.isatty():
    raise SystemExit('Запускайте приложение через START_TRAINER.command.')
secret = sys.stdin.buffer.readline(8193).strip()
if not secret or len(secret) > 8192:
    raise SystemExit('Ключ не получен. Запустите настройку OpenAI заново.')
os.environ['OPENAI_API_KEY'] = secret.decode('utf-8')
del secret
sys.argv = [str(Path(__file__).with_name('serve_dashboard.py')), *sys.argv[1:]]
runpy.run_path(sys.argv[0], run_name='__main__')
