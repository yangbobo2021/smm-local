"""MCP stdio adapter over the same archive API."""

from __future__ import annotations

import argparse
import json
import os
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import StrictInt

from .core import Archive, shared_db_path
from .federation import configure_and_start, read_archive, search_archive
from .service import Action, control_source, maintain
from .documents import Documents
from .document_search import search as document_search,read as document_read
from .document_sync import hub_projects,hub_sources,combined_listing


def create_mcp(archive: Archive | None = None) -> FastMCP:
    db = archive or Archive(shared_db_path())
    server = FastMCP("smm-local")
    documents = Documents(db)
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
        """Configure Hub lookup and this computer's name. New connections do not upload dialogue until a Web/CLI upload choice. Use a credential file, never its contents in chat."""
        return configure_and_start(db, address, device_name, token_file)

    @server.tool(annotations=readonly)
    def search_conversations(query: str, scope: str = "all", project_id: int | None = None, limit: int = 5, current_session_id: str | None = None, current_source: str | None = None, include_current: bool = False, local: bool = False, hub_project_id: StrictInt | None = None) -> str:
        """Search local and configured Hub candidates together, reranked locally; unuploaded local conversations participate. Project scope uses Hub direct links online, only the requested local project on Hub failure; local=true uses local links. Pass the returned reference to read_conversation for exact evidence. Previews default to 600 characters."""
        current_id = current_session_id or os.environ.get("CODEX_THREAD_ID") or os.environ.get("CODEX_SESSION_ID") or os.environ.get("CLAUDE_SESSION_ID")
        source = current_source or ("codex" if os.environ.get("CODEX_THREAD_ID") or os.environ.get("CODEX_SESSION_ID") else "claude-code" if os.environ.get("CLAUDE_SESSION_ID") else None)
        size = int(os.environ.get("SMM_SEARCH_PREVIEW_CHARS", "600"))
        return json.dumps(search_archive(db, query, local=local, scope=scope, project_id=project_id, hub_project_id=hub_project_id, limit=limit, current_session_id=current_id, current_source=source, include_current=include_current, preview_chars=size), ensure_ascii=False)

    @server.tool(annotations=readonly)
    def read_conversation(conversation_id: int | None = None, start: int | None = None, end: int | None = None,
                          hub_id: str | None = None, hub_message_id: int | None = None,
                          reference: str | None = None) -> str:
        """Read original messages using the exact search reference. Old integer/hub_id/message_id calls remain supported; never reuse another archive's numeric ID."""
        return json.dumps(read_archive(db, conversation_id, start=start, end=end, hub_id=hub_id,
                                       hub_message_id=hub_message_id, reference=reference), ensure_ascii=False)

    @server.tool(annotations=readonly)
    def list_projects(include_hub: bool = False) -> str:
        """List project IDs, source paths, direct links, and conversation counts. include_hub=true returns both lists with per-endpoint coverage and an unavailable reason; the default Local array is unchanged."""
        return json.dumps(combined_listing(db) if include_hub else db.projects(), ensure_ascii=False)

    @server.tool(annotations=readonly)
    def resolve_project(cwd: str) -> str:
        """Find the configured project for a working directory or its nearest parent."""
        return json.dumps(db.resolve_project(cwd), ensure_ascii=False)

    @server.tool(annotations=readonly)
    def list_document_sources(hub: bool = False, include_hub: bool = False) -> str:
        """List explicitly configured Local sources by default. include_hub=true returns both endpoints with coverage and an unavailable reason while preserving Local results. hub=true requests only Hub. No scan or sync. Configure with Web or smm documents; supports UTF-8 Markdown/TXT only."""
        return json.dumps(combined_listing(db, sources=True) if include_hub else hub_sources(db) if hub else documents.sources(), ensure_ascii=False)

    @server.tool(annotations=readonly)
    def search_documents(query: str, scope: str = 'all', project_id: StrictInt | None = None, limit: StrictInt = 5, local: bool = False, hub_project_id: StrictInt | None = None) -> str:
        """Search captured local and Hub documents with a common direct project range and local reranking. local=true uses local links; hub_project_id selects an explicit remote root. Never scans files. Results include capture version, coverage and a signed reference; use read_document for evidence."""
        return json.dumps(document_search(db,query, scope=scope, project_id=project_id, hub_project_id=hub_project_id,limit=limit,local=local), ensure_ascii=False)

    @server.tool(annotations=readonly)
    def read_document(reference: str, start: StrictInt | None = None, end: StrictInt | None = None) -> str:
        """Read a captured document using its exact search reference. Default is the hit window; optional whole-file Unicode codepoint [start,end) range, max16000. Old versions/qualifications require a new search. No source-file read."""
        return json.dumps(document_read(db,reference, start=start, end=end), ensure_ascii=False)

    return server


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", help="覆盖档案路径（用于独立测试实例）")
    args = parser.parse_args()
    create_mcp(Archive(args.db or shared_db_path())).run(transport="stdio")


if __name__ == "__main__":
    main()
