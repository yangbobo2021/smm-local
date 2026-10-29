"""Human and agent command-line interface."""

import argparse
import json
import os

from .core import Archive


def main() -> None:
    parser = argparse.ArgumentParser(prog="smm", description="本地 Codex 对话知识库")
    parser.add_argument("--db", help="知识库 SQLite 路径")
    sub = parser.add_subparsers(dest="command", required=True)
    sync = sub.add_parser("sync", help="立即导入新增 Codex 对话")
    sync.add_argument("--root", help="Codex 会话目录")
    sub.add_parser("status", help="查看导入状态")
    sub.add_parser("projects", help="列出项目及关联")
    resolve = sub.add_parser("resolve-project", help="按当前目录确定项目")
    resolve.add_argument("--cwd", default=os.getcwd())
    search = sub.add_parser("search", help="BM25 检索")
    search.add_argument("query")
    search.add_argument("--scope", choices=["all", "project"], default="all")
    search.add_argument("--project-id", type=int)
    search.add_argument("--limit", type=int, default=5)
    search.add_argument("--current-session-id")
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
            result = db.sync_codex(args.root)
        elif args.command == "status":
            result = db.status()
        elif args.command == "projects":
            result = db.projects()
        elif args.command == "resolve-project":
            result = db.resolve_project(args.cwd)
        elif args.command == "search":
            current_id = args.current_session_id or os.environ.get("CODEX_THREAD_ID") or os.environ.get("CODEX_SESSION_ID")
            result = db.search(args.query, scope=args.scope, project_id=args.project_id, limit=args.limit, current_session_id=current_id, include_current=args.include_current)
        elif args.command == "read":
            result = db.read(args.conversation_id, start=args.start, end=args.end)
        else:
            raise AssertionError(args.command)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
