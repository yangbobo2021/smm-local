import json
import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from smm_local.api import create_app
from smm_local.core import Archive
from smm_local.mcp_server import create_mcp


def line(kind, payload, ordinal, timestamp="2026-10-29T08:00:00Z"):
    return json.dumps({"type": kind, "ordinal": ordinal, "timestamp": timestamp, "payload": payload}, ensure_ascii=False) + "\n"


def session(path: Path, sid: str, cwd: Path, user: str, assistant: str) -> None:
    path.write_text(
        line("session_meta", {"id": sid, "cwd": str(cwd)}, 1)
        + line("response_item", {"type": "message", "id": sid+"-u", "role": "user", "content": [{"type": "input_text", "text": user}]}, 2)
        + line("event_msg", {"type": "item_completed", "item": {"type": "UserMessage"}}, 3)
        + line("response_item", {"type": "message", "id": sid+"-a", "role": "assistant", "content": [{"type": "output_text", "text": assistant}]}, 4),
        encoding="utf-8",
    )


def test_incremental_copy_survives_deletion_and_partial_line(tmp_path):
    root = tmp_path / "sessions"
    root.mkdir()
    file = root / "one.jsonl"
    session(file, "s1", tmp_path / "ProjectA", "晨星上线失败", "先恢复数据库快照")
    db = Archive(tmp_path / "archive.sqlite3")
    first = db.sync_codex(root)
    assert (first["conversations_new"], first["messages_new"]) == (1, 2)
    assert db.sync_codex(root)["messages_new"] == 0
    with file.open("a", encoding="utf-8") as stream:
        stream.write(line("response_item", {"type": "message", "id": "s1-u2", "role": "user", "content": [{"type": "input_text", "text": "回滚后检查索引"}]}, 5))
        stream.write('{"type":"response_item"')
    partial = db.sync_codex(root)
    assert partial["messages_new"] == 1
    assert partial["errors"]
    with file.open("a", encoding="utf-8") as stream:
        stream.write(',"ordinal":6,"payload":{"type":"message","id":"s1-a2","role":"assistant","content":[{"type":"output_text","text":"索引已经恢复"}]}}\n')
    assert db.sync_codex(root)["messages_new"] == 1
    file.unlink()
    assert len(db.read(1)["messages"]) == 4
    assert db.search("晨星 恢复")["results"][0]["source_session_id"] == "s1"


def test_long_conversation_preview_keeps_later_decision_and_its_question(tmp_path):
    root = tmp_path / "sessions"
    root.mkdir()
    path = root / "long.jsonl"
    content = [line("session_meta", {"id": "long", "cwd": str(tmp_path / "Project")}, 1)]
    for turn in range(61):
        user = "BM25 规模 检索 的初步想法" if turn < 12 else f"第 {turn} 次普通进度"
        answer = "先比较文档分段方案" if turn < 12 else "记录完成"
        if turn == 60:
            user = "BM25 规模 检索 的最终方向是什么？"
            answer = "最终决定优先按项目过滤无关信息。"
        content.append(line("response_item", {"type": "message", "id": f"u-{turn}", "role": "user", "content": [{"type": "input_text", "text": user}]}, turn * 2 + 2))
        content.append(line("response_item", {"type": "message", "id": f"a-{turn}", "role": "assistant", "content": [{"type": "output_text", "text": answer}]}, turn * 2 + 3))
    path.write_text("".join(content), encoding="utf-8")
    db = Archive(tmp_path / "archive.sqlite3")
    assert db.sync_codex(root)["messages_new"] == 122
    result = db.search("BM25 规模 检索")["results"][0]
    positions = [m["position"] for m in result["matched_messages"]]
    assert result["source_session_id"] == "long"
    assert positions == sorted(positions)
    assert 122 in positions and 123 in positions
    assert any("最终决定优先按项目过滤" in m["text"] for m in result["matched_messages"])


def test_compact_search_preserves_rank_and_can_read_complete_message(tmp_path):
    root = tmp_path / "sessions"
    root.mkdir()
    evidence = "晨星上线失败后，先停写，再从昨日快照恢复。"
    long_reply = "普通诊断记录。" * 300 + evidence + "恢复后核对索引。" * 100
    session(root / "long.jsonl", "long", tmp_path / "Project", "晨星上线如何恢复？", long_reply)
    session(root / "short.jsonl", "short", tmp_path / "Project", "晨星上线进度", "正在检查")
    db = Archive(tmp_path / "archive.sqlite3")
    db.sync_codex(root)
    full = db.search("晨星 上线 恢复")
    compact = db.search("晨星 上线 恢复", preview_chars=600)
    assert [r["id"] for r in compact["results"]] == [r["id"] for r in full["results"]]
    for old, new in zip(full["results"], compact["results"]):
        assert old["bm25_score"] == new["bm25_score"]
        assert [m["position"] for m in old["matched_messages"]] == [m["position"] for m in new["matched_messages"]]
        for message in new["matched_messages"]:
            assert "text" not in message
            assert len(message["preview"]) <= 600
            if message["preview_truncated"]:
                assert message["text_chars"] > 600
                assert db.read(new["id"], start=message["position"], end=message["position"])["messages"][0]["text"] == next(
                    original["text"] for original in old["matched_messages"] if original["position"] == message["position"]
                )
    assert any("晨星上线失败后" in m["preview"] for r in compact["results"] for m in r["matched_messages"])


def test_mcp_keeps_full_default_and_allows_compact_configuration(tmp_path, monkeypatch):
    root = tmp_path / "sessions"
    root.mkdir()
    session(root / "one.jsonl", "one", tmp_path / "Project", "晨星恢复方案？", "先检查。" * 300 + "晨星从快照恢复。")
    db = Archive(tmp_path / "archive.sqlite3")
    db.sync_codex(root)
    server = create_mcp(db)
    monkeypatch.delenv("SMM_SEARCH_PREVIEW_CHARS", raising=False)
    full = json.loads(asyncio.run(server.call_tool("search_conversations", {"query": "晨星 恢复"}))[0][0].text)
    monkeypatch.setenv("SMM_SEARCH_PREVIEW_CHARS", "600")
    compact = json.loads(asyncio.run(server.call_tool("search_conversations", {"query": "晨星 恢复"}))[0][0].text)
    assert compact["results"][0]["id"] == full["results"][0]["id"]
    assert "text" not in compact["results"][0]["matched_messages"][0]
    assert "text" in full["results"][0]["matched_messages"][0]


def test_project_mapping_direct_links_and_current_exclusion(tmp_path):
    root = tmp_path / "sessions"
    root.mkdir()
    for sid, project, text in [("a", "Alpha", "部署晨星服务"), ("b", "Beta", "晨星联动测试"), ("c", "Gamma", "晨星远端记录")]:
        session(root / f"{sid}.jsonl", sid, tmp_path / project, text, "记录完成")
    db = Archive(tmp_path / "db.sqlite3")
    db.sync_codex(root)
    projects = {p["name"]: p["id"] for p in db.projects()}
    a,b,c = (projects[x] for x in ("Alpha", "Beta", "Gamma"))
    db.link_projects(a,b)
    db.link_projects(b,c)
    assert set(db.effective_projects(a)) == {a,b}
    result = db.search("晨星", scope="project", project_id=a)
    assert {r["source_session_id"] for r in result["results"]} == {"a", "b"}
    assert {r["source_session_id"] for r in db.search("晨星", scope="all")["results"]} == {"a", "b", "c"}
    assert {r["source_session_id"] for r in db.search("晨星", scope="project", project_id=a, current_session_id="a")["results"]} == {"b"}
    assert {r["source_session_id"] for r in db.search("晨星", scope="project", project_id=a, current_session_id="a", include_current=True)["results"]} == {"a", "b"}
    db.map_path(str(tmp_path / "Beta"), a)
    assert {r["source_session_id"] for r in db.search("晨星", scope="project", project_id=a)["results"]} == {"a", "b"}
    assert db.resolve_project(str(tmp_path / "Beta" / "src"))["id"] == a
    db.link_projects(a,b,False)
    assert db.effective_projects(a) == [a]
    db.merge_projects(b,a)
    assert db.resolve_project(str(tmp_path / "Beta"))["id"] == a
    assert b not in {p["id"] for p in db.projects()}
    assert {r["source_session_id"] for r in db.search("晨星", scope="project", project_id=a)["results"]} == {"a", "b", "c"}


def test_parent_path_mapping_applies_to_existing_and_future_child_sessions(tmp_path):
    root = tmp_path / "sessions"
    root.mkdir()
    parent = tmp_path / "Product"
    session(root / "old.jsonl", "old", parent / "module", "产品部署记录", "完成")
    db = Archive(tmp_path / "db.sqlite3")
    db.sync_codex(root)
    other = tmp_path / "Other"
    session(root / "other.jsonl", "other", other, "其他记录", "完成")
    db.sync_codex(root)
    target = db.resolve_project(str(other))["id"]
    db.map_path(str(parent), target)
    assert db.resolve_project(str(parent / "module"))["id"] == target
    session(root / "new.jsonl", "new", parent / "new-module", "新增记录", "完成")
    db.sync_codex(root)
    assert db.resolve_project(str(parent / "new-module"))["id"] == target
    assert {r["source_session_id"] for r in db.search("记录", scope="project", project_id=target)["results"]} == {"old", "other", "new"}


def test_web_api_uses_same_archive(tmp_path):
    root = tmp_path / "sessions"
    root.mkdir()
    session(root / "one.jsonl", "web-1", tmp_path / "WebProject", "Web UI 搜索晨星", "已找到原文")
    db = Archive(tmp_path / "db.sqlite3")
    db.sync_codex(root)
    with TestClient(create_app(db, auto_sync=False)) as client:
        assert client.get("/").status_code == 200
        assert "检索测试" in client.get("/").text
        result = client.post("/api/search", json={"query": "晨星", "scope": "all"}).json()
        assert result["results"][0]["source_session_id"] == "web-1"
        assert client.get("/api/conversations/1").json()["messages"][0]["role"] == "user"
        assert client.get("/api/status").json()["conversations"] == 1
        assert client.get("/api/projects").json()[0]["name"] == "WebProject"
        assert "合并同一项目" in client.get("/").text
        assert client.post("/api/search", json={"query": "", "scope": "all"}).status_code == 400


def test_source_file_rewrite_does_not_duplicate(tmp_path):
    root = tmp_path / "sessions"
    root.mkdir()
    path = root / "one.jsonl"
    session(path, "same", tmp_path / "Proj", "项目故障", "检查日志")
    db = Archive(tmp_path / "db.sqlite3")
    db.sync_codex(root)
    original = path.read_text()
    path.write_text(original)
    db.sync_codex(root)
    assert db.status()["messages"] == 2
    assert db.status()["conversations"] == 1


def claude_line(kind, sid, cwd, uuid, content):
    return json.dumps({
        "type": kind, "sessionId": sid, "cwd": str(cwd), "uuid": uuid,
        "timestamp": "2026-10-29T09:00:00Z",
        "message": {"role": kind, "content": content},
    }, ensure_ascii=False) + "\n"


def test_codex_and_claude_share_durable_archive_without_tool_output(tmp_path, monkeypatch):
    codex_root = tmp_path / "codex"
    claude_root = tmp_path / "claude"
    codex_root.mkdir()
    claude_root.mkdir()
    project = tmp_path / "SharedProject"
    session(codex_root / "same.jsonl", "same", project, "晨星项目上线计划", "检查回滚流程")
    claude_file = claude_root / "same.jsonl"
    claude_file.write_text(
        claude_line("user", "same", project, "c-u1", [{"type": "text", "text": "晨星项目值班人是谁？"}])
        + claude_line("assistant", "same", project, "c-a1", [
            {"type": "thinking", "thinking": "SECRET_THINKING_MARKER"},
            {"type": "tool_use", "name": "Read", "input": {"path": "secret"}},
            {"type": "text", "text": "值班人为周宁。"},
        ])
        + claude_line("user", "same", project, "c-tool", [{"type": "tool_result", "content": "SECRET_TOOL_MARKER"}])
        + json.dumps({"type": "user", "sessionId": "same", "cwd": str(project), "uuid": "c-meta", "isMeta": True,
                      "message": {"role": "user", "content": "SECRET_META_MARKER"}}) + "\n"
        + json.dumps({"type": "user", "sessionId": "same", "cwd": str(project), "uuid": "c-compact", "isCompactSummary": True,
                      "message": {"role": "user", "content": "SECRET_COMPACT_MARKER"}}) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("SMM_CODEX_ROOT", str(codex_root))
    monkeypatch.setenv("SMM_CLAUDE_ROOT", str(claude_root))
    db = Archive(tmp_path / "db.sqlite3")
    first = db.sync_all()
    assert first["conversations_new"] == 2
    assert first["messages_new"] == 4
    assert db.sync_all()["messages_new"] == 0
    project_id = db.resolve_project(str(project))["id"]
    both = db.search("晨星", scope="project", project_id=project_id, limit=5)["results"]
    assert {r["source"] for r in both} == {"codex", "claude-code"}
    assert {r["source_session_id"] for r in both} == {"same"}
    assert {r["source"] for r in db.search("晨星", scope="project", project_id=project_id,
                                            current_session_id="same", current_source="codex")["results"]} == {"claude-code"}
    assert not db.search("SECRET_TOOL_MARKER")["results"]
    assert not db.search("SECRET_THINKING_MARKER")["results"]
    assert not db.search("SECRET_META_MARKER")["results"]
    assert not db.search("SECRET_COMPACT_MARKER")["results"]

    with claude_file.open("a", encoding="utf-8") as stream:
        stream.write(claude_line("assistant", "same", project, "c-a2", [{"type": "text", "text": "周宁负责周四。"}]))
        stream.write('{"type":"assistant"')
    partial = db.sync_all()
    assert partial["messages_new"] == 1 and partial["errors"]
    with claude_file.open("a", encoding="utf-8") as stream:
        stream.write(',"uuid":"c-tool2","sessionId":"same","cwd":"'+str(project)+'","timestamp":"2026-10-29T09:01:00Z","message":{"role":"assistant","content":[{"type":"text","text":"交接完成"}]}}\n')
    assert db.sync_all()["messages_new"] == 1
    claude_file.unlink()
    db.sync_all()
    claude = next(r for r in both if r["source"] == "claude-code")
    assert len(db.read(claude["id"])["messages"]) == 4
    assert db.search("周宁", scope="project", project_id=project_id)["results"]


def test_missing_claude_source_does_not_block_codex(tmp_path, monkeypatch):
    codex_root = tmp_path / "codex"
    codex_root.mkdir()
    session(codex_root / "one.jsonl", "s1", tmp_path / "Project", "独立 Codex 来源", "已经导入")
    monkeypatch.setenv("SMM_CODEX_ROOT", str(codex_root))
    monkeypatch.setenv("SMM_CLAUDE_ROOT", str(tmp_path / "missing"))
    db = Archive(tmp_path / "db.sqlite3")
    result = db.sync_all()
    assert result["messages_new"] == 2
    assert result["sources"]["claude-code"]["available"] is False
    assert result["sources"]["codex"]["available"] is True


def test_web_sync_and_source_settings_share_one_archive(tmp_path, monkeypatch):
    codex_root = tmp_path / "codex"
    claude_root = tmp_path / "claude"
    codex_root.mkdir()
    claude_root.mkdir()
    project = tmp_path / "Project"
    session(codex_root / "a.jsonl", "codex-session", project, "青松项目上线安排", "周四执行")
    (claude_root / "b.jsonl").write_text(claude_line("user", "claude-session", project, "u1", "青松项目回滚检查"), encoding="utf-8")
    db = Archive(tmp_path / "archive.sqlite3")
    with TestClient(create_app(db, auto_sync=False)) as client:
        updated = client.put("/api/settings", json={"codex_root": str(codex_root), "claude_root": str(claude_root), "sync_interval_seconds": 30})
        assert updated.status_code == 200
        started = client.post("/api/sync").json()
        assert started["started"] is True
        import time
        for _ in range(100):
            status = client.get("/api/status").json()
            if not status["sync"]["running"] and status["conversations"] == 2:
                break
            time.sleep(.01)
        assert status["conversations"] == 2
        assert status["by_source"]["codex"]["conversations"] == 1
        assert status["by_source"]["claude-code"]["conversations"] == 1
        results = client.post("/api/search", json={"query": "青松", "scope": "all"}).json()["results"]
        assert {r["source"] for r in results} == {"codex", "claude-code"}


def test_codex_injected_context_is_not_archived_and_old_copy_is_cleaned(tmp_path):
    root = tmp_path / "sessions"
    root.mkdir()
    file = root / "one.jsonl"
    file.write_text(
        line("session_meta", {"id": "s", "cwd": str(tmp_path / "Proj")}, 1)
        + line("response_item", {"type": "message", "id": "injected", "role": "user", "content": [{"type": "input_text", "text": "# AGENTS.md instructions for /tmp/Proj\nSECRET_CONTEXT"}]}, 2)
        + line("response_item", {"type": "message", "id": "real", "role": "user", "content": [{"type": "input_text", "text": "晨星上线计划"}]}, 3),
        encoding="utf-8",
    )
    db = Archive(tmp_path / "db.sqlite3")
    assert db.sync_codex(root)["messages_new"] == 1
    with db.connect() as con:
        con.execute("DELETE FROM schema_migrations WHERE name='codex-injected-context-v1'")
        con.execute("INSERT INTO messages(conversation_id,source_key,position,role,text) VALUES(1,'legacy',1,'user',?)", ("<environment_context>SECRET_CONTEXT</environment_context>",))
        db._reindex(con, 1)
    reopened = Archive(tmp_path / "db.sqlite3")
    assert not reopened.search("SECRET_CONTEXT")["results"]
    assert len(reopened.read(1)["messages"]) == 1
    assert reopened.search("晨星")["results"]
