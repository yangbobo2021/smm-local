# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SubLang International <https://sublang.ai>
"""Verify approved conversation boundaries independently of adapter output."""

import json
import sqlite3
from contextlib import closing


def validate(scope):
    if scope == {"kind": "all"} or (
        isinstance(scope, dict) and set(scope) == {"kind", "all_sessions"}
        and scope["kind"] == "zcode" and scope["all_sessions"] is True
    ):
        return scope
    if not isinstance(scope, dict) or scope.get("kind") not in ("sessions", "zcode"):
        raise ValueError("验收样本需要独立提供 scope，明确授权全部来源或限定会话")
    kind = scope["kind"]
    fields = {"kind", "session_ids"}
    if kind == "zcode":
        fields.add("first_user_prefix")
    ids = scope.get("session_ids")
    if set(scope) != fields or not isinstance(ids, list) or any(
        not isinstance(sid, str) or not sid.strip() or len(sid) > 1024 for sid in ids
    ):
        raise ValueError("scope.session_ids 必须是授权的会话 ID 列表")
    if kind == "zcode":
        prefix = scope["first_user_prefix"]
        if not isinstance(prefix, str) or not prefix.strip() or len(prefix) > 1024:
            raise ValueError("ZCode scope 需要非空的首条可见用户消息前缀 first_user_prefix")
    elif not ids:
        raise ValueError("scope.session_ids 至少需要一个授权会话")
    return {**scope, "session_ids": sorted(set(ids))}


def _first_prompt(db, session_id):
    for (message_id,) in db.execute("""
        SELECT id FROM message
        WHERE session_id=? AND json_extract(data,'$.role')='user'
          AND NOT COALESCE(json_extract(data,'$.synthetic'),0)
          AND NOT COALESCE(json_extract(data,'$.hidden'),0)
          AND COALESCE(json_extract(data,'$.visibility'),'') NOT IN ('hidden','model-only')
          AND COALESCE(json_extract(data,'$.metadata.visibility'),'') NOT IN ('hidden','model-only')
          AND COALESCE(json_extract(data,'$.semantics.origin'),'') <> 'system'
          AND COALESCE(json_extract(data,'$.semantics.kind'),'') NOT IN ('timeline_event','step','tool')
        ORDER BY rowid
    """, (session_id,)):
        text = "".join(part for (part,) in db.execute("""
            SELECT json_extract(data,'$.text') FROM part
            WHERE message_id=? AND json_extract(data,'$.type')='text'
              AND json_type(data,'$.text')='text'
              AND NOT COALESCE(json_extract(data,'$.synthetic'),0)
              AND NOT COALESCE(json_extract(data,'$.hidden'),0)
              AND COALESCE(json_extract(data,'$.visibility'),'') NOT IN ('hidden','model-only')
              AND COALESCE(json_extract(data,'$.metadata.visibility'),'') NOT IN ('hidden','model-only')
            ORDER BY sequence, rowid
        """, (message_id,)))
        if text.strip():
            return text
    return ""


def check(scope, root, messages):
    if scope is None or scope["kind"] == "all":
        return
    allowed = set(scope.get("session_ids", []))

    def reject(message, reason):
        sid, mid = (json.dumps(message[field], ensure_ascii=False)
                    for field in ("session_id", "message_id"))
        raise ValueError(f"超出授权导入范围：会话 {sid}，消息 {mid}（{reason}）")

    if scope["kind"] == "sessions":
        for message in messages:
            if message["session_id"] not in allowed:
                reject(message, "不在授权会话列表中")
        return
    if not root.is_file():
        raise ValueError("ZCode 授权范围需要使用实际 SQLite 文件路径")
    try:
        with closing(sqlite3.connect(root.as_uri() + "?mode=ro", uri=True, timeout=1)) as db:
            db.execute("BEGIN")
            for message in messages:
                sid = message["session_id"]
                if not scope.get("all_sessions") and sid not in allowed:
                    if not _first_prompt(db, sid).startswith(scope["first_user_prefix"]):
                        reject(message, "首条可见用户消息不匹配授权前缀")
                    allowed.add(sid)
                if db.execute("""
                    SELECT 1 FROM message WHERE id=? AND session_id=?
                """, (message["message_id"], sid)).fetchone() is None:
                    reject(message, "实际来源中该消息不属于所报会话")
    except sqlite3.Error as exc:
        raise ValueError(f"无法独立核对 ZCode SQLite 授权范围：{exc}") from exc
