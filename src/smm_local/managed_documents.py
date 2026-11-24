"""Creator-owned managed raw copies and atomic captured text publication.

No networking. External directory sources retain their existing refresh behavior.
Managed uploads write only hidden, UUID-separated files owned by this archive.
"""

from __future__ import annotations
import base64
import json
import os
from pathlib import Path
import re
import tempfile
from uuid import uuid4
from .core import tokens, utcnow
from .documents import Documents, _link
from .document_protocol import normalize, sha, integer
from .archive_protocol import digest, control_lock


def display_name(name):
    if (
        not isinstance(name, str)
        or not name
        or len(name) > 240
        or any(ord(c) < 32 for c in name)
        or any(c in name for c in "/\\:")
        or name in {".", ".."}
        or name.endswith((" ", "."))
    ):
        raise ValueError("文件名称必须是安全的单个显示名称")
    if name.split(".")[0].upper() in {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *[f"COM{i}" for i in range(1, 10)],
        *[f"LPT{i}" for i in range(1, 10)],
    }:
        raise ValueError("文件名不能是系统保留名")
    if Path(name).suffix.lower() not in {".md", ".markdown", ".txt"}:
        raise ValueError("首版只支持 .md/.markdown/.txt")
    return name


def content(value):
    if not isinstance(value, str) or len(value) > 3 * 1024 * 1024:
        raise ValueError("上传数据无效或超过2MiB")
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, UnicodeError) as exc:
        raise ValueError("上传内容不是有效base64") from exc
    return raw, normalize(raw)


class ManagedDocuments:
    def __init__(self, db):
        self.db = db
        self.documents = Documents(db)
        self.root = db.db_path.resolve().parent / ".documents"
        self.lock = self.root.with_name(".documents-library.lock")
        with db.connect() as c:
            c.executescript(
                """
            CREATE TABLE IF NOT EXISTS document_library(
                document_id TEXT PRIMARY KEY,source_id TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,created_project INTEGER NOT NULL,removed INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS document_library_submissions(
                submission_id TEXT PRIMARY KEY,digest TEXT NOT NULL,document_id TEXT NOT NULL,response TEXT NOT NULL);
            CREATE TRIGGER IF NOT EXISTS document_library_removed AFTER DELETE ON document_sources
            BEGIN UPDATE document_library SET removed=1 WHERE source_id=old.id; END;
            """
            )

    def _root(self):
        if self.root.exists() or self.root.is_symlink():
            if _link(self.root) or not self.root.is_dir():
                raise ValueError("管理副本存储根不能是链接或junction")
        else:
            self.root.mkdir(mode=0o700)
        if any(_link(p) for p in self.root.parents):
            raise ValueError("管理副本存储路径不能经过链接或junction")

    @staticmethod
    def _submission(value):
        if not isinstance(value, str) or not value or len(value) > 200:
            raise ValueError("需要有效submission_id")
        return value

    def _receipt(self, c, ident):
        row = c.execute(
            "SELECT l.*,d.path,d.version,d.sha256,d.text_sha256,d.text_length,s.revision AS source_revision FROM document_library l JOIN documents d ON d.id=l.document_id LEFT JOIN document_sources s ON s.id=l.source_id WHERE l.document_id=?",
            (ident,),
        ).fetchone()
        if row is None or row["removed"] or row["source_revision"] is None:
            raise ValueError("管理文档不存在或已移除")
        result = {
            k: row[k]
            for k in (
                "path",
                "version",
                "sha256",
                "text_sha256",
                "text_length",
                "source_revision",
                "source_id",
                "display_name",
            )
        }
        result["id"] = ident
        result["project_ids"] = [
            r[0]
            for r in c.execute(
                "SELECT project_id FROM document_source_projects WHERE source_id=? ORDER BY project_id",
                (row["source_id"],),
            )
        ]
        return result

    def list(self, project_id=None):
        with self.db.connect() as c:
            c.execute("BEGIN")
            if project_id is not None:
                self.documents._projects(c, [project_id])
            ids = [
                r[0]
                for r in c.execute(
                    "SELECT document_id FROM document_library WHERE removed=0 ORDER BY rowid"
                )
            ]
            rows = [self._receipt(c, ident) for ident in ids]
            return [
                r for r in rows if project_id is None or project_id in r["project_ids"]
            ]

    def _retry(self, c, submission, fingerprint):
        old = c.execute(
            "SELECT * FROM document_library_submissions WHERE submission_id=?",
            (submission,),
        ).fetchone()
        if not old:
            return None
        if old["digest"] != fingerprint:
            raise ValueError("submission_id已用于不同的目标或字节")
        self._receipt(c, old["document_id"])  # Removed submissions never enroll again.
        return json.loads(old["response"])

    def _publish(self, c, ident, source, path, raw, text):
        seq = c.execute(
            "UPDATE document_meta SET value=value+1 WHERE key='request_seq' RETURNING value"
        ).fetchone()[0]
        row = c.execute("SELECT * FROM documents WHERE id=?", (ident,)).fetchone()
        now = utcnow()
        raw_sha = sha(raw)
        version = (row["version"] if row else 0) + int(
            row is None or row["sha256"] != raw_sha
        )
        if row is None:
            pk = c.execute(
                "INSERT INTO documents(id,path_key,path) VALUES(?,?,?) RETURNING pk",
                (ident, os.path.normcase(str(path)), str(path)),
            ).fetchone()[0]
        else:
            pk = row["pk"]
        c.execute(
            "UPDATE documents SET version=?,sha256=?,text_sha256=?,text=?,text_length=?,captured_at=?,captured_by_source_id=?,publish_seq=? WHERE pk=?",
            (
                version,
                raw_sha,
                sha(text.encode("utf-8")),
                text,
                len(text),
                now,
                source,
                seq,
                pk,
            ),
        )
        member = c.execute(
            "SELECT status,qualification FROM document_memberships WHERE source_id=? AND document_pk=?",
            (source, pk),
        ).fetchone()
        qual = (
            1
            if member is None
            else member["qualification"] + int(member["status"] != "ready")
        )
        c.execute(
            "INSERT INTO document_memberships VALUES(?,?,?,'ready',?,NULL) ON CONFLICT(source_id,document_pk) DO UPDATE SET status='ready',qualification=excluded.qualification,error=NULL",
            (source, pk, path.name, qual),
        )
        c.execute("DELETE FROM document_fts WHERE rowid=?", (pk,))
        c.execute(
            "INSERT INTO document_fts(rowid,text) VALUES(?,?)",
            (pk, " ".join(tokens(text))),
        )
        counts = {
            "ready": 1,
            "failed": 0,
            "candidates": 1,
            "billed_bytes": len(raw),
            "ignored_entries": 0,
        }
        c.execute(
            "UPDATE document_sources SET status='ready',resume_status='ready',request_seq=?,refresh_id=NULL,finished_at=?,error=NULL,counts=? WHERE id=?",
            (seq, now, json.dumps(counts), source),
        )

    @staticmethod
    def _replace(path, raw):
        fd, tmp = tempfile.mkstemp(prefix=".upload-", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp, path)
        finally:
            Path(tmp).unlink(missing_ok=True)

    @staticmethod
    def _project_key(c, project_id, project_key):
        if project_key is None:
            return
        row = c.execute(
            "SELECT remote_key FROM hub_local_project_keys WHERE id=?", (project_id,)
        ).fetchone()
        if row is None or row[0] != project_key:
            raise ValueError("本机项目身份已变化，请重新查看项目")

    def create(
        self, *, project_id, name, content_base64, submission_id, project_key=None
    ):
        name = display_name(name)
        raw, text = content(content_base64)
        submission = self._submission(submission_id)
        integer(project_id, "项目ID")
        fingerprint = digest(["create", project_id, name, sha(raw)])
        with control_lock(self.lock), self.db.connect() as c:
            c.execute("BEGIN IMMEDIATE")
            self.documents._projects(c, [project_id])
            self._project_key(c, project_id, project_key)
            if (retry := self._retry(c, submission, fingerprint)) is not None:
                return retry
            self._root()
            ident = uuid4().hex
            source = uuid4().hex
            directory = self.root / uuid4().hex
            directory.mkdir(mode=0o700)
            path = directory / ("file" + Path(name).suffix.lower())
            try:
                self._replace(path, raw)
                c.execute(
                    "INSERT INTO document_sources(id,path,kind,recursive,exclude) VALUES(?,?,'file',1,'[]')",
                    (source, str(path)),
                )
                c.execute(
                    "INSERT INTO document_source_projects VALUES(?,?)",
                    (source, project_id),
                )
                c.execute(
                    "INSERT INTO document_library(document_id,source_id,display_name,created_project) VALUES(?,?,?,?)",
                    (ident, source, name, project_id),
                )
                self._publish(c, ident, source, path, raw, text)
                receipt = self._receipt(c, ident)
                c.execute(
                    "INSERT INTO document_library_submissions VALUES(?,?,?,?)",
                    (
                        submission,
                        fingerprint,
                        ident,
                        json.dumps(receipt, ensure_ascii=False),
                    ),
                )
                c.commit()
                return receipt
            except BaseException:
                path.unlink(missing_ok=True)
                directory.rmdir()
                raise

    def update(
        self,
        ident,
        *,
        project_id,
        expected_version,
        expected_revision,
        content_base64,
        submission_id,
        project_key=None,
    ):
        raw, text = content(content_base64)
        submission = self._submission(submission_id)
        fingerprint = digest(
            ["update", ident, project_id, expected_version, expected_revision, sha(raw)]
        )
        with control_lock(self.lock), self.db.connect() as c:
            c.execute("BEGIN IMMEDIATE")
            self.documents._projects(c, [project_id])
            self._project_key(c, project_id, project_key)
            if (retry := self._retry(c, submission, fingerprint)) is not None:
                return retry
            current = self._receipt(c, ident)
            self._check(current, project_id, expected_version, expected_revision)
            self._root()
            path = Path(current["path"])
            if _link(path) or any(_link(p) for p in path.parents):
                raise ValueError("管理副本路径已变为链接")
            old = path.read_bytes()
            try:
                self._replace(path, raw)
                self._publish(c, ident, current["source_id"], path, raw, text)
                receipt = self._receipt(c, ident)
                c.execute(
                    "INSERT INTO document_library_submissions VALUES(?,?,?,?)",
                    (
                        submission,
                        fingerprint,
                        ident,
                        json.dumps(receipt, ensure_ascii=False),
                    ),
                )
                c.commit()
                return receipt
            except BaseException:
                self._replace(path, old)
                raise

    @staticmethod
    def _check(current, project_id, version, revision):
        integer(project_id, "项目ID")
        integer(version, "文档版本")
        integer(revision, "来源版本")
        if (
            project_id not in current["project_ids"]
            or current["version"] != version
            or current["source_revision"] != revision
        ):
            raise ValueError("项目或版本已变化，请重新查看后提交")

    def remove(
        self,
        ident,
        *,
        project_id,
        expected_version,
        expected_revision,
        submission_id=None,
        project_key=None,
    ):
        with control_lock(self.lock), self.db.connect() as c:
            c.execute("BEGIN IMMEDIATE")
            self._project_key(c, project_id, project_key)
            current = self._receipt(c, ident)
            self._check(current, project_id, expected_version, expected_revision)
            c.execute(
                "DELETE FROM document_sources WHERE id=?", (current["source_id"],)
            )
            self.documents._prune(c)
            return {
                "removed": ident,
                "message": "已撤回文档资格，副本保留，不会因重放上传而恢复",
            }
