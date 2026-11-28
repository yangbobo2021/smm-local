"""Real observer channels; these microcontrols are not E/H business proof."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/acceptance'))
from document_formats_guard_primitives import AUDIT_PRIMITIVES, IDENTITY_SOURCE, actual_identity
from document_formats_protocol_guards import HOOK
from document_formats_cross_os import RECEIVER_HOOK


def observed(tmp_path, kind, code):
    log = tmp_path / 'observer.jsonl'
    phase = tmp_path / 'phase.txt'
    phase.write_text('read-only')
    sources = tmp_path / 'sources.json'
    sources.write_text('[]')
    expected = [sys.executable, '-I', '-c', 'print(73428)', 'smm_local.mcp_server', '--db', str(tmp_path / '档案 空格 😀.sqlite3')]
    config = {'log': str(log), 'phase': str(phase), 'sources': str(tmp_path / 'protected'),
              'source_paths': str(sources) if kind == 'E' else [], 'network_endpoints': [],
              'mcp_wrapper': str(tmp_path / 'exact-mcp-wrapper.py'), 'mcp_argv': expected,
              'local_db': str(tmp_path / '档案 空格 😀.sqlite3'), 'listen_endpoints': [], 'expected_identity': actual_identity()}
    hook = tmp_path / 'hook.py'
    hook.write_text('C=' + repr(config) + '\n' + IDENTITY_SOURCE + '\n' + AUDIT_PRIMITIVES + '\n' + (HOOK if kind == 'E' else RECEIVER_HOOK) + '\n' + code)
    result = subprocess.run([sys.executable, '-I', '-X', 'utf8', str(hook)], capture_output=True, timeout=15)
    assert log.is_file(), result.stderr
    events = [json.loads(line) for line in log.read_text().splitlines()]
    return result, events


@pytest.mark.parametrize('kind', ['E', 'X'])
@pytest.mark.parametrize('channel', ['popen', 'system', 'spawn', 'posix-spawn', 'fork', 'exec'])
def test_private_guard_rejects_actual_child_start_channels(tmp_path, kind, channel):
    if channel in {'posix-spawn', 'fork'} and not hasattr(os, channel.replace('-', '_')):
        pytest.skip('API genuinely absent on this native platform')
    code = {
        'popen': 'import subprocess;subprocess.run([sys.executable,"-c","print(99999)"])',
        'spawn': 'os.spawnv(os.P_WAIT,sys.executable,[sys.executable,"-c","pass"])',
        'system': 'os.system("exit 0" if os.name=="nt" else ":")',
        'posix-spawn': 'pid=os.posix_spawn(sys.executable,[sys.executable,"-c","pass"],os.environ);os.waitpid(pid,0)',
        'fork': 'pid=os.fork();os._exit(0) if pid==0 else os.waitpid(pid,0)',
        'exec': 'os.execv(sys.executable,[sys.executable,"-c","print(99999)"])',
    }[channel]
    result, events = observed(tmp_path, kind, code)
    assert result.returncode != 0 and b'attempted child process' in result.stderr
    assert b'99999' not in result.stdout
    attempts = [e for e in events if e['kind'] == 'child-start']
    assert len(attempts) == 1
    assert attempts[0].get('allowed', False) is False


@pytest.mark.parametrize('kind', ['E', 'X'])
@pytest.mark.parametrize('channel', ['sendto', 'sendmsg', 'connect', 'connect-ex', 'dns'])
def test_private_guard_rejects_actual_udp_and_stream_egress(tmp_path, kind, channel):
    if channel == 'sendmsg' and not hasattr(socket.socket, 'sendmsg'):
        pytest.skip('sendmsg genuinely absent on this native platform')
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver:
        receiver.bind(('127.0.0.1', 0))
        address = receiver.getsockname()
        receiver.settimeout(.15)
        # Positive receiver control proves a missing negative payload has an
        # observable meaning, independent of the guarded child.
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
            sender.sendto(b'positive receiver control', address)
        assert receiver.recvfrom(100)[0] == b'positive receiver control'
        code = {
            'sendto': 'socket.socket(socket.AF_INET,socket.SOCK_DGRAM).sendto(b"blocked payload",' + repr(address) + ')',
            'sendmsg': 'socket.socket(socket.AF_INET,socket.SOCK_DGRAM).sendmsg([b"blocked payload"],[],0,' + repr(address) + ')',
            'connect': 'socket.socket().connect(' + repr(address) + ')',
            'connect-ex': 'socket.socket().connect_ex(' + repr(address) + ')',
            'dns': 'socket.getaddrinfo("models.example.invalid",443)',
        }[channel]
        result, events = observed(tmp_path, kind, code)
        marker = b'attempted network outside' if kind == 'E' else b'attempted outbound network'
        assert result.returncode != 0 and marker in result.stderr
        with pytest.raises(socket.timeout):
            receiver.recvfrom(100)
    attempts = [e for e in events if e['kind'] in {'network', 'network-call'}]
    assert len(attempts) == 1 and attempts[0].get('allowed', False) is False


@pytest.mark.parametrize('kind', ['E', 'X'])
def test_private_guard_preserves_real_socketpair(tmp_path, kind):
    result, _ = observed(tmp_path, kind, 'a,b=socket.socketpair();a.sendall(b"pair");assert b.recv(4)==b"pair";a.close();b.close()')
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize('actual_matches', [False, True])
def test_mcp_exception_checks_actual_command_not_only_wrapper_globals(tmp_path, actual_matches):
    actual = 'argv' if actual_matches else '[sys.executable,"-I","-c","print(99999)"]'
    body = 'import subprocess\nsubprocess.run(' + actual + ',check=True)'
    code = 'namespace={"argv":C["mcp_argv"],"sys":sys};exec(compile(' + repr(body) + ',C["mcp_wrapper"],"exec"),namespace)'
    result, events = observed(tmp_path, 'E', code)
    if actual_matches:
        assert result.returncode == 0 and result.stdout.strip() == b'73428', result.stderr
        starts = [e for e in events if e['kind'] == 'transport-start']
        assert starts and all(e['allowed'] for e in starts)
    else:
        assert result.returncode != 0 and b'attempted child process' in result.stderr
        assert not result.stdout and not [e for e in events if e['kind'] == 'transport-start']


def test_mcp_exception_rejects_changed_expected_bootstrap(tmp_path):
    code = ('namespace={"argv":[sys.executable,"-I","-c","print(99999)","smm_local.mcp_server","--db",C["local_db"]],"sys":sys};'
            'exec(compile("import subprocess\\nsubprocess.run(argv,check=True)",C["mcp_wrapper"],"exec"),namespace)')
    result, events = observed(tmp_path, 'E', code)
    assert result.returncode != 0 and b'attempted child process' in result.stderr
    assert not result.stdout and not [e for e in events if e['kind'] == 'transport-start']


def test_reply_exception_uses_real_task_listener_not_any_connected_socket():
    scope = {}
    exec(AUDIT_PRIMITIVES, scope)
    with socket.socket() as listener, socket.socket() as client:
        listener.bind(('127.0.0.1', 0))
        listener.listen(1)
        client.connect(listener.getsockname())
        accepted, _ = listener.accept()
        with accepted:
            endpoints = {listener.getsockname()}
            assert scope['accepted_server_reply'](accepted, None, endpoints)
            assert not scope['accepted_server_reply'](client, None, endpoints)
            assert not scope['accepted_server_reply'](accepted, None, set())
            assert not scope['accepted_server_reply'](accepted, accepted.getpeername(), endpoints)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as datagram:
        datagram.bind(('127.0.0.1', 0))
        assert not scope['accepted_server_reply'](datagram, None, {datagram.getsockname()})


def test_ocr_absence_probe_rejects_actual_path_component_and_explicit_data(tmp_path, monkeypatch):
    from document_formats_receiver_absence import ocr_absence
    engine = tmp_path / ('tesseract.exe' if os.name == 'nt' else 'tesseract')
    engine.write_bytes(b'observer control only, never executed')
    engine.chmod(0o700)
    monkeypatch.setenv('PATH', str(tmp_path))
    found = ocr_absence()
    assert found['status'] == 'present_or_not_proven'
    assert any(item['kind'] == 'engine' and Path(item['path']).samefile(engine) for item in found['present'])
    engine.unlink()
    monkeypatch.setenv('TESSDATA_PREFIX', str(tmp_path / 'explicit-data'))
    found = ocr_absence()
    assert found['status'] == 'present_or_not_proven'
    assert found['ocr_environment']['TESSDATA_PREFIX'] == str(tmp_path / 'explicit-data')


@pytest.mark.skipif(os.name != 'nt', reason='native Windows private API only')
def test_mcp_exception_rejects_direct_private_createprocess(tmp_path):
    # Even a valid expected command inside a matching wrapper is not enough:
    # native calls must originate from the real stdlib Popen implementation.
    body = ('import _winapi,subprocess\n'
            'handles=_winapi.CreateProcess(None,subprocess.list2cmdline(argv),None,None,False,0,None,None,subprocess.STARTUPINFO())\n'
            '_winapi.TerminateProcess(handles[0],93)\n'
            '_winapi.CloseHandle(handles[0]);_winapi.CloseHandle(handles[1])')
    code = 'namespace={"argv":C["mcp_argv"],"sys":sys};exec(compile(' + repr(body) + ',C["mcp_wrapper"],"exec"),namespace)'
    result, events = observed(tmp_path, 'E', code)
    assert result.returncode != 0 and b'attempted child process' in result.stderr
    assert not result.stdout and not [e for e in events if e['kind'] == 'transport-start']
    denied = [e for e in events if e['kind'] == 'child-start']
    assert len(denied) == 1 and denied[0]['validation_source'] == 'untrusted-native-caller'
