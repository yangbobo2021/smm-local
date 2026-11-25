# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SubLang International <https://sublang.ai>
"""Client-side archive replication and search routing."""

from __future__ import annotations

import http.client
import json
import socket
import sqlite3
import tempfile
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request
from uuid import uuid4

from .core import Archive
from .service import LOCAL_HTTP
from .support import hub_url
from .archive_protocol import ControlConflict, atomic_json, digest, legacy_message_key, message_version
from .upload import LocalUpload
from . import references
from .core import tokens, compact_message
from .search_merge import merge_candidates

API = "/v1"
BATCH_SIZE = 100


class HubUnavailable(RuntimeError):
    def __init__(self, message, *, status=None):
        super().__init__(message)
        self.status = status


def hub_config(db: Archive) -> dict:
    path = db.db_path.resolve().with_suffix(db.db_path.suffix + ".hub.json")
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def _request(config: dict, route: str, payload: dict | None = None) -> dict | list:
    request = Request(
        config["address"] + API + route,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None,
        headers={"Authorization": "Bearer " + config["token"], "Content-Type": "application/json"},
    )
    try:
        with LOCAL_HTTP.open(request, timeout=5) as response:
            data = json.load(response)
            if not isinstance(data, dict) and not (route in {"/projects", "/documents/sources"} and isinstance(data,list)):
                raise HubUnavailable("汇总服务返回了无效数据")
            return data
    except HTTPError as exc:
        if exc.code == 401:
            raise HubUnavailable("汇总服务拒绝连接凭证", status=exc.code) from exc
        if exc.code == 403:
            raise HubUnavailable("Hub 当前规则拒绝此项目上传，请查看上传范围", status=exc.code) from exc
        if exc.code == 409:
            raise HubUnavailable("Hub 状态、规则或项目登记已改变，请重新检索或查看上传差异", status=exc.code) from exc
        raise HubUnavailable(f"汇总服务返回 HTTP {exc.code}", status=exc.code) from exc
    except (OSError, ValueError, http.client.HTTPException) as exc:
        raise HubUnavailable("无法连接汇总服务") from exc



def _request_binary(config, route, raw=None, *, method='PUT', payload=None, headers=None):
    """Authenticated immutable-blob traffic over the configured Hub transport."""
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        content_type = 'application/json'
    else:
        data = raw
        content_type = 'application/octet-stream'
    request = Request(config['address'] + API + route, data=data, method=method,
                      headers={**(headers or {}), 'Authorization': 'Bearer ' + config['token'], 'Content-Type': content_type})
    try:
        with LOCAL_HTTP.open(request, timeout=5) as response:
            body = response.read(20 * 1024 * 1024 + 1)
            if len(body) > 20 * 1024 * 1024:
                raise HubUnavailable('Hub二进制响应超过20MiB')
            if 'json' in response.headers.get('Content-Type', ''):
                value = json.loads(body)
                if not isinstance(value, dict):
                    raise HubUnavailable('Hub分块确认无效')
                return value
            return body
    except HTTPError as exc:
        raise HubUnavailable('Hub二进制传输返回HTTP ' + str(exc.code), status=exc.code) from exc
    except (OSError, ValueError, http.client.HTTPException) as exc:
        raise HubUnavailable('无法连接Hub原件传输') from exc


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
                  "device_id": old.get("device_id") or uuid4().hex, "policy_protocol": 1,
                  "legacy_candidate": old.get("legacy_candidate", bool(old and old.get("policy_protocol") is None))
                    and not old.get("bound_hub_id") and address == old.get("address")}
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as out:
            json.dump(config, out, ensure_ascii=False)
        temporary = Path(out.name)
        try:
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
    try:
        info = _hub_info(config)
        config = _bind_hub(db, config, info["hub_id"])
        _register_device(config, info["hub_id"], managed="upload-policy-v1" in info.get("capabilities", []))
        _controller(db, config, info["hub_id"])
    except HubUnavailable as exc:
        return {"configured": True, "connected": False, "address": address,
                "device_name": device_name, "reason": str(exc)}
    return {"configured": True, "connected": True, "address": address, "device_name": device_name}


def _register_device(config: dict, hub_id: str, *, managed=False) -> None:
    _request(config, "/upload", {"hub_id": hub_id, "device_id": config["device_id"],
                                 "device_name": config["device_name"], "records": []})
    if managed:
        _request(config, "/upload-policy/register", {"hub_id": hub_id, "device_id": config["device_id"]})


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


def _bind_hub(db: Archive, config: dict, hub_id: str) -> dict:
    updated = {**config, "bound_hub_id": hub_id}
    if config.get("policy_protocol") is None:
        updated.update(policy_protocol=1, legacy_candidate=not config.get("bound_hub_id") or config["bound_hub_id"] == hub_id)
    if config.get("bound_hub_id") and config["bound_hub_id"] != hub_id:
        updated["legacy_candidate"] = False
    if updated != config:
        with db.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            if hub_config(db) != config:
                raise HubUnavailable("汇总目标已改变，本次操作停止")
            atomic_json(db.db_path.resolve().with_suffix(db.db_path.suffix + ".hub.json"), updated)
    return updated


def _controller(db, config, hub_id):
    upload = LocalUpload(db, config, hub_id)
    row = upload.row()
    if config.get("legacy_candidate") and row["generation"] == 0:
        with db.connect() as con:
            prior = con.execute("SELECT value FROM settings WHERE key=?", (f"hub_cursor:{hub_id}:{config['device_id']}",)).fetchone()
        if prior and int(prior[0]) > 0:
            try:
                upload._save({"mode": "all", "projects": []})
            except ControlConflict:
                pass  # A restored old cursor cannot bypass a newer protected rule.
    return upload


def upload_status(db):
    config = hub_config(db)
    if not config:
        return {"configured": False, "state": "unconfigured", "policy": None}
    if not config.get("bound_hub_id"):
        try:
            config = _bind_hub(db, config, _hub_identity(config))
        except HubUnavailable as exc:
            return {"configured": True, "state": "unverified", "policy": None, "problem": str(exc)}
    return _controller(db, config, config["bound_hub_id"]).status()


def project_status(db):
    from .archive_protocol import permits
    status = upload_status(db)
    paused = db.get_settings()["sync_paused"]
    return [{**p, "upload_selected": permits(status.get("policy"), p["stable_key"]),
             "upload_allowed": status.get("state") == "confirmed" and not paused and permits(status.get("policy"), p["stable_key"])}
            for p in db.projects()]


def upload_control(db):
    config = hub_config(db)
    if not config:
        raise ValueError("尚未配置 Hub，请先通过 configure-hub 连接")
    info = _hub_info(config)
    if "upload-policy-v1" not in info.get("capabilities", []):
        raise ValueError("Hub 尚不支持上传规则，请先升级 Hub；本机不会发送正文")
    config = _bind_hub(db, config, info["hub_id"])
    return _controller(db, config, info["hub_id"])


def choose_upload(db, mode, project_ids, expected_generation=None):
    config = hub_config(db)
    if not config or not config.get("bound_hub_id"):
        upload = upload_control(db)
    else:
        upload = _controller(db, config, config["bound_hub_id"])
    upload.choose(mode, project_ids, expected_generation=expected_generation)
    try:
        info = _hub_info(upload.config)
        if info["hub_id"] != upload.hub_id:
            raise HubUnavailable("Hub 身份已改变，请重新连接并选择上传范围")
        if "upload-policy-v1" not in info.get("capabilities", []):
            raise HubUnavailable("旧 Hub 不支持上传规则，正文未发送；请先升级 Hub")
        upload.sync_policy(_request)
    except (HubUnavailable, ControlConflict) as exc:
        upload._mark("pending", str(exc))
    return upload.status()


def push_pending(db: Archive, *, control_only=False) -> dict | None:
    config = hub_config(db)
    if not config:
        return None
    info = _hub_info(config)
    hub_id = info["hub_id"]
    config = _bind_hub(db, config, hub_id)
    if "upload-policy-v1" not in info.get("capabilities", []):
        if "projects" in info.get("capabilities", []):
            _push_projects(db, config, hub_id, 0)
        return {"uploaded": 0, "pending": True, "reason": "旧 Hub 不支持上传规则，正文未发送"}
    _register_device(config, hub_id, managed=True)
    upload = _controller(db, config, hub_id)
    upload.sync_policy(_request)
    try:
        upload.resolve_unknown(_request)
    except (HubUnavailable, ControlConflict) as exc:
        upload.transfer_result(str(exc))
        raise
    _push_projects(db, config, hub_id, 0)
    if control_only or db.get_settings()["sync_paused"] or upload.row()["desired"] is None:
        return {"uploaded": 0, "pending": False, "upload": upload.status()}
    upload.catalog()
    sent = 0
    errors = []
    for _ in range(25):
        if db.get_settings()["sync_paused"] or hub_config(db) != config:
            break
        row = upload.row()
        if row["state"] != "confirmed" or row["ack_generation"] != row["generation"]:
            break
        rows = upload.candidates(row["ack_epoch"], BATCH_SIZE)
        if not rows:
            break
        if not upload.eligible(rows, row['generation']):
            break
        try:
            known = _request(config, "/known-upload-messages", {"hub_id": hub_id, "device_id": config["device_id"],
                "policy_revision": row["ack_revision"], "control_epoch": row["ack_epoch"],
                "records": [{"conversation_digest": digest([r["source"], r["source_session_id"]]),
                             "source_key": legacy_message_key(r), "version": r["version"],
                             "project_id": r["project_id"], "position": r["position"], "source_order": r["source_order"]} for r in rows]})
            if (known.get("hub_id") != hub_id or known.get("device_id") != config["device_id"]
                    or known.get("control_epoch") != row["ack_epoch"]):
                raise ControlConflict("既有消息核对的目标或恢复代次不匹配")
            wanted = {(r["logical_id"], r["version"]) for r in rows}
            verified = {(r["logical_id"], r["version"]) for r in known["known"]}
            if not verified <= wanted:
                raise ControlConflict("Hub 返回了本轮未请求的接收确认")
            upload.acknowledge_known(rows, verified, row['ack_epoch'])
            rows = [r for r in rows if (r["logical_id"], r["version"]) not in verified]
        except (HubUnavailable, ControlConflict) as exc:
            upload.transfer_result(str(exc))
            if isinstance(exc, ControlConflict):
                raise
            errors.append({"project_id": rows[0]["project_id"], "reason": str(exc)})
            continue
        if not rows:
            continue
        batch = upload.dispatch(rows)
        if batch is None:
            continue
        try:
            receipt = _request(config, "/upload", batch)
            upload.acknowledge(batch["batch_id"], receipt)
            sent += len(rows)
        except (HubUnavailable, ControlConflict) as exc:
            rejected = getattr(exc, "status", None) in {400, 403, 409, 422}
            with db.connect() as con:
                con.execute("UPDATE local_upload_batches SET state=? WHERE hub_id=? AND device_id=? AND batch_id=?",
                            ("rejected" if rejected else "unknown", hub_id, config["device_id"], batch["batch_id"]))
            upload.transfer_result(str(exc))
            if isinstance(exc, ControlConflict):
                raise
            errors.append({"project_id": rows[0]["project_id"], "reason": str(exc)})
    if not errors:
        upload.transfer_result()
    status = upload.status()
    return {"uploaded": sent, "pending": bool(upload.candidates(upload.row()["ack_epoch"], 1)) or upload.catalog_pending(),
            "errors": errors, "upload": status}


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
    """Names and stable keys only. No forbidden conversation enumeration."""
    with db.connect() as con:
        _project_keys(con)
        con.execute("CREATE TABLE IF NOT EXISTS hub_metadata_uploads (hub_id TEXT NOT NULL,device_id TEXT NOT NULL,kind TEXT NOT NULL,local_key TEXT NOT NULL,value TEXT NOT NULL,PRIMARY KEY(hub_id,device_id,kind,local_key))")
    for _ in range(25):
        if hub_config(db) != config:
            return True
        with db.connect() as con:
            names = list(con.execute("""
                SELECT k.remote_key,p.name,p.kind FROM projects p JOIN hub_local_project_keys k ON k.id=p.id
                LEFT JOIN hub_metadata_uploads a ON a.hub_id=? AND a.device_id=?
                    AND a.kind='project-v1' AND a.local_key=k.remote_key
                WHERE a.value IS NOT p.name ORDER BY p.id LIMIT ?
            """, (hub_id, config["device_id"], BATCH_SIZE)))
        if not names:
            return False
        response = _request(config, "/project-metadata", {"hub_id": hub_id,
            "device_id": config["device_id"], "device_name": config["device_name"],
            "projects": [{"id": key, "name": name, "kind": kind} for key, name, kind in names], "memberships": []})
        if response.get("projects") != len(names):
            raise HubUnavailable("汇总服务未确认整批最小项目资料")
        with db.connect() as con:
            con.executemany("INSERT INTO hub_metadata_uploads VALUES(?,?,'project-v1',?,?) ON CONFLICT(hub_id,device_id,kind,local_key) DO UPDATE SET value=excluded.value",
                            [(hub_id, config["device_id"], key, name) for key, name, _ in names])
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


def _decorate_local(db, hit, config):
    hit = _with_local_origins(hit, "matched_messages", config)
    hit["archive_scope"] = "local"
    hit["origin_session_key"] = hit["source_session_id"]
    with db.connect() as con:
        for message in hit["matched_messages"]:
            occurrence = None
            if message["source_key"].startswith("offset:"):
                occurrence = con.execute("""SELECT COUNT(*) FROM messages WHERE conversation_id=?
                    AND source_key LIKE 'offset:%' AND role=? AND text=? AND timestamp IS ?
                    AND (position<? OR (position=? AND id<=?))""", (hit["id"], message["role"], message["text"], message.get("timestamp"), message["position"], message["position"], message["_message_id"])).fetchone()[0]
            record = {**message, "occurrence": occurrence}
            source_key = legacy_message_key(record) if hit["source"] in {"codex", "claude-code"} else message["source_key"]
            message["canonical_id"] = digest([hit["source"], hit["source_session_id"], source_key])
            message["content_version"] = message_version(message)
            message["source_order"] = con.execute("SELECT COUNT(*) FROM messages WHERE conversation_id=? AND (position<? OR (position=? AND id<=?))", (hit["id"], message["position"], message["position"], message["_message_id"])).fetchone()[0]
    hit["reference"] = references.issue(db, hit["id"], hit["matched_messages"], project_ids=[hit["project_id"]] if hit.get("project_id") is not None else [])
    for message in hit["matched_messages"]:
        message["reference"] = hit["reference"]
        message.pop("source_key", None)
        message.pop("_message_id", None)
        message.pop("_query_match", None)
    return hit


def _local_search(db, query, config, options):
    result = db.search(query, **options, preview_chars=0, include_message_ids=True)
    hits = []
    failures = []
    for hit in result["results"]:
        try:
            hits.append(_decorate_local(db, hit, config))
        except ValueError as exc:
            failures.append(str(exc))
    return {**result, "results": hits, "candidate_failures": failures}


def _display(result, query, preview_chars):
    if preview_chars:
        terms = list(dict.fromkeys(tokens(query)))
        for hit in result["results"]:
            hit["matched_messages"] = [compact_message(m, terms, preview_chars) for m in hit["matched_messages"]]
    return result


def _legacy_candidate(db, config, hub_id, hit):
    """Read only old Hub's returned anchors, without widening its recall."""
    messages = []
    for candidate in hit["matched_messages"]:
        mid = candidate.get("hub_message_id")
        if type(mid) is not int:
            raise HubUnavailable("旧 Hub 未提供可核验的消息定位")
        result = _request(config, "/read", {"hub_id": hub_id, "conversation_id": hit["id"], "message_id": mid})
        if (result.get("hub_id", hub_id) != hub_id or result.get("id") != hit["id"]
                or any(result.get(k) != hit.get(k) for k in ("source", "source_session_id"))):
            raise HubUnavailable("旧 Hub 的候选来源发生变化，请重新检索")
        exact = [m for m in result["messages"] if m.get("hub_message_id") == mid]
        if len(exact) != 1 or exact[0]["role"] != candidate["role"] or exact[0]["text"] != candidate["text"]:
            raise HubUnavailable("旧 Hub 的候选消息发生变化，请重新检索")
        messages.append({**exact[0], "content_version": message_version(exact[0])})
    hit["matched_messages"] = messages
    hit["reference"] = references.legacy_hub(db, hub_id, hit, messages)
    hit["identity_verification"] = "legacy_message_version_only"
    return hit


def _validated_scope(response, hub_id, device_id, project_key):
    try:
        projects = response["effective_projects"]
        if response["hub_id"] != hub_id or not isinstance(projects, list) or not projects:
            raise ValueError()
        if any(not isinstance(p, dict) or type(p.get("id")) is not int or p["id"] < 1
               or not all(isinstance(p.get(k), str) and p[k] for k in ("name", "source", "owner", "source_key")) for p in projects):
            raise ValueError()
        if len({p["id"] for p in projects}) != len(projects) or not any(
                p["source"] == "device" and p["owner"] == device_id and p["source_key"] == project_key for p in projects):
            raise ValueError()
        payload = references.routing_metadata(response["scope_reference"])
        if (payload.get("format") != 1 or payload.get("kind") != "query_scope" or payload.get("hub_id") != hub_id
                or payload.get("device_id") != device_id or payload.get("project_key") != project_key
                or payload.get("projects") != projects):
            raise ValueError()
        return response
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise HubUnavailable("Hub 返回了无效的项目范围，本次只查本机所请求项目") from exc


def search_archive(db: Archive, query: str, *, local: bool = False, **options) -> dict:
    scope = options.get("scope", "all")
    hub_project_id = options.pop("hub_project_id", None)
    limit = options.get("limit", 5)
    preview = options.pop("preview_chars", 0)
    if not tokens(query):
        raise ValueError("查询词不能为空")
    if scope not in {"all", "project"}:
        raise ValueError("范围必须是 all 或 project")
    if not 1 <= limit <= 50:
        raise ValueError("limit 必须在 1 到 50 之间")
    if preview != 0 and not 100 <= preview <= 2000:
        raise ValueError("preview_chars 必须为 0 或 100 到 2000")
    if hub_project_id is not None:
        if type(hub_project_id) is not int or hub_project_id<1 or options.get('project_id') is not None or scope!='project' or local:
            raise ValueError('请选择一个本机或Hub项目根；Hub根不支持仅本机')
    if scope == "project":
        project_id = options.get("project_id")
        if hub_project_id is None:
            if project_id is None:raise ValueError("项目范围必须指定 project_id")
            db.effective_projects(project_id)
    elif options.get('project_id') is not None:raise ValueError('all不能指定项目根')
    config = hub_config(db)
    if hub_project_id is not None and not config:
        return {'results':[],'scope':scope,'archive_scope':'local','fallback_reason':'未连接Hub，无法确定Hub根范围','coverage':{'local':'complete','hub':'unavailable'},'candidate_failures':[],'effective_projects':[]}
    if local or not config:
        result = _local_search(db, query, config, options)
        return _display({**result, "archive_scope": "local", "requested_scope": scope,
                         "fallback_reason": None, "coverage": {"local": "complete" if not result["candidate_failures"] else "partial", "hub": "not_requested"}}, query, preview)
    snapshot = None
    remote = None
    hub_reason = None
    effective = "all"
    local_options = dict(options)
    try:
        info = _hub_info(config)
        config = _bind_hub(db, config, info["hub_id"])
        source = options.get("current_source")
        hub_source = source if source in {None, "codex", "claude-code"} else None
        payload = {"query": query, "current_session_id": options.get("current_session_id") if source == hub_source else None,
                   "current_source": hub_source, "include_current": options.get("include_current", False),
                   "limit": limit, "preview_chars": 0}
        if scope == "project":
            if "query-scope-v1" not in info.get("capabilities", []):
                raise HubUnavailable("Hub 不支持共同项目范围，本次只查本机所请求项目")
            from .document_search import _scope
            snapshot = _scope(db,config,info,options.get('project_id'),hub_project_id)
            effective = snapshot["effective_projects"]
            local_keys = {p["stable_key"]: p["id"] for p in db.projects()}
            local_options["exact_project_ids"] = tuple(sorted({local_keys[p["source_key"]] for p in effective
                if p.get("source") == "device" and p.get("owner") == config["device_id"] and p.get("source_key") in local_keys}))
            payload.update(scope_reference=snapshot["scope_reference"], device_id=config["device_id"])
        remote = _request(config, "/search", payload)
        if not isinstance(remote.get("results"), list) or remote.get("hub_id") != info["hub_id"]:
            raise HubUnavailable("汇总服务返回了无效搜索结果")
        usable = []
        failures = list(remote.get("candidate_failures", []))
        remote["returned_count"] = len(remote["results"])
        for hit in remote["results"]:
            try:
                if not isinstance(hit, dict) or not all(k in hit for k in ("id", "source", "source_session_id", "matched_messages")):
                    raise ValueError()
                hit["archive_scope"] = "hub"
                if not hit.get("reference"):
                    if "full-candidates-v1" in info.get("capabilities", []):
                        raise ValueError()
                    _legacy_candidate(db, config, info["hub_id"], hit)
                if not hit["matched_messages"]:
                    raise ValueError()
                for message in hit["matched_messages"]:
                    if (not isinstance(message.get("text"), str) or message.get("content_version") != message_version(message)):
                        raise ValueError()
                    message["reference"] = hit["reference"]
                usable.append(hit)
            except (HubUnavailable, ValueError, KeyError, TypeError, AttributeError):
                failures.append("Hub 候选缺少可核验的完整消息或精确引用，已排除且不扩大召回")
        remote.update(results=usable, candidate_failures=failures)
    except HubUnavailable as exc:
        hub_reason = str(exc)
        remote = None
        if snapshot is not None and getattr(exc, "status", None) in {400, 409, 422}:
            snapshot = None  # The Hub rejected this scope, rather than merely failing its search.
        if scope == "project" and snapshot is None:
            local_options["exact_project_ids"] = (options["project_id"],) if hub_project_id is None else ()
    try:
        local_result = _local_search(db, query, config, local_options)
    except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
        if remote is None:
            raise
        local_result = {"results": [], "candidate_failures": [str(exc)], "effective_projects": []}
    if remote is None:
        coverage = {"local": "partial" if local_result["candidate_failures"] else "complete", "hub": "unavailable"}
        result = {**local_result, "archive_scope": "local", "requested_scope": scope,
                  "fallback_reason": hub_reason, "coverage": coverage}
        if snapshot is not None:
            result["effective_projects"] = effective
        return _display(result, query, preview)
    hits = merge_candidates(local_result["results"], remote["results"], query, limit)
    for hit in hits:
        if hit.pop("needs_bundle", False):
            hit["reference"] = references.bundle(db, [r["reference"] for r in hit["origin_references"]])
            hit["archive_scope"] = "combined"
    return _display({"query": query, "scope": scope, "requested_scope": scope,
        "archive_scope": "combined", "hub_id": remote["hub_id"], "effective_projects": effective,
        "local_effective_projects": local_result["effective_projects"],
        "excluded_current_session_id": local_result.get("excluded_current_session_id"),
        "coverage": {"local": "partial" if local_result["candidate_failures"] else "complete", "hub": "partial" if remote["candidate_failures"] else "complete"},
        "candidate_failures": local_result["candidate_failures"] + remote["candidate_failures"],
        "capability_limitations": [] if "full-candidates-v1" in info.get("capabilities", []) else ["旧 Hub 使用兼容候选核验；未证实跨档案同源的副本不会合并"],
        "rerank": {"scope": "returned_candidates", "local_count": len(local_result["results"]),
                   "hub_count": len(remote["results"]), "hub_returned_count": remote["returned_count"], "method": "BM25"}, "results": hits}, query, preview)


def read_archive(db: Archive, conversation_id: int | None = None, *, start: int | None = None,
                 end: int | None = None, hub_id: str | None = None,
                 hub_message_id: int | None = None, reference: str | None = None) -> dict:
    if reference is not None:
        route = references.routing_metadata(reference)
        payload = (route if route.get("kind") == "citation" and route.get("archive_scope") == "hub"
                   else references.decode(db, reference))
        if payload.get("kind") == "bundle":
            if conversation_id is not None or hub_id is not None or hub_message_id is not None or start is not None or end is not None:
                raise ValueError("多来源引用请单独选择来源后指定消息范围")
            parts = [read_archive(db, reference=part) for part in payload["parts"]]
            if not parts:
                raise ValueError("原文引用没有可读取的来源")
            messages = {}
            for part in parts:
                for message in part["messages"]:
                    key = (message.get("canonical_id", (part["archive_scope"], message["position"])), message.get("content_version"))
                    if key not in messages:
                        messages[key] = message
                    else:
                        for origin in message.get("origins", []):
                            if origin not in messages[key].setdefault("origins", []):
                                messages[key]["origins"].append(origin)
            return {**parts[0], "archive_scope": "combined", "origin_references": payload["parts"],
                    "messages": sorted(messages.values(), key=lambda m: (m.get("source_order", m["position"]), m.get("canonical_id", "")))}
        if conversation_id is not None and conversation_id != payload.get("conversation_id"):
            raise ValueError("reference 与会话定位参数冲突")
        if hub_id is not None and hub_id != payload.get("hub_id"):
            raise ValueError("reference 与 Hub 定位参数冲突")
        if hub_message_id is not None:
            raise ValueError("请单独使用 reference 读取")
        if payload.get("kind") == "legacy_hub":
            config = hub_config(db)
            if not config or config.get("bound_hub_id") != payload["hub_id"]:
                raise HubUnavailable("Hub 已切换，请重新搜索")
            selected = []
            for stamp in payload["messages"]:
                result = _request(config, "/read", {"hub_id": payload["hub_id"],
                    "conversation_id": payload["conversation_id"], "message_id": stamp["id"]})
                if (result.get("hub_id", payload["hub_id"]) != payload["hub_id"] or result.get("id") != payload["conversation_id"]
                        or digest([result.get("source"), result.get("source_session_id")]) != payload["origin_identity"]):
                    raise ValueError("原文引用的来源已改变，请重新检索")
                exact = [m for m in result["messages"] if m.get("hub_message_id") == stamp["id"]]
                if len(exact) != 1 or message_version(exact[0]) != stamp["version"]:
                    raise ValueError("原文引用的消息版本已改变，请重新检索")
                message = exact[0]
                if (start is None or message["position"] >= start) and (end is None or message["position"] <= end):
                    selected.append({**message, "reference": reference, "content_version": stamp["version"]})
            return {**result, "messages": selected, "archive_scope": "hub"}
        if payload.get("kind") == "remote_reference" or payload.get("archive_scope") == "hub":
            config = hub_config(db)
            if not config:
                raise HubUnavailable("当前未配置汇总服务，请重新搜索")
            if config.get("bound_hub_id") != payload["hub_id"]:
                raise HubUnavailable("Hub 已切换，请重新搜索")
            result = _request(config, "/read", {"hub_id": payload["hub_id"], "reference": payload.get("hub_reference", reference),
                                                 "start": start, "end": end})
            for message in result["messages"]:
                message["reference"] = reference
            return {**result, "archive_scope": "hub"}
        result = references.read(db, reference, start=start, end=end)
        for message in result["messages"]:
            occurrence = None
            if message["source_key"].startswith("offset:"):
                with db.connect() as con:
                    occurrence = con.execute("SELECT COUNT(*) FROM messages WHERE conversation_id=? AND source_key LIKE 'offset:%' AND role=? AND text=? AND timestamp IS ? AND (position<? OR (position=? AND id<=?))", (result["id"], message["role"], message["text"], message.get("timestamp"), message["position"], message["position"], message["_message_id"])).fetchone()[0]
            key = legacy_message_key({**message, "occurrence": occurrence}) if result["source"] in {"codex", "claude-code"} else message["source_key"]
            message["canonical_id"] = digest([result["source"], result["source_session_id"], key])
            message["content_version"] = message_version(message)
            message["reference"] = reference
            with db.connect() as con:
                message["source_order"] = con.execute("SELECT COUNT(*) FROM messages WHERE conversation_id=? AND (position<? OR (position=? AND id<=?))", (result["id"], message["position"], message["position"], message["_message_id"])).fetchone()[0]
            message.pop("_message_id", None)
            message.pop("source_key", None)
        return {**_with_local_origins(result, "messages", hub_config(db)), "archive_scope": "local"}
    if conversation_id is None:
        raise ValueError("请提供原文引用或会话 ID")
    if hub_id is not None:
        config = hub_config(db)
        if not config:
            raise HubUnavailable("当前未配置汇总服务，请重新搜索")
        result = _request(config, "/read", {"hub_id": hub_id, "conversation_id": conversation_id,
                                           "start": start, "end": end, "message_id": hub_message_id})
        return {**result, "archive_scope": "hub"}
    if hub_message_id is not None:
        raise ValueError("汇总消息必须提供搜索返回的 hub_id")
    result = db.read(conversation_id, start=start, end=end)
    return {**_with_local_origins(result, "messages", hub_config(db)), "archive_scope": "local"}
