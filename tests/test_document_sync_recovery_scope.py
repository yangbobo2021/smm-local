"""Regression: repairing one choice cannot revive another saved Hub target."""

from contextlib import ExitStack
from pathlib import Path
from copy import deepcopy

from fastapi.testclient import TestClient
from document_helpers import Fixture
from smm_local import federation
from smm_local.core import Archive
from smm_hub.hub import create_hub


def test_repair_selection_does_not_reauthorize_other_hub(tmp_path, monkeypatch):
    f = Fixture(tmp_path / "local")
    token = "synthetic-recovery-scope-" + "a" * 40
    token_file = tmp_path / "token"
    token_file.write_text(token)
    calls = []
    with ExitStack() as stack:
        clients = {
            "http://localhost:"
            + str(port): stack.enter_context(
                TestClient(
                    create_hub(Archive(tmp_path / str(port) / "hub.sqlite3"), token),
                    headers={"Authorization": "Bearer " + token},
                )
            )
            for port in (19001, 19002)
        }

        def request(config, route, payload=None):
            calls.append((config["address"], route, deepcopy(payload)))
            client = clients[config["address"]]
            r = (
                client.get("/v1" + route)
                if payload is None
                else client.post("/v1" + route, json=payload)
            )
            if r.status_code >= 400:
                raise federation.HubUnavailable(str(r.json()), status=r.status_code)
            return r.json()

        monkeypatch.setattr(federation, "_request", request)
        addresses = list(clients)
        projects = [f.project("P"), f.project("Q")]
        sources = []
        for name, project in zip(("P", "Q"), projects):
            path = f.file(name + ".txt", "scopenonce " + name + " original")
            source = f.add(path, [project])
            f.refresh(source)
            sources.append((path, source))

        def connect(address):
            assert federation.configure_hub(
                f.db, address, "scope-device", str(token_file)
            )["connected"]

        def status():
            return f.request("GET", "/api/documents/sync-status")

        def choose(project):
            state = status()
            row = next(p for p in state["projects"] if p["project_id"] == project)
            return f.request(
                "POST",
                "/api/documents/sync-policy",
                {
                    "project_key": row["project_key"],
                    "enabled": True,
                    "expected_hub_id": state["hub_id"],
                    "expected_generation": row["generation"],
                },
            )

        connect(addresses[0])
        for project in projects:
            choose(project)
        connect(addresses[1])
        choose(projects[1])
        guard = Path(str(f.db.db_path.resolve()) + ".documents-guard.json")
        guard.unlink()
        assert status()["protection_error"]
        repaired = choose(projects[0])
        selected = next(
            p for p in repaired["projects"] if p["project_id"] == projects[0]
        )
        other = next(p for p in repaired["projects"] if p["project_id"] == projects[1])
        assert selected["enabled"] and not selected["conflict"]
        assert other["conflict"]
        connect(addresses[0])
        restored = status()
        assert all(
            p["conflict"] for p in restored["projects"] if p["project_id"] in projects
        )
        marker = len(calls)
        for name, (path, source) in zip(("P", "Q"), sources):
            path.write_text("scopenonce " + name + " replacement")
            f.refresh(source)
        result = f.request("POST", "/api/documents/sync", {})
        assert result["pending"] and result["errors"]
        assert not any(
            route in {"/documents/stage", "/documents/publish"}
            for _, route, _ in calls[marker:]
        )
        choose(projects[0])
        latest = status()
        assert next(p for p in latest["projects"] if p["project_id"] == projects[1])[
            "conflict"
        ]
        hub = clients[addresses[0]]
        info = hub.get("/v1/info").json()
        found = hub.post(
            "/v1/documents/search",
            json={
                "hub_id": info["hub_id"],
                "document_epoch": info["document_epoch"],
                "query": "scopenonce",
                "limit": 50,
            },
        ).json()["results"]
        texts = {
            hub.post(
                "/v1/documents/read",
                json={
                    "hub_id": info["hub_id"],
                    "document_epoch": info["document_epoch"],
                    "reference": h["reference"],
                },
            ).json()["text"]
            for h in found
        }
        assert texts == {"scopenonce P replacement", "scopenonce Q original"}


def test_deleted_project_is_rechecked_inside_selection_write(tmp_path, monkeypatch):
    from contextlib import contextmanager
    from smm_local.document_protocol import DocumentGuard

    f = Fixture(tmp_path / "local")
    token = "synthetic-project-race-" + "b" * 40
    token_file = tmp_path / "token"
    token_file.write_text(token)
    remote = Archive(tmp_path / "hub.sqlite3")
    with TestClient(
        create_hub(remote, token), headers={"Authorization": "Bearer " + token}
    ) as client:

        def request(config, route, payload=None):
            r = (
                client.get("/v1" + route)
                if payload is None
                else client.post("/v1" + route, json=payload)
            )
            if r.status_code >= 400:
                raise federation.HubUnavailable(str(r.json()), status=r.status_code)
            return r.json()

        monkeypatch.setattr(federation, "_request", request)
        assert federation.configure_hub(
            f.db, "http://localhost:19003", "race-device", str(token_file)
        )["connected"]
        project = f.project("Original")
        state = f.request("GET", "/api/documents/sync-status")
        shown = next(p for p in state["projects"] if p["project_id"] == project)
        with f.db.connect() as c:
            before = [dict(r) for r in c.execute("SELECT * FROM local_document_sync")]
        original = DocumentGuard.hold
        injected = []

        @contextmanager
        def interleaved(self, *, recover=False):
            if (
                recover
                and self.db.db_path.resolve() == f.db.db_path.resolve()
                and not injected
            ):
                with f.db.connect() as c:
                    c.execute("DELETE FROM projects WHERE id=?", (project,))
                replacement = f.db.create_project("Replacement")
                assert replacement["id"] == project
                assert replacement["stable_key"] != shown["project_key"]
                injected.append(replacement)
            with original(self, recover=recover):
                yield

        with monkeypatch.context() as patch:
            patch.setattr(DocumentGuard, "hold", interleaved)
            response = f.client.post(
                "/api/documents/sync-policy",
                json={
                    "project_key": shown["project_key"],
                    "enabled": True,
                    "expected_hub_id": state["hub_id"],
                    "expected_generation": shown["generation"],
                },
            )
        assert injected
        assert response.status_code == 400, response.text
        with f.db.connect() as c:
            after = [dict(r) for r in c.execute("SELECT * FROM local_document_sync")]
        assert after == before
        fresh = f.request("GET", "/api/documents/sync-status")
        replacement = next(p for p in fresh["projects"] if p["project_id"] == project)
        assert (
            replacement["project_key"] == injected[0]["stable_key"]
            and not replacement["enabled"]
            and replacement["generation"] == 0
        )


import pytest


@pytest.mark.parametrize("stop", ["pause", "guard"])
def test_new_stage_stops_without_exposing_unsent_members(tmp_path, monkeypatch, stop):
    f = Fixture(tmp_path / "local")
    token = "synthetic-stage-fence-" + "c" * 40
    token_file = tmp_path / "token"
    token_file.write_text(token)
    remote = Archive(tmp_path / "hub.sqlite3")
    with TestClient(
        create_hub(remote, token), headers={"Authorization": "Bearer " + token}
    ) as client:
        project = f.project("Staged")
        root = tmp_path / "source"
        root.mkdir()
        for name in ("first.txt", "second.txt"):
            (root / name).write_text("stagenonce " + name)
        source = f.add(root, [project])
        f.refresh(source)
        ids = {row["id"] for row in f.files(source)}
        calls = []
        staged = []

        def request(config, route, payload=None):
            calls.append((route, deepcopy(payload)))
            r = (
                client.get("/v1" + route)
                if payload is None
                else client.post("/v1" + route, json=payload)
            )
            if r.status_code >= 400:
                raise federation.HubUnavailable(str(r.json()), status=r.status_code)
            result = r.json()
            if route == "/documents/stage":
                staged.append(payload["document"]["document_id"])
                if len(staged) == 1:
                    if stop == "guard":
                        Path(
                            str(f.db.db_path.resolve()) + ".documents-guard.json"
                        ).unlink()
                    else:
                        state = f.request("GET", "/api/documents/sync-status")
                        row = next(
                            p for p in state["projects"] if p["project_id"] == project
                        )
                        f.request(
                            "POST",
                            "/api/documents/sync-policy",
                            {
                                "project_key": row["project_key"],
                                "enabled": False,
                                "expected_hub_id": state["hub_id"],
                                "expected_generation": row["generation"],
                            },
                        )
            return result

        monkeypatch.setattr(federation, "_request", request)
        assert federation.configure_hub(
            f.db, "http://localhost:19004", "stage-device", str(token_file)
        )["connected"]
        state = f.request("GET", "/api/documents/sync-status")
        row = next(p for p in state["projects"] if p["project_id"] == project)
        f.request(
            "POST",
            "/api/documents/sync-policy",
            {
                "project_key": row["project_key"],
                "enabled": True,
                "expected_hub_id": state["hub_id"],
                "expected_generation": row["generation"],
            },
        )
        assert len(staged) == 1
        unsent = ids - set(staged)
        assert len(unsent) == 1
        for route, payload in calls:
            if route == "/documents/control" and not payload["enabled"]:
                assert all(ident not in str(payload) for ident in unsent)
        assert not any(route == "/documents/publish" for route, _ in calls)
        info = client.get("/v1/info").json()
        result = client.post(
            "/v1/documents/search",
            json={
                "hub_id": info["hub_id"],
                "document_epoch": info["document_epoch"],
                "query": "stagenonce",
            },
        )
        assert result.status_code == 200 and result.json()["results"] == []
        local = f.search("stagenonce", local=True, limit=50)
        assert {f.read(h)["text"] for h in local["results"]} == {
            "stagenonce first.txt",
            "stagenonce second.txt",
        }
