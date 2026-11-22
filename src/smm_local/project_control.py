"""Preview and conditionally apply explicit project-affiliation changes."""
from contextlib import nullcontext
import json
from pathlib import Path

from .archive_protocol import control_lock, digest, permits, sign, verify
from . import references
from .federation import hub_config
from .upload import LocalUpload


def _snapshot(db, con, operation, data):
    config = hub_config(db)
    target_id = data["target_id"]
    target = con.execute("SELECT p.id,p.name,p.kind,k.remote_key FROM projects p LEFT JOIN hub_local_project_keys k ON k.id=p.id WHERE p.id=?", (target_id,)).fetchone()
    if target is None:
        raise ValueError("项目不存在")
    rows = con.execute("""SELECT c.id,c.title,c.source,c.source_session_id,c.project_id,c.cwd,c.project_path,k.remote_key,
        (SELECT COUNT(*) FROM messages m WHERE m.conversation_id=c.id) AS messages,
        (SELECT MAX(id) FROM messages m WHERE m.conversation_id=c.id) AS latest_message
        FROM conversations c LEFT JOIN hub_local_project_keys k ON k.id=c.project_id ORDER BY c.id""").fetchall()
    if operation == "assign":
        rows = [r for r in rows if r["id"] == data["conversation_id"]]
        if not rows:
            raise ValueError("对话不存在")
    elif operation == "map":
        path = Path(data["path"]).expanduser().absolute()
        rows = [r for r in rows if (r["project_path"] or r["cwd"]) and Path(r["project_path"] or r["cwd"]).is_relative_to(path)]
    elif operation == "merge":
        source = con.execute("SELECT kind FROM projects WHERE id=?", (data["source_id"],)).fetchone()
        if source is None or data["source_id"] == target_id:
            raise ValueError("请选择两个不同的有效项目")
        if source[0] != target["kind"]:
            raise ValueError("普通项目与全局项目不能合并")
        rows = [r for r in rows if r["project_id"] == data["source_id"]]
    else:
        raise ValueError("未知项目操作")
    rule = None
    generation = 0
    if config.get("bound_hub_id") and con.execute("SELECT 1 FROM sqlite_master WHERE name='local_upload_policies'").fetchone():
        row = con.execute("SELECT desired,generation FROM local_upload_policies WHERE hub_id=? AND device_id=?",
                          (config["bound_hub_id"], config["device_id"])).fetchone()
        if row:
            rule = json.loads(row[0]) if row[0] else None
            generation = row[1]
    expanded = [r["id"] for r in rows if permits(rule, target["remote_key"]) and not permits(rule, r["remote_key"])]
    state = {"operation": operation, "data": data, "target": dict(target), "affected": [dict(r) for r in rows],
             "target_hub": {k: config.get(k) for k in ("address", "bound_hub_id", "device_id")},
             "policy": rule, "generation": generation}
    return state, expanded


def change(db, operation, data, confirmation=None, *, always_preview=False):
    db.projects()  # Ensure stable keys before entering the write transaction.
    identity, key = references.material(db)
    config = hub_config(db)
    upload = LocalUpload(db, config, config["bound_hub_id"]) if config.get("bound_hub_id") else None
    with control_lock(upload.guard.lock) if upload else nullcontext():
        with db.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            state, expanded = _snapshot(db, con, operation, data)
            stopped = [r["id"] for r in state["affected"] if permits(state["policy"], r["remote_key"])
                       and not permits(state["policy"], state["target"]["remote_key"])]
            report = {"affected_conversations": [r["id"] for r in state["affected"]],
                      "newly_allowed_conversations": expanded, "newly_stopped_conversations": stopped,
                      "conversations": [{k: r[k] for k in ("id", "title", "source", "source_session_id", "project_id")} for r in state["affected"]],
                      "target": state["target"]}
            fingerprint = digest(state)
            if confirmation is not None:
                payload = verify(confirmation, key)
                if payload != {"kind": "project_change", "archive_id": identity, "snapshot": fingerprint}:
                    raise ValueError("归属、范围或上传规则已改变，请重新预览")
            elif always_preview or expanded:
                return {"applied": False, "requires_confirmation": True, **report,
                        "confirmation": sign({"kind": "project_change", "archive_id": identity, "snapshot": fingerprint}, key),
                        "message": "核对影响范围后提交该确认标识；Hub 旧副本不会自动撤回"}
            if operation == "assign":
                db.assign_conversation(data["conversation_id"], data["target_id"], connection=con)
            elif operation == "map":
                db.map_path(data["path"], data["target_id"], connection=con)
            else:
                db.merge_projects(data["source_id"], data["target_id"], connection=con)
    return {"applied": True, **report,
            "message": f"已更新 {len(state['affected'])} 段本机会话；新增允许 {len(expanded)} 段、停止允许 {len(stopped)} 段。Hub 旧副本继续保留。"}
