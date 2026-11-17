"""Exercise citation recovery without model or database requests."""

import hashlib
import importlib
import json
from pathlib import Path
import shutil

import pytest


@pytest.fixture
def fixture_round(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(root))
    helper = importlib.import_module("build_audited_scores")
    source = root / "runs/2026-11-17-v1"
    output = tmp_path / "round"
    shutil.copytree(source, output)
    expected = json.loads((output / "scores-audited.json").read_text())["results"]
    (output / "scores-audited.json").unlink()
    return helper, output, expected


def snapshots(output):
    return {
        str(p.relative_to(output)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in output.rglob("*")
        if p.is_file()
    }


def test_rebuilds_existing_citation_audit_without_changing_raw_records(fixture_round):
    helper, output, expected = fixture_round
    before = snapshots(output)
    target = helper.build(output)
    assert json.loads(target.read_text())["results"] == expected
    after = snapshots(output)
    assert after.keys() - before.keys() == {"scores-audited.json"}
    assert {key: after[key] for key in before} == before


def test_refuses_to_overwrite_audited_scores(fixture_round):
    helper, output, _ = fixture_round
    helper.build(output)
    before = snapshots(output)
    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        helper.build(output)
    assert snapshots(output) == before


@pytest.mark.parametrize(
    "problem", ["score_change", "nonverbatim_replacement", "altered_grades"]
)
def test_invalid_audit_creates_no_summary_and_keeps_input_bytes(fixture_round, problem):
    helper, output, _ = fixture_round
    audit_path = output / "citation-audit.json"
    audit = json.loads(audit_path.read_text())
    if problem == "score_change":
        audit["score_changes"] = [{"score": 1}]
    elif problem == "nonverbatim_replacement":
        audit["corrections"][0]["replacement"] = "not present in the answer"
    else:
        grades_path = output / audit["corrections"][0]["file"]
        grades = json.loads(grades_path.read_text())
        grades["answers"][0]["checks"][0]["score"] = 0
        grades_path.write_text(json.dumps(grades))
    audit_path.write_text(json.dumps(audit))
    before = snapshots(output)
    with pytest.raises((AssertionError, ValueError)):
        helper.build(output)
    assert snapshots(output) == before
    assert not (output / "scores-audited.json").exists()
