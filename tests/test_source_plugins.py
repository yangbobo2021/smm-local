# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SubLang International <https://sublang.ai>

import asyncio
import json
import sqlite3
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from smm_local.api import create_app
from smm_local.core import Archive
from smm_local.importers import plugin, registry
from smm_local.mcp_server import create_mcp
from smm_local.service import _request, running_service, stop_on_demand


ROOT = Path(__file__).resolve().parents[1]
ACCEPT = ROOT / "skills/smm-source-adapter/scripts/accept.py"
JSON_ADAPTER = """
import json, sys, time
from pathlib import Path

request = json.load(sys.stdin)
root = Path(request["root"])
mode = root.with_name("mode")
mode = mode.read_text() if mode.is_file() else ""
if mode == "hang":
    while True:
        time.sleep(1)
if mode == "crash":
    sys.exit(13)
if mode == "overflow":
    print("a" * 5000000)
    sys.exit()
if mode == "slow":
    time.sleep(0.8)
items = json.loads(root.read_text(encoding="utf-8"))
start = int(request["cursor"] or 0)
end = min(len(items), start + request["limit"])
messages = [
    dict(session_id=row["thread"], message_id=row["event"], position=row["ordinal"],
         role=row["author"], text=row["body"], origin=root.name, cwd=row.get("cwd"))
    for row in items[start:end] if row["author"] in ("user", "assistant")
]
if mode == "bad":
    messages[-1]["position"] = -1
if mode == "conflict":
    messages.append(dict(session_id="alpha", message_id="1", position=0,
                         role="user", text="corrupted duplicate", origin=root.name))
print(json.dumps(dict(messages=messages, cursor=str(end), more=end < len(items))))
"""
SQLITE_ADAPTER = """
import json, sqlite3, sys
from pathlib import Path

request = json.load(sys.stdin)
root = Path(request["root"])
after = int(request["cursor"] or 0)
with sqlite3.connect(root.as_uri() + "?mode=ro", uri=True) as db:
    rows = db.execute(
        "SELECT seq,chat,speaker,body FROM events WHERE seq>? ORDER BY seq LIMIT ?",
        (after, request["limit"] + 1),
    ).fetchall()
messages = [
    dict(session_id=chat, message_id=str(seq), position=seq,
         role=speaker, text=body, origin=root.name)
    for seq, chat, speaker, body in rows[:request["limit"]] if speaker in ("user", "assistant")
]
end = rows[min(len(rows), request["limit"]) - 1][0] if rows else after
print(json.dumps(dict(messages=messages, cursor=str(end), more=len(rows) > request["limit"])))
"""


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


@pytest.fixture
def archive(tmp_path, monkeypatch):
    monkeypatch.setenv("SMM_SERVICE_PORT", "0")
    monkeypatch.setenv("PYTHONPATH", str(ROOT / "src"))
    db = Archive(tmp_path / "smm.sqlite3")
    roots = []
    for name in ("codex", "claude"):
        directory = tmp_path / name
        directory.mkdir()
        roots.append(str(directory))
    db.set_settings(codex_root=roots[0], claude_root=roots[1], sync_interval_seconds=10)
    yield db
    stop_on_demand(db)


def cli(db, *args, ok=True, skill=False):
    entry = [str(ACCEPT)] if skill else ["-m", "smm_local.cli"]
    completed = subprocess.run([sys.executable, *entry, "--db", str(db.db_path), *map(str, args)],
                               capture_output=True, text=True, timeout=30)
    if ok:
        assert completed.returncode == 0, completed.stderr
        return json.loads(completed.stdout)
    assert completed.returncode != 0
    return completed.stderr


def eventually(check, limit=15):
    deadline = time.monotonic() + limit
    while time.monotonic() < deadline:
        if value := check():
            return value
        time.sleep(0.1)
    pytest.fail("等待后台处理超时")


def json_source(base, source="custom-json"):
    data = [
        {"thread": "alpha", "event": "1", "ordinal": 0, "author": "user", "body": "白鹭验收 重复原文"},
        {"thread": "alpha", "event": "2", "ordinal": 1, "author": "tool", "body": "内部鹦鹉标记"},
        {"thread": "alpha", "event": "3", "ordinal": 2, "author": "assistant", "body": "首轮结果"},
        {"thread": "beta", "event": "1", "ordinal": 0, "author": "user", "body": "另一段会话"},
    ]
    extra = [{"thread": "alpha", "event": "4", "ordinal": 3, "author": "user", "body": "白鹭验收 重复原文"}]
    before, after, live = [base / part / "events.json" for part in ("before", "after", "live")]
    dump(before, data)
    dump(after, data + extra)
    dump(live, data)
    fixture = base / "fixture.json"
    expected = [
        dict(session_id="alpha", message_id="1", position=0, role="user", text="白鹭验收 重复原文", origin="events.json"),
        dict(session_id="alpha", message_id="3", position=2, role="assistant", text="首轮结果", origin="events.json"),
        dict(session_id="beta", message_id="1", position=0, role="user", text="另一段会话", origin="events.json"),
    ]
    dump(fixture, {"before": str(before), "after": str(after), "scope": {"kind": "all"}, "expected_before": expected,
                   "expected_added": [{**expected[0], "message_id": "4", "position": 3}]})
    manifest = base / "manifest.json"
    script = base / "adapter.py"
    script.write_text(JSON_ADAPTER, encoding="utf-8")
    dump(manifest, {"version": 1, "root": str(live), "script": script.name,
                    "name": f"来源 {source}", "id": source})
    return manifest, fixture, live, data, extra


@pytest.mark.parametrize(("stage", "phase", "kind"), [
    ("before", "首次读取", "文件"), ("after", "追加读取", "目录"), ("live", "实际来源探测", "文件"),
])
def test_skill_reports_failed_stage_and_root_type(archive, tmp_path, stage, phase, kind):
    manifest, fixture, live, *_ = json_source(tmp_path)
    sample = json.loads(fixture.read_text(encoding="utf-8"))
    before, after = Path(sample["before"]), Path(sample["after"])
    if stage == "after":
        sample["after"] = str(after.parent)
        dump(fixture, sample)
    failed = {"before": before, "after": after.parent, "live": live}[stage].resolve()
    candidate = manifest.with_name("adapter.py")
    candidate.write_text(
        JSON_ADAPTER.replace(
            'request = json.load(sys.stdin)',
            'request = json.load(sys.stdin)\n'
            f'if request["root"] == {str(failed)!r}: raise SystemExit(17)',
        ), encoding="utf-8",
    )
    error = cli(archive, "validate", manifest, "--fixture", fixture, skill=True, ok=False)
    assert f"{stage}（{phase}），root=「{failed}」（{kind}）" in error, error
    assert "退出码 17" in error
    assert "custom-json" not in archive.configured_sources()


def test_skill_registers_and_background_resumes_after_restart(archive, tmp_path):
    manifest, fixture, live, data, extra = json_source(tmp_path)
    result = cli(archive, "validate", manifest, "--fixture", fixture, skill=True)
    assert result["checks"] == {"first": 3, "added": 1, "live_preview": 3}
    assert "custom-json" not in archive.configured_sources()
    candidate = manifest.with_name("adapter.py")
    candidate.write_text(JSON_ADAPTER.replace('row["body"]', '"incorrect"'))
    assert "独立预期不符" in cli(archive, "register", manifest, "--fixture", fixture, skill=True, ok=False)
    candidate.write_text(JSON_ADAPTER)
    registered = cli(archive, "register", manifest, "--fixture", fixture, skill=True)
    assert registered["digest"] == result["digest"]
    candidate.write_text("raise RuntimeError('different candidate')")
    manifest.unlink()
    assert cli(archive, "maintenance", "status", "--source", "custom-json")["sync"]["sources"]["custom-json"]["enabled"]
    eventually(lambda: archive.source_status()["custom-json"]["messages"] == 3)
    previous = archive.source_status()["custom-json"]["last_success"]
    assert cli(archive, "maintenance", "sync", "--source", "custom-json")["result"]["messages_new"] == 0
    stop_on_demand(archive)
    assert not running_service(archive)
    cli(archive, "maintenance", "status", "--source", "custom-json")
    dump(live, data + extra)
    eventually(lambda: archive.source_status()["custom-json"]["messages"] == 4)
    assert archive.source_status()["custom-json"]["last_success"] > previous
    found = cli(archive, "search", "白鹭验收", "--local")
    assert found["archive_scope"] == "local"
    conversation = cli(archive, "read", found["results"][0]["id"])
    assert [m["text"] for m in conversation["messages"]] == ["白鹭验收 重复原文", "首轮结果", "白鹭验收 重复原文"]
    assert [m["position"] for m in conversation["messages"]] == [0, 2, 3]
    assert [m["role"] for m in conversation["messages"]] == ["user", "assistant", "user"]
    assert conversation["messages"][-1]["plugin_revision"] == registered["revision"]
    assert not archive.search("内部鹦鹉标记")["results"]


def test_scope_rejects_later_live_page_and_persistent_batch(archive, tmp_path):
    manifest, fixture, live, data, extra = json_source(tmp_path)
    sample = json.loads(fixture.read_text(encoding="utf-8"))
    sample["scope"] = {"kind": "sessions", "session_ids": ["alpha"]}
    sample["expected_before"] = sample["expected_before"][:2]
    dump(fixture, sample)
    for field, rows in (("before", data), ("after", data + extra)):
        dump(Path(sample[field]), [row for row in rows if row["thread"] == "alpha"])
    candidate = manifest.with_name("adapter.py")
    candidate.write_text(JSON_ADAPTER.replace('request["limit"]', '3'), encoding="utf-8")

    error = cli(archive, "register", manifest, "--fixture", fixture, skill=True, ok=False)
    assert "live（实际来源探测）" in error
    assert '超出授权导入范围：会话 "beta"，消息 "1"' in error
    assert "custom-json" not in archive.configured_sources()
    assert not running_service(archive)

    dump(live, data[:3])
    cli(archive, "register", manifest, "--fixture", fixture, skill=True)
    eventually(lambda: archive.source_status()["custom-json"]["messages"] == 2)
    dump(live, data[:3] + extra + data[3:])
    result = archive.sync_all()["sources"]["custom-json"]
    assert "超出授权导入范围" in result["errors"][0]["error"]
    assert not archive.search("另一段会话")["results"]
    assert archive.source_status()["custom-json"]["messages"] == 2
    dump(live, data[:3] + extra)
    assert archive.sync_all()["sources"]["custom-json"]["messages_new"] == 1


ZCODE_FIXTURE_ADAPTER = """
import json, sqlite3, sys
from pathlib import Path

req = json.load(sys.stdin)
root = Path(req["root"])
scope = req["scope"]
with sqlite3.connect(root.as_uri() + "?mode=ro", uri=True) as db:
    db.row_factory = sqlite3.Row
    rows = db.execute('''
        SELECT m.rowid AS rid,m.*,p.data AS part
        FROM message m LEFT JOIN part p ON m.id=p.message_id ORDER BY m.rowid
    ''').fetchall()
allowed = set(scope["session_ids"])
seen = set()
for row in rows:
    meta = json.loads(row["data"])
    part = json.loads(row["part"] or "{}")
    sid = row["session_id"]
    visible = not meta.get("hidden") and part.get("metadata", {}).get("visibility") != "model-only"
    if meta["role"] == "user" and visible and part.get("text") and sid not in seen:
        seen.add(sid)
        if part["text"].startswith(scope["first_user_prefix"]):
            allowed.add(sid)
cursor = req["cursor"]
result = []
for row in rows:
    if row["rid"] <= int(cursor or 0) or row["session_id"] not in allowed:
        continue
    meta = json.loads(row["data"])
    text = json.loads(row["part"] or "{}").get("text", "")
    if meta.get("visibility") == "model-only" or meta.get("semantics", {}).get("origin") == "system":
        continue
    if meta["role"] == "assistant" and not meta.get("finish"):
        break
    cursor = str(row["rid"])
    if text:
        result.append(dict(session_id=row["session_id"], message_id=row["id"],
                           position=row["sequence"], role=meta["role"], text=text, origin=root.name))
print(json.dumps(dict(messages=result, cursor=cursor, more=False)))
"""


@pytest.mark.parametrize(("old_behavior", "failed_stage"), [
    ("defer_system", "zcode-pending"),
    ("skip_empty_reply", "zcode-after"),
    ("accept_later_prefix", "zcode-before"),
    ("ignore_scope_on_live", "live（实际来源探测）"),
])
def test_skill_rejects_zcode_fixture_regressions(archive, tmp_path, old_behavior, failed_stage):
    from shutil import copyfile

    sample = cli(archive, "samples-zcode", tmp_path / "fixed", skill=True)
    paths, expected = sample["roots"], sample["expected"]
    live = tmp_path / "db.sqlite"
    copyfile(paths["after"], live)
    fixture, manifest = tmp_path / "fixture.json", tmp_path / "manifest.json"
    dump(fixture, {"before": paths["before"], "after": paths["after"], "scope": sample["scope"],
                   "expected_before": expected["before"],
                   "expected_added": expected["pending"] + expected["after"]})
    dump(manifest, {"version": 1, "id": "test-zcode", "name": "ZCode", "root": str(live),
                    "script": "zcode.py"})
    candidate = tmp_path / "zcode.py"
    bad = {
        "defer_system": ZCODE_FIXTURE_ADAPTER.replace(
            '    if meta.get("visibility") == "model-only" or meta.get("semantics", {}).get("origin") == "system":',
            '    if meta.get("visibility") != "model-only" and meta["role"] == "assistant" and not text:\n'
            '        break\n'
            '    if meta.get("visibility") == "model-only" or meta.get("semantics", {}).get("origin") == "system":'),
        "skip_empty_reply": ZCODE_FIXTURE_ADAPTER.replace(
            '    if meta["role"] == "assistant" and not meta.get("finish"):',
            '    if not text:\n        cursor = str(row["rid"])\n        continue\n'
            '    if meta["role"] == "assistant" and not meta.get("finish"):'),
        "accept_later_prefix": ZCODE_FIXTURE_ADAPTER.replace(' and sid not in seen', ''),
        "ignore_scope_on_live": ZCODE_FIXTURE_ADAPTER.replace(
            "cursor = req", "if root.parent.name not in {'before', 'pending', 'after'}:\n"
            "    allowed.update(row['session_id'] for row in rows)\n"
            "cursor = req"),
    }
    candidate.write_text(bad[old_behavior], encoding="utf-8")
    error = cli(archive, "register", manifest, "--fixture", fixture, skill=True, ok=False)
    assert failed_stage in error
    assert "test-zcode" not in archive.configured_sources()
    candidate.write_text(ZCODE_FIXTURE_ADAPTER, encoding="utf-8")
    valid = cli(archive, "validate", manifest, "--fixture", fixture, skill=True)
    assert valid["checks"] == {"zcode_fixed": 4, "first": 2, "added": 2, "live_preview": 4}


def test_faults_do_not_block_other_sources_or_advance_cursor(archive, tmp_path, monkeypatch):
    manifest, fixture, live, data, extra = json_source(tmp_path / "first")
    second = json_source(tmp_path / "second", "second-json")
    registry.configure(archive, manifest, fixture, register=True)
    registry.configure(archive, second[0], second[1], register=True)
    assert archive.sync_all()["messages_new"] == 6
    dump(live, data + extra)
    mode = live.with_name("mode")

    original = plugin.execute
    monkeypatch.setattr(plugin, "execute", lambda *args: original(*args, timeout=1.5))
    with TestClient(create_app(archive, auto_sync=False)) as web:
        for n, (fault, reason) in enumerate((("hang", "超时"), ("crash", "异常退出"),
                                              ("overflow", "超过上限"), ("bad", "无效消息位置"),
                                              ("conflict", "同一消息身份"))):
            event = {"event": f"new-{n}", "thread": "alpha", "ordinal": 4 + n, "author": "user", "body": f"独立来源 {n}"}
            second[3].append(event)
            dump(second[2], second[3])
            mode.write_text(fault)
            web.post("/api/sync")
            assert web.post("/api/search", json={"query": "白鹭验收"}).status_code == 200
            eventually(lambda: not web.get("/api/status").json()["sync"]["running"])
            status = web.get("/api/status").json()["sync"]["sources"]
            assert reason in status["custom-json"]["last_result"]["errors"][0]["error"]
            assert status["custom-json"]["messages"] == 3
            assert status["second-json"]["messages"] == 4 + n
        mode.unlink()
        assert web.post("/api/sync?source=custom-json&wait=true").json()["result"]["messages_new"] == 1
        assert web.post("/api/sync?source=custom-json&wait=true").json()["result"]["messages_new"] == 0


def test_source_controls_compete_for_one_job_and_preserve_archive(archive, tmp_path):
    manifest, fixture, live, data, extra = json_source(tmp_path)
    registry.configure(archive, manifest, fixture, register=True)
    assert archive.sync_all()["messages_new"] == 3
    archive.set_settings(sync_paused=True)
    status = cli(archive, "maintenance", "status", "--source", "custom-json")
    assert status["sync"]["paused"]
    dump(live, data + extra)
    live.with_name("mode").write_text("slow")
    with ThreadPoolExecutor() as pool:
        first = pool.submit(cli, archive, "maintenance", "sync", "--source", "custom-json")
        endpoint = running_service(archive)
        eventually(lambda: _request(endpoint, "/api/status")["sync"]["running"])
        assert _request(endpoint, "/api/sync?source=custom-json", method="POST")["started"] is False
        mcp = create_mcp(archive)
        response = asyncio.run(mcp.call_tool("manage_sync", {"action": "sync", "source": "custom-json"}))
        results = [first.result(timeout=10), json.loads(response[0].text)]
    assert [result["started"] for result in results] == [True, False]
    assert [r["result"]["sources"]["custom-json"]["batch"] for r in results] == [2, 2]
    assert cli(archive, "source", "disable", "custom-json")["enabled"] is False
    assert "已停用" in cli(archive, "maintenance", "sync", "--source", "custom-json", ok=False)
    assert cli(archive, "maintenance", "sync")["result"]["sources"]["custom-json"]["reason"] == "来源已停用"
    assert archive.search("白鹭验收")["results"]
    revision = registry.batches(archive, "custom-json")[0]
    code = manifest.with_name("adapter.py")
    code.write_text(JSON_ADAPTER + "\n# verified update\n")
    replacement = registry.configure(archive, manifest, fixture, register=True)
    assert replacement["revision"] != revision["revision"] and not replacement["enabled"]
    assert registry.rollback(archive, "custom-json")["revision"] == revision["revision"]
    assert registry.purge_batch(archive, "custom-json", revision["id"])["messages_deleted"] == 1
    assert archive.source_status()["custom-json"]["messages"] == 3
    assert cli(archive, "source", "enable", "custom-json")["enabled"]
    assert cli(archive, "maintenance", "sync", "--source", "custom-json")["result"]["messages_new"] == 1
    assert archive.source_status()["custom-json"]["messages"] == 4
    assert archive.get_settings()["sync_paused"]


def test_sqlite_and_json_sources_use_same_protocol(archive, tmp_path):
    manifest, fixture, *_ = json_source(tmp_path / "json")
    registry.configure(archive, manifest, fixture, register=True)
    data = [
        (1, "alpha", "user", "岸线入口"),
        (2, "alpha", "tool", "隐蔽内部数据"),
        (3, "beta", "assistant", "SQLite 验收"),
        (4, "beta", "user", "SQLite 追问"),
    ]
    before, after, live = [tmp_path / part / "chats.db" for part in ("before", "after", "live")]
    for path, rows in ((before, data[:-1]), (after, data), (live, data[:-1])):
        path.parent.mkdir()
        with sqlite3.connect(path) as origin:
            origin.execute("CREATE TABLE events(seq INTEGER PRIMARY KEY, chat TEXT, speaker TEXT, body TEXT)")
            origin.executemany("INSERT INTO events VALUES(?,?,?,?)", rows)
    fixture = tmp_path / "sqlite-fixture.json"
    dump(fixture, {"before": str(before), "after": str(after), "scope": {"kind": "all"}, "expected_before": [
        dict(session_id="alpha", message_id="1", position=1, role="user", text="岸线入口", origin="chats.db"),
        dict(session_id="beta", message_id="3", position=3, role="assistant", text="SQLite 验收", origin="chats.db"),
    ], "expected_added": [
        dict(session_id="beta", message_id="4", position=4, role="user", text="SQLite 追问", origin="chats.db"),
    ]})
    manifest = tmp_path / "sqlite.json"
    (tmp_path / "sqlite.py").write_text(SQLITE_ADAPTER)
    dump(manifest, {"version": 1, "root": str(live), "script": "sqlite.py",
                    "name": "SQLite 来源", "id": "sample-sqlite"})
    cli(archive, "register", manifest, "--fixture", fixture, skill=True)
    one = cli(archive, "maintenance", "sync")
    assert one["result"]["sources"]["sample-sqlite"]["messages_new"] == 2
    assert one["result"]["sources"]["custom-json"]["messages_new"] == 3
    with sqlite3.connect(live) as origin:
        origin.execute("INSERT INTO events VALUES(?,?,?,?)", data[-1])
    assert cli(archive, "maintenance", "sync", "--source", "sample-sqlite")["result"]["messages_new"] == 1
    hit = cli(archive, "search", "SQLite 追问", "--local")["results"][0]
    assert [m["text"] for m in cli(archive, "read", hit["id"])["messages"]] == ["SQLite 验收", "SQLite 追问"]


def test_local_plugin_does_not_block_old_hub_upload(archive, tmp_path, monkeypatch):
    import smm_local.federation as federation
    from smm_hub.hub import create_hub

    manifest, fixture, *_ = json_source(tmp_path)
    registry.configure(archive, manifest, fixture, register=True)
    assert archive.sync_all()["messages_new"] == 3
    codex = Path(archive.get_settings()["codex_root"])
    rows = [
        {"type": "session_meta", "payload": {"id": "builtin-local"}},
        {"type": "response_item", "ordinal": 1, "payload": {
            "type": "message", "id": "original-1", "role": "user",
            "content": [{"type": "input_text", "text": "旧汇总风车回归"}]}},
    ]
    (codex / "session.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
    assert archive.sync_all()["messages_new"] == 1
    hub_archive = Archive(tmp_path / "hub.sqlite3")
    token = "local-test-token-" + "a" * 32
    config = {"device_id": "a" * 32, "device_name": "试用节点", "token": token,
              "address": "http://127.0.0.1"}
    monkeypatch.setattr(federation, "hub_config", lambda db: config)

    with TestClient(create_hub(hub_archive, token)) as hub:
        def request(_config, route, data=None):
            headers = {"Authorization": f"Bearer {token}"}
            response = (hub.get("/v1" + route, headers=headers) if data is None
                        else hub.post("/v1" + route, json=data, headers=headers))
            assert response.status_code == 200, response.text
            return response.json()

        monkeypatch.setattr(federation, "_request", request)
        assert federation.push_pending(archive)["uploaded"] == 1
        assert federation.push_pending(archive)["uploaded"] == 0
        assert federation.search_archive(archive, "旧汇总风车回归")["results"][0]["source"] == "codex"
        assert not federation.search_archive(archive, "白鹭验收", current_source="custom-json",
                                             current_session_id="alpha")["results"]
        local = federation.search_archive(archive, "白鹭验收", local=True)
        assert local["archive_scope"] == "local"
        assert local["results"][0]["source"] == "custom-json"


def test_source_registered_during_full_sync_gets_its_own_job(archive, tmp_path):
    first = json_source(tmp_path / "first")
    second = json_source(tmp_path / "second", "late-json")
    registry.configure(archive, first[0], first[1], register=True)
    first[2].with_name("mode").write_text("slow")
    with TestClient(create_app(archive, auto_sync=False)) as web:
        started = web.post("/api/sync").json()
        assert started["started"]
        registry.configure(archive, second[0], second[1], register=True)
        reply = web.post("/api/sync?source=late-json&wait=true").json()
        assert reply["result"]["sources"]["late-json"]["messages_new"] == 3
        assert "custom-json" not in reply["result"]["sources"]


def test_disable_during_plugin_execution_prevents_batch_commit(archive, tmp_path):
    manifest, fixture, live, data, extra = json_source(tmp_path)
    registry.configure(archive, manifest, fixture, register=True)
    archive.sync_all()
    dump(live, data + extra)
    live.with_name("mode").write_text("slow")
    with TestClient(create_app(archive, auto_sync=False)) as web:
        assert web.post("/api/sync?source=custom-json").json()["started"]
        response = web.put("/api/sources/custom-json/enabled", json={"enabled": False})
        assert response.json()["enabled"] is False
        eventually(lambda: not web.get("/api/status").json()["sync"]["running"])
        assert archive.source_status()["custom-json"]["messages"] == 3
        assert archive.search("白鹭验收")["results"]
        web.put("/api/sources/custom-json/enabled", json={"enabled": True})
        assert web.post("/api/sync?source=custom-json&wait=true").json()["result"]["messages_new"] == 1


def test_candidate_with_incorrect_live_origin_cannot_register(archive, tmp_path):
    manifest, fixture, live, *_ = json_source(tmp_path)
    manifest.with_name("adapter.py").write_text(JSON_ADAPTER.replace(
        "origin=root.name", 'origin="other.json" if root.parent.name == "live" else root.name'
    ))
    error = cli(archive, "register", manifest, "--fixture", fixture, skill=True, ok=False)
    assert "超出已注册范围" in error
    assert "custom-json" not in archive.configured_sources()


def test_purged_conversation_id_is_reserved_for_the_original_source_session(archive, tmp_path):
    manifest, fixture, live, data, extra = json_source(tmp_path)
    registry.configure(archive, manifest, fixture, register=True)
    result = archive.sync_all()["sources"]["custom-json"]
    old_id = archive.search("白鹭验收")["results"][0]["id"]
    archive.set_source_enabled("custom-json", False)
    assert registry.purge_batch(archive, "custom-json", result["batch"])["messages_deleted"] == 3
    with pytest.raises(ValueError, match="对话不存在"):
        archive.read(old_id)
    assert not archive.search("白鹭验收")["results"]
    archive.set_source_enabled("custom-json", True)
    dump(live, [{"thread":"new", "event":"009", "ordinal":0, "author":"user", "body":"全新白桦会话"}])
    assert archive.sync_all()["messages_new"] == 1
    assert archive.search("全新白桦会话")["results"][0]["id"] != old_id
    corrected = tmp_path / "corrected-project"
    data[0]["cwd"] = str(corrected)
    dump(live, [{"thread":"new", "event":"009", "ordinal":0, "author":"user", "body":"全新白桦会话"}] + data + extra)
    assert archive.sync_all()["messages_new"] == 4
    assert archive.search("白鹭验收")["results"][0]["id"] == old_id
    assert archive.read(old_id)["cwd"] == str(corrected)
