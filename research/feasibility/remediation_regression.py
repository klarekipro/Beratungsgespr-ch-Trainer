#!/usr/bin/env python3
"""Mission 00.2 regression only; no mocks, no overwrite of original artifacts.
Local checks: python3 remediation_regression.py --local-checks
Real tests: python3 remediation_regression.py --run
Successful execution still requires a manual semantic review; never auto-PASS.
"""
import argparse
import ast
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
spike = runpy.run_path(str(ROOT / 'feasibility_spike.py'))


def read(name):
    return json.loads((ROOT / name).read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plan():
    suite = read('test_cases.json')
    original = read('results.json')
    extra = read('remediation/additional_cases.json')
    tasks = []
    cases = {c['id']: c for c in suite['cases']}
    for rep in range(suite['repetitions']):
        for case in suite['cases']:
            tasks.append({'label': f'independent/{rep}/{case["id"]}', 'case': case,
                          'state_group': None, 'initial_state': None})
        for conversation in suite['conversations']:
            for step, case_id in enumerate(conversation['case_ids']):
                group = f'conversation/{conversation["id"]}/{rep}'
                tasks.append({'label': f'{group}/{step}', 'case': cases[case_id],
                              'state_group': group, 'initial_state': None})
    # Replay the exact original allowed state and Actor history, not a newly
    # corrected flow. These historical contexts are marked as replay-only.
    for number, event in enumerate(original['events'], 1):
        if set(event['expected_categories']) == set(event['director']['categories']):
            continue
        old_actor = original['calls'][event['call_indices'][1]]['request']['input']
        context = json.loads(old_actor[0]['content'].split('\n')[-1])
        state = {'allowed': event['allowed_before'], 'reaction': context['reaction'],
                 'history': old_actor[1:-1]}
        tasks.append({'label': f'replay_original/{number}', 'case': cases[event['case_id']],
                      'state_group': None, 'initial_state': state, 'original_event': number})
    for rep in range(extra['repetitions']):
        for case in extra['cases']:
            tasks.append({'label': f'additional/{rep}/{case["id"]}', 'case': case,
                          'state_group': None, 'initial_state': {
                              'allowed': case['initial_allowed'], 'reaction': 'neutral', 'history': []}})
    return tasks


def local_checks():
    manifest = read('remediation/before/sha256.json')
    for name, expected in manifest.items():
        if name != 'feasibility_spike.py':
            if digest(ROOT / name) != expected:
                raise ValueError('Original artifact changed: ' + name)
    # Existing implementation may differ only in the DIRECTOR assignment.
    before = ast.parse((ROOT / 'remediation/before/feasibility_spike.py').read_text())
    after = ast.parse((ROOT / 'feasibility_spike.py').read_text())
    for tree in (before, after):
        tree.body = [node for node in tree.body if not (
            isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'DIRECTOR' for t in node.targets))]
    assert ast.dump(before) == ast.dump(after), 'Change outside Director instructions'
    tasks = plan()
    assert len(tasks) == 74 and len({t['label'] for t in tasks}) == 74
    assert sum(t['label'].startswith('independent/') and t['case']['baseline'] for t in tasks) == 20
    replay = [t for t in tasks if t['label'].startswith('replay_original/')]
    assert [t['original_event'] for t in replay] == [9,13,15,18,36,40,42,45]
    for t in replay:
        event = read('results.json')['events'][t['original_event']-1]
        call = read('results.json')['calls'][event['call_indices'][0]]
        old = json.loads(call['request']['input'][-1]['content'])
        assert old['question'] == t['case']['question']
        assert old['allowed_information'] == {k: spike['FACTS'][k] for k in t['initial_state']['allowed']}
    for t in tasks:
        assert set(t['case']['expected_categories']) <= {'A','B','C','NONE','PRESSURE'}
    # Test actual validation and isolation, never substitute model outputs.
    for invalid in ([], ['A','A'], ['NONE','A'], ['UNKNOWN']):
        try:
            spike['validate_director']({'categories': invalid, 'reasons': ['validation input'], 'confident': True})
        except ValueError:
            pass
        else:
            raise AssertionError('Invalid categories accepted')
    first, second = spike['fresh_state'](), spike['fresh_state']()
    first['allowed'].add('A')
    assert not second['allowed'] and not second['history']
    return {'passed': True, 'checks': [
        'original artifact hashes unchanged', 'only Director assignment changed in existing script',
        '20 baseline checks / two runs', 'all eight original error contexts replayed exactly',
        'two attacks / three five-turn conversations / two runs',
        'six frozen additional cases / two runs', 'decision validation and isolated state'],
        'planned_events': len(tasks), 'planned_api_calls': len(tasks)*2}


def execute(output_dir):
    checks = local_checks()  # Must precede any API call.
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / 'results.json'
    if output.exists():
        raise ValueError('Refusing to overwrite prior run; choose another --output-dir')
    tasks = plan()
    spike['save'](output_dir / 'plan.json', tasks)
    result = {'status': 'RUNNING', 'created_at': datetime.now(timezone.utc).isoformat(),
              'model': 'gpt-4.1-mini-2025-04-14', 'api_attempts': 0, 'api_successes': 0,
              'baseline_ids': read('test_cases.json')['cases'][:10],
              'calls': [], 'events': [], 'cost_from_api': None,
              'local_checks': checks, 'original_sha256': read('remediation/before/sha256.json'),
              'director_prompt': spike['DIRECTOR'],
              'script_sha256': digest(ROOT / 'feasibility_spike.py'),
              'runner_sha256': digest(Path(__file__)),
              'additional_cases_sha256': digest(ROOT / 'remediation/additional_cases.json')}
    result['baseline_ids'] = [c['id'] for c in result['baseline_ids']]
    try:
        key = spike['load_key'](ROOT / '.env')
        if not key:
            raise RuntimeError('API-ключ отсутствует в окружении и локальном .env; реальные тесты не выполнены.')
        api = spike['API'](key, result['model'], result, output)
        states = {}
        for task in tasks:
            if task['state_group']:
                state = states.setdefault(task['state_group'], spike['fresh_state']())
            elif task['initial_state']:
                state = copy.deepcopy(task['initial_state'])
                state['allowed'] = set(state['allowed'])
            else:
                state = spike['fresh_state']()
            spike['turn'](api, task['case'], state, task['label'])
            event = result['events'][-1]
            event['original_event'] = task.get('original_event')
            event['disclosure_log'] = [{
                'fact': fact, 'question': task['case']['question'],
                'director_reasons': event['director']['reasons'],
                'confident': event['director']['confident'],
                'program_rule': 'New category + confident=true; semantic justification still needs human review.'
            } for fact in event['newly_released']]
            spike['save'](output, result)
            print(task['label'], 'correct=' + str(event['classification_correct']), flush=True)
        result['status'] = 'AWAITING_MANUAL_REVIEW'
    except (RuntimeError, ValueError, KeyError) as exc:
        result['status'] = 'BLOCKED'
        result['block_reason'] = str(exc)
    spike['summarize'](result)
    spike['save'](output, result)
    print(result['status'], result['api_attempts'], 'API attempts;', result['api_successes'], 'successful')
    return 2 if result['status'] == 'BLOCKED' else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--local-checks', action='store_true')
    mode.add_argument('--run', action='store_true')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'remediation' / ('run-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')))
    args = parser.parse_args()
    if args.local_checks:
        checks = local_checks()
        spike['save'](ROOT / 'remediation/local_checks.json', checks)
        print(json.dumps(checks, ensure_ascii=False))
        return 0
    return execute(args.output_dir.resolve())


if __name__ == '__main__':
    sys.exit(main())
