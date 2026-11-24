"""Python layer: pinned requirements install, and every import in the tracked files resolves."""
import argparse
import ast
import json
import subprocess
import sys
import venv
from collections import namedtuple
from pathlib import Path, PurePosixPath

import check_cli
import common

REPO_ROOT = check_cli.REPO_ROOT
INSTALL_TIMEOUT = 600
RESOLVE_TIMEOUT = 300

Unit = namedtuple('Unit', 'name cloud directory files requirements')

# Run by the unit's venv interpreter, in isolated mode: reads the entries as JSON on stdin.
RESOLVER = '''
import importlib.util, json, sys
entries = json.load(sys.stdin)
unresolved = []
for entry in entries:
    sys.path[:0] = [entry['directory'], entry['root']]
    for module, line in entry['imports']:
        if module.split('.')[0] in sys.stdlib_module_names:
            continue
        try:
            found = importlib.util.find_spec(module) is not None
        except (ImportError, ValueError, AttributeError):
            found = False
        if not found:
            unresolved.append({'file': entry['file'], 'line': line, 'module': module})
    del sys.path[:2]
json.dump(unresolved, sys.stdout)
'''


def covering_directory(directory, requirement_dirs):
    """Nearest directory at or above `directory` that has a requirements.txt, or None."""
    for candidate in (directory, *directory.parents):
        if candidate in requirement_dirs:
            return candidate
    return None


def build_units(cloud, files, parent_requirements):
    """Group the tracked .py files into units; each unit is installed once in its own venv."""
    names = [PurePosixPath(name) for name in files if not name.startswith(check_cli.EXCLUDED)]
    requirement_dirs = {name.parent for name in names if name.name == 'requirements.txt'}
    grouped = {}
    for name in names:
        if name.suffix != '.py':
            continue
        if 'aws' in name.parent.parts:
            if cloud != 'aws':
                continue
            index = name.parent.parts.index('aws')
            unit_dir = PurePosixPath(*name.parent.parts[:index + 1])
        else:
            if cloud != 'azure':
                continue
            unit_dir = covering_directory(name.parent, requirement_dirs)
            if unit_dir is None:
                continue
        grouped.setdefault(unit_dir, []).append(str(name))
    units = []
    for unit_dir, members in sorted(grouped.items()):
        if cloud == 'azure':
            requirements = ['-r', str(unit_dir / 'requirements.txt')]
        elif unit_dir in requirement_dirs:
            requirements = ['-r', str(unit_dir / 'requirements.txt')]
        elif str(unit_dir) in parent_requirements:
            requirements = ['-r', str(unit_dir.parent / 'requirements.txt'), 'boto3']
        else:
            requirements = ['boto3']
        units.append(Unit(str(unit_dir).replace('/', '_'), cloud, str(unit_dir), sorted(members), requirements))
    return units


def collect_imports(source):
    """Return (module, line) for every absolute import statement, at any depth."""
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found.extend((alias.name, node.lineno) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.append((node.module, node.lineno))
    return sorted(found, key=lambda item: item[1])


def resolve(python, entries):
    """Run the resolver with `python`; return the imports that do not resolve."""
    done = subprocess.run([python, '-I', '-c', RESOLVER], input=json.dumps(entries), capture_output=True, text=True,
                          timeout=RESOLVE_TIMEOUT)
    if done.returncode != 0:
        raise RuntimeError(done.stderr.strip().splitlines()[-1] if done.stderr.strip() else 'resolver failed')
    return json.loads(done.stdout)


def last_line(text):
    lines = [line for line in text.strip().splitlines() if line.strip()]
    return lines[-1] if lines else ''


def is_skipped(module, skip_imports):
    for entry in skip_imports:
        if module == entry['target'] or module.startswith(entry['target'] + '.'):
            return entry
    return None


def run_unit(unit, root, venv_dir, skip, pip=None, timeout=INSTALL_TIMEOUT):
    """Install the unit's requirements and resolve its imports; write the rows."""
    root = Path(root)
    venv_dir = Path(venv_dir)
    where = dict(cloud=unit.cloud, exercise=check_cli.exercise_of(unit.directory), layer='python')
    if not venv_dir.exists():
        venv.create(venv_dir, with_pip=pip is None)
    python = str(venv_dir / 'bin' / 'python')
    command = [*(pip or [python, '-m', 'pip']), 'install', '--disable-pip-version-check', *unit.requirements]
    target = ' '.join(unit.requirements)
    log = common.log_path(f'python-{unit.name}.log')
    try:
        with log.open('w', encoding='utf-8') as output:
            done = subprocess.run(command, cwd=root, stdin=subprocess.DEVNULL, stdout=output,
                                  stderr=subprocess.STDOUT, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as error:
        common.write_row(target=target, check='install', status='infrastructure', error=str(error), **where)
        return
    if done.returncode != 0:
        error = last_line(log.read_text(errors='replace'))
        common.write_row(target=target, check='install', status='drift', error=error, **where)
        return
    common.write_row(target=target, check='install', status='ok', **where)
    exercise_root = root / unit.directory.split('/')[0]
    entries = []
    for name in unit.files:
        imports = collect_imports((root / name).read_text(encoding='utf-8'))
        entries.append({'file': name, 'directory': str(root / name).rsplit('/', 1)[0], 'root': str(exercise_root),
                        'imports': imports})
    try:
        unresolved = resolve(python, entries)
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        common.write_row(target=unit.name, check='import', status='infrastructure', error=str(error), **where)
        return
    for item in unresolved:
        entry = is_skipped(item['module'], skip)
        if entry:
            common.write_row(target=item['module'], file=item['file'], line=item['line'], check='import',
                             status='skipped', reason=entry['reason'], **where)
        else:
            common.write_row(target=item['module'], file=item['file'], line=item['line'], check='import',
                             status='drift', error='no module found', **where)


def main(argv=None, root=REPO_ROOT, files=None, pip=None, timeout=INSTALL_TIMEOUT):
    parser = argparse.ArgumentParser()
    parser.add_argument('--cloud', choices=('azure', 'aws'), required=True)
    parser.add_argument('--unit')
    args = parser.parse_args(argv)
    python = common.load_targets().get('python') or {}
    if files is None:
        files = subprocess.run(['git', 'ls-files'], cwd=root, capture_output=True, text=True,
                               check=True).stdout.splitlines()
    units = build_units(args.cloud, files, python.get('parent_requirements') or [])
    if args.unit:
        units = [unit for unit in units if unit.name == args.unit]
    skip = python.get('skip_imports') or []
    for unit in units:
        print(f'{args.cloud}: {unit.name}', flush=True)
        run_unit(unit, root, common.base_dir() / 'venvs' / unit.name, skip, pip=pip, timeout=timeout)
    return 0


if __name__ == '__main__':
    sys.exit(main())
