"""Human and agent command-line interface."""

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

from .core import Archive, shared_db_path
from .federation import (configure_and_start, read_archive, search_archive, upload_status,
                         choose_upload, upload_control, hub_config, project_status, _request)
from .upload import LocalUpload
from .project_control import change as change_project
from .importers import registry
from .service import DEFAULT_PORT, control_source, ensure_service, maintain, running_service, serve as run_service, stop_on_demand


def _before_batch_id(value: str) -> int:
    try:
        batch_id = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("必须是有效的正整数批次 ID") from None
    if not 0 < batch_id < 2**63:
        raise argparse.ArgumentTypeError("必须是有效的正整数批次 ID")
    return batch_id


def main() -> None:
    parser = argparse.ArgumentParser(prog="smm", description="本机 Agent 对话知识库")
    parser.add_argument("--db", help="知识库 SQLite 路径")
    sub = parser.add_subparsers(dest="command", required=True)
    sync = sub.add_parser("sync", help="立即导入新增对话")
    sync.add_argument("--source", default="all")
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
    search.add_argument("--current-source")
    search.add_argument("--local", action="store_true", help="明确检索本机档案")
    search.add_argument("--include-current", action="store_true")
    read = sub.add_parser("read", help="读取对话原文")
    read.add_argument("conversation_id", type=int, nargs="?")
    read.add_argument("--reference", help="直接使用本次搜索返回的 reference，不手工拼接档案 ID")
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
    maintenance.add_argument("--source")
    source = sub.add_parser("source", help="验收、注册或管理本机来源")
    actions = source.add_subparsers(dest="source_action", required=True)
    actions.add_parser("list", help="列出本机对话来源及其状态")
    for action, help_text in (
        ("validate", "验收候选来源适配器"),
        ("register", "验收并注册来源适配器"),
    ):
        candidate = actions.add_parser(action, help=help_text)
        candidate.add_argument("manifest", type=Path)
        candidate.add_argument("--fixture", type=Path, required=True)
    for action, help_text in (
        ("enable", "启用指定来源的导入"),
        ("disable", "停用指定来源的导入，保留已导入的记录"),
        ("rollback", "将指定插件来源的适配器切回上一版"),
    ):
        control = actions.add_parser(action, help=help_text)
        control.add_argument("source_id")
    batches = actions.add_parser(
        "batches",
        help="查看指定插件来源的导入批次",
        description="默认显示最近 100 批。按导入时间 (imported_at)、版本 (revision) 和消息数 (messages) "
        "辨认批次，取记录的 id。清理前的停用要求见 smm source purge-batch --help。",
    )
    batches.add_argument("source_id", help="插件来源 ID。用 smm source list 查找对应来源。")
    batches.add_argument(
        "--before",
        type=_before_batch_id,
        metavar="批次ID",
        help="填当前页最后一条记录的 id，查询更早的批次。返回 [] 表示已查到末尾。",
    )
    purge_help = "从本机档案删除指定批次已导入的记录。清理批次前须先停用对应的插件来源"
    purge = actions.add_parser(
        "purge-batch", help=purge_help,
        description=f"{purge_help}。使用 smm source disable <来源ID> 停用该来源。",
    )
    purge.add_argument(
        "source_id", help="待清理批次所属的插件来源 ID。用 smm source list 查找对应来源。",
    )
    purge.add_argument(
        "batch", type=int,
        help="要删除的导入批次 ID。用 smm source batches <来源ID> 查询同一来源，"
        "取目标批次记录的 id。默认只显示最近 100 批。用 --before 查询更早的批次，"
        "详见 smm source batches --help。",
    )
    sub.add_parser("stop-on-demand", help="停止按需启动的后台服务")
    configure = sub.add_parser("configure-hub", help="配置汇总电脑和本机名称")
    configure.add_argument("address")
    configure.add_argument("device_name")
    configure.add_argument("--token-file")
    upload = sub.add_parser("upload", help="选择对话上传范围并查看 Hub 确认；停止不撤回旧副本")
    upload_actions = upload.add_subparsers(dest="upload_action", required=True)
    upload_actions.add_parser("status", help="查看当前 Hub、规则、本机/Hub 确认和历史进度")
    choice = upload_actions.add_parser("set", help="保存完整规则；用 smm projects 取得本机项目 ID")
    choice.add_argument("--mode", required=True, choices=["all", "only", "except", "none"],
                        help="all 全部；only 仅指定；except 排除指定；none 不上传；only 空名单不上传，except 空名单全部")
    choice.add_argument("--project-id", action="append", type=int, default=[], help="运行 smm projects 取得本机项目 ID，可重复；不是 Hub 项目 ID")
    reconcile = upload_actions.add_parser("reconcile", help="无参数只查看差异；选择 hub 采用当前 Hub 规则，或明确重提 local")
    reconcile.add_argument("--use", choices=["hub", "local"])
    reconcile.add_argument("--expected-hub-revision", type=int, help="刚查看差异中 hub.revision；--use local 必填，过期则重新查看")
    reconcile.add_argument("--expected-local-generation", type=int, help="刚查看 upload reconcile 输出中 local.generation；--use local 必填，过期则重新查看")
    upload_actions.add_parser("prepare-restore", help="先停止正文并输出恢复/排除清单，再停服务恢复备份；不要覆盖保护文件")
    project = sub.add_parser("project", help="管理明确的全局项目和会话归属")
    project_actions = project.add_subparsers(dest="project_action", required=True)
    project_actions.add_parser("ensure-global", help="创建或取得唯一全局项目；全局不是所有项目检索")
    assign = project_actions.add_parser("assign-conversation", help="用本机搜索的会话 ID 预览归属变更，核对后 --confirm 提交")
    assign.add_argument("conversation_id", type=int)
    assign.add_argument("--project-id", type=int, required=True, help="smm projects 返回的目标本机项目 ID")
    assign.add_argument("--confirm", help="上次预览返回的 confirmation，归属/范围/规则变化后须重取")
    args = parser.parse_args()
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
            result = maintain(db, args.action, args.source)
        elif args.command == "configure-hub":
            result = configure_and_start(db, args.address, args.device_name, args.token_file)
        elif args.command == "stop-on-demand":
            stop_on_demand(db)
            result = {"ok": True}
        elif args.command == "sync":
            if args.root:
                if args.source not in ("codex", "claude-code"):
                    parser.error("--root 只支持 Codex 或 Claude Code 的一次性导入")
                if not db.configured_sources()[args.source]["enabled"]:
                    raise ValueError("来源已停用")
                # Compatibility for explicit one-off fixture imports.
                result = (db.sync_codex if args.source == "codex" else db.sync_claude)(args.root)
            else:
                round_result = maintain(db, "sync", None if args.source == "all" else args.source)
                result = round_result["result"] if round_result["result"] is not None else round_result
                if args.source in {"codex", "claude-code"} and "sources" in result:
                    result = result["sources"].get(args.source, result)
        elif args.command == "status":
            result = {**db.status(), "sources": db.source_status()}
        elif args.command == "source":
            action = args.source_action
            if action == "list":
                result = db.source_status()
            elif action in {"validate", "register"}:
                result = registry.configure(db, args.manifest, args.fixture, register=action == "register")
                if action == "register":
                    try:
                        result["service_url"] = ensure_service(db, sync_on_start=False)["url"]
                    except (OSError, RuntimeError, ValueError) as exc:
                        result["service_error"] = str(exc)
            elif action in {"enable", "disable"}:
                result = control_source(db, args.source_id, action == "enable")
            elif action == "rollback":
                result = registry.rollback(db, args.source_id)
            elif action == "batches":
                result = registry.batches(db, args.source_id, before=args.before)
            else:
                result = registry.purge_batch(db, args.source_id, args.batch)
        elif args.command == "doctor":
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
            home = Path.home()
            skills = {"codex": any((home / directory / "skills/smm-search/SKILL.md").is_file()
                                   for directory in (".agents", ".codex")),
                      "claude": (home / ".claude/skills/smm-search/SKILL.md").is_file()}
            with db.connect() as con:
                database_ok = con.execute("PRAGMA quick_check").fetchone()[0] == "ok"
            sources = {name: source["available"] for name, source in db.source_status().items()}
            endpoint = running_service(db)
            service_ok = endpoint is not None
            result = {"database_ok": database_ok, "database_path": str(db.db_path), "sources": sources,
                      "agents": agents, "skills": skills, "installation": installation,
                      "service_ok": service_ok, "service_url": endpoint["url"] if endpoint else None,
                      "model_auth_checked": False, "status": db.status(),
                      "ready": database_ok and any(sources.values()) and service_ok and any(v["installed"] and v["mcp"] and skills[k] for k, v in agents.items())}
        elif args.command == "projects":
            result = project_status(db)
        elif args.command == "upload":
            if args.upload_action == "status":
                result = upload_status(db)
            elif args.upload_action == "set":
                result = choose_upload(db, args.mode, args.project_id)
            elif args.upload_action == "reconcile":
                result = upload_control(db).reconcile(_request, use=args.use, expected_hub_revision=args.expected_hub_revision,
                                                      expected_local_generation=args.expected_local_generation)
            else:
                config = hub_config(db)
                controller = (LocalUpload(db, config, config["bound_hub_id"])
                              if config.get("bound_hub_id") else upload_control(db))
                result = controller.prepare_restore()
        elif args.command == "project":
            if args.project_action == "ensure-global":
                result = db.ensure_global_project()
            else:
                result = change_project(db, "assign", {"conversation_id": args.conversation_id,
                    "target_id": args.project_id}, args.confirm, always_preview=True)
        elif args.command == "resolve-project":
            result = db.resolve_project(args.cwd)
        elif args.command == "search":
            current_id = args.current_session_id or os.environ.get("CODEX_THREAD_ID") or os.environ.get("CODEX_SESSION_ID") or os.environ.get("CLAUDE_SESSION_ID")
            current_source = args.current_source or ("codex" if os.environ.get("CODEX_THREAD_ID") or os.environ.get("CODEX_SESSION_ID") else "claude-code" if os.environ.get("CLAUDE_SESSION_ID") else None)
            result = search_archive(db, args.query, local=args.local, scope=args.scope, project_id=args.project_id, limit=args.limit, current_session_id=current_id, current_source=current_source, include_current=args.include_current)
        elif args.command == "read":
            result = read_archive(db, args.conversation_id, start=args.start, end=args.end,
                                  hub_id=args.hub_id, hub_message_id=args.hub_message_id, reference=args.reference)
        else:
            raise AssertionError(args.command)
    except (OSError, RuntimeError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
