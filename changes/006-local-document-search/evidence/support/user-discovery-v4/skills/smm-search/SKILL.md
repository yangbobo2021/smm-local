---
name: smm-search
description: Search archived Agent conversations or explicitly captured local documents, manage SMM sync, or configure a multi-computer archive hub. Use for prior project decisions and evidence, configured document knowledge, or archive maintenance. Do not use for information only in the current chat.
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

1. Determine scope. For work tied to a project, call `resolve_project` with the current working directory, then search with `scope="project"` and that `project_id`. This includes directly linked projects. When the search runs on a configured SMM Hub, project links come from the Hub and may include other devices or VibeInsight. Use the returned effective scope and fallback reason when reporting which archive was searched. Use `scope="all"` when the user asks across projects, the project cannot be resolved, or a focused search misses relevant history. State the scope when it matters to the answer.
2. Search with a few distinctive terms from the user's question. Adjust terms and search again if the results contain plausible leads but not the needed evidence. Do not infer that no information exists from a project-scoped miss alone.
3. Examine the source, project, time, and matched message positions. Search previews may be abbreviated; use `read_conversation(reference=<that hit reference>)` (launcher `read --reference <reference>`) and relevant positions to inspect complete messages before answering. Distinguish the archived user's statement from an assistant's proposal or speculation.
4. Cite the computer name, Agent type, original source conversation ID and original message position. For a Hub result, use that message's `origins` and `source_position`. When an old result has no `reference`, pass the exact returned `hub_id` to `read_conversation` or launcher `read --hub-id`. Read the entire conversation, or pass the returned `hub_message_id` (launcher `--hub-message-id`) for an exact message. If reading remote evidence fails, search again and report the actual scope; never use the same numeric ID against another archive.

When the user explicitly requests this computer, pass `local=true` to MCP or `--local` to the launcher.

With 005-capable Local and Hub, default CLI/MCP/Web search queries both archives, including unuploaded local records and local plugins. Each returns its normal N candidates; local BM25 merges and reranks their full matched messages. No local candidate body is sent for ranking. `archive_scope=combined` is top-level coverage; always read each hit's own `reference`, never combine its integer ID with the top-level Hub ID. Preserve individual `origin_references` for a merged hit. A bundle can be read whole; to restrict positions, select one of its individual references first.

For project scope, the Hub supplies one common direct-one-hop snapshot; local links do not expand it again. Explicit local search uses local links. If the Hub cannot resolve the snapshot, fallback is only the requested local project; an all-project request falls back to local all. If a valid snapshot was obtained before Hub search failed, local results can retain that snapshot with partial coverage. Report `coverage`, `effective_projects`, `fallback_reason`, `candidate_failures` and `capability_limitations` accurately; do not present missing endpoints as searched. An empty Hub result is not a connection failure. Hub links are managed through `smm-hub hub project`; local Web links apply to explicit local search.

Version boundary: 005 is not in the 0.4.0 published package currently installed by the launcher. Use these new behaviors only when the running components support them (`upload --help` for Local, `upload-policy-v1`/`query-scope-v1` Hub capabilities). Do not promise a new capability by reinstalling 0.4.0. For old results without `reference`, use that result's exact old `hub_id`/`hub_message_id` parameters; never guess archive identity or silently broaden project scope. A new Local on an old Hub stops body uploads and falls back to the requested local project for project searches.

MCP tools: `list_projects`, `resolve_project`, `search_conversations`, `read_conversation`.

Launcher arguments: `projects`, `resolve-project --cwd "$PWD"`, `search "terms" --scope project --project-id ID`, `read ID --start POSITION --end POSITION`.

The MCP/CLI adapter excludes the current conversation by default when `CODEX_THREAD_ID`, `CODEX_SESSION_ID`, or `CLAUDE_SESSION_ID` is available. Set `include_current=true` only when earlier content from this same conversation is needed. If the Agent does not expose its session ID, pass `current_session_id` explicitly when known.

## Search captured local documents (006)

Use this path only when the installed component exposes `list_document_sources`, `search_documents`, and `read_document`, or `documents --help` succeeds in its actual CLI environment. The published 0.4.0 package and first-use launcher do not yet include 006; reinstalling 0.4.0 does not add it. An unpublished source/wheel preview is described in the repository's README and TRIAL_GUIDE. Report an unsupported installed version accurately; do not pretend a conversation search searched documents.

1. Call `list_document_sources` to check explicit roots, bound local project IDs and pending/refreshing/partial/failed coverage. This does not scan or refresh. For a project use `list_projects`/`resolve_project` as appropriate, and pass a real local ID to `search_documents(scope="project",project_id=...)`; scope expands local direct one-hop links even with a Hub configured. Global projects are independent; unbound documents only join `scope="all"`.
2. Search with distinctive content terms, then pass each hit's exact `reference` to `read_document`. Default windows are at most 2000 Unicode codepoints; optional `start`/`end` are whole normalized snapshot codepoint [start,end), max16000. Never use a conversation ID/reference here or guess byte/UTF-16 offsets. Cite canonical path, capture time/version, and line/character range. Read evidence before making a claim and distinguish source text from inference.
3. These are captured UTF-8 Markdown/TXT files only, not live disk state, Word/Excel/PDF/images, or Hub documents. Only explicit Web/CLI `documents refresh` reads current files. Do not scan project roots/home or refresh just because a search missed. For authorized source management use Web “文档” or CLI `documents add <absolute-local-path> [--project-id ID ...]`, `sources`, `files`, `set`, `refresh`, `remove`. IDs come from `projects`/`documents sources`; create an ordinary identity with `project create <name>` or use `project ensure-global`.
4. Explain full replacement: set omits project/exclude lists to clear them and defaults to recursive; add/set are pending, no body read. Exclusions are POSIX `* ? **` and directory trailing `/`; hidden/build directories are excluded by default and links/junctions are never followed. Explicitly chosen actual files/subdirectories may be separate sources. Per-file2MiB, per-source1000 candidates/16MiB; partial/failed are incomplete coverage. Do not call a zero-hit result proof of absence when sources are pending or failing.
5. A refreshed content change or terminal qualification failure invalidates old refs, including later restoration of identical bytes; search again rather than substituting another source/version. Removing a source does not delete original files, but its exclusive snapshots leave search/read; other uninterrupted overlap qualifications retain the current version. No historical-version read. Unchanged refresh/restart preserves continuous valid references. Document operations do not change conversation pause/upload policies and do not send document bodies, summaries, or file lists to Hub/models. Content read into this Agent follows the Agent's normal context handling.

Configuration via CLI/Web is separate from the three read-only MCP tools. Use dedicated conversation tools when both discussions and documents are needed. Do not imply 007 Hub sync or 008 format processing is already available.

## Configure the aggregation computer

When the user asks to link this computer to an aggregation computer, take the address and this computer's name from their request. Call `configure_hub(address, device_name)`, or pass `configure-hub <address> <device_name>` to the launcher. If the user supplies a credential file path, include `token_file` or `--token-file <path>`. If the result says `needs_token`, ask for the path to the credential file provided by the hub administrator. Do not read its contents into the conversation.

Report whether configuration was saved and the Hub is reachable. With 005, a new connection initially only queries and registers minimal project/device names; body upload requires an explicit user choice. A verified migration of an already uploading device to the same Hub can preserve all. Do not infer upload permission just from a configured address. A saved offline Hub still allows local search.

For user-authorized upload choices, use the local Web configuration page or launcher `upload status`, `projects`, and `upload set --mode all|only|except|none [--project-id LOCAL_ID ...]`. IDs come from local `projects`, not the Hub list. `only` empty allows none; `except` empty allows all; all/none reject lists. MCP does not add rule-writing tools. Saving a restriction immediately stops new local dispatch; status distinguishes pending Hub confirmation and in-flight requests. Do not call pending a confirmed stop. Existing Hub copies remain; allowing again backfills missing old/new/appended records. Global pause does not prevent control confirmation and must not be resumed without the user's request.

For explicitly global conversations use `project ensure-global`, then `project assign-conversation LOCAL_CONVERSATION_ID --project-id LOCAL_PROJECT_ID`; review the returned affected conversations and confirmation before resubmitting with `--confirm`. Missing cwd remains unresolved, not automatically global. Ordinary project queries do not include global by default. Expanding map/merge changes similarly require their bound preview.

Restore uses `upload prepare-restore` before stopping the service/restoring the listed backup set; keep the excluded guard/lock files. Hub uses `smm-hub hub --state-dir <actual directory> prepare-restore`. Then `upload reconcile` only inspects differences. Explicit `--use hub` adopts Hub; `--use local --expected-hub-revision <fresh hub.revision> --expected-local-generation <fresh local.generation>` resubmits exactly the displayed local rule. Both values come from the latest `upload reconcile` output; missing/invalid/stale values reject without changing either rule. Web adoption binds both displayed versions; CLI `--use hub` protects changes made during its call. Do not auto-resolve a conflict or restore an old allow rule. Never expose credential contents in chat.
