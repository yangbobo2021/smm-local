"""Native directory policy, with real Windows descriptors rather than ACL mocks."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from smm_hub.document_storage_windows import configure
from smm_local.core import Archive
from smm_local.document_snapshots import Snapshots


def test_local_and_foreground_snapshot_policy_stays_private(tmp_path):
    db = Archive(tmp_path / 'local.sqlite3')
    configure(db)
    snapshots = Snapshots(db)
    directory = snapshots._directory('raw')
    assert not hasattr(db, '_document_snapshot_directory')
    if os.name != 'nt':
        assert directory.stat().st_mode & 0o777 == 0o700
    foreground = Archive(tmp_path / 'smm-hub.sqlite3')
    configure(foreground)
    assert not hasattr(foreground, '_document_snapshot_directory')


@pytest.mark.skipif(sys.platform != 'win32', reason='requires real Windows security descriptors')
def test_managed_hub_atomic_role_directories_and_existing_acl_safety(tmp_path):
    import ctypes
    if not ctypes.windll.shell32.IsUserAnAdmin():
        pytest.skip('component prepares a real protected service root as administrator')
    from smm_hub.document_storage_windows import Directories
    from smm_hub.hub_os import Service
    from smm_local.document_processing import execution_identity
    def descriptor(path):
        expression = "(Get-Acl -LiteralPath '" + str(path).replace("'", "''") + "').Sddl"
        return subprocess.check_output(['powershell.exe', '-NoProfile', '-Command', expression])
    root = tmp_path / 'managed'
    root.mkdir()
    subprocess.run(['icacls.exe', str(root), '/inheritance:r', '/grant:r',
        '*S-1-5-32-544:(OI)(CI)F', '*S-1-5-18:(OI)(CI)F', '*S-1-5-19:(OI)(CI)M'], check=True, capture_output=True)
    # Administrator tokens may default ownership to BA or to the user SID.
    # Explicitly construct the latter instead of depending on machine defaults.
    subprocess.run(['icacls.exe', str(root), '/setowner', '*' + execution_identity()['sid']],
        check=True, capture_output=True)
    old = root / 'old';old.mkdir(mode=0o700)
    old_body = old / 'text';old_body.write_bytes(b'unchanged old text')
    old_alias = tmp_path / 'old-alias';os.link(old_body, old_alias)
    before_claim = {p: descriptor(p) for p in (old, old_body, old_alias)}
    root_dacl = descriptor(root).split(b'D:', 1)[1]
    with pytest.raises(ValueError, match='所有者'):
        Directories(root).create(root / '.document-snapshots' / 'raw')
    assert not (root / '.document-snapshots').exists()
    Service(root).claim_state_owner()
    assert descriptor(root).split(b'D:', 1)[1] == root_dacl
    assert all(descriptor(p) == acl for p, acl in before_claim.items())
    assert old_body.read_bytes() == old_alias.read_bytes() == b'unchanged old text'
    (root / 'hub.json').write_text(json.dumps({'address': 'https://localhost:12345',
        'bind': '127.0.0.1', 'port': 12345, 'enabled': True}))
    db = Archive(root / 'smm-hub.sqlite3')
    configure(db)
    snapshots = Snapshots(db)
    target = snapshots.root / 'raw'
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert all(p == target for p in pool.map(lambda _: snapshots._directory('raw'), range(8)))
    # Verify the actual descriptor and effective inherited grants on new bytes.
    (target / 'new').write_bytes(b'independent byte truth')
    factory = Directories(root)
    for path in (snapshots.root, target, snapshots._directory('tasks/current')):
        with factory._pin(path) as handle:
            factory._check(handle)
    raw_acl = descriptor(target / 'new')
    assert b';;;LS)' in raw_acl and b';;;OW)' not in raw_acl
    # No directory repair may silently modify a legacy file or its hardlink.
    legacy = snapshots.root / 'legacy700'
    legacy.mkdir(mode=0o700)
    body = legacy / 'old';body.write_bytes(b'unchanged legacy')
    alias = root / 'outside-alias';os.link(body, alias)
    before = {p: descriptor(p) for p in (legacy, body, alias)}
    with pytest.raises(ValueError, match='权限'):
        snapshots._directory('legacy700')
    assert all(descriptor(p) == acl for p, acl in before.items())
    assert body.read_bytes() == alias.read_bytes() == b'unchanged legacy'
    # Pinning prevents rename and reparse traversal, not just a lexical check.
    with factory._pin(target):
        with pytest.raises(PermissionError):
            target.rename(snapshots.root / 'renamed')
    junction = snapshots.root / 'junction'
    subprocess.run(['cmd.exe', '/c', 'mklink', '/J', str(junction), str(root)], check=True, capture_output=True)
    try:
        with pytest.raises(ValueError, match='junction'):
            snapshots._directory('junction/escape')
        assert not (root / 'escape').exists()
    finally:
        os.rmdir(junction)
    with pytest.raises(ValueError):
        factory.create(snapshots.root / '..' / 'outside')
    # A fake profile never allows a broadly accessible foreground tree to be
    # granted service access. Validation precedes any new snapshot directory.
    broad = tmp_path / 'broad';broad.mkdir()
    with pytest.raises(ValueError, match='权限|所有者'):
        Directories(broad).create(broad / '.document-snapshots' / 'raw')
    assert not (broad / '.document-snapshots').exists()
