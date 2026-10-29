"""MCP stdio adapter over the same archive API."""

from __future__ import annotations

import json
import os
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .core import Archive


def create_mcp(archive: Archive | None = None) -> FastMCP:
    db = archive or Archive()
    server = FastMCP("smm-local")
    readonly = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)

    @server.tool(annotations=readonly)
    def search_conversations(query: str, scope: str = "all", project_id: int | None = None, limit: int = 5, current_session_id: str | None = None, current_source: str | None = None, include_current: bool = False) -> str:
        """Search archived conversations with bounded previews and original positions; read_conversation returns full evidence. scope=project includes direct links; pass current_session_id to exclude the active conversation by default."""
        current_id = current_session_id or os.environ.get("CODEX_THREAD_ID") or os.environ.get("CODEX_SESSION_ID") or os.environ.get("CLAUDE_SESSION_ID")
        source = current_source or ("codex" if os.environ.get("CODEX_THREAD_ID") or os.environ.get("CODEX_SESSION_ID") else "claude-code" if os.environ.get("CLAUDE_SESSION_ID") else None)
        size = int(os.environ.get("SMM_SEARCH_PREVIEW_CHARS", "600"))
        return json.dumps(db.search(query, scope=scope, project_id=project_id, limit=limit, current_session_id=current_id, current_source=source, include_current=include_current, preview_chars=size), ensure_ascii=False)

    @server.tool(annotations=readonly)
    def read_conversation(conversation_id: int, start: int | None = None, end: int | None = None) -> str:
        """Read preserved original user/assistant messages from one archived conversation."""
        return json.dumps(db.read(conversation_id, start=start, end=end), ensure_ascii=False)

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
    create_mcp().run(transport="stdio")


if __name__ == "__main__":
    main()
