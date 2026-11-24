"""Azure targets: Bicep build, Terraform validate and the exercise 9 sample against the Cosmos DB emulator."""
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import check_cli
import common

REPO_ROOT = check_cli.REPO_ROOT
BUILD_TIMEOUT = 300
SAMPLE_TIMEOUT = 600
PROBE_TRIES = 60
PROBE_INTERVAL = 5
EMULATOR_IMAGE = 'mcr.microsoft.com/cosmosdb/linux/azure-cosmos-emulator:vnext-preview'
EMULATOR_HOST = 'http://127.0.0.1:8081/'
# The emulator's documented, public well-known key (not a secret).
EMULATOR_KEY = 'C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw=='
SAMPLE_MARKER = 'run_sample has caught an error'
# Run by the exercise 9 venv: TCP connect, then list databases.
PROBE = '''
import os, socket
from azure.cosmos import CosmosClient
socket.create_connection(("127.0.0.1", 8081), timeout=5).close()
list(CosmosClient(os.environ["ACCOUNT_HOST"], {"masterKey": os.environ["ACCOUNT_KEY"]}).list_databases())
'''


def last_line(text):
    lines = [line for line in text.strip().splitlines() if line.strip()]
    return lines[-1] if lines else ''


def classify_bicep(returncode, stderr):
    """Any error, or warning BCP081 (resource type unavailable for that API version), is drift."""
    for line in stderr.splitlines():
        if re.search(r'\bError\b', line) or 'Warning BCP081' in line:
            return 'drift', line.strip()
    if returncode != 0:
        return 'drift', last_line(stderr) or f'exit {returncode}'
    return 'ok', None


def classify_terraform(text):
    """Return (target, status, error) per error diagnostic, or one ok row when valid."""
    try:
        result = json.loads(text)
    except ValueError:
        return [('terraform validate', 'drift', last_line(text) or 'no JSON output')]
    errors = [item for item in result.get('diagnostics') or [] if item.get('severity') == 'error']
    if result.get('valid') and not errors:
        return [('terraform validate', 'ok', None)]
    rows = []
    for item in errors:
        where = item.get('range') or {}
        address = f"{where.get('filename', '?')}:{(where.get('start') or {}).get('line', '?')}"
        rows.append((address, 'drift', item.get('summary', '')))
    return rows or [('terraform validate', 'drift', 'invalid')]


def classify_sample(returncode, stdout, gaps):
    """Return (status, error, reason); the sample catches API errors and exits 0, so read its output."""
    if returncode == 0 and SAMPLE_MARKER not in stdout:
        return 'ok', None, None
    error = last_line(stdout) if returncode != 0 else stdout[stdout.index(SAMPLE_MARKER):].splitlines()[0]
    for gap in gaps:
        if re.search(gap['pattern'], stdout):
            return 'not-covered', error, gap['reason']
    return 'drift', error, None


def run_logged(command, log, cwd, timeout, env=None):
    """Run a command with output in the log file; return the exit code, or None on timeout."""
    try:
        with open(log, 'w', encoding='utf-8') as output:
            return subprocess.run(command, cwd=cwd, stdin=subprocess.DEVNULL, stdout=output,
                                  stderr=subprocess.STDOUT, timeout=timeout, env=env).returncode
    except subprocess.TimeoutExpired:
        return None


def run_bicep(entry, root, where):
    log = common.log_path(f"azure-bicep-{entry['exercise']}.log")
    stderr_log = log.with_suffix('.stderr')
    try:
        with open(log, 'w', encoding='utf-8') as output, open(stderr_log, 'w', encoding='utf-8') as errors:
            done = subprocess.run(['az', 'bicep', 'build', '--file', 'main.bicep', '--stdout'],
                                  cwd=root / entry['directory'], stdin=subprocess.DEVNULL, stdout=output,
                                  stderr=errors, timeout=BUILD_TIMEOUT)
    except subprocess.TimeoutExpired:
        common.write_row(target='az bicep build', check='build', status='drift', error='timeout', **where)
        return
    status, error = classify_bicep(done.returncode, stderr_log.read_text(errors='replace'))
    common.write_row(target='az bicep build', check='build', status=status, error=error, **where)


def run_terraform(entry, root, where):
    with tempfile.TemporaryDirectory() as copy:
        archive = subprocess.run(['git', 'archive', 'HEAD', entry['directory']], cwd=root, capture_output=True,
                                 check=True).stdout
        subprocess.run(['tar', '-x', '-C', copy], input=archive, check=True)
        directory = Path(copy) / entry['directory']
        log = common.log_path(f"azure-terraform-{entry['exercise']}.log")
        code = run_logged(['terraform', 'init', '-backend=false', '-input=false'], log, directory, BUILD_TIMEOUT)
        if code != 0:
            error = 'timeout' if code is None else last_line(log.read_text(errors='replace'))
            # Keyed as the pending row, so it is closed.
            common.write_row(target='terraform validate', check='validate', status='drift',
                             error=f'init: {error}', **where)
            return
        try:
            done = subprocess.run(['terraform', 'validate', '-json'], cwd=directory, stdin=subprocess.DEVNULL,
                                  capture_output=True, text=True, timeout=BUILD_TIMEOUT)
        except subprocess.TimeoutExpired:
            common.write_row(target='terraform validate', check='validate', status='drift', error='timeout', **where)
            return
        with open(log, 'a', encoding='utf-8') as output:
            output.write(done.stdout)
    rows = classify_terraform(done.stdout)
    for target, status, error in rows:
        if status == 'ok' or target == 'terraform validate':
            common.write_row(target=target, check='validate', status=status, error=error, **where)
        else:
            name, _, line = target.rpartition(':')
            common.write_row(target='terraform validate', file=f"{entry['directory']}/{name}",
                             line=int(line) if line.isdigit() else None, check='validate', status=status,
                             error=error, **where)
    if rows[0][1] != 'ok' and rows[0][0] != 'terraform validate':
        # Resolves the pending row, which has no file or line.
        common.write_row(target='terraform validate', check='validate', status='drift',
                         error=f'{len(rows)} validation errors', **where)


def wait_ready(python, env):
    """Poll the emulator; a probe that times out counts as not ready."""
    for _ in range(PROBE_TRIES):
        try:
            if subprocess.run([str(python), '-I', '-c', PROBE], env=env, capture_output=True,
                              timeout=60).returncode == 0:
                return True
        except subprocess.TimeoutExpired:
            pass
        time.sleep(PROBE_INTERVAL)
    return False


def run_cosmos(entry, root, where, gaps):
    target = 'azure-cosmosdb-sample.py'
    python = common.base_dir() / 'venvs' / entry['directory'] / 'bin' / 'python'
    if not python.exists():
        common.write_row(target=target, check='run', status='infrastructure',
                         error=f'venv missing: {python}', **where)
        return
    env = {**os.environ, 'ACCOUNT_HOST': EMULATOR_HOST, 'ACCOUNT_KEY': EMULATOR_KEY,
           'PYTHONDONTWRITEBYTECODE': '1'}
    name = f'api-check-cosmos-{os.getpid()}'
    try:
        try:
            started = subprocess.run(['docker', 'run', '-d', '--name', name, '-p', '127.0.0.1:8081:8081',
                                      EMULATOR_IMAGE], capture_output=True, text=True, timeout=BUILD_TIMEOUT)
        except subprocess.TimeoutExpired:
            common.write_row(target=target, check='run', status='infrastructure',
                             error='docker run timeout', **where)
            return
        if started.returncode != 0:
            common.write_row(target=target, check='run', status='infrastructure',
                             error=last_line(started.stderr) or 'docker run failed', **where)
            return
        if not wait_ready(python, env):
            common.write_row(target=target, check='run', status='infrastructure',
                             error='emulator not ready after 5 min', **where)
            return
        log = common.log_path('azure-cosmos-9.log')
        code = run_logged([str(python), target], log, root / entry['directory'], SAMPLE_TIMEOUT, env)
        if code is None:
            common.write_row(target=target, check='run', status='drift', error='timeout', **where)
            return
        status, error, reason = classify_sample(code, log.read_text(errors='replace'), gaps)
        common.write_row(target=target, check='run', status=status, error=error, reason=reason, **where)
    finally:
        subprocess.run(['docker', 'rm', '-f', name], capture_output=True, timeout=60)


def pending_target(entry):
    return {'bicep': 'az bicep build', 'terraform': 'terraform validate'}.get(entry['kind'], 'azure-cosmosdb-sample.py')


def run_target(entry, root, gaps):
    where = dict(cloud='azure', exercise=entry['exercise'], layer='emulator' if entry['kind'] == 'cosmos' else 'iac')
    if entry['kind'] == 'bicep':
        run_bicep(entry, root, where)
    elif entry['kind'] == 'terraform':
        run_terraform(entry, root, where)
    else:
        run_cosmos(entry, root, where, gaps)


def main(argv=None, root=REPO_ROOT):
    targets = common.load_targets()
    gaps = [gap for gap in targets.get('emulator_gaps') or [] if str(gap.get('exercise')) == '9']
    for entry in targets.get('azure') or []:
        where = dict(cloud='azure', exercise=entry['exercise'], layer='emulator' if entry['kind'] == 'cosmos' else 'iac')
        check = {'bicep': 'build', 'terraform': 'validate'}.get(entry['kind'], 'run')
        print(f"azure: {entry['kind']} {entry['directory']}", flush=True)
        common.write_row(target=pending_target(entry), check=check, status='pending', **where)
        try:
            run_target(entry, root, gaps)
        except (OSError, RuntimeError, subprocess.SubprocessError) as error:
            common.write_row(target=pending_target(entry), check=check, status='infrastructure', error=str(error),
                             **where)
    return 0


if __name__ == '__main__':
    sys.exit(main())
