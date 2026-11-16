# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SubLang International <https://sublang.ai>
"""Client-side archive replication and search routing."""

from __future__ import annotations

import http.client
import json
import socket
import tempfile
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request
from uuid import uuid4

from .core import Archive
from .service import LOCAL_HTTP
from .support import hub_url

API = "/v1"
BATCH_SIZE = 100


class HubUnavailable(RuntimeError):
    pass


def hub_config(db: Archive) -> dict:
    path = db.db_path.resolve().with_suffix(db.db_path.suffix + ".hub.json")
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def _request(config: dict, route: str, payload: dict | None = None) -> dict:
    request = Request(
        config["address"] + API + route,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None,
        headers={"Authorization": "Bearer " + config["token"], "Content-Type": "application/json"},
    )
    try:
        with LOCAL_HTTP.open(request, timeout=5) as response:
            data = json.load(response)
            if not isinstance(data, dict):
                raise HubUnavailable("汇总服务返回了无效数据")
            return data
    except HTTPError as exc:
        if exc.code in (401, 403):
            raise HubUnavailable("汇总服务拒绝连接凭证") from exc
        raise HubUnavailable(f"汇总服务返回 HTTP {exc.code}") from exc
    except (OSError, ValueError, http.client.HTTPException) as exc:
        raise HubUnavailable("无法连接汇总服务") from exc


def _hub_info(config: dict) -> dict:
    response = _request(config, "/info")
    if response.get("protocol") != 1 or not response.get("hub_id"):
        raise HubUnavailable("该地址没有可用的 SMM 汇总服务")
    return response


def _hub_identity(config: dict) -> str:
    return _hub_info(config)["hub_id"]


def configure_hub(db: Archive, address: str, device_name: str, token_file: str | None = None) -> dict:
    address = hub_url(address)
    device_name = device_name.strip()
    if not 1 <= len(device_name) <= 120:
        raise ValueError("本机名称应为 1 到 120 个字符")
    path = db.db_path.resolve().with_suffix(db.db_path.suffix + ".hub.json")
    with db.connect() as con:
        # Serialize concurrent Codex and Claude Code configuration for this archive.
        con.execute("BEGIN IMMEDIATE")
        old = hub_config(db)
        token = old.get("token") if address == old.get("address") else None
        if token_file:
            token = Path(token_file).expanduser().read_text(encoding="ascii").strip()
        elif not token:
            provisioned = path.parent / "hub-token"
            if provisioned.is_file():
                token = provisioned.read_text(encoding="ascii").strip()
        if not token or not token.isascii() or any(not 33 <= ord(char) <= 126 for char in token):
            return {"configured": False, "needs_token": True, "address": address}
        config = {"address": address, "device_name": device_name, "token": token,
                  "device_id": old.get("device_id") or uuid4().hex}
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as out:
            json.dump(config, out, ensure_ascii=False)
        temporary = Path(out.name)
        try:
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
    try:
        _register_device(config, _hub_identity(config))
    except HubUnavailable as exc:
        return {"configured": True, "connected": False, "address": address,
                "device_name": device_name, "reason": str(exc)}
    return {"configured": True, "connected": True, "address": address, "device_name": device_name}


def _register_device(config: dict, hub_id: str) -> None:
    _request(config, "/upload", {"hub_id": hub_id, "device_id": config["device_id"],
                                 "device_name": config["device_name"], "records": []})


def configure_and_start(db: Archive, address: str, device_name: str, token_file: str | None = None) -> dict:
    from .service import _request as request_local, ensure_service

    result = configure_hub(db, address, device_name, token_file)
    if result["configured"]:
        try:
            endpoint = ensure_service(db)
            if result["connected"] and not db.get_settings()["sync_paused"]:
                request_local(endpoint, "/api/sync", method="POST")
        except (OSError, RuntimeError, ValueError) as exc:
            result["local_service_error"] = str(exc)
    return result


def push_pending(db: Archive) -> dict | None:
    config = hub_config(db)
    if not config:
        return None
    info = _hub_info(config)
    hub_id = info["hub_id"]
    key = f"hub_cursor:{hub_id}:{config['device_id']}"
    with db.connect() as con:
        saved = con.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        cursor = int(saved[0]) if saved else 0
    sent = 0
    # Bound a round so a large archive can catch up over multiple sync cycles.
    for _ in range(25):
        if db.get_settings()["sync_paused"] or hub_config(db) != config:
            return {"uploaded": sent, "pending": True}
        with db.connect() as con:
            rows = [dict(row) for row in con.execute("""
                SELECT m.id AS seq, c.source, c.source_session_id, c.started_at,
                       m.source_key, m.position, m.role, m.text, m.timestamp,
                       (SELECT COUNT(*) FROM messages ordered
                        WHERE ordered.conversation_id=m.conversation_id
                          AND (ordered.position,ordered.id)<=(m.position,m.id)) AS source_order,
                       CASE WHEN m.source_key LIKE 'offset:%' THEN (
                           SELECT COUNT(*) FROM messages earlier
                           WHERE earlier.conversation_id=m.conversation_id
                               AND earlier.source_key LIKE 'offset:%'
                               AND earlier.role=m.role AND earlier.text=m.text
                               AND earlier.timestamp IS m.timestamp
                               AND (earlier.position<m.position OR (earlier.position=m.position AND earlier.id<=m.id))
                       ) END AS occurrence
                FROM messages m JOIN conversations c ON c.id = m.conversation_id
                WHERE m.id > ? AND c.source IN ('codex','claude-code') ORDER BY m.id LIMIT ?
            """, (cursor, BATCH_SIZE))]
        if not rows:
            if sent == 0:
                _register_device(config, hub_id)
            pending = "projects" in info.get("capabilities", ()) and _push_projects(db, config, hub_id, cursor)
            return {"uploaded": sent, "pending": pending}
        response = _request(config, "/upload", {
            "hub_id": hub_id, "device_id": config["device_id"],
            "device_name": config["device_name"], "records": rows,
        })
        if response.get("accepted") != len(rows):
            raise HubUnavailable("汇总服务未确认整批记录")
        cursor = rows[-1]["seq"]
        with db.connect() as con:
            con.execute("""
                INSERT INTO settings(key,value) VALUES(?,?)
                ON CONFLICT(key) DO UPDATE SET value=MAX(CAST(settings.value AS INTEGER), CAST(excluded.value AS INTEGER))
            """, (key, str(cursor)))
        sent += len(rows)
    if "projects" in info.get("capabilities", ()):
        _push_projects(db, config, hub_id, cursor)
    return {"uploaded": sent, "pending": True}


def _project_keys(con) -> None:
    con.execute("""
        CREATE TABLE IF NOT EXISTS hub_local_project_keys (
            id INTEGER PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
            remote_key TEXT NOT NULL UNIQUE
        )
    """)
    con.execute("""
        INSERT INTO hub_local_project_keys(id,remote_key)
        SELECT id,lower(hex(randomblob(16))) FROM projects
        WHERE id NOT IN (SELECT id FROM hub_local_project_keys)
    """)


def _push_projects(db: Archive, config: dict, hub_id: str, cursor: int) -> bool:
    device = config["device_id"]
    with db.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        _project_keys(con)
        con.execute("""
            CREATE TABLE IF NOT EXISTS hub_metadata_uploads (
                hub_id TEXT NOT NULL, device_id TEXT NOT NULL, kind TEXT NOT NULL,
                local_key TEXT NOT NULL, value TEXT NOT NULL,
                PRIMARY KEY(hub_id,device_id,kind,local_key)
            )
        """)
    for _ in range(25):
        if db.get_settings()["sync_paused"] or hub_config(db) != config:
            return True
        with db.connect() as con:
            names = list(con.execute("""
                SELECT k.remote_key,p.name FROM projects p JOIN hub_local_project_keys k ON k.id=p.id
                LEFT JOIN hub_metadata_uploads a ON a.hub_id=? AND a.device_id=? AND a.kind='project'
                  AND a.local_key=k.remote_key
                WHERE a.value IS NOT p.name ORDER BY p.id LIMIT ?
            """, (hub_id, device, BATCH_SIZE)))
            memberships = [] if names else list(con.execute("""
                SELECT c.source,c.source_session_id,k.remote_key FROM conversations c
                LEFT JOIN hub_local_project_keys k ON k.id=c.project_id
                LEFT JOIN hub_metadata_uploads a ON a.hub_id=? AND a.device_id=? AND a.kind='membership'
                  AND a.local_key=c.source || ':' || c.source_session_id
                WHERE a.value IS NOT COALESCE(k.remote_key,'')
                  AND c.source IN ('codex','claude-code')
                  AND EXISTS(SELECT 1 FROM messages m WHERE m.conversation_id=c.id AND m.id<=?)
                ORDER BY c.id LIMIT ?
            """, (hub_id, device, cursor, BATCH_SIZE)))
        if not names and not memberships:
            return False
        response = _request(config, "/project-metadata", {
            "hub_id": hub_id, "device_id": device, "device_name": config["device_name"],
            "projects": [{"id": key, "name": name} for key, name in names],
            "memberships": [{"source": source, "source_session_id": session, "project_id": key}
                            for source, session, key in memberships],
        })
        if response.get("projects") != len(names) or response.get("memberships") != len(memberships):
            raise HubUnavailable("汇总服务未确认整批项目资料")
        with db.connect() as con:
            con.executemany("""
                INSERT INTO hub_metadata_uploads(hub_id,device_id,kind,local_key,value) VALUES(?,?,?,?,?)
                ON CONFLICT(hub_id,device_id,kind,local_key) DO UPDATE SET value=excluded.value
            """, [(hub_id, device, "project", key, name) for key, name in names] +
                 [(hub_id, device, "membership", f"{source}:{session}", key or "")
                  for source, session, key in memberships])
    return True


def _remote_project_key(db: Archive, project_id: int) -> str:
    with db.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        _project_keys(con)
        row = con.execute("SELECT remote_key FROM hub_local_project_keys WHERE id=?", (project_id,)).fetchone()
        if row is None:
            raise ValueError("项目不存在")
        return row[0]


def _local_origin(config: dict) -> dict:
    return {"device_name": config.get("device_name") or socket.gethostname(),
            "device_id": config.get("device_id")}


def _with_local_origins(conversation: dict, message_field: str, config: dict) -> dict:
    origin = _local_origin(config)
    for message in conversation[message_field]:
        message["origins"] = [{**origin, "source_position": message["position"]}]
    return {**conversation, "origins": [origin]}


def search_archive(db: Archive, query: str, *, local: bool = False, **options) -> dict:
    config = hub_config(db)
    reason = None
    if config and not local:
        try:
            source = options.get("current_source")
            hub_source = source if source in {None, "codex", "claude-code"} else None
            payload = {
                "query": query, "current_session_id": options.get("current_session_id") if source == hub_source else None,
                "current_source": hub_source, "include_current": options.get("include_current", False),
                "limit": options.get("limit", 5), "preview_chars": options.get("preview_chars", 0),
            }
            if options.get("scope") == "project":
                if options.get("project_id") is None:
                    raise ValueError("项目范围必须指定 project_id")
                if "projects" in _hub_info(config).get("capabilities", ()):
                    payload.update(device_id=config["device_id"],
                                   project_id=_remote_project_key(db, options["project_id"]))
            result = _request(config, "/search", payload)
            if not isinstance(result.get("results"), list) or not result.get("hub_id"):
                raise HubUnavailable("汇总服务返回了无效搜索结果")
            return {**result, "archive_scope": "hub", "requested_scope": options.get("scope", "all")}
        except HubUnavailable as exc:
            reason = str(exc)
            options.update(scope="all", project_id=None)
    result = db.search(query, **options)
    return {**result, "archive_scope": "local", "fallback_reason": reason,
            "results": [_with_local_origins(hit, "matched_messages", config) for hit in result["results"]]}


def read_archive(db: Archive, conversation_id: int, *, start: int | None = None,
                 end: int | None = None, hub_id: str | None = None,
                 hub_message_id: int | None = None) -> dict:
    if hub_id is not None:
        config = hub_config(db)
        if not config:
            raise HubUnavailable("当前未配置汇总服务，请重新搜索")
        result = _request(config, "/read", {"hub_id": hub_id, "conversation_id": conversation_id,
                                           "start": start, "end": end, "message_id": hub_message_id})
        return {**result, "archive_scope": "hub"}
    if hub_message_id is not None:
        raise ValueError("汇总消息必须提供搜索返回的 hub_id")
    config = hub_config(db)
    result = db.read(conversation_id, start=start, end=end)
    return {**_with_local_origins(result, "messages", config), "archive_scope": "local"}
