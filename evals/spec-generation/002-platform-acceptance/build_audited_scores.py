"""Build an audited summary from immutable grades after citation-only correction."""

import argparse
from contextlib import redirect_stdout
import io
from pathlib import Path
import shutil
import tempfile

import compare
import verify_results


def build(output):
    output = output.resolve()
    target = output / "scores-audited.json"
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite audited scores: {target}")
    compare.check_round(output)
    audit = compare.read_json(output / "citation-audit.json")
    if audit.get("score_changes") != [] or not audit.get("corrections"):
        raise ValueError(
            "A nonempty citation-only audit with no score changes is required"
        )

    rows = []
    for case in compare.check_definition()["cases"]:
        labels = compare.read_json(output / f"{case['id']}-blind-map.json")
        grades = compare.read_json(output / f"{case['id']}-grades.json")
        for answer in grades["answers"]:
            parts = labels[answer["label"]].removesuffix(".md").split("-")
            checks = answer["checks"]
            rows.append(
                {
                    "case": case["id"],
                    "variant": parts[-2],
                    "repeat": int(parts[-1]),
                    "passed": all(c["score"] == 1 for c in checks),
                    "score": sum(c["score"] for c in checks),
                    "maximum": len(checks),
                    "failed_checks": [c["id"] for c in checks if not c["score"]],
                }
            )
    rows.sort(key=lambda row: (row["case"], row["variant"], row["repeat"]))
    summary = {
        "note": "Scores reproduced from unchanged blind grades; citation corrections are recorded separately in citation-audit.json.",
        "results": rows,
    }

    # Stage separately: an invalid audit must never create a result in the evidence.
    with tempfile.TemporaryDirectory(prefix="smm-audited-scores-") as directory:
        staged = Path(directory) / "round"
        shutil.copytree(output, staged)
        compare.write_json(staged / target.name, summary)
        with redirect_stdout(io.StringIO()):
            verify_results.verify(staged)
        encoded = (staged / target.name).read_bytes()
    with target.open("xb") as stream:
        stream.write(encoded)
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, required=True)
    args = parser.parse_args()
    print(build(args.runs))
