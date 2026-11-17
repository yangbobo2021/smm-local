"""Committed position boundaries are independent of the wall clock and other projects."""
import json

import pytest

from smm_hub.vibeinsight import VibeInsightSync
from smm_hub.vibeinsight_settings import Connection, VibeInsightSettings
from smm_local.core import Archive
from test_vibeinsight_sync import FixtureSource, event


def test_project_lookback_includes_boundary_and_resumes_after_days(tmp_path):
    a, b = "git.example/team/alpha", "git.example/team/beta"
    rows = [event(1, "a", "user", a, created="2026-09-10T12:00:00"),
            event(2, "b", "user", b, created="2026-09-11T12:00:00")]
    source = FixtureSource(rows, [a, b])
    archive = Archive(tmp_path / "hub.sqlite3")
    VibeInsightSync(archive, "fixture").run(source)
    # Different committed project positions can arise after an interrupted stream.
    with archive.connect() as con:
        con.execute("UPDATE hub_vibeinsight_cursors SET timestamp=? WHERE project=?",
                    ("2026-09-10T12:00:00", a))
    rows.extend([
        event(3, "a-boundary", "user", a, created="2026-09-09T12:00:00"),
        event(4, "a-inside", "user", a, created="2026-09-09T12:00:01"),
        event(5, "a-outside", "user", a, created="2026-09-09T11:59:59"),
        event(6, "b-boundary", "user", b, created="2026-09-10T12:00:00"),
        event(7, "b-inside", "user", b, created="2026-09-10T12:00:01"),
        event(8, "b-outside", "user", b, created="2026-09-10T11:59:59"),
        event(9, "during-downtime", "user", a, created="2026-09-12T12:00:00"),
        event(10, "after-days", "user", a, created="2026-09-15T12:00:00"),
    ])
    VibeInsightSync(archive, "fixture").run(source)
    before = archive.search("evidence", limit=30)["results"]
    sessions = {json.loads(archive.read(hit["id"])["source_session_id"])[-1] for hit in before}
    assert sessions >= {"a", "b", "a-boundary", "a-inside", "b-boundary", "b-inside",
                        "during-downtime", "after-days"}
    VibeInsightSync(archive, "fixture").run(source)
    assert {hit["id"] for hit in archive.search("evidence", limit=30)["results"]} == {hit["id"] for hit in before}
    assert all(len(archive.read(hit["id"])["messages"]) == 1 for hit in before)
    # Excluded older arrivals are an implementation observation, not a promised rejection API.


@pytest.mark.parametrize("field,new_value", [("host", "other-host"), ("port", 5433), ("database", "other-db")])
def test_connection_target_changes_isolate_progress_and_preserve_archive(tmp_path, field, new_value):
    archive = Archive(tmp_path / "hub.sqlite3")
    source = FixtureSource([event(1, "same-session", "user", created="2026-09-14T00:00:00")],
                           ["git.example/team/alpha"])
    settings = VibeInsightSettings(tmp_path, archive, source_factory=lambda config, password: source)
    conn = dict(host="original", port=5432, database="fixture", user="reader", interval=1, psql="fixture")
    settings.configure(Connection(**conn), "synthetic-secret")
    settings.sync(settings.load(), lambda: False)
    old_hit, = archive.search("evidence")["results"]
    with archive.connect() as con:
        initial = [dict(row) for row in con.execute("SELECT * FROM hub_vibeinsight_cursors")]
    conn["user"] = "replacement-reader"
    settings.configure(Connection(**conn), "replacement-secret")
    settings.sync(settings.load(), lambda: False)
    with archive.connect() as con:
        assert [dict(row) for row in con.execute("SELECT * FROM hub_vibeinsight_cursors")] == initial
    conn[field] = new_value
    source.rows = [event(2, "same-session", "user", created="2026-08-01T00:00:00", text="earlier target history")]
    settings.configure(Connection(**conn), "replacement-secret")
    settings.sync(settings.load(), lambda: False)
    assert archive.read(old_hit["id"])["messages"][0]["text"] == "evidence same-session 1"
    new_hit, = archive.search("earlier")["results"]
    assert new_hit["id"] != old_hit["id"]
    assert archive.read(new_hit["id"])["messages"][0]["text"] == "earlier target history"
    with archive.connect() as con:
        cursors = {row["source_id"]: dict(row) for row in con.execute("SELECT * FROM hub_vibeinsight_cursors")}
    assert set(cursors) == {json.dumps(["original", 5432, "fixture"]),
                            json.dumps([conn["host"], conn["port"], conn["database"]])}


@pytest.mark.parametrize("interval", [0, -1])
def test_invalid_interval_does_not_replace_saved_configuration(tmp_path, interval):
    archive = Archive(tmp_path / "hub.sqlite3")
    source = FixtureSource([], [])
    settings = VibeInsightSettings(tmp_path, archive, source_factory=lambda config, password: source)
    settings.configure(Connection("fixture", 5432, "fixture", "reader", 300, "fixture"), "synthetic-secret")
    before = {p.name: p.read_bytes() for p in tmp_path.glob("vibeinsight*")}
    with pytest.raises(ValueError, match="周期"):
        settings.configure(Connection("fixture", 5432, "fixture", "reader", interval, "fixture"), "other")
    assert {p.name: p.read_bytes() for p in tmp_path.glob("vibeinsight*")} == before
