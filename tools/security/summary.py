"""Sanitized report view for Actions job summary; no source/executable artifacts."""
import json
from pathlib import Path
import sys
p=Path(sys.argv[1])
for name in ('gate','secrets','sast','dependencies','workflows','tests','selftest'):
 f=p/(name+'.json')
 if not f.exists():continue
 v=json.loads(f.read_text())
 print(f"### {name}: {v['status']}")
 print('Checked SHA: `'+v.get('commit','NOT VERIFIED')+'`')
 for x in v.get('findings',[]):
  print('- '+x['severity']+' `'+x['rule']+'` at `'+x['file']+':'+str(x['line'])+'`'+(' — `'+x['package']+'@'+x.get('version','')+'`' if x.get('package') else ''))
 if name=='tests':
  for kind in ('failures','errors'):
   for x in v.get('details',{}).get('native_linux_tests',{}).get(kind,[]):print('- Failing regression: `'+x+'`')
