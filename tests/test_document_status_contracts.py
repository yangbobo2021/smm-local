"""B2/B3/B5/B6 metadata and B8 directory guidance found by PR39 v2."""

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timezone

import pytest
from test_hub_documents_contracts import w
from test_document_pr39_contracts import actual_browser
from document_helpers import observe, deny_source_reads
from copy import deepcopy
from smm_local import references


def moment(value):
    parsed = datetime.fromisoformat(value)
    assert parsed.tzinfo is not None
    return parsed


def status_world(w, tmp_path):
    p, q = w.project("Status P"), w.project("Status Q")
    expected = {}
    paths = []
    local_sources = []
    for name, text, project in [
        ("received-one.txt", "statusmetanonce original one", p),
        ("received-two.md", "statusmetanonce 独立二😀", q),
    ]:
        path, source = w.source(name, text, [project])
        row = w.local.files(source)[0]
        paths.append(path)
        local_sources.append(source)
        expected[(w.device, w.archive, row["id"])] = {
            "text": text,
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
            "captured_at": row["captured_at"],
            "project": project,
            "source": source["id"],
            "kind": "device",
        }
    before_receive = datetime.now(timezone.utc)
    w.policy(p)
    w.policy(q)
    w.sync()
    after_receive = datetime.now(timezone.utc)

    def seed_cli(*args):
        run = subprocess.run(
            [
                sys.executable,
                "-X",
                "utf8",
                "-m",
                "smm_hub.cli",
                "hub",
                "--state-dir",
                str(w.pair.remote.db_path.parent),
                "documents",
                *map(str, args),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        observe(
            "status-seed-cli",
            {
                "args": args,
                "exit": run.returncode,
                "stdout": run.stdout,
                "stderr": run.stderr,
            },
        )
        assert run.returncode == 0, run.stderr
        return json.loads(run.stdout)

    hp = w.hub_project("Native status")
    hq = w.hub_project("Native second binding")
    native_before = datetime.now(timezone.utc)
    asset = w.upload(hp, "native.txt", "statusmetanonce native original", hub=True)
    w.remote(
        "PUT",
        "/documents/sources/" + asset["source_id"],
        {
            **w.project_context(hp),
            "project_ids": [hp["id"], hq["id"]],
            "exclude": [],
            "recursive": True,
        },
    )
    seed_cli("refresh", "--source-id", asset["source_id"])
    native_after = datetime.now(timezone.utc)
    expected[
        (w.context()["hub_id"], references.material(w.pair.remote)[0], asset["id"])
    ] = {
        "text": "statusmetanonce native original",
        "sha256": hashlib.sha256(b"statusmetanonce native original").hexdigest(),
        "project": [hp["id"], hq["id"]],
        "source": asset["source_id"],
        "kind": "hub",
    }
    unbound_path = tmp_path / "native-unbound.txt"
    unbound_text = "statusmetanonce unbound native"
    unbound_path.write_text(unbound_text)
    unbound_before = datetime.now(timezone.utc)
    unbound_source = seed_cli("add", unbound_path)
    seed_cli("refresh", "--source-id", unbound_source["id"])
    unbound_after = datetime.now(timezone.utc)
    unbound_file = seed_cli("files", "--source-id", unbound_source["id"])[0]
    expected[
        (
            w.context()["hub_id"],
            references.material(w.pair.remote)[0],
            unbound_file["id"],
        )
    ] = {
        "text": unbound_text,
        "sha256": hashlib.sha256(unbound_text.encode()).hexdigest(),
        "project": [],
        "source": unbound_source["id"],
        "kind": "hub",
        "window": (unbound_before, unbound_after),
    }
    paths.extend([Path(asset["path"]), unbound_path])
    expected_projects = {
        key: (
            {w.hub_project_for(value["project"])["id"]}
            if value["kind"] == "device"
            else set(value["project"])
        )
        for key, value in expected.items()
    }

    return (
        p,
        q,
        expected,
        paths,
        local_sources,
        expected_projects,
        (before_receive, after_receive),
        (native_before, native_after),
    )


# @case-id: TC-007-hub-status-provenance
def test_hub_status_provenance(w, monkeypatch, tmp_path):
    (
        p,
        q,
        expected,
        paths,
        local_sources,
        expected_projects,
        received_window,
        native_window,
    ) = status_world(w, tmp_path)
    before_receive, after_receive = received_window
    native_before, native_after = native_window

    def cli_files(source=None, command="files", selfcheck=False):
        protected = [os.path.normcase(str(path.resolve())) for path in paths]
        code = (
            "import json,os,pathlib,sys\nprotected="
            + repr(protected)
            + '\ndef hook(event,args):\n if event=="open" and isinstance(args[0],(str,bytes)) and os.path.normcase(str(pathlib.Path(os.fsdecode(args[0])).resolve())) in protected:raise AssertionError("status CLI opened source body")\nsys.addaudithook(hook)\nfrom smm_hub.cli import main\nsys.argv='
            + repr(
                [
                    "smm-hub",
                    "hub",
                    "--state-dir",
                    str(w.pair.remote.db_path.parent),
                    "documents",
                    command,
                ]
                + (["--source-id", source] if source else [])
            )
            + ("\nopen(protected[0], 'rb')" if selfcheck else "\nmain()")
        )
        run = subprocess.run(
            [sys.executable, "-X", "utf8", "-c", code],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        observe(
            "metadata-cli",
            {
                "source": source,
                "exit": run.returncode,
                "stdout": run.stdout,
                "stderr": run.stderr,
            },
        )
        if selfcheck:
            assert run.returncode != 0 and "status CLI opened source body" in run.stderr
            return
        assert run.returncode == 0, run.stderr
        return json.loads(run.stdout)

    def verify(rows):
        keys = []
        for row in rows:
            key = tuple(
                row["origin"][field]
                for field in ["device_id", "archive_id", "document_id"]
            )
            keys.append(key)
            item = expected[key]
            assert (
                row["origin_kind"] == item["kind"]
                and set(row["project_ids"]) == expected_projects[key]
            )
            assert (
                row["sha256"] == item["sha256"]
                and row["version"] == 1
                and row["text_length"] == len(item["text"])
            )
            assert row["qualification"] == 1
            assert row["source_origin"]["source_id"] == item["source"]
            if item["kind"] == "device":
                assert row["source_origin"] == {
                    "kind": "device",
                    "device_id": key[0],
                    "archive_id": key[1],
                    "source_id": item["source"],
                    "project_key": next(
                        p["stable_key"]
                        for p in w.pair.local.projects()
                        if p["id"] == item["project"]
                    ),
                }
            else:
                assert row["source_origin"] == {
                    "kind": "hub",
                    "hub_id": w.context()["hub_id"],
                    "source_id": item["source"],
                }
            assert "text" not in row and row["status"] == "ready"
            if item["kind"] == "device":
                assert (
                    row["device_name"] == w.config["device_name"]
                    and row["captured_at"] == item["captured_at"]
                )
                assert before_receive <= moment(row["received_at"]) <= after_receive
            else:
                window = item.get("window", (native_before, native_after))
                assert (
                    row["received_at"] is None
                    and window[0] <= moment(row["captured_at"]) <= window[1]
                )
        assert len(set(keys)) == len(keys)
        return set(keys)

    def verify_sources(sources):
        assert len(sources) == len(expected)
        origins = [(s["origin"]["kind"], s["origin"]["source_id"]) for s in sources]
        assert len(set(origins)) == len(expected) and set(origins) == {
            (v["kind"], v["source"]) for v in expected.values()
        }
        for source in sources:
            own = [
                key
                for key, value in expected.items()
                if value["source"] == source["origin"]["source_id"]
            ]
            assert len(own) == 1
            for rows in [
                w.remote("GET", "/documents/files?source_id=" + source["id"]),
                cli_files(source["id"]),
            ]:
                assert verify(rows) == set(own)
            assert (
                "latest_document_captured_at" in source
                and "latest_document_received_at" in source
            )
            item = expected[own[0]]
            assert (
                set(source["project_ids"]) == expected_projects[own[0]]
                and source["status"] == "ready"
            )
            assert (
                source["read_only"] is (item["kind"] == "device")
                and "text" not in source
            )
            assert source["revision"] == (
                2 if item["kind"] == "hub" and item["project"] else 1
            )
            if item["kind"] == "device":
                assert source["origin"] == {
                    "kind": "device",
                    "device_id": own[0][0],
                    "archive_id": own[0][1],
                    "source_id": item["source"],
                    "project_key": next(
                        p["stable_key"]
                        for p in w.pair.local.projects()
                        if p["id"] == item["project"]
                    ),
                }
                assert source["latest_document_captured_at"] == item["captured_at"]
            else:
                assert source["origin"] == {
                    "kind": "hub",
                    "hub_id": w.context()["hub_id"],
                    "source_id": item["source"],
                }
                window = item.get("window", (native_before, native_after))
                assert (
                    window[0]
                    <= moment(source["latest_document_captured_at"])
                    <= window[1]
                )
            if source["origin"]["kind"] == "device":
                assert (
                    before_receive
                    <= moment(source["latest_document_received_at"])
                    <= after_receive
                )
            else:
                assert source["latest_document_received_at"] is None

    # Verify the new assertion helper on independent known metadata before product output.
    sample_key = next(iter(expected))
    sample = expected[sample_key]
    key = next(
        p["stable_key"] for p in w.pair.local.projects() if p["id"] == sample["project"]
    )
    known = {
        "origin": dict(zip(["device_id", "archive_id", "document_id"], sample_key)),
        "origin_kind": "device",
        "device_name": w.config["device_name"],
        "project_ids": list(expected_projects[sample_key]),
        "sha256": sample["sha256"],
        "version": 1,
        "text_length": len(sample["text"]),
        "qualification": 1,
        "source_origin": {
            "kind": "device",
            "device_id": sample_key[0],
            "archive_id": sample_key[1],
            "source_id": sample["source"],
            "project_key": key,
        },
        "captured_at": sample["captured_at"],
        "received_at": before_receive.isoformat(),
        "status": "ready",
    }
    assert verify([known]) == {sample_key}
    for field, value in [
        ("sha256", "0" * 64),
        ("project_ids", []),
        ("qualification", 0),
        ("received_at", "2000-01-01T00:00:00+00:00"),
    ]:
        bad = deepcopy(known)
        bad[field] = value
        with pytest.raises(AssertionError):
            verify([bad])
    with pytest.raises(AssertionError):
        verify([known, known])
    assert moment("2026-11-23T00:00:00+00:00").utcoffset().total_seconds() == 0
    with pytest.raises(AssertionError):
        moment("2026-11-23T00:00:00")
    cli_files(selfcheck=True)
    with monkeypatch.context() as audit_check:
        attempted = deny_source_reads(audit_check, *paths)
        with pytest.raises(AssertionError):
            paths[0].read_bytes()
        assert len(attempted) == 1
    observe(
        "status-probe-selfcheck",
        {
            "valid_metadata": True,
            "invalid_sha_project_qualification_time_duplicate_rejected": True,
            "python_and_cli_audits_block_actual_source_open": True,
        },
    )
    before = w.snapshot()
    with monkeypatch.context() as guard:
        attempts = deny_source_reads(guard, *paths)
        for rows in [w.remote("GET", "/documents/files"), cli_files()]:
            assert verify(rows) == set(expected)
        for sources in [
            w.remote("GET", "/documents/sources"),
            cli_files(command="sources"),
        ]:
            verify_sources(sources)

    assert not attempts and w.snapshot() == before


# @case-id: TC-007-hub-retained-state
def test_hub_retained_state(w, tmp_path):
    (
        p,
        q,
        expected,
        paths,
        local_sources,
        expected_projects,
        received_window,
        native_window,
    ) = status_world(w, tmp_path)
    active = w.search_hub(query="statusmetanonce", limit=50)
    old = {
        tuple(h["origin"][k] for k in ["device_id", "archive_id", "document_id"]): h
        for h in active["results"]
    }
    assert set(old) == set(expected) and len(old) == len(active["results"])

    def assert_allowed_sources(rows, paused=False):
        assert len(rows) == len(expected)
        assert {r["origin"]["source_id"] for r in rows} == {
            item["source"] for item in expected.values()
        }
        expected_sources = {
            item["source"]: (key, item) for key, item in expected.items()
        }
        for source in rows:
            key, item = expected_sources[source["origin"]["source_id"]]
            kind = item["kind"]
            if kind == "device":
                expected_origin = {
                    "kind": "device",
                    "device_id": key[0],
                    "archive_id": key[1],
                    "source_id": item["source"],
                    "project_key": next(
                        p["stable_key"]
                        for p in w.pair.local.projects()
                        if p["id"] == item["project"]
                    ),
                }
            else:
                expected_origin = {
                    "kind": "hub",
                    "hub_id": key[0],
                    "source_id": item["source"],
                }
            retained = paused and kind == "device" and item["project"] == p
            assert source["origin"] == expected_origin
            assert source["sync_state"] == (
                "paused" if retained else "allowed" if kind == "device" else "native"
            )
            assert source["retained_snapshot"] is retained
            assert ("暂停" in source["sync_message"]) is retained
            assert set(source["project_ids"]) == expected_projects[key]

    def assert_allowed_hits(hits, paused=False):
        assert len(hits) == len(expected)
        assert {
            tuple(h["origin"][k] for k in ["device_id", "archive_id", "document_id"])
            for h in hits
        } == set(expected)
        for hit in hits:
            key = tuple(
                hit["origin"][k] for k in ["device_id", "archive_id", "document_id"]
            )
            item = expected[key]
            retained = paused and item["kind"] == "device" and item["project"] == p
            assert hit["retained_snapshot"] is retained and len(hit["sync_states"]) == 1
            assert hit["sync_states"][0]["state"] == (
                "paused"
                if retained
                else "allowed" if item["kind"] == "device" else "native"
            )
            assert hit["sync_states"][0]["source_id"] == item["source"]

    assert_allowed_sources(w.remote("GET", "/documents/sources"))
    assert_allowed_hits(active["results"])
    w.policy(p, False)
    w.sync()
    status = w.status()
    choice = next(x for x in status["projects"] if x["project_id"] == p)
    assert (
        choice["state"] == "paused"
        and choice["generation"] == choice["confirmed_generation"]
    )
    paused_sources = w.remote("GET", "/documents/sources")
    assert_allowed_sources(paused_sources, paused=True)
    p_source = next(
        s for s in paused_sources if s["origin"]["source_id"] == local_sources[0]["id"]
    )
    q_source = next(
        s for s in paused_sources if s["origin"]["source_id"] == local_sources[1]["id"]
    )
    assert (
        p_source["sync_state"] == "paused"
        and p_source["retained_snapshot"] is True
        and "保留" in p_source["sync_message"]
    )
    assert (
        q_source["sync_state"] == "allowed" and q_source["retained_snapshot"] is False
    )
    paused = w.search_hub(query="statusmetanonce", limit=50)
    assert_allowed_hits(paused["results"], paused=True)
    assert len(paused["results"]) == len(expected)
    assert {
        tuple(h["origin"][k] for k in ["device_id", "archive_id", "document_id"])
        for h in paused["results"]
    } == set(expected)
    for hit in paused["results"]:
        key = tuple(
            hit["origin"][k] for k in ["device_id", "archive_id", "document_id"]
        )
        item = expected[key]
        retained = item["kind"] == "device" and item["project"] == p
        assert (
            hit["retained_snapshot"] is retained
            and hit["reference"] == old[key]["reference"]
        )
        assert any(s["state"] == "paused" for s in hit["sync_states"]) is retained
        assert w.read_hub(hit)["text"] == item["text"]
    pw = pytest.importorskip("playwright.sync_api")
    with actual_browser(w, "hub") as (page, requests):
        page.goto("http://localhost:18765/")
        page.locator("#credential").set_input_files(str(w.pair.token_file))
        pw.expect(page.locator("#workspace")).to_be_visible()
        row = page.locator("#hub-sources .result").filter(has_text=p_source["id"])
        pw.expect(row).to_be_visible()
        assert "保留" in row.inner_text() and "暂停" in row.inner_text()
        page.locator("#hub-project").select_option(str(w.hub_project_for(p)["id"]))
        page.locator("#hub-query").fill("statusmetanonce")
        page.locator("#hub-search-form").evaluate("(f)=>f.requestSubmit()")
        pw.expect(page.locator("#hub-results .result")).to_have_count(1)
        hit = page.locator("#hub-results .result")
        pw.expect(hit).to_be_visible()
        assert (
            "保留" in hit.inner_text() and w.config["device_name"] in hit.inner_text()
        )
    w.policy(p, True)
    w.sync()
    resumed = w.remote("GET", "/documents/sources")
    assert_allowed_sources(resumed)
    assert (
        next(s for s in resumed if s["id"] == p_source["id"])["retained_snapshot"]
        is False
    )
    result = w.search_hub(query="statusmetanonce", limit=50)
    assert_allowed_hits(result["results"])
    assert len(result["results"]) == len(expected) and all(
        h["retained_snapshot"] is False for h in result["results"]
    )
    assert {
        tuple(h["origin"][k] for k in ["device_id", "archive_id", "document_id"])
        for h in result["results"]
    } == set(expected)
    for hit in result["results"]:
        key = tuple(
            hit["origin"][k] for k in ["device_id", "archive_id", "document_id"]
        )
        assert (
            hit["reference"] == old[key]["reference"]
            and w.read_hub(hit)["text"] == expected[key]["text"]
        )

    # A shared current file carries both qualifications; pause must not freeze it.
    shared_text = "sharedstatusnonce current one"
    shared_path, shared_source = w.source("shared-status.txt", shared_text, [p, q])
    w.sync()
    initial = w.search_hub(query="sharedstatusnonce")["results"]
    assert len(initial) == 1
    w.policy(p, False)
    w.sync()
    combined = w.search_hub(query="sharedstatusnonce")["results"]
    assert len(combined) == 1
    states = {item["project_key"]: item["state"] for item in combined[0]["sync_states"]}
    project_keys = {item["id"]: item["stable_key"] for item in w.pair.local.projects()}
    assert (
        states == {project_keys[p]: "paused", project_keys[q]: "allowed"}
        and combined[0]["retained_snapshot"] is True
    )
    for project, state in [(p, "paused"), (q, "allowed")]:
        hit = w.search_hub(
            query="sharedstatusnonce",
            scope="project",
            project_id=w.hub_project_for(project)["id"],
        )["results"]
        assert len(hit) == 1
        assert {item["state"] for item in hit[0]["sync_states"]} == {state} and hit[0][
            "retained_snapshot"
        ] is (state == "paused")
        assert w.read_hub(hit[0])["text"] == shared_text
    advanced = "sharedstatusnonce advanced through allowed project"
    shared_path.write_text(advanced)
    w.local.refresh(shared_source)
    w.sync()
    hit = w.search_hub(
        query="sharedstatusnonce",
        scope="project",
        project_id=w.hub_project_for(p)["id"],
    )["results"]
    assert (
        len(hit) == 1 and hit[0]["version"] == 2 and hit[0]["retained_snapshot"] is True
    )
    assert w.read_hub(hit[0])["text"] == advanced


def document_snapshot(db):
    with db.connect() as c:
        tables = [
            r[0]
            for r in c.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND (name LIKE '%document%' OR name IN ('projects','hub_projects'))"
            )
            if not r[0].startswith("sqlite_")
        ]
        return {
            name: [
                dict(row)
                for row in c.execute('SELECT * FROM "' + name + '" ORDER BY 1')
            ]
            for name in tables
        }


# @case-id: TC-007-folder-guidance
@pytest.mark.parametrize("role", ["local", "hub"])
def test_folder_guidance(w, role, tmp_path, monkeypatch):
    pw = pytest.importorskip("playwright.sync_api")
    expect = pw.expect
    project = w.project("Directory user")
    folder = tmp_path / "example-folder"
    folder.mkdir()
    child = folder / "body.txt"
    child.write_text("foldernonce private child")
    fingerprint = (child.read_bytes(), child.stat().st_mtime_ns)
    valid = tmp_path / "valid.txt"
    valid.write_text("mixedfoldernonce independent valid")
    with monkeypatch.context() as guarded, actual_browser(w, role) as (page, requests):
        attempted = deny_source_reads(guarded, child)
        with pytest.raises(AssertionError):
            child.read_bytes()
        assert len(attempted) == 1
        attempted.clear()
        page.goto("http://localhost:18765/")
        if role == "local":
            page.locator("nav button[data-tab=documents]").click()
            page.locator("#doc-library-project").select_option(str(project))
            drop = "#doc-upload-drop"
            prefix = "doc"
            client = w.local.client
            endpoint = "/api"
            db = w.pair.local
        else:
            page.locator("#credential").set_input_files(str(w.pair.token_file))
            expect(page.locator("#workspace")).to_be_visible()
            page.locator("#hub-project-name").fill("Folder target")
            page.locator("#hub-project-create").click()
            expect(page.locator("#notice")).to_contain_text("已创建")
            drop = "#hub-drop"
            prefix = "hub"
            client = w.hub
            endpoint = "/v1"
            db = w.pair.remote
        # Observe actual directory-enumeration APIs, delegate original behavior.
        page.evaluate(
            """selector=>{
          window.folderAudit=[];window.folderSelfcheck=true;
          function observe(proto,name){if(!proto||!proto[name])return;const original=proto[name];proto[name]=function(...args){window.folderAudit.push(name);return original.apply(this,args)}}
          const instrumented=new WeakSet();
          function instrumentEntry(entry){
            if(!entry)return;const proto=Object.getPrototypeOf(entry);if(instrumented.has(proto))return;instrumented.add(proto);
            if(entry.isDirectory){const original=proto.createReader;proto.createReader=function(...args){window.folderAudit.push('createReader');const reader=original.apply(this,args);const read=reader.readEntries;reader.readEntries=function(...args){window.folderAudit.push('readEntries');const callback=args[0];args[0]=entries=>{entries.forEach(instrumentEntry);return callback(entries)};return read.apply(this,args)};return reader};for(const name of ['getDirectory','getFile'])observe(proto,name)}
            else observe(proto,'file');
          }
          observe(window.FileSystemFileEntry?.prototype,'file');
          for(const name of ['entries','values','keys',Symbol.asyncIterator])observe(window.FileSystemDirectoryHandle?.prototype,name);
          observe(window.FileSystemFileHandle?.prototype,'getFile');
          document.addEventListener('drop',event=>{
            const items=[...event.dataTransfer.items].map(item=>{const entry=item.webkitGetAsEntry?.();instrumentEntry(entry);if(entry?.isDirectory)window.folderEntry=entry;return {kind:item.kind,name:entry?.name,isDirectory:entry?.isDirectory}});
            window.folderWitness={inside:!!event.target.closest(selector),items};
            if(window.folderSelfcheck)event.stopImmediatePropagation();
          },true);
        }""",
            drop,
        )
        session = page.context.new_cdp_session(page)

        def drag(paths):
            page.locator(drop).scroll_into_view_if_needed()
            box = page.locator(drop).bounding_box()
            assert box
            data = {
                "items": [],
                "files": [str(path) for path in paths],
                "dragOperationsMask": 1,
            }
            for kind in ["dragEnter", "dragOver", "drop"]:
                session.send(
                    "Input.dispatchDragEvent",
                    {
                        "type": kind,
                        "x": box["x"] + 10,
                        "y": box["y"] + 10,
                        "data": data,
                    },
                )
            witness = page.evaluate("window.folderWitness")
            assert witness["inside"] is True
            assert {item["name"] for item in witness["items"]} == {
                path.name for path in paths
            }
            assert any(
                item["isDirectory"] is True and item["name"] == folder.name
                for item in witness["items"]
            )
            return witness

        drag([folder])
        children = page.evaluate(
            """()=>new Promise((resolve,reject)=>window.folderEntry.createReader().readEntries(entries=>resolve(entries.map(e=>e.name)),reject))"""
        )
        assert children == ["body.txt"] and page.evaluate("window.folderAudit") == [
            "createReader",
            "readEntries",
        ]
        observe(
            "folder-probe-selfcheck",
            {
                "role": role,
                "known_directory_children": children,
                "audit_detected_explicit_enumeration": page.evaluate(
                    "window.folderAudit"
                ),
                "server_child_open_blocked": True,
            },
        )
        page.evaluate("window.folderAudit=[];window.folderSelfcheck=false")
        report = page.locator("#" + prefix + "-upload-results")

        def guidance(text):
            assert re.search("目录|文件夹", text) and "来源" in text
            assert re.search("未处理|失败|拒绝", text) and "成功" not in text
            if role == "local":
                assert "添加" in text and ("刷新" in text or "refresh" in text)
            else:
                assert (
                    "Hub" in text
                    and "CLI" in text
                    and "电脑" in text
                    and ("刷新" in text or "refresh" in text)
                )

        correct = (
            "example-folder：未处理 · 文件夹请添加本机目录来源并明确刷新"
            if role == "local"
            else "example-folder：未处理 · 文件夹请在Hub电脑用Hub CLI添加目录来源并明确refresh"
        )
        guidance(correct)
        for bad in ["example-folder：成功 · 已保存", "example-folder：失败 · 不能读取"]:
            with pytest.raises(AssertionError):
                guidance(bad)
        marker = len(requests)
        before = document_snapshot(db)
        hub_before = w.snapshot()
        witness = drag([folder])
        expect(report).to_be_visible()
        expect(report).to_contain_text("example-folder")
        expect(report).to_contain_text(re.compile("目录|文件夹"), timeout=5000)
        row = report.locator("li").filter(has_text="example-folder")
        expect(row).to_have_count(1)
        expect(row).to_be_visible()
        guidance(row.inner_text())
        assert not any(
            r["method"] == "POST" and r["url"].endswith("/documents/library")
            for r in requests[marker:]
        )
        assert (
            client.get(endpoint + "/documents/library").json() == []
            and document_snapshot(db) == before
            and w.snapshot() == hub_before
        )
        assert not attempted and page.evaluate("window.folderAudit") == []
        observe(
            "actual-folder-guidance",
            {
                "role": role,
                "directory_entry": witness,
                "visible_report": row.inner_text(),
                "no_upload_or_scan": True,
                "state_unchanged": True,
            },
        )
        witness = drag([folder, valid])
        expect(report).to_contain_text("example-folder")
        expect(report).to_contain_text("valid.txt")
        directory_row = report.locator("li").filter(has_text="example-folder")
        expect(directory_row).to_have_count(1)
        guidance(directory_row.inner_text())
        valid_row = report.locator("li").filter(has_text="valid.txt")
        expect(valid_row).to_have_count(1)
        expect(valid_row).to_contain_text("成功")
        library = client.get(endpoint + "/documents/library").json()
        assert len(library) == 1 and library[0]["display_name"] == "valid.txt"
        hits = client.post(
            endpoint + "/documents/search",
            json={
                **(w.context() if role == "hub" else {}),
                "query": "mixedfoldernonce",
                "limit": 50,
            },
        ).json()["results"]
        assert len(hits) == 1 and hits[0]["id"] == library[0]["id"]
        read = client.post(
            endpoint + "/documents/read",
            json={
                **(w.context() if role == "hub" else {}),
                "reference": hits[0]["reference"],
            },
        ).json()
        assert read["text"] == "mixedfoldernonce independent valid"
        assert (
            len(client.get(endpoint + "/documents/sources").json()) == 1
            and not attempted
            and page.evaluate("window.folderAudit") == []
        )
        observe(
            "actual-mixed-folder-guidance",
            {
                "role": role,
                "directory_entry": witness,
                "visible_report": report.inner_text(),
                "library": library,
                "read": read,
                "no_directory_scan": True,
            },
        )
    assert (child.read_bytes(), child.stat().st_mtime_ns) == fingerprint
