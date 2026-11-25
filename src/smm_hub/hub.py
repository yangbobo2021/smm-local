# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SubLang International <https://sublang.ai>
"""Authenticated aggregation API backed by a separate archive."""

from __future__ import annotations

import hashlib
import heapq
import hmac
import json
from collections import defaultdict
from typing import Literal
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from ._archive import (Archive, digest, legacy_message_key, message_version, sign,
                       reference_material, reference_decode, reference_issue, reference_read, tokens, compact_message)
from .projects import HubProjects
from .upload import HubUpload
from .documents import HubDocuments
from .document_api import install as install_documents
from .vibeinsight import SOURCE as VIBEINSIGHT


class Record(BaseModel):
    source: Literal["codex", "claude-code"]
    source_session_id: str = Field(min_length=1, max_length=1024)
    started_at: str | None
    source_key: str = Field(min_length=1, max_length=1024)
    position: int = Field(ge=0)
    role: Literal["user", "assistant"]
    text: str
    timestamp: str | None
    occurrence: int | None = Field(default=None, ge=1)
    source_order: int = Field(ge=1)
    project_id: str | None = None


class Upload(BaseModel):
    hub_id: str
    device_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    device_name: str = Field(min_length=1, max_length=120)
    records: list[Record] = Field(max_length=100)
    policy_revision: int | None = Field(default=None, ge=0)
    control_epoch: str | None = None
    batch_id: str | None = Field(default=None, min_length=1, max_length=128)


class PolicyQuery(BaseModel):
    hub_id: str
    device_id: str = Field(pattern=r"^[a-f0-9]{32}$")


class PolicySet(PolicyQuery):
    expected_revision: int = Field(ge=0)
    submission_id: str = Field(min_length=1, max_length=128)
    policy: dict
    reconcile: bool = False


class Receipts(PolicyQuery):
    batch_ids: list[str] = Field(max_length=100)


class KnownMessage(BaseModel):
    conversation_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_key: str = Field(pattern=r"^[a-f0-9]{64}$")
    version: str = Field(pattern=r"^[a-f0-9]{64}$")
    project_id: str = Field(min_length=1, max_length=1024)
    position: int = Field(ge=0)
    source_order: int = Field(ge=1)


class KnownMessages(PolicyQuery):
    policy_revision: int = Field(ge=1)
    control_epoch: str
    records: list[KnownMessage] = Field(max_length=100)


class QueryScope(BaseModel):
    hub_id: str
    device_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")
    project_id: str | None = Field(default=None, min_length=1, max_length=1024)
    hub_project_id: int | None = Field(default=None, strict=True, ge=1)


class Search(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    current_session_id: str | None = None
    current_source: Literal["codex", "claude-code"] | None = None
    include_current: bool = False
    limit: int = Field(default=5, ge=1, le=50)
    preview_chars: int = 600
    device_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")
    project_id: int | str | None = None
    scope_reference: str | None = None


class DeviceProject(BaseModel):
    id: int | str
    name: str = Field(min_length=1)
    kind: Literal["ordinary", "global"] = "ordinary"


class Membership(BaseModel):
    source: Literal["codex", "claude-code"]
    source_session_id: str
    project_id: int | str | None


class ProjectMetadata(BaseModel):
    hub_id: str
    device_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    device_name: str = Field(min_length=1, max_length=120)
    projects: list[DeviceProject] = Field(max_length=100)
    memberships: list[Membership] = Field(max_length=100)
    policy_revision: int | None = Field(default=None, ge=0)
    control_epoch: str | None = None


class Read(BaseModel):
    hub_id: str
    conversation_id: int | None = None
    start: int | None = None
    end: int | None = None
    message_id: int | None = Field(default=None, ge=1)
    reference: str | None = None


def record_origin(con, message_id, device_id, position, source_order):
    # A later prefix can reveal the actual position of a previously partial copy.
    removed = con.execute('DELETE FROM hub_origins WHERE message_id=? AND device_id=? AND source_order=? AND source_position<>?',
                          (message_id, device_id, source_order, position)).rowcount
    origin = con.execute('''INSERT INTO hub_origins VALUES(?,?,?,?)
        ON CONFLICT(message_id,device_id,source_position) DO UPDATE SET source_order=excluded.source_order
        WHERE hub_origins.source_order<>excluded.source_order''', (message_id, device_id, position, source_order))
    return removed or origin.rowcount


def order_messages(con, conversation_id: int) -> None:
    """Merge the ordering constraints visible in each device's original copy."""
    rows = con.execute("""
        SELECT m.id, m.timestamp, o.device_id, o.source_order
        FROM messages m JOIN hub_origins o ON o.message_id=m.id
        WHERE m.conversation_id=? ORDER BY o.device_id,o.source_order,m.id
    """, (conversation_id,))
    keys = {}
    previous = {}
    following = defaultdict(set)
    incoming = defaultdict(int)
    for message_id, timestamp, device_id, source_order in rows:
        key = (timestamp or "", source_order, message_id)
        keys[message_id] = min(keys.get(message_id, key), key)
        if (prior := previous.get(device_id)) is not None and prior != message_id:
            if message_id not in following[prior]:
                following[prior].add(message_id)
                incoming[message_id] += 1
        previous[device_id] = message_id
    ready = [key for mid, key in keys.items() if not incoming[mid]]
    heapq.heapify(ready)
    ordered = []
    while ready:
        _, _, message_id = heapq.heappop(ready)
        ordered.append(message_id)
        for child in following[message_id]:
            incoming[child] -= 1
            if not incoming[child]:
                heapq.heappush(ready, keys[child])
    # Divergent copies may disagree on order. Keep all originals and use a
    # deterministic ordering for the unresolved remainder.
    ordered.extend(sorted(set(keys) - set(ordered), key=keys.__getitem__))
    con.executemany("UPDATE messages SET position=? WHERE id=?",
                    enumerate(ordered, 1))


def create_hub(db: Archive, token: str, *, lifespan=None) -> FastAPI:
    if not token.isascii() or len(token) < 32 or any(not 33 <= ord(char) <= 126 for char in token):
        raise ValueError("汇总服务需要至少 32 字符的连接凭证")
    projects = HubProjects(db)
    with db.connect() as con:
        con.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('hub_identity',?)",
                    (json.dumps(uuid4().hex),))
        hub_id = json.loads(con.execute("SELECT value FROM settings WHERE key='hub_identity'").fetchone()[0])
        con.execute("""CREATE TABLE IF NOT EXISTS hub_message_identities (
            message_id INTEGER PRIMARY KEY REFERENCES messages(id) ON DELETE CASCADE,
            canonical_key TEXT NOT NULL, content_version TEXT NOT NULL
        )""")
    uploads = HubUpload(db, hub_id)
    documents = HubDocuments(db)

    def authorize(authorization: str = Header(default="")) -> None:
        if not hmac.compare_digest(authorization.encode("utf-8"), ("Bearer " + token).encode("ascii")):
            raise HTTPException(401, "需要有效的汇总服务凭证")

    app = FastAPI(title="SMM Hub", docs_url=None, redoc_url=None, openapi_url=None,
                  lifespan=lifespan)
    install_documents(app,documents,token)

    def require_hub(expected: str) -> None:
        if expected != hub_id:
            raise HTTPException(409, "汇总数据库已切换，请重新搜索或同步")

    @app.get("/v1/info")
    def info():
        return {"protocol": 1, "hub_id": hub_id, "capabilities": ["projects", "upload-policy-v1", "query-scope-v1", "scope-reference-v1", "full-candidates-v1", "documents-v1", "processed_documents_v1"], "processed_documents": {"schemas":["processed_documents_v1"], "formats":["docx","xlsx","pdf"]}, **documents.context()}

    @app.post("/v1/query-scope")
    def query_scope(req: QueryScope):
        require_hub(req.hub_id)
        if req.hub_project_id is not None:
            if req.project_id is not None:raise HTTPException(400,"项目根选择器互斥")
            if not any(p['id']==req.hub_project_id for p in projects.list()):raise HTTPException(400,"Hub项目不存在")
            effective = projects._list_for_ids(tuple(db.effective_projects(req.hub_project_id)))
        else:
            if req.device_id is None or req.project_id is None:raise HTTPException(400,"需要明确项目根")
            effective = projects.effective(req.device_id, req.project_id)
        if not effective:
            raise HTTPException(409, "当前项目尚未登记，请重试最小项目登记")
        identity, key = reference_material(db)
        payload = {"format": 1, "kind": "query_scope", "archive_id": identity,
                   "hub_id": hub_id, "device_id": req.device_id, "project_key": req.project_id,
                   "projects": effective, "hub_project_id": req.hub_project_id}
        return {"hub_id": hub_id, "effective_projects": effective, "scope_reference": sign(payload, key)}

    @app.post("/v1/upload-policy/status")
    def policy_status(req: PolicyQuery):
        require_hub(req.hub_id)
        return uploads.status(req.device_id)

    @app.post("/v1/upload-policy/register")
    def register_policy(req: PolicyQuery):
        require_hub(req.hub_id)
        return uploads.register(req.device_id)

    @app.post("/v1/upload-policy/set")
    def policy_set(req: PolicySet):
        require_hub(req.hub_id)
        try:
            return uploads.set(req.device_id, req.policy, req.expected_revision, req.submission_id,
                               reconcile=req.reconcile)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.post("/v1/upload-receipts")
    def upload_receipts(req: Receipts):
        require_hub(req.hub_id)
        from ._archive import control_lock
        with control_lock(uploads.guard.lock):
            guard = uploads._guard()
            with db.connect() as con:
                state = uploads._status(con, guard, req.device_id)
                receipts = []
                for batch_id in req.batch_ids:
                    row = con.execute("SELECT * FROM hub_upload_batches WHERE device_id=? AND batch_id=?",
                                      (req.device_id, batch_id)).fetchone()
                    if row:
                        receipts.append({"hub_id": hub_id, "device_id": req.device_id,
                                         "batch_id": batch_id, "accepted": row["accepted"],
                                         "control_epoch": row["control_epoch"], "batch_digest": row["digest"]})
                return {**state, "receipts": receipts}

    @app.post("/v1/known-upload-messages")
    def known_upload_messages(req: KnownMessages):
        require_hub(req.hub_id)
        from ._archive import control_lock, permits
        with control_lock(uploads.guard.lock):
            guard = uploads._guard()
            with db.connect() as con:
                con.execute("BEGIN IMMEDIATE")
                policy = uploads._check(con, guard, req.device_id, req.policy_revision, req.control_epoch)
                if policy is None:
                    raise HTTPException(409, "请先确认上传规则")
                con.execute("CREATE TABLE IF NOT EXISTS hub_conversation_fingerprints(conversation_id INTEGER PRIMARY KEY REFERENCES conversations(id) ON DELETE CASCADE,digest TEXT NOT NULL UNIQUE)")
                missing = con.execute("SELECT id,source,source_session_id FROM conversations WHERE source IN ('codex','claude-code') AND id NOT IN (SELECT conversation_id FROM hub_conversation_fingerprints) LIMIT 25000").fetchall()
                con.executemany("INSERT OR IGNORE INTO hub_conversation_fingerprints VALUES(?,?)", [(r["id"], digest([r["source"], r["source_session_id"]])) for r in missing])
                known = []
                changed = set()
                for record in req.records:
                    if not permits(policy, record.project_id):
                        raise HTTPException(403, "该项目不允许上传")
                    project = con.execute("SELECT id FROM hub_projects WHERE kind='device' AND owner=? AND source_key=?", (req.device_id, record.project_id)).fetchone()
                    if project is None:
                        raise HTTPException(409, "需先登记项目")
                    row = con.execute("SELECT m.*,c.source,c.source_session_id FROM hub_conversation_fingerprints f JOIN conversations c ON c.id=f.conversation_id JOIN messages m ON m.conversation_id=c.id WHERE f.digest=? AND m.source_key IN (?,?) AND (SELECT COUNT(*) FROM hub_message_identities i WHERE i.message_id=m.id AND i.canonical_key<>?)=0 ORDER BY m.id", (record.conversation_digest, record.source_key, 'v1:' + record.source_key + ':' + record.version, record.source_key)).fetchall()
                    row = next((r for r in row if message_version(dict(r)) == record.version), None)
                    if row is None or message_version(dict(row)) != record.version:
                        continue
                    record_origin(con, row['id'], req.device_id, record.position, record.source_order)
                    con.execute("INSERT OR IGNORE INTO hub_message_projects VALUES(?,?,?)", (row["id"], req.device_id, project[0]))
                    con.execute("INSERT OR IGNORE INTO hub_project_memberships VALUES(?,'device',?,?)", (row["conversation_id"], req.device_id, project[0]))
                    changed.add(row["conversation_id"])
                    known.append({"logical_id": digest([row["source"], row["source_session_id"], record.source_key]), "version": record.version})
                for conversation in changed:
                    order_messages(con, conversation)
                    projects.reindex(con, conversation)
                return {"hub_id": hub_id, "device_id": req.device_id, "control_epoch": guard["control_epoch"], "known": known}

    @app.post("/v1/upload")
    def upload(batch: Upload):
        require_hub(batch.hub_id)
        changed = set()
        with uploads.transaction(batch) as con:
            con.execute("""
                INSERT INTO hub_devices(id,name) VALUES(?,?)
                ON CONFLICT(id) DO UPDATE SET name=excluded.name
            """, (batch.device_id, batch.device_name))
            for record in batch.records:
                con.execute("""
                    INSERT INTO conversations(source,source_session_id,source_path,started_at,updated_at)
                    VALUES(?,?,?,?,?)
                    ON CONFLICT(source,source_session_id) DO UPDATE SET
                    updated_at=CASE WHEN excluded.updated_at > conversations.updated_at
                                    THEN excluded.updated_at
                                    ELSE COALESCE(conversations.updated_at,excluded.updated_at) END
                """, (record.source, record.source_session_id, "", record.started_at, record.timestamp))
                conversation_id = con.execute(
                    "SELECT id FROM conversations WHERE source=? AND source_session_id=?",
                    (record.source, record.source_session_id),
                ).fetchone()[0]
                key = legacy_message_key(record.model_dump())
                version = message_version(record.model_dump())
                existing = con.execute("SELECT * FROM messages WHERE conversation_id=? AND source_key=?",
                                       (conversation_id, key)).fetchone()
                storage_key = key
                if existing is not None and message_version(dict(existing)) != version:
                    storage_key = 'v1:' + key + ':' + version
                row = con.execute("""
                    INSERT INTO messages(conversation_id,source_key,position,role,text,timestamp)
                    VALUES(?,?,?,?,?,?) ON CONFLICT(conversation_id,source_key) DO NOTHING
                    RETURNING id
                """, (conversation_id, storage_key, record.source_order, record.role, record.text, record.timestamp)).fetchone()
                if row is not None:
                    changed.add(conversation_id)
                else:
                    row = con.execute("SELECT id FROM messages WHERE conversation_id=? AND source_key=?",
                                      (conversation_id, storage_key)).fetchone()
                stored = con.execute("SELECT role,text,timestamp FROM messages WHERE id=?", (row[0],)).fetchone()
                if message_version(dict(stored)) != version:
                    raise HTTPException(409, "消息版本冲突，未确认该批次")
                con.execute("INSERT OR IGNORE INTO hub_message_identities VALUES(?,?,?)", (row[0], key, version))
                if record_origin(con, row[0], batch.device_id, record.position, record.source_order):
                    changed.add(conversation_id)
                if record.project_id is not None:
                    project = con.execute("SELECT id FROM hub_projects WHERE kind='device' AND owner=? AND source_key=?",
                                          (batch.device_id, record.project_id)).fetchone()
                    if project is None:
                        raise HTTPException(409, "设备需先登记项目")
                    con.execute("INSERT OR IGNORE INTO hub_message_projects(message_id,device_id,project_id) VALUES(?,?,?)",
                                (row[0], batch.device_id, project[0]))
                    con.execute("INSERT OR IGNORE INTO hub_project_memberships VALUES(?,'device',?,?)",
                                (conversation_id, batch.device_id, project[0]))
                    changed.add(conversation_id)
            for conversation_id in changed:
                order_messages(con, conversation_id)
                db._reindex(con, conversation_id)
                projects.reindex(con, conversation_id)
        return {"accepted": len(batch.records), "hub_id": hub_id, "device_id": batch.device_id,
                "policy_revision": batch.policy_revision, "control_epoch": batch.control_epoch,
                "batch_id": batch.batch_id, "batch_digest": digest([r.model_dump() for r in batch.records])}

    @app.post("/v1/project-metadata")
    def project_metadata(batch: ProjectMetadata):
        require_hub(batch.hub_id)
        with uploads.transaction(batch, metadata=True) as con:
            con.execute("""
                INSERT INTO hub_devices(id,name) VALUES(?,?)
                ON CONFLICT(id) DO UPDATE SET name=excluded.name
            """, (batch.device_id, batch.device_name))
            for project in batch.projects:
                project_id = projects.upsert(con, "device", batch.device_id, str(project.id), project.name)
                con.execute("UPDATE projects SET kind=? WHERE id=?", (project.kind, project_id))
            for item in batch.memberships:
                row = con.execute("""
                    SELECT c.id FROM conversations c WHERE c.source=? AND c.source_session_id=?
                    AND EXISTS (
                        SELECT 1 FROM messages m JOIN hub_origins o ON o.message_id=m.id
                        WHERE m.conversation_id=c.id AND o.device_id=?
                    )
                """, (item.source, item.source_session_id, batch.device_id)).fetchone()
                if row is None:
                    raise HTTPException(409, "设备需先上传会话")
                project_id = None
                if item.project_id is not None:
                    project = con.execute("""
                        SELECT id FROM hub_projects WHERE kind='device' AND owner=? AND source_key=?
                    """, (batch.device_id, str(item.project_id))).fetchone()
                    if project is None:
                        raise HTTPException(409, "设备需先上传项目")
                    project_id = project[0]
                projects.assign(con, row[0], "device", batch.device_id, project_id)
                projects.reindex(con, row[0])
        return {"projects": len(batch.projects), "memberships": len(batch.memberships)}

    def add_projects(conversation: dict, within: tuple[int, ...] | None = None,
                     messages: tuple[int, ...] | None = None) -> None:
        assigned = projects.memberships(conversation["id"], within, messages)
        conversation["projects"] = assigned
        if assigned:
            conversation["project_id"] = assigned[0]["id"]
            conversation["project_name"] = assigned[0]["name"]

    def add_origins(conversation: dict, message_field: str, within: tuple[int, ...] | None = None) -> dict:
        original_session = conversation["source_session_id"]
        conversation["origin_session_key"] = digest([conversation["source"], original_session]) if conversation["source"] == VIBEINSIGHT else original_session
        conversation["identity_namespace"] = "vibeinsight" if conversation["source"] == VIBEINSIGHT else "agent"
        with db.connect() as con:
            for message in conversation[message_field]:
                if "source_key" in message:
                    identity = con.execute("SELECT canonical_key FROM hub_message_identities WHERE message_id=?",
                                           (message["_message_id"],)).fetchone()
                    canonical_key = identity[0] if identity else message["source_key"]
                    message.pop("source_key")
                    message["canonical_id"] = digest([conversation["source"], original_session, canonical_key])
                    message["content_version"] = message_version(message)
        if conversation["source"] == VIBEINSIGHT:
            source_id, _, platform, original_session = json.loads(conversation["source_session_id"])
            conversation["source_session_id"] = original_session
            origin = {"source": VIBEINSIGHT, "source_id": source_id, "platform": platform}
            with db.connect() as con:
                for message in conversation[message_field]:
                    message_id = message.pop("_message_id")
                    event = con.execute("""
                        SELECT v.event_id,v.project_id,p.name FROM hub_vibeinsight_messages v
                        JOIN projects p ON p.id=v.project_id WHERE v.id=?
                    """, (message_id,)).fetchone()
                    message["hub_message_id"] = message_id
                    message["origins"] = [{**origin, "source_position": message["position"],
                                           "source_event_id": event[0], "project_id": event[1],
                                           "project_name": event[2]}]
            conversation["origins"] = [origin]
            return conversation
        devices = {}
        with db.connect() as con:
            for message in conversation[message_field]:
                message_id = message.pop("_message_id")
                message["hub_message_id"] = message_id
                origins = [dict(row) for row in con.execute("""
                    SELECT d.id AS device_id, d.name AS device_name,o.source_position,o.source_order,
                           pm.project_id,p.name AS project_name
                    FROM hub_origins o JOIN hub_devices d ON d.id=o.device_id
                    LEFT JOIN hub_message_projects mp ON mp.message_id=o.message_id AND mp.device_id=o.device_id
                    LEFT JOIN hub_project_memberships pm ON pm.kind='device' AND pm.owner=d.id
                        AND pm.conversation_id=? AND (mp.project_id IS NULL OR pm.project_id=mp.project_id)
                    LEFT JOIN projects p ON p.id=pm.project_id
                    WHERE o.message_id=? ORDER BY d.name,d.id,o.source_position
                """, (conversation["id"], message_id))]
                if within is not None:
                    origins = [origin for origin in origins if origin["project_id"] in within]
                message["origins"] = origins
                message["source_order"] = min((origin["source_order"] for origin in origins), default=message["position"])
                for origin in origins:
                    devices[origin["device_id"]] = {
                        "device_id": origin["device_id"], "device_name": origin["device_name"]
                    }
        conversation["origins"] = list(devices.values())
        return conversation

    @app.post("/v1/search")
    def search(req: Search):
        try:
            if req.preview_chars != 0 and not 100 <= req.preview_chars <= 2000:
                raise ValueError("preview_chars 必须为 0 或 100 到 2000")
            effective = None
            ids = None
            if req.scope_reference is not None:
                snapshot = reference_decode(db, req.scope_reference)
                if snapshot.get("kind") != "query_scope" or snapshot.get("hub_id") != hub_id:
                    raise ValueError("项目范围快照无效")
                effective = snapshot["projects"]
                ids = tuple(p["id"] for p in effective)
                current = {p["id"]: p for p in projects.list()}
                for project in effective:
                    if any(current.get(project["id"], {}).get(k) != project[k] for k in ("source", "owner", "source_key")):
                        raise ValueError("项目身份已改变，请重新检索")
                if req.device_id is not None and req.device_id != snapshot["device_id"]:
                    raise ValueError("项目范围与设备不匹配")
            elif req.project_id is not None:
                if req.device_id is None:
                    raise ValueError("项目检索需要设备标识")
                effective = projects.effective(req.device_id, str(req.project_id))
                ids = tuple(project["id"] for project in effective)
            result = db.search(**req.model_dump(exclude={"project_id", "device_id", "scope_reference", "preview_chars"}),
                               preview_chars=0, include_message_ids=True, hub_project_ids=ids)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        if effective is not None:
            result.update(scope="project", effective_projects=effective)
        usable, failures = [], []
        for hit in result["results"]:
            try:
                matched = hit["matched_messages"]
                anchors = tuple(item["_message_id"] for item in matched if item.pop("_query_match", False))
                add_projects(hit, ids, anchors or tuple(item["_message_id"] for item in matched))
                hit["reference"] = reference_issue(db, hit["id"], matched, scope="hub", hub_id=hub_id,
                                                    project_ids=list(ids) if ids is not None else None)
                add_origins(hit, "matched_messages", ids)
                hit["archive_scope"] = "hub"
                if req.preview_chars:
                    hit["matched_messages"] = [compact_message(m, list(dict.fromkeys(tokens(req.query))), req.preview_chars) for m in matched]
                usable.append(hit)
            except (ValueError, TypeError):
                failures.append("Hub 候选在定位完整原文时改变，已排除且不扩大召回")
        return {**result, "results": usable, "candidate_failures": failures, "hub_id": hub_id}

    @app.post("/v1/read")
    def read(req: Read):
        require_hub(req.hub_id)
        try:
            if req.reference is not None:
                payload = reference_decode(db, req.reference)
                if payload.get("hub_id") != hub_id:
                    raise ValueError("原文引用属于其他 Hub")
                if req.conversation_id is not None and req.conversation_id != payload.get("conversation_id"):
                    raise ValueError("reference 与会话定位参数冲突")
                if req.message_id is not None and req.message_id not in {m["id"] for m in payload.get("messages", [])}:
                    raise ValueError("reference 与消息定位参数冲突")
                result = reference_read(db, req.reference, start=req.start, end=req.end)
            else:
                if req.conversation_id is None:
                    raise ValueError("请提供原文引用或会话 ID")
                result = db.read(req.conversation_id, start=req.start, end=req.end,
                                 include_message_ids=True, message_id=req.message_id)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc
        # A single-message citation carries the actual project of that message
        # even when the conversation has been seen in several projects.
        within = tuple(payload["project_ids"]) if req.reference and payload.get("project_ids") is not None else None
        add_projects(result, within, messages=tuple(m["_message_id"] for m in result["messages"]) if req.reference else (req.message_id,) if req.message_id is not None else None)
        return add_origins(result, "messages", within)

    return app
