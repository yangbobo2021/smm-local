"""Public behavior contracts for 005; synthetic data only, no user services."""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from smm_local.core import Archive
from smm_local import federation
from smm_hub.hub import create_hub
from smm_hub.projects import HubProjects


@pytest.fixture
def pair(tmp_path, monkeypatch):
    local = Archive(tmp_path / "local.sqlite3")
    remote = Archive(tmp_path / "hub.sqlite3")
    histories = tmp_path / "histories"
    histories.mkdir()
    empty = tmp_path / "empty"
    empty.mkdir()
    local.set_settings(codex_root=str(histories), claude_root=str(empty))
    token = "isolated-005-token-" + "a" * 40
    token_file = tmp_path / "token"
    token_file.write_text(token)
    calls = []
    with TestClient(create_hub(remote, token), headers={"Authorization": "Bearer " + token}) as client:
        def request(config, route, payload=None):
            calls.append((route, json.loads(json.dumps(payload))))
            response = client.get("/v1" + route) if payload is None else client.post("/v1" + route, json=payload)
            if response.status_code >= 400:
                raise federation.HubUnavailable(str(response.json()))
            return response.json()
        monkeypatch.setattr(federation, "_request", request)
        state = SimpleNamespace(local=local, remote=remote, client=client, histories=histories,
                                token_file=token_file, calls=calls, hub_id=client.get("/v1/info").json()["hub_id"])
        yield state


def add_local(pair, session, project, text):
    cwd = pair.histories.parent / project
    cwd.mkdir(exist_ok=True)
    events = [
        {"type": "session_meta", "payload": {"id": session, "cwd": str(cwd)}},
        {"type": "response_item", "ordinal": 1,
         "payload": {"type": "message", "id": session + "-message", "role": "user",
                     "content": [{"type": "input_text", "text": text}]}},
    ]
    (pair.histories / (session + ".jsonl")).write_text("".join(json.dumps(e) + "\n" for e in events))
    pair.local.sync_codex(pair.histories)
    with pair.local.connect() as con:
        return dict(con.execute("SELECT id,project_id FROM conversations WHERE source_session_id=?", (session,)).fetchone())


def connect(pair):
    result = federation.configure_hub(pair.local, "http://localhost:18770", "synthetic-device", str(pair.token_file))
    assert result["connected"] is True
    return federation.hub_config(pair.local)


def seed_remote(pair, text="common remote-only", session="remote", device="b" * 32):
    record = {"source": "codex", "source_session_id": session, "started_at": None,
              "source_key": session + "-message", "position": 1, "role": "user", "text": text,
              "timestamp": "2026-11-01T00:00:00Z", "source_order": 1}
    response = pair.client.post("/v1/upload", json={"hub_id": pair.hub_id, "device_id": device,
                                "device_name": "other-device", "records": [record]})
    assert response.status_code == 200, response.text
    return record


def bodies(archive):
    with archive.connect() as con:
        return [row[0] for row in con.execute("SELECT text FROM messages ORDER BY id")]


def test_new_connection_is_query_only_until_selected(pair):
    """TC-005-default: unknown upload choice must not send body or session metadata."""
    private = "private-local-dialogue"
    session = "private-local-session"
    add_local(pair, session, "A", private)
    seed_remote(pair, "remote known evidence")
    connect(pair)
    federation.push_pending(pair.local)
    assert bodies(pair.remote) == ["remote known evidence"], "new connection must not upload local dialogue"
    assert session not in json.dumps(pair.calls), "minimal registration must not enumerate forbidden conversations"
    assert private not in json.dumps(pair.calls), "minimal registration must not send forbidden body"
    for route, payload in pair.calls:
        if route == "/project-metadata":
            assert not payload.get("memberships"), "forbidden conversations must not be registered through memberships"
            for project in payload.get("projects", []):
                assert set(project) <= {"id", "name", "kind", "project_kind"}
    assert any(p["name"] == "A" for p in HubProjects(pair.remote).list())
    result = federation.search_archive(pair.local, "known evidence", limit=5)
    assert any(h["source_session_id"] == "remote" for h in result["results"])


def test_hub_rejects_stale_policy_and_legacy_body_after_restriction(pair):
    """TC-005-cas: policy confirmation fences stale and unversioned body requests."""
    device = "c" * 32
    seed_remote(pair, "accepted before stop", "accepted-before-stop", device)
    first = pair.client.post("/v1/upload-policy/set", json={"hub_id": pair.hub_id, "device_id": device,
        "expected_revision": 0, "submission_id": "initial", "policy": {"mode": "all", "projects": []}})
    assert first.status_code == 200, "Hub must support versioned policy confirmation"
    first = first.json()
    old_revision = first["revision"]
    project_key = "d" * 32
    metadata = pair.client.post("/v1/project-metadata", json={"hub_id": pair.hub_id, "device_id": device,
        "device_name": "managed", "policy_revision": old_revision, "control_epoch": first["control_epoch"],
        "projects": [{"id": project_key, "name": "A"}], "memberships": []})
    assert metadata.status_code == 200, metadata.text
    record = {"source": "codex", "source_session_id": "managed-rounds", "started_at": None,
              "source_key": "allowed-message", "position": 1, "role": "user", "text": "allowed before stop",
              "timestamp": None, "source_order": 1, "project_id": project_key}
    valid = pair.client.post("/v1/upload", json={"hub_id": pair.hub_id, "device_id": device,
        "device_name": "managed", "policy_revision": old_revision, "control_epoch": first["control_epoch"],
        "batch_id": "valid-before-stop", "records": [record]})
    assert valid.status_code == 200, valid.text
    assert bodies(pair.remote) == ["accepted before stop", "allowed before stop"]
    second = pair.client.post("/v1/upload-policy/set", json={"hub_id": pair.hub_id, "device_id": device,
        "expected_revision": old_revision, "submission_id": "stop", "policy": {"mode": "none", "projects": []}})
    assert second.status_code == 200, second.text
    current_revision = second.json()["revision"]
    before = bodies(pair.remote)
    stale = pair.client.post("/v1/upload-policy/set", json={"hub_id": pair.hub_id, "device_id": device,
        "expected_revision": old_revision, "submission_id": "late-allow", "policy": {"mode": "all", "projects": []}})
    assert stale.status_code >= 400
    record = {**record, "source_key": "stale-message", "position": 2, "source_order": 2, "text": "must not arrive"}
    for extra in ({}, {"policy_revision": old_revision, "control_epoch": first["control_epoch"]}):
        response = pair.client.post("/v1/upload", json={"hub_id": pair.hub_id, "device_id": device,
            "device_name": "managed", "records": [record], **extra})
        assert response.status_code >= 400, response.text
        assert bodies(pair.remote) == before
    status = pair.client.post("/v1/upload-policy/status", json={"hub_id": pair.hub_id, "device_id": device}).json()
    assert status["revision"] == current_revision
    assert status["policy"] == {"mode": "none", "projects": []}


def test_project_query_combines_unuploaded_local_and_linked_hub(pair):
    """TC-005-combined: local unuploaded and linked Hub candidates both participate."""
    a = add_local(pair, "local-a", "A", "common local-only")
    seed_remote(pair)
    config = connect(pair)
    key = federation._remote_project_key(pair.local, a["project_id"])
    for device, project_key, name, memberships in [
        (config["device_id"], key, "A", []),
        ("b" * 32, "remote-b", "B", [{"source": "codex", "source_session_id": "remote", "project_id": "remote-b"}]),
    ]:
        response = pair.client.post("/v1/project-metadata", json={"hub_id": pair.hub_id, "device_id": device,
            "device_name": name, "projects": [{"id": project_key, "name": name}], "memberships": memberships})
        assert response.status_code == 200, response.text
    projects = HubProjects(pair.remote)
    ids = {p["name"]: p["id"] for p in projects.list()}
    projects.link(ids["A"], ids["B"])
    result = federation.search_archive(pair.local, "common", scope="project", project_id=a["project_id"], limit=5)
    assert {h["source_session_id"] for h in result["results"]} == {"local-a", "remote"}
    assert result["archive_scope"] == "combined"
    assert {h["archive_scope"] for h in result["results"]} == {"local", "hub"}
    by_session = {h["source_session_id"]: h for h in result["results"]}
    assert by_session["local-a"]["archive_scope"] == "local"
    assert by_session["remote"]["archive_scope"] == "hub"
    assert by_session["local-a"]["matched_messages"][0]["text"] == "common local-only"
    assert by_session["remote"]["matched_messages"][0]["text"] == "common remote-only"


def test_references_read_the_right_archive_and_fail_closed(pair, monkeypatch):
    """TC-005-reference: identical numeric IDs in different archives remain distinct."""
    local = add_local(pair, "local-a", "A", "common exact local original")
    seed_remote(pair, "common exact remote original")
    connect(pair)
    local_hit = federation.search_archive(pair.local, "common", local=True)["results"][0]
    assert "reference" in local_hit, "new results need a precise, verifiable original reference"
    remote_hit = next(h for h in federation.search_archive(pair.local, "common")["results"]
                      if h["source_session_id"] == "remote")
    assert remote_hit["id"] == local["id"]
    read_local = federation.read_archive(pair.local, reference=local_hit["reference"])
    read_remote = federation.read_archive(pair.local, reference=remote_hit["reference"])
    assert [m["text"] for m in read_local["messages"]] == ["common exact local original"]
    assert [m["text"] for m in read_remote["messages"]] == ["common exact remote original"]
    with pytest.raises(ValueError):
        federation.read_archive(pair.local, conversation_id=local["id"] + 100, reference=local_hit["reference"])
    def offline(*args, **kwargs):
        raise federation.HubUnavailable("synthetic offline")
    monkeypatch.setattr(federation, "_request", offline)
    with pytest.raises(federation.HubUnavailable):
        federation.read_archive(pair.local, reference=remote_hit["reference"])
    assert [m["text"] for m in federation.read_archive(pair.local, reference=local_hit["reference"])["messages"]] == ["common exact local original"]
    with pair.local.connect() as con:
        con.execute("UPDATE messages SET text='different archived version' WHERE conversation_id=?", (local["id"],))
    with pytest.raises(ValueError):
        federation.read_archive(pair.local, reference=local_hit["reference"])


def test_project_fallback_does_not_expand_local_links(pair, monkeypatch):
    """TC-005-fallback: fallback A is narrower than explicit local A and links."""
    a = add_local(pair, "local-a", "A", "common A")
    d = add_local(pair, "local-d", "D", "common D")
    pair.local.link_projects(a["project_id"], d["project_id"])
    connect(pair)
    def offline(*args, **kwargs):
        raise federation.HubUnavailable("synthetic offline")
    monkeypatch.setattr(federation, "_request", offline)
    result = federation.search_archive(pair.local, "common", scope="project", project_id=a["project_id"])
    assert {h["source_session_id"] for h in result["results"]} == {"local-a"}
    assert result["fallback_reason"]
    assert result["archive_scope"] == "local"
    assert {p["id"] for p in result["effective_projects"]} == {a["project_id"]}
    explicit = federation.search_archive(pair.local, "common", scope="project", project_id=a["project_id"], local=True)
    assert {h["source_session_id"] for h in explicit["results"]} == {"local-a", "local-d"}
