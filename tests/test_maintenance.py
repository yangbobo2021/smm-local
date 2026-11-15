# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SubLang International <https://sublang.ai>

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.request import urlopen

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from smm_local.core import Archive
from smm_local.service import maintain, running_service, stop_on_demand


def test_agent_maintenance_starts_reuses_and_preserves_pause(tmp_path, monkeypatch):
    db = Archive(tmp_path / "archive.sqlite3")
    source = tmp_path / "codex-sessions"
    source.mkdir()
    claude = tmp_path / "claude-projects"
    claude.mkdir()
    db.set_settings(codex_root=str(source), claude_root=str(claude), sync_interval_seconds=10)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("SMM_SERVICE_PORT", "0")
    manifest = tmp_path / ".local/share/smm-local/install.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"db_path": str(db.db_path)}), encoding="utf-8")
    root = Path(__file__).resolve().parents[1]
    subprocess.run([sys.executable, str(root / "scripts/install_skill.py"), "--home", str(tmp_path)],
                   check=True, capture_output=True)
    installed = [
        (tmp_path / f".{agent}/skills/smm-search/SKILL.md").read_bytes()
        for agent in ("codex", "claude")
    ]
    assert installed[0] == installed[1]

    def write_conversation(name):
        records = [
            {"type": "session_meta", "payload": {"id": name, "cwd": str(tmp_path)}},
            {"type": "response_item", "payload": {"type": "message", "role": "user",
             "content": [{"type": "input_text", "text": f"同步验收 {name}"}]}},
        ]
        (source / f"{name}.jsonl").write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records), encoding="utf-8"
        )

    async def call(action, agent="codex", *, tool="manage_sync"):
        alternate_db = tmp_path / f"{agent}-private.sqlite3"
        params = StdioServerParameters(command=sys.executable, args=["-m", "smm_local.mcp_server"],
                                       env={**os.environ, "SMM_DB": str(alternate_db)})
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer) as client:
                await client.initialize()
                arguments = {"action": action} if tool == "manage_sync" else {"query": action}
                response = await client.call_tool(tool, arguments)
                assert not response.isError
                data = (response.structuredContent if tool == "manage_sync" else None)
                if data is None:
                    data = json.loads(response.content[0].text)
                assert data and not data.get("error"), data
                assert not alternate_db.exists()
                return data

    async def exercise():
        assert await call("pause") == {"service_running": False, "paused": True}
        write_conversation("first")
        first, second = await asyncio.gather(call("status"), call("status", "claude"))
        assert first["url"] == second["url"]
        assert first["sync"]["paused"] and first["conversations"] == 0
        assert first["sync"]["sources"]["claude-code"]["available"]
        original = running_service(db)
        with urlopen(first["url"], timeout=5) as page:
            assert "自动同步已暂停" in page.read().decode()
        opened_urls = []
        monkeypatch.setattr("smm_local.service.webbrowser.open", lambda url: not opened_urls.append(url))
        assert maintain(db, "open")["opened"]
        assert opened_urls == [first["url"]]

        sync = await call("sync", "claude")
        assert sync["result"]["conversations_new"] == 1
        for agent in ("codex", "claude"):
            search = await call("first", agent, tool="search_conversations")
            assert search["results"][0]["source_session_id"] == "first"
        assert running_service(db) == original
        stop_on_demand(db)
        write_conversation("second")
        restarted = await call("status")
        assert restarted["sync"]["paused"] and not restarted["sync"]["running"]
        assert restarted["conversations"] == 1
        assert restarted["sync"]["last_result"]["finished_at"] == sync["result"]["finished_at"]
        assert running_service(db) != original
        assert not (await call("resume", "claude"))["paused"]
        for _ in range(80):
            if db.status()["conversations"] == 2:
                break
            await asyncio.sleep(0.05)
        assert db.status()["conversations"] == 2
        assert not (await call("status"))["sync"]["paused"]
        write_conversation("third")
        for _ in range(120):
            if db.status()["conversations"] == 3:
                break
            await asyncio.sleep(0.1)
        assert db.status()["conversations"] == 3

    try:
        asyncio.run(exercise())
    finally:
        stop_on_demand(db)
