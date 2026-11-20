import json
import os
from pathlib import Path

import pytest
import yaml

import check_cli
import common


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
