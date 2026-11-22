"""Pure archive identity, policy, durable control and signing primitives.

Vendored by the Hub build. This module must not import either network client.
"""
from __future__ import annotations

import base64
from contextlib import contextmanager
import hashlib
import hmac
import json
import os
from pathlib import Path
import tempfile
import time


MODES = frozenset({"all", "only", "except", "none"})
UPLOAD_SOURCES = frozenset({"codex", "claude-code"})


def canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def normalize_policy(value: dict) -> dict:
    if not isinstance(value, dict) or value.get("mode") not in MODES:
        raise ValueError("上传模式必须为 all、only、except 或 none")
    selected = value.get("projects", [])
    if not isinstance(selected, list) or any(not isinstance(k, str) or not k for k in selected):
        raise ValueError("请选择有效的稳定项目身份")
    mode = value["mode"]
    if mode in {"all", "none"} and selected:
        raise ValueError("all 和 none 不接受项目名单")
    return {"mode": mode, "projects": sorted(set(selected))}


def permits(policy: dict | None, project: str | None) -> bool:
    if policy is None or not project:
        return False
    mode = policy["mode"]
    return (mode == "all" or (mode == "only" and project in policy["projects"])
            or (mode == "except" and project not in policy["projects"]))


def digest(value) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def message_version(message: dict) -> str:
    return digest([message.get("role"), message.get("text"), message.get("timestamp")])


def legacy_message_key(record: dict) -> str:
    """Exactly preserve 0.4.0's existing Hub storage fingerprint."""
    identity = (["offset", record.get("timestamp"), record["occurrence"]]
                if record.get("occurrence") is not None else ["id", record["source_key"]])
    return hashlib.sha256(json.dumps([identity, record["role"], record["text"]],
                                     ensure_ascii=False).encode("utf-8")).hexdigest()


def sign(value: dict, key: str) -> str:
    payload = canonical(value)
    encoded = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    signature = hmac.new(bytes.fromhex(key), payload, hashlib.sha256).hexdigest()
    return "r1." + encoded + "." + signature


def verify(reference: str, key: str) -> dict:
    try:
        prefix, encoded, signature = reference.split(".")
        if prefix != "r1":
            raise ValueError()
        payload = base64.b64decode(encoded + "=" * (-len(encoded) % 4), altchars=b"-_", validate=True)
        expected = hmac.new(bytes.fromhex(key), payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise ValueError()
        value = json.loads(payload)
        if not isinstance(value, dict):
            raise ValueError()
        return value
    except (TypeError, ValueError, UnicodeError) as exc:
        raise ValueError("原文引用无效或已经损坏，请重新检索") from exc


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    temporary = Path(temporary)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(canonical(value) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        if os.name != "nt":
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def control_lock(path: Path, timeout: float = 5):
    """A bounded inter-process lock; never keep it across a network request."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with os.fdopen(os.open(path, os.O_RDWR | os.O_CREAT, 0o600), "r+b") as stream:
        deadline = time.monotonic() + timeout
        while True:
            try:
                if os.name == "nt":
                    import msvcrt
                    stream.seek(0)
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as exc:
                if time.monotonic() >= deadline:
                    raise RuntimeError("上传控制正在处理其他操作，请稍后重试") from exc
                time.sleep(.01)
        try:
            # Windows permits locking beyond EOF. Initializing before taking
            # the lock would itself write another process's locked byte.
            if os.fstat(stream.fileno()).st_size == 0:
                stream.write(b"\0")
                stream.flush()
            yield
        finally:
            if os.name == "nt":
                import msvcrt
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_UN)


class ControlConflict(ValueError):
    """A durable control mismatch. Caller must stop body I/O."""


class ControlGuard:
    def __init__(self, db_path: Path):
        self.path = Path(str(db_path.resolve()) + ".upload-guard.json")
        self.lock = self.path.with_suffix(self.path.suffix + ".lock")

    def read(self) -> dict:
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            if value.get("format") != 1 or not isinstance(value.get("devices"), dict):
                raise ValueError()
            return value
        except (OSError, ValueError, AttributeError) as exc:
            raise ControlConflict("上传保护状态缺失或损坏，正文已停止，请查看差异并处理恢复") from exc

    def write(self, value: dict) -> None:
        atomic_json(self.path, value)

    def prepare_restore(self) -> dict:
        from uuid import uuid4
        with control_lock(self.lock):
            value = self.read()
            value.update(control_epoch=uuid4().hex, restore_pending=True)
            self.write(value)
            return value
