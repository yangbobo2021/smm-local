"""Compare another candidate against the unchanged, frozen evaluation suite."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parent


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--private-logs", type=Path, required=True)
    args = parser.parse_args()
    candidate = args.candidate.resolve()
    output = args.output.resolve()
    private = args.private_logs.resolve()
    if output.exists():
        raise RuntimeError("Use a new output directory to preserve earlier results")
    original = json.loads((ROOT / "frozen.json").read_text())
    grading = json.loads((ROOT / "grading-frozen.json").read_text())
    for manifest in (original, grading):
        for name, expected in manifest["sha256"].items():
            if digest(ROOT / name) != expected:
                raise RuntimeError(f"Original frozen material changed: {name}")
    output.mkdir(parents=True)
    private.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(candidate, output / "candidate.md")
    shutil.copyfile(ROOT / "prompts/current.md", output / "current.md")
    round_info = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "original_frozen_sha256": digest(ROOT / "frozen.json"),
        "original_grading_frozen_sha256": digest(ROOT / "grading-frozen.json"),
        "replay_sha256": digest(Path(__file__)),
        "candidate_sha256": digest(candidate),
        "candidate_source": str(candidate.relative_to(ROOT)),
        "baseline_prompt_sha256": digest(ROOT / "prompts/current.md"),
        "case_sha256": {name: value for name, value in original["sha256"].items()
                        if name.startswith("cases/")},
        "rubric_sha256": digest(ROOT / "rubric.md"),
        "legacy_rubric_sha256": digest(ROOT.parent / "001-source-cli-help/rubric.md"),
        "review_runs": 12,
        "scoring": "unchanged original rubric and anonymous grading prompt",
    }
    (output / "round.json").write_text(json.dumps(round_info, ensure_ascii=False, indent=2) + "\n")
    with tempfile.TemporaryDirectory(prefix="smm-review-eval-round-") as directory:
        suite = Path(directory) / "002-vibeinsight-entry"
        for manifest in (original, grading):
            for name in manifest["sha256"]:
                target = suite / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, target)
        shutil.copyfile(candidate, suite / "prompts/candidate.md")
        frozen = json.loads(json.dumps(original))
        frozen["frozen_at"] = round_info["started_at"]
        frozen["sha256"]["prompts/candidate.md"] = digest(candidate)
        assert all(frozen["sha256"][name] == expected
                   for name, expected in original["sha256"].items()
                   if name != "prompts/candidate.md")
        (suite / "frozen.json").write_text(json.dumps(frozen, indent=2) + "\n")
        shutil.copyfile(ROOT / "grading-frozen.json", suite / "grading-frozen.json")
        shutil.copyfile(suite / "frozen.json", output / "frozen.json")
        shutil.copyfile(suite / "grading-frozen.json", output / "grading-frozen.json")
        subprocess.run([sys.executable, str(suite / "run.py"), "--output", str(output),
                        "--private-logs", str(private), "--workers", "2"], check=True)

        def grade(case):
            return subprocess.run(
                [sys.executable, str(suite / "grade.py"), "--runs", str(output),
                 "--private-logs", str(private), "--case", case], check=False).returncode

        with ThreadPoolExecutor(max_workers=2) as pool:
            codes = list(pool.map(grade, ("01", "02", "03", "04")))
        if any(codes):
            raise RuntimeError(
                f"A grading session failed. Inspect input/stdout/stderr logs in {private}. "
                "A timed-out grader may exit before writing its receipt."
            )


if __name__ == "__main__":
    main()
