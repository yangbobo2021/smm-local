# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SubLang International <https://sublang.ai>
"""Persistent state and atomic archive commits for Python source plugins."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from . import plugin


def _now():
    return datetime.now(timezone.utc).isoformat()


SCHEMA = """
CREATE TABLE IF NOT EXISTS plugin_sources (
    id TEXT PRIMARY KEY,
    enabled INTEGER NOT NULL,
    live_version INTEGER NOT NULL,
    previous_version INTEGER,
    generation INTEGER NOT NULL DEFAULT 0,
    cursor TEXT
);
CREATE TABLE IF NOT EXISTS plugin_versions (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL REFERENCES plugin_sources(id),
    config TEXT NOT NULL,
    code BLOB NOT NULL
);
CREATE TABLE IF NOT EXISTS plugin_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL REFERENCES plugin_sources(id),
    version INTEGER NOT NULL REFERENCES plugin_versions(id),
    imported_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS plugin_messages (
    id INTEGER PRIMARY KEY REFERENCES messages(id) ON DELETE CASCADE,
    batch INTEGER NOT NULL REFERENCES plugin_batches(id),
    origin TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS plugin_messages_batch ON plugin_messages(batch);
"""


def _active(con, source):
    return con.execute("""
        SELECT s.*, v.config, v.code FROM plugin_sources s
        JOIN plugin_versions v ON v.id=s.live_version WHERE s.id=?
    """, (source,)).fetchone()


def configure(archive, manifest: Path, fixture: Path, *, register: bool) -> dict:
    config, code = plugin.descriptor(manifest)
    checks, scope = plugin.validate_candidate(config, code, fixture)
    config["scope"] = scope
    result = {"id": config["id"], "digest": config["digest"], "checks": checks}
    if not register:
        return result
    # Registration repeats validation and saves those same bytes and that same
    # resolved configuration. The candidate never supplies a pass receipt.
    with archive.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        row = _active(con, config["id"])
        serialized = json.dumps(config, ensure_ascii=False, sort_keys=True)
        if row and row["config"] == serialized and row["code"] == code:
            return {**result, "revision": row["live_version"], "enabled": bool(row["enabled"])}
        if row is None:
            con.execute("INSERT INTO plugin_sources(id,enabled,live_version) VALUES(?,1,0)",
                        (config["id"],))
        version = con.execute("INSERT INTO plugin_versions(source,config,code) VALUES(?,?,?)",
                              (config["id"], serialized, code)).lastrowid
        con.execute("""
            UPDATE plugin_sources SET previous_version=NULLIF(live_version,0),live_version=?,
            cursor=NULL,generation=generation+1 WHERE id=?
        """, (version, config["id"]))
        return {**result, "revision": version, "enabled": row is None or bool(row["enabled"])}


def sources(archive) -> dict:
    with archive.connect() as con:
        rows = con.execute("""
            SELECT s.id,s.enabled,s.live_version,s.previous_version,v.config
            FROM plugin_sources s JOIN plugin_versions v ON v.id=s.live_version
            ORDER BY s.id
        """).fetchall()
    return {row["id"]: {**json.loads(row["config"]), "enabled": bool(row["enabled"]),
                         "revision": row["live_version"], "previous_revision": row["previous_version"],
                         "plugin": True, "archive_scope": "local"} for row in rows}


def set_enabled(archive, source: str, enabled: bool) -> None:
    with archive.connect() as con:
        updated = con.execute("""
            UPDATE plugin_sources SET enabled=?,generation=generation+1 WHERE id=? AND enabled<>?
        """, (enabled, source, enabled))
        if not updated.rowcount and not _active(con, source):
            raise ValueError("未知对话来源")


def rollback(archive, source: str) -> dict:
    with archive.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        row = _active(con, source)
        if not row or row["previous_version"] is None:
            raise ValueError("该来源没有可回退的版本")
        previous = row["previous_version"]
        con.execute("""
            UPDATE plugin_sources SET live_version=previous_version,previous_version=live_version,
            generation=generation+1,cursor=NULL WHERE id=?
        """, (source,))
    return {"id": source, "revision": previous}


def batches(archive, source: str, *, before: int | None = None) -> list[dict]:
    with archive.connect() as con:
        if not _active(con, source):
            raise ValueError("未知插件来源")
        where = "b.source=?"
        params = (source,)
        if before is not None:
            where += " AND b.id < ?"
            params = (source, before)
        return [dict(row) for row in con.execute(f"""
            SELECT b.id,b.version AS revision,b.imported_at,COUNT(m.id) AS messages
            FROM plugin_batches b LEFT JOIN plugin_messages m ON m.batch=b.id
            WHERE {where} GROUP BY b.id ORDER BY b.id DESC LIMIT 100
        """, params)]


def purge_batch(archive, source: str, batch: int) -> dict:
    with archive.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        row = _active(con, source)
        if not row or row["enabled"]:
            raise ValueError("清理前请停用插件来源")
        if not con.execute("SELECT 1 FROM plugin_batches WHERE id=? AND source=?", (batch, source)).fetchone():
            raise ValueError("该来源没有此导入批次")
        affected = con.execute("""
            SELECT DISTINCT conversation_id FROM messages
            WHERE id IN (SELECT id FROM plugin_messages WHERE batch=?)
        """, (batch,)).fetchall()
        deleted = con.execute("DELETE FROM messages WHERE id IN (SELECT id FROM plugin_messages WHERE batch=?)",
                              (batch,)).rowcount
        for (conversation_id,) in affected:
            times = con.execute("SELECT MIN(timestamp),MAX(timestamp) FROM messages WHERE conversation_id=?",
                                (conversation_id,)).fetchone()
            if con.execute("SELECT 1 FROM messages WHERE conversation_id=?", (conversation_id,)).fetchone():
                con.execute("UPDATE conversations SET started_at=?, updated_at=? WHERE id=?",
                            (*times, conversation_id))
                archive._reindex(con, conversation_id)
            else:
                con.execute("DELETE FROM conversation_fts WHERE rowid=?", (conversation_id,))
                # Preserve the ID for a possible replay of this same session.
                con.execute("""
                    UPDATE conversations SET title='',search_text='',started_at=NULL,updated_at=NULL
                    WHERE id=?
                """, (conversation_id,))
        con.execute("UPDATE plugin_sources SET cursor=NULL,generation=generation+1 WHERE id=?", (source,))
    return {"id": source, "batch": batch, "messages_deleted": deleted}


def sync(archive, source: str) -> dict:
    with archive.connect() as con:
        row = _active(con, source)
    if not row or not row["enabled"]:
        raise ValueError("来源已停用")
    config = json.loads(row["config"])
    if (config["version"] != plugin.API_VERSION
            or hashlib.sha256(row["code"]).hexdigest() != config["digest"]):
        raise ValueError("已注册插件不兼容或内容已变更，请重新验收")
    root = Path(config["root"])
    batch = plugin.execute(row["code"], root, row["cursor"], config.get("scope"))
    positions = {relative: str(plugin.origin_path(root, relative))
                 for relative in {message["origin"] for message in batch["messages"]}}

    with archive.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        current = _active(con, source)
        if (current["generation"], current["cursor"]) != (row["generation"], row["cursor"]):
            raise ValueError("来源配置或读取进度已变更，请重试")
        created = changed = 0
        touched = set()
        batch_id = None
        for message in batch["messages"]:
            origin = positions[message["origin"]]
            session_id = message["session_id"]
            timestamp = message["timestamp"]
            existing = con.execute("""
                SELECT c.id, EXISTS(SELECT 1 FROM messages m WHERE m.conversation_id=c.id) AS populated
                FROM conversations c WHERE c.source=? AND c.source_session_id=?
            """, (source, session_id)).fetchone()
            if existing is None or not existing["populated"]:
                cwd = message["cwd"]
                project_path = archive.project_path(cwd) if cwd else None
                project_id = archive._project_for_path(con, cwd)
                conversation = con.execute("""
                    INSERT INTO conversations(source,source_session_id,source_path,cwd,project_path,
                                              project_id,started_at,updated_at)
                    VALUES(?,?,?,?,?,?,?,?)
                    ON CONFLICT(source,source_session_id) DO UPDATE SET
                      source_path=excluded.source_path,cwd=excluded.cwd,project_path=excluded.project_path,
                      project_id=excluded.project_id,started_at=excluded.started_at,updated_at=excluded.updated_at
                    RETURNING id
                """, (source, session_id, origin, cwd, project_path, project_id, timestamp, timestamp)).fetchone()[0]
                created += 1
            else:
                conversation = existing["id"]
            identity = (conversation, message["message_id"])
            previous = con.execute("""
                SELECT position,role,text,timestamp FROM messages WHERE conversation_id=? AND source_key=?
            """, identity).fetchone()
            body = tuple(message[field] for field in ("position", "role", "text", "timestamp"))
            if previous is not None:
                if tuple(previous) != body:
                    raise ValueError("同一消息身份对应不同内容或位置")
                continue
            if batch_id is None:
                batch_id = con.execute("INSERT INTO plugin_batches(source,version,imported_at) VALUES(?,?,?)",
                                       (source, row["live_version"], _now())).lastrowid
            message_id = con.execute("""
                INSERT INTO messages(id,conversation_id,source_key,position,role,text,timestamp)
                VALUES((SELECT CAST(value AS INTEGER)+1 FROM settings WHERE key='message_sequence'),?,?,?,?,?,?)
            """, (*identity, *body)).lastrowid
            con.execute("INSERT INTO plugin_messages(id,batch,origin) VALUES(?,?,?)",
                        (message_id, batch_id, origin))
            con.execute("""
                UPDATE conversations SET
                  started_at=CASE WHEN started_at IS NULL OR started_at>? THEN ? ELSE started_at END,
                  updated_at=CASE WHEN updated_at IS NULL OR updated_at<? THEN ? ELSE updated_at END
                WHERE id=?
            """, (timestamp, timestamp, timestamp, timestamp, conversation))
            changed += 1
            touched.add(conversation)
        for conversation in touched:
            archive._reindex(con, conversation)
        con.execute("UPDATE plugin_sources SET cursor=? WHERE id=?", (batch["cursor"], source))
    return {"files_seen": 0, "files_changed": 0, "conversations_new": created,
            "messages_new": changed, "batch": batch_id, "more": batch["more"], "errors": []}
