---
name: smm-search
description: Search archived Agent conversations, manage SMM sync, or configure a multi-computer archive hub. Use for prior project decisions, fixes and preferences, or to check, sync, pause or resume the archive. Do not use for information only in the current chat.
---

# SMM conversation archive

Use the `smm-local` MCP tools when `configure_hub` is available. If this session has an older MCP or no MCP, use the Skill's first-use launcher for the entire request, including search and evidence reads. Use the scripts next to this `SKILL.md`, with paths resolved relative to this Skill directory:

- macOS and Linux: `sh "<skill-directory>/scripts/first_use.sh" <arguments>`
- Windows: invoke `"<skill-directory>\scripts\first_use.ps1"` with `&` in PowerShell, followed by the arguments.

The launcher installs the supported SMM Local package from the Python package index on first use or finds the existing installation for this OS account. It reports stages and download progress, and handles interrupted downloads and installation retries. Tell the user that first use is installing and relay progress when the install is still running. If the shell moves the command to a background task, keep following that same task and its output until it finishes. Do not launch another copy or treat a still-running command as a failure. Then continue the original request through the launcher even when the newly registered MCP tools are not visible yet. Do not ask the user to install Python, run an SMM command, or restart the Agent to complete the first request. If the launcher ultimately fails, explain the specific error.

## Maintain conversation sync

Call `manage_sync` with the action that matches the user's request:

| Request | Action | What to report |
| --- | --- | --- |
| 查看同步状态 / check sync status | `status` | Service and pause state, source availability and counts, last completed sync and errors. Use `sync.last_result.finished_at` for the last completed sync if available. |
| 打开状态页 / open the status page | `open` | Confirm if `opened` is true. Otherwise give the returned `url` as a clickable link. |
| 立即同步 / sync now | `sync` | Report new conversations and messages and any errors in `result`. If `running` is true, say it is still running and use `status` to check progress. |
| 暂停同步 / pause automatic sync | `pause` | Confirm the saved pause. An in-flight sync can finish. Explicit one-off sync and searches are still available. |
| 恢复同步 / resume automatic sync | `resume` | Confirm the change and whether sync is in progress. |

For a specific source, find its ID in status and pass `source` with status or sync. To enable or disable it, call `set_source_enabled` with the ID, or pass `source enable|disable <ID>` to the launcher. The source state and global pause are independent. To add a new source, use `smm-source-adapter`.

For maintenance requests, the management tool result is sufficient. Zero archived conversations can be a valid status; report what SMM sees and ask before investigating unrelated directories or configuration.

If MCP or this tool is unavailable, pass `maintenance <action> [--source ID]` to the launcher. Use an argument vector or quote paths for the current shell.

The local tool starts the service when needed and reuses it if running. Only use `resume` when the user asks to resume automatic sync. Treat a failed tool response as a failure, not as confirmation.

## Search archived conversations

Before searching, call `manage_sync(action="status")` (or `maintenance status` through the launcher) to ensure the local service is available. If startup fails, still search existing archives and mention that they may be out of date. If automatic sync is enabled and the first import has not finished or the user needs very recent history, use `sync` and check its result before relying on the search. If the import is still running, report that results may be incomplete.

1. Determine scope. For work tied to a project, call `resolve_project` with the current working directory, then search with `scope="project"` and that `project_id`. This includes directly linked projects. Use `scope="all"` when the user asks across projects, the project cannot be resolved, or a focused search misses relevant history. State the scope when it matters to the answer.
2. Search with a few distinctive terms from the user's question. Adjust terms and search again if the results contain plausible leads but not the needed evidence. Do not infer that no information exists from a project-scoped miss alone.
3. Examine the source, project, time, and matched message positions. Search previews may be abbreviated; use `read_conversation` with the conversation ID and relevant positions to inspect complete messages before answering. Distinguish the archived user's statement from an assistant's proposal or speculation.
4. Cite the computer name, Agent type, original source conversation ID and original message position. For a hub result, use that message's `origins` and `source_position`. Pass the exact returned `hub_id` to `read_conversation` or launcher `read --hub-id`. Read the entire conversation, or pass the returned `hub_message_id` (launcher `--hub-message-id`) for an exact message. If reading remote evidence fails, search again and report the actual scope; never use the same numeric ID against another archive.

When the user requests this computer or a local plugin source, pass `local=true` to MCP or `--local` to the launcher.

If `archive_scope` is `hub`, search covered all devices in the hub. Local project IDs do not filter the hub. If `archive_scope` is `local` and `fallback_reason` is present, tell the user that the hub was unavailable and this search covered only this computer. An empty hub result is not a connection failure.

MCP tools: `list_projects`, `resolve_project`, `search_conversations`, `read_conversation`.

Launcher arguments: `projects`, `resolve-project --cwd "$PWD"`, `search "terms" --scope project --project-id ID`, `read ID --start POSITION --end POSITION`.

The MCP/CLI adapter excludes the current conversation by default when `CODEX_THREAD_ID`, `CODEX_SESSION_ID`, or `CLAUDE_SESSION_ID` is available. Set `include_current=true` only when earlier content from this same conversation is needed. If the Agent does not expose its session ID, pass `current_session_id` explicitly when known.

## Configure the aggregation computer

When the user asks to link this computer to an aggregation computer, take the address and this computer's name from their request. Call `configure_hub(address, device_name)`, or pass `configure-hub <address> <device_name>` to the launcher. If the user supplies a credential file path, include `token_file` or `--token-file <path>`. If the result says `needs_token`, ask for the path to the credential file provided by the hub administrator. Do not read its contents into the conversation.

Report whether the configuration was saved and the hub is reachable. When reachable, SMM starts the first upload if automatic sync is enabled. The background service retries pending records after reconnecting. A saved but offline hub still allows local search.
