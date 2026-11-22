"""Project policy, continuation, and control persistence behavior."""
import json
import sqlite3

import pytest

from smm_local import federation
from smm_local.core import Archive
from smm_local.upload import LocalUpload
from test_005_contracts import pair, add_local, connect, bodies


@pytest.mark.parametrize("mode,selected,expected", [
    ("all", [], {"a", "b"}), ("none", [], set()),
    ("only", [], set()), ("except", [], {"a", "b"}),
    ("only", ["A"], {"a"}), ("except", ["A"], {"b"}),
])
def test_modes_upload_only_selected_projects(pair, mode, selected, expected):
    a = add_local(pair, "a", "A", "a")
    b = add_local(pair, "b", "B", "b")
    connect(pair)
    ids = {"A": a["project_id"], "B": b["project_id"]}
    status = federation.choose_upload(pair.local, mode, [ids[k] for k in selected])
    assert status["state"] == "confirmed"
    federation.push_pending(pair.local)
    assert set(bodies(pair.remote)) == expected
    assert federation.push_pending(pair.local)["uploaded"] == 0


def test_invalid_choices_do_not_change_active_policy(pair):
    a = add_local(pair, "a", "A", "a")
    connect(pair)
    before = federation.choose_upload(pair.local, "none", [])
    for mode, ids in [("invalid", []), ("all", [a["project_id"]]), ("none", [a["project_id"]]), ("only", [99999])]:
        with pytest.raises(ValueError):
            federation.choose_upload(pair.local, mode, ids)
        after = federation.upload_status(pair.local)
        assert after["policy"] == before["policy"]
        assert after["generation"] == before["generation"]


def test_global_assignment_survives_reimport_and_unknown_stays_local(pair):
    """TC-005-global: explicit global is persistent; unknown is not global."""
    a = add_local(pair, "a", "A", "a global dialogue")
    connect(pair)
    global_project = pair.local.ensure_global_project()
    assert pair.local.ensure_global_project()["id"] == global_project["id"]
    pair.local.assign_conversation(a["id"], global_project["id"])
    source = pair.histories / "a.jsonl"
    source.write_text(source.read_text() + json.dumps({"type": "session_meta", "payload": {"id": "a", "cwd": str(pair.histories.parent / "A")}}) + "\n")
    pair.local.sync_codex(pair.histories)
    assert pair.local.read(a["id"])["project_id"] == global_project["id"]
    missing = [
        {"type": "session_meta", "payload": {"id": "unknown"}},
        {"type": "response_item", "ordinal": 1, "payload": {"type": "message", "id": "unknown-message", "role": "user", "content": [{"type": "input_text", "text": "unknown must remain local"}]}},
    ]
    (pair.histories / "unknown.jsonl").write_text("".join(json.dumps(r) + "\n" for r in missing))
    pair.local.sync_codex(pair.histories)
    federation.choose_upload(pair.local, "all", [])
    federation.push_pending(pair.local)
    assert bodies(pair.remote) == ["a global dialogue"]
    with pair.local.connect() as con:
        assert con.execute("SELECT project_id FROM conversations WHERE source_session_id='unknown'").fetchone()[0] is None


def test_resume_backfills_old_new_and_appended_despite_global_cursor(pair):
    """TC-005-backfill: an unrelated cursor cannot erase A's pending history."""
    a = add_local(pair, "a", "A", "A old history")
    b = add_local(pair, "b", "B", "B already uploaded")
    config = connect(pair)
    federation.choose_upload(pair.local, "only", [b["project_id"]])
    federation.push_pending(pair.local)
    assert bodies(pair.remote) == ["B already uploaded"]
    with pair.local.connect() as con:
        con.execute("INSERT INTO settings VALUES(?,?)", (f"hub_cursor:{config['bound_hub_id']}:{config['device_id']}", "99999999"))
    appended = {"type": "response_item", "ordinal": 2, "payload": {"type": "message", "id": "a-append", "role": "assistant", "content": [{"type": "output_text", "text": "A appended during stop"}]}}
    with (pair.histories / "a.jsonl").open("a") as stream:
        stream.write(json.dumps(appended) + "\n")
    add_local(pair, "a-new", "A", "A new conversation during stop")
    federation.choose_upload(pair.local, "all", [])
    federation.push_pending(pair.local)
    assert sorted(bodies(pair.remote)) == sorted(["B already uploaded", "A old history", "A appended during stop", "A new conversation during stop"])
    with pair.remote.connect() as con:
        old = con.execute("SELECT id FROM conversations WHERE source_session_id='a'").fetchone()[0]
    assert [m["text"] for m in pair.remote.read(old)["messages"]] == ["A old history", "A appended during stop"]
    assert federation.push_pending(pair.local)["uploaded"] == 0
    assert len(bodies(pair.remote)) == 4


def test_unknown_receipt_can_resolve_after_stop_without_sending_body(pair, monkeypatch):
    add_local(pair, "a", "A", "committed before stop")
    connect(pair)
    federation.choose_upload(pair.local, "all", [])
    original = federation._request
    lost = False
    def request(config, route, payload=None):
        nonlocal lost
        result = original(config, route, payload)
        if route == "/upload" and payload["records"] and not lost:
            lost = True
            federation.choose_upload(pair.local, "none", [])
            raise federation.HubUnavailable("synthetic confirmation lost")
        return result
    monkeypatch.setattr(federation, "_request", request)
    federation.push_pending(pair.local)
    assert federation.upload_status(pair.local)["inflight_messages"] == 1
    before = len(pair.calls)
    federation.push_pending(pair.local)
    assert not any(route == "/upload" and payload["records"] for route, payload in pair.calls[before:])
    status = federation.upload_status(pair.local)
    assert status["policy"]["mode"] == "none"
    assert status["inflight_messages"] == 0
    assert status["confirmed_messages"] == 1
    assert bodies(pair.remote) == ["committed before stop"]


def test_old_allow_backup_blocks_until_explicit_hub_reconciliation(pair, tmp_path):
    """TC-005-local-restore: stale local allow cannot silently replace Hub none."""
    add_local(pair, "a", "A", "old history")
    config = connect(pair)
    federation.choose_upload(pair.local, "all", [])
    backup = tmp_path / "backup.sqlite3"
    with pair.local.connect() as source, sqlite3.connect(backup) as target:
        source.backup(target)
    federation.choose_upload(pair.local, "none", [])
    controller = LocalUpload(pair.local, config, config["bound_hub_id"])
    prepared = controller.prepare_restore()
    assert prepared["body_stopped"] is True
    assert str(controller.guard.path) in prepared["do_not_restore"]
    with sqlite3.connect(backup) as source, pair.local.connect() as target:
        source.backup(target)
    restored = Archive(pair.local.db_path)
    controller = LocalUpload(restored, config, config["bound_hub_id"])
    assert controller.status()["state"] == "conflict"
    before = controller.row()["desired"]
    difference = controller.reconcile(federation._request)
    assert difference["hub"]["policy"]["mode"] == "none"
    assert controller.row()["desired"] == before
    result = controller.reconcile(federation._request, use="hub")
    assert result["state"] == "confirmed"
    assert result["policy"]["mode"] == "none"
    federation.push_pending(restored)
    assert bodies(pair.remote) == []
