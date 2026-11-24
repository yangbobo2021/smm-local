"""Draft regression for the unconfigured explicit Hub project boundary."""

import asyncio
from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import sys
from unittest.mock import patch
import pytest
from document_helpers import Fixture, document_state, deny_source_reads, observe
from smm_local import federation
from smm_local.cli import main
from smm_local.mcp_server import create_mcp


# @case-id: TC-007-unconfigured-hub-root
@pytest.mark.parametrize("entry", ["cli", "api", "mcp"])
@pytest.mark.parametrize("root_position", [0, 1])
def test_unconfigured_hub_root(tmp_path, monkeypatch, entry, root_position):
    local = Fixture(tmp_path / "local")
    projects = [local.project("Local P"), local.project("Local Q")]
    paths = []
    expected = {}
    for i, project in enumerate(projects):
        path = local.file(str(i) + ".txt", "needle local private " + str(i))
        source = local.add(path, [project])
        local.refresh(source)
        rows = local.files(source)
        assert len(rows) == 1 and Path(rows[0]["path"]) == path.resolve()
        expected[rows[0]["id"]] = "needle local private " + str(i)
        paths.append(path)
    assert not federation.hub_config(local.db)
    network = []

    def deny_network(*args, **kwargs):
        network.append((args, kwargs))
        raise AssertionError("standalone Hub root attempted network")

    monkeypatch.setattr(federation, "_request", deny_network)
    server = create_mcp(local.db)

    def query(**options):
        body = {"query": "needle", "limit": 50, **options}
        if entry == "api":
            return local.request("POST", "/api/documents/search", body)
        if entry == "mcp":
            result = asyncio.run(server.call_tool("search_documents", body))
            return json.loads(result[0][0].text)
        args = [
            "smm",
            "--db",
            str(local.db.db_path),
            "documents",
            "search",
            "needle",
            "--limit",
            "50",
        ]
        if options.get("scope"):
            args += ["--scope", options["scope"]]
        if options.get("project_id"):
            args += ["--project-id", str(options["project_id"])]
        if options.get("hub_project_id"):
            args += ["--hub-project-id", str(options["hub_project_id"])]
        if options.get("local"):
            args += ["--local"]
        stdout, stderr = io.StringIO(), io.StringIO()
        code = 0
        with (
            patch.object(sys, "argv", args),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            try:
                main()
            except SystemExit as error:
                code = error.code or 0
        observe(
            "unconfigured-cli",
            {
                "argv": args,
                "exit_code": code,
                "stdout": stdout.getvalue(),
                "stderr": stderr.getvalue(),
            },
        )
        assert code == 0, stderr.getvalue()
        return json.loads(stdout.getvalue())

    before = document_state(local)
    with monkeypatch.context() as guarded:
        source_opens = deny_source_reads(guarded, *paths)
        normal = query()
        explicit = query(local=True)
        assert len(expected) == 2
        for value in [normal, explicit]:
            assert len(value["results"]) == len(expected)
            assert {hit["id"] for hit in value["results"]} == set(expected)
            for hit in value["results"]:
                original = expected[hit["id"]]
                assert hit["text"] == original
                actual = local.read(hit, start=0, end=len(original))
                assert actual["id"] == hit["id"] and actual["text"] == original
                assert actual["start"] == 0 and actual["end"] == len(original)
        assert [h["reference"] for h in normal["results"]] == [
            h["reference"] for h in explicit["results"]
        ]
        for value in [normal, explicit]:
            assert (
                value["coverage"]["hub"] == "not_requested"
                and value["fallback_reason"] is None
            )
        result = query(scope="project", hub_project_id=projects[root_position])
        observe(
            "unconfigured-root",
            {
                "entry": entry,
                "colliding_local_project": projects[root_position],
                "response": result,
            },
        )
        assert result["results"] == [] and result["effective_projects"] == []
        assert result["coverage"]["local"] == "complete"
        assert result["coverage"]["hub"] == "unavailable" and result["fallback_reason"]
        assert network == [] and source_opens == []
    assert document_state(local) == before
