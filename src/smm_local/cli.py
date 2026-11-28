"""Human and agent command-line interface."""

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

from .core import Archive, shared_db_path
from .documents import Documents
from .document_processing import Configuration, configuration_arguments
from .document_sync import DocumentSync,schedule as schedule_documents,hub_sources,hub_projects
from .document_search import search as search_documents,read as read_document,original as original_document
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
    projects_parser = sub.add_parser("projects", help="列出项目及关联")
    resolve = sub.add_parser("resolve-project", help="按当前目录确定项目")
    resolve.add_argument("--cwd", default=os.getcwd())
    search = sub.add_parser("search", help="BM25 检索")
    search.add_argument("query")
    search.add_argument("--hub-project-id",type=int,help="projects --hub取得的Hub根ID，与--project-id互斥")
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
    projects_parser.add_argument("--hub", action="store_true", help="列出Hub项目根，供--hub-project-id")
    project = sub.add_parser("project", help="管理明确的全局项目和会话归属")
    project_actions = project.add_subparsers(dest="project_action", required=True)
    project_create = project_actions.add_parser('create', help='创建普通本机项目；可同名，不推断目录/对话/关联')
    project_create.add_argument('name', help='非空显示名称；返回本机ID和stable_key，用于documents --project-id')
    project_actions.add_parser("ensure-global", help="创建或取得唯一全局项目；全局不是所有项目检索")
    documents = sub.add_parser('documents', help='项目文档采集、独立同步选择及联合检索；路径来源需明确refresh', description='本机明确采集 .md/.markdown/.txt/.docx/.xlsx/.pdf；创建端需安装[documents]依赖。PDF文字优先，OCR先用processing-configure及processing-status --check准备本地组件。源正文不改写。项目文档同步默认关闭，以sync-policy独立允许；默认联合检索，--local仅本机。保存来源后明确refresh。')
    document_actions = documents.add_subparsers(dest='document_action', required=True)
    configuration_arguments(document_actions)
    doc_retry=document_actions.add_parser('reprocess',help='只重处理files给出的合法保存原件，不重开源路径')
    for flag in ('document-id','capture-id','expected-attempt-id'):doc_retry.add_argument('--'+flag,required=True)
    for flag in ('expected-version','expected-processing-version'):doc_retry.add_argument('--'+flag,type=int,required=True)
    for action in ['add','set']:
        doc = document_actions.add_parser(action, help='添加来源（pending）' if action=='add' else '完整替换配置并使旧来源资格失效', description='来源项目ID用 smm projects 取得，无项目时先 smm project create 名称。名单可重复，省略即空名单；省略--no-recursive即递归。保存只为pending，随后运行 smm documents refresh。')
        doc.add_argument('path' if action=='add' else 'source_id',help='服务器所在本机的可读绝对文件/目录路径（非链接）' if action=='add' else 'smm documents sources 返回的来源id；不能改变根路径')
        doc.add_argument('--project-id',type=int,action='append',default=[],help='现有本机项目ID（smm projects），可重复；省略只参加全部文档检索')
        doc.add_argument('--exclude',action='append',default=[],help='相对POSIX路径，可重复；*单段、?单字符、**零/多目录，尾/排目录。禁止绝对路径、..和反斜杠')
        doc.add_argument('--no-recursive',action='store_true',help='仅根直接文件；不跟随链接/junction，默认跳过隐藏与构建目录')
    doc_sources = document_actions.add_parser('sources',help='查看来源id/完整配置、pending/refreshing/ready/partial/failed、真实计数和错误')
    doc_sources.add_argument('--hub',action='store_true',help='列出Hub自有/设备来源；失败明确报错')
    document_actions.add_parser('sync-status',help='查看稳定KEY/HID/generation及本机选择/Hub确认')
    doc_policy=document_actions.add_parser('sync-policy',help='保存项目文档选择后尝试同步；暂停保留旧资格，失效仍撤回')
    doc_policy.add_argument('project_key');doc_policy.add_argument('--enabled',choices=['yes','no'],required=True);doc_policy.add_argument('--expected-hub-id',required=True);doc_policy.add_argument('--expected-generation',type=int,required=True)
    doc_sync=document_actions.add_parser('sync',help='重试采集档案和撤回，不扫描源文件；手动不改变全局暂停');doc_sync.add_argument('--project-key')
    doc_files = document_actions.add_parser('files',help='查看已发现文件元信息、ready/failed/missing及原因，不返回正文')
    doc_files.add_argument('--source-id',help='来源id取自documents sources，省略看全部')
    doc_refresh = document_actions.add_parser('refresh',help='明确读取并刷新采集快照；旧版本ref失效，失败后可重试',description='仅明确刷新读取来源正文。旧 TXT/Markdown 单文件2MiB、每来源累计16MiB；DOCX/XLSX/PDF 原件单份20MiB、每来源原件及处理结果各累计128MiB；各格式共同计入每来源1000候选。创建端须安装 [documents]；PDF 本地OCR先用 processing-configure 和 processing-status --check 准备。个别失败见 files/sources，已保存合法原件按 retry_target 明确 reprocess。')
    doc_refresh.add_argument('--source-id',help='来源id取自documents sources，省略逐来源刷新全部')
    doc_remove = document_actions.add_parser('remove',help='取消来源；独占材料立即退出检索/读取，不删除原文件')
    doc_remove.add_argument('source_id',help='来源id取自documents sources；其他有效重叠来源继续保留当前版本')
    doc_search = document_actions.add_parser('search',help='检索本机/Hub采集正文并本机重排；--local仅本机，不扫描源文件')
    doc_search.add_argument('query',help='非空中英文正文查询词')
    doc_search.add_argument('--scope',choices=['all','project'],default='all')
    doc_search.add_argument('--project-id',type=int,help='smm projects的本机根ID，与--hub-project-id互斥；线上用Hub一层关联，--local用本机关联')
    doc_search.add_argument('--local',action='store_true',help='仅查本机和本机关联；不连接Hub')
    doc_search.add_argument('--hub-project-id',type=int,help='projects --hub取得的Hub根ID，与--project-id互斥')
    doc_search.add_argument('--limit',type=int,default=5,help='1至50，默认5；按文件去重和词法相关性排序')
    doc_read = document_actions.add_parser('read',help='按搜索返回的reference准确读取采集版本',description='缺省读命中片段。start/end是整个规范化采集文本的Unicode码点 [start,end)，非字节或UTF-16；最多16000字符。旧 TXT/Markdown 只去BOM并将CRLF/CR转LF；DOCX/XLSX/PDF 返回创建端提取文本和覆盖信息，不等同原始文件。原字节用 --view original-info 核对、--original-output 导出；表格用 --view table 和同次返回的 table_id。旧版本/来源资格失效须重新检索，不读历史版本。')
    doc_read.add_argument('--reference',required=True,help='原样复制documents search返回的reference，不能用对话ID')
    doc_read.add_argument('--start',type=int,help='Unicode起始码点（含，0开始）')
    doc_read.add_argument('--end',type=int,help='Unicode结束码点（不含）')
    doc_read.add_argument('--view',choices=['text','table','original-info'],default='text',help='提取文本、表格窗口或已保存原件信息；默认text')
    doc_read.add_argument('--table-id',help='取自本次命中/普通read的tables定位')
    for flag in ('row-start','row-end','column-start','column-end'):
        doc_read.add_argument('--'+flag,type=int,help='表格行列窗口，1起、终点不含；仅table视图')
    doc_read.add_argument('--original-output',help='将准确采集原件保存到本机新文件；拒绝覆盖，与文本范围/表格参数互斥')
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
            result = hub_projects(db) if args.hub else project_status(db)
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
            if args.project_action == 'create':
                result = db.create_project(args.name)
            elif args.project_action == "ensure-global":
                result = db.ensure_global_project()
            else:
                result = change_project(db, "assign", {"conversation_id": args.conversation_id,
                    "target_id": args.project_id}, args.confirm, always_preview=True)
        elif args.command == 'documents':
            documents = Documents(db)
            action = args.document_action
            if action == 'processing-status':result=Configuration(documents.snapshots).status(check=args.check)
            elif action == 'processing-configure':result=Configuration(documents.snapshots).configure(expected_revision=args.expected_revision,ocr_executable=args.ocr_executable,ocr_data_dir=args.ocr_data_dir,languages=args.languages)
            elif action == 'reprocess':result=documents.reprocess(args.document_id,args.capture_id,args.expected_attempt_id,args.expected_version,args.expected_processing_version)
            elif action == 'add':
                result = documents.add(args.path, project_ids=args.project_id, exclude=args.exclude, recursive=not args.no_recursive)
            elif action == 'set':
                result = documents.set(args.source_id, project_ids=args.project_id, exclude=args.exclude, recursive=not args.no_recursive)
            elif action == 'remove': result = documents.remove(args.source_id)
            elif action == 'sources': result = hub_sources(db) if args.hub else documents.sources()
            elif action == 'files': result = documents.files(args.source_id)
            elif action == 'refresh': result = documents.refresh(args.source_id)
            elif action == 'sync-status':result=DocumentSync(db).status()
            elif action == 'sync-policy':result=DocumentSync(db).choose(args.project_key,args.enabled=='yes',args.expected_hub_id,args.expected_generation)
            elif action == 'sync':result=DocumentSync(db).sync(project_key=args.project_key)
            elif action == 'search': result = search_documents(db,args.query,scope=args.scope,project_id=args.project_id,hub_project_id=args.hub_project_id,limit=args.limit,local=args.local)
            else:
                table_options={key:getattr(args,key) for key in ('table_id','row_start','row_end','column_start','column_end') if getattr(args,key) is not None}
                if args.original_output is not None:
                    if args.start is not None or args.end is not None or args.view=='table' or table_options:
                        raise ValueError('原件输出与文本范围或表格读取参数互斥')
                    from .document_protocol import write_original_output
                    metadata=read_document(db,args.reference,view='original-info')
                    raw=original_document(db,args.reference)
                    output=write_original_output(args.original_output,raw,metadata)
                    result={**metadata,'output_path':str(output)}
                else:result=read_document(db,args.reference,start=args.start,end=args.end,view=args.view,**table_options)
            if action in {'add','set','remove','refresh'}:schedule_documents(db)
        elif args.command == "resolve-project":
            result = db.resolve_project(args.cwd)
        elif args.command == "search":
            current_id = args.current_session_id or os.environ.get("CODEX_THREAD_ID") or os.environ.get("CODEX_SESSION_ID") or os.environ.get("CLAUDE_SESSION_ID")
            current_source = args.current_source or ("codex" if os.environ.get("CODEX_THREAD_ID") or os.environ.get("CODEX_SESSION_ID") else "claude-code" if os.environ.get("CLAUDE_SESSION_ID") else None)
            result = search_archive(db, args.query, local=args.local, scope=args.scope, project_id=args.project_id, hub_project_id=args.hub_project_id, limit=args.limit, current_session_id=current_id, current_source=current_source, include_current=args.include_current)
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
