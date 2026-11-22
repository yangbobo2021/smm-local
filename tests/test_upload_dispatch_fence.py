"""Additional commit-boundary regressions; synthetic archives, no live services."""
import pytest

from smm_local import federation
from test_005_contracts import pair, add_local, connect, bodies


@pytest.mark.parametrize('change', ['address', 'token', 'device_name'])
def test_same_hub_configuration_change_discards_old_dispatch_snapshot(pair, monkeypatch, change):
    add_local(pair, 'a', 'A', 'only dispatched from current configuration')
    original = connect(pair)
    federation.choose_upload(pair.local, 'all', [])
    request = federation._request
    changed = False
    def mutate(config, route, payload=None):
        nonlocal changed
        result = request(config, route, payload)
        if route == '/known-upload-messages' and not changed:
            changed = True
            if change == 'token':
                pair.token_file.write_text('different-synthetic-token-' + 'b' * 40)
            assert federation.configure_hub(pair.local,
                'http://localhost:18771' if change == 'address' else original['address'],
                'renamed-device' if change == 'device_name' else original['device_name'],
                str(pair.token_file))['connected']
        return result
    monkeypatch.setattr(federation, '_request', mutate)
    assert federation.push_pending(pair.local)['uploaded'] == 0
    assert bodies(pair.remote) == []
    assert federation.upload_status(pair.local)['policy']['mode'] == 'all'
    assert federation.push_pending(pair.local)['uploaded'] == 1
    assert bodies(pair.remote) == ['only dispatched from current configuration']


@pytest.mark.parametrize('mutation', ["UPDATE messages SET source_key='changed-key'",
                                    'UPDATE messages SET position=9',
                                    "UPDATE conversations SET source_session_id='changed-session'"])
def test_message_identity_change_during_lookup_rebuilds_before_dispatch(pair, monkeypatch, mutation):
    add_local(pair, 'a', 'A', 'one exact current identity')
    connect(pair); federation.choose_upload(pair.local, 'all', [])
    request = federation._request
    changed = False
    def mutate(config, route, payload=None):
        nonlocal changed
        result = request(config, route, payload)
        if route == '/known-upload-messages' and not changed:
            changed = True
            with pair.local.connect() as con:
                con.execute(mutation)
        return result
    monkeypatch.setattr(federation, '_request', mutate)
    first = federation.push_pending(pair.local)
    assert first['uploaded'] == 0 and first['pending']
    assert bodies(pair.remote) == []
    assert federation.push_pending(pair.local)['uploaded'] == 1
    assert bodies(pair.remote) == ['one exact current identity']
    assert federation.push_pending(pair.local)['pending'] is False
