#!/usr/bin/env python3
"""Limited real MISSION 02 evaluation. Raw outputs stay in reports/private.
No automatic semantic PASS. No API retries or model substitution.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
from backend.app.actor_prompt import ACTOR_PROMPT, build_actor_messages

ARCHIVE = ROOT / 'research/feasibility'


def load():
    return runpy.run_path(str(ARCHIVE / 'feasibility_spike.py'))


def inputs():
    old = json.loads((ARCHIVE / 'remediation/run-002/results.json').read_text())
    spec = json.loads((ROOT / 'tests/evals/actor_grounding_cases.json').read_text())
    suite = json.loads((ARCHIVE / 'test_cases.json').read_text())
    cases = {case['id']: case for case in suite['cases']}
    groups = {}
    for number in spec['historical_events']:
        event = old['events'][number-1]
        call = old['calls'][event['call_indices'][1]]
        group = groups.setdefault(call['request_sha256'], {'original_events': [], 'request': call['request']})
        group['original_events'].append(number)
    assert len(groups) == 4
    tasks = []
    for rep in range(spec['repetitions']):
        for number, group in enumerate(groups.values(), 1):
            original_input = group['request']['input']
            context = json.loads(original_input[0]['content'].split('\n')[-1])
            tasks.append({'label': f'historical/{rep}/{number}', 'original_events': group['original_events'],
                          'context': context, 'history': original_input[1:-1], 'question': original_input[-1]['content']})
        context = {'public_scenario': load()['PUBLIC'], 'released_facts': [], 'reaction': 'neutral'}
        for case in spec['boundary_cases']:
            tasks.append({'label': f'boundary/{rep}/{case["id"]}', 'context': context, 'history': [], 'question': case['question']})
        for case_id in spec['attack_case_ids']:
            tasks.append({'label': f'attack/{rep}/{case_id}', 'context': context, 'history': [], 'question': cases[case_id]['question']})
    assert len(tasks) == 20
    return old, spec, cases, tasks


def local_checks():
    subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests/unit', '-v'], cwd=ROOT, check=True)
    subprocess.run([sys.executable, str(ROOT / 'scripts/check_workspace.py')], cwd=ROOT, check=True)
    old, spec, cases, tasks = inputs()
    assert spec['repetitions'] == 2 and len(spec['conversation_case_ids']) == 5
    assert {i for task in tasks for i in task.get('original_events', [])} == set(spec['historical_events'])
    for task in tasks:
        messages = build_actor_messages(task['context'], task['history'], task['question'])
        assert json.loads(messages[0]['content'].split('\n')[-1]) == task['context']
    spike = load()
    assert spike['DIRECTOR'] == old['director_prompt']
    return {'passed': True, 'unique_historical_inputs': 4, 'historical_events_covered': 13,
            'planned_actor_calls': 30, 'planned_director_calls': 10, 'planned_api_calls': 40}


def execute(args):
    checks = local_checks()
    old, spec, cases, tasks = inputs()
    spike = load()
    director = spike['DIRECTOR']
    # Change only Actor instructions in this isolated in-memory PoC runtime.
    spike['turn'].__globals__['ACTOR'] = ACTOR_PROMPT
    assert spike['turn'].__globals__['DIRECTOR'] == director == old['director_prompt']
    os.umask(0o077)
    output_dir = ROOT / 'reports/private' / ('actor-grounding-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    output_dir.mkdir(parents=True, mode=0o700)
    output_dir.parent.chmod(0o700)
    output = output_dir / 'results.json'
    result = {'status': 'RUNNING', 'model': old['model'], 'created_at': datetime.now(timezone.utc).isoformat(),
              'api_attempts': 0, 'api_successes': 0, 'calls': [], 'events': [], 'local_checks': checks,
              'actor_prompt': ACTOR_PROMPT, 'actor_prompt_sha256': hashlib.sha256(ACTOR_PROMPT.encode()).hexdigest(),
              'director_prompt_sha256': hashlib.sha256(director.encode()).hexdigest(),
              'cases_sha256': hashlib.sha256((ROOT / 'tests/evals/actor_grounding_cases.json').read_bytes()).hexdigest(),
              'archive_source_sha256': hashlib.sha256((ARCHIVE / 'feasibility_spike.py').read_bytes()).hexdigest(),
              'cost_from_api': None}
    spike['save'](output_dir / 'plan.json', {'isolated_actor_cases': tasks, 'conversations': spec['conversation_case_ids'], 'repetitions': 2})
    try:
        key = spike['load_key'](args.env_file)
        if not key:
            raise RuntimeError('BLOCKED: API key unavailable in environment or the selected local configuration')
        api = spike['API'](key, result['model'], result, output)
        for task in tasks:
            messages = build_actor_messages(task['context'], task['history'], task['question'])
            answer, index = api.call('actor', messages)
            event = {'label': task['label'], 'original_events': task.get('original_events', []),
                     'question': task['question'], 'context': task['context'], 'actor_answer': answer,
                     'call_indices': [index], 'review': None}
            result['events'].append(event)
            spike['save'](output, result)
            print(task['label'], 'completed', flush=True)
        for rep in range(2):
            state = spike['fresh_state']()
            for step, case_id in enumerate(spec['conversation_case_ids']):
                spike['turn'](api, cases[case_id], state, f'conversation/{rep}/{step}')
                event = result['events'][-1]
                actor_call = result['calls'][event['call_indices'][1]]
                context = json.loads(actor_call['request']['input'][0]['content'].split('\n')[-1])
                assert actor_call['request']['input'] == build_actor_messages(context, state['history'][:-2], event['question'])
                assert result['calls'][event['call_indices'][0]]['request']['input'][0]['content'] == director
                print(event['label'], 'correct=' + str(event['classification_correct']), flush=True)
        result['status'] = 'AWAITING_MANUAL_REVIEW'
    except (RuntimeError, ValueError, KeyError) as exc:
        result['status'] = 'BLOCKED'
        result['block_reason'] = str(exc)
    finally:
        result['metrics'] = {
            'input_tokens': sum(c.get('response', {}).get('usage', {}).get('input_tokens', 0) for c in result['calls']),
            'output_tokens': sum(c.get('response', {}).get('usage', {}).get('output_tokens', 0) for c in result['calls']),
            'director_correct': sum(e.get('classification_correct', False) for e in result['events']),
            'director_total': sum('director' in e for e in result['events'])}
        spike['save'](output, result)
    print(result['status'], result['api_attempts'], 'API attempts;', result['api_successes'], 'successful')
    print('Results:', output)
    return 2 if result['status'] == 'BLOCKED' else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--local-checks', action='store_true')
    modes.add_argument('--paid', action='store_true')
    parser.add_argument('--env-file', type=Path, default=ROOT / '.env')
    args = parser.parse_args()
    if args.local_checks:
        print(json.dumps(local_checks()))
        return 0
    return execute(args)


if __name__ == '__main__':
    sys.exit(main())
