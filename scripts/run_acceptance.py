"""Run a reviewer-readable, isolated end-to-end acceptance flow."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from smm_local.api import create_app
from smm_local.core import Archive


ROOT = Path(__file__).resolve().parents[1]
steps: list[dict] = []


def add(name: str, expected: str, observed: object, okay: bool) -> None:
    steps.append({"step": len(steps) + 1, "name": name, "expected": expected, "observed": observed, "passed": bool(okay)})
    if not okay:
        raise AssertionError(f"{name}: {observed}")


def record(kind: str, payload: dict, ordinal: int) -> str:
    return json.dumps({"type": kind, "ordinal": ordinal, "timestamp": "2026-10-29T08:00:00Z", "payload": payload}, ensure_ascii=False) + "\n"


def make_session(path: Path, sid: str, cwd: Path, text: str) -> None:
    path.write_text(
        record("session_meta", {"id": sid, "cwd": str(cwd)}, 1)
        + record("response_item", {"type": "message", "id": sid+"-u", "role": "user", "content": [{"type": "input_text", "text": text}]}, 2)
        + record("response_item", {"type": "message", "id": sid+"-a", "role": "assistant", "content": [{"type": "output_text", "text": "请检查这项记录的日志。"}]}, 3),
        encoding="utf-8",
    )


async def mcp_search(db_path: Path) -> tuple[list[str], str, bool]:
    params = StdioServerParameters(
        command=str(ROOT / ".venv/bin/smm-mcp"),
        args=["--db", str(db_path)],
        env={**os.environ, "CODEX_THREAD_ID": "alpha-session"},
    )
    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            tools = (await session.list_tools()).tools
            names = [t.name for t in tools]
            readonly = all(t.annotations and t.annotations.readOnlyHint is (t.name not in {"manage_sync", "configure_hub"}) for t in tools)
            response = await session.call_tool("search_conversations", {"query": "晨星", "scope": "all", "limit": 5})
            data = json.loads(response.content[0].text)
            return names, data["excluded_current_session_id"], readonly


def run() -> None:
    with tempfile.TemporaryDirectory(prefix="smm-acceptance-") as temp:
        base = Path(temp)
        source = base / "sessions"
        source.mkdir()
        for sid, name, text in [
            ("alpha-session", "Alpha", "晨星部署失败"),
            ("beta-session", "Beta", "晨星联动排查"),
            ("gamma-session", "Gamma", "晨星其他背景"),
        ]:
            make_session(source / f"{sid}.jsonl", sid, base / name, text)
        db_path = base / "archive.sqlite3"
        db = Archive(db_path)
        result = db.sync_codex(source)
        add("首次持久导入", "3 段对话、6 条可见消息", {"conversations": result["conversations_new"], "messages": result["messages_new"]}, (result["conversations_new"], result["messages_new"]) == (3, 6))

        again = db.sync_codex(source)
        add("重复同步幂等", "新增消息 0 条", again["messages_new"], again["messages_new"] == 0)

        with (source / "alpha-session.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(record("response_item", {"type": "message", "id": "alpha-new", "role": "user", "content": [{"type": "input_text", "text": "恢复时先回滚数据库"}]}, 4))
        update = db.sync_codex(source)
        add("追加记录增量同步", "只新增 1 条消息", update["messages_new"], update["messages_new"] == 1)

        projects = {p["name"]: p["id"] for p in db.projects()}
        db.link_projects(projects["Alpha"], projects["Beta"])
        db.link_projects(projects["Beta"], projects["Gamma"])
        focused = db.search("晨星", scope="project", project_id=projects["Alpha"])
        found = {r["source_session_id"] for r in focused["results"]}
        add("项目关联只展开一层", "Alpha 查询包含 Alpha、Beta，不包含 Gamma", sorted(found), found == {"alpha-session", "beta-session"})

        all_found = {r["source_session_id"] for r in db.search("晨星", scope="all")["results"]}
        add("所有项目范围", "3 段对话均可找到", sorted(all_found), all_found == {"alpha-session", "beta-session", "gamma-session"})

        excluded = db.search("晨星", scope="project", project_id=projects["Alpha"], current_session_id="alpha-session")
        add("当前对话默认排除", "只剩 Beta", [r["source_session_id"] for r in excluded["results"]], [r["source_session_id"] for r in excluded["results"]] == ["beta-session"])

        included = db.search("晨星", scope="project", project_id=projects["Alpha"], current_session_id="alpha-session", include_current=True)
        add("当前对话显式纳入", "Alpha 与 Beta 均出现", sorted(r["source_session_id"] for r in included["results"]), {r["source_session_id"] for r in included["results"]} == {"alpha-session", "beta-session"})

        db.map_path(str(base / "Beta"), projects["Alpha"])
        resolved = db.resolve_project(str(base / "Beta" / "src"))
        add("路径合并与子目录解析", "Beta 路径映射到 Alpha ID", resolved["id"], resolved["id"] == projects["Alpha"])

        db.link_projects(projects["Alpha"], projects["Beta"], False)
        add("取消关联", "Alpha 只包含自身", db.effective_projects(projects["Alpha"]), db.effective_projects(projects["Alpha"]) == [projects["Alpha"]])

        db.merge_projects(projects["Beta"], projects["Alpha"])
        merged = {p["id"] for p in db.projects()}
        add("合并同一项目", "Beta 路径与对话转到 Alpha，来源项目被删除", {"source_removed": projects["Beta"] not in merged, "path_project": db.resolve_project(str(base / "Beta"))["id"]}, projects["Beta"] not in merged and db.resolve_project(str(base / "Beta"))["id"] == projects["Alpha"])

        source_file = source / "alpha-session.jsonl"
        source_file.unlink()
        alpha_id = next(r["id"] for r in db.search("晨星", scope="all")["results"] if r["source_session_id"] == "alpha-session")
        retained = db.read(alpha_id)
        add("删除来源后独立保留", "原文 3 条仍可读取，搜索仍命中", {"messages": len(retained["messages"]), "source_exists": source_file.exists()}, len(retained["messages"]) == 3 and not source_file.exists())

        env = {**os.environ, "CODEX_THREAD_ID": "alpha-session"}
        command = [str(ROOT / ".venv/bin/smm"), "--db", str(db_path), "search", "晨星", "--scope", "all"]
        cli_data = json.loads(subprocess.check_output(command, env=env, text=True))
        add("CLI 共用知识库", "同一档案可搜且排除当前会话", {"results": len(cli_data["results"]), "excluded": cli_data["excluded_current_session_id"]}, len(cli_data["results"]) == 2 and cli_data["excluded_current_session_id"] == "alpha-session")

        names, current_id, readonly = asyncio.run(mcp_search(db_path))
        add("MCP 实际握手与工具调用", "4 个只读工具与 2 个管理工具可发现，自动排除当前会话", {"tools": names, "annotations_ok": readonly, "excluded": current_id}, len(names) == 6 and {"manage_sync", "configure_hub"} <= set(names) and readonly and current_id == "alpha-session")

        with TestClient(create_app(db, auto_sync=False)) as client:
            page = client.get("/")
            web = client.post("/api/search", json={"query": "晨星", "scope": "all"}).json()
            add("Web 页面与 HTTP 检索", "页面可加载、3 段对话可检索", {"page_status": page.status_code, "results": len(web["results"])}, page.status_code == 200 and len(web["results"]) == 3)
            response = client.put("/api/settings", json={"codex_root": str(source), "sync_interval_seconds": 30})
            add("Web 配置可保存", "目录与间隔可回读", response.json(), response.status_code == 200 and response.json()["sync_interval_seconds"] == 30)

        install = subprocess.check_output([sys.executable, str(ROOT / "scripts/install_skill.py"), "--home", str(base / "home")], text=True)
        paths = [base / "home/.codex/skills/smm-search/SKILL.md", base / "home/.claude/skills/smm-search/SKILL.md"]
        add("同一 Skill 可安装到 Codex 和 Claude Code", "两个目录字节相同", {"paths": [str(p.relative_to(base)) for p in paths]}, all(p.exists() for p in paths) and paths[0].read_bytes() == paths[1].read_bytes())

    output = ROOT / "reports"
    output.mkdir(exist_ok=True)
    date = datetime.now(timezone.utc).isoformat()
    (output / "first-version-e2e.json").write_text(json.dumps({"executed_at": date, "steps": steps}, ensure_ascii=False, indent=2) + "\n")
    rows = "\n".join(f"| {x['step']} | {x['name']} | {x['expected']} | {json.dumps(x['observed'],ensure_ascii=False)} | {'通过' if x['passed'] else '失败'} |" for x in steps)
    report = f"""# SMM Local 第一版端到端验收

执行时间：{date}。\n执行环境：隔离临时 Codex JSONL 样本与独立 SQLite 数据库；没有读取或修改用户真实对话。\n结论：{sum(x['passed'] for x in steps)}/{len(steps)} 步通过。\n
| 步骤 | 操作 | 预期 | 实际 | 结果 |
| --- | --- | --- | --- | --- |
{rows}

## 审核边界

这组流程验证了机制连通性与持久性，不代表真实大库的导入耗时、召回准确率或所有历史会话格式均已覆盖。
真实本机导入及性能另行记录。
"""
    (output / "first-version-e2e.md").write_text(report, encoding="utf-8")
    print(f"{len(steps)}/{len(steps)} passed; report={output / 'first-version-e2e.md'}")


if __name__ == "__main__":
    run()
