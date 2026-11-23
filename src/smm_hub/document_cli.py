"""Hub document CLI uses the same checked context and storage as the Web API."""

from ._archive import Archive
from .documents import HubDocuments


def add_arguments(actions, project_actions):
    create = project_actions.add_parser("create", help="创建Hub自有普通项目")
    create.add_argument("name")
    project_actions.add_parser("ensure-global", help="取得或创建Hub自有全局项目")
    parser = actions.add_parser(
        "documents", help="管理Hub自有文档、检索及恢复；设备投影只读"
    )
    sub = parser.add_subparsers(dest="document_action", required=True)
    for action in ("add", "set"):
        p = sub.add_parser(action, help="保存配置为pending；需明确refresh")
        p.add_argument("path" if action == "add" else "source_id")
        p.add_argument("--project-id", type=int, action="append", default=[])
        p.add_argument("--exclude", action="append", default=[])
        p.add_argument("--no-recursive", action="store_true")
    sub.add_parser("sources", help="列出Hub自有与设备来源及其创建端")
    for action in ("files", "refresh"):
        p = sub.add_parser(action)
        p.add_argument("--source-id")
    p = sub.add_parser("remove")
    p.add_argument("source_id")
    p = sub.add_parser("search")
    p.add_argument("query")
    p.add_argument("--scope", choices=["all", "project"], default="all")
    p.add_argument("--project-id", type=int)
    p.add_argument("--limit", type=int, default=5)
    p = sub.add_parser("read")
    p.add_argument("--reference", required=True)
    p.add_argument("--start", type=int)
    p.add_argument("--end", type=int)
    sub.add_parser("recovery-status", help="查看文档保护冲突、影响及不透明state")
    p = sub.add_parser(
        "recover", help="重建文档epoch，使全部旧引用失效；需明确重新采集/选择"
    )
    p.add_argument("--expected-state", required=True)


def dispatch(state, args):
    documents = HubDocuments(Archive(state / "smm-hub.sqlite3"))
    action = args.document_action
    if action == "sources":
        return documents.sources()
    if action == "files":
        return documents.documents.files(args.source_id)
    if action == "recovery-status":
        return documents.recovery_status()
    if action == "recover":
        return documents.recover(args.expected_state)
    context = documents.context()
    if action in ("add", "set"):
        body = {
            **context,
            "project_ids": args.project_id,
            "exclude": args.exclude,
            "recursive": not args.no_recursive,
        }
        if action == "add":
            body["path"] = args.path
        return documents.native(
            action, body, args.source_id if action == "set" else None
        )
    if action in ("refresh", "remove"):
        return documents.native(action, context, args.source_id)
    if action == "search":
        return documents.search(
            {
                **context,
                "query": args.query,
                "scope": args.scope,
                "project_id": args.project_id,
                "limit": args.limit,
            }
        )
    if action == "read":
        return documents.read(
            {
                **context,
                "reference": args.reference,
                **{
                    k: getattr(args, k)
                    for k in ("start", "end")
                    if getattr(args, k) is not None
                },
            }
        )
    raise ValueError("未知文档操作")
