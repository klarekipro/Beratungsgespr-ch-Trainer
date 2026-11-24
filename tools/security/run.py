#!/usr/bin/env python3
"""Local/CI security checks. No deployment, issue creation, cloud secrets or paid APIs."""
import argparse
import datetime as dt
import hashlib
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / '.security'
CHECKS = ('secrets', 'sast', 'dependencies', 'workflows', 'tests', 'selftest')

def read(path):
    return json.loads(Path(path).read_text())

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def execute(args, cwd=ROOT, env=None, timeout=300):
    clean = {k: os.environ[k] for k in ('PATH', 'HOME', 'TMPDIR', 'DOCKER_HOST', 'DOCKER_CONTEXT') if k in os.environ}
    clean.update({'CI': 'true', 'NO_COLOR': '1', 'SEMGREP_SEND_METRICS': 'off', 'SEMGREP_ENABLE_VERSION_CHECK': '0'})
    if env:
        clean.update(env)
    return subprocess.run([str(a) for a in args], cwd=cwd, env=clean, capture_output=True, text=True, timeout=timeout)

def docker(image, command, mounts=(), network=False, timeout=300):
    args = ['docker', 'run', '--rm', '--user', f'{os.getuid()}:{os.getgid()}',
            '--network', 'bridge' if network else 'none',
            '--cap-drop=ALL', '--security-opt=no-new-privileges', '--pids-limit=256',
            '-e', 'HOME=/tmp', '-e', 'XDG_CACHE_HOME=/tmp/.cache',
            '-e', 'CI=true', '-e', 'SEMGREP_SEND_METRICS=off', '-e', 'SEMGREP_ENABLE_VERSION_CHECK=0']
    for source, target, writable in mounts:
        args += ['--mount', f'type=bind,src={Path(source).resolve()},dst={target}' + ('' if writable else ',readonly')]
    return execute(args + ['--workdir', '/work', image] + command, timeout=timeout)

def relative(path):
    value = str(path).replace('\\', '/')
    if value.startswith('/work/'):
        value = value[6:]
    try:
        value = str(Path(value).relative_to(ROOT)) if Path(value).is_absolute() else value
    except ValueError:
        return '[outside-repository]'
    if '..' in Path(value).parts:
        return '[invalid-path]'
    return value

def finding(rule, file, line=1, severity='MEDIUM', advisory=None):
    # No scanner-provided message, match, secret, code snippet or metavariable is published.
    rule = re.sub(r'[^A-Za-z0-9_.:-]', '_', str(rule))[:160]
    value = {'rule': rule, 'file': relative(file), 'line': int(line or 1), 'severity': severity}
    if advisory and re.fullmatch(r'(?:GHSA-[a-z0-9-]+|CVE-\d{4}-\d+)', advisory):
        value['advisory'] = advisory
    value['fingerprint'] = hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()[:24]
    return value

def write_result(out, name, status, details, findings=()):
    out.mkdir(parents=True, exist_ok=True)
    result = {'check': name, 'status': status, 'time': dt.datetime.now(dt.timezone.utc).isoformat(),
              'commit': execute(['git', 'rev-parse', 'HEAD']).stdout.strip(),
              'tested_material_sha256': source_digest(),
              'details': details, 'findings': list(findings)}
    (out / (name + '.json')).write_text(json.dumps(result, indent=2) + '\n')
    print(f'{name}: {status} ({len(result["findings"])} findings)')
    return status

def tool(tools, name):
    p = tools / name
    if not p.is_file():
        raise RuntimeError(f'missing reviewed tool: {name}; run bootstrap first')
    receipts = read(tools / 'verified-tools.json')
    if receipts[name]['binary_sha256'] != sha(p):
        raise RuntimeError(f'changed tool binary: {name}')
    return p

def bootstrap(tools, selected=CHECKS):
    lock = read(CONFIG / 'tools.lock.json')
    system = {'Darwin': 'darwin', 'Linux': 'linux'}.get(platform.system())
    arch = {'arm64': 'arm64', 'aarch64': 'arm64', 'x86_64': 'amd64', 'AMD64': 'amd64'}.get(platform.machine())
    key = f'{system}-{arch}'
    tools.mkdir(parents=True, exist_ok=True)
    receipt_path = tools / 'verified-tools.json'
    receipts = read(receipt_path) if receipt_path.exists() else {}
    needed = set()
    for check in selected:
        needed.update({'secrets': ['gitleaks'], 'dependencies': ['osv-scanner'],
                       'workflows': ['actionlint', 'zizmor'], 'selftest': ['gitleaks', 'actionlint', 'zizmor']}.get(check, []))
    for name, spec in lock['binaries'].items():
        if name not in needed:
            continue
        if name == 'osv-scanner' and not (ROOT/'deploy/pilot/requirements-linux-amd64.txt').exists():
            continue
        asset = spec['assets'][key]
        target = tools / name
        if name in receipts and target.exists() and receipts[name]['binary_sha256'] == sha(target) and receipts[name]['version'] == spec['version']:
            continue
        download = tools / 'downloads' / asset['name']
        download.parent.mkdir(exist_ok=True)
        if not download.exists():
            with urlopen(asset['url'], timeout=90) as response:
                download.write_bytes(response.read(150_000_000))
        if sha(download) != asset['sha256']:
            raise RuntimeError('tool download checksum mismatch')
        if asset['name'].endswith('.tar.gz'):
            with tarfile.open(download, 'r:gz') as archive:
                member = next(m for m in archive.getmembers() if m.isfile() and Path(m.name).name == name)
                target.write_bytes(archive.extractfile(member).read())
        else:
            shutil.copyfile(download, target)
        target.chmod(0o755)
        version = execute([target] + spec['version_args'], timeout=30)
        if version.returncode or spec['version'] not in version.stdout + version.stderr:
            raise RuntimeError('unexpected tool version')
        receipts[name] = {'version': spec['version'], 'asset_sha256': asset['sha256'], 'binary_sha256': sha(target)}
        receipt_path.write_text(json.dumps(receipts, indent=2) + '\n')
    images = [lock['images']['semgrep']] if set(selected) & {'sast', 'tests', 'selftest'} else []
    if 'tests' in selected:
        images.append(lock['images']['node'])
    for image in images:
        if execute(['docker', 'image', 'inspect', image]).returncode:
            p = execute(['docker', 'pull', image], timeout=600)
            if p.returncode:
                raise RuntimeError('could not obtain reviewed container image')
    print('bootstrap: PASS (checksummed local tools and pinned images)')

def tracked_sources():
    p = execute(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'])
    if p.returncode:
        raise RuntimeError('cannot enumerate sources')
    return sorted(set(x for x in p.stdout.split('\0') if x))

def source_digest():
    digest = hashlib.sha256()
    for name in tracked_sources():
        if name.startswith('docs/') or name.endswith('.md'):
            continue
        p = ROOT/name
        if p.is_symlink():
            raise RuntimeError('source symlink requires explicit security review')
        if p.is_file():
            digest.update(name.encode()+b'\0'+hashlib.sha256(p.read_bytes()).digest())
    return digest.hexdigest()

def collect_sast(dest):
    count = 0
    mapping = {}
    for name in tracked_sources():
        p = ROOT / name
        if not name.startswith(tuple(read(CONFIG/'profile.json')['sast_roots'])):
            continue
        if name.startswith(('.security/', 'docs/', 'test/', 'tests/', 'tools/security/test_rules/')) or not p.is_file() or p.is_symlink():
            continue
        if name.endswith(('.min.js', '.bundle.js')):
            continue  # vendored assets are covered by hashes/OSV; secrets scan still covers Git history.
        if p.suffix in ('.js', '.mjs', '.py'):
            target = dest / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(p.read_bytes())
            mapping[name] = name
            count += 1
        elif p.suffix == '.html':
            text = p.read_text()
            for i, match in enumerate(re.finditer(r'<script\b([^>]*)>([\s\S]*?)</script\s*>', text, re.I)):
                attributes = match[1]
                if re.search(r'\bsrc\s*=', attributes, re.I) or re.search(r'\btype\s*=\s*[\"\x27](?!module|text/javascript|application/javascript)', attributes, re.I):
                    continue
                rel = name + f'.inline-{i}.js'
                target = dest / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('\n' * text[:match.start(2)].count('\n') + match[2])
                mapping[rel] = name
                count += 1
            # Inline handlers are executable first-party JS too. No HTML or JS is executed here.
            handlers = []
            class HandlerParser(HTMLParser):
                def handle_starttag(self, tag, attrs):
                    for key, value in attrs:
                        if key.lower().startswith('on') and value is not None:
                            handlers.append((self.getpos()[0], value))
            HandlerParser().feed(text)
            for i, (line, value) in enumerate(handlers):
                rel = name + f'.handler-{i}.js'
                target = dest / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('\n' * (line-1) + 'function jscEvent(event) {' + value + '\n}')
                mapping[rel] = name
                count += 1
    if not count:
        raise RuntimeError('no first-party SAST sources collected')
    return count, mapping

def severity(vulnerability, package=None):
    value = (vulnerability.get('database_specific') or {}).get('severity', '').upper()
    if value:
        return {'MODERATE':'MEDIUM'}.get(value,value)
    if package and package.get('ecosystem','').startswith('Debian:'):
        # Debian's package/release-specific assessment, never one from a different suite.
        entries = [x for x in vulnerability.get('affected',[]) if
                   x.get('package',{}).get('name') == package['name'] and
                   x.get('package',{}).get('ecosystem') == package['ecosystem']]
        urgency = next(((x.get('ecosystem_specific') or {}).get('urgency') for x in entries
                        if (x.get('ecosystem_specific') or {}).get('urgency')),None)
        return {'unimportant':'INFO','low':'LOW','medium':'MEDIUM','high':'HIGH'}.get(urgency,'UNKNOWN')
    return 'UNKNOWN'

def run_check(name, tools, out, include_runtime):
    lock = read(CONFIG/'tools.lock.json')
    findings, details, status = [], {}, 'PASS'
    with tempfile.TemporaryDirectory(prefix='trainer-security-') as tmp:
        tmp = Path(tmp)
        if name == 'secrets':
            report = tmp / 'gitleaks.json'
            p = execute([tool(tools, 'gitleaks'), 'git', '--no-banner', '--redact=100', '--config', CONFIG/'gitleaks.toml',
                         '--report-format', 'json', '--report-path', report, '--log-opts=--all', ROOT], timeout=300)
            if p.returncode not in (0, 1) or not report.exists():
                raise RuntimeError('secrets scanner did not produce a complete report')
            raw = read(report)
            if p.returncode == 1 and not raw:
                raise RuntimeError('secrets scanner error without findings')
            reviews = read(CONFIG/'secrets-review.json')['reviews']
            today = dt.datetime.now(dt.timezone.utc).date().isoformat()
            reviewed = []
            for x in raw:
                review = next((v for v in reviews if v['fingerprint'] == x['Fingerprint'] and v['rule'] == x['RuleID'] and
                               v['file'] == x['File'] and v['line'] == x['StartLine'] and today <= v['expires']), None)
                f = finding(x['RuleID'], x['File'], x['StartLine'], 'HIGH')
                if review:
                    reviewed.append({'finding': f, 'expires': review['expires'], 'reason': review['reason']})
                else:
                    findings.append(f)
            details = {'tool': lock['binaries']['gitleaks']['version'], 'scope': 'complete local Git history; default rules plus database URI rule', 'redaction': '100% plus output field allowlist'}
            details['reviewed_false_positives'] = reviewed
            status = 'FAIL' if findings else 'PASS'
        elif name == 'sast':
            sources = tmp / 'source'
            sources.mkdir()
            count, mapping = collect_sast(sources)
            report = tmp / 'semgrep.json'
            p = docker(lock['images']['semgrep'], ['semgrep', 'scan', '--oss-only', '--config', '/config/semgrep.yml', '--metrics=off',
                '--disable-version-check', '--strict', '--error', '--json', '--jobs', '2', '--timeout', '15', '--max-target-bytes', '2000000',
                '--output', '/report/semgrep.json', '/work'],
                [(sources, '/work', False), (CONFIG, '/config', False), (tmp, '/report', True)], timeout=600)
            if p.returncode not in (0, 1) or not report.exists():
                raise RuntimeError('SAST execution failed (raw output withheld)')
            raw = read(report)
            if raw.get('errors'):
                # Parse/timeouts are not silently counted as clean scans.
                raise RuntimeError('SAST reported parse errors or incomplete coverage')
            if len(raw.get('paths', {}).get('scanned', [])) != count:
                raise RuntimeError('SAST skipped a collected first-party source unit')
            for x in raw.get('results', []):
                path = relative(x['path'])
                original = mapping.get(path, path)
                sev = (x['extra'].get('metadata') or {}).get('jsc_severity', 'MEDIUM')
                findings.append(finding(x['check_id'], original, x['start']['line'], sev))
            details = {'tool': 'Semgrep CE 1.186.0', 'source_units': count, 'scanned_units': len(raw.get('paths', {}).get('scanned', [])),
                       'network': 'none', 'rules': 'reviewed local JS/Python rules; inline scripts and handlers extracted with source line mapping',
                       'limitations': 'CE rules are not a complete interfile proof; SQL requires separate review'}
            status = 'FAIL' if any(f['severity'] in ('HIGH', 'CRITICAL') for f in findings) else 'PASS'
        elif name == 'dependencies':
            inputs = read(CONFIG/'advisories.inputs.json')
            for path, digest in inputs['input_sha256'].items():
                if sha(ROOT/path) != digest:
                    raise RuntimeError('dependency SBOM is stale; regenerate from the pinned runtime-deps image')
            if sha(CONFIG/'advisories.cdx.json') != inputs['sbom_sha256']:
                raise RuntimeError('dependency SBOM digest differs from build receipt')
            graph = read(ROOT/'deploy/pilot/python-lock.json')
            installed = {p['name'].lower().replace('_','-'):p['version'] for p in graph['packages']}
            for line in (ROOT/'requirements-dashboard.txt').read_text().splitlines():
                if line and not line.startswith('#'):
                    package, version = line.split('==')
                    if installed.get(package.lower().replace('_','-')) != version:
                        raise RuntimeError('direct dependency pins and native lock differ')
            graphs = [CONFIG/'advisories.cdx.json']
            deployed = read(CONFIG/'deployed.json')
            seen = {sha(graphs[0])}
            for item in deployed['active']:
                graph_path = ROOT/item['sbom']
                if not item['sbom'].startswith('.security/deployed/') or graph_path.is_symlink() or not graph_path.resolve().is_relative_to((CONFIG/'deployed').resolve()):
                    raise RuntimeError('invalid deployed graph path')
                if sha(graph_path) != item['sbom_sha256']:
                    raise RuntimeError('deployed graph checksum mismatch')
                if item['sbom_sha256'] not in seen:
                    graphs.append(graph_path);seen.add(item['sbom_sha256'])
            report = tmp/'osv.json'
            command = [tool(tools,'osv-scanner'),'scan','source','--data-source','native','--no-resolve',
                '--no-call-analysis=all','--all-packages','--format','json','--output-file',report,
                ]
            for graph_path in graphs:command += ['--lockfile', graph_path]
            p = execute(command, timeout=300)
            if p.returncode not in (0,1) or not report.exists():
                raise RuntimeError('OSV did not return complete dependency evidence')
            raw = read(report)
            packages = 0
            for item in raw.get('results',[]):
                for package in item.get('packages',[]):
                    packages += 1
                    for v in package.get('vulnerabilities',[]):
                        f = finding(v['id'],'.security/advisories.cdx.json',severity=severity(v,package['package']),advisory=v['id'])
                        f['package'] = re.sub(r'[^A-Za-z0-9+_.:-]','_',package['package']['name'])[:120]
                        f['version'] = re.sub(r'[^A-Za-z0-9+_.:~-]','_',package['package']['version'])[:100]
                        findings.append(f)
            expected = {(c['name'].lower().replace('_','-'), c['version']) for graph_path in graphs for c in read(graph_path)['components']}
            observed = {(p['package']['name'].lower().replace('_','-'), p['package']['version']) for x in raw.get('results',[]) for p in x.get('packages',[])}
            if not expected <= observed or packages < len(installed):
                raise RuntimeError('OSV dependency coverage incomplete')
            details = {'tool':'OSV Scanner 2.7.1','packages':packages,'python_locked_packages':len(installed),
                'scope':'versioned candidate Linux runtime graph; not an attestation of an already deployed pilot',
                'external_data':'package names/versions only; no source or conversation upload',
                'sqlite_upstream':'3.54.1 checksum-pinned; native version/compatibility tested separately',
                'pip_audit':'not duplicated; OSV already audits the complete Python transitive lock',
                'active_deployed_graphs':len(deployed['active']),
                'deployment_coverage':'NOT VERIFIED / NOT DEPLOYED' if not deployed['active'] else 'versioned retained active graphs',
                'deduplicated_graphs':len(graphs),
                'severity_policy':'Debian suite-specific urgency; unimportant is informational, unassigned remains blocking UNKNOWN; no CVSS score invented'}
            status = 'FAIL' if any(f['severity'] in ('HIGH','CRITICAL','UNKNOWN') for f in findings) else 'PASS'
        elif name == 'workflows':
            files = sorted((ROOT/'.github/workflows').glob('*.y*ml'))
            p = execute([tool(tools, 'actionlint'), '-oneline', '-shellcheck=', '-pyflakes='] + files)
            details['actionlint'] = 'PASS' if p.returncode == 0 else 'FAIL'
            # ShellCheck/pyflakes are explicitly not claimed as installed or run.
            details['shellcheck_pyflakes'] = 'NOT VERIFIED (not installed; actionlint core syntax/expressions checked)'
            if p.returncode:
                status = 'FAIL'
                for line in p.stdout.splitlines():
                    m = re.match(r'(.+?):(\d+):\d+:.*\[([\w-]+)\]', line)
                    if m: findings.append(finding('actionlint:'+m[3], m[1], m[2], 'HIGH'))
            p = execute([tool(tools, 'zizmor'), '--offline', '--strict-collection', '--format=json'] + files)
            if p.returncode not in (0, 11, 12, 13, 14, 1) or not p.stdout.strip():
                raise RuntimeError('workflow security scanner failed')
            raw = json.loads(p.stdout)
            entries = raw if isinstance(raw, list) else raw.get('findings', [])
            for entry in entries:
                rule = entry.get('ident') or entry.get('rule_id') or (entry.get('rule') or {}).get('id') or 'zizmor-finding'
                sev = str((entry.get('determinations') or {}).get('severity') or entry.get('severity') or 'MEDIUM').upper()
                locations = entry.get('locations') or []
                location = locations[0] if locations else {}
                concrete = location.get('concrete') or {}
                symbolic = location.get('symbolic') or {}
                path = symbolic.get('key', {}).get('path', '') if isinstance(symbolic.get('key'), dict) else ''
                path = path or location.get('path') or concrete.get('input') or '.github/workflows/'
                row = (concrete.get('location') or {}).get('start_point', {}).get('row', 0)
                f = finding('zizmor:'+str(rule), str(path), int(row)+1, sev)
                findings.append(f)
                if sev in ('HIGH', 'CRITICAL'): status = 'FAIL'
            details.update({'zizmor': 'PASS' if not entries else 'FINDINGS', 'scope': 'all workflow definitions, including existing deployment/OSV',
                            'versions': 'actionlint 1.7.12; zizmor 1.33.1 offline', 'deployment':'no deployment operations'})
        elif name == 'tests':
            image = 'trainer-security-test:'+execute(['git','rev-parse','HEAD']).stdout.strip()
            p = execute(['docker','build','--platform','linux/amd64','--target','test','--build-arg',
                'SOURCE_REVISION='+execute(['git','rev-parse','HEAD']).stdout.strip(),
                '-f','deploy/pilot/Dockerfile','-t',image,'.'],timeout=1200)
            if p.returncode:
                raise RuntimeError('pinned Linux test image could not be built')
            p = execute(['docker','run','--rm','--platform','linux/amd64','--network','none','--read-only',
                '--cap-drop=ALL','--security-opt=no-new-privileges','--pids-limit=128','--memory=512m',
                '--cpus=1','--tmpfs','/tmp:size=268435456,mode=1777',image],timeout=300)
            if not p.stdout.strip():
                raise RuntimeError('offline test runner produced no evidence')
            result = json.loads(p.stdout)
            details = {'native_linux_tests':result,'network':'none','production_data_used':False,'paid_ai_calls':0}
            status = result['status']
            if result.get('network',{}).get('blocked_attempts'):
                status = 'FAIL'
            q = docker(lock['images']['node'],['node','--test','tests/frontend/conversation.test.cjs',
                'tests/frontend/presentation.test.cjs'],[(ROOT,'/work',False)])
            details['frontend_builtin_node_tests'] = 'PASS' if q.returncode == 0 else 'FAIL'
            if q.returncode:
                status = 'FAIL'
        elif name == 'selftest':
            p = execute([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', str(ROOT/'tools/security/test_rules'), '-q'],
                        env={'JSC_SECURITY_TOOLS': str(tools)}, timeout=600)
            status = 'PASS' if p.returncode == 0 else 'FAIL'
            details = {'fixtures': 'scanner positive/negative, source mapping, hash tampering and report minimization', 'raw_output_withheld': True}
        return write_result(out, name, status, details, findings)

def content_hash(names, extra=''):
    digest = hashlib.sha256(extra.encode())
    for name in sorted(set(names)):
        p = ROOT/name
        if p.is_symlink():
            raise RuntimeError('symlink requires review')
        digest.update(name.encode()+b'\0')
        digest.update(hashlib.sha256(p.read_bytes()).digest() if p.is_file() else b'MISSING')
    return digest.hexdigest()

def identities():
    # A changed engine invalidates every receipt; changes to inputs invalidate only their check.
    names = tracked_sources()
    engine = content_hash(['tools/security/run.py', '.security/tools.lock.json', '.security/profile.json'])
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    history = execute(['git', 'log', '--all', '--format=', '--patch', '--no-ext-diff', '--no-textconv'], timeout=120)
    if history.returncode:
        raise RuntimeError('cannot verify complete Git history')
    selectors = {
        'secrets': [n for n in names if n in ('.security/gitleaks.toml', '.security/secrets-review.json')],
        'sast': [n for n in names if n.startswith(('backend/','frontend/','scripts/','deploy/pilot/','tools/security/')) and n.endswith(('.js','.mjs','.py','.html')) and
                 not n.startswith(('tests/','docs/','tools/security/test_rules/'))] + ['.security/semgrep.yml'],
        'dependencies': ['requirements-dashboard.txt','deploy/pilot/requirements-linux-amd64.txt',
                         'deploy/pilot/python-lock.json','.security/advisories.cdx.json','.security/advisories.inputs.json',
                         'deploy/pilot/Dockerfile','.security/exceptions.json','.security/deployed.json'] + [n for n in names if n.startswith('.security/deployed/')],
        'workflows': [n for n in names if n.startswith('.github/')],
        'tests': [n for n in names if n.startswith(('backend/','frontend/','materials/','profiles/','tests/','deploy/pilot/'))]
                 + ['tools/security/offline_tests.py'],
        'selftest': [n for n in names if n.startswith(('.security/','tools/security/test_rules/')) and not n.endswith('.md')],
    }
    result = {}
    for check, paths in selectors.items():
        extra = engine
        if check == 'secrets':
            # Patch history detects even a secret added then removed; no-op commits do not invalidate it.
            extra += hashlib.sha256(history.stdout.encode()).hexdigest()+today
        if check == 'dependencies':
            extra += today  # OSV knowledge refresh on the next PR/manual event, at most one UTC day old.
        result[check] = content_hash(paths, extra)
    return result

def plan(out):
    ids = identities()
    out.mkdir(parents=True, exist_ok=True)
    value = {'schema': 2, 'inputs': ids, 'key': hashlib.sha256(json.dumps(ids, sort_keys=True).encode()).hexdigest()}
    (out/'plan.json').write_text(json.dumps(value, indent=2)+'\n')
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write('key='+value['key']+'\n')
    return value

def reusable(receipt, check, identity, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    try:
        timestamp = dt.datetime.fromisoformat(receipt['time'])
        age = (now-timestamp).total_seconds()
        return (receipt.get('schema') == 2 and receipt.get('check') == check and
                receipt.get('input_sha256') == identity and receipt.get('status') in ('PASS', 'FAIL') and
                receipt.get('execution') == 'executed' and bool(receipt.get('commit')) and
                0 <= age < 7*86400 and isinstance(receipt.get('findings'), list))
    except (KeyError, ValueError, TypeError):
        return False

def gate(out):
    checks, modes = {}, {}
    current = identities()
    for check in CHECKS:
        path = out/(check+'.json')
        r = read(path) if path.exists() else {}
        checks[check] = r.get('status', 'NOT VERIFIED')
        if checks[check] in ('PASS', 'FAIL') and (r.get('execution') not in ('executed', 'reused verified result') or
                not reusable(dict(r, execution='executed'), check, current[check])):
            checks[check] = 'NOT VERIFIED'
        modes[check] = r.get('execution', 'not executed')
    status = ('FAIL' if 'FAIL' in checks.values() else 'BLOCKED' if 'BLOCKED' in checks.values()
              else 'NOT VERIFIED' if any(x != 'PASS' for x in checks.values()) else 'PASS')
    write_result(out, 'gate', status, {'checks': checks, 'execution': modes, 'required_checks': list(CHECKS),
                                      'skipped_is_not_pass': True})
    commit = execute(['git', 'rev-parse', 'HEAD']).stdout.strip()
    lines = ['# Security result', '', 'Checked commit: `'+commit+'`', '', '| Check | Result | Evidence |', '|---|---|---|']
    lines += [f'| {k} | {v} | {modes[k]} |' for k, v in checks.items()]
    lines += ['', 'Gate: **'+status+'**. Missing, expired or skipped evidence never means PASS.',
              'See each JSON receipt for original checked commit, timestamp and input SHA-256.']
    (out/'summary.md').write_text('\n'.join(lines)+'\n')
    return status

def smart(tools, out, cache, force=False, approved=True):
    ids = plan(out)['inputs']
    selected = []
    # Cache is only a transport. Validate each receipt's input identity, age and terminal status.
    for check in CHECKS:
        p = cache/(check+'.json')
        try:
            old = read(p) if p.exists() and not p.is_symlink() and p.stat().st_size < 1_000_000 else {}
        except (ValueError, OSError):
            old = {}
        if not force and reusable(old, check, ids[check]):
            result = dict(old)
            result['execution'] = 'reused verified result'
            result['current_commit'] = execute(['git', 'rev-parse', 'HEAD']).stdout.strip()
            (out/(check+'.json')).write_text(json.dumps(result, indent=2)+'\n')
            print(check+': '+old['status']+' (reused matching input receipt)')
        else:
            selected.append(check)
    if not approved:
        for check in CHECKS:
            write_result(out, check, 'BLOCKED', {'reason': 'Hosted activation variable is not true.'})
    elif selected:
        try:
            bootstrap(tools, selected)
            ready = True
        except Exception as exc:
            ready = False
            for check in selected:
                write_result(out, check, 'BLOCKED', {'reason': type(exc).__name__, 'message': 'Reviewed tool preparation failed.'})
        for check in selected if ready else []:
            try:
                run_check(check, tools, out, True)
            except Exception as exc:
                write_result(out, check, 'BLOCKED', {'reason': type(exc).__name__, 'message': 'Tool or coverage failure; no raw output published.'})
            result = read(out/(check+'.json'))
            result.update({'schema': 2, 'input_sha256': ids[check], 'execution': 'executed',
                           'run_id': os.environ.get('GITHUB_RUN_ID'), 'run_attempt': os.environ.get('GITHUB_RUN_ATTEMPT')})
            (out/(check+'.json')).write_text(json.dumps(result, indent=2)+'\n')
            if result['status'] in ('PASS', 'FAIL'):
                cache.mkdir(parents=True, exist_ok=True)
                (cache/(check+'.json')).write_text(json.dumps(result, indent=2)+'\n')
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write('executed_count='+str(len(selected) if approved else 0)+'\n')
    (out/'selection.json').write_text(json.dumps({'executed_checks': selected if approved else [],
                                                'reused_checks': [x for x in CHECKS if x not in selected] if approved else []}, indent=2)+'\n')
    return gate(out)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('check', choices=('bootstrap', 'all', 'smart', 'plan', 'gate')+CHECKS)
    parser.add_argument('--tools-dir', type=Path, default=Path(os.environ.get('JSC_SECURITY_TOOLS', str(Path.home()/'.cache/jsc-security'))))
    parser.add_argument('--output', type=Path, default=ROOT/'.security-reports')
    parser.add_argument('--receipts-dir', type=Path, default=ROOT/'.security-receipts')
    parser.add_argument('--runtime', action='store_true', help='Include candidate runtime for explicit local checks.')
    parser.add_argument('--only-dependencies', action='store_true', help='Prepare only OSV for the lightweight advisory monitor')
    parser.add_argument('--force', action='store_true', help='Manually request fresh execution of all checks.')
    args = parser.parse_args()
    tools, out = args.tools_dir.resolve(), args.output.resolve()
    if args.check == 'plan':
        plan(out)
        return 0
    if args.check == 'bootstrap':
        bootstrap(tools, ('dependencies',) if args.only_dependencies else CHECKS)
        return 0
    if args.check == 'gate':
        return int(gate(out) != 'PASS')
    if args.check in ('smart', 'all'):
        approved = os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('JSC_HOSTED_APPROVED') == 'true'
        return int(smart(tools, out, args.receipts_dir.resolve(), args.force or args.check == 'all', approved) != 'PASS')
    try:
        run_check(args.check, tools, out, args.runtime)
        result = read(out/(args.check+'.json'))
        result.update({'schema': 2, 'input_sha256': identities()[args.check], 'execution': 'executed'})
        (out/(args.check+'.json')).write_text(json.dumps(result, indent=2)+'\n')
    except Exception as exc:
        write_result(out, args.check, 'BLOCKED', {'reason': type(exc).__name__})
    return int(read(out/(args.check+'.json'))['status'] != 'PASS')

if __name__ == '__main__':
    sys.exit(main())
