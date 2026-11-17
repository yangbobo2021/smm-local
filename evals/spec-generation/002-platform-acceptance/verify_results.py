"""Reproduce scores from immutable grades; validate recorded citation corrections."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import compare


def verify(output, write_report=False):
    manifest = compare.check_round(output)
    definition = compare.check_definition()
    settings, results = set(), []
    for job in manifest["schedule"]:
        stem = f"{job['case']}-{job['variant']}-{job['repeat']}"
        template = (output / f"{job['variant']}.md").read_bytes()
        packet = (compare.ROOT / f"cases/{job['case']}.md").read_bytes()
        request = (
            compare.GENERATION_HEADER.encode()
            + template
            + "\n\n样本：\n\n".encode()
            + packet
        )
        receipt = compare.read_json(output / f"{stem}.json")
        assert receipt["request_sha256"] == compare.digest(request), stem
        assert receipt["template_sha256"] == compare.digest(template), stem
        assert receipt["input_sha256"] == compare.digest(packet), stem
        assert receipt["answer_sha256"] == compare.digest(
            (output / f"{stem}.md").read_bytes()
        ), stem
        assert (
            receipt["execution_status"] == "completed" and receipt["returncode"] == 0
        ), stem
        assert not receipt["tool_invocations_observed"], stem
        settings.add(
            (
                receipt["model_reported"],
                receipt["reasoning_effort_reported"],
                receipt["cli_version"],
            )
        )

    audit_path = output / "citation-audit.json"
    audit = (
        compare.read_json(audit_path)
        if audit_path.exists()
        else {"score_changes": [], "corrections": []}
    )
    assert audit["score_changes"] == [], "Citation audit cannot change scores"
    fixes = {
        (f["file"], f["label"], f["check"], f["quote_index"]): f
        for f in audit["corrections"]
    }
    used = set()
    for case in definition["cases"]:
        number = case["id"]
        grades_path = output / f"{number}-grades.json"
        grades = compare.read_json(grades_path)
        labels = compare.read_json(output / f"{number}-blind-map.json")
        assert (
            grades["case"] == number and len(grades["answers"]) == len(labels) == 6
        ), number
        assert {a["label"] for a in grades["answers"]} == set(labels), number
        assert len(set(labels.values())) == 6, number

        rubric = (compare.ROOT / "rubric.md").read_text()
        if number == "case-06":
            rubric += (
                "\n\n旧样本原规则（使用 R1–R5）：\n"
                + (compare.ROOT.parent / "001-source-cli-help/rubric.md").read_text()
            )
        request = (compare.ROOT / "grading.prompt.md").read_text()
        request += (
            f"\n\n仅评分 {number}，检查 ID 为：{', '.join(case['required_checks'])}。\n\n评分规则：\n"
            + rubric
        )
        request += "\n\n原始样本：\n" + (compare.ROOT / case["input"]).read_text()
        for label, name in labels.items():
            request += f"\n\n匿名规格 {label}\n<answer>\n{(output / name).read_text()}\n</answer>"
        receipt = compare.read_json(output / f"{number}-grader.json")
        assert receipt["request_sha256"] == compare.digest(request.encode()), number
        assert receipt["answer_sha256"] == compare.digest(
            grades_path.read_bytes()
        ), number
        assert (
            receipt["execution_status"] == "completed" and receipt["returncode"] == 0
        ), number
        assert (
            not receipt["tool_invocations_observed"] and receipt["prompt_labels_hidden"]
        ), number
        settings.add(
            (
                receipt["model_reported"],
                receipt["reasoning_effort_reported"],
                receipt["cli_version"],
            )
        )

        for answer in grades["answers"]:
            body = (output / labels[answer["label"]]).read_text()
            checks = answer["checks"]
            assert len(checks) == len(case["required_checks"]), number
            assert {c["id"] for c in checks} == set(case["required_checks"]), number
            for check in checks:
                assert check["score"] in (0, 1) and check["reason"], number
                assert not check["score"] or check["quotes"], number
                for index, quote in enumerate(check["quotes"]):
                    assert quote, number
                    if quote in body:
                        continue
                    key = (grades_path.name, answer["label"], check["id"], index)
                    assert key in fixes, f"Unresolved nonverbatim citation: {key}"
                    fix = fixes[key]
                    assert fix["original"] == quote and fix["replacement"] in body, key
                    assert fix["answer"] == labels[answer["label"]], key
                    assert fix["raw_sha256"] == compare.digest(
                        grades_path.read_bytes()
                    ), key
                    used.add(key)
            parts = labels[answer["label"]].removesuffix(".md").split("-")
            assert parts[-2] in {"current", "candidate"} and int(parts[-1]) in {1, 2, 3}
            results.append(
                {
                    "case": number,
                    "variant": parts[-2],
                    "repeat": int(parts[-1]),
                    "passed": all(c["score"] == 1 for c in checks),
                    "score": sum(c["score"] for c in checks),
                    "maximum": len(checks),
                    "failed_checks": [c["id"] for c in checks if not c["score"]],
                }
            )
    assert used == set(fixes), "Unused or duplicate citation correction"
    assert len(settings) == 1 and all(
        v is not None for v in next(iter(settings))
    ), settings
    results.sort(key=lambda r: (r["case"], r["variant"], r["repeat"]))
    assert len({(r["case"], r["variant"], r["repeat"]) for r in results}) == 36
    summary_path = output / ("scores-audited.json" if fixes else "scores.json")
    assert (
        compare.read_json(summary_path)["results"] == results
    ), "Summary differs from raw scores"
    totals = {}
    for variant in ("current", "candidate"):
        rows = [r for r in results if r["variant"] == variant]
        totals[variant] = {
            "passed_answers": sum(r["passed"] for r in rows),
            "answers": len(rows),
            "score": sum(r["score"] for r in rows),
            "maximum": sum(r["maximum"] for r in rows),
        }
    report = {
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "verifier_sha256": compare.digest(Path(__file__).read_bytes()),
        "round_sha256": compare.digest((output / "round.json").read_bytes()),
        "configuration": list(next(iter(settings))),
        "generations": 36,
        "graders": 6,
        "check_judgments": 150,
        "citation_corrections": len(fixes),
        "score_changes": 0,
        "requests_reconstructed": True,
        "summary_reproduced_from_raw_grades": True,
        "scope": "File integrity, configuration and citation validation; semantic judgments remain those of the blind graders and documented primary-agent audit.",
        "totals": totals,
    }
    if write_report:
        target = output / "verification.json"
        if target.exists():
            raise RuntimeError(f"Refusing to overwrite verification: {target}")
        compare.write_json(target, report)
    print(
        json.dumps(
            {"round": output.name, **totals, "citation_corrections": len(fixes)},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, required=True)
    parser.add_argument(
        "--write-report",
        action="store_true",
        help="Save a new verification.json; default only reads evidence",
    )
    args = parser.parse_args()
    verify(args.runs.resolve(), args.write_report)
