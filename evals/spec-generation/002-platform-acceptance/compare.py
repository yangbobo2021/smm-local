"""Compare frozen SPEC templates, then grade the resulting answers anonymously."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import random
import re
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
TIMEOUT = 900
SEED = 20261117
GENERATION_HEADER = (
    "这是独立的离线规格起草任务。仅依据下面提供的模板与样本直接输出 SPEC 正文。"
    "不要使用工具、读取文件、访问网络或历史会话。\n\n待测模板：\n\n"
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, data):
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def check_definition():
    frozen = read_json(ROOT / "frozen.json")
    for path, expected in frozen["sha256"].items():
        if digest((ROOT / path).read_bytes()) != expected:
            raise RuntimeError(f"Original EVAL material changed: {path}")
    for path, expected in frozen["external_sha256"].items():
        if digest((PROJECT / path).read_bytes()) != expected:
            raise RuntimeError(f"Original regression material changed: {path}")
    return frozen


def check_round(output):
    manifest = read_json(output / "round.json")
    for path, expected in manifest["package_sha256"].items():
        if digest((ROOT / path).read_bytes()) != expected:
            raise RuntimeError(f"Round source changed: {path}")
    for path, expected in manifest["snapshot_sha256"].items():
        if digest((output / path).read_bytes()) != expected:
            raise RuntimeError(f"Round snapshot changed: {path}")
    check_definition()
    return manifest


def invoke(binary, request, answer, private, stem, schema=None):
    """Capture raw logs privately and record the real CLI configuration per call."""
    if answer.exists() or answer.with_suffix(".json").exists():
        raise RuntimeError(f"Refusing to overwrite: {answer}")
    private.mkdir(parents=True, exist_ok=True)
    (private / f"{stem}.input").write_bytes(request)
    started, clock = utc_now(), time.monotonic()
    environment = {
        key: value
        for key, value in os.environ.items()
        if key not in {"CODEX_THREAD_ID", "CODEX_SESSION_ID", "CLAUDE_SESSION_ID"}
    }
    with tempfile.TemporaryDirectory(prefix="smm-spec-eval-") as workspace:
        command = [
            binary,
            "--no-daemon",
            "--ask-for-approval",
            "never",
            "exec",
            "--ignore-user-config",
            "--ignore-rules",
            "--ephemeral",
            "--sandbox",
            "read-only",
            "--skip-git-repo-check",
            "--color",
            "never",
            "-c",
            "project_doc_max_bytes=0",
            "--cd",
            workspace,
            "--output-last-message",
            str(answer),
        ]
        if schema is not None:
            command.extend(["--output-schema", str(schema)])
        command.append("-")
        with (
            (private / f"{stem}.stdout").open("wb") as stdout,
            (private / f"{stem}.stderr").open("wb") as stderr,
        ):
            try:
                result = subprocess.run(
                    command,
                    input=request,
                    stdout=stdout,
                    stderr=stderr,
                    env=environment,
                    timeout=TIMEOUT,
                    check=False,
                )
                code = result.returncode
            except subprocess.TimeoutExpired:
                code = 124
    logs = (private / f"{stem}.stderr").read_text(errors="replace")
    model = re.search(r"^model:\s*(.+)$", logs, re.M)
    effort = re.search(r"^reasoning effort:\s*(.+)$", logs, re.M)
    # A tool invocation violates this offline replay, even if the final answer looks valid.
    tool_lines = re.findall(r"^(?:exec|tool\s+\S+|web\.\S+)$", logs, re.M)
    successful = (
        code == 0 and answer.is_file() and answer.stat().st_size > 0 and not tool_lines
    )
    receipt = {
        "started_at": started,
        "ended_at": utc_now(),
        "elapsed_seconds": round(time.monotonic() - clock, 2),
        "returncode": code,
        "execution_status": "completed" if successful else "technical_failure",
        "request_sha256": digest(request),
        "answer_sha256": digest(answer.read_bytes()) if answer.is_file() else None,
        "model_reported": model.group(1) if model else None,
        "reasoning_effort_reported": effort.group(1) if effort else None,
        "tool_invocations_observed": tool_lines,
        "cli_version": subprocess.check_output(
            [binary, "--version"], text=True
        ).strip(),
        "configuration": {
            "ignore_user_config": True,
            "ignore_rules": True,
            "ephemeral": True,
            "sandbox": "read-only",
            "project_doc_max_bytes": 0,
            "context": "fresh empty directory; supplied packet only; no chat history",
            "model_override": None,
            "reasoning_override": None,
            "timeout_seconds": TIMEOUT,
        },
    }
    return receipt


def run_one(job, output, private, binary):
    name = f"{job['case']}-{job['variant']}-{job['repeat']}"
    template = (output / f"{job['variant']}.md").read_bytes()
    packet = (ROOT / f"cases/{job['case']}.md").read_bytes()
    request = GENERATION_HEADER.encode() + template + "\n\n样本：\n\n".encode() + packet
    answer = output / f"{name}.md"
    receipt = invoke(binary, request, answer, private, name)
    receipt.update(job)
    receipt.update(template_sha256=digest(template), input_sha256=digest(packet))
    write_json(answer.with_suffix(".json"), receipt)
    print(
        json.dumps(
            {
                "run": name,
                "status": receipt["execution_status"],
                "seconds": receipt["elapsed_seconds"],
            }
        ),
        flush=True,
    )
    return receipt


def initialize(output, candidate):
    frozen = check_definition()
    if output.exists():
        raise RuntimeError(
            "Use a new output directory; --resume only continues absent runs"
        )
    output.mkdir(parents=True)
    shutil.copyfile(ROOT / "templates/current-spec.md", output / "current.md")
    shutil.copyfile(candidate, output / "candidate.md")
    shutil.copyfile(ROOT / "frozen.json", output / "definition-frozen.json")
    schedule = []
    for repeat in range(1, 4):
        for index, case in enumerate(frozen["cases"]):
            variants = (
                ("current", "candidate")
                if (index + repeat) % 2
                else ("candidate", "current")
            )
            schedule.extend(
                {"case": case["id"], "variant": variant, "repeat": repeat}
                for variant in variants
            )
    package_paths = [
        "compare.py",
        "grading.prompt.md",
        "grading.schema.json",
        "rubric.md",
        "frozen.json",
    ]
    manifest = {
        "started_at": utc_now(),
        "seed": SEED,
        "repeats_per_case_per_variant": 3,
        "schedule": schedule,
        "snapshot_sha256": {
            name: digest((output / name).read_bytes())
            for name in ("current.md", "candidate.md", "definition-frozen.json")
        },
        "package_sha256": {
            name: digest((ROOT / name).read_bytes()) for name in package_paths
        },
    }
    write_json(output / "round.json", manifest)
    return manifest


def run(args, binary):
    output = args.output.resolve()
    manifest = (
        check_round(output)
        if args.resume
        else initialize(output, args.candidate.resolve())
    )
    jobs = []
    for job in manifest["schedule"]:
        receipt = output / f"{job['case']}-{job['variant']}-{job['repeat']}.json"
        if receipt.exists():
            existing = read_json(receipt)
            answer = receipt.with_suffix(".md")
            if (
                existing["execution_status"] != "completed"
                or digest(answer.read_bytes()) != existing["answer_sha256"]
            ):
                raise RuntimeError(
                    f"Existing failed or altered run needs separate diagnosis: {receipt}"
                )
        else:
            jobs.append(job)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        receipts = list(
            pool.map(
                lambda job: run_one(job, output, args.private_logs.resolve(), binary),
                jobs,
            )
        )
    if any(item["execution_status"] != "completed" for item in receipts):
        raise SystemExit(
            "Technical failures recorded; do not count them as content failures"
        )


def grade_case(number, output, private, binary):
    frozen = check_definition()
    case = next(item for item in frozen["cases"] if item["id"] == number)
    target = output / f"{number}-grades.json"
    grader_receipt = output / f"{number}-grader.json"
    if target.exists() or grader_receipt.exists():
        raise RuntimeError(f"Refusing to overwrite grading: {number}")
    answers = []
    for variant in ("current", "candidate"):
        for repeat in range(1, 4):
            answer = output / f"{number}-{variant}-{repeat}.md"
            receipt = read_json(answer.with_suffix(".json"))
            if (
                receipt["execution_status"] != "completed"
                or digest(answer.read_bytes()) != receipt["answer_sha256"]
            ):
                raise RuntimeError(
                    f"Cannot grade incomplete or changed answer: {answer}"
                )
            answers.append((answer.name, answer.read_text()))
    random.Random(SEED + int(number[-2:])).shuffle(answers)
    labels = {f"A{index+1}": name for index, (name, _) in enumerate(answers)}
    write_json(output / f"{number}-blind-map.json", labels)
    rubric = (ROOT / "rubric.md").read_text()
    if number == "case-06":
        rubric += (
            "\n\n旧样本原规则（使用 R1–R5）：\n"
            + (ROOT.parent / "001-source-cli-help/rubric.md").read_text()
        )
    request = (ROOT / "grading.prompt.md").read_text()
    request += (
        f"\n\n仅评分 {number}，检查 ID 为：{', '.join(case['required_checks'])}。\n\n评分规则：\n"
        + rubric
    )
    request += "\n\n原始样本：\n" + (ROOT / case["input"]).read_text()
    for label, (_, body) in zip(labels, answers):
        request += f"\n\n匿名规格 {label}\n<answer>\n{body}\n</answer>"
    receipt = invoke(
        binary,
        request.encode(),
        target,
        private,
        f"{number}-grader",
        ROOT / "grading.schema.json",
    )
    receipt.update(case=number, prompt_labels_hidden=True)
    write_json(grader_receipt, receipt)
    print(
        json.dumps(
            {
                "grader": number,
                "status": receipt["execution_status"],
                "seconds": receipt["elapsed_seconds"],
            }
        ),
        flush=True,
    )
    if receipt["execution_status"] != "completed":
        raise RuntimeError(f"Grading failed: {number}")


def summarize(output):
    manifest = check_round(output)
    frozen = check_definition()
    rows, metadata = [], set()
    for job in manifest["schedule"]:
        receipt = read_json(
            output / f"{job['case']}-{job['variant']}-{job['repeat']}.json"
        )
        metadata.add(
            (
                receipt["model_reported"],
                receipt["reasoning_effort_reported"],
                receipt["cli_version"],
            )
        )
    if len(metadata) != 1 or any(value is None for value in next(iter(metadata))):
        raise RuntimeError(
            f"Generation configuration must be known and identical: {metadata}"
        )
    for case in frozen["cases"]:
        labels = read_json(output / f"{case['id']}-blind-map.json")
        grades = read_json(output / f"{case['id']}-grades.json")
        if grades["case"] != case["id"] or len(grades["answers"]) != 6:
            raise RuntimeError(f"Wrong grading target/count: {case['id']}")
        seen = set()
        for answer in grades["answers"]:
            label = answer["label"]
            if label in seen or label not in labels:
                raise RuntimeError(f"Unknown/duplicate grading label: {label}")
            seen.add(label)
            body = (output / labels[label]).read_text()
            checks = answer["checks"]
            if len(checks) != len(case["required_checks"]) or {
                item["id"] for item in checks
            } != set(case["required_checks"]):
                raise RuntimeError(f"Wrong grading checks: {case['id']} {label}")
            for item in checks:
                if item["score"] not in (0, 1) or not item["reason"]:
                    raise RuntimeError("Invalid grading record")
                if item["score"] == 1 and not item["quotes"]:
                    raise RuntimeError("Positive score requires an exact quote")
                if any(not quote or quote not in body for quote in item["quotes"]):
                    raise RuntimeError(
                        f"Non-verbatim grading quote: {case['id']} {label} {item['id']}"
                    )
            parts = labels[label].removesuffix(".md").split("-")
            rows.append(
                {
                    "case": case["id"],
                    "variant": parts[-2],
                    "repeat": int(parts[-1]),
                    "passed": all(item["score"] == 1 for item in checks),
                    "score": sum(item["score"] for item in checks),
                    "maximum": len(checks),
                    "failed_checks": [
                        item["id"] for item in checks if not item["score"]
                    ],
                }
            )
    summary = {
        "generation_configuration": list(next(iter(metadata))),
        "quote_validation": "all grading quotes found verbatim in their own answer",
        "results": sorted(
            rows, key=lambda row: (row["case"], row["variant"], row["repeat"])
        ),
    }
    write_json(output / "scores.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("run", "grade", "summarize"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--candidate", type=Path, default=ROOT / "templates/candidate-spec-v1.md"
    )
    parser.add_argument("--private-logs", type=Path)
    parser.add_argument("--workers", type=int, choices=(1, 2, 3), default=3)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--case", choices=tuple(f"case-{n:02d}" for n in range(1, 7)))
    args = parser.parse_args()
    if args.operation == "summarize":
        summarize(args.output.resolve())
        return
    binary = shutil.which("codex")
    if not binary or args.private_logs is None:
        parser.error("Codex CLI and --private-logs are required")
    if args.operation == "run":
        run(args, binary)
    else:
        check_round(args.output.resolve())
        cases = [args.case] if args.case else [f"case-{n:02d}" for n in range(1, 7)]
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [
                pool.submit(
                    grade_case,
                    case,
                    args.output.resolve(),
                    args.private_logs.resolve(),
                    binary,
                )
                for case in cases
            ]
            for future in as_completed(futures):
                future.result()


if __name__ == "__main__":
    main()
