"""Pure document validation and rollback protection, shared with the Hub wheel."""

from __future__ import annotations
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import re
from .archive_protocol import atomic_json, canonical, control_lock, digest

FILE_LIMIT = 2 * 1024 * 1024
REQUEST_LIMIT = 16 * 1024 * 1024


def identity(value, label="身份"):
    if not isinstance(value, str) or not re.fullmatch("[0-9a-f]{32}", value):
        raise ValueError(label + "须为32位小写十六进制稳定身份")
    return value


def integer(value, label="数值", minimum=1):
    if type(value) is not int or value < minimum:
        raise ValueError(label + "不是有效整数")
    return value


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def normalize(raw):
    if not isinstance(raw, bytes) or len(raw) > FILE_LIMIT:
        raise ValueError("文件超过2MiB")
    if b"\0" in raw:
        raise ValueError("文件含二进制NUL")
    try:
        text = raw.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    except UnicodeError as exc:
        raise ValueError("文件不是严格UTF-8文本") from exc
    if len(text.encode("utf-8")) > FILE_LIMIT:
        raise ValueError("规范化文本超过2MiB")
    return text


def document(value):
    if not isinstance(value, dict):
        raise ValueError("文档须为对象")
    required = {
        "document_id",
        "version",
        "sha256",
        "text_sha256",
        "text",
        "text_length",
        "capture_sequence",
        "path",
        "display_name",
        "captured_at",
        "captured_by_source_id",
    }
    if set(value) != required:
        raise ValueError("文档字段不完整或包含未知字段")
    identity(value["document_id"])
    integer(value["version"])
    integer(value["capture_sequence"])
    integer(value["text_length"], minimum=0)
    identity(value["captured_by_source_id"], "采集来源")
    for k in ("path", "display_name", "captured_at"):
        if not isinstance(value[k], str) or not value[k] or "\0" in value[k]:
            raise ValueError("文档元信息无效")
    if any(
        not isinstance(value[k], str) or not re.fullmatch("[0-9a-f]{64}", value[k])
        for k in ("sha256", "text_sha256")
    ):
        raise ValueError("文档摘要无效")
    text = value["text"]
    if (
        not isinstance(text, str)
        or len(text.encode("utf-8")) > FILE_LIMIT
        or "\r" in text
        or "\0" in text
        or text.startswith("\ufeff")
    ):
        raise ValueError("规范化文本无效或超过2MiB")
    if value["text_length"] != len(text) or value["text_sha256"] != sha(
        text.encode("utf-8")
    ):
        raise ValueError("规范化文本长度/摘要不匹配")
    return value


class DocumentGuard:
    """Independent durable fingerprint. A failed commit cannot silently reset it.

    Callers list ONLY their document control/storage tables. Conversation state
    and 005's guard are deliberately outside this boundary. No network in hold().
    """

    def __init__(self, db, tables):
        self.db = db
        self.tables = tuple(tables)
        self.path = Path(str(db.db_path.resolve()) + ".documents-guard.json")
        self.lock = self.path.with_suffix(self.path.suffix + ".lock")

    def fingerprint(self):
        result = {}
        with self.db.connect() as c:
            c.execute("BEGIN")
            for table in self.tables:
                if not re.fullmatch("[a-z_]+", table):
                    raise ValueError("内部表名无效")
                columns = [
                    r["name"]
                    for r in c.execute("PRAGMA table_info(" + table + ")")
                    if r["name"] not in {"text", "payload"}
                ]
                if columns:
                    result[table] = [
                        tuple(row)
                        for row in c.execute(
                            "SELECT "
                            + ",".join(columns)
                            + " FROM "
                            + table
                            + " ORDER BY "
                            + ",".join(columns)
                        )
                    ]
        return digest(result)

    def initialize(self, pristine):
        with control_lock(self.lock):
            if pristine and not self.path.exists():
                atomic_json(self.path, {"format": 1, "fingerprint": self.fingerprint()})

    def status(self, *, locked=False):
        if not locked:
            with control_lock(self.lock):
                return self.status(locked=True)
        current = self.fingerprint()
        try:
            saved = json.loads(self.path.read_text(encoding="utf-8"))
            if saved.get("format") != 1 or saved.get("fingerprint") != current:
                raise ValueError()
            return None
        except (OSError, ValueError, AttributeError):
            return (
                "文档保护记录缺失、损坏或与数据库不一致；正文停止，需明确恢复/重新选择"
            )

    def state(self, *, locked=False):
        if not locked:
            with control_lock(self.lock):
                return self.state(locked=True)
        try:
            raw = self.path.read_bytes()
        except OSError:
            raw = b"<missing>"
        return digest([self.fingerprint(), sha(raw)])

    def prepare_restore(self):
        with control_lock(self.lock):
            atomic_json(
                self.path,
                {
                    "format": 1,
                    "fingerprint": digest(["restore_pending", self.state(locked=True)]),
                    "restore_pending": True,
                },
            )
        parent=self.db.db_path.resolve().parent
        snapshot=parent/'.document-snapshots'
        excluded=[str(self.path),str(self.lock)]
        if snapshot.exists():
            # Keep current expiration fences; runtime leases/locks are not data.
            excluded.extend(str(snapshot/name) for name in ('tasks','services','capacity.lock','upload-queue.lock','expired-transfers','reclamation'))
        return {
            'do_not_restore':excluded,
            'restore_files':[str(parent/name) for name in ('.documents','.document-snapshots') if (parent/name).exists()],
        }

    def checkpoint(self):
        atomic_json(self.path, {"format": 1, "fingerprint": self.fingerprint()})

    @contextmanager
    def hold(self, *, recover=False):
        with control_lock(self.lock):
            problem = self.status(locked=True)
            if problem and not recover:
                raise ValueError(problem)
            yield
            if self.status(locked=True):
                self.checkpoint()



def write_original_output(path,raw,metadata):
    """Write only a verified saved snapshot, never overwrite an existing path."""
    import os
    if not isinstance(raw,bytes) or len(raw)!=metadata.get('bytes') or sha(raw)!=metadata.get('sha256'):
        raise ValueError('原件长度或摘要与读取信息不一致')
    path=Path(path).expanduser().absolute()
    descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_BINARY',0),0o600)
    identity=os.fstat(descriptor)
    try:
        with os.fdopen(descriptor,'wb') as target:
            target.write(raw);target.flush();os.fsync(target.fileno())
    except BaseException:
        # Remove our incomplete output only; a concurrently replaced path is
        # owned by its new creator and must never be unlinked by this request.
        try:
            if os.path.samestat(identity,path.lstat()):path.unlink()
        except FileNotFoundError:pass
        raise
    return path
