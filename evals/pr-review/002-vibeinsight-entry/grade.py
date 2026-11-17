"""Blind the prompt labels before grading each case's completed answers."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import re
import shutil
import subprocess
import tempfile
import time


ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=Path, required=True)
    parser.add_argument("--private-logs", type=Path, required=True)
    parser.add_argument("--case", choices=("01", "02", "03", "04"), required=True)
    args = parser.parse_args()
    runs = args.runs.resolve()
    private = args.private_logs.resolve()
    private.mkdir(parents=True, exist_ok=True)
    for name in ("frozen.json", "grading-frozen.json"):
        manifest = json.loads((ROOT / name).read_text())
        for path, expected in manifest["sha256"].items():
            if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != expected:
                raise RuntimeError(f"Frozen material changed: {path}")
    repeats = 3 if args.case == "01" else 1
    answers = []
    for variant in ("current", "candidate"):
        for repeat in range(1, repeats + 1):
            path = runs / f"case-{args.case}-{variant}-{repeat}.md"
            receipt = json.loads(path.with_suffix(".json").read_text())
            body = path.read_text()
            assert receipt["returncode"] == 0
            assert hashlib.sha256(path.read_bytes()).hexdigest() == receipt["answer_sha256"]
            answers.append((path.name, body))
    random.Random(20261117 + int(args.case)).shuffle(answers)
    labels = {f"R{index + 1}": name for index, (name, _) in enumerate(answers)}
    (runs / f"case-{args.case}-blind-map.json").write_text(
        json.dumps(labels, ensure_ascii=False, indent=2) + "\n")
    rubric = ROOT.parent / "001-source-cli-help/rubric.md" if args.case == "04" else ROOT / "rubric.md"
    prompt = (ROOT / "grading.prompt.md").read_text()
    prompt += f"\n\n当前只评分 Case {args.case}。\n\n评分规则\n\n{rubric.read_text()}"
    prompt += "\n\n原始输入\n\n" + (ROOT / f"cases/case-{args.case}.md").read_text()
    for index, (_, body) in enumerate(answers):
        prompt += f"\n\n匿名回答 R{index + 1}\n\n<answer>\n{body}\n</answer>"
    request = prompt.encode()
    target = runs / f"case-{args.case}-grades.json"
    if target.exists():
        raise RuntimeError(f"Refusing to overwrite grades: {target}")
    binary = shutil.which("codex")
    if binary is None:
        raise RuntimeError("Codex CLI is required")
    started = datetime.now(timezone.utc).isoformat()
    start = time.monotonic()
    stem = f"case-{args.case}-grader"
    (private / f"{stem}.input").write_bytes(request)
    with tempfile.TemporaryDirectory(prefix="smm-eval-grading-") as workspace:
        command = [binary, "--no-daemon", "--ask-for-approval", "never", "exec",
                   "--ignore-user-config", "--ephemeral", "--sandbox", "read-only",
                   "--skip-git-repo-check", "--color", "never", "--cd", workspace,
                   "--output-schema", str(ROOT / "grading.schema.json"),
                   "--output-last-message", str(target), "-"]
        with (private / f"{stem}.stdout").open("wb") as stdout, \
                (private / f"{stem}.stderr").open("wb") as stderr:
            result = subprocess.run(command, input=request, stdout=stdout, stderr=stderr,
                                    timeout=900, check=False)
    log = (private / f"{stem}.stderr").read_text(errors="replace")
    model = re.search(r"^model:\s*(.+)$", log, re.MULTILINE)
    receipt = {
        "case": args.case, "started_at": started,
        "elapsed_seconds": round(time.monotonic() - start, 2),
        "returncode": result.returncode,
        "request_sha256": hashlib.sha256(request).hexdigest(),
        "model_reported": model.group(1) if model else None,
        "prompt_labels_hidden": True,
    }
    (runs / f"{stem}.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt), flush=True)
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
