#!/usr/bin/env python3
"""Inspect an owner-built LOCAL runtime-deps image; never pull, publish or access live data."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from urllib.parse import quote

ROOT=Path(__file__).resolve().parents[2]
INPUTS=['requirements-dashboard.txt','deploy/pilot/Dockerfile','deploy/pilot/requirements-linux-amd64.txt','deploy/pilot/python-lock.json']
CODE='''import importlib.metadata as m,json,subprocess,sqlite3,platform
print(json.dumps({'python':[{'name':d.metadata['Name'],'version':d.version} for d in m.distributions()],
'debian':subprocess.check_output(['dpkg-query','-W','-f=${source:Package}\\t${source:Version}\\n'],text=True).splitlines(),
'sqlite':sqlite3.sqlite_version,'python_version':platform.python_version(),'arch':platform.machine(),'input_sha256':json.load(open('/usr/share/trainer-build/input-sha256.json'))}))'''

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--image',required=True);a=p.parse_args()
 image=subprocess.check_output(['docker','image','inspect','--format','{{.Id}}',a.image],text=True).strip()
 data=subprocess.check_output(['docker','run','--rm','--pull=never','--platform','linux/amd64','--network','none','--read-only',
  '--cap-drop=ALL','--security-opt=no-new-privileges','--pids-limit=32','--memory=256m',image,'python','-B','-c',CODE],timeout=90)
 if len(data)>2_000_000:raise RuntimeError('image metadata exceeds review limit')
 v=json.loads(data)
 if (v['sqlite'],v['python_version'],v['arch'])!=('3.54.1','3.14.7','x86_64'):raise RuntimeError('unexpected native runtime')
 expected={x:hashlib.sha256((ROOT/x).read_bytes()).hexdigest() for x in INPUTS}
 if v.get('input_sha256') != expected:raise RuntimeError('image was built from different dependency inputs; rebuild first')
 components=[]
 for x in v['python']:
  n=x['name'].lower().replace('_','-');components.append({'type':'library','name':n,'version':x['version'],'purl':f'pkg:pypi/{n}@{x["version"]}'})
 for n,version in sorted(set(tuple(x.split('\t')) for x in v['debian'] if '\t' in x)):
  components.append({'type':'library','name':n,'version':version,'purl':'pkg:deb/debian/'+quote(n,safe='')+'@'+quote(version,safe='')+'?arch=source&distro=debian-13'})
 bom={'bomFormat':'CycloneDX','specVersion':'1.5','version':1,'metadata':{'properties':[
  {'name':'trainer.scope','value':'candidate-runtime-not-yet-deployed'},
  {'name':'trainer.custom_sqlite','value':'3.54.1; upstream source checksum verified; separate from Debian sqlite package'}]},'components':components}
 out=ROOT/'.security/advisories.cdx.json';out.write_text(json.dumps(bom,indent=2)+'\n')
 receipt={'schema':1,'platform':'linux/amd64','dependency_image_id':image,
  'input_sha256':{x:hashlib.sha256((ROOT/x).read_bytes()).hexdigest() for x in INPUTS},
  'sbom_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'components':len(components),'python':len(v['python']),'sqlite':'3.54.1'}
 (ROOT/'.security/advisories.inputs.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print('SBOM generated:',len(components),'components; candidate graph only; no deployed-state attestation.')
if __name__=='__main__':main()
