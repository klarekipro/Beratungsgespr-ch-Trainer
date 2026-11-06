"""A10 release gate: functional/security smoke, not model-quality test counts."""
from pathlib import Path
import subprocess
import sys
import shutil
root=Path(__file__).resolve().parents[1]
result=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests/functional','-q'],cwd=root)
if result.returncode:raise SystemExit(result.returncode)
node=shutil.which('node')
if not node:
    candidates=sorted((Path.home()/'.nvm/versions/node').glob('*/bin/node'))
    node=str(candidates[-1]) if candidates else None
if not node:raise SystemExit('Node.js нужен для проверки синтаксиса frontend.')
for path in (root/'frontend').glob('*.js'):
    if subprocess.run([node,'--check',str(path)]).returncode:raise SystemExit(1)
print('Release smoke: auth/ownership/migration/profile/export and JS syntax passed. AI quality not evaluated.')
