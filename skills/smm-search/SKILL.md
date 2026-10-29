---
name: smm-search
description: Search and read the user's archived AI conversations when prior project decisions, experiments, fixes, or preferences may help the current task. Use the shared SMM archive across projects; do not use it for information only in the current chat.
---

# Search archived conversations

Use the `smm-local` MCP tools when available. If MCP is unavailable and a local shell is available, use the installed `smm` CLI; both read the same archive. If `smm` is not on `PATH`, use `$HOME/.local/bin/smm`. The installer records its current location in `$HOME/.local/share/smm-local/install.json`.

1. Determine scope. For work tied to a project, call `resolve_project` with the current working directory, then search with `scope="project"` and that `project_id`. This includes directly linked projects. Use `scope="all"` when the user asks across projects, the project cannot be resolved, or a focused search misses relevant history. State the scope when it matters to the answer.
2. Search with a few distinctive terms from the user's question. Adjust terms and search again if the results contain plausible leads but not the needed evidence. Do not infer that no information exists from a project-scoped miss alone.
3. Examine the source, project, time, and matched message positions. Call `read_conversation` for the useful conversation, optionally passing a position range. Distinguish the archived user's statement from an assistant's proposal or speculation.
4. Cite the source conversation ID and relevant position when using archived information. If the evidence is incomplete, say what is missing rather than presenting a search hit as a verified answer.

MCP tools: `list_projects`, `resolve_project`, `search_conversations`, `read_conversation`.

CLI equivalents: `smm projects`, `smm resolve-project --cwd "$PWD"`, `smm search "terms" --scope project --project-id ID`, `smm read ID --start POSITION --end POSITION`. Replace `smm` with `$HOME/.local/bin/smm` when needed.

The MCP/CLI adapter excludes the current conversation by default when `CODEX_THREAD_ID`, `CODEX_SESSION_ID`, or `CLAUDE_SESSION_ID` is available. Set `include_current=true` only when earlier content from this same conversation is needed. If the Agent does not expose its session ID, pass `current_session_id` explicitly when known.
