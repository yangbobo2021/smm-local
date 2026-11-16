"""MCP stdio adapter over the same archive API."""

from __future__ import annotations

import argparse
import json
import os
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .core import Archive, shared_db_path
from .federation import configure_and_start, read_archive, search_archive
from .service import Action, control_source, maintain


def create_mcp(archive: Archive | None = None) -> FastMCP:
    db = archive or Archive(shared_db_path())
    server = FastMCP("smm-local")
    readonly = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)

    @server.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False))
    def manage_sync(action: Action, source: str | None = None) -> dict:
        """Manage local SMM sync. status starts/reuses the service and returns its state; open opens its status page; sync runs one sync; pause persists a pause for automatic sync; resume reenables it. A manual sync leaves the pause setting unchanged."""
        try:
            return maintain(db, action, source)
        except (OSError, RuntimeError, ValueError) as exc:
            return {"ok": False, "error": str(exc)}

    @server.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False))
    def set_source_enabled(source: str, enabled: bool) -> dict:
        """Enable or disable a registered local conversation source by ID."""
        return control_source(db, source, enabled)

    @server.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=True))
    def configure_hub(address: str, device_name: str, token_file: str | None = None) -> dict:
        """Configure a user's SMM hub and this computer's name. Use a local credential file; never ask for its contents in chat."""
        return configure_and_start(db, address, device_name, token_file)

    @server.tool(annotations=readonly)
    def search_conversations(query: str, scope: str = "all", project_id: int | None = None, limit: int = 5, current_session_id: str | None = None, current_source: str | None = None, include_current: bool = False, local: bool = False) -> str:
        """Search archived conversations with 600-character message previews and original positions by default. read_conversation returns full evidence. scope=project includes direct links in the archive being searched; pass current_session_id to exclude the active conversation by default."""
        current_id = current_session_id or os.environ.get("CODEX_THREAD_ID") or os.environ.get("CODEX_SESSION_ID") or os.environ.get("CLAUDE_SESSION_ID")
        source = current_source or ("codex" if os.environ.get("CODEX_THREAD_ID") or os.environ.get("CODEX_SESSION_ID") else "claude-code" if os.environ.get("CLAUDE_SESSION_ID") else None)
        size = int(os.environ.get("SMM_SEARCH_PREVIEW_CHARS", "600"))
        return json.dumps(search_archive(db, query, local=local, scope=scope, project_id=project_id, limit=limit, current_session_id=current_id, current_source=source, include_current=include_current, preview_chars=size), ensure_ascii=False)

    @server.tool(annotations=readonly)
    def read_conversation(conversation_id: int, start: int | None = None, end: int | None = None,
                          hub_id: str | None = None, hub_message_id: int | None = None) -> str:
        """Read original messages. Pass the exact hub_id from hub search results; omit it for local results."""
        return json.dumps(read_archive(db, conversation_id, start=start, end=end, hub_id=hub_id,
                                       hub_message_id=hub_message_id), ensure_ascii=False)

    @server.tool(annotations=readonly)
    def list_projects() -> str:
        """List project IDs, source paths, direct links, and conversation counts for choosing search scope."""
        return json.dumps(db.projects(), ensure_ascii=False)

    @server.tool(annotations=readonly)
    def resolve_project(cwd: str) -> str:
        """Find the configured project for a working directory or its nearest parent."""
        return json.dumps(db.resolve_project(cwd), ensure_ascii=False)

    return server


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", help="覆盖档案路径（用于独立测试实例）")
    args = parser.parse_args()
    create_mcp(Archive(args.db or shared_db_path())).run(transport="stdio")


if __name__ == "__main__":
    main()
