"""Archive-local signed citations. No network or cross-archive routing."""
import json
import base64
from uuid import uuid4

from .archive_protocol import digest, message_version, sign, verify


def material(db):
    cached = getattr(db, "_reference_material", None)
    if cached:
        return cached
    with db.connect() as con:
        identity = con.execute("SELECT value FROM settings WHERE key='archive:identity'").fetchone()
        has_table = con.execute("SELECT 1 FROM sqlite_master WHERE name='archive_reference_material'").fetchone()
        secret = con.execute("SELECT signing_key FROM archive_reference_material WHERE singleton=1").fetchone() if has_table else None
        if identity and secret:
            value = (json.loads(identity[0]), secret[0])
            db._reference_material = value
            return value
        con.execute("BEGIN IMMEDIATE")
        con.execute("CREATE TABLE IF NOT EXISTS archive_reference_material(singleton INTEGER PRIMARY KEY CHECK(singleton=1),signing_key TEXT NOT NULL)")
        con.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('archive:identity',?)", (json.dumps(uuid4().hex),))
        old = con.execute("SELECT value FROM settings WHERE key='archive:reference_key'").fetchone()
        con.execute("INSERT OR IGNORE INTO archive_reference_material VALUES(1,?)", (json.loads(old[0]) if old else uuid4().hex + uuid4().hex,))
        con.execute("DELETE FROM settings WHERE key='archive:reference_key'")
        identity = con.execute("SELECT value FROM settings WHERE key='archive:identity'").fetchone()
        secret = con.execute("SELECT signing_key FROM archive_reference_material WHERE singleton=1").fetchone()
    value = (json.loads(identity[0]), secret[0])
    db._reference_material = value
    return value


def decode(db, reference):
    identity, key = material(db)
    payload = verify(reference, key)
    if payload.get("archive_id") != identity or payload.get("format") != 1:
        raise ValueError("原文引用属于其他档案，请重新检索")
    return payload


def routing_metadata(reference):
    """Untrusted routing only; the destination Hub must verify its signature."""
    try:
        if not isinstance(reference, str) or len(reference) > 1_000_000:
            raise ValueError()
        prefix, encoded, signature = reference.split(".")
        payload = json.loads(base64.b64decode(encoded + "=" * (-len(encoded) % 4), altchars=b"-_", validate=True))
        if prefix != "r1" or not isinstance(payload, dict):
            raise ValueError()
        return payload
    except (TypeError, ValueError, UnicodeError) as exc:
        raise ValueError("原文引用无效，请重新检索") from exc


def issue(db, conversation_id, messages, *, scope="local", hub_id=None, project_ids=None):
    identity, key = material(db)
    with db.connect() as con:
        conversation = con.execute("SELECT source,source_session_id FROM conversations WHERE id=?", (conversation_id,)).fetchone()
        if conversation is None:
            raise ValueError("对话不存在")
        ids = [m.get("_message_id", m.get("hub_message_id")) for m in messages]
        expected = {m.get("_message_id", m.get("hub_message_id")): m.get("content_version") or message_version(m) for m in messages}
        source_keys = {m.get("_message_id", m.get("hub_message_id")): m.get("source_key") for m in messages}
        stamps = []
        for message_id in dict.fromkeys(ids):
            row = con.execute("SELECT id,source_key,position,role,text,timestamp FROM messages WHERE id=? AND conversation_id=?",
                              (message_id, conversation_id)).fetchone()
            if (row is None or expected[message_id] != message_version(dict(row))
                    or (source_keys[message_id] is not None and source_keys[message_id] != row["source_key"])):
                raise ValueError("原消息已改变，请重新检索")
            stamps.append({"id": row["id"], "source_key": row["source_key"], "position": row["position"], "version": message_version(dict(row))})
    return sign({"format": 1, "kind": "citation", "archive_scope": scope, "archive_id": identity, "hub_id": hub_id,
                 "conversation_id": conversation_id, "source": conversation["source"],
                 "origin_identity": digest([conversation["source"], conversation["source_session_id"]]), "messages": stamps,
                 "project_ids": project_ids}, key)


def wrap_hub(db, hub_id, reference):
    identity, key = material(db)
    return sign({"format": 1, "kind": "remote_reference", "archive_id": identity, "archive_scope": "hub",
                 "hub_id": hub_id, "hub_reference": reference}, key)


def bundle(db, parts):
    identity, key = material(db)
    return sign({"format": 1, "kind": "bundle", "archive_id": identity,
                 "archive_scope": "combined", "parts": list(dict.fromkeys(parts))}, key)


def legacy_hub(db, hub_id, conversation, messages):
    """Bind precisely read old-Hub candidates; never infer shared source keys."""
    identity, key = material(db)
    return sign({"format": 1, "kind": "legacy_hub", "archive_id": identity,
                 "archive_scope": "hub", "hub_id": hub_id, "conversation_id": conversation["id"],
                 "origin_identity": digest([conversation["source"], conversation["source_session_id"]]),
                 "messages": [{"id": m["hub_message_id"], "position": m["position"],
                               "version": message_version(m)} for m in messages]}, key)


def read(db, reference, *, start=None, end=None):
    payload = decode(db, reference)
    if payload.get("kind") != "citation" or "hub_reference" in payload:
        raise ValueError("远端引用应由联合档案入口读取")
    conversation_id = payload["conversation_id"]
    result = db.read(conversation_id, include_message_ids=True)
    if digest([result["source"], result["source_session_id"]]) != payload["origin_identity"]:
        raise ValueError("引用的来源身份已改变，请重新检索")
    indexed = {m["_message_id"]: m for m in result["messages"]}
    selected = []
    for stamp in payload["messages"]:
        message = indexed.get(stamp["id"])
        if (message is None or message["source_key"] != stamp["source_key"]
                or (payload["archive_scope"] == "local" and message["position"] != stamp["position"])
                or message_version(message) != stamp["version"]):
            raise ValueError("引用的原消息或内容版本已改变，请重新检索")
        if (start is None or message["position"] >= start) and (end is None or message["position"] <= end):
            selected.append(message)
    return {**result, "messages": selected}
