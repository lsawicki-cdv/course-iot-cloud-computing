"""Results file, masking and targets for the daily API check."""
import argparse
import json
import os
import re
import shlex
import shutil
import tempfile
from pathlib import Path

STATUSES = {
    'ok', 'missing-command', 'missing-flag', 'drift', 'not-covered', 'newly-covered',
    'consequential', 'skipped', 'infrastructure', 'pending',
}
FIELDS = ('cloud', 'exercise', 'layer', 'target', 'file', 'line', 'check', 'status', 'error', 'reason')
ROW_KEY = ('cloud', 'exercise', 'layer', 'target', 'file', 'line', 'check')
# Required keys per kind of entry in the `aws` section of targets.yml.
AWS_REQUIRED = {
    'script': {'exercise', 'directory', 'script', 'working_directory'},
    'cloudformation': {'exercise', 'directory', 'working_directory', 'template', 'stack_name', 'capabilities'},
    'terraform': {'exercise', 'directory', 'working_directory'},
    'cfn-lint': {'exercise', 'directory', 'template'},
}
TARGETS_FILE = Path(__file__).with_name('targets.yml')

_SECRET = r'[\w-]*(?:password|secret|key|token)[\w-]*'
_VALUE = r'''"[^"]*"|'[^']*'|[^\s,}&"']+'''
_FLAG_VALUE = re.compile(rf'(--{_SECRET}\s+)(?:{_VALUE})', re.IGNORECASE)
_NAME_VALUE = re.compile(rf'(\b{_SECRET}=)(?:{_VALUE})', re.IGNORECASE)
_CODE_VALUE = re.compile(r'([?&]code=)[^&\s"\']+')


def base_dir():
    root = os.environ.get('RUNNER_TEMP') or tempfile.gettempdir()
    return Path(root) / 'api-check'


def results_path():
    return base_dir() / 'results.jsonl'


def log_path(name):
    logs = base_dir() / 'logs'
    logs.mkdir(parents=True, exist_ok=True)
    return logs / name


def mask(text):
    text = _FLAG_VALUE.sub(r'\1***', text)
    text = _NAME_VALUE.sub(r'\1***', text)
    return _CODE_VALUE.sub(r'\1***', text)


def write_row(**fields):
    if fields.get('status') not in STATUSES:
        raise ValueError(f"unknown status: {fields.get('status')!r}")
    unknown = set(fields) - set(FIELDS)
    if unknown:
        raise ValueError(f'unknown fields: {sorted(unknown)}')
    row = {name: fields.get(name) for name in FIELDS}
    for name in ('target', 'error', 'reason'):
        if row[name]:
            row[name] = mask(row[name])
    if row['error']:
        row['error'] = row['error'][:200]
    path = results_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as results:
        results.write(json.dumps(row) + '\n')


def read_rows():
    path = results_path()
    if not path.exists():
        return []
    rows = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.strip():
            row = json.loads(line)
            rows[tuple(row.get(name) for name in ROW_KEY)] = row
    return list(rows.values())


def load_targets(path=TARGETS_FILE):
    import yaml

    with open(path, encoding='utf-8') as targets_file:
        targets = yaml.safe_load(targets_file) or {}
    for section in ('skip', 'emulator_gaps'):
        for entry in targets.get(section) or []:
            if not entry.get('reason'):
                raise ValueError(f'{section} entry without a reason: {entry}')
    for entry in targets.get('emulator_gaps') or []:
        if not entry.get('exercise') or not (entry.get('pattern') or entry.get('target')):
            raise ValueError(f'emulator_gaps entry needs exercise and pattern or target: {entry}')
    for entry in targets.get('aws') or []:
        missing = AWS_REQUIRED[entry.get('kind')] - set(entry) if entry.get('kind') in AWS_REQUIRED else {'kind'}
        if missing:
            raise ValueError(f'aws entry {entry} lacks {sorted(missing)}')
    return targets


def raw_log_path():
    return base_dir() / 'aws-calls.jsonl'


def write_raw_call(script, line, argv, exit_code, stderr, timed_out):
    """Append one masked aws call to the raw log."""
    masked = shlex.split(mask(shlex.join(argv)))
    entry = {'script': script, 'line': line, 'argv': masked, 'exit': exit_code,
             'stderr': mask(stderr), 'timed_out': timed_out}
    path = raw_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as raw_log:
        raw_log.write(json.dumps(entry) + '\n')


def main(argv=None):
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('reset')
    infra = commands.add_parser('infra')
    infra.add_argument('--cloud', required=True)
    infra.add_argument('--check', required=True)
    infra.add_argument('--error', required=True)
    raw = commands.add_parser('rawlog')
    raw.add_argument('--script', default='')
    raw.add_argument('--line', default='')
    raw.add_argument('--exit', type=int, required=True)
    raw.add_argument('--timed-out', type=int, default=0)
    raw.add_argument('--stderr-file', required=True)
    raw.add_argument('call', nargs='*')
    args = parser.parse_args(argv)
    if args.command == 'rawlog':
        stderr = Path(args.stderr_file).read_text(encoding='utf-8', errors='replace')
        write_raw_call(args.script, args.line, args.call, args.exit, stderr, bool(args.timed_out))
    elif args.command == 'reset':
        shutil.rmtree(base_dir(), ignore_errors=True)
    else:
        write_row(cloud=args.cloud, layer='static', check=args.check, status='infrastructure', error=args.error)


if __name__ == '__main__':
    main()
