# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SubLang International <https://sublang.ai>
"""Run SMM's source admission checks using the installed Python."""

import argparse
import json
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("validate", "register", "samples-zcode"))
    parser.add_argument("target", help="候选清单路径，或 samples-zcode 的新输出目录")
    parser.add_argument("--fixture")
    parser.add_argument("--db")
    args = parser.parse_args()
    if args.action == "samples-zcode":
        from smm_local.importers.zcode_fixture import SCOPE, create

        directory = Path(args.target).resolve()
        directory.mkdir(parents=True, exist_ok=False)
        paths, expected = create(directory)
        result = {"scope": SCOPE, "expected": expected,
                  "roots": {stage: str(path) for stage, path in paths.items()}}
        (directory / "expected.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 0
    if not args.fixture:
        parser.error("--fixture is required for validate and register")
    command = [sys.executable, "-m", "smm_local.cli"]
    if args.db:
        command.extend(("--db", args.db))
    command.extend(("source", args.action, args.target, "--fixture", args.fixture))
    return subprocess.run(command).returncode


if __name__ == "__main__":
    sys.exit(main())
