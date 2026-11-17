# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SubLang International <https://sublang.ai>

import asyncio
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from smm_local.core import Archive
from smm_local.service import running_service, stop_on_demand


def cli(db, *args):
    process = subprocess.run([sys.executable, "-m", "smm_local.cli", "--db", str(db), *args],
                             capture_output=True, check=True, timeout=30)
    return json.loads(process.stdout)


def eventually(check, seconds=20):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if result := check():
            return result
        time.sleep(0.15)
    pytest.fail("等待同步超时")


def record_codex(root, session, messages, *, cwd=None):
    events = [{"type": "session_meta", "payload": {"id": session, "cwd": str(cwd if cwd is not None else root)}}]
    events += [{"type": "response_item", "ordinal": i, "payload": {
        "type": "message", **({"id": key} if key else {}), "role": "user",
        "content": [{"type": "input_text", "text": body}]}}
        for i, key, body in messages]
    (root / f"{session}.jsonl").write_text("".join(json.dumps(row) + "\n" for row in events))


def test_federation_offline_recovery_dedup_and_provenance(tmp_path, monkeypatch):
    monkeypatch.setenv("SMM_SERVICE_PORT", "0")
    monkeypatch.setenv("PYTHONPATH", str(Path(__file__).resolve().parents[1] / "src"))
    token = "isolated-test-only-" + "1" * 40
    token_file = tmp_path / "hub-token"
    token_file.write_text(token)
    hub_db = tmp_path / "hub.sqlite3"
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    address = f"http://127.0.0.1:{port}"
    headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}

    def hub_call(route, payload=None):
        req = Request(address + "/v1/" + route, headers=headers,
                      data=json.dumps(payload).encode() if payload is not None else None)
        with urlopen(req, timeout=3) as response:
            return json.load(response)

    def start_hub():
        process = subprocess.Popen(
            [sys.executable, "-m", "smm_hub.cli", "--db", str(hub_db), "serve-hub",
             "--port", str(port), "--token-file", str(token_file)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

        def ready():
            if process.poll() is not None:
                pytest.fail(f"汇总服务退出：{process.returncode}")
            try:
                return hub_call("info")
            except (URLError, TimeoutError):
                return False
        try:
            eventually(ready, 8)
        except BaseException:
            process.terminate()
            process.wait(timeout=10)
            raise
        return process

    def client(name):
        root = tmp_path / name
        root.mkdir()
        codex, claude = root / "codex", root / "claude"
        codex.mkdir()
        claude.mkdir()
        db = Archive(root / "archive.sqlite3")
        db.set_settings(codex_root=str(codex), claude_root=str(claude), sync_interval_seconds=10)
        return db, codex, claude

    a, a_codex, a_claude = client("a")
    b, b_codex, _ = client("b")
    record_codex(a_codex, "duplicate-session", [(11, "u1", "Northstar amber")])
    record_codex(b_codex, "duplicate-session", [(99, "u1", "Northstar amber")])
    record_codex(b_codex, "only-b", [(22, "u2", "Northstar remote")])
    record_codex(a_codex, "offset-session", [(4, None, "Snowfinch first"),
                                            (9, None, "Snowfinch second")])
    record_codex(b_codex, "offset-session", [(98, None, "Snowfinch second")])

    async def mcp_call(db, tool, arguments):
        params = StdioServerParameters(command=sys.executable, args=["-m", "smm_local.mcp_server",
                                      "--db", str(db.db_path)], env=dict(os.environ))
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                response = await session.call_tool(tool, arguments)
                assert not response.isError, response
                return json.loads(response.content[0].text)

    hub = start_hub()
    try:
        with pytest.raises(HTTPError, match="401"):
            urlopen(address + "/v1/info", timeout=3)
        missing = cli(a.db_path, "configure-hub", address, "Laptop A")
        assert missing["needs_token"] and not missing["configured"]
        # B uploads a partial copy before A sends the complete conversation.
        assert cli(b.db_path, "configure-hub", address, "Desktop B", "--token-file", str(token_file))["connected"]
        cli(b.db_path, "maintenance", "sync")
        configured = asyncio.run(mcp_call(a, "configure_hub", {
            "address": address, "device_name": "Laptop A", "token_file": str(token_file),
        }))
        assert configured["connected"] and configured["device_name"] == "Laptop A"
        config_path = a.db_path.with_suffix(".sqlite3.hub.json")
        before = json.loads(config_path.read_text())
        assert before["address"] == address and before["device_name"] == "Laptop A"
        assert cli(a.db_path, "configure-hub", address, "Laptop A")["connected"]
        assert json.loads(config_path.read_text())["device_id"] == before["device_id"]
        cli(a.db_path, "maintenance", "sync")
        online = cli(a.db_path, "search", "Northstar")
        assert online["archive_scope"] == "hub"
        assert {r["source_session_id"] for r in online["results"]} == {"duplicate-session", "only-b"}
        duplicate = next(r for r in online["results"] if r["source_session_id"] == "duplicate-session")
        matches = duplicate["matched_messages"]
        assert len(matches) == 1
        assert {(o["device_name"], o["source_position"]) for o in matches[0]["origins"]} == {
            ("Laptop A", 11), ("Desktop B", 99),
        }
        assert len({o["device_id"] for o in matches[0]["origins"]}) == 2
        offsets = cli(a.db_path, "search", "Snowfinch")
        offset_hit, = offsets["results"]
        assert offset_hit["source_session_id"] == "offset-session"
        original = cli(b.db_path, "read", str(offset_hit["id"]), "--hub-id", offsets["hub_id"])
        assert [m["text"] for m in original["messages"]] == ["Snowfinch first", "Snowfinch second"]
        last = original["messages"][1]
        assert {o["source_position"] for o in last["origins"]} == {9, 98}
        match_id = next(m["hub_message_id"] for m in offset_hit["matched_messages"]
                        if m["text"] == "Snowfinch second")
        exact = cli(b.db_path, "read", str(offset_hit["id"]), "--hub-id", offsets["hub_id"],
                    "--hub-message-id", str(match_id))
        assert exact["messages"] == [last]
        hub.terminate()
        hub.wait(timeout=10)
        record_codex(a_codex, "duplicate-session", [(11, "u1", "Northstar amber"),
                                                   (33, "u3", "Northstar offline codex")])
        (a_claude / "claude.jsonl").write_text(json.dumps({
            "type": "user", "sessionId": "duplicate-session", "uuid": "c1",
            "cwd": str(a_claude), "message": {"role": "user", "content": "Northstar offline claude"}
        }) + "\n")
        result = cli(a.db_path, "maintenance", "sync")
        assert result["result"]["hub"]["pending"]
        with a.connect() as con:
            # Simulate a committed upload whose acknowledgement was not saved locally.
            con.execute("DELETE FROM settings WHERE key LIKE 'hub_cursor:%'")
        project = a.resolve_project(str(a_codex))["id"]
        offline = cli(a.db_path, "search", "Northstar", "--scope", "project", "--project-id", str(project))
        assert offline["archive_scope"] == "local" and offline["fallback_reason"]
        assert {r["source"] for r in offline["results"]} == {"codex", "claude-code"}
        assert {r["source_session_id"] for r in offline["results"]} == {"duplicate-session"}
        assert all(r["origins"][0]["device_name"] == "Laptop A" for r in offline["results"])
        # No explicit sync after reconnect; the periodic local service retries.
        hub = start_hub()
        caught_up = eventually(lambda: (
            hits if any(r["source"] == "claude-code" for r in hits["results"]) else False
        ) if (hits := hub_call("search", {"query": "Northstar"})) else False)
        assert caught_up["hub_id"] == online["hub_id"]
        restored = asyncio.run(mcp_call(b, "search_conversations", {"query": "Northstar"}))
        assert restored["archive_scope"] == "hub"
        by_session = {(r["source"], r["source_session_id"]): r for r in restored["results"]}
        assert set(by_session) == {("codex", "duplicate-session"), ("codex", "only-b"),
                                   ("claude-code", "duplicate-session")}
        assert by_session["codex", "only-b"]["matched_messages"][0]["origins"][0]["device_name"] == "Desktop B"
        claude_hit = by_session["claude-code", "duplicate-session"]
        claude_message = claude_hit["matched_messages"][0]
        assert [(o["device_name"], o["source_position"]) for o in claude_message["origins"]] == [("Laptop A", 0)]
        full = asyncio.run(mcp_call(b, "read_conversation", {
            "conversation_id": by_session["codex", "duplicate-session"]["id"], "hub_id": restored["hub_id"],
        }))
        assert full["source_session_id"] == "duplicate-session" and full["source"] == "codex"
        assert len(full["messages"]) == 2
        newer = next(m for m in full["messages"] if m["text"] == "Northstar offline codex")
        assert [(o["device_name"], o["source_position"]) for o in newer["origins"]] == [("Laptop A", 33)]
        assert running_service(a)
    finally:
        for db in (a, b):
            stop_on_demand(db)
        if hub.poll() is None:
            hub.terminate()
            hub.wait(timeout=10)


def test_project_links_filter_before_ranking_and_follow_only_one_hop(tmp_path):
    from fastapi.testclient import TestClient
    from smm_hub.hub import create_hub

    token = "t" * 40
    with TestClient(create_hub(Archive(tmp_path / "hub.sqlite3"), token),
                    headers={"Authorization": "Bearer " + token}) as hub:
        info = hub.get("/v1/info").json()
        assert "projects" in info.get("capabilities", [])
        for index, label in enumerate(("alpha", "bravo", "charlie", "delta"), 1):
            payload = {
                "hub_id": info["hub_id"], "device_id": f"{index:032x}", "device_name": label,
                "records": [{"source": "codex", "source_session_id": label, "started_at": None,
                             "source_key": label, "position": 0, "source_order": 1, "timestamp": None,
                             "role": "user", "text": f"asteroid {label}"}],
            }
            assert hub.post("/v1/upload", json=payload).status_code == 200
            assert hub.post("/v1/project-metadata", json={
                **{k: payload[k] for k in ("hub_id", "device_id", "device_name")},
                "projects": [{"id": 1, "name": "Same name"}],
                "memberships": [{"source": "codex", "source_session_id": label, "project_id": 1}],
            }).status_code == 200

        from smm_hub.projects import HubProjects

        manager = HubProjects(Archive(tmp_path / "hub.sqlite3"))
        projects = {p["device_name"]: p["id"] for p in manager.list()}
        a, b, c, d = (projects[label] for label in ("alpha", "bravo", "charlie", "delta"))
        for one, other in [(a, b), (b, a), (a, c), (b, d)]:
            manager.link(one, other)
        assert len(manager.links()) == 3

        def check(label, expected):
            result = hub.post("/v1/search", json={
                "query": "asteroid", "device_id": f"{label:032x}", "project_id": 1, "limit": len(expected),
            })
            assert result.status_code == 200, result.text
            data = result.json()
            assert {p["id"] for p in data["effective_projects"]} == expected
            assert {hit["project_id"] for hit in data["results"]} == expected

        check(1, {a, b, c})
        check(2, {a, b, d})
        manager.link(c, a, linked=False)
        check(1, {a, b})
        assert len(hub.post("/v1/search", json={"query": "asteroid"}).json()["results"]) == 4


def test_project_request_reports_actual_scope_before_any_links(tmp_path):
    from fastapi.testclient import TestClient
    from smm_hub.hub import create_hub

    token = "s" * 40
    device = "0" * 32
    with TestClient(create_hub(Archive(tmp_path / "hub.sqlite3"), token),
                    headers={"Authorization": "Bearer " + token}) as hub:
        info = hub.get("/v1/info").json()
        if "projects" in info.get("capabilities", []):
            result = hub.post("/v1/project-metadata", json={
                "hub_id": info["hub_id"], "device_id": device, "device_name": "Laptop",
                "projects": [{"id": 1, "name": "Empty"}], "memberships": [],
            })
            assert result.status_code == 200
        result = hub.post("/v1/search", json={"query": "evidence", "device_id": device, "project_id": 1})
        assert result.status_code == 200
        assert result.json()["scope"] == "project"
        assert [p["name"] for p in result.json()["effective_projects"]] == ["Empty"]


def test_vibeinsight_configuration_has_managed_hub_entry_point():
    command = [sys.executable, "-m", "smm_hub.cli", "hub", "vibeinsight", "--help"]
    result = subprocess.run(command, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert "configure" in result.stdout and "status" in result.stdout
