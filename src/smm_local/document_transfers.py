"""Bounded resumable immutable blob transfers; standard-library only."""
from __future__ import annotations
import json
import os
import stat
import time
from pathlib import Path
from .archive_protocol import atomic_json, control_lock, digest
from .document_results import sha

BLOCK_LIMIT = 1024 * 1024

TRANSFER_TTL = 24 * 60 * 60


def _regular(path, directory=False):
    value = path.lstat()
    expected = stat.S_ISDIR if directory else stat.S_ISREG
    if not expected(value.st_mode) or bool(getattr(value, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400)):
        raise ValueError('传输存储不能经过链接、junction或特殊文件')


def _expired_marker(snapshots, transfer_id):
    path = snapshots._directory('expired-transfers') / transfer_id
    if os.path.lexists(path):
        _regular(path)
    return path


def _states(snapshots):
    directory = snapshots.root / 'transfers'
    if not os.path.lexists(directory):
        return []
    _regular(directory, directory=True)
    values = []
    for folder in directory.iterdir():
        _regular(folder, directory=True)
        if len(folder.name) != 32 or any(c not in '0123456789abcdef' for c in folder.name):
            raise ValueError('传输暂存身份无效')
        path = folder / 'state.json'
        if not os.path.lexists(path):
            if any(folder.iterdir()):
                raise ValueError('传输暂存缺少元信息')
            continue
        _regular(path)
        with path.open('rb') as source:
            raw = source.read(128 * 1024 + 1)
        if len(raw) > 128 * 1024:
            raise ValueError('传输元信息超限')
        state = json.loads(raw)
        for kind, item in state['blobs'].items():
            if kind not in {'raw', 'results'} or type(item['bytes']) is not int or item['bytes'] < 0:
                raise ValueError('传输预约无效')
            snapshots.blob(kind, item['sha256'])
        values.append((folder, state))
    return values


def _expired(snapshots, folder, state, now):
    return _expired_marker(snapshots, folder.name).exists() or (not state.get('committed') and now - state['created_at'] >= TRANSFER_TTL)


def reclaim_expired(snapshots):
    """Called under capacity.lock; retain identity and canonical committed blobs.

    Keep state metadata for crash-idempotent cleanup: if interrupted after a
    marker or an unlink, the next admission can finish the same retirement.
    """
    now = time.time()
    states = _states(snapshots)
    expired = [(folder, state) for folder, state in states if _expired(snapshots, folder, state, now)]
    live = {(kind, item['sha256']) for folder, state in states if not _expired(snapshots, folder, state, now) for kind, item in state['blobs'].items()}
    # Reject the identity durably BEFORE releasing any promise or body bytes.
    for folder, state in expired:
        marker = _expired_marker(snapshots, folder.name)
        if not marker.exists():
            atomic_json(marker, {'expired': True})
    for folder, state in expired:
        for kind, item in state['blobs'].items():
            if (kind, item['sha256']) in live:
                continue
            directory = snapshots.root / kind
            if not os.path.lexists(directory):
                continue
            _regular(directory, directory=True)
            incoming = directory / ('.incoming-' + item['sha256'])
            if os.path.lexists(incoming):
                _regular(incoming)
                incoming.unlink()



def reservations(snapshots, expected_blobs=None):
    """Count each promised blob conservatively, including unreceived bytes."""
    reserved = {}
    now = time.time()
    for folder, state in _states(snapshots):
        if _expired(snapshots, folder, state, now):
            continue
        for kind, item in state['blobs'].items():
            if kind not in {'raw', 'results'} or type(item['bytes']) is not int or item['bytes'] < 0:
                raise ValueError('传输预约无效')
            target = snapshots.blob(kind, item['sha256'])
            requested = expected_blobs.get(kind) if expected_blobs is not None else None
            if requested and requested['sha256'] == item['sha256'] and requested['bytes'] != item['bytes']:
                raise ValueError('同一原件或结果SHA已有不同长度预约')
            # A shorter untrusted declaration must not overwrite a larger live
            # promise. Group before subtracting bytes already on disk, so both
            # accounting and legacy conflicting entries are order-independent.
            if not target.exists():
                key = (kind, item['sha256'])
                reserved[key] = max(reserved.get(key, 0), item['bytes'])
    outstanding = 0
    for (kind, digest), promised in reserved.items():
        incoming = snapshots.root / kind / ('.incoming-' + digest)
        present = incoming.stat().st_size if incoming.exists() else 0
        if present > promised:
            raise ValueError('传输暂存字节越界')
        outstanding += promised - present
    return outstanding


class BlobTransfers:
    def __init__(self, snapshots, *, raw_only=False):
        self.snapshots = snapshots
        self.kinds = {'raw'} if raw_only else {'raw', 'results'}

    def _folder(self, transfer_id):
        if not isinstance(transfer_id, str) or len(transfer_id) != 32 or any(c not in '0123456789abcdef' for c in transfer_id):
            raise ValueError('传输身份无效')
        return self.snapshots._directory('transfers') / transfer_id

    def _load(self, transfer_id):
        folder = self._folder(transfer_id)
        marker = _expired_marker(self.snapshots, transfer_id)
        if marker.exists():
            raise ValueError('传输已过期，请用新的提交身份重新传输')
        if folder.is_symlink():
            raise ValueError('传输目录不能经过链接')
        _regular(folder, directory=True)
        path = folder / 'state.json'
        if path.is_symlink():
            raise ValueError('传输状态不能经过链接')
        _regular(path)
        with path.open('rb') as source:
            raw = source.read(128 * 1024 + 1)
        if len(raw) > 128 * 1024:
            raise ValueError('传输状态超限')
        state = json.loads(raw)
        if set(state['blobs']) != self.kinds:
            raise ValueError('传输不属于此原件或成套接收入口')
        if not state.get('committed') and time.time() - state['created_at'] >= TRANSFER_TTL:
            atomic_json(marker, {'expired': True})
            raise ValueError('传输已过期，请用新的提交身份重新传输')
        return folder, state

    def _read_blob(self, folder, kind, item):
        target = self.snapshots.blob(kind, item['sha256'])
        path = target if target.exists() else self.snapshots._directory(kind) / ('.incoming-' + item['sha256'])
        if path.is_symlink():
            raise ValueError('传输内容不能经过链接')
        with path.open('rb') as source:
            raw = source.read(item['bytes'] + 1)
        if len(raw) != item['bytes'] or sha(raw) != item['sha256']:
            raise ValueError('传输内容不完整或摘要错误')
        return raw

    def _status(self, transfer_id, folder, state):
        received = {}
        for kind, item in state['blobs'].items():
            target = self.snapshots.blob(kind, item['sha256'])
            part = self.snapshots._directory(kind) / ('.incoming-' + item['sha256'])
            count = item['bytes'] if target.exists() else (part.stat().st_size if part.exists() else 0)
            if count > item['bytes']:
                raise ValueError('传输已收数据越界')
            received[kind] = count if count == item['bytes'] else count // BLOCK_LIMIT * BLOCK_LIMIT
        return {'transfer_id': transfer_id, 'block_bytes': BLOCK_LIMIT, 'received': received, 'committed': bool(state.get('committed'))}

    def begin(self, binding, blobs):
        from .document_snapshots import RAW_LIMIT, STAGING_LIMIT
        from .document_results import RESULT_LIMIT
        if set(blobs) != self.kinds:
            raise ValueError('必须成套传输原件和结果')
        for kind, item in blobs.items():
            maximum = RAW_LIMIT if kind == 'raw' else RESULT_LIMIT
            if set(item) != {'bytes', 'sha256'} or type(item['bytes']) is not int or not 0 < item['bytes'] <= maximum:
                raise ValueError('传输原件/结果长度无效')
            self.snapshots.blob(kind, item['sha256'])
        if len(json.dumps(binding, ensure_ascii=False).encode('utf-8')) > 64 * 1024:
            raise ValueError('传输绑定超限')
        transfer_id = digest([binding.get(key) for key in ('hub_id', 'document_epoch', 'device_id', 'archive_id', 'project_key', 'generation', 'submission_id')])[:32]
        folder = self._folder(transfer_id)
        with control_lock(self.snapshots.root / 'capacity.lock'):
            reclaim_expired(self.snapshots)
            if _expired_marker(self.snapshots, transfer_id).exists():
                raise ValueError('传输已过期，请用新的提交身份重新传输')
            if folder.exists():
                saved_folder, state = self._load(transfer_id)
                if state['binding'] != binding or state['blobs'] != blobs:
                    raise ValueError('同一传输身份不能改变数据')
                return self._status(transfer_id, saved_folder, state)
            self.snapshots.reclaim_candidates()
            # Validate shared SHA/length contracts before creating a new state.
            reservations(self.snapshots, blobs)
            required = 0
            for kind, item in blobs.items():
                target = self.snapshots.blob(kind, item['sha256'])
                if target.exists():
                    self._read_blob(folder, kind, item)
                else:
                    required += item['bytes']
            folder.mkdir(mode=0o700)
            state = {'binding': binding, 'blobs': blobs, 'created_at': time.time(), 'committed': False}
            try:
                atomic_json(folder / 'state.json', state)
                if self.snapshots._unpublished_bytes() > STAGING_LIMIT:
                    raise ValueError('未发布暂存超过256MiB，拒绝新传输')
                return self._status(transfer_id, folder, state)
            except BaseException:
                (folder / 'state.json').unlink(missing_ok=True)
                folder.rmdir()
                raise

    def binding(self, transfer_id):
        with control_lock(self.snapshots.root / 'capacity.lock'):
            return self._load(transfer_id)[1]['binding']

    def part(self, transfer_id, kind, offset, raw, expected_sha):
        if kind not in {'raw', 'results'} or type(offset) is not int or offset < 0 or offset % BLOCK_LIMIT:
            raise ValueError('传输块类型/起点无效')
        if not isinstance(raw, bytes) or not 0 < len(raw) <= BLOCK_LIMIT or sha(raw) != expected_sha:
            raise ValueError('传输块大小或摘要无效')
        with control_lock(self.snapshots.root / 'capacity.lock'):
            folder, state = self._load(transfer_id)
            item = state['blobs'][kind]
            if offset >= item['bytes'] or len(raw) != min(BLOCK_LIMIT, item['bytes'] - offset):
                raise ValueError('传输块超出声明范围')
            target = self.snapshots.blob(kind, item['sha256'])
            path = target if target.exists() else self.snapshots._directory(kind) / ('.incoming-' + item['sha256'])
            if path.is_symlink():
                raise ValueError('传输块不能经过链接')
            size = path.stat().st_size if path.exists() else 0
            if offset < size:
                with path.open('rb') as source:
                    source.seek(offset)
                    existing = source.read(len(raw))
                    if existing != raw[:len(existing)]:
                        raise ValueError('重复块的数据不一致')
                if len(existing) < len(raw):
                    with path.open('ab') as output:
                        output.write(raw[len(existing):])
                        output.flush()
                        os.fsync(output.fileno())
            elif offset != size or state.get('committed'):
                raise ValueError('请从当前已收位置继续传输')
            else:
                with path.open('ab') as output:
                    output.write(raw)
                    output.flush()
                    os.fsync(output.fileno())
            return self._status(transfer_id, folder, state)

    def commit(self, transfer_id, validator):
        with control_lock(self.snapshots.root / 'capacity.lock'):
            folder, state = self._load(transfer_id)
            raw = self._read_blob(folder, 'raw', state['blobs']['raw'])
            result = self._read_blob(folder, 'results', state['blobs']['results']) if 'results' in self.kinds else None
            value = validator(state['binding'], raw, result)
            for kind, item in state['blobs'].items():
                target = self.snapshots._directory(kind) / item['sha256']
                part = self.snapshots._directory(kind) / ('.incoming-' + item['sha256'])
                if target.exists():
                    self._read_blob(folder, kind, item)
                    self.snapshots._own_blob(kind,item['sha256'],created=False)
                    if part.exists():
                        part.unlink()
                else:
                    os.replace(part, target)
                    self.snapshots._own_blob(kind,item['sha256'],created=True)
            state['committed'] = True
            atomic_json(folder / 'state.json', state)
            return state['binding'], value
