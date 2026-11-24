"""Job summary and failure policy for the daily API check."""
import argparse
import json
import os
import sys
from collections import Counter

import common

FAILING = {'missing-command', 'missing-flag', 'drift', 'infrastructure'}
NOT_FAILING = ('not-covered', 'newly-covered', 'consequential', 'skipped')
FOOTER = ('Not checked: short flags (`-x`), positional arguments, and the data plane '
          '(only control-plane commands and flags are verified).')


def step_rows(cloud, steps):
    return [
        dict(cloud=cloud, layer='infrastructure', check=step_id, status='infrastructure', error='step failed')
        for step_id, step in steps.items() if step.get('outcome') == 'failure'
    ]


def normalise(row):
    """Pending targets were never finished; mask the text again on output."""
    row = dict(row)
    if row['status'] == 'pending':
        row.update(status='infrastructure', error='not reached')
    if row['status'] == 'infrastructure':
        row['layer'] = 'infrastructure'
    for name in ('target', 'error', 'reason'):
        if row.get(name):
            row[name] = common.mask(row[name])
    return row


def cell(value):
    return str(value if value is not None else '').replace('|', '\\|').replace('\n', ' ')


def where(row):
    if not row.get('file'):
        return row.get('target')
    place = f"{row['file']}:{row['line']}" if row.get('line') else row['file']
    return f"{place} `{row['target']}`" if row.get('target') else place


def table(rows, last_column):
    lines = [f'| exercise | layer | file:line or target | check | status | {last_column} |',
             '| --- | --- | --- | --- | --- | --- |']
    for row in rows:
        detail = row.get('error') if last_column == 'error' else row.get('reason')
        cells = (row.get('exercise'), row.get('layer'), where(row), row.get('check'), row['status'], detail)
        lines.append('| ' + ' | '.join(cell(value) for value in cells) + ' |')
    return lines


def exercise_number(row):
    return int(row['exercise']) if str(row.get('exercise')).isdigit() else 0


def sort_key(row):
    return (row['layer'] != 'infrastructure', exercise_number(row), str(row.get('layer')),
            str(row.get('file')), row.get('line') or 0, str(row.get('target')), str(row.get('check')))


def render(cloud, rows):
    failing = sorted((row for row in rows if row['status'] in FAILING), key=sort_key)
    other = sorted((row for row in rows if row['status'] in NOT_FAILING), key=sort_key)
    counts = Counter(row['status'] for row in rows)
    lines = [f'## Daily API check: {cloud}', '', f'### Failing ({len(failing)})', '']
    lines += table(failing, 'error') if failing else ['None.']
    lines += ['', f'### Not failing ({len(other)})', '']
    lines += table(other, 'reason') if other else ['None.']
    lines += ['', FOOTER, '', 'Counts: ' + (', '.join(f'{n} {status}' for status, n in sorted(counts.items())) or 'no rows')]
    return '\n'.join(lines) + '\n', bool(failing)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--cloud', required=True)
    parser.add_argument('--steps-json', default=os.environ.get('STEPS_JSON') or '{}')
    args = parser.parse_args(argv)
    rows = [normalise(row) for row in common.read_rows() if row.get('cloud') == args.cloud]
    rows += step_rows(args.cloud, json.loads(args.steps_json))
    text, failed = render(args.cloud, rows)
    target = os.environ.get('GITHUB_STEP_SUMMARY')
    if target:
        with open(target, 'a', encoding='utf-8') as step_summary:
            step_summary.write(text)
    else:
        sys.stdout.write(text)
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
