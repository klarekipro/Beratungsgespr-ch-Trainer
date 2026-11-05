#!/usr/bin/env python3
"""Offline workspace/provenance checks. Never calls an LLM or writes the archive."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import runpy
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
TOKEN_PATTERNS = (
    re.compile(rb'sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{24,}'),
    re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})'),
    re.compile(rb'AKIA[A-Z0-9]{16}'),
    re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
)


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def sensitive_path(name):
    p = Path(name)
    return (
        (p.name == '.env' or p.name.startswith('.env.')) and p.name != '.env.example'
        or p.suffix in {'.key', '.pem', '.db', '.sqlite', '.sqlite3', '.log', '.jsonl'}
        or p.name in {'results.json', 'manual_review.json', 'plan.json'}
        or name.startswith('reports/private/')
        or name.startswith('research/feasibility/remediation/run-')
    )


def check_staged():
    names = [n.decode() for n in git('diff', '--cached', '--name-only', '-z', '--diff-filter=ACMR').split(b'\0') if n]
    if not names:
        raise RuntimeError('No staged files to audit')
    for name in names:
        if sensitive_path(name):
            raise RuntimeError('Sensitive path staged: ' + name)
        data = git('show', ':' + name)
        if any(pattern.search(data) for pattern in TOKEN_PATTERNS):
            raise RuntimeError('Potential credential in staged file: ' + name)
    return len(names)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--staged', action='store_true')
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'reports/COPY_SHA256_MANIFEST.json').read_text())
    for item in manifest['files']:
        path = ROOT / 'research/feasibility' / item['path']
        if not path.exists():
            raise RuntimeError('Local archive file missing (raw outputs are intentionally absent from Git): ' + item['path'])
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256_before'] == item['sha256_after'], item['path']
    for path in [*list((ROOT / 'backend/app').glob('*.py')), *list((ROOT / 'scripts').glob('*.py'))]:
        ast.parse(path.read_text(), filename=str(path))
    regression = runpy.run_path(str(ROOT / 'research/feasibility/remediation_regression.py'))
    checks = regression['local_checks']()
    assert checks['passed'] and checks['planned_api_calls'] == 148
    print('PASS: 18 archive hashes, original offline regression checks, Python syntax. No API calls.')
    if args.staged:
        print('PASS: staged credential/path scan for', check_staged(), 'files. Heuristic scan, not a universal secret detector.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
