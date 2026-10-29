"""Human and agent command-line interface."""

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from urllib.request import urlopen

from .core import Archive


def main() -> None:
    parser = argparse.ArgumentParser(prog="smm", description="本地 Codex / Claude Code 对话知识库")
    parser.add_argument("--db", help="知识库 SQLite 路径")
    sub = parser.add_subparsers(dest="command", required=True)
    sync = sub.add_parser("sync", help="立即导入新增对话")
    sync.add_argument("--source", choices=["all", "codex", "claude-code"], default="all")
    sync.add_argument("--root", help="所选单个来源的会话目录")
    sub.add_parser("status", help="查看导入状态")
    sub.add_parser("doctor", help="检查安装、来源和 Agent 接入")
    sub.add_parser("projects", help="列出项目及关联")
    resolve = sub.add_parser("resolve-project", help="按当前目录确定项目")
    resolve.add_argument("--cwd", default=os.getcwd())
    search = sub.add_parser("search", help="BM25 检索")
    search.add_argument("query")
    search.add_argument("--scope", choices=["all", "project"], default="all")
    search.add_argument("--project-id", type=int)
    search.add_argument("--limit", type=int, default=5)
    search.add_argument("--current-session-id")
    search.add_argument("--current-source", choices=["codex", "claude-code"])
    search.add_argument("--include-current", action="store_true")
    read = sub.add_parser("read", help="读取对话原文")
    read.add_argument("conversation_id", type=int)
    read.add_argument("--start", type=int)
    read.add_argument("--end", type=int)
    serve = sub.add_parser("serve", help="启动本地 Web UI")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    db = Archive(args.db)
    if args.command == "serve":
        import uvicorn
        from .api import create_app
        uvicorn.run(create_app(db), host=args.host, port=args.port)
        return
    try:
        if args.command == "sync":
            if args.source == "all":
                if args.root:
                    parser.error("--root 需要同时指定 --source codex 或 claude-code")
                result = db.sync_all()
            elif args.source == "codex":
                result = db.sync_codex(args.root)
            else:
                result = db.sync_claude(args.root)
        elif args.command == "status":
            result = db.status()
        elif args.command == "doctor":
            settings = db.get_settings()
            manifest = Path.home() / ".local/share/smm-local/install.json"
            installation = json.loads(manifest.read_text()) if manifest.is_file() else {}
            mcp_path = installation.get("mcp_path", "")
            agents = {}
            for agent in ("codex", "claude"):
                executable = shutil.which(agent)
                if not executable:
                    agents[agent] = {"installed": False, "mcp": False}
                    continue
                check = subprocess.run([executable, "mcp", "get", "smm-local"], capture_output=True, text=True, timeout=15)
                agents[agent] = {"installed": True, "mcp": check.returncode == 0 and bool(mcp_path) and mcp_path in check.stdout + check.stderr}
            skills = {agent: (Path.home() / f".{agent}/skills/smm-search/SKILL.md").is_file() for agent in ("codex", "claude")}
            with db.connect() as con:
                database_ok = con.execute("PRAGMA quick_check").fetchone()[0] == "ok"
            sources = {"codex": Path(settings["codex_root"]).is_dir(), "claude-code": Path(settings["claude_root"]).is_dir()}
            try:
                with urlopen("http://127.0.0.1:8766/api/status", timeout=2) as response:
                    payload = json.load(response)
                    service_ok = response.status == 200 and "by_source" in payload and "settings" in payload
            except (OSError, TimeoutError, ValueError):
                service_ok = False
            result = {"database_ok": database_ok, "database_path": str(db.db_path), "sources": sources,
                      "agents": agents, "skills": skills, "installation": installation,
                      "service_ok": service_ok, "model_auth_checked": False, "status": db.status(),
                      "ready": database_ok and any(sources.values()) and service_ok and any(v["installed"] and v["mcp"] and skills[k] for k, v in agents.items())}
        elif args.command == "projects":
            result = db.projects()
        elif args.command == "resolve-project":
            result = db.resolve_project(args.cwd)
        elif args.command == "search":
            current_id = args.current_session_id or os.environ.get("CODEX_THREAD_ID") or os.environ.get("CODEX_SESSION_ID") or os.environ.get("CLAUDE_SESSION_ID")
            current_source = args.current_source or ("codex" if os.environ.get("CODEX_THREAD_ID") or os.environ.get("CODEX_SESSION_ID") else "claude-code" if os.environ.get("CLAUDE_SESSION_ID") else None)
            result = db.search(args.query, scope=args.scope, project_id=args.project_id, limit=args.limit, current_session_id=current_id, current_source=current_source, include_current=args.include_current)
        elif args.command == "read":
            result = db.read(args.conversation_id, start=args.start, end=args.end)
        else:
            raise AssertionError(args.command)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
