"""Synthetic source fixtures for Hub synchronization through its normal archive."""
from pathlib import Path

import pytest

from smm_local.core import Archive


def event(number, session, role, project="git.example/team/alpha", *, trace=None, created=None, text=None):
    return {
        "id": f"event-{number:04d}", "user_id": "owner", "platform_code": "codex",
        "session_id": session, "trace_id": trace or f"trace-{number // 2}",
        "event_type": {"user": "trace.started", "assistant": "trace.completed"}[role],
        "message": text or f"evidence {session} {number}", "project": project,
        "event_timestamp": f"2026-09-14T00:{number:02d}:00",
        "created_at": created or f"2026-09-14T00:{number:02d}:00",
    }


def position(row):
    return row["created_at"], row["id"]


class FixtureSource:
    def __init__(self, rows, projects):
        self.rows = rows
        self.visible = projects
        self.fail = False

    def validate(self):
        return None

    def projects(self, through=None):
        return self.visible

    def upper(self):
        return max((position(row) for row in self.rows if row["project"] in self.visible), default=None)

    def page(self, project, after, through, limit):
        if self.fail:
            raise RuntimeError("fixture connection unavailable")
        return sorted((row for row in self.rows if row["project"] == project
                       and (after is None or position(row) > after) and position(row) <= through),
                      key=position)[:limit]


def synchronizer(path: Path):
    from smm_hub.vibeinsight import VibeInsightSync

    return VibeInsightSync(Archive(path), "fixture", batch_size=2)


def test_all_visible_projects_and_historical_discovery(tmp_path):
    alpha, beta, gamma = ("git.example/team/" + name for name in ("alpha", "beta", "gamma"))
    source = FixtureSource(
        [event(8, "alpha", "user", alpha), event(9, "beta", "user", beta),
         event(1, "gamma", "user", gamma)],
        [alpha, beta],
    )
    database = tmp_path / "hub.sqlite3"
    run = synchronizer(database)
    run.run(source)
    hits = Archive(database).search("evidence")["results"]
    assert len(hits) == 2
    assert {Archive(database).read(hit["id"])["messages"][0]["text"] for hit in hits} == {
        "evidence alpha 8", "evidence beta 9",
    }
    source.visible.append(gamma)
    run.run(source)
    hits = Archive(database).search("evidence")["results"]
    assert {Archive(database).read(hit["id"])["messages"][0]["text"] for hit in hits} == {
        "evidence alpha 8", "evidence beta 9", "evidence gamma 1",
    }


def test_resume_appends_to_same_conversation_in_source_order(tmp_path):
    alpha = "git.example/team/alpha"
    rows = [event(n, "old", "user" if n % 2 == 0 else "assistant") for n in range(6)]
    source = FixtureSource(rows, [alpha])
    database = tmp_path / "hub.sqlite3"
    synchronizer(database).run(source)
    store = Archive(database)
    original, = store.search("evidence")["results"]
    before = store.read(original["id"])["messages"]
    rows.extend([event(n, "old", "user" if n % 2 == 0 else "assistant") for n in range(6, 10)])
    rows.append(event(12, "new", "user"))
    resumed = synchronizer(database)
    resumed.run(source)
    resumed.run(source)
    assert len(store.search("evidence")["results"]) == 2
    assert store.search("old")["results"][0]["id"] == original["id"]
    after = store.read(original["id"])["messages"]
    assert after[:6] == before
    assert [(msg["role"], msg["text"]) for msg in after] == [
        ("user" if n % 2 == 0 else "assistant", f"evidence old {n}") for n in range(10)
    ]


def test_failed_batch_retries_and_late_event_is_read_once(tmp_path):
    alpha = "git.example/team/alpha"
    rows = [event(0, "old", "user"), event(1, "old", "assistant")]
    source = FixtureSource(rows, [alpha])
    database = tmp_path / "hub.sqlite3"
    sync = synchronizer(database)
    sync.run(source)
    store = Archive(database)
    hit, = store.search("evidence")["results"]
    source.fail = True
    rows.extend([event(2, "old", "user"), event(4, "other", "user")])
    with pytest.raises(RuntimeError, match="fixture connection unavailable"):
        sync.run(source)
    assert len(store.read(hit["id"])["messages"]) == 2
    source.fail = False
    sync.run(source)
    rows.append(event(3, "old", "assistant"))
    rows[1]["message"] = "in-place historical edit"
    synchronizer(database).run(source)
    synchronizer(database).run(source)
    assert [msg["text"] for msg in store.read(hit["id"])["messages"]] == [
        f"evidence old {n}" for n in range(4)
    ]


def fixture_source(config, password):
    import json
    if password != "synthetic-reader-password":
        raise RuntimeError("fixture authentication rejected")
    raw = json.loads(Path(config["host"]).read_text(encoding="utf-8"))
    result = FixtureSource(raw["rows"], raw["projects"])
    result.fail = raw["fail"]
    return result


def run_test_entry():
    import functools
    import sys

    from smm_hub import vibeinsight_settings

    settings = functools.partial(vibeinsight_settings.VibeInsightSettings, source_factory=fixture_source)
    if sys.argv[1] == "serve":
        import uvicorn
        from smm_hub.hub import create_hub

        state, port = Path(sys.argv[2]), int(sys.argv[3])
        archive = Archive(state / "smm-hub.sqlite3")
        app = create_hub(archive, "h" * 40, lifespan=settings(state, archive).lifespan)
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
    else:
        from smm_hub.cli import main

        vibeinsight_settings.VibeInsightSettings = settings
        main()


def test_managed_hub_credential_restart_and_mixed_project_search(tmp_path, monkeypatch):
    import asyncio
    import json
    import os
    import socket
    import subprocess
    import sys
    from urllib.error import URLError
    from urllib.request import Request, urlopen

    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    from smm_local.federation import configure_hub, push_pending
    from test_federation import cli, eventually, record_codex

    monkeypatch.setenv("PYTHONPATH", str(Path(__file__).resolve().parents[1] / "src"))
    launcher = [sys.executable, "-c",
                f"import runpy; runpy.run_path({str(__file__)!r})['run_test_entry']()"]
    state = tmp_path / "hub"
    state.mkdir()
    data = tmp_path / "fixture.json"
    password = tmp_path / "password"
    password.write_text("synthetic-reader-password", encoding="utf-8")
    token = tmp_path / "hub-token"
    token.write_text("h" * 40, encoding="ascii")
    alpha, beta, gamma = ("git.example/team/" + name for name in ["alpha", "beta", "gamma"])
    rows = [event(n, "vibe-A", "user" if n % 2 == 0 else "assistant", alpha)
            for n in range(10, 16)]
    rows.extend([event(16, "vibe-B", "user", beta), event(1, "vibe-C", "user", gamma)])

    def write_source(projects, *, fail=False):
        temporary = data.with_suffix(".tmp")
        temporary.write_text(json.dumps({"rows": rows, "projects": projects, "fail": fail}), encoding="utf-8")
        temporary.replace(data)

    def admin(*args, expected=0):
        result = subprocess.run(launcher + ["hub", "--state-dir", str(state), *args],
                                capture_output=True, text=True, timeout=10)
        assert result.returncode == expected, result.stderr
        assert "synthetic-reader-password" not in result.stdout + result.stderr
        return json.loads(result.stdout) if expected == 0 else result.stderr

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    address = f"http://127.0.0.1:{port}"

    def hub_call(route, payload=None):
        request = Request(address + "/v1/" + route,
                          data=json.dumps(payload).encode() if payload is not None else None,
                          headers={"Content-Type":"application/json", "Authorization":"Bearer " + "h" * 40})
        try:
            with urlopen(request, timeout=2) as response:
                return json.load(response)
        except URLError:
            return None

    def start():
        service = subprocess.Popen(launcher + ["serve", str(state), str(port)])
        try:
            eventually(lambda: hub_call("info"))
        except BaseException:
            stop(service)
            raise
        return service

    def stop(process):
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)

    def query(word="evidence"):
        result = hub_call("search", {"query": word, "limit": 20})
        return result["results"] if result else []

    write_source([alpha, beta])
    config = ["vibeinsight", "configure", "--host", str(data), "--database", "fixture", "--user", "reader",
              "--interval", "1", "--password-file", str(password)]
    assert admin(*config)["credential_saved"]
    stored_profile = (state / "vibeinsight.json").read_bytes()
    assert b"synthetic-reader-password" not in stored_profile
    password.write_text("wrong-password", encoding="utf-8")
    assert "fixture authentication rejected" in admin(*config, expected=2)
    assert (state / "vibeinsight.json").read_bytes() == stored_profile
    password.unlink()
    service = start()

    async def mcp(db, tool, arguments):
        params = StdioServerParameters(command=sys.executable,
                                       args=["-m", "smm_local.mcp_server", "--db", str(db.db_path)],
                                       env=dict(os.environ))
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer) as endpoint:
                await endpoint.initialize()
                reply = await endpoint.call_tool(tool, arguments)
                assert not reply.isError
                return json.loads(reply.content[0].text)

    try:
        initially = eventually(lambda: hits if len(hits := query()) == 2 else None)
        assert {hit["source_session_id"] for hit in initially} == {"vibe-A", "vibe-B"}
        a = next(hit for hit in initially if hit["source_session_id"] == "vibe-A")
        assert admin("vibeinsight", "status")["last_success"]
        hub_id = hub_call("info")["hub_id"]
        write_source([alpha, beta, gamma])
        eventually(lambda: any(hit["source_session_id"] == "vibe-C" for hit in query()))
        stop(service)

        rows.extend(event(n, "vibe-A", "user" if n % 2 == 0 else "assistant", alpha) for n in range(20, 24))
        rows.append(event(24, "independent", "user", beta))
        write_source([alpha, beta, gamma])
        service = start()
        eventually(lambda: query("independent"))
        later = hub_call("read", {"hub_id": hub_id, "conversation_id": a["id"]})
        assert later["source_session_id"] == "vibe-A"
        assert [item["text"] for item in later["messages"]] == [
            f"evidence vibe-A {n}" for n in [10, 11, 12, 13, 14, 15, 20, 21, 22, 23]
        ]
        assert [item["origins"][0]["source_event_id"] for item in later["messages"]][-2:] == [
            "event-0022", "event-0023"
        ]
        assert admin("vibeinsight", "status")["credential_saved"]
        write_source([alpha, beta, gamma], fail=True)
        eventually(lambda: admin("vibeinsight", "status")["last_error"])
        assert query("independent")
        write_source([alpha, beta, gamma])
        recovered = eventually(lambda: status if not (status := admin("vibeinsight", "status"))["last_error"] else None)
        assert "fixture connection unavailable" in recovered["last_failure"]["reason"]

        clients = []
        for name in ("device-a", "device-b"):
            working = tmp_path / name / "work" / "duplicate-name"
            sessions = tmp_path / name / "sessions"
            working.mkdir(parents=True)
            sessions.mkdir()
            # Original project is determined by cwd, while the file resides in the import root.
            record_codex(sessions, name, [(0, name, f"evidence from {name}")])
            history = sessions / f"{name}.jsonl"
            history.write_text(history.read_text().replace(str(sessions), str(working)), encoding="utf-8")
            archive = Archive(tmp_path / name / "local.sqlite3")
            archive.set_settings(codex_root=str(sessions))
            archive.sync_codex()
            assert configure_hub(archive, address, name, str(token))["connected"]
            clients.append((archive, archive.resolve_project(str(working))["id"]))
        client_a, project_a = clients[0]
        client_b, project_b = clients[1]

        # Reproduce an old upload with its message cursor independently of project metadata.
        legacy = {
            "hub_id": hub_id, "device_name": "device-a",
            "device_id": json.loads(client_a.db_path.with_suffix(".sqlite3.hub.json").read_text())["device_id"],
            "records": [{"source":"codex","source_session_id":"device-a","started_at":None,
                         "source_key":"device-a","position":0,"role":"user",
                         "text":"evidence from device-a","timestamp":None,"source_order":1}],
        }
        assert hub_call("upload", legacy)["accepted"] == 1
        with client_a.connect() as con:
            message_id = con.execute("SELECT MAX(id) FROM messages").fetchone()[0]
            con.execute("INSERT INTO settings(key,value) VALUES(?,?)",
                        (f"hub_cursor:{hub_id}:{legacy['device_id']}", str(message_id)))
        historical = next(hit for hit in query() if hit["source_session_id"] == "device-a")
        assert historical["project_id"] is None
        assert push_pending(client_a)["uploaded"] == 0
        assert push_pending(client_b)["uploaded"] == 1

        names = admin("project", "list")
        device_a, device_b = [next(p for p in names if p["device_name"] == name) for name in ("device-a", "device-b")]
        vibe_a, vibe_b = [next(p for p in names if p["source_key"] == name) for name in (alpha, beta)]
        assert device_a["name"] == device_b["name"] == "duplicate-name"
        for one, other in [(device_a, device_b), (device_a, vibe_a), (device_b, vibe_b), (device_b, device_a)]:
            links = admin("project", "link", str(one["id"]), str(other["id"]))
        assert len(links) == 3
        client_b.rename_project(project_b, "renamed")
        assert push_pending(client_b)["uploaded"] == 0

        def scope(archive, project):
            return cli(archive.db_path, "search", "evidence", "--scope", "project",
                       "--project-id", str(project), "--limit", "20")

        scoped = scope(client_a, project_a)
        scoped_b = scope(client_b, project_b)
        assert {hit["source_session_id"] for hit in scoped["results"]} == {"device-a", "device-b", "vibe-A"}
        assert {p["name"] for p in scoped["effective_projects"]} >= {"duplicate-name", "renamed"}
        assert {hit["source_session_id"] for hit in scoped_b["results"]} == {
            "device-a", "device-b", "vibe-B", "independent"
        }
        via_mcp = asyncio.run(mcp(client_a, "search_conversations", {
            "query":"evidence", "scope":"project", "project_id":project_a, "limit":20,
        }))
        assert via_mcp["effective_projects"] == scoped["effective_projects"]
        for session in ("device-a", "vibe-A"):
            hit = next(row for row in via_mcp["results"] if row["source_session_id"] == session)
            message = hit["matched_messages"][0]
            exact = asyncio.run(mcp(client_a, "read_conversation", {
                "conversation_id":hit["id"], "hub_id":hub_id, "hub_message_id":message["hub_message_id"],
            }))
            assert exact["messages"][0]["position"] == message["position"]
            assert exact["messages"][0]["text"] == message["preview"]
            assert exact["project_name"] == hit["project_name"]
        original = hub_call("read", {"hub_id":hub_id,"conversation_id":historical["id"]})
        assert [msg["text"] for msg in original["messages"]] == ["evidence from device-a"]
        admin("project", "unlink", str(vibe_a["id"]), str(device_a["id"]))
        assert {hit["source_session_id"] for hit in scope(client_a, project_a)["results"]} == {"device-a", "device-b"}
        assert "vibe-A" in {hit["source_session_id"] for hit in query()}

        stop(service)
        other = tmp_path / "different-project"
        other.mkdir()
        sessions = tmp_path / "device-a" / "sessions"
        record_codex(sessions, "offline-local", [(0, "new", "evidence only in another local project")])
        history = sessions / "offline-local.jsonl"
        history.write_text(history.read_text().replace(str(sessions), str(other)), encoding="utf-8")
        client_a.sync_codex()
        offline = scope(client_a, project_a)
        assert offline["scope"] == "all" and offline["archive_scope"] == "local" and offline["fallback_reason"]
        offline_mcp = asyncio.run(mcp(client_a, "search_conversations", {
            "query":"evidence", "scope":"project", "project_id":project_a,
        }))
        assert offline_mcp["scope"] == "all" and offline_mcp["fallback_reason"]
        for result in (offline, offline_mcp):
            assert {hit["source_session_id"] for hit in result["results"]} == {"device-a", "offline-local"}
    finally:
        stop(service)


def test_archive_and_cursor_rollback_together(tmp_path, monkeypatch):
    rows = [event(0, "baseline", "user"), event(1, "baseline", "assistant")]
    source = FixtureSource(rows, ["git.example/team/alpha"])
    database = tmp_path / "hub.sqlite3"
    sync = synchronizer(database)
    sync.run(source)

    def cursor():
        with sync.db.connect() as connection:
            return tuple(connection.execute(
                "SELECT timestamp,event_id FROM hub_vibeinsight_cursors"
            ).fetchone())

    committed = cursor()
    # An exact timestamp tie straddles the two-record page boundary.
    rows.extend([
        event(2, "batch", "user", created="2026-09-14T00:01:00"),
        event(3, "batch", "assistant", created="2026-09-14T00:01:00"),
    ])
    original = sync._archive

    def fail_after_first_write(connection, row, project):
        inserted = original(connection, row, project)
        if row["id"] == "event-0003":
            raise RuntimeError("rollback this page")
        return inserted

    with monkeypatch.context() as changes:
        changes.setattr(sync, "_archive", fail_after_first_write)
        with pytest.raises(RuntimeError, match="rollback this page"):
            sync.run(source)
    assert cursor() == committed
    assert sync.db.search("batch")["results"] == []
    assert sync.db.search("baseline")["results"]
    sync.run(source)
    sync.run(source)
    result, = sync.db.search("batch")["results"]
    assert [item["text"] for item in sync.db.read(result["id"])["messages"]] == [
        "evidence batch 2", "evidence batch 3",
    ]

def test_delayed_reply_keeps_source_turns_grouped(tmp_path):
    directory = tmp_path / "hub.sqlite3"
    rows = [
        event(0, "grouped", "user", trace="first"),
        event(1, "grouped", "user", trace="second"),
        event(2, "grouped", "assistant", trace="second"),
        event(3, "grouped", "assistant", trace="first"),
    ]
    sync = synchronizer(directory)
    sync.run(FixtureSource(rows, ["git.example/team/alpha"]))
    hit, = sync.db.search("grouped")["results"]
    assert [m["text"] for m in sync.db.read(hit["id"])["messages"]] == [
        f"evidence grouped {n}" for n in (0, 3, 1, 2)
    ]


def test_scoped_shared_conversations_keep_only_matching_project_messages(tmp_path):
    from fastapi.testclient import TestClient
    from smm_hub.hub import create_hub
    from smm_hub.projects import HubProjects

    archive = Archive(tmp_path / "hub.sqlite3")
    token = "x" * 40
    device_a, device_b = "a" * 32, "b" * 32
    with TestClient(create_hub(archive, token), headers={"Authorization": "Bearer " + token}) as hub:
        hub_id = hub.get("/v1/info").json()["hub_id"]
        for device, project, word in [(device_a, "Alpha", "quasar"), (device_b, "Bravo", "orion")]:
            address = {"device_id": device, "device_name": project, "hub_id": hub_id}
            upload = hub.post("/v1/upload", json={**address, "records": [
                {"source":"codex", "source_session_id":"same-archive", "started_at":None,
                 "source_key":word, "position":1, "source_order":1, "timestamp":None,
                 "role":"user", "text":f"common {word}"}
            ]})
            assert upload.status_code == 200
            metadata = hub.post("/v1/project-metadata", json={**address, "projects":[{"id":1,"name":project}],
                "memberships":[{"source":"codex","source_session_id":"same-archive","project_id":1}]})
            assert metadata.status_code == 200

        def scoped(word):
            return hub.post("/v1/search", json={
                "query": word, "device_id": device_a, "project_id": 1, "preview_chars": 0,
            }).json()["results"]

        assert scoped("orion") == []
        hit, = scoped("common")
        assert [message["text"] for message in hit["matched_messages"]] == ["common quasar"]
        assert hit["matched_messages"][0]["origins"][0]["project_name"] == "Alpha"

        first, second = HubProjects(archive).list()
        projects = FixtureSource([
            event(0, "cross-repo", "user", "alpha-repo", text="nebula alphaonly"),
            event(1, "cross-repo", "assistant", "alpha-repo", text="nebula firstreply"),
            event(2, "cross-repo", "user", "beta-repo", text="nebula betaonly"),
            event(3, "cross-repo", "assistant", "beta-repo", text="nebula secondreply"),
        ], ["alpha-repo", "beta-repo"])
        synchronizer(archive.db_path).run(projects)
        global_hit, = hub.post("/v1/search", json={"query":"nebula"}).json()["results"]
        assert {p["name"] for p in global_hit["projects"]} == {"alpha-repo", "beta-repo"}
        project_ids = {p["name"]: p["id"] for p in HubProjects(archive).list()}
        manager = HubProjects(archive)
        manager.link(first["id"], project_ids["beta-repo"])
        manager.link(second["id"], project_ids["alpha-repo"])
        assert scoped("alphaonly") == []
        beta, = scoped("nebula")
        assert beta["id"] == global_hit["id"] and beta["project_name"] == "beta-repo"
        assert [msg["text"] for msg in beta["matched_messages"]] == [
            "nebula betaonly", "nebula secondreply",
        ]
        message_id = beta["matched_messages"][1]["hub_message_id"]
        exact = hub.post("/v1/read", json={"hub_id":hub_id,"conversation_id":beta["id"],
                                          "message_id":message_id}).json()
        assert exact["project_name"] == "beta-repo"
        assert exact["messages"][0]["origins"][0]["source_event_id"] == "event-0003"
