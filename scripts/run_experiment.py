#!/usr/bin/env python3
"""Explicitly paid regression, using a masked prompt or an existing environment key."""
import argparse
from datetime import datetime, timezone
import getpass
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--paid', action='store_true', help='Authorize up to 148 real API calls')
    args = parser.parse_args()
    if not args.paid:
        parser.error('Use --paid only when you intentionally want real API charges')
    subprocess.run([sys.executable, str(ROOT / 'scripts/check_workspace.py')], cwd=ROOT, check=True)
    api_key = os.environ.get('OPENAI_API_KEY', '').strip() or getpass.getpass('OpenAI API key (hidden): ').strip()
    if not api_key:
        parser.error('API key missing; no API calls made')
    child_env = os.environ.copy()
    child_env['OPENAI_API_KEY'] = api_key
    child_env['PYTHONDONTWRITEBYTECODE'] = '1'
    # New local results are private. Never write credentials to a file or argv.
    os.umask(0o077)
    private = ROOT / 'reports/private'
    private.mkdir(parents=True, exist_ok=True, mode=0o700)
    private.chmod(0o700)
    output = private / ('feasibility-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    command = [sys.executable, str(ROOT / 'research/feasibility/remediation_regression.py'), '--run', '--output-dir', str(output)]
    print('Real regression: up to 148 API calls. Results:', output, flush=True)
    try:
        return subprocess.run(command, cwd=ROOT, env=child_env).returncode
    finally:
        child_env.pop('OPENAI_API_KEY', None)
        api_key = ''


if __name__ == '__main__':
    sys.exit(main())
