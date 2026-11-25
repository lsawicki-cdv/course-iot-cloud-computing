import json
import os
import re
import stat
import subprocess
import sys
import time
from pathlib import Path

import pytest
import yaml

import check_cli
import check_python
import classify
import run_aws_targets
import run_azure_targets
import common
import summary


RUNNER_ENV = (
    'GITHUB_STEP_SUMMARY', 'STEPS_JSON', 'API_CHECK_PYTHON', 'API_CHECK_REAL_AWS', 'API_CHECK_REAL_CURL',
    'API_CHECK_SCRIPT', 'API_CHECK_LINE', 'API_CHECK_AWS_TIMEOUT', 'AWS_ENDPOINT_URL', 'AWS_CA_BUNDLE',
    'AWS_CONFIG_FILE', 'AWS_SHARED_CREDENTIALS_FILE', 'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY',
    'AWS_SESSION_TOKEN', 'AWS_REGION', 'AWS_DEFAULT_REGION', 'AWS_PROFILE',
)


@pytest.fixture(autouse=True)
def results_dir(tmp_path, monkeypatch):
    monkeypatch.setenv('RUNNER_TEMP', str(tmp_path))
    # The runner's own variables must not reach the tests (the job exports them to every step).
    for name in RUNNER_ENV:
        monkeypatch.delenv(name, raising=False)


def test_mask_values():
    assert common.mask('--master-user-password x') == '--master-user-password ***'
    assert common.mask('ADMIN_PASSWORD=x') == 'ADMIN_PASSWORD=***'
    assert common.mask('Variables={API_KEY=x,B=y}') == 'Variables={API_KEY=***,B=y}'
    assert common.mask('--token x --name n') == '--token *** --name n'
    assert common.mask('https://h/api?a=1&code=x&b=2') == 'https://h/api?a=1&code=***&b=2'


def test_mask_leaves_plain_text():
    assert common.mask('aws s3 ls --region eu-west-2') == 'aws s3 ls --region eu-west-2'


def raw_argv(argv):
    common.write_raw_call('s.sh', '1', argv, 0, '', False)
    return json.loads(common.raw_log_path().read_text().splitlines()[-1])['argv']


def test_raw_log_masks_each_element_and_keeps_unbalanced_quotes():
    argv = ['ssm', 'put-parameter', '--value', "TOKEN='x", '--master-user-password', 'p w',
            '--db-password=abc', '--environment', 'Variables={API_KEY=k1,OTHER=v}',
            'https://x/api?code=k', '--region', 'eu-west-2']
    assert raw_argv(argv) == [
        'ssm', 'put-parameter', '--value', 'TOKEN=***', '--master-user-password', '***',
        '--db-password=***', '--environment', 'Variables={API_KEY=***,OTHER=v}',
        'https://x/api?code=***', '--region', 'eu-west-2']


def test_results_last_row_wins():
    key = dict(cloud='aws', exercise='7', layer='emulator', target='t', file='f.sh', line=3, check='run')
    common.write_row(status='pending', **key)
    common.write_row(status='ok', **key)
    rows = common.read_rows()
    assert [row['status'] for row in rows] == ['ok']


def test_write_row_rejects_unknown_status():
    with pytest.raises(ValueError):
        common.write_row(cloud='aws', status='bogus')


def test_write_row_masks_and_truncates_error():
    common.write_row(cloud='aws', status='drift', error='--token abc ' + 'z' * 500)
    error = common.read_rows()[0]['error']
    assert 'abc' not in error and len(error) <= 200


def test_log_path_under_logs():
    path = common.log_path('a.log')
    assert path.parent.name == 'logs' and path.parent.is_dir()


def test_targets_schema(tmp_path):
    bad = tmp_path / 'targets.yml'
    bad.write_text(yaml.safe_dump({'skip': [{'target': 'x'}], 'emulator_gaps': []}))
    with pytest.raises(ValueError):
        common.load_targets(bad)
    good = tmp_path / 'good.yml'
    good.write_text(yaml.safe_dump({'skip': [{'target': 'x', 'reason': 'r'}], 'emulator_gaps': []}))
    assert common.load_targets(good)['skip'][0]['reason'] == 'r'


def test_shipped_targets_load():
    assert common.load_targets()['python']['parent_requirements'] == ['6-paas-iot-mqtt/aws']


def test_infra_cli_writes_row():
    common.main(['infra', '--cloud', 'aws', '--check', 'install', '--error', 'boom --token s'])
    row = common.read_rows()[0]
    assert row['status'] == 'infrastructure' and row['check'] == 'install' and 's' not in row['error'].split()[-1:]
    assert row['error'] == 'boom --token ***'


FIXTURES = Path(__file__).parent / 'fixtures'


def commands_by_key(text, markdown):
    return {(c.cloud, c.words): c for c in check_cli.extract_commands(text, markdown)}


def test_extract_markdown_fixture():
    found = commands_by_key((FIXTURES / 'commands.md').read_text(), True)
    ecr = found['aws', ('ecr', 'get-login-password')]
    assert set(ecr.flags) == {'--region'}
    assert set(found['aws', ('s3api', 'create-bucket')].flags) == {'--bucket', '--region'}
    assert set(found['az', ('vm', 'create')].flags) == {'--name', '--resource-group'}
    query = found['az', ('cognitiveservices', 'account', 'list')]
    assert set(query.flags) == {'--query'}
    for key in [('az', ('group', 'show')), ('aws', ('iot', 'describe-endpoint')),
                ('aws', ('dynamodb', 'wait', 'table-exists')), ('aws', ('--version',)), ('aws', ('configure',)),
                ('az', ('group', 'list'))]:
        assert key in found
    assert ('aws', ('s3', 'ls')) not in found
    assert not any(words and words[0] == 'ignored' for _, words in found)
    assert ('az', ()) not in found and all(words for _, words in found)


def test_extract_shell_fixture():
    found = commands_by_key((FIXTURES / 'commands.sh').read_text(), False)
    assert set(found['az', ('group', 'list')].flags) == {'--output'}
    assert set(found['aws', ('sts', 'get-caller-identity')].flags) == {'--query'}
    assert ('aws', ('s3',)) not in found and len(found) == 2


def test_extract_line_numbers():
    found = commands_by_key((FIXTURES / 'commands.sh').read_text(), False)
    assert found['az', ('group', 'list')].line == 3


@pytest.fixture
def fake_cli(tmp_path, monkeypatch):
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    for name in ('aws', 'az'):
        (bin_dir / name).symlink_to(FIXTURES / 'fake-cli')
    log = tmp_path / 'argv.log'
    monkeypatch.setenv('PATH', f'{bin_dir}{os.pathsep}{os.environ["PATH"]}')
    monkeypatch.setenv('FAKE_CLI_LOG', str(log))

    def recorded():
        return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
    return recorded


def run_static(tmp_path, cloud, text, skip=()):
    (tmp_path / 'x.md').write_text(text)
    check_cli.run(cloud, ['x.md'], tmp_path, list(skip))
    return {(row['target'], row['check']): row for row in common.read_rows()}


def test_validation_statuses_and_argv(tmp_path, fake_cli):
    text = ('```bash\naws s3 ls --regoin r\naws bogus thing\naws s3 mb --name n --region r\n'
            'aws skipped op --name n\naws s3 mb --name m\n```\n')
    skip = [{'target': 'aws skipped op', 'reason': 'why'}]
    rows = run_static(tmp_path, 'aws', text, skip)
    assert rows['aws s3 ls', 'command']['status'] == 'ok'
    assert rows['aws s3 ls --regoin', 'flag']['status'] == 'missing-flag'
    assert rows['aws bogus thing', 'command']['status'] == 'missing-command'
    assert rows['aws skipped op', 'command']['status'] == 'skipped'
    assert rows['aws skipped op', 'command']['reason'] == 'why'
    assert all(row['layer'] == 'static' and row['cloud'] == 'aws' for row in rows.values())
    assert fake_cli() == [['aws', 's3', 'ls', 'help'], ['aws', 'bogus', 'thing', 'help'], ['aws', 's3', 'mb', 'help']]


def test_az_argv_and_extension_setting(tmp_path, fake_cli):
    rows = run_static(tmp_path, 'azure', '```bash\naz group show --name g\naz group show --nme g\n```\n')
    assert rows['az group show --nme', 'flag']['status'] == 'missing-flag'
    calls = fake_cli()
    assert calls[0] == ['az', 'config', 'set', 'extension.use_dynamic_install=yes_without_prompt']
    assert calls[1:] == [['az', 'group', 'show', '--help']]


def test_top_level_aws_forms_argv(tmp_path, fake_cli):
    run_static(tmp_path, 'aws', '```bash\naws --version\naws configure set x y\naws help\n```\n')
    assert fake_cli() == [['aws', '--version'], ['aws', 'configure', 'help'], ['aws', 'help']]
    assert not [row for row in common.read_rows() if row['check'] == 'flag']


def test_command_substitution_is_never_run(tmp_path, fake_cli):
    marker = tmp_path / 'pwned'
    run_static(tmp_path, 'azure', f'```bash\naz $(touch {marker}) --help\n```\n')
    assert not marker.exists() and fake_cli() == []


def test_run_with_missing_rows_exits_zero(tmp_path, fake_cli):
    (tmp_path / 'x.md').write_text('```bash\naws bogus thing\n```\n')
    assert check_cli.main(['--cloud', 'aws'], root=tmp_path, files=['x.md']) == 0
    assert common.read_rows()[0]['status'] == 'missing-command'


def test_flag_prefixes(tmp_path, fake_cli):
    text = ('```bash\naz prefixed op --destination-port-range p --destination-port-rangezz p --start s '
            '--start-ip s\n```\n')
    rows = run_static(tmp_path, 'azure', text)
    assert ('az prefixed op --destination-port-range', 'flag') not in rows
    assert rows['az prefixed op --destination-port-rangezz', 'flag']['status'] == 'missing-flag'
    assert rows['az prefixed op --start', 'flag']['status'] == 'missing-flag'
    assert ('az prefixed op --start-ip', 'flag') not in rows


def summarize(capsys, *argv, cloud='aws'):
    code = summary.main(['--cloud', cloud, *argv])
    return code, capsys.readouterr().out


def row(status, **fields):
    values = dict(cloud='aws', exercise='7', layer='static', target='aws s3 ls', check='command', error=None)
    common.write_row(status=status, **{**values, **fields})


def test_summary_failing_row_exits_one(capsys):
    row('ok')
    row('missing-flag', target='aws s3 ls --regoin', check='flag', file='7/readme.md', line=12, error='not listed')
    code, out = summarize(capsys)
    failing, _, other = out.partition('Not failing')
    assert code == 1 and '7/readme.md:12' in failing and 'missing-flag' in failing and 'not listed' in failing
    assert 'aws s3 ls --regoin' not in other and '1 ok' in out


def test_summary_non_failing_rows_exit_zero(capsys):
    for status in ('not-covered', 'consequential', 'skipped', 'newly-covered'):
        row(status, target=f'target-{status}', check='run', reason='why')
    code, out = summarize(capsys)
    failing, _, other = out.partition('Not failing')
    assert code == 0 and 'target-' not in failing
    assert all(f'target-{status}' in other for status in ('not-covered', 'consequential', 'skipped', 'newly-covered'))


def test_summary_pending_is_not_reached(capsys):
    row('pending', layer='emulator', target='7/run.sh', check='run')
    code, out = summarize(capsys)
    assert code == 1 and 'not reached' in out and '7/run.sh' in out and 'infrastructure' in out


def test_summary_failed_step_is_infrastructure(capsys):
    steps = json.dumps({'install-az': {'outcome': 'failure'}, 'pytest': {'outcome': 'success'}})
    code, out = summarize(capsys, '--steps-json', steps)
    assert code == 1 and 'install-az' in out and 'pytest' not in out


def test_summary_steps_from_environment(capsys, monkeypatch):
    monkeypatch.setenv('STEPS_JSON', '{"emulator": {"outcome": "failure"}}')
    code, out = summarize(capsys)
    assert code == 1 and 'emulator' in out


def test_summary_filters_cloud(capsys):
    row('drift', cloud='azure', target='az vm create')
    code, out = summarize(capsys)
    assert code == 0 and 'az vm create' not in out


def test_summary_masks_error_again(capsys, tmp_path):
    line = dict(cloud='aws', exercise='7', layer='static', target='t', check='run', status='drift',
                error='boom --token abc123')
    common.results_path().parent.mkdir(parents=True)
    common.results_path().write_text(json.dumps(line) + '\n')
    code, out = summarize(capsys)
    assert code == 1 and 'abc123' not in out and '--token ***' in out


def test_summary_appends_to_step_summary(capsys, tmp_path, monkeypatch):
    target = tmp_path / 'step.md'
    monkeypatch.setenv('GITHUB_STEP_SUMMARY', str(target))
    row('missing-command', target='aws bogus thing')
    code, out = summarize(capsys)
    assert code == 1 and out == '' and 'aws bogus thing' in target.read_text()


def test_summary_footer_lists_gaps(capsys):
    _, out = summarize(capsys)
    assert 'short flags' in out and 'positional arguments' in out and 'data plane' in out


REPO = Path(__file__).resolve().parents[2]
PARENT_REQUIREMENTS = ['6-paas-iot-mqtt/aws']


def tracked_python_inputs():
    names = subprocess.run(['git', 'ls-files'], cwd=REPO, capture_output=True, text=True, check=True).stdout
    return [name for name in names.splitlines() if not name.startswith('.github/')]


def units_of(cloud):
    return {unit.name: unit for unit in check_python.build_units(cloud, tracked_python_inputs(), PARENT_REQUIREMENTS)}


def test_azure_units():
    units = units_of('azure')
    nosql = units['9-storage-nosql']
    assert nosql.requirements == ['-r', '9-storage-nosql/requirements.txt']
    assert set(nosql.files) == {'9-storage-nosql/azure-cosmosdb-sample.py', '9-storage-nosql/config.py'}
    assert {'18-timescaledb-terraform', '18-timescaledb-terraform_app'} <= set(units)
    assert '18-timescaledb-terraform/app/api.py' not in units['18-timescaledb-terraform'].files
    assert units['18-timescaledb-terraform_app'].files == ['18-timescaledb-terraform/app/api.py']
    assert not any('/aws/' in name for unit in units.values() for name in unit.files)
    assert not any(name.endswith('_aws') for name in units)


def test_aws_units():
    units = units_of('aws')
    for exercise in ('13-iac-iot-routing', '15-iot-terraform', '16-iot-certificates'):
        assert units[f'{exercise}_aws'].requirements == ['-r', f'{exercise}/aws/requirements.txt']
    assert units['6-paas-iot-mqtt_aws'].requirements == ['-r', '6-paas-iot-mqtt/requirements.txt', 'boto3']
    for exercise in ('9-storage-nosql', '10-faas-functions', '11-serverless-iot-platform'):
        assert units[f'{exercise}_aws'].requirements == ['boto3']
    assert '9-storage-nosql/aws/dynamodb_sample.py' in units['9-storage-nosql_aws'].files
    assert all('/aws/' in name for unit in units.values() for name in unit.files)


def test_import_collector_finds_function_level_import():
    source = (REPO / '10-faas-functions/function_app.py').read_text()
    assert 'openai' in {module for module, _ in check_python.collect_imports(source)}


def test_import_collector_absolute_only_with_lines():
    found = check_python.collect_imports('import a.b, c\nfrom . import d\nfrom e.f import g\n')
    assert found == [('a.b', 1), ('c', 1), ('e.f', 3)]


def test_resolver_finds_shared_module_via_exercise_root():
    root = '10-faas-functions'
    entry = {'file': f'{root}/aws/agent_function.py', 'directory': str(REPO / root / 'aws'),
             'root': str(REPO / root), 'imports': [['sensor_tools', 14], ['os', 9], ['no_such_module_xyz', 15]]}
    assert check_python.resolve(sys.executable, [entry]) == [
        {'file': f'{root}/aws/agent_function.py', 'line': 15, 'module': 'no_such_module_xyz'}]


def fake_pip(tmp_path, body):
    script = tmp_path / 'pip'
    script.write_text('#!/bin/bash\n' + body + '\n')
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return [str(script)]


def run_unit_rows(tmp_path, **kwargs):
    unit = check_python.Unit('u', 'azure', 'u', [], ['-r', 'x'])
    check_python.run_unit(unit, tmp_path, tmp_path / 'venv', skip=[], **kwargs)
    return common.read_rows()


def test_pip_failure_is_drift_with_last_error_line(tmp_path):
    pip = fake_pip(tmp_path, 'echo start; echo "ERROR: no matching distribution" >&2; exit 1')
    rows = run_unit_rows(tmp_path, pip=pip)
    assert [(row['layer'], row['status'], row['error']) for row in rows] == [
        ('python', 'drift', 'ERROR: no matching distribution')]


def test_pip_timeout_is_infrastructure(tmp_path):
    rows = run_unit_rows(tmp_path, pip=fake_pip(tmp_path, 'sleep 5'), timeout=1)
    assert [(row['status']) for row in rows] == ['infrastructure']


def test_unresolved_import_is_drift_with_file_line_and_skip(tmp_path):
    (tmp_path / 'u').mkdir()
    (tmp_path / 'u/a.py').write_text('import os\nimport no_such_xyz\nimport layer_mod\n')
    unit = check_python.Unit('u', 'azure', 'u', ['u/a.py'], [])
    skip = [{'target': 'layer_mod', 'reason': 'Lambda layer'}]
    check_python.run_unit(unit, tmp_path, tmp_path / 'venv', skip=skip, pip=fake_pip(tmp_path, 'exit 0'))
    rows = {row['target']: row for row in common.read_rows() if row['check'] == 'import'}
    assert (rows['no_such_xyz']['status'], rows['no_such_xyz']['file'], rows['no_such_xyz']['line']) == (
        'drift', 'u/a.py', 2)
    assert rows['layer_mod']['status'] == 'skipped' and 'os' not in rows


def test_main_exits_zero_with_drift_row(tmp_path):
    (tmp_path / 'u').mkdir()
    (tmp_path / 'u/requirements.txt').write_text('x\n')
    (tmp_path / 'u/a.py').write_text('import no_such_xyz\n')
    code = check_python.main(['--cloud', 'azure', '--unit', 'u'], root=tmp_path, files=['u/requirements.txt', 'u/a.py'],
                             pip=fake_pip(tmp_path, 'exit 0'))
    assert code == 0
    assert any(row['status'] == 'drift' for row in common.read_rows())


def test_bicep_classification():
    assert run_azure_targets.classify_bicep(0, 'main.bicep(3,1) : Warning BCP081: no type for x')[0] == 'drift'
    assert run_azure_targets.classify_bicep(0, 'main.bicep(3,1) : Warning no-unused-params: x') == ('ok', None)
    status, error = run_azure_targets.classify_bicep(1, 'main.bicep(9,2) : Error BCP035: bad')
    assert status == 'drift' and 'BCP035' in error
    assert run_azure_targets.classify_bicep(0, '')[0] == 'ok'


def terraform_json(*diagnostics, valid=False):
    return json.dumps({'valid': valid, 'diagnostics': list(diagnostics)})


def diagnostic(filename, line, summary):
    return {'severity': 'error', 'summary': summary, 'range': {'filename': filename, 'start': {'line': line}}}


def test_terraform_errors_one_row_each():
    text = terraform_json(diagnostic('main.tf', 4, 'Unsupported argument'), diagnostic('x.tf', 9, 'Bad block'))
    rows = run_azure_targets.classify_terraform(text)
    assert rows == [('main.tf:4', 'drift', 'Unsupported argument'), ('x.tf:9', 'drift', 'Bad block')]


def test_terraform_valid_one_ok_row():
    assert run_azure_targets.classify_terraform(terraform_json(valid=True)) == [('terraform validate', 'ok', None)]


def test_terraform_unparsable_output_is_drift():
    rows = run_azure_targets.classify_terraform('boom')
    assert rows[0][1] == 'drift'


GAPS = [{'pattern': 'not supported by the emulator', 'reason': 'preview image lacks it'}]


def test_sample_classification():
    classify = run_azure_targets.classify_sample
    assert classify(0, 'Database created\nrun_sample done', GAPS) == ('ok', None, None)
    status, error, _ = classify(0, 'run_sample has caught an error. Bad thing\nrun_sample done', GAPS)
    assert status == 'drift' and 'Bad thing' in error
    status, _, reason = classify(0, 'run_sample has caught an error. not supported by the emulator', GAPS)
    assert (status, reason) == ('not-covered', 'preview image lacks it')
    assert classify(1, 'Traceback\nValueError: x', GAPS)[0:2] == ('drift', 'ValueError: x')


def test_azure_main_writes_pending_then_rows(tmp_path, monkeypatch):
    for name in ('12-x', '14-y'):
        (tmp_path / name).mkdir()
    targets = {'azure': [{'exercise': '12', 'kind': 'bicep', 'directory': '12-x'},
                         {'exercise': '14', 'kind': 'terraform', 'directory': '14-y'}]}
    monkeypatch.setattr(common, 'load_targets', lambda: targets)
    seen = []

    def fake_target(entry, root, gaps):
        seen.append([row['status'] for row in common.read_rows()])
        if entry['kind'] == 'terraform':
            raise RuntimeError('boom')
    monkeypatch.setattr(run_azure_targets, 'run_target', fake_target)
    assert run_azure_targets.main([], root=tmp_path) == 0
    assert seen == [['pending'], ['pending', 'pending']]
    statuses = {row['exercise']: row['status'] for row in common.read_rows()}
    assert statuses == {'12': 'pending', '14': 'infrastructure'}


class FakeRun:
    """Stands in for subprocess.run: handlers map the command's first words to a reply or an exception."""

    def __init__(self, **handlers):
        self.handlers = handlers
        self.calls = []

    def __call__(self, command, **kwargs):
        self.calls.append(command)
        for prefix, reply in self.handlers.items():
            if ' '.join(command).startswith(prefix):
                if isinstance(reply, Exception):
                    raise reply
                if callable(reply):
                    reply = reply(command, kwargs)
                return reply
        return subprocess.CompletedProcess(command, 0, b'', b'')

    def ran(self, prefix):
        return [call for call in self.calls if ' '.join(call).startswith(prefix)]


def reply(stdout='', returncode=0, stderr=''):
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


def timeout(*_):
    return subprocess.TimeoutExpired('x', 1)


def logged(text, returncode):
    """Reply of a command run through run_logged: writes text to the stdout file."""
    def run(command, kwargs):
        kwargs['stdout'].write(text)
        return reply(returncode=returncode)
    return run


TERRAFORM = {'exercise': '14', 'kind': 'terraform', 'directory': '14-y'}
COSMOS = {'exercise': '9', 'kind': 'cosmos', 'directory': '9-z'}


def run_one(entry, monkeypatch, tmp_path, fake, gaps=()):
    """Run main for one entry with subprocess.run faked; return the final rows."""
    monkeypatch.setattr(common, 'load_targets', lambda: {'azure': [entry]})
    monkeypatch.setattr(run_azure_targets.subprocess, 'run', fake)
    monkeypatch.setattr(run_azure_targets.time, 'sleep', lambda _: None)
    assert run_azure_targets.main([], root=tmp_path) == 0
    rows = common.read_rows()
    assert not [row for row in rows if row['status'] == 'pending']
    return rows


def test_terraform_init_failure_closes_pending_row(tmp_path, monkeypatch):
    fake = FakeRun(**{'terraform init': logged('Error: no provider\n', 1)})
    rows = run_one(TERRAFORM, monkeypatch, tmp_path, fake)
    assert [(row['target'], row['check'], row['status']) for row in rows] == [('terraform validate', 'validate', 'drift')]
    assert rows[0]['error'].startswith('init: ') and 'no provider' in rows[0]['error']
    assert not fake.ran('terraform validate')


def test_terraform_init_timeout_closes_pending_row(tmp_path, monkeypatch):
    fake = FakeRun(**{'terraform init': timeout()})
    rows = run_one(TERRAFORM, monkeypatch, tmp_path, fake)
    assert [(row['target'], row['status'], row['error']) for row in rows] == [
        ('terraform validate', 'drift', 'init: timeout')]


def test_terraform_validate_errors_rows_and_log(tmp_path, monkeypatch):
    text = terraform_json(diagnostic('main.tf', 4, 'Unsupported argument'), diagnostic('x.tf', 9, 'Bad block'))
    fake = FakeRun(**{'terraform init': logged('init output\n', 0), 'terraform validate': reply(text)})
    rows = run_one(TERRAFORM, monkeypatch, tmp_path, fake)
    assert sorted((row['file'], row['line']) for row in rows if row['file']) == [('14-y/main.tf', 4), ('14-y/x.tf', 9)]
    assert [row['error'] for row in rows if row['file'] is None] == ['2 validation errors']
    log = common.log_path('azure-terraform-14.log').read_text()
    assert 'init output' in log and 'Unsupported argument' in log


def test_terraform_validate_timeout_closes_pending_row(tmp_path, monkeypatch):
    fake = FakeRun(**{'terraform init': logged('', 0), 'terraform validate': timeout()})
    rows = run_one(TERRAFORM, monkeypatch, tmp_path, fake)
    assert [(row['target'], row['status'], row['error']) for row in rows] == [
        ('terraform validate', 'drift', 'timeout')]


@pytest.fixture
def cosmos_venv(tmp_path):
    python = tmp_path / 'api-check' / 'venvs' / '9-z' / 'bin' / 'python'
    python.parent.mkdir(parents=True)
    python.write_text('')


def cosmos_row(rows):
    assert len(rows) == 1
    return rows[0]


def test_cosmos_docker_run_timeout_removes_container(tmp_path, monkeypatch, cosmos_venv):
    fake = FakeRun(**{'docker run': timeout()})
    row = cosmos_row(run_one(COSMOS, monkeypatch, tmp_path, fake))
    assert row['status'] == 'infrastructure'
    name = fake.ran('docker run')[0][fake.ran('docker run')[0].index('--name') + 1]
    assert ['docker', 'rm', '-f', name] in fake.calls


def test_cosmos_probe_timeout_keeps_polling(tmp_path, monkeypatch, cosmos_venv):
    answers = iter([timeout(), reply(returncode=1), reply()])

    def probe(command, kwargs):
        answer = next(answers)
        if isinstance(answer, Exception):
            raise answer
        return answer
    fake = FakeRun(**{'docker run': reply('abc\n'), str(tmp_path / 'api-check/venvs/9-z/bin/python') + ' -I': probe,
                      str(tmp_path / 'api-check/venvs/9-z/bin/python') + ' azure': logged('run_sample done\n', 0)})
    row = cosmos_row(run_one(COSMOS, monkeypatch, tmp_path, fake))
    assert row['status'] == 'ok'
    assert fake.ran('docker rm -f')


def test_cosmos_probe_never_ready_is_infrastructure(tmp_path, monkeypatch, cosmos_venv):
    fake = FakeRun(**{'docker run': reply('abc\n'), str(tmp_path / 'api-check/venvs/9-z/bin/python') + ' -I': timeout()})
    row = cosmos_row(run_one(COSMOS, monkeypatch, tmp_path, fake))
    assert row['status'] == 'infrastructure' and 'not ready' in row['error']
    assert len(fake.ran(str(tmp_path / 'api-check/venvs/9-z/bin/python') + ' -I')) == run_azure_targets.PROBE_TRIES
    assert fake.ran('docker rm -f')


@pytest.mark.parametrize('output, code, status', [
    ('run_sample has caught an error. Bad\nrun_sample done\n', 0, 'drift'),
    ('Traceback\nValueError: x\n', 1, 'drift'),
    ('', None, 'drift'),
])
def test_cosmos_sample_failures_remove_container(tmp_path, monkeypatch, cosmos_venv, output, code, status):
    python = str(tmp_path / 'api-check/venvs/9-z/bin/python')
    sample = timeout() if code is None else logged(output, code)
    fake = FakeRun(**{'docker run': reply('abc\n'), python + ' azure': sample})
    row = cosmos_row(run_one(COSMOS, monkeypatch, tmp_path, fake))
    assert row['status'] == status
    removal = fake.ran('docker rm -f')
    assert removal and removal[0][-1] == fake.ran('docker run')[0][fake.ran('docker run')[0].index('--name') + 1]


SHIMS = Path(__file__).parent / 'shims'


def fake_script(path, body):
    path.write_text('#!/bin/bash\n' + body)
    path.chmod(0o755)
    return path


@pytest.fixture
def shim_env(tmp_path, monkeypatch):
    """Environment for the shims: real aws and curl are fixtures; calls are recorded."""
    calls = tmp_path / 'calls'
    fake_script(tmp_path / 'real-aws', f'echo "$@" >> {calls}\necho out-$1\necho err-$1 >&2\nexit "${{FAKE_EXIT:-0}}"\n')
    fake_script(tmp_path / 'real-curl', f'echo "$@" >> {calls}\necho curl-ok\n')
    env = dict(os.environ, API_CHECK_REAL_AWS=str(tmp_path / 'real-aws'),
               API_CHECK_REAL_CURL=str(tmp_path / 'real-curl'), API_CHECK_PYTHON=sys.executable,
               API_CHECK_SCRIPT='2/aws/x.sh', API_CHECK_LINE='42', RUNNER_TEMP=str(tmp_path))
    env.pop('API_CHECK_AWS_TIMEOUT', None)
    env['calls'] = str(calls)
    return env


def run_shim(name, env, *args, cwd=None):
    return subprocess.run([str(SHIMS / name), *args], env=env, cwd=cwd, capture_output=True, text=True, timeout=60)


def raw_calls(env):
    path = Path(env['RUNNER_TEMP']) / 'api-check' / 'aws-calls.jsonl'
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def real_calls(env):
    path = Path(env['calls'])
    return path.read_text().splitlines() if path.exists() else []


def test_shims_are_executable():
    for name in ('aws', 'curl', 'psql'):
        assert os.access(SHIMS / name, os.X_OK)


def test_aws_shim_passes_output_and_logs_one_line(shim_env):
    shim_env['FAKE_EXIT'] = '3'
    result = run_shim('aws', shim_env, 's3', 'ls', '--password', 'hunter2')
    assert result.stdout == 'out-s3\n'
    assert result.returncode == 3
    assert 'err-s3' in result.stderr
    (entry,) = raw_calls(shim_env)
    assert entry['script'] == '2/aws/x.sh'
    assert entry['line'] == '42'
    assert entry['argv'] == ['s3', 'ls', '--password', '***']
    assert entry['exit'] == 3
    assert 'err-s3' in entry['stderr']
    assert entry['timed_out'] is False
    assert 'hunter2' not in json.dumps(entry)


def fake_timeout(tmp_path, env):
    """Put a `timeout` on PATH that records its arguments, then runs the command."""
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    fake_script(bin_dir / 'timeout', f'echo "$@" > {tmp_path}/timeout-args\nwhile [[ $1 == --* ]]; do shift; done\nshift\nexec "$@"\n')
    env['PATH'] = f"{bin_dir}:{env['PATH']}"
    return tmp_path / 'timeout-args'


def test_aws_shim_default_and_deploy_timeouts(tmp_path, shim_env):
    args = fake_timeout(tmp_path, shim_env)
    run_shim('aws', shim_env, 's3', 'ls')
    assert args.read_text().startswith('--foreground --kill-after=5 120 ')
    run_shim('aws', shim_env, 'cloudformation', 'deploy', '--stack-name', 's')
    assert args.read_text().startswith('--foreground --kill-after=5 600 ')
    shim_env['API_CHECK_AWS_TIMEOUT'] = '7'
    run_shim('aws', shim_env, 'cloudformation', 'deploy')
    assert args.read_text().startswith('--foreground --kill-after=5 7 ')


def test_aws_shim_timeout_kills_and_logs(tmp_path, shim_env):
    fake_script(tmp_path / 'real-aws', 'exec sleep 30\n')
    shim_env['API_CHECK_AWS_TIMEOUT'] = '1'
    result = run_shim('aws', shim_env, 'ecs', 'wait', 'tasks-running')
    assert result.returncode != 0
    (entry,) = raw_calls(shim_env)
    assert entry['timed_out'] is True


def test_group_kill_leaves_no_aws_call_process(tmp_path, shim_env):
    marker = f'apicheck-{tmp_path.name}'
    fake_script(tmp_path / 'real-aws', f'(exec -a sleep-{marker} sleep 30) &\nwait\n')
    try:
        code = run_aws_targets.run_group([str(SHIMS / 'aws'), 's3', marker], tmp_path / 'log', tmp_path, 1, shim_env)
        assert code is None
        for _ in range(50):
            if subprocess.run(['pgrep', '-f', marker], capture_output=True).returncode != 0:
                break
            time.sleep(0.1)
        else:
            pytest.fail('a process of the aws call outlived the group kill')
    finally:
        subprocess.run(['pkill', '-9', '-f', marker], check=False)


def test_aws_shim_works_without_yaml_from_another_directory(tmp_path, shim_env):
    bin_dir = tmp_path / 'venv-bin'
    bin_dir.mkdir()
    fake_script(bin_dir / 'python3', 'echo "No module named yaml" >&2\nexit 1\n')
    shim_env['PATH'] = f"{bin_dir}:{shim_env['PATH']}"
    elsewhere = tmp_path / 'elsewhere'
    elsewhere.mkdir()
    result = run_shim('aws', shim_env, 'sts', 'get-caller-identity', cwd=elsewhere)
    assert result.stdout == 'out-sts\n'
    assert len(raw_calls(shim_env)) == 1


@pytest.mark.parametrize('url', [
    'https://raw.githubusercontent.com/lsawicki-cdv/course-iot-cloud-computing/x',
    'https://checkip.amazonaws.com',
    'https://checkip.amazonaws.com/',
    'http://127.0.0.1:1/',
    'http://localhost:8080/a',
    'http://[::1]:9/',
])
def test_curl_shim_passes_allowed_urls(shim_env, url):
    result = run_shim('curl', shim_env, '-s', url)
    assert result.returncode == 0
    assert result.stdout == 'curl-ok\n'
    assert real_calls(shim_env) == [f'-s {url}']


@pytest.mark.parametrize('url', [
    'http://203.0.113.5',
    'https://abc.execute-api.eu-west-2.amazonaws.com/x?code=k',
    'https://raw.githubusercontent.com.evil.example/lsawicki-cdv/course-iot-cloud-computing/x',
    'https://checkip.amazonaws.com@203.0.113.5/',
    'https://raw.githubusercontent.com/other/repo/x',
    'http://127.0.0.1@203.0.113.5/',
    'http://localhost.evil.example/',
])
def test_curl_shim_refuses_other_urls(shim_env, url):
    result = run_shim('curl', shim_env, '-s', url)
    assert result.returncode == 7
    assert real_calls(shim_env) == []


def test_curl_shim_refuses_one_bad_url_among_good(shim_env):
    result = run_shim('curl', shim_env, 'https://checkip.amazonaws.com', 'http://203.0.113.5')
    assert result.returncode == 7
    assert real_calls(shim_env) == []


def test_curl_shim_refuses_without_url_and_with_proxy(shim_env):
    assert run_shim('curl', shim_env, '-s').returncode == 7
    assert run_shim('curl', shim_env, '-x', 'http://203.0.113.5', 'https://checkip.amazonaws.com').returncode == 7
    assert real_calls(shim_env) == []


def test_psql_shim_exits_two_and_calls_nothing(shim_env):
    result = run_shim('psql', shim_env, '-h', 'db')
    assert result.returncode == 2
    assert real_calls(shim_env) == []


# --- AWS classification (T7) ---

def _call(argv, exit_code=0, stderr='', timed_out=False, line=1, script='2-iaas/aws/x.sh'):
    return {'script': script, 'line': line, 'argv': argv, 'exit': exit_code, 'stderr': stderr,
            'timed_out': timed_out}


def _statuses(rows):
    return [row['status'] for row in rows]


def test_script_501_is_not_covered_and_later_failures_consequential():
    calls = [
        _call(['ec2', 'run-instances'], 254, 'An error occurred (NotImplemented) when calling the RunInstances', line=3),
        _call(['ec2', 'describe-instances'], 254, 'An error occurred (InvalidInstanceID)', line=5),
        _call(['s3', 'ls'], 0, line=6),
    ]
    rows = classify.classify_script('2', '2-iaas/aws/x.sh', calls, [])
    assert _statuses(rows) == ['not-covered', 'consequential', 'not-covered']
    assert rows[0]['line'] == 3 and rows[0]['check'] == 'ec2 run-instances' and rows[0]['cloud'] == 'aws'


def test_script_http_501_status_is_not_covered():
    calls = [_call(['iot', 'create-thing'], 254, 'Received response with status code 501')]
    assert _statuses(classify.classify_script('6', 's.sh', calls, [])) == ['not-covered', 'not-covered']


def test_script_other_error_is_drift_and_clean_script_is_ok():
    calls = [_call(['ec2', 'run-instances'], 252, 'Unknown options: --bogus')]
    assert _statuses(classify.classify_script('2', 's.sh', calls, [])) == ['drift', 'drift']
    rows = classify.classify_script('2', 's.sh', [_call(['s3', 'ls'])], [])
    assert _statuses(rows) == ['ok'] and rows[0]['check'] == 'run'


@pytest.mark.parametrize('argv', [
    ['elbv2', 'wait', 'target-in-service', '--target-group-arn', 'x'],
    ['cloudformation', 'deploy', '--stack-name', 's'],
])
def test_waiter_timeout_is_not_covered(argv):
    rows = classify.classify_script('3', 's.sh', [_call(argv, 124, '', timed_out=True)], [])
    assert _statuses(rows) == ['not-covered', 'not-covered']


def test_other_timeout_is_drift_timeout():
    rows = classify.classify_script('3', 's.sh', [_call(['ec2', 'run-instances'], 124, '', timed_out=True)], [])
    assert _statuses(rows) == ['drift', 'drift'] and rows[0]['error'] == 'timeout'


def test_waiter_api_error_is_classified_from_the_error():
    calls = [_call(['ec2', 'wait', 'instance-running'], 255, 'Waiter failed: InvalidInstanceID')]
    assert _statuses(classify.classify_script('2', 's.sh', calls, [])) == ['drift', 'drift']


def test_closing_row_is_worst_status_on_the_script_key():
    calls = [_call(['s3', 'ls'], 252, 'Unknown options', line=2),
             _call(['ec2', 'run-instances'], 254, 'NotImplemented', line=3)]
    rows = classify.classify_script('2', 's.sh', calls, [])
    assert _statuses(rows) == ['drift', 'not-covered', 'drift']
    closing = rows[-1]
    assert (closing['target'], closing['check'], closing['file'], closing['line']) == ('s.sh', 'run', None, None)
    assert closing['error'] == '2 calls failed'
    only_501 = classify.classify_script('6', 's.sh', [_call(['iot', 'x'], 254, 'status code 501')], [])[-1]
    assert only_501['status'] == 'not-covered' and only_501['error'] == '1 calls failed'


def test_consequential_does_not_raise_the_closing_row():
    calls = [_call(['a', 'b'], 254, 'NotImplemented'), _call(['c', 'd'], 254, 'boom')]
    assert classify.classify_script('2', 's.sh', calls, [])[-1]['status'] == 'not-covered'


def test_emulator_gap_match_is_not_covered_with_reason():
    gaps = [{'exercise': '7', 'cloud': 'aws', 'target': r'^rds create-db-instance', 'pattern': 'InvalidParameter',
             'reason': 'emulator rejects the engine version'}]
    calls = [
        _call(['rds', 'create-db-instance'], 254, 'An error occurred (InvalidParameterValue)', line=4),
        _call(['rds', 'describe-db-instances'], 254, 'DBInstanceNotFound', line=5),
    ]
    rows = classify.classify_script('7', 's.sh', calls, gaps)
    assert _statuses(rows) == ['not-covered', 'consequential', 'not-covered']
    assert rows[0]['reason'] == 'emulator rejects the engine version'


def test_gap_for_another_exercise_or_cloud_does_not_match():
    calls = [_call(['rds', 'create-db-instance'], 254, 'InvalidParameterValue')]
    for gap in ({'exercise': '8', 'cloud': 'aws', 'target': 'rds', 'reason': 'r'},
                {'exercise': '7', 'target': 'rds', 'reason': 'r'}):
        assert _statuses(classify.classify_script('7', 's.sh', calls, [gap])) == ['drift', 'drift']


def test_passing_call_matching_gap_is_newly_covered():
    gaps = [{'exercise': '7', 'cloud': 'aws', 'target': 'rds create-db-instance', 'reason': 'was rejected'}]
    rows = classify.classify_script('7', 's.sh', [_call(['rds', 'create-db-instance'], 0, line=4)], gaps)
    assert _statuses(rows) == ['newly-covered', 'newly-covered'] and rows[0]['line'] == 4
    assert rows[1]['line'] is None and rows[1]['error'] is None


SAMPLE_ERROR = 'start\nrun_sample has caught an error. Table x is not supported\n'


def test_sample_gap_matches_only_text_after_the_marker():
    out = 'not supported yet, skipping\nrun_sample has caught an error. Bad request\n'
    gaps = [{'exercise': '9', 'cloud': 'aws', 'pattern': 'not supported', 'reason': 'r'}]
    assert classify.classify_sample_output('9', out, gaps)['status'] == 'drift'


def test_sample_marker_is_drift_unless_gap_matches():
    assert classify.classify_sample_output('9', SAMPLE_ERROR, [])['status'] == 'drift'
    gaps = [{'exercise': '9', 'cloud': 'aws', 'pattern': 'not supported', 'reason': 'no TTL'}]
    row = classify.classify_sample_output('9', SAMPLE_ERROR, gaps)
    assert row['status'] == 'not-covered' and row['reason'] == 'no TTL'
    assert classify.classify_sample_output('9', 'all fine\n', gaps)['status'] == 'ok'


def _diag(address, summary, detail=''):
    return json.dumps({'@level': 'error', 'type': 'diagnostic', 'diagnostic': {
        'severity': 'error', 'summary': summary, 'detail': detail, 'address': address}})


GRAPH = '''digraph {
  compound = "true"
  subgraph "root" {
    "[root] aws_instance.web (expand)" -> "[root] aws_security_group.sg (expand)"
    "[root] aws_security_group.sg (expand)" -> "[root] data.aws_ssm_parameter.ubuntu (expand)"
    "[root] aws_s3_bucket.other (expand)" -> "[root] provider[\\"registry.terraform.io/hashicorp/aws\\"]"
    "[root] aws_instance.web (expand)" -> "[root] provider[\\"registry.terraform.io/hashicorp/aws\\"]"
  }
}'''


def test_terraform_dependent_error_is_consequential_independent_is_drift():
    lines = [
        _diag('data.aws_ssm_parameter.ubuntu', 'reading SSM parameter', 'NotImplemented: 501'),
        _diag('aws_instance.web', 'creating EC2 Instance', 'ImageNotFound'),
        _diag('aws_s3_bucket.other', 'creating bucket', 'AccessDenied'),
    ]
    rows = classify.classify_terraform('14', lines, GRAPH, [])
    assert [(row['target'], row['status']) for row in rows] == [
        ('data.aws_ssm_parameter.ubuntu', 'not-covered'),
        ('aws_instance.web', 'consequential'),
        ('aws_s3_bucket.other', 'drift'),
        ('terraform apply', 'drift'),
    ]
    assert rows[-1]['error'] == '3 errors'


def test_terraform_gap_error_is_not_covered_with_reason_and_seeds_consequential():
    gaps = [{'exercise': '14', 'cloud': 'aws', 'target': r'^data\.aws_ssm_parameter\.ubuntu$',
             'pattern': 'ParameterNotFound', 'reason': 'public parameter missing'}]
    lines = [_diag('data.aws_ssm_parameter.ubuntu', 'reading', 'ParameterNotFound'),
             _diag('aws_instance.web', 'creating', 'x')]
    rows = classify.classify_terraform('14', lines, GRAPH, gaps)
    assert _statuses(rows) == ['not-covered', 'consequential', 'not-covered']
    assert rows[0]['reason'] == 'public parameter missing'


def test_terraform_success_is_one_ok_row_and_gap_that_passed_is_newly_covered():
    gaps = [{'exercise': '15', 'cloud': 'aws', 'target': 'aws_iot_endpoint', 'reason': 'was missing'}]
    lines = [json.dumps({'type': 'apply_complete', 'hook': {'resource': {'addr': 'data.aws_iot_endpoint.e'}}}),
             json.dumps({'type': 'apply_complete', 'hook': {'resource': {'addr': 'aws_s3_bucket.b'}}})]
    rows = classify.classify_terraform('15', lines, GRAPH, gaps)
    assert _statuses(rows) == ['newly-covered', 'newly-covered']
    assert rows[-1]['target'] == 'terraform apply'
    assert rows[0]['target'] == 'data.aws_iot_endpoint.e'


def test_terraform_error_without_address_is_classified_on_the_configuration_key():
    def bare(summary, detail=''):
        return json.dumps({'type': 'diagnostic', 'diagnostic': {'severity': 'error', 'summary': summary,
                                                                 'detail': detail}})
    rows = classify.classify_terraform('14', [bare('Invalid provider configuration')], GRAPH, [])
    assert _statuses(rows) == ['drift', 'drift']
    assert rows[-1]['target'] == 'terraform apply' and rows[-1]['check'] == 'apply'
    rows = classify.classify_terraform('14', [bare('x', 'NotImplemented')], GRAPH, [])
    assert rows[-1]['status'] == 'not-covered'


def test_terraform_ignores_warnings_and_non_json_lines():
    warning = json.dumps({'type': 'diagnostic', 'diagnostic': {'severity': 'warning', 'summary': 'w'}})
    assert _statuses(classify.classify_terraform('14', ['not json', warning], GRAPH, [])) == ['ok']


def test_terraform_timeout_is_drift_timeout():
    rows = classify.classify_terraform('14', [], GRAPH, [], timed_out=True)
    assert _statuses(rows) == ['drift'] and rows[0]['error'] == 'timeout'


def test_aws_targets_scripts_exist_and_exclude_user_data():
    targets = common.load_targets()['aws']
    tracked = set(subprocess.run(['git', 'ls-files'], capture_output=True, text=True, check=True,
                                 cwd=Path(__file__).parents[2]).stdout.split('\n'))
    scripts = [entry for entry in targets if entry['kind'] == 'script']
    assert len(scripts) == 11
    for entry in scripts:
        path = f"{entry['directory']}/{entry['script']}"
        assert path in tracked, path
        name = Path(path).name
        assert not name.startswith('install-docker') and name != 'vm.sh' and 'elastic-beanstalk' not in name
    by_script = {Path(entry['script']).name: entry for entry in scripts}
    assert by_script['aws-cli-s3-website.sh']['working_directory'] == '.'
    assert by_script['aws-cli-dynamodb.sh']['marker'] == 'run_sample has caught an error'
    assert by_script['aws-cli-rds-postgresql.sh']['placeholders']['<your-public-ip>'] == '203.0.113.10'
    assert {entry['kind'] for entry in targets} == {'script', 'cloudformation', 'terraform', 'cfn-lint'}


def test_aws_targets_schema_rejects_incomplete_entries(tmp_path):
    path = tmp_path / 'targets.yml'
    path.write_text(yaml.safe_dump({'aws': [{'exercise': '2', 'kind': 'script', 'directory': 'd'}]}))
    with pytest.raises(ValueError):
        common.load_targets(path)
    path.write_text(yaml.safe_dump({'emulator_gaps': [{'exercise': '2', 'reason': 'r'}]}))
    with pytest.raises(ValueError):
        common.load_targets(path)


# ---- AWS targets runner ----

EMULATOR_ENV = {'AWS_ACCESS_KEY_ID': 'EMULATORABC', 'AWS_SECRET_ACCESS_KEY': 'x',
                'AWS_ENDPOINT_URL': 'https://127.0.0.1:9297'}
FORBIDDEN = ('AWS_SESSION_TOKEN', 'AWS_PROFILE', 'AWS_WEB_IDENTITY_TOKEN_FILE', 'AWS_ROLE_ARN',
             'AWS_CONTAINER_CREDENTIALS_FULL_URI', 'AWS_CONTAINER_CREDENTIALS_RELATIVE_URI',
             'AWS_CONTAINER_AUTHORIZATION_TOKEN')

FAKE_AWS = '''echo "$*" >> "$OUT/aws-calls"
case "$1" in
  sts) echo "${FAKE_ACCOUNT:-000000000000}" ;;
  s3) echo "NotImplemented: s3" >&2; exit 254 ;;
  cloudformation)
    if [ "$2" = deploy ]; then [ -n "$DEPLOY_SLEEP" ] && exec sleep "$DEPLOY_SLEEP"; echo "Failed to create the stack" >&2; exit 255; fi
    echo "Handler NotImplemented in the emulator" ;;
esac
'''
FAKE_TERRAFORM = '''echo "$PWD $1 $AWS_ENDPOINT_URL" >> "$OUT/terraform-calls"
case "$1" in
  graph) [ -n "$GRAPH_FAIL" ] && { echo graph-broken >&2; exit 1; }; echo "digraph {}" ;;
  apply) [ -n "$APPLY_SLEEP" ] && sleep "$APPLY_SLEEP"; echo '{"type":"diagnostic","diagnostic":{"severity":"error","summary":"Bad","detail":"d","address":"aws_x.y"}}'; exit 1 ;;
esac
'''
FAKE_CFN_LINT = '''case "$PWD" in *12-faas*) echo "aws/template.yaml:3:1:E2531:deprecated runtime"; exit 2 ;; esac'''


@pytest.fixture
def aws_env(tmp_path, monkeypatch):
    """A git repo with the exercises, fake aws/terraform/cfn-lint on PATH and an emulator-like environment."""
    out = tmp_path / 'out'
    out.mkdir()
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    for name, body in (('aws', FAKE_AWS), ('terraform', FAKE_TERRAFORM), ('cfn-lint', FAKE_CFN_LINT)):
        fake_script(bin_dir / name, body)
    repo = tmp_path / 'repo'
    repo.mkdir()
    monkeypatch.setenv('PATH', f"{bin_dir}:{os.environ['PATH']}")
    monkeypatch.setenv('OUT', str(out))
    monkeypatch.setenv('RUNNER_TEMP', str(tmp_path / 'tmp'))
    monkeypatch.delenv('API_CHECK_REAL_AWS', raising=False)
    for name in FORBIDDEN:
        monkeypatch.delenv(name, raising=False)
    for name, value in EMULATOR_ENV.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv('FAKE_ACCOUNT', '000000000000')
    return repo, out


def commit_repo(repo, files):
    for name, text in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    git = ['git', '-c', 'user.email=a@b', '-c', 'user.name=n']
    subprocess.run(['git', 'init', '-q'], cwd=repo, check=True)
    subprocess.run(['git', 'add', '.'], cwd=repo, check=True)
    subprocess.run([*git, 'commit', '-q', '-m', 'x'], cwd=repo, check=True)


def run_aws(monkeypatch, repo, targets, *argv, gaps=()):
    monkeypatch.setattr(common, 'load_targets', lambda: {'aws': targets, 'emulator_gaps': list(gaps)})
    return run_aws_targets.main(list(argv), root=repo)


def result_statuses():
    path = common.results_path()
    return [(row['target'], row['status']) for row in map(json.loads, path.read_text().splitlines())]


SCRIPT_ENTRY = {'exercise': '2', 'kind': 'script', 'directory': '2-iaas', 'script': 'aws/a.sh',
                'working_directory': 'aws'}
DUMP_SCRIPT = '''#!/bin/bash
pwd > "$OUT/pwd"
readlink /proc/self/fd/0 > "$OUT/stdin"
echo "$REGION $API_CHECK_REAL_AWS ${PATH%%:*}" > "$OUT/env"
X=$(aws s3 ls)
'''


def test_script_runs_in_archive_copy_with_shims_and_line_numbers(aws_env, monkeypatch):
    repo, out = aws_env
    commit_repo(repo, {'2-iaas/aws/a.sh': DUMP_SCRIPT, '2-iaas/aws/b.sh': 'touch "$OUT/b-ran"\n'})
    (repo / '2-iaas' / 'aws' / 'untracked.txt').write_text('x')
    assert run_aws(monkeypatch, repo, [SCRIPT_ENTRY]) == 0
    work = (out / 'pwd').read_text().strip()
    assert work.endswith('2-iaas/aws') and not work.startswith(str(repo))
    assert (out / 'stdin').read_text().strip() == '/dev/null'
    region, real_aws, first = (out / 'env').read_text().split()
    assert region == 'eu-west-2' and real_aws.endswith('/bin/aws') and first.endswith('api-check/shims')
    assert not (out / 'b-ran').exists()
    assert result_statuses()[0] == ('2-iaas/aws/a.sh', 'pending')
    rows = common.read_rows()
    call = next(row for row in rows if row['check'] == 's3 ls')
    assert call['line'] == '5' and call['status'] == 'not-covered'
    assert [row['status'] for row in rows if row['check'] == 'run'] == ['not-covered']
    assert common.log_path('x').parent.glob('*a.sh*')


def test_script_target_not_in_targets_never_runs(aws_env, monkeypatch):
    repo, out = aws_env
    commit_repo(repo, {'2-iaas/aws/a.sh': 'touch "$OUT/ran"\n'})
    run_aws(monkeypatch, repo, [])
    assert not (out / 'ran').exists()


def test_placeholders_replaced_in_copy_only(aws_env, monkeypatch):
    repo, out = aws_env
    script = 'echo "$PW $IP" > "$OUT/values"\nPW="<your-password>"\nIP="<your-public-ip>"\necho "$PW $IP" > "$OUT/values"\n'
    commit_repo(repo, {'7-storage/aws/a.sh': script})
    entry = {'exercise': '7', 'kind': 'script', 'directory': '7-storage', 'script': 'aws/a.sh',
             'working_directory': 'aws',
             'placeholders': {'<your-password>': {'generate': 'password'}, '<your-public-ip>': '203.0.113.10'}}
    run_aws(monkeypatch, repo, [entry])
    password, ip = (out / 'values').read_text().split()
    assert len(password) >= 16 and '<' not in password and ip == '203.0.113.10'
    status = subprocess.run(['git', 'status', '--porcelain'], cwd=repo, capture_output=True, text=True).stdout
    assert status == ''


def test_exercise_9_uses_its_venv_python_and_missing_venv_is_infrastructure(aws_env, monkeypatch):
    repo, out = aws_env
    commit_repo(repo, {'9-storage-nosql/aws/a.sh': 'command -v python3 > "$OUT/python"\n'})
    entry = {'exercise': '9', 'kind': 'script', 'directory': '9-storage-nosql', 'script': 'aws/a.sh',
             'working_directory': 'aws', 'marker': 'run_sample has caught an error'}
    run_aws(monkeypatch, repo, [entry])
    assert not (out / 'python').exists()
    assert result_statuses()[-1] == ('9-storage-nosql/aws/a.sh', 'infrastructure')
    venv_bin = common.base_dir() / 'venvs' / '9-storage-nosql_aws' / 'bin'
    venv_bin.mkdir(parents=True)
    fake_script(venv_bin / 'python3', 'echo "run_sample has caught an error: boom"\n')
    run_aws(monkeypatch, repo, [entry])
    assert (out / 'python').read_text().strip() == str(venv_bin / 'python3')


def test_cfn_lint_one_row_per_template(aws_env, monkeypatch):
    repo, _ = aws_env
    commit_repo(repo, {'12-faas/aws/template.yaml': 'x', '13-iot/aws/template.yaml': 'x'})
    targets = [{'exercise': '12', 'kind': 'cfn-lint', 'directory': '12-faas', 'template': 'aws/template.yaml'},
               {'exercise': '13', 'kind': 'cfn-lint', 'directory': '13-iot', 'template': 'aws/template.yaml'}]
    run_aws(monkeypatch, repo, targets, '--cfn-lint')
    rows = {row['exercise']: row for row in common.read_rows()}
    assert rows['12']['status'] == 'drift' and 'E2531' in rows['12']['error']
    assert rows['13']['status'] == 'ok'
    assert not (Path(os.environ['OUT']) / 'aws-calls').exists()


def test_cloudformation_deploy_reads_stack_events_on_failure(aws_env, monkeypatch):
    repo, out = aws_env
    commit_repo(repo, {'12-faas/aws/template.yaml': 'x'})
    entry = {'exercise': '12', 'kind': 'cloudformation', 'directory': '12-faas', 'working_directory': 'aws',
             'template': 'template.yaml', 'stack_name': 'cloud-x', 'capabilities': ['CAPABILITY_IAM'],
             'parameters': {'ProjectName': 'contoso'}}
    run_aws(monkeypatch, repo, [entry])
    calls = (out / 'aws-calls').read_text()
    assert 'cloudformation deploy' in calls and '--stack-name cloud-x' in calls
    assert 'ProjectName=contoso' in calls and 'describe-stack-events' in calls
    rows = [row for row in common.read_rows() if row['status'] != 'pending']
    assert {row['status'] for row in rows} == {'not-covered'}


def test_terraform_runs_in_copy_with_emulator_endpoint(aws_env, monkeypatch):
    repo, out = aws_env
    commit_repo(repo, {'14-vm/aws/main.tf': 'x'})
    entry = {'exercise': '14', 'kind': 'terraform', 'directory': '14-vm', 'working_directory': 'aws'}
    run_aws(monkeypatch, repo, [entry])
    lines = [line.split() for line in (out / 'terraform-calls').read_text().splitlines()]
    assert [line[1] for line in lines] == ['init', 'graph', 'apply']
    assert all(line[0].endswith('14-vm/aws') and not line[0].startswith(str(repo)) for line in lines)
    assert lines[0][2] == 'https://127.0.0.1:9297'
    assert ('aws_x.y', 'drift') in [(row['target'], row['status']) for row in common.read_rows()]


def test_terraform_apply_timeout_is_killed_and_classified(aws_env, monkeypatch):
    repo, _ = aws_env
    commit_repo(repo, {'14-vm/aws/main.tf': 'x'})
    entry = {'exercise': '14', 'kind': 'terraform', 'directory': '14-vm', 'working_directory': 'aws'}
    monkeypatch.setenv('APPLY_SLEEP', '30')
    monkeypatch.setattr(run_aws_targets, 'TERRAFORM_TIMEOUT', 1)
    run_aws(monkeypatch, repo, [entry])
    rows = common.read_rows()
    assert [(row['status'], row['error']) for row in rows] == [('drift', 'timeout')]


CFN_ENTRY = {'exercise': '12', 'kind': 'cloudformation', 'directory': '12-faas', 'working_directory': 'aws',
             'template': 'template.yaml', 'stack_name': 'cloud-x', 'capabilities': ['CAPABILITY_IAM']}


def test_deploy_timeout_in_the_shim_is_not_covered(aws_env, monkeypatch):
    repo, _ = aws_env
    commit_repo(repo, {'12-faas/aws/template.yaml': 'x'})
    monkeypatch.setenv('DEPLOY_SLEEP', '30')
    monkeypatch.setenv('API_CHECK_AWS_TIMEOUT', '1')
    assert run_aws_targets.DEPLOY_TIMEOUT > 600
    monkeypatch.setattr(run_aws_targets, 'DEPLOY_TIMEOUT', 20)
    run_aws(monkeypatch, repo, [CFN_ENTRY])
    rows = [row for row in common.read_rows() if row['status'] != 'pending']
    assert {row['status'] for row in rows} == {'not-covered'}
    assert 'timeout' in {row['error'] for row in rows}


def test_deploy_killed_by_the_runner_is_not_covered_never_ok(aws_env, monkeypatch):
    repo, _ = aws_env
    commit_repo(repo, {'12-faas/aws/template.yaml': 'x'})
    monkeypatch.setenv('DEPLOY_SLEEP', '3')
    monkeypatch.setattr(run_aws_targets, 'DEPLOY_TIMEOUT', 1)
    run_aws(monkeypatch, repo, [CFN_ENTRY])
    rows = [row for row in common.read_rows() if row['status'] != 'pending']
    assert [(row['status'], row['error']) for row in rows] == [('not-covered', 'timeout')]


def test_script_timeout_kills_the_process_group_and_is_drift(aws_env, monkeypatch):
    repo, out = aws_env
    commit_repo(repo, {'2-iaas/aws/a.sh': 'sleep 30 &\necho $! > "$OUT/pid"\nsleep 30\n'})
    monkeypatch.setattr(run_aws_targets, 'SCRIPT_TIMEOUT', 1)
    run_aws(monkeypatch, repo, [SCRIPT_ENTRY])
    rows = [row for row in common.read_rows() if row['status'] != 'pending']
    assert [(row['status'], row['error']) for row in rows] == [('drift', 'timeout')]
    pid = int((out / 'pid').read_text())
    for _ in range(50):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.1)
    else:
        os.kill(pid, 9)
        pytest.fail('background child outlived the script')


def test_raw_log_of_an_earlier_run_is_not_counted(aws_env, monkeypatch):
    repo, _ = aws_env
    commit_repo(repo, {'2-iaas/aws/a.sh': 'true\n'})
    common.write_raw_call('2-iaas/aws/a.sh', '1', ['aws', 's3', 'ls'], 1, 'NotImplemented', False)
    run_aws(monkeypatch, repo, [SCRIPT_ENTRY])
    assert [row['status'] for row in common.read_rows() if row['status'] != 'pending'] == ['ok']


def test_terraform_graph_failure_is_logged_and_classification_goes_on(aws_env, monkeypatch):
    repo, _ = aws_env
    commit_repo(repo, {'14-vm/aws/main.tf': 'x'})
    entry = {'exercise': '14', 'kind': 'terraform', 'directory': '14-vm', 'working_directory': 'aws'}
    monkeypatch.setenv('GRAPH_FAIL', '1')
    run_aws(monkeypatch, repo, [entry])
    assert ('aws_x.y', 'drift') in [(row['target'], row['status']) for row in common.read_rows()]
    assert 'graph-broken' in common.log_path('aws-terraform-graph-14.log').read_text()


@pytest.mark.parametrize('name', FORBIDDEN)
def test_preflight_refuses_real_credential_variables(aws_env, monkeypatch, name):
    repo, out = aws_env
    commit_repo(repo, {'2-iaas/aws/a.sh': 'touch "$OUT/ran"\n'})
    monkeypatch.setenv(name, 'x')
    run_aws(monkeypatch, repo, [SCRIPT_ENTRY])
    assert not (out / 'ran').exists()
    assert [row['status'] for row in common.read_rows()] == ['infrastructure']


@pytest.mark.parametrize('name, value', [
    ('AWS_PROFILE', ''), ('AWS_ENDPOINT_URL', 'https://127.0.0.1.evil:9297'),
    ('AWS_ENDPOINT_URL', 'https://localhost.example'), ('AWS_ENDPOINT_URL', 'https://127.0.0.1:٩٢٩٧'),
    ('AWS_ACCESS_KEY_ID', 'AKIAREAL'), ('AWS_ENDPOINT_URL', 'https://example.com:9297'),
    ('AWS_ENDPOINT_URL', 'http://127.0.0.1:9297'), ('FAKE_ACCOUNT', '123456789012')])
def test_preflight_refuses_wrong_key_endpoint_or_account(aws_env, monkeypatch, name, value):
    repo, out = aws_env
    commit_repo(repo, {'2-iaas/aws/a.sh': 'touch "$OUT/ran"\n'})
    monkeypatch.setenv(name, value)
    run_aws(monkeypatch, repo, [SCRIPT_ENTRY])
    assert not (out / 'ran').exists()
    assert [row['status'] for row in common.read_rows()] == ['infrastructure']


def test_child_environment_drops_real_credential_variables():
    env = run_aws_targets.child_env({'PATH': 'p', **dict.fromkeys(FORBIDDEN, 'x')})
    assert env['PATH'] == 'p' and not set(FORBIDDEN) & set(env)


WORKFLOW = Path(__file__).parents[1] / 'workflows' / 'cloud-api-check.yml'
LAYERS = {'azure': ['pytest', 'static', 'python', 'targets'], 'aws': ['pytest', 'static', 'python', 'cfn-lint', 'targets']}
AWS_VARIABLES = ('AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN', 'AWS_PROFILE')


def workflow():
    data = yaml.safe_load(WORKFLOW.read_text())
    data['on'] = data.pop(True, data.get('on'))  # YAML 1.1 reads the key `on` as True
    return data


def job_steps(name):
    return workflow()['jobs'][name]['steps']


def step_by_id(name, step_id):
    return next(step for step in job_steps(name) if step.get('id') == step_id)


def test_workflow_permissions_and_triggers():
    data = workflow()
    assert 'pull_request_target' not in data['on']
    assert set(data['on']) == {'workflow_dispatch', 'schedule'}
    assert data['on']['schedule'] == [{'cron': '0 5 * * *'}]
    assert data['permissions'] == {'contents': 'read'}
    assert all(job.get('permissions', {'contents': 'read'}) == {'contents': 'read'} for job in data['jobs'].values())


def test_workflow_jobs_timeouts_and_runner():
    jobs = workflow()['jobs']
    assert set(jobs) == {'azure', 'aws'}
    assert (jobs['azure']['timeout-minutes'], jobs['aws']['timeout-minutes']) == (60, 180)
    assert all(job['runs-on'] == 'ubuntu-latest' for job in jobs.values())


def test_workflow_actions_pinned_to_a_commit():
    uses = [step['uses'] for job in workflow()['jobs'].values() for step in job['steps'] if 'uses' in step]
    assert {name.split('@')[0] for name in uses} == {'actions/checkout', 'actions/setup-python'}
    assert all(re.fullmatch(r'[\w./-]+@[0-9a-f]{40}', name) for name in uses)


@pytest.mark.parametrize('job', ['azure', 'aws'])
def test_workflow_steps_have_ids_and_layer_order(job):
    steps = job_steps(job)
    ids = [step.get('id') for step in steps]
    assert all(ids) and len(set(ids)) == len(ids)
    layers = LAYERS[job]
    assert [i for i in ids if i in layers] == layers
    for layer in layers:
        assert step_by_id(job, layer)['if'] == 'always()'
    assert ids[-1] == 'summary' and steps[-1]['if'] == 'always()'
    assert all(i.startswith('install-') for i in ids if i.startswith('install'))


@pytest.mark.parametrize('job', ['azure', 'aws'])
def test_workflow_commands_run_the_checker_scripts(job):
    runs = {layer: step_by_id(job, layer)['run'] for layer in LAYERS[job]}
    assert 'pytest .github/api-check' in runs['pytest']
    assert f'check_cli.py --cloud {job}' in runs['static']
    assert f'check_python.py --cloud {job}' in runs['python']
    assert f'run_{job}_targets.py' in runs['targets'] and '--cfn-lint' not in runs['targets']
    if job == 'aws':
        assert 'run_aws_targets.py --cfn-lint' in runs['cfn-lint']
    summary_step = step_by_id(job, 'summary')
    assert f'summary.py --cloud {job}' in summary_step['run']
    assert summary_step['env'] == {'STEPS_JSON': '${{ toJSON(steps) }}'}
    assert 'API_CHECK_PYTHON' in ''.join(step.get('run', '') for step in job_steps(job))


def test_workflow_sets_no_real_aws_credentials():
    data = workflow()
    scopes = [data.get('env') or {}]
    for job in data['jobs'].values():
        scopes.append(job.get('env') or {})
        scopes += [step.get('env') or {} for step in job['steps']]
    assert not {name for scope in scopes for name in scope} & set(AWS_VARIABLES)
    assert '::add-mask::' in step_by_id('aws', 'emulator')['run']


def test_workflow_emulator_command():
    run = step_by_id('aws', 'emulator')['run']
    command = next(line for line in run.splitlines() if 'nohup' in line)
    assert '-p 9297' in command and '-t off' in command
    assert not re.search(r'\s-b\b|\s-a off', command)
    assert re.search(r'unset .*AWS_SESSION_TOKEN', run)


def test_workflow_curl_fails_on_http_errors():
    runs = [step['run'] for job in workflow()['jobs'].values() for step in job['steps'] if 'run' in step]
    calls = [line for run in runs for line in run.splitlines() if re.search(r'\bcurl\b', line)]
    assert calls
    assert all(re.search(r'\s(-[a-zA-Z]*f[a-zA-Z]*|--fail)\b', line) for line in calls)
    assert not any('| sudo bash' in line or '| bash' in line for line in calls)


def test_workflow_emulator_reads_credentials_in_one_call():
    run = step_by_id('aws', 'emulator')['run']
    assert run.count('import configparser') == 1
    assert run.index('::add-mask::') < run.index('>> "$GITHUB_ENV"')


def _run2_rows():
    """Rows the classifier writes for the run-2 errors, with the shipped emulator_gaps."""
    gaps = common.load_targets()['emulator_gaps']
    ssm = 'An error occurred (InvalidAMIID.NotFound) when calling the RunInstances operation: The image id ' \
          "'[resolve:ssm:/aws/service/canonical/ubuntu/server/26.04/stable/current/amd64/hvm/ebs-gp3/ami-id]'"
    lt = 'An error occurred (SsmInvalidParameter) when calling the CreateLaunchTemplate operation: The ' \
         'following aliases are invalid: /aws/service/canonical/ubuntu/server/26.04/stable/current/amd6'
    task = 'Waiter TasksRunning failed: Waiter encountered a terminal failure state: For expression ' \
           '"tasks[].lastStatus" we matched expected path: "STOPPED" at least once'
    cfn = 'Resource handler returned message: "this emulator does not apply the InvokedViaFunctionUrl ' \
          'property of AWS::Lambda::Permission"'
    s3 = 'listing tags for S3 (Simple Storage) Bucket (b): operation error S3 Control: ListTagsForResource, ' \
         'https response error StatusCode: 0'
    scripts = {
        '2': [_call(['ec2', 'run-instances'], 254, ssm, line=20), _call(['ec2', 'wait', 'instance-running'], 255, 'x')],
        '3': [_call(['ec2', 'create-launch-template'], 254, lt, line=9),
              _call(['autoscaling', 'create-auto-scaling-group'], 254, 'ValidationError: launch template does not exist', line=30)],
        '4': [_call(['ec2', 'run-instances'], 254, ssm, line=12)],
        '6': [_call(['ec2', 'run-instances'], 254, ssm, line=12)],
        '10': [_call(['logs', 'tail'], 254, 'An error occurred (ResourceNotFoundException) when calling the '
                     'FilterLogEvents operation: The specified log group does not exist.', line=40)],
        '12': [_call(['cloudformation', 'deploy'], 255, cfn)],
    }
    rows = []
    for exercise, calls in scripts.items():
        rows += classify.classify_script(exercise, f'{exercise}/aws/x.sh', calls, gaps)
    rows += classify.classify_script('4', '4/aws/aws-ecs-fargate.sh', [
        _call(['ecs', 'wait', 'tasks-running'], 255, task, line=91),
        _call(['ec2', 'describe-network-interfaces'], 254, 'InvalidNetworkInterfaceID.NotFound', line=105)], gaps)
    rows += classify.classify_terraform('14', [
        _diag('data.aws_ssm_parameter.ubuntu', 'reading SSM Parameter',
              "(/aws/service/canonical/ubuntu/server/26.04/stable/current/amd64/hvm/ebs-gp3/ami-id): couldn't find resource")],
        '', gaps)
    rows += classify.classify_terraform('15', [
        _diag('module.storage_route.aws_s3_bucket.telemetry', 'reading tags', s3),
        _diag('module.device.aws_iot_thing_principal_attachment.device', 'attaching', 'NotImplemented')], '', gaps)
    return rows


def test_run2_errors_are_covered_by_the_shipped_emulator_gaps():
    rows = _run2_rows()
    by = {(row['exercise'], row['check'], row['target']): row for row in rows}
    for key in [('2', 'ec2 run-instances', '2/aws/x.sh'), ('3', 'ec2 create-launch-template', '3/aws/x.sh'),
                ('4', 'ec2 run-instances', '4/aws/x.sh'), ('6', 'ec2 run-instances', '6/aws/x.sh'),
                ('4', 'ecs wait', '4/aws/aws-ecs-fargate.sh'), ('10', 'logs tail', '10/aws/x.sh'),
                ('12', 'cloudformation deploy', '12/aws/x.sh'),
                ('14', 'apply', 'data.aws_ssm_parameter.ubuntu'),
                ('15', 'apply', 'module.storage_route.aws_s3_bucket.telemetry')]:
        assert by[key]['status'] == 'not-covered' and by[key]['reason'], key
    assert by[('3', 'autoscaling create-auto-scaling-group', '3/aws/x.sh')]['status'] == 'consequential'
    assert by[('4', 'ec2 describe-network-interfaces', '4/aws/aws-ecs-fargate.sh')]['status'] == 'consequential'
    assert by[('2', 'ec2 wait', '2/aws/x.sh')]['status'] == 'consequential'
    closing = [row for row in rows if row['check'] == 'run' or row['target'] == 'terraform apply']
    assert len(closing) == 9 and all(row['status'] not in summary.FAILING for row in closing)
    assert all(row['status'] not in summary.FAILING for row in rows)


def test_run2_rows_make_summary_exit_zero(capsys):
    for row in _run2_rows():
        common.write_row(**row)
    assert summary.main(['--cloud', 'aws']) == 0
