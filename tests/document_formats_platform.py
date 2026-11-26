"""Task-only platform boundaries; no production imports or relaxed business checks."""
import ntpath
import os
import socket


def path_key(value):
    return os.path.normcase(os.path.abspath(os.fsdecode(value)))


def windows_target_key(value):
    """Compare ordinary absolute link targets without resolving a broken link.

    Extended paths with special dot/space components retain their namespace:
    stripping that prefix indiscriminately could change the target's meaning.
    """
    original = ntpath.normcase(os.fsdecode(value))
    if original.startswith('\\\\?\\unc\\'):
        candidate = '\\\\' + original[8:]
    elif original.startswith('\\\\?\\'):
        candidate = original[4:]
    else:
        return ntpath.normcase(ntpath.normpath(original))
    drive, tail = ntpath.splitdrive(candidate)
    if not drive or not tail.startswith('\\'):
        return original
    if any(part in {'.', '..'} or part.endswith(('.', ' ')) for part in tail.split('\\') if part):
        return original
    return ntpath.normcase(ntpath.normpath(candidate))


def internal_socketpair(frame, channel, address):
    """Only the real stdlib fallback may connect its csock to its own listener."""
    codes = {getattr(getattr(socket, name, None), '__code__', None)
             for name in ('socketpair', '_fallback_socketpair')} - {None}
    if frame.f_code not in codes or frame.f_globals is not socket.__dict__:
        return False
    listener = frame.f_locals.get('lsock')
    return (channel is frame.f_locals.get('csock') and listener is not None
            and channel.family == listener.family and channel.family in (socket.AF_INET, socket.AF_INET6)
            and isinstance(address, tuple) and len(address) >= 2
            and address[0] in {'127.0.0.1', '::1'}
            and address[:2] == listener.getsockname()[:2])


def utf8_environment(base, **values):
    return dict(base, PYTHONUTF8='1', PYTHONIOENCODING='utf-8', **values)


def process_identity(process):
    import psutil
    if not process.is_running():raise psutil.NoSuchProcess(process.pid)
    result = {'pid': process.pid, 'created': process.create_time(),
              'argv': process.cmdline(), 'exe': path_key(process.exe())}
    if not process.is_running():raise psutil.NoSuchProcess(process.pid)
    return result


def spawn_identity(process):
    """Creation identity before a platform launcher has settled its image/argv."""
    assert process.is_running()
    return {'pid': process.pid, 'created': process.create_time()}


def same_existing_path(left, right):
    try:
        return os.path.samefile(left, right)
    except OSError:
        return False


def matching_process(stamp):
    import psutil
    try:
        process = psutil.Process(stamp['pid'])
        if not process.is_running() or process.status() == psutil.STATUS_ZOMBIE:
            return None
        assert set(stamp) in ({'pid', 'created'}, {'pid', 'created', 'argv', 'exe'})
        assert process.create_time() == stamp['created'], 'task process creation identity changed'
        if 'argv' in stamp:
            assert process_identity(process) == stamp, 'task process identity changed'
        return process
    except (psutil.NoSuchProcess, psutil.ZombieProcess):
        return None


def process_tree(stamp):
    import psutil
    parent = matching_process(stamp)
    if parent is None:
        return []
    try:result = [process_identity(parent)]
    except (psutil.NoSuchProcess, psutil.ZombieProcess):return []
    try:children = parent.children(recursive=True)
    except (psutil.NoSuchProcess, psutil.ZombieProcess):children = []
    for child in children:
        try:
            result.append(process_identity(child))
        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            pass
    return result


def refresh_owned_records(records, executables):
    """Recheck creation and program before cleanup, allowing declared launchers."""
    import psutil
    result = []
    for stamp in records:
        process = matching_process({'pid': stamp['pid'], 'created': stamp['created']})
        if process is None:
            continue
        try:current = process_identity(process)
        except (psutil.NoSuchProcess, psutil.ZombieProcess):continue
        assert current['argv'][1:] == stamp['argv'][1:], 'task program arguments changed'
        same_image = same_existing_path(current['exe'], stamp['exe'])
        known_transition = (any(same_existing_path(stamp['exe'], p) for p in executables)
                            and any(same_existing_path(current['exe'], p) for p in executables))
        assert same_image or known_transition, 'task executable changed outside declared launchers'
        result.append(current)
    return result


def verify_server(launcher, value, *, argv, archive, owner, nonce, cwd, executables):
    import psutil
    assert set(value) == {'pid', 'archive', 'owner', 'nonce'}
    assert type(value['pid']) is int and value['pid'] > 0
    assert value['nonce'] == nonce and value['owner'] == owner
    assert same_existing_path(value['archive'], archive)
    members = process_tree(launcher)
    stamps = {item['pid']: item for item in members}
    assert value['pid'] in stamps, 'HTTP server is not our launcher or descendant'
    stamp = stamps[value['pid']]
    actual = matching_process(stamp)
    assert actual is not None and stamp['argv'][1:] == argv[1:]
    assert any(same_existing_path(stamp['exe'], p) for p in executables)
    assert same_existing_path(actual.cwd(), cwd)
    return stamp


def terminate_verified(records, *, owner=None):
    """Escalation only: each PID is checked again before the signal is sent."""
    import psutil
    processes = []
    for stamp in reversed(records):
        process = matching_process(stamp)
        if process is not None:
            try:
                process.terminate()
                processes.append((stamp, process))
            except psutil.NoSuchProcess:
                pass
    if owner is not None:
        import subprocess
        try:
            owner.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass
    watched = [p for _, p in processes if owner is None or p.pid != owner.pid]
    psutil.wait_procs(watched, timeout=2)
    for stamp, _ in processes:
        process = matching_process(stamp)
        if process is not None:
            try:
                process.kill()
            except psutil.NoSuchProcess:
                pass
    if owner is not None:
        owner.wait(timeout=2)
    _, alive = psutil.wait_procs(watched, timeout=2)
    assert not alive, 'task process tree did not exit'


def preserve_diagnostics(root, label):
    """Keep only task logs; never copy databases, credentials or source bodies."""
    import hashlib
    import json
    import stat
    from pathlib import Path
    destination = os.environ.get('ACCEPTANCE_EVIDENCE_DIR')
    if not destination:
        return
    root = Path(root)
    folder = Path(destination) / 'diagnostics'
    blobs = folder / 'blobs'
    blobs.mkdir(parents=True, exist_ok=True)
    rows = []
    paths = []
    for directory, directories, files in os.walk(root, followlinks=False):
        kept = []
        for name in directories:
            path = Path(directory) / name
            info = path.lstat()
            if stat.S_ISDIR(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & 0x400:
                kept.append(name)
        directories[:] = kept
        paths.extend(Path(directory) / name for name in files)
    for path in paths:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            continue
        identity_log = path.suffix == '.json' and path.stem.removeprefix('identity-').isdigit() and path.stem.startswith('identity-')
        if not (path.name.endswith(('.stderr', '.stdout')) or identity_log
                or path.name in {'supervision.json', 'active.json', 'cleanup-incomplete.json'}):
            continue
        try:
            raw = path.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            target = blobs / digest
            if not target.exists():
                target.write_bytes(raw)
            rows.append({'path': path.relative_to(root).as_posix(), 'sha256': digest, 'bytes': len(raw)})
        except OSError as error:
            rows.append({'path': path.relative_to(root).as_posix(), 'error': str(error)})
    key = hashlib.sha256((str(root) + label).encode('utf-8')).hexdigest()
    (folder / (key + '.json')).write_text(json.dumps({'label': label, 'files': rows}, ensure_ascii=False), encoding='utf-8')


def diagnostics_on_failure(function):
    import functools
    @functools.wraps(function)
    def wrapped(self, *args, **kwargs):
        try:
            return function(self, *args, **kwargs)
        except BaseException:
            try:
                preserve_diagnostics(self.root, function.__name__ + '-' + str(self.number))
            except Exception:
                # Diagnostics must never replace the original test failure.
                pass
            raise
    return wrapped
