# Independent Windows actual-platform scope review — f45

**Both runs passed the handed-off supplemental scope.** No actionable product/evidence defect was found within that scope. This is an external read-only review of two completed executions, not a new execution or complete A/E delivery verdict.

## Baseline and provenance

Grounding is approved change 005 intent/spec/plan: B5/A9 requires unavailable-Hub all-project fallback with all local sources and truthful coverage, through actual CLI, stdio MCP and browser in E1. B7/A8 requires shared-conversation scoped references to exclude outside-project content while retaining old unscoped semantics. D4/E1/E3 requires actual installed bytes, identities, entrances and restart evidence. Excluding the out-of-scope Y secret from visible title follows that content boundary; exact X title is a fixture witness, not a newly imposed universal title format.

I used each run's snapshot copies of `selective_upload_scope.py`, `selective_upload_platform.py`, fixture and Windows wrapper. They are byte-identical across these two runs (and the previously reviewed copies); I did not compare these receipts to the later checkout's controller version. Frozen `<task-path> is clean at `f45da53b4aa6860f5a92d80869073756dbf319f8`.

Independently hashed all Python/HTML entries in both current wheels: 25 Local and 24 Hub files. These exactly equal both Windows actual installed maps and candidate maps, including Local HTML. All entries match frozen source; generated Hub `_archive/__init__.py` matches `build_packages.py` shim transformation. Independent installed environments have `other_package=false`; product CLI/MCP subprocesses use `-I -X utf8`.

- Local wheel: `46e8c2366fcad19654a7fcf48943434b6c09ac84df219dcdbcee58bbda3ace71`.
- Hub wheel: `5c333e635b0b5b1d004a8a7a76eae4358458a3bdb6644068d64edbe06e9f8fdc`.
- Scope/Run/fixture/wrapper hashes and every evidence file hash are in the companion JSON.

## Per-run findings

| Run | Scoped judgment | Actual execution |
|---|---|---|
| windows-scope-run11 | passed | Windows 11 build 26100, Python 3.14.2; <ordinary-user> controller `elevated_admin=false`; ordinary on-demand Local; independent serve-hub PID 15732 → 12772. Edge 158.0.4370.33. Offline CLI/MCP/Edge all-project queries and reads, scoped split reads and restart are supported. |
| windows-hub-scope-run11 | passed | Same Windows build; elevated <ordinary-user> controller, distinct actual Hub `NT AUTHORITY\LocalService`; CIM process owner `LOCAL SERVICE`/ReturnValue 0 and service Running before/after restart, PID 15612 → 16276. Protocol-only CLI/MCP/API split reads and restart are supported. |

The supplied Windows wrapper defines an interactive scheduled task with Limited for client and Highest for Hub service, and checks the worker token before running. Actual manifest identity is independently produced by `IsUserAnAdmin`, with client enforcement of non-elevation. These directories do not include the outer task-registration/worker receipt; I do not claim to have independently inspected the scheduler itself. The actual ordinary-vs-elevated process token and separate LocalService Hub owner needed for this scope are evidenced.

For both runs `result.json` reports no failure; I checked actual bodies and metadata rather than using that label as proof. Both contain 33 successful recorded commands and empty cleanup failure arrays. Ordinary serve-hub exits were code 1 **after** explicit stop requests; snapshot code accepts Windows termination code 1 only when stop_requested is true, and rejects an early exit. Both Local archives' stop-on-demand calls return `ok:true`. Service cleanup returns enabled=false/running=false, followed by successful `sc.exe delete` exit 0. Its disable status contains an endpoint timeout diagnostic after stopping; I record it rather than treating this disabled endpoint as evidence of a running healthy service. No fresh remote liveness/SCM check was performed.

## Input-derived result verification

For `windows-scope-run11/offline-all.json`, I reconstructed expected original values from snapshot fixture construction: Local A,D,G,U,U2 are distinct Codex sessions, each position-1/user original; plugin-history has position-1/user original and position-2/assistant appended content. The fixture snapshot puts G in the explicit global project and U/U2 unassigned. CLI, initialized actual stdio MCP and Edge each return exactly all six sessions, each own-reference read has the correct archive/session/source and exact full original messages, roles, positions and null timestamps. Decoded references bind the correct local conversation IDs and archive scope. Search previews match those originals (MCP's documented preview field, not assumed text field). All three expose local complete/Hub unavailable, actual scope local/all and HTTP 503 explanation. Relay log shows failed actual requests in the offline interval, without replacing product network functions.

Both split-scope files contain one remote Codex conversation `scope-shared`: first message/project Y has `OUTSIDE_Y_ONLY_SECRET_TITLE`; second/project X has `boundaryneedle allowed X full original`. Actual protocol receipt accepts 2. Actual admin link adds A—X for this fixture, not A—Y. Search snapshot is V,A,B,X. CLI/MCP hit metadata and reads, direct Hub read and post-restart read return exactly position-2/user X with X title/project and correct source/session; decoded reference binds actual Hub/archive and only the position-2 message/version. Enlarging start/end to 0..999999 on CLI/MCP/API does not read Y. Legacy unscoped integer read deliberately returns both original Y,X messages and Y title, proving Y exists and preserving the distinct legacy behavior. Same old scoped reference reads X after actual PID change.

The LocalService run has browser=null, no browser images/traces and no offline-all file. Its generic result.scope text mentions offline-all because inherited ScopeProbe uses one static label. Snapshot lifecycle explicitly skips offline_all when protocol_only and skips browser in split_scope. Its result is interpreted as protocol-only, with no E1 offline/browser claim.

## Actual Edge visual and network review

I opened both original Windows PNGs with view_image. `selective-browser.png` visibly shows all six sessions, two plugin messages with different roles, A/D ordinary labels, G global label, U/U2 unassigned labels, truthful HTTP 503 all-project fallback and final U2 original reader. `boundaryneedle-browser.png` shows combined V,A,B,X scope and only the X hit and X reader, X title/project, position 2 and full allowed original; Y secret is absent.

I inspected original trace network resource bodies. Each has one actual search, followed by six offline reads or one split read, all HTTP 200 from the Local API. Search JSON exactly matches saved browser search. Each actual request uses that result hit's reference; actual response source/session/title and exact message tuple matches the saved full read and independent input. User-Agent contains Windows NT 10.0 and Edg/158.0.0.0, consistent with recorded Edge version. Local source paths differ from saved JSON only because the latter redacts task/home paths; full raw byte equality of those path fields is not claimed.

## Counterexamples against actual assertions

1. Only first offline target works: exact session-set checks (ScopeProbe 55/29) reject missing other targets; every-target own-reference loop (59–61/33–36) and checked_read (14–15) reject wrong/incomplete full bodies. Second plugin assistant content is independently checked too.
2. Both entrances read the same wrong target: expected input-derived originals/session identity, rather than equality between entrances, reject it. Trace read requests use each own reference.
3. X body is filtered but first Y title leaks: fixture intentionally puts Y first; search/read title checks (91/93/97/103), browser secret checks (37–39) and actual screenshot intercept it.
4. Expanded bounds expose Y: all three 0..999999 read calls are followed by exact one-X assertion and X project checks.
5. Y never arrived or both modern/legacy paths wrongly omit Y: accepted=2 and legacy exact Y+X/Y-title assertion (98–99) intercept that false proof.
6. Scope works only before restart: actual changed PIDs followed by old-reference exact-X/title assertion (101–103) intercept it.
7. Only elevated client or controller account works: actual ordinary client token is non-elevated; actual service CIM owner is LocalService, separate from controller identity.

Equivalent extra identifiers are optional for this narrow supplement; unexecuted complete-spec states remain uncredited.

## Limits

This report does not deliver whole A8/A9/E1/E3 or stopped-upload/backfill/recovery A11. P1 stale-local-reconcile remains pending user decision outside this batch, and Mac E3 remains unrun. The separate isolation extra14 is outside this batch and receives no credit here. Prior Mac/Linux results are not substituted for Windows evidence, nor are unit/native greens. Only these two new opinion files were written; product, tests and supplied evidence were not modified.
