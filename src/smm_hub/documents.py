"""Hub-owned document management and device publication, separate from dialogues."""

from __future__ import annotations
import json
from pathlib import Path
from uuid import uuid4
from ._archive import (
    Archive,
    Documents,
    ManagedDocuments,
    DocumentGuard,
    document_validate,
    document_identity,
    document_integer,
    digest,
    sign,
    reference_material,
    reference_decode,
    tokens,
    utcnow,
    control_lock,
)
from .projects import HubProjects


class HubDocuments:
    def __init__(self, db):
        self.db = db
        self.documents = Documents(db)
        self.library = ManagedDocuments(db)
        self.projects = HubProjects(db)
        with db.connect() as c:
            pristine = not c.execute(
                "SELECT 1 FROM sqlite_master WHERE name='hub_document_meta'"
            ).fetchone()
            c.executescript(
                """
            CREATE TABLE IF NOT EXISTS hub_document_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS hub_document_controls(
                device_id TEXT,archive_id TEXT,project_key TEXT,generation INTEGER,enabled INTEGER,
                sequence INTEGER,digest TEXT,project_id INTEGER,blocked_generation INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(device_id,archive_id,project_key));
            CREATE TABLE IF NOT EXISTS hub_document_stages(
                device_id TEXT,archive_id TEXT,document_id TEXT,version INTEGER,sha256 TEXT,text_sha256 TEXT,
                capture_sequence INTEGER,payload TEXT NOT NULL,
                PRIMARY KEY(device_id,archive_id,document_id,version));
            CREATE TABLE IF NOT EXISTS hub_document_origins(
                document_id TEXT PRIMARY KEY,device_id TEXT,archive_id TEXT,origin_document_id TEXT,
                capture_sequence INTEGER,received_at TEXT,display_name TEXT,UNIQUE(device_id,archive_id,origin_document_id));
            CREATE TABLE IF NOT EXISTS hub_document_sources(
                source_id TEXT PRIMARY KEY,device_id TEXT,archive_id TEXT,project_key TEXT,origin_source_id TEXT,
                sequence INTEGER,digest TEXT,generation INTEGER);
            CREATE TABLE IF NOT EXISTS hub_document_qualifications(
                source_id TEXT REFERENCES document_sources(id) ON DELETE CASCADE,
                document_pk INTEGER REFERENCES documents(pk) ON DELETE CASCADE,
                origin_qualification INTEGER NOT NULL,PRIMARY KEY(source_id,document_pk));
            CREATE TABLE IF NOT EXISTS hub_document_receipts(
                submission_id TEXT PRIMARY KEY,digest TEXT,response TEXT NOT NULL);
            """
            )
            c.execute(
                "INSERT OR IGNORE INTO settings(key,value) VALUES('hub_identity',?)",
                (json.dumps(uuid4().hex),),
            )
            c.execute(
                "INSERT OR IGNORE INTO hub_document_meta VALUES('epoch',?)",
                (uuid4().hex,),
            )
        self.guard = DocumentGuard(
            db,
            (
                "hub_document_meta",
                "hub_document_controls",
                "hub_document_stages",
                "hub_document_origins",
                "hub_document_sources",
                "hub_document_qualifications",
                "hub_document_receipts",
                "document_sources",
                "document_source_projects",
                "documents",
                "document_memberships",
                "document_meta",
                "document_library",
                "document_library_submissions",
            ),
        )
        self.guard.initialize(pristine)

    def context(self):
        with self.db.connect() as c:
            return {
                "hub_id": json.loads(
                    c.execute(
                        "SELECT value FROM settings WHERE key='hub_identity'"
                    ).fetchone()[0]
                ),
                "document_epoch": c.execute(
                    "SELECT value FROM hub_document_meta WHERE key='epoch'"
                ).fetchone()[0],
            }

    def _context(self, body):
        context = self.context()
        if any(body.get(k) != v for k, v in context.items()):
            raise ValueError("Hub身份或文档epoch已改变，请重新查看")

    def _own_project(self, project_id, project_key=None):
        document_integer(project_id, "项目ID")
        row = next((p for p in self.projects.list() if p["id"] == project_id), None)
        if (
            not row
            or row["source"] != "hub"
            or row["owner"] != self.context()["hub_id"]
            or (project_key is not None and row["source_key"] != project_key)
        ):
            raise ValueError("仅Hub创建的项目可在Hub管理文档")
        return row

    def _own_source(self, source_id):
        document_identity(source_id, "来源ID")
        with self.db.connect() as c:
            if c.execute(
                "SELECT 1 FROM hub_document_sources WHERE source_id=?", (source_id,)
            ).fetchone():
                raise ValueError("设备同步投影只读，请在创建端管理")
        if not any(s["id"] == source_id for s in self.documents.sources()):
            raise ValueError("文档来源不存在")

    def project_create(self, body):
        with self.guard.hold():
            self._context(body)
            name = body.get("name")
            kind = body.get("kind", "ordinary")
            if (
                set(body) - {"hub_id", "document_epoch", "name", "kind"}
                or not isinstance(name, str)
                or not name.strip()
                or kind not in {"ordinary", "global"}
            ):
                raise ValueError("项目名称/类型无效")
            owner = self.context()["hub_id"]
            with self.db.connect() as c:
                c.execute("BEGIN IMMEDIATE")
                old = (
                    c.execute(
                        "SELECT h.id FROM hub_projects h JOIN projects p ON p.id=h.id WHERE h.kind='hub' AND h.owner=? AND p.kind='global'",
                        (owner,),
                    ).fetchone()
                    if kind == "global"
                    else None
                )
                ident = (
                    old[0]
                    if old
                    else self.projects.upsert(
                        c, "hub", owner, uuid4().hex, name.strip()
                    )
                )
                c.execute("UPDATE projects SET kind=? WHERE id=?", (kind, ident))
            return next(p for p in self.projects.list() if p["id"] == ident)

    def sources(self):
        with self.db.connect() as c:
            origins = {
                r["source_id"]: dict(r)
                for r in c.execute("SELECT * FROM hub_document_sources")
            }
        result = []
        for source in self.documents.sources():
            origin = origins.get(source["id"])
            source["origin"] = (
                {
                    "kind": "device",
                    "device_id": origin["device_id"],
                    "archive_id": origin["archive_id"],
                    "source_id": origin["origin_source_id"],
                    "project_key": origin["project_key"],
                }
                if origin
                else {
                    "kind": "hub",
                    "hub_id": self.context()["hub_id"],
                    "source_id": source["id"],
                }
            )
            source["read_only"] = origin is not None
            source["message"] = (
                "同步投影只读" if origin else "Hub自有来源；仅明确refresh读取文件"
            )
            result.append(source)
        return result

    def native(self, action, body=None, source_id=None):
        body = dict(body or {})
        context = {k: body.pop(k, None) for k in ("hub_id", "document_epoch")}
        with self.guard.hold():
            self._context(context)
            if source_id is not None:
                self._own_source(source_id)
            project_id = body.pop("project_id", None)
            project_key = body.pop("project_key", None)
            if project_id is not None:
                self._own_project(project_id, project_key)
            if action in {"add", "set"}:
                ids = body.get("project_ids", [])
                if not isinstance(ids, list):
                    raise ValueError("项目名单无效")
                for ident in ids:
                    self._own_project(ident)
                return getattr(self.documents, action)(
                    *([source_id] if action == "set" else []), **body
                )
            if action == "refresh":
                if source_id is not None:
                    return self.documents.refresh(source_id)
                return {
                    "sources": [
                        self.documents.refresh(s["id"])
                        for s in self.sources()
                        if s["origin"]["kind"] == "hub"
                    ]
                }
            if action == "remove":
                return self.documents.remove(source_id)
            raise ValueError("未知来源操作")

    def managed(self, action, body, ident=None):
        body = dict(body)
        context = {k: body.pop(k, None) for k in ("hub_id", "document_epoch")}
        with self.guard.hold():
            self._context(context)
            key = body.pop("project_key", None)
            if key is None:
                raise ValueError("需要刚查看的稳定项目身份")
            self._own_project(body.get("project_id"), key)
            if ident is not None:
                current = next(
                    (d for d in self.library.list() if d["id"] == ident), None
                )
                if not current:
                    raise ValueError("此文档不是Hub创建的管理副本")
                if body["project_id"] not in current["project_ids"]:
                    raise ValueError("项目不匹配")
            try:
                return getattr(self.library, action)(
                    *([ident] if ident is not None else []), **body
                )
            except TypeError as exc:
                raise ValueError("未知或缺失的文档管理字段") from exc

    def _control_row(self, c, p, enabled=True):
        self._context(p)
        for key in ("device_id", "archive_id", "project_key"):
            document_identity(p.get(key), key)
        document_integer(p.get("generation"), "授权generation")
        row = c.execute(
            "SELECT * FROM hub_document_controls WHERE device_id=? AND archive_id=? AND project_key=?",
            (p["device_id"], p["archive_id"], p["project_key"]),
        ).fetchone()
        if (
            row is None
            or row["generation"] != p["generation"]
            or row["blocked_generation"] >= p["generation"]
            or (enabled and not row["enabled"])
        ):
            raise ValueError("项目文档授权已变化或需要重新选择")
        return row

    def control(self, p):
        self._context(p)
        for key in ("device_id", "archive_id", "project_key"):
            document_identity(p.get(key), key)
        generation = document_integer(p.get("generation"))
        sequence = document_integer(p.get("sequence"))
        if (
            type(p.get("enabled")) is not bool
            or not isinstance(p.get("project_name"), str)
            or not p["project_name"].strip()
            or not isinstance(p.get("retained"), list)
        ):
            raise ValueError("控制快照无效")
        retained = {}
        for source in p["retained"]:
            sid = document_identity(source.get("source_id"))
            revision = document_integer(source.get("revision"))
            files = source.get("files")
            if not isinstance(files, list) or sid in retained:
                raise ValueError("保留资格清单无效")
            byid = {}
            for f in files:
                ident = document_identity(f.get("document_id"))
                q = document_integer(f.get("qualification"))
                if ident in byid:
                    raise ValueError("重复资格")
                byid[ident] = q
            retained[sid] = (revision, byid)
        fingerprint = digest(p)
        with self.guard.hold(), self.db.connect() as c:
            c.execute("BEGIN IMMEDIATE")
            old = c.execute(
                "SELECT * FROM hub_document_controls WHERE device_id=? AND archive_id=? AND project_key=?",
                (p["device_id"], p["archive_id"], p["project_key"]),
            ).fetchone()
            if old:
                if (
                    generation < old["generation"]
                    or generation <= old["blocked_generation"]
                    or (
                        generation == old["generation"]
                        and (
                            sequence < old["sequence"]
                            or (
                                sequence == old["sequence"]
                                and fingerprint != old["digest"]
                            )
                        )
                    )
                ):
                    raise ValueError("旧授权/控制不能覆盖新状态")
                if generation == old["generation"] and sequence == old["sequence"]:
                    return {
                        "generation": generation,
                        "sequence": sequence,
                        "enabled": p["enabled"],
                    }
            c.execute(
                "INSERT OR IGNORE INTO hub_devices VALUES(?,?)",
                (p["device_id"], p.get("device_name", p["device_id"])),
            )
            project = self.projects.upsert(
                c, "device", p["device_id"], p["project_key"], p["project_name"]
            )
            c.execute(
                "INSERT INTO hub_document_controls VALUES(?,?,?,?,?,?,?,?,0) ON CONFLICT(device_id,archive_id,project_key) DO UPDATE SET generation=excluded.generation,enabled=excluded.enabled,sequence=excluded.sequence,digest=excluded.digest,project_id=excluded.project_id",
                (
                    p["device_id"],
                    p["archive_id"],
                    p["project_key"],
                    generation,
                    int(p["enabled"]),
                    sequence,
                    fingerprint,
                    project,
                ),
            )
            sources = c.execute(
                "SELECT h.*,s.revision FROM hub_document_sources h JOIN document_sources s ON s.id=h.source_id WHERE device_id=? AND archive_id=? AND project_key=?",
                (p["device_id"], p["archive_id"], p["project_key"]),
            ).fetchall()
            for source in sources:
                keep = retained.get(source["origin_source_id"])
                members = c.execute(
                    "SELECT m.document_pk,q.origin_qualification AS qualification,o.origin_document_id FROM document_memberships m JOIN hub_document_qualifications q ON q.source_id=m.source_id AND q.document_pk=m.document_pk JOIN documents d ON d.pk=m.document_pk JOIN hub_document_origins o ON o.document_id=d.id WHERE m.source_id=?",
                    (source["source_id"],),
                ).fetchall()
                for m in members:
                    if (
                        not keep
                        or source["revision"] != keep[0]
                        or keep[1].get(m["origin_document_id"]) != m["qualification"]
                    ):
                        c.execute(
                            "UPDATE document_memberships SET status='missing' WHERE source_id=? AND document_pk=?",
                            (source["source_id"], m["document_pk"]),
                        )
            self.documents._prune(c)
        return {"generation": generation, "sequence": sequence, "enabled": p["enabled"]}

    def stage(self, p):
        value = document_validate(p.get("document"))
        with self.guard.hold(), self.db.connect() as c:
            c.execute("BEGIN IMMEDIATE")
            self._control_row(c, p)
            args = (
                p["device_id"],
                p["archive_id"],
                value["document_id"],
                value["version"],
            )
            previous = c.execute(
                "SELECT * FROM hub_document_stages WHERE device_id=? AND archive_id=? AND document_id=? AND version=?",
                args,
            ).fetchone()
            if previous and (
                previous["sha256"] != value["sha256"]
                or previous["text_sha256"] != value["text_sha256"]
            ):
                raise ValueError("同一身份和版本不能有不同内容")
            if not previous or value["capture_sequence"] > previous["capture_sequence"]:
                c.execute(
                    "INSERT INTO hub_document_stages VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(device_id,archive_id,document_id,version) DO UPDATE SET capture_sequence=excluded.capture_sequence,payload=excluded.payload",
                    (
                        *args,
                        value["sha256"],
                        value["text_sha256"],
                        value["capture_sequence"],
                        json.dumps(value, ensure_ascii=False),
                    ),
                )
        return {
            "document_id": value["document_id"],
            "version": value["version"],
            "staged": True,
        }

    def publish(self, p):
        from ._archive import utcnow

        document_identity(p.get("source_id"))
        revision = document_integer(p.get("revision"))
        sequence = document_integer(p.get("sequence"))
        document_integer(p.get("control_sequence"))
        if (
            not isinstance(p.get("submission_id"), str)
            or not p["submission_id"]
            or not isinstance(p.get("files"), list)
        ):
            raise ValueError("发布清单无效")
        fingerprint = digest(p)
        source = digest(
            [p.get(k) for k in ("device_id", "archive_id", "project_key", "source_id")]
        )[:32]
        with self.guard.hold(), self.db.connect() as c:
            c.execute("BEGIN IMMEDIATE")
            control = self._control_row(c, p)
            if control["sequence"] != p["control_sequence"]:
                raise ValueError("发布使用了过期控制快照")
            receipt = c.execute(
                "SELECT * FROM hub_document_receipts WHERE submission_id=?",
                (p["submission_id"],),
            ).fetchone()
            if receipt:
                if receipt["digest"] != fingerprint:
                    raise ValueError("同提交不能改变载荷")
                return json.loads(receipt["response"])
            old = c.execute(
                "SELECT h.*,s.revision FROM hub_document_sources h JOIN document_sources s ON s.id=h.source_id WHERE h.source_id=?",
                (source,),
            ).fetchone()
            if old and (
                revision < old["revision"]
                or (
                    p["generation"] == old["generation"]
                    and (
                        sequence < old["sequence"]
                        or (
                            sequence == old["sequence"] and fingerprint != old["digest"]
                        )
                    )
                )
            ):
                raise ValueError("旧配置或发布不能覆盖当前来源")
            prepared = []
            seen = set()
            fields = {
                "document_id",
                "version",
                "sha256",
                "text_sha256",
                "path",
                "display_name",
                "captured_at",
                "captured_by_source_id",
                "capture_sequence",
                "relative_path",
                "qualification",
            }
            for item in p["files"]:
                if not isinstance(item, dict) or set(item) != fields:
                    raise ValueError("清单字段无效")
                ident = document_identity(item["document_id"])
                document_integer(item["qualification"])
                document_integer(item["version"])
                document_integer(item["capture_sequence"])
                if ident in seen:
                    raise ValueError("重复文件成员")
                seen.add(ident)
                staged = c.execute(
                    "SELECT payload FROM hub_document_stages WHERE device_id=? AND archive_id=? AND document_id=? AND version=?",
                    (p["device_id"], p["archive_id"], ident, item["version"]),
                ).fetchone()
                if not staged:
                    raise ValueError("完整清单含未暂存的正文")
                value = document_validate(json.loads(staged[0]))
                if (
                    any(
                        value[k] != item[k]
                        for k in ("sha256", "text_sha256", "path", "display_name")
                    )
                    or item["capture_sequence"] > value["capture_sequence"]
                    or (
                        item["capture_sequence"] == value["capture_sequence"]
                        and any(
                            value[k] != item[k]
                            for k in ("captured_at", "captured_by_source_id")
                        )
                    )
                ):
                    raise ValueError("清单与暂存内容不一致")
                if any(
                    not isinstance(item[k], str) or not item[k]
                    for k in ("relative_path", "captured_at", "captured_by_source_id")
                ):
                    raise ValueError("清单元信息无效")
                hub_ident = digest([p["device_id"], p["archive_id"], ident])[:32]
                current = c.execute(
                    "SELECT * FROM documents WHERE id=?", (hub_ident,)
                ).fetchone()
                if current and (
                    current["version"] > item["version"]
                    or (
                        current["version"] == item["version"]
                        and (
                            current["sha256"] != item["sha256"]
                            or current["text_sha256"] != item["text_sha256"]
                        )
                    )
                ):
                    raise ValueError("较旧版本/异文不得覆盖当前文件")
                prepared.append((item, value, hub_ident, current))
            # Nothing above mutates publication state. All members commit together.
            c.execute(
                "INSERT INTO document_sources(id,path,kind,recursive,exclude,revision,status,resume_status) VALUES(?,?,'device',0,'[]',?,'ready','ready') ON CONFLICT(id) DO UPDATE SET revision=excluded.revision,status='ready',resume_status='ready'",
                (source, "device:" + source, revision),
            )
            c.execute(
                "INSERT OR IGNORE INTO document_source_projects VALUES(?,?)",
                (source, control["project_id"]),
            )
            c.execute(
                "INSERT INTO hub_document_sources VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(source_id) DO UPDATE SET sequence=excluded.sequence,digest=excluded.digest,generation=excluded.generation",
                (
                    source,
                    p["device_id"],
                    p["archive_id"],
                    p["project_key"],
                    p["source_id"],
                    sequence,
                    fingerprint,
                    p["generation"],
                ),
            )
            prior_members = {
                r["document_pk"]: dict(r)
                for r in c.execute(
                    "SELECT m.*,q.origin_qualification FROM document_memberships m JOIN hub_document_qualifications q ON q.source_id=m.source_id AND q.document_pk=m.document_pk WHERE m.source_id=?",
                    (source,),
                )
            }
            c.execute(
                "UPDATE document_memberships SET status='missing' WHERE source_id=?",
                (source,),
            )
            for item, value, hub_ident, current in prepared:
                metadata = c.execute(
                    "SELECT capture_sequence FROM hub_document_origins WHERE document_id=?",
                    (hub_ident,),
                ).fetchone()
                if not current:
                    pk = c.execute(
                        "INSERT INTO documents(id,path_key,path) VALUES(?,?,?) RETURNING pk",
                        (hub_ident, "device:" + hub_ident, item["path"]),
                    ).fetchone()[0]
                else:
                    pk = current["pk"]
                if (
                    not current
                    or item["version"] > current["version"]
                    or metadata is None
                    or value["capture_sequence"] >= metadata[0]
                ):
                    c.execute(
                        "UPDATE documents SET path=?,version=?,sha256=?,text_sha256=?,text=?,text_length=?,captured_at=?,captured_by_source_id=?,publish_seq=? WHERE pk=?",
                        (
                            value["path"],
                            value["version"],
                            value["sha256"],
                            value["text_sha256"],
                            value["text"],
                            value["text_length"],
                            value["captured_at"],
                            value["captured_by_source_id"],
                            value["capture_sequence"],
                            pk,
                        ),
                    )
                    c.execute(
                        "INSERT INTO hub_document_origins VALUES(?,?,?,?,?,?,?) ON CONFLICT(document_id) DO UPDATE SET capture_sequence=excluded.capture_sequence,received_at=excluded.received_at,display_name=excluded.display_name",
                        (
                            hub_ident,
                            p["device_id"],
                            p["archive_id"],
                            item["document_id"],
                            value["capture_sequence"],
                            utcnow(),
                            value["display_name"],
                        ),
                    )
                    c.execute("DELETE FROM document_fts WHERE rowid=?", (pk,))
                    c.execute(
                        "INSERT INTO document_fts(rowid,text) VALUES(?,?)",
                        (pk, " ".join(tokens(value["text"]))),
                    )
                previous = prior_members.get(pk)
                continuous = (
                    previous
                    and previous["status"] == "ready"
                    and previous["origin_qualification"] == item["qualification"]
                    and old
                    and old["revision"] == revision
                )
                qualification = (
                    previous["qualification"]
                    if continuous
                    else (previous["qualification"] + 1 if previous else 1)
                )
                c.execute(
                    "INSERT INTO document_memberships VALUES(?,?,?,'ready',?,NULL) ON CONFLICT(source_id,document_pk) DO UPDATE SET relative_path=excluded.relative_path,status='ready',qualification=excluded.qualification,error=NULL",
                    (source, pk, item["relative_path"], qualification),
                )
                c.execute(
                    "INSERT INTO hub_document_qualifications VALUES(?,?,?) ON CONFLICT(source_id,document_pk) DO UPDATE SET origin_qualification=excluded.origin_qualification",
                    (source, pk, item["qualification"]),
                )
            self.documents._prune(c)
            response = {
                "source_id": p["source_id"],
                "revision": revision,
                "sequence": sequence,
                "generation": p["generation"],
                "published": len(prepared),
                "submission_id": p["submission_id"],
            }
            c.execute(
                "INSERT INTO hub_document_receipts VALUES(?,?,?)",
                (p["submission_id"], fingerprint, json.dumps(response)),
            )
        return response

    def _origin(self, ident):
        with self.db.connect() as c:
            row = c.execute(
                "SELECT * FROM hub_document_origins WHERE document_id=?", (ident,)
            ).fetchone()
        if row:
            return {
                "device_id": row["device_id"],
                "archive_id": row["archive_id"],
                "document_id": row["origin_document_id"],
            }, row["received_at"]
        return {
            "device_id": self.context()["hub_id"],
            "archive_id": reference_material(self.db)[0],
            "document_id": ident,
        }, None

    def search(self, body):
        self._context(body)
        with self.guard.hold():
            options = {
                k: body[k]
                for k in ("query", "scope", "project_id", "limit")
                if k in body
            }
            if body.get("scope_reference"):
                snapshot = reference_decode(self.db, body["scope_reference"])
                if (
                    snapshot.get("kind") != "query_scope"
                    or snapshot.get("hub_id") != self.context()["hub_id"]
                ):
                    raise ValueError("项目范围签名无效")
                current = {p["id"]: p for p in self.projects.list()}
                frozen = snapshot["projects"]
                if any(
                    any(
                        current.get(p["id"], {}).get(k) != p[k]
                        for k in ("source", "owner", "source_key")
                    )
                    for p in frozen
                ):
                    raise ValueError("项目范围身份已变化")
                if (
                    body.get("device_id") is not None
                    and snapshot.get("device_id") != body["device_id"]
                ):
                    raise ValueError("项目范围不属于本设备")
                options["exact_project_ids"] = [p["id"] for p in frozen]
                options.pop("project_id", None)
                options["scope"] = "all"
            result = self.documents.search(**options)
            sources = {s["id"]: s for s in self.sources()}
            archive, key = reference_material(self.db)
            for hit in result["results"]:
                with self.db.connect() as c:
                    display = c.execute(
                        "SELECT display_name FROM hub_document_origins WHERE document_id=?",
                        (hit["id"],),
                    ).fetchone()
                if display:
                    hit["display_name"] = display[0]
                origin, received = self._origin(hit["id"])
                hit["origin"] = origin
                hit["received_at"] = received
                hit["archive_scope"] = "hub"
                hit["snapshot_kind"] = "Hub采集/接收版本"
                hit["provenance"] = [
                    {
                        "source_id": sources[s]["origin"]["source_id"],
                        "project_key": sources[s]["origin"].get("project_key"),
                        "source_revision": sources[s]["revision"],
                    }
                    for s in hit["source_ids"]
                ]
                hit["reference"] = sign(
                    {
                        "format": 1,
                        "kind": "hub_document",
                        "archive_id": archive,
                        **self.context(),
                        "origin": origin,
                        "reference": hit["reference"],
                        "version": hit["version"],
                        "sha256": hit["sha256"],
                        "text_sha256": hit["text_sha256"],
                        "text_length": hit["text_length"],
                    },
                    key,
                )
            return {**result, **self.context()}

    def read(self, body):
        self._context(body)
        with self.guard.hold():
            payload = reference_decode(self.db, body.get("reference"))
            self._context(payload)
            if type(payload.get("format")) is not int:
                raise ValueError("文档引用格式无效")
            if payload.get("kind") != "hub_document":
                raise ValueError("需要Hub文档引用")
            document_integer(payload.get("version"), "引用版本")
            document_integer(payload.get("text_length"), "引用长度", minimum=0)
            value = self.documents.read(
                payload.get("reference"),
                **{k: body[k] for k in ("start", "end") if k in body},
            )
            origin, received = self._origin(value["id"])
            with self.db.connect() as c:
                display = c.execute(
                    "SELECT display_name FROM hub_document_origins WHERE document_id=?",
                    (value["id"],),
                ).fetchone()
            if display:
                value["display_name"] = display[0]
            if origin != payload.get("origin") or any(
                value.get(k) != payload.get(k)
                for k in ("version", "sha256", "text_sha256", "text_length")
            ):
                raise ValueError("引用身份或版本不匹配")
            return {
                **value,
                "origin": origin,
                "received_at": received,
                "archive_scope": "hub",
                **self.context(),
            }

    def recovery_status(self):
        with control_lock(self.guard.lock):
            with self.db.connect() as c:
                count = c.execute("SELECT COUNT(*) FROM document_sources").fetchone()[0]
                qualified = c.execute(
                    "SELECT COUNT(*) FROM document_memberships WHERE status='ready'"
                ).fetchone()[0]
            problem = self.guard.status(locked=True)
            return {
                "conflict": bool(problem),
                "reason": problem,
                "state": self.guard.state(locked=True),
                "affected_sources": count,
                "invalidated_qualifications": qualified,
                **self.context(),
            }

    def recover(self, expected_state):
        with self.guard.hold(recover=True):
            if expected_state != self.guard.state(locked=True):
                raise ValueError("恢复状态已变化，请重新查看影响")
            with self.db.connect() as c:
                c.execute("BEGIN IMMEDIATE")
                c.execute(
                    "UPDATE hub_document_meta SET value=? WHERE key='epoch'",
                    (uuid4().hex,),
                )
                c.execute(
                    "UPDATE hub_document_controls SET blocked_generation=generation,enabled=0"
                )
                ids = [
                    r[0]
                    for r in c.execute("SELECT source_id FROM hub_document_sources")
                ]
                for sid in ids:
                    c.execute("DELETE FROM document_sources WHERE id=?", (sid,))
                pks = [
                    r[0]
                    for r in c.execute(
                        "SELECT d.pk FROM documents d JOIN hub_document_origins o ON o.document_id=d.id"
                    )
                ]
                for pk in pks:
                    c.execute("DELETE FROM document_fts WHERE rowid=?", (pk,))
                    c.execute(
                        "DELETE FROM document_memberships WHERE document_pk=?", (pk,)
                    )
                    c.execute("DELETE FROM documents WHERE pk=?", (pk,))
                for table in (
                    "hub_document_sources",
                    "hub_document_origins",
                    "hub_document_stages",
                    "hub_document_receipts",
                ):
                    c.execute("DELETE FROM " + table)
                c.execute(
                    "UPDATE document_sources SET status='pending',resume_status='pending',refresh_id=NULL"
                )
                self.documents._prune(c)
        return {"recovered": True, **self.context()}
