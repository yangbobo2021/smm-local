"""Human and agent command-line interface."""

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

from .core import Archive, shared_db_path
from .federation import configure_and_start, read_archive, search_archive
from .service import DEFAULT_PORT, maintain, running_service, serve as run_service, stop_on_demand


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
    read.add_argument("--hub-id", help="汇总搜索返回的档案 ID")
    read.add_argument("--hub-message-id", type=int, help="汇总搜索返回的精确消息 ID")
    serve = sub.add_parser("serve", help="启动本地 Web UI")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=DEFAULT_PORT)
    serve.add_argument("--on-demand", action="store_true", help=argparse.SUPPRESS)
    serve.add_argument("--skip-initial-sync", action="store_true", help=argparse.SUPPRESS)
    maintenance = sub.add_parser("maintenance", help="管理本机同步与状态页")
    maintenance.add_argument("action", choices=["status", "open", "sync", "pause", "resume"])
    sub.add_parser("stop-on-demand", help="停止按需启动的后台服务")
    configure = sub.add_parser("configure-hub", help="配置汇总电脑和本机名称")
    configure.add_argument("address")
    configure.add_argument("device_name")
    configure.add_argument("--token-file")
    hub = sub.add_parser("serve-hub", help="运行独立的多机汇总服务")
    hub.add_argument("--host", default="127.0.0.1")
    hub.add_argument("--port", type=int, default=8770)
    hub.add_argument("--token-file", required=True)
    hub.add_argument("--tls-cert")
    hub.add_argument("--tls-key")
    from .hub_admin import add_arguments, dispatch

    add_arguments(sub)
    args = parser.parse_args()
    if args.command == "hub":
        try:
            result = dispatch(args)
        except (OSError, RuntimeError, ValueError) as exc:
            parser.error(str(exc))
        if result is not None:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    if args.command == "serve-hub":
        import uvicorn
        from .hub import create_hub

        if bool(args.tls_cert) != bool(args.tls_key):
            parser.error("TLS 证书和私钥必须一起提供")
        if args.host not in {"127.0.0.1", "::1", "localhost"} and not args.tls_cert:
            parser.error("非回环地址必须启用 TLS")
        local_path = shared_db_path().resolve()
        hub_path = Path(args.db or local_path.with_name("smm-hub.sqlite3")).expanduser().resolve()
        if hub_path == local_path or (hub_path.exists() and local_path.exists() and hub_path.samefile(local_path)):
            parser.error("汇总服务必须使用独立数据库")
        try:
            token = Path(args.token_file).expanduser().read_text(encoding="ascii").strip()
            uvicorn.run(create_hub(Archive(hub_path), token), host=args.host, port=args.port,
                        ssl_certfile=args.tls_cert, ssl_keyfile=args.tls_key)
        except (OSError, ValueError) as exc:
            parser.error(str(exc))
        return
    db_path = Path(args.db or shared_db_path()).expanduser()
    if args.command == "stop-on-demand" and not db_path.is_file():
        print('{"ok": true}')
        return
    db = Archive(db_path)
    try:
        if args.command == "serve":
            run_service(db, args.host, args.port, on_demand=args.on_demand,
                        sync_on_start=not args.skip_initial_sync)
            return
        if args.command == "maintenance":
            result = maintain(db, args.action)
        elif args.command == "configure-hub":
            result = configure_and_start(db, args.address, args.device_name, args.token_file)
        elif args.command == "stop-on-demand":
            stop_on_demand(db)
            result = {"ok": True}
        elif args.command == "sync":
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
            endpoint = running_service(db)
            service_ok = endpoint is not None
            result = {"database_ok": database_ok, "database_path": str(db.db_path), "sources": sources,
                      "agents": agents, "skills": skills, "installation": installation,
                      "service_ok": service_ok, "service_url": endpoint["url"] if endpoint else None,
                      "model_auth_checked": False, "status": db.status(),
                      "ready": database_ok and any(sources.values()) and service_ok and any(v["installed"] and v["mcp"] and skills[k] for k, v in agents.items())}
        elif args.command == "projects":
            result = db.projects()
        elif args.command == "resolve-project":
            result = db.resolve_project(args.cwd)
        elif args.command == "search":
            current_id = args.current_session_id or os.environ.get("CODEX_THREAD_ID") or os.environ.get("CODEX_SESSION_ID") or os.environ.get("CLAUDE_SESSION_ID")
            current_source = args.current_source or ("codex" if os.environ.get("CODEX_THREAD_ID") or os.environ.get("CODEX_SESSION_ID") else "claude-code" if os.environ.get("CLAUDE_SESSION_ID") else None)
            result = search_archive(db, args.query, scope=args.scope, project_id=args.project_id, limit=args.limit, current_session_id=current_id, current_source=current_source, include_current=args.include_current)
        elif args.command == "read":
            result = read_archive(db, args.conversation_id, start=args.start, end=args.end,
                                  hub_id=args.hub_id, hub_message_id=args.hub_message_id)
        else:
            raise AssertionError(args.command)
    except (OSError, RuntimeError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
