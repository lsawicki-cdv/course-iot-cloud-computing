import pytest
import yaml

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
