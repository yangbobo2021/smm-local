"""The public standalone entry uses saved source state without service registration."""
import asyncio
import sys
from pathlib import Path

import pytest

from smm_local.core import Archive


def test_standalone_runs_saved_source_lifecycle(tmp_path, monkeypatch):
    import uvicorn
    from smm_hub import cli, vibeinsight_settings
    from test_vibeinsight_sync import FixtureSource, event

    root = tmp_path / "state"
    root.mkdir()
    token = tmp_path / "token"
    token.write_text("t" * 40)
    source = FixtureSource([event(1, "standalone", "user", text="standalone persisted message")],
                           ["git.example/team/alpha"])
    real_settings = vibeinsight_settings.VibeInsightSettings

    def settings(root, archive):
        return real_settings(root, archive, source_factory=lambda config, password: source)

    archive = Archive(root / "smm-hub.sqlite3")
    settings(root, archive).configure(
        vibeinsight_settings.Connection("fixture", 5432, "fixture", "reader", 1, "fixture-psql"),
        "synthetic-standalone-secret",
    )
    monkeypatch.setattr(vibeinsight_settings, "VibeInsightSettings", settings)
    observed = []

    def run(app, **kwargs):
        async def check():
            async with app.router.lifespan_context(app):
                for _ in range(100):
                    hits = archive.search("persisted")["results"]
                    if hits:
                        observed.extend(archive.read(hit["id"]) for hit in hits)
                        break
                    await asyncio.sleep(.02)
        asyncio.run(check())

    monkeypatch.setattr(uvicorn, "run", run)
    monkeypatch.setattr(sys, "argv", ["smm-hub", "serve-hub", "--state-dir", str(root),
                                    "--token-file", str(token)])
    cli.main()
    assert len(observed) == 1
    assert [message["text"] for message in observed[0]["messages"]] == ["standalone persisted message"]
    assert settings(root, archive).status()["last_success"]
    assert not (root / "hub.json").exists()  # no system service setup was needed


def test_standalone_rejects_conflicting_archive_before_writing(tmp_path, monkeypatch, capsys):
    from smm_hub.cli import main

    root = tmp_path / "state"
    other = tmp_path / "other.sqlite3"
    monkeypatch.setattr(sys, "argv", ["smm-hub", "--db", str(other), "serve-hub", "--state-dir", str(root),
                                    "--token-file", str(tmp_path / "missing-token")])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2
    error = capsys.readouterr().err
    assert "--db 与 --state-dir" in error
    assert not other.exists() and not root.exists()


@pytest.mark.parametrize("with_state", [False, True], ids=["legacy", "matching-explicit-db"])
def test_standalone_explicit_archive_remains_supported(tmp_path, monkeypatch, with_state):
    import uvicorn
    from smm_hub.cli import main

    root = tmp_path / "state"
    database = root / "smm-hub.sqlite3"
    token = tmp_path / "token"
    token.write_text("t" * 40)
    invocations = []
    monkeypatch.setattr(uvicorn, "run", lambda app, **kwargs: invocations.append(app))
    args = ["smm-hub", "--db", str(database), "serve-hub", "--token-file", str(token)]
    if with_state:
        args += ["--state-dir", str(root)]
    monkeypatch.setattr(sys, "argv", args)
    main()
    assert len(invocations) == 1 and database.is_file()
