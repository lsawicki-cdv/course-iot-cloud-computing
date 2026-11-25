"""AWS targets against the AWS Emulator: cfn-lint, the exercise scripts, CloudFormation and Terraform."""
import argparse
import json
import os
import re
import secrets
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

import check_cli
import classify
import common

REPO_ROOT = check_cli.REPO_ROOT
SHIMS = Path(__file__).with_name('shims')
SCRIPT_TIMEOUT = 600
DEPLOY_TIMEOUT = 660  # above the shim's 600 s, so the shim records the timeout first
TERRAFORM_TIMEOUT = 600
STEP_TIMEOUT = 300
REGION = 'eu-west-2'
EMULATOR_ACCOUNT = '000000000000'
ENDPOINT = re.compile(r'https://127\.0\.0\.1:[0-9]+/?')
# Variables that would let a child process reach a real AWS account.
REAL_CREDENTIALS = (
    'AWS_SESSION_TOKEN', 'AWS_PROFILE', 'AWS_WEB_IDENTITY_TOKEN_FILE', 'AWS_ROLE_ARN',
    'AWS_CONTAINER_CREDENTIALS_FULL_URI', 'AWS_CONTAINER_CREDENTIALS_RELATIVE_URI',
    'AWS_CONTAINER_AUTHORIZATION_TOKEN',
)


def child_env(env):
    return {name: value for name, value in env.items() if name not in REAL_CREDENTIALS}


def preflight(env):
    """Return why the environment is not the emulator's, or None."""
    for name in REAL_CREDENTIALS:
        if name in env:
            return f'{name} is set'
    if not env.get('AWS_ACCESS_KEY_ID', '').startswith('EMULATOR'):
        return 'AWS_ACCESS_KEY_ID is not an emulator key'
    if not ENDPOINT.fullmatch(env.get('AWS_ENDPOINT_URL', '')):
        return 'AWS_ENDPOINT_URL is not https://127.0.0.1:<port>'
    try:
        done = subprocess.run([env['API_CHECK_REAL_AWS'], 'sts', 'get-caller-identity', '--region', REGION,
                               '--query', 'Account', '--output', 'text'], env=child_env(env),
                              stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as error:
        return f'sts get-caller-identity: {error}'
    if done.stdout.strip() != EMULATOR_ACCOUNT:
        return f'account is not {EMULATOR_ACCOUNT}'
    return None


def run_group(command, log, cwd, timeout, env):
    """Run in its own process group with output in `log`; return the exit code, or None after killing on timeout."""
    with open(log, 'w', encoding='utf-8') as output:
        process = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=output,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        try:
            return process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            return None


def last_line(text):
    lines = [line for line in text.strip().splitlines() if line.strip()]
    return lines[-1] if lines else ''


def extract(directory, root, into):
    """Copy the tracked files of `directory` (git archive HEAD) into `into`; return its path there."""
    archive = subprocess.run(['git', 'archive', 'HEAD', directory], cwd=root, capture_output=True,
                             check=True).stdout
    subprocess.run(['tar', '-x', '-C', into], input=archive, check=True)
    return Path(into) / directory


def key_of(entry):
    """(target, check, layer) of the target's own row, which its pending row and closing row share."""
    base = f"{entry['directory']}/{entry.get('working_directory', '.')}"
    if entry['kind'] == 'script':
        return f"{entry['directory']}/{entry['script']}", 'run', 'emulator'
    if entry['kind'] == 'cloudformation':
        return f"{base}/{entry['template']}", 'run', 'emulator'
    if entry['kind'] == 'terraform':
        return 'terraform apply', 'apply', 'emulator'
    return f"{entry['directory']}/{entry['template']}", 'cfn-lint', 'iac'


def write_rows(rows):
    for row in rows:
        common.write_row(**row)


def raw_calls(key):
    path = common.raw_log_path()
    if not path.exists():
        return []
    calls = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    return [call for call in calls if call['script'] == key]


def fill_placeholders(path, placeholders):
    text = path.read_text(encoding='utf-8')
    for placeholder, value in placeholders.items():
        if isinstance(value, dict):
            value = secrets.token_hex(12)
        text = text.replace(placeholder, str(value))
    path.write_text(text, encoding='utf-8')


def close_on_timeout(rows):
    rows[-1].update(status='drift', error='timeout', reason=None)


def run_cfn_lint(entry, root, where):
    target, check, layer = key_of(entry)
    log = common.log_path(f"aws-cfn-lint-{entry['exercise']}.log")
    code = run_group(['cfn-lint', entry['template']], log, root / entry['directory'], STEP_TIMEOUT,
                     child_env(os.environ))
    text = log.read_text(errors='replace')
    if code is None:
        common.write_row(target=target, check=check, status='drift', error='timeout', **where)
    elif code == 1 or code & 2:
        common.write_row(target=target, check=check, status='drift', error=last_line(text), **where)
    else:
        common.write_row(target=target, check=check, status='ok', **where)


def run_script(entry, root, env, gaps, key):
    exercise = entry['exercise']
    venv_bin = None
    if entry.get('marker'):
        venv_bin = common.base_dir() / 'venvs' / f"{entry['directory']}_aws" / 'bin'
        if not (venv_bin / 'python3').exists():
            common.write_row(cloud='aws', exercise=exercise, layer='emulator', target=key, check='run',
                             status='infrastructure', error=f'venv missing: {venv_bin.parent}')
            return
    with tempfile.TemporaryDirectory() as copy:
        directory = extract(entry['directory'], root, copy)
        script = directory / entry['script']
        if entry.get('placeholders'):
            fill_placeholders(script, entry['placeholders'])
        path = [str(SHIMS)] + ([str(venv_bin)] if venv_bin else []) + [env['PATH']]
        env = {**env, 'PATH': os.pathsep.join(path), 'REGION': REGION, 'API_CHECK_SCRIPT': key}
        command = ['bash', '-c', 'set -T; trap "export API_CHECK_LINE=\\$LINENO" DEBUG; source '
                   + shlex.quote(str(script))]
        log = common.log_path(f"aws-script-{key.replace('/', '_')}.log")
        code = run_group(command, log, directory / entry['working_directory'], SCRIPT_TIMEOUT, env)
        output = log.read_text(errors='replace')
    sample = [classify.classify_sample_output(exercise, output, gaps)] if entry.get('marker') and code is not None else []
    rows = classify.classify_script(exercise, key, raw_calls(key), gaps, extra_rows=sample)
    if code is None:
        close_on_timeout(rows)
    write_rows(rows)


def stack_failures(env, stack_name):
    """Failed stack events as text: the emulator's NotImplemented answer shows up there."""
    done = subprocess.run([env['API_CHECK_REAL_AWS'], 'cloudformation', 'describe-stack-events', '--region', REGION,
                           '--stack-name', stack_name, '--query',
                           "StackEvents[?contains(ResourceStatus,'FAILED')].[LogicalResourceId,ResourceStatusReason]",
                           '--output', 'text'], env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                          timeout=STEP_TIMEOUT)
    return done.stdout + done.stderr


def run_cloudformation(entry, root, env, gaps, key):
    with tempfile.TemporaryDirectory() as copy:
        directory = extract(entry['directory'], root, copy)
        command = ['aws', 'cloudformation', 'deploy', '--region', REGION, '--template-file', entry['template'],
                   '--stack-name', entry['stack_name'], '--capabilities', *entry['capabilities']]
        if entry.get('parameters'):
            command += ['--parameter-overrides', *(f'{name}={value}' for name, value in entry['parameters'].items())]
        env = {**env, 'PATH': os.pathsep.join([str(SHIMS), env['PATH']]), 'API_CHECK_SCRIPT': key}
        log = common.log_path(f"aws-cloudformation-{entry['exercise']}.log")
        code = run_group(command, log, directory / entry['working_directory'], DEPLOY_TIMEOUT, env)
    calls = raw_calls(key)
    if code not in (0, None) and calls and not calls[-1]['timed_out']:
        calls[-1]['stderr'] = stack_failures(env, entry['stack_name']) + calls[-1]['stderr']
    rows = classify.classify_script(entry['exercise'], key, calls, gaps)
    if code is None:  # killed before the shim could record it: a deploy is a waiting call
        rows[-1].update(status='not-covered', error='timeout', reason=None)
    write_rows(rows)


def run_terraform(entry, root, env, gaps, key):
    exercise = entry['exercise']
    with tempfile.TemporaryDirectory() as copy:
        directory = extract(entry['directory'], root, copy) / entry['working_directory']
        log = common.log_path(f'aws-terraform-{exercise}.log')
        if run_group(['terraform', 'init', '-input=false'], log, directory, STEP_TIMEOUT, env) != 0:
            error = last_line(log.read_text(errors='replace')) or 'timeout'
            common.write_row(cloud='aws', exercise=exercise, layer='emulator', target=key, check='apply',
                             status='drift', error=f'init: {error}')
            return
        graph_log = common.log_path(f'aws-terraform-graph-{exercise}.log')
        graph_code = run_group(['terraform', 'graph'], graph_log, directory, STEP_TIMEOUT, env)
        graph = graph_log.read_text(errors='replace') if graph_code == 0 else ''
        code = run_group(['terraform', 'apply', '-auto-approve', '-json', '-input=false'], log, directory,
                         TERRAFORM_TIMEOUT, env)
        lines = log.read_text(errors='replace').splitlines()
    write_rows(classify.classify_terraform(exercise, lines, graph, gaps, timed_out=code is None))


def run_target(entry, root, env, gaps):
    key = key_of(entry)[0]
    where = dict(cloud='aws', exercise=entry['exercise'], layer=key_of(entry)[2])
    if entry['kind'] == 'cfn-lint':
        run_cfn_lint(entry, root, where)
    elif entry['kind'] == 'script':
        run_script(entry, root, env, gaps, key)
    elif entry['kind'] == 'cloudformation':
        run_cloudformation(entry, root, env, gaps, key)
    else:
        run_terraform(entry, root, env, gaps, key)


def main(argv=None, root=REPO_ROOT):
    parser = argparse.ArgumentParser()
    parser.add_argument('--cfn-lint', action='store_true')
    parser.add_argument('--exercise', nargs='+', help='run only these exercises')
    args = parser.parse_args(argv)
    targets = common.load_targets()
    gaps = targets.get('emulator_gaps') or []
    wanted = {'cfn-lint'} if args.cfn_lint else {'script', 'cloudformation', 'terraform'}
    entries = [entry for entry in targets.get('aws') or []
               if entry['kind'] in wanted and (not args.exercise or entry['exercise'] in args.exercise)]
    os.environ.setdefault('API_CHECK_PYTHON', sys.executable)
    os.environ.setdefault('API_CHECK_REAL_AWS', shutil.which('aws') or 'aws')
    os.environ.setdefault('API_CHECK_REAL_CURL', shutil.which('curl') or 'curl')
    env = child_env(os.environ)
    if not args.cfn_lint:
        problem = preflight(os.environ)
        if problem:
            common.write_row(cloud='aws', layer='emulator', target='preflight', check='preflight',
                             status='infrastructure', error=problem)
            return 0
    common.raw_log_path().unlink(missing_ok=True)
    for entry in entries:
        target, check, layer = key_of(entry)
        where = dict(cloud='aws', exercise=entry['exercise'], layer=layer)
        print(f"aws: {entry['kind']} {target}", flush=True)
        common.write_row(target=target, check=check, status='pending', **where)
        try:
            run_target(entry, root, env, gaps)
        except (OSError, RuntimeError, subprocess.SubprocessError) as error:
            common.write_row(target=target, check=check, status='infrastructure', error=str(error), **where)
    return 0


if __name__ == '__main__':
    sys.exit(main())
