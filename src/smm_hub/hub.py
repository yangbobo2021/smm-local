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

from ._archive import Archive


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


class Upload(BaseModel):
    hub_id: str
    device_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    device_name: str = Field(min_length=1, max_length=120)
    records: list[Record] = Field(max_length=100)


class Search(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    current_session_id: str | None = None
    current_source: Literal["codex", "claude-code"] | None = None
    include_current: bool = False
    limit: int = Field(default=5, ge=1, le=50)
    preview_chars: int = 600


class Read(BaseModel):
    hub_id: str
    conversation_id: int
    start: int | None = None
    end: int | None = None
    message_id: int | None = Field(default=None, ge=1)


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


def create_hub(db: Archive, token: str) -> FastAPI:
    if not token.isascii() or len(token) < 32 or any(not 33 <= ord(char) <= 126 for char in token):
        raise ValueError("汇总服务需要至少 32 字符的连接凭证")
    with db.connect() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS hub_devices (id TEXT PRIMARY KEY, name TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS hub_origins (
                message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
                device_id TEXT NOT NULL REFERENCES hub_devices(id),
                source_position INTEGER NOT NULL,
                source_order INTEGER NOT NULL,
                PRIMARY KEY (message_id, device_id, source_position)
            );
        """)
        con.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('hub_identity',?)",
                    (json.dumps(uuid4().hex),))
        hub_id = json.loads(con.execute("SELECT value FROM settings WHERE key='hub_identity'").fetchone()[0])

    def authorize(authorization: str = Header(default="")) -> None:
        if not hmac.compare_digest(authorization.encode("utf-8"), ("Bearer " + token).encode("ascii")):
            raise HTTPException(401, "需要有效的汇总服务凭证")

    app = FastAPI(title="SMM Hub", docs_url=None, redoc_url=None, openapi_url=None,
                  dependencies=[Depends(authorize)])

    def require_hub(expected: str) -> None:
        if expected != hub_id:
            raise HTTPException(409, "汇总数据库已切换，请重新搜索或同步")

    @app.get("/v1/info")
    def info():
        return {"protocol": 1, "hub_id": hub_id}

    @app.post("/v1/upload")
    def upload(batch: Upload):
        require_hub(batch.hub_id)
        changed = set()
        with db.connect() as con:
            con.execute("BEGIN IMMEDIATE")
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
                identity = (["offset", record.timestamp, record.occurrence]
                            if record.occurrence is not None else ["id", record.source_key])
                key = hashlib.sha256(json.dumps([identity, record.role, record.text],
                                               ensure_ascii=False).encode("utf-8")).hexdigest()
                row = con.execute("""
                    INSERT INTO messages(conversation_id,source_key,position,role,text,timestamp)
                    VALUES(?,?,?,?,?,?) ON CONFLICT(conversation_id,source_key) DO NOTHING
                    RETURNING id
                """, (conversation_id, key, record.source_order, record.role, record.text, record.timestamp)).fetchone()
                if row is not None:
                    changed.add(conversation_id)
                else:
                    row = con.execute("SELECT id FROM messages WHERE conversation_id=? AND source_key=?",
                                      (conversation_id, key)).fetchone()
                origin = con.execute("""
                    INSERT INTO hub_origins(message_id,device_id,source_position,source_order)
                    VALUES(?,?,?,?) ON CONFLICT(message_id,device_id,source_position)
                    DO UPDATE SET source_order=excluded.source_order
                    WHERE hub_origins.source_order<>excluded.source_order
                """, (row[0], batch.device_id, record.position, record.source_order))
                if origin.rowcount:
                    changed.add(conversation_id)
            for conversation_id in changed:
                order_messages(con, conversation_id)
                db._reindex(con, conversation_id)
        return {"accepted": len(batch.records)}

    def add_origins(conversation: dict, message_field: str) -> dict:
        devices = {}
        with db.connect() as con:
            for message in conversation[message_field]:
                message_id = message.pop("_message_id")
                message["hub_message_id"] = message_id
                origins = [dict(row) for row in con.execute("""
                    SELECT d.id AS device_id, d.name AS device_name, o.source_position
                    FROM hub_origins o JOIN hub_devices d ON d.id=o.device_id
                    WHERE o.message_id=? ORDER BY d.name,d.id,o.source_position
                """, (message_id,))]
                message["origins"] = origins
                for origin in origins:
                    devices[origin["device_id"]] = {
                        "device_id": origin["device_id"], "device_name": origin["device_name"]
                    }
        conversation["origins"] = list(devices.values())
        return conversation

    @app.post("/v1/search")
    def search(req: Search):
        try:
            result = db.search(**req.model_dump(), include_message_ids=True)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        for hit in result["results"]:
            add_origins(hit, "matched_messages")
        return {**result, "hub_id": hub_id}

    @app.post("/v1/read")
    def read(req: Read):
        require_hub(req.hub_id)
        try:
            result = db.read(req.conversation_id, start=req.start, end=req.end,
                             include_message_ids=True, message_id=req.message_id)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc
        return add_origins(result, "messages")

    return app
