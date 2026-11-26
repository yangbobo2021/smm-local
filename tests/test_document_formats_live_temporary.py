"""Real Windows deletion-pending directories must not break space supervision.

The walk wrapper only schedules real filesystem changes after enumeration; it
never supplies a fabricated result or exception to the product.
"""
from __future__ import annotations

import ctypes
import hashlib
import json
import os
from pathlib import Path
import threading

import pytest

from smm_local.document_supervisor import TEMP_LIMIT, temporary_bytes

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='real Windows handle semantics')


class DirectoryHandle:
    def __init__(self, path, *, shared=True):
        from ctypes import wintypes as w
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.kernel.CreateFileW.argtypes = [w.LPCWSTR, w.DWORD, w.DWORD,
                                           ctypes.c_void_p, w.DWORD, w.DWORD, w.HANDLE]
        self.kernel.CreateFileW.restype = w.HANDLE
        self.kernel.CloseHandle.argtypes = [w.HANDLE]
        self.kernel.CloseHandle.restype = w.BOOL
        self.kernel.SetFileInformationByHandle.argtypes = [w.HANDLE, ctypes.c_int,
                                                          ctypes.c_void_p, w.DWORD]
        self.kernel.SetFileInformationByHandle.restype = w.BOOL
        # DELETE for disposition, FILE_LIST_DIRECTORY for exclusive observation.
        self.value = self.kernel.CreateFileW(str(path), 0x10000 if shared else 1,
                                             7 if shared else 0, None, 3, 0x02000000, None)
        if self.value == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        self.lock = threading.Lock()

    def mark_deleted(self):
        class Disposition(ctypes.Structure):
            _fields_ = [('DeleteFile', ctypes.c_ubyte)]  # Win32 BOOLEAN, not BOOL.
        info = Disposition(1)
        if not self.kernel.SetFileInformationByHandle(self.value, 4, ctypes.byref(info),
                                                       ctypes.sizeof(info)):
            raise ctypes.WinError(ctypes.get_last_error())

    def close(self):
        with self.lock:
            if self.value is not None:
                if not self.kernel.CloseHandle(self.value):
                    raise ctypes.WinError(ctypes.get_last_error())
                self.value = None


def error_info(exc):
    return {'type': type(exc).__name__, 'errno': exc.errno,
            'winerror': getattr(exc, 'winerror', None)}


def test_live_temporary_deletion_keeps_exact_supervision(tmp_path, monkeypatch):
    root = tmp_path / 'task'
    root.mkdir()
    assert temporary_bytes(root) == 0
    kept = root / 'kept.bin'
    original = b'K' * 37
    kept.write_bytes(original)
    observations = {'scope': 'Windows component temporary-space sampler only',
                    'errors': [], 'cleanup': []}
    handles = []
    try:
        # Persistent inability to observe is not a harmless deletion race.
        denied = root / 'inaccessible'
        denied.mkdir()
        (denied / 'data.bin').write_bytes(b'D' * 41)
        handle = DirectoryHandle(denied, shared=False)
        handles.append(handle)
        with pytest.raises(PermissionError) as raw_denial:
            list(os.scandir(denied))
        observations['persistent_native_denial'] = error_info(raw_denial.value)
        real_walk = os.walk
        denial_walks = []

        def bounded_denial_walk(*args, **kwargs):
            denial_walks.append(True)
            assert len(denial_walks) <= 2, 'more than one full rescan'
            yield from real_walk(*args, **kwargs)

        with monkeypatch.context() as patch:
            patch.setattr(os, 'walk', bounded_denial_walk)
            with pytest.raises(PermissionError) as product_denial:
                temporary_bytes(root)
        observations['persistent_walks'] = len(denial_walks)
        observations['persistent_product_denial'] = error_info(product_denial.value)
        handle.close()
        assert temporary_bytes(root) == 78
        assert (denied / 'data.bin').read_bytes() == b'D' * 41
        (denied / 'data.bin').unlink()
        denied.rmdir()
        root_handle = DirectoryHandle(root, shared=False)
        handles.append(root_handle)
        with pytest.raises(PermissionError):
            list(os.scandir(root))
        root_walks = []

        def root_denial_walk(*args, **kwargs):
            root_walks.append(True)
            assert len(root_walks) <= 1, 'must not rescan an unreadable task root'
            yield from real_walk(*args, **kwargs)

        with monkeypatch.context() as patch:
            patch.setattr(os, 'walk', root_denial_walk)
            with pytest.raises(PermissionError):
                temporary_bytes(root)
        observations['inaccessible_root_walks'] = len(root_walks)
        root_handle.close()
        assert temporary_bytes(root) == 37
        observations['inaccessible_root_rejected'] = True

        # Missing task roots must not silently report zero used space.
        missing = tmp_path / 'missing'
        with pytest.raises(FileNotFoundError):
            temporary_bytes(missing)
        observations['missing_root_rejected'] = True

        # Counts use true logical bytes, including the unchanged real quota.
        sparse = root / 'boundary.bin'
        with sparse.open('wb') as file:
            file.truncate(TEMP_LIMIT - len(original))
        assert temporary_bytes(root) == 256 * 1024 * 1024
        with sparse.open('ab') as file:
            file.write(b'+')
        assert temporary_bytes(root) == 256 * 1024 * 1024 + 1
        sparse.unlink()
        observations['boundary_bytes'] = [256 * 1024 * 1024, 256 * 1024 * 1024 + 1]

        pending = [root / 'pdf-one', root / 'pdf-two']
        for directory, size in zip(pending, (13, 19)):
            directory.mkdir()
            (directory / 'decoded.bin').write_bytes(b'P' * size)
            handles.append(DirectoryHandle(directory))
        assert temporary_bytes(root) == 69
        real_walk = os.walk
        triggered = False
        walk_calls = 0
        released = False
        late = root / 'late.bin'

        def scheduled_walk(top, *args, **kwargs):
            nonlocal triggered, walk_calls, released
            walk_calls += 1
            assert walk_calls <= 2, 'more than one full rescan'
            if triggered:
                yield from real_walk(top, *args, **kwargs)
                return
            triggered = True
            real_onerror = kwargs.get('onerror')

            def observed_error(exc):
                observations['errors'].append(error_info(exc))
                if real_onerror:
                    real_onerror(exc)

            kwargs['onerror'] = observed_error
            iterator = real_walk(top, *args, **kwargs)
            first = next(iterator)
            assert set(directory.name for directory in pending) <= set(first[1])
            for directory, item in zip(pending, handles[-2:]):
                (directory / 'decoded.bin').unlink()
                item.mark_deleted()
                # Independently demonstrate the actual OS condition before sampling.
                with pytest.raises(PermissionError) as native:
                    list(os.scandir(directory))
                assert native.value.winerror == 5
            late.write_bytes(b'L' * 11)
            assert late.name not in first[2]
            yield first
            try:
                yield from iterator
            except PermissionError:
                # Real failed traversal is allowed to unwind; close only our
                # own handles so an immediate complete rescan can now succeed.
                for item in handles:
                    item.close()
                released = True
                raise

        with monkeypatch.context() as patch:
            patch.setattr(os, 'walk', scheduled_walk)
            count = temporary_bytes(root)
        observations['after_deletion_bytes'] = count
        assert count == 48
        assert walk_calls == 2
        assert released
        observations['complete_walks'] = walk_calls
        assert triggered
        assert any(row['winerror'] == 5 for row in observations['errors'])
        assert all(not directory.exists() for directory in pending)
        assert temporary_bytes(root) == 48
        assert late.read_bytes() == b'L' * 11
        assert kept.read_bytes() == original
        observations['retained_sha256'] = hashlib.sha256(kept.read_bytes()).hexdigest()
    finally:
        for item in handles:
            item.close()
        observations['cleanup'] = {'all_handles_closed': all(h.value is None for h in handles),
                                   'kept_unchanged': kept.read_bytes() == original}
        destination = os.environ.get('ACCEPTANCE_EVIDENCE_DIR')
        if destination:
            path = Path(destination)
            path.mkdir(parents=True, exist_ok=True)
            (path / 'live-temporary-observations.json').write_text(
                json.dumps(observations, indent=2), encoding='utf-8')
