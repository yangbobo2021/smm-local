"""Run frozen review prompts in independent Codex material-replay sessions."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time


ROOT = Path(__file__).resolve().parent
SCHEDULE = [
    ("01", 1, "current"), ("01", 1, "candidate"),
    ("02", 1, "candidate"), ("02", 1, "current"),
    ("01", 2, "candidate"), ("01", 2, "current"),
    ("03", 1, "current"), ("03", 1, "candidate"),
    ("01", 3, "current"), ("01", 3, "candidate"),
    ("04", 1, "candidate"), ("04", 1, "current"),
]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_one(job, output: Path, private: Path, binary: str):
    number, repeat, variant = job
    name = f"case-{number}-{variant}-{repeat}"
    prompt = (ROOT / "prompts" / f"{variant}.md").read_bytes()
    packet = (ROOT / "cases" / f"case-{number}.md").read_bytes()
    request = prompt + b"\n\n" + packet
    answer = output / f"{name}.md"
    receipt = output / f"{name}.json"
    if answer.exists() or receipt.exists():
        raise RuntimeError(f"Refusing to overwrite an existing run: {name}")
    started = datetime.now(timezone.utc).isoformat()
    start = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="smm-eval-context-") as workspace:
        command = [
            binary, "--no-daemon", "--ask-for-approval", "never", "exec",
            "--ignore-user-config", "--ephemeral", "--sandbox", "read-only",
            "--skip-git-repo-check", "--color", "never", "--cd", workspace,
            "--output-last-message", str(answer), "-",
        ]
        with (private / f"{name}.stdout").open("wb") as stdout, \
                (private / f"{name}.stderr").open("wb") as stderr:
            try:
                result = subprocess.run(command, input=request, stdout=stdout, stderr=stderr,
                                        timeout=900, check=False)
                code = result.returncode
            except subprocess.TimeoutExpired:
                code = 124
    log = (private / f"{name}.stderr").read_text(errors="replace")
    model = re.search(r"^model:\s*(.+)$", log, re.MULTILINE)
    reasoning = re.search(r"^reasoning effort:\s*(.+)$", log, re.MULTILINE)
    data = {
        "case": number, "repeat": repeat, "prompt": variant,
        "started_at": started, "elapsed_seconds": round(time.monotonic() - start, 2),
        "returncode": code, "prompt_sha256": digest(prompt),
        "input_sha256": digest(packet), "request_sha256": digest(request),
        "answer_sha256": digest(answer.read_bytes()) if answer.is_file() else None,
        "model_reported": model.group(1) if model else None,
        "reasoning_effort_reported": reasoning.group(1) if reasoning else None,
        "cli_version": subprocess.check_output([binary, "--version"], text=True).strip(),
        "configuration": {
            "ignore_user_config": True, "ephemeral": True, "sandbox": "read-only",
            "context": "fresh empty temporary directory and supplied packet only",
            "model_override": None, "reasoning_override": None,
            "timeout_seconds": 900,
        },
    }
    receipt.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"run": name, "returncode": code,
                      "elapsed_seconds": data["elapsed_seconds"]}), flush=True)
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--private-logs", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=2, choices=(1, 2, 3))
    parser.add_argument("--only", help="Run one case-current/candidate-repeat, for diagnosis")
    args = parser.parse_args()
    output = args.output.resolve()
    private = args.private_logs.resolve()
    output.mkdir(parents=True, exist_ok=True)
    private.mkdir(parents=True, exist_ok=True)
    binary = shutil.which("codex")
    if binary is None:
        raise RuntimeError("Codex CLI is required")
    frozen = json.loads((ROOT / "frozen.json").read_text())
    for path, expected in frozen["sha256"].items():
        if digest((ROOT / path).read_bytes()) != expected:
            raise RuntimeError(f"Frozen input changed: {path}")
    jobs = SCHEDULE
    if args.only:
        jobs = [job for job in jobs if f"case-{job[0]}-{job[2]}-{job[1]}" == args.only]
        if len(jobs) != 1:
            parser.error("--only must select one scheduled run")
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(lambda job: run_one(job, output, private, binary), jobs))
    if any(result["returncode"] != 0 for result in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
