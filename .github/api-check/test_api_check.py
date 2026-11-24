import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

import check_cli
import check_python
import common
import summary


@pytest.fixture(autouse=True)
def results_dir(tmp_path, monkeypatch):
    monkeypatch.setenv('RUNNER_TEMP', str(tmp_path))


def test_mask_values():
    assert common.mask('--master-user-password x') == '--master-user-password ***'
    assert common.mask('ADMIN_PASSWORD=x') == 'ADMIN_PASSWORD=***'
    assert common.mask('Variables={API_KEY=x,B=y}') == 'Variables={API_KEY=***,B=y}'
    assert common.mask('--token x --name n') == '--token *** --name n'
    assert common.mask('https://h/api?a=1&code=x&b=2') == 'https://h/api?a=1&code=***&b=2'


def test_mask_leaves_plain_text():
    assert common.mask('aws s3 ls --region eu-west-2') == 'aws s3 ls --region eu-west-2'


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
