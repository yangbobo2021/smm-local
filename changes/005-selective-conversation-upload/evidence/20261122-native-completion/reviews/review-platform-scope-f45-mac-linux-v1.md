# Independent actual-platform scope review — f45

Result: **passed for the handed-off supplemental scope only**, for all three runs. No actionable product or evidence defect was found in that scope. This is an external evidence review, not a new execution or a whole A/E delivery verdict.

I read project AGENTS.md, the native acceptance reviewer instructions, and approved change 005 intent/spec/plan. Baseline: SPEC B5/A9 for unavailable-Hub all-project fallback; B7/A8 for shared-conversation scoped reading and legacy compatibility; D4 and E1/E3/E4 for actual entrances, installed bytes, identity and restart evidence. Excluding Y's secret from a visible title follows the content boundary; the fixture's exact X title is a witness, not a new universal formatting requirement.

## Provenance

Frozen source `<task-path> is clean at `f45da53b4aa6860f5a92d80869073756dbf319f8`. Independently hashed all Python/HTML entries of both active wheels: 25 Local and 24 Hub files. These maps equal candidate and actual installed maps in each of the three manifests, including HTML. Every file matches frozen source; generated Hub `_archive/__init__.py` matches the shim transformation in `scripts/build_packages.py`. Installed environments are separate (`other_package=false`); CLI/MCP use isolated `-I` interpreters. Full hashes are in the companion JSON.

- Local wheel SHA-256: `46e8c2366fcad19654a7fcf48943434b6c09ac84df219dcdbcee58bbda3ace71`.
- Hub wheel SHA-256: `5c333e635b0b5b1d004a8a7a76eae4358458a3bdb6644068d64edbe06e9f8fdc`.
- All three recorded scope/Run/fixture controllers have identical bytes; their hashes are recorded per run.

## Run judgments

| Run | Scoped verdict | Actual environment and evidence |
|---|---|---|
| mac-scope-run11 | passed | macOS 15.3.1 arm64, UID 501 <ordinary-user>; ordinary on-demand Local service and self-managed `serve-hub`; Hub PID 81081 → 81414. Chrome 157.0.8103.50. Offline three entrances and split scope, browser and restart proved. |
| linux-scope-run11 | passed | Linux 6.8.0-149 x86_64, UID 1000 <ordinary-user>; ordinary on-demand Local and `serve-hub`; Hub PID 151956 → 152590. Chromium 159.0.8154.6. Offline three entrances and split scope, browser and restart proved. |
| linux-hub-scope-run11 | passed | Same Linux/UID 1000; actual systemd user unit `smm-hub-2df72c301e6e.service`, active PID 151977 → 152222, installed Hub interpreter and same `<task>/hub-state` in captured ExecStart. Controller checks `/proc/PID` UID against its non-root UID. Protocol-only split scope and restart proved. No browser or offline claim. |

`manifest.json`, `commands.jsonl`, `service-events.json`, `result.json` and `cleanup.json` were inspected for each run. The self-managed processes exited -15 after explicit stop requests, not an early-exit success. Both on-demand Local archives returned `ok:true` on cleanup. The systemd run's final disable returned `enabled:false/running:false`, then task unit removal and successful daemon-reload; cleanup failure arrays are empty. These are historical execution records and controller checks, not newly observed live processes.

## Actual results and independent oracles

For the two E1 supplements, `offline-all.json` CLI, real stdio MCP and browser results each contain exactly Local A,D,G,U,U2 plus `plugin-history`. I reconstructed expected values from `selective_upload_fixture.py` construction rather than trusting `expected_bodies` or the passed label: Codex sessions each have position-1 user original; plugin has position-1 user original and position-2 assistant appended text. Actual full reads match those exact texts, roles, positions, source identities, session identities and null timestamps. G maps to the explicit global project; U/U2 remain unassigned. All six per-channel reads correspond to their own result IDs/references. All three entrances return `archive_scope=local`, `effective_projects=all`, local complete/Hub unavailable, with HTTP 503 fallback explanation. Relay logs record actual failed info requests during the offline interval; product Hub request functions are not replaced.

All three `split-scope.json` files show the same two independently specified protocol inputs in one `scope-shared` Codex conversation: position 1/project Y has `OUTSIDE_Y_ONLY_SECRET_TITLE`, position 2/project X has `boundaryneedle allowed X full original`. Receipt accepted=2. Actual admin link command adds only A—X for this fixture, not Y; effective snapshot is V,A,B,X. CLI/MCP search hit and full reads, direct Hub read, and post-restart old-reference read return exactly position-2 X, with its user role, Codex/session identity, X project metadata and allowed title. Decoded reference binds actual Hub/archive, position-2 message/version and project snapshot. CLI/MCP/direct enlarged 0..999999 read bounds do not add Y. Legacy unscoped integer read returns both originals with Y title, proving Y still exists and preserving the deliberately different legacy semantics. The same pre-restart reference remains valid after actual PID change.

For Mac/Linux I opened **all four original PNGs** with `view_image`: each `selective-browser.png` visibly shows all six sessions, plugin's two roles, global/pending/ordinary labels and HTTP 503 fallback scope; reader shows final G original. Each `boundaryneedle-browser.png` shows only X in hit and reader, X title/project and position 2, and visible V,A,B,X combined scope; Y secret is absent. Each original trace has one search and six (offline) or one (split) actual read requests with HTTP 200. I inspected trace network resource bodies: searches equal saved browser search results; every read request uses that hit's reference and responses independently match saved session/source/title/full message tuples. Local trace paths are unredacted while JSON paths are redacted, so byte equality of those path fields is neither claimed nor required.

`ScopeProbe` asserts session identity and full body arrays (lines 14–15), exact offline target sets (55/29), every own-reference read (59–61/33–36), fallback (56–57/63–64), split search/read titles and projects (91–99), browser secret exclusion (37–39) and old reference after restart (101–103). `Run.mcp` uses initialized real MCP ClientSession over stdio; `Run.cli` invokes installed CLI. I additionally compared raw roles/source/metadata and browser resources, beyond its narrower body assertions.

## Counterexample check

- Only the first local target works: exact full session-set checks reject missing A,D,G,U,U2/plugin; the per-hit expected-session/full-body loop rejects a wrong second target and catches the second plugin message being omitted.
- Both entrances read the same wrong target: independently constructed per-session originals and expected session identity reject this; no cross-entrance equality is used as the body oracle. Actual browser request resources use each own reference.
- Shared conversation filters body but leaks its first Y title: first source message is outside Y, so title assertions and actual browser image/reader checks intercept it.
- Enlarged bounds expose Y: exact one-X read assertions reject it on CLI, MCP and direct Hub.
- A destructive implementation drops Y altogether or both comparison paths accidentally omit it: accepted=2 plus legacy full-body/Y-title check intercepts that false proof.
- Only pre-restart state works: changed PIDs and old reference read after restart intercept it. Systemd definition retains the same task state directory.

The fixtures cover the differing conditions of this narrow supplement. More equivalent identifiers are optional here; complete A8/A9/A11 states are not silently converted to passed.

## Limits

This does not deliver A8, A9, E1, E3 or E4 as whole requirements. In particular, these runs do not test all stopped-upload/reallow lifecycle states, stale local reconcile or recovery races, other A8 conflicts, unavailable-Hub same-ID read failure, Mac system launchd, or Windows. P1 stale-local-reconcile is still pending outside this batch per handoff; nothing here resolves it. Mac E3 remains unrun; Windows progress outside this batch is not assessed. The Linux Hub record has browser=null and no offline-all evidence. Native green records and the supplemental 187-pass/1-skip log were not used in place of actual evidence.

Companion JSON contains per-run status, limitations and SHA-256 of every supplied run evidence file. No product/test/evidence file was modified.
