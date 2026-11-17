# SPDX-License-Identifier: Apache-2.0
"""Shared setup and provenance for the optional local acceptance probes."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASELINE = "d2dee18fcc050dcf20bd4108429975477399db8d"


def arguments(description):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--hub-env", type=Path, required=True)
    parser.add_argument("--local-env", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.hub_env = args.hub_env.resolve()
    args.local_env = args.local_env.resolve()
    args.output = args.output.resolve()
    return args


def executable(environment, name):
    folder = "Scripts" if os.name == "nt" else "bin"
    suffix = ".exe" if os.name == "nt" else ""
    return environment / folder / (name + suffix)


def clean_environment():
    return {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("PG") and key not in {"PYTHONPATH", "VIRTUAL_ENV"}
    }


def export_baseline(directory):
    files = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", BASELINE, "src"], cwd=ROOT, text=True
    ).splitlines()
    for name in files:
        target = directory / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(
            subprocess.check_output(["git", "show", f"{BASELINE}:{name}"], cwd=ROOT)
        )
    return directory / "src"


def installed_identity(args):
    identities = {}
    program = """
import hashlib, importlib.util, json, sys
from pathlib import Path
package, names = sys.argv[1], json.loads(sys.argv[2])
root = Path(importlib.util.find_spec(package).origin).parent
print(json.dumps({name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in names}))
"""
    packages = [
        (
            args.hub_env,
            "smm_hub",
            [
                "hub.py",
                "hub_admin.py",
                "projects.py",
                "vibeinsight.py",
                "vibeinsight_settings.py",
            ],
        ),
        (
            args.local_env,
            "smm_local",
            ["core.py", "federation.py", "mcp_server.py", "cli.py"],
        ),
    ]
    for environment, package, names in packages:
        hashes = json.loads(
            subprocess.check_output(
                [
                    str(executable(environment, "python")),
                    "-c",
                    program,
                    package,
                    json.dumps(names),
                ],
                env=clean_environment(),
                text=True,
            )
        )
        for name, observed in hashes.items():
            path = f"src/{package}/{name}"
            expected = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            if observed != expected:
                raise RuntimeError(
                    f"Installed package differs from {path}. Build and reinstall the current wheels."
                )
            identities[path] = observed
    return identities


def save_report(args, evidence, identities):
    revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    files = subprocess.check_output(
        [
            "git",
            "ls-files",
            "src",
            "tests",
            "scripts/acceptance",
            "README.md",
            "TRIAL_GUIDE.md",
            "skills/smm-search/SKILL.md",
            "changes/003-search-vibeinsight-conversations/spec.md",
            "changes/003-search-vibeinsight-conversations/plan.md",
        ],
        cwd=ROOT,
        text=True,
    ).splitlines()
    wheels = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (ROOT / "dist/packages").glob("*.whl")
    }
    data = {
        "status": "passed",
        "acceptance_id": "AT-SMM-VIBEINSIGHT-003",
        "fixture": "isolated synthetic data",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "revision": revision,
        "legacy_revision": BASELINE,
        "installed_source_sha256": identities,
        "source_files_sha256": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in files
        },
        "wheel_sha256": wheels,
        "evidence": evidence,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
