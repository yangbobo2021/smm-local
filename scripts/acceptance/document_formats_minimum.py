"""Prepare separate installed Python 3.11 products and run the portable fixture.

The fixture driver may use this checkout. Every product invocation uses -I and
the independently installed Local or Hub wheel from a non-source directory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import traceback
import uuid
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prepare(work, materials, uv):
    work = work.resolve()
    work.mkdir(parents=True, exist_ok=False)
    records = []

    def run(label, argv):
        p = subprocess.run(list(map(str, argv)), cwd=ROOT, capture_output=True, timeout=300)
        (work / (label + ".stdout")).write_bytes(p.stdout)
        (work / (label + ".stderr")).write_bytes(p.stderr)
        records.append({"label": label, "argv": list(map(str, argv)), "exit_code": p.returncode,
                        "stdout_sha256": hashlib.sha256(p.stdout).hexdigest(),
                        "stderr_sha256": hashlib.sha256(p.stderr).hexdigest()})
        save(work / "prepare-commands.json", records)
        assert p.returncode == 0, (label, p.returncode, p.stderr.decode("utf-8", "replace"))
        return p.stdout.decode("utf-8").strip()

    python = run("find-python311", [uv, "python", "find", "3.11"])
    run("packages", [python, "-I", ROOT / "scripts/acceptance/hub_documents_packages.py",
                     "--uv", uv, "--output", work / "packages"])
    requirements = work / "documents-locked.txt"
    run("export-locked", [uv, "export", "--frozen", "--extra", "documents", "--no-dev",
                          "--no-emit-project", "--format", "requirements.txt", "-o", requirements])
    packages = work / "packages"
    config = {"expected_system": platform.system(), "materials": str(materials.resolve()),
              "controller_python": sys.executable, "base_python": python,
              "source_root": str(ROOT)}
    for owner in ("local", "hub"):
        env = packages / (owner + "-env")
        executable = env / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        wheel = next((packages / "wheels").glob("smm_" + owner + "-*.whl"))
        run(owner + "-locked-dependencies", [uv, "pip", "sync", "--python", executable,
                                             "--require-hashes", requirements])
        run(owner + "-exact-wheel", [uv, "pip", "install", "--python", executable,
                                     "--no-deps", wheel])
        with ZipFile(wheel) as archive:
            assert archive.testzip() is None
        config[owner] = {"python": str(executable), "wheel": str(wheel),
                         "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest()}
        # Shared standard-account provisioner consumes these exact file fields.
        config[owner + "_wheel"] = str(wheel)
    save(work / "target.json", config)
    return config


def execute(config_path, output):
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    materials = json.loads(Path(config["materials"]).read_text(encoding="utf-8"))
    sys.path.insert(0, str(ROOT / "scripts/acceptance"))
    from hub_documents_platform import Probe
    actor = Probe.actor()  # Native ordinary account, including real Windows token.
    save(output / "controller-identity.json", actor)
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8",
           "SMM_008_MINIMUM_INSTALLED_CONFIG": str(config_path.resolve()),
           "SMM_008_OCR_EXECUTABLE": materials["ocr_executable"],
           "SMM_008_OCR_DATA": materials["ocr_data_dir"],
           "SMM_008_FONT": materials["font"]["path"],
           "ACCEPTANCE_EVIDENCE_DIR": str(output / "attachments")}
    temporary = config_path.resolve().parent / ('business-temp-' + uuid.uuid4().hex)
    save(output / 'temporary-location.json', {'path': str(temporary), 'retained_task_owned': True})
    argv = [sys.executable, "-B", "-m", "pytest", "-q", "--tb=short",
            "tests/test_document_formats_minimum_platform.py", "tests/test_document_formats_minimum_custody.py",
            "--basetemp", str(temporary),
            "--junitxml", str(output / "junit.xml")]
    result = None
    try:
        with (output / "run.stdout").open("wb") as stdout, (output / "run.stderr").open("wb") as stderr:
            p = subprocess.run(argv, cwd=ROOT, env=env, stdout=stdout, stderr=stderr, timeout=300)
        result = {"status": "passed" if p.returncode == 0 else "failed", "argv": argv,
                  "exit_code": p.returncode, "actor": actor,
                  "purpose": "Python3.11 installed business only; not full E/H/X"}
        save(output / "result.json", result)
        assert p.returncode == 0, result
    except BaseException:
        save(output / "failure.json", {"traceback": traceback.format_exc()})
        raise
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="phase", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--work", type=Path, required=True)
    prep.add_argument("--materials", type=Path, required=True)
    prep.add_argument("--uv", default=shutil.which("uv"))
    run = sub.add_parser("run")
    run.add_argument("--target-config", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    value = prepare(a.work, a.materials, a.uv) if a.phase == "prepare" else execute(a.target_config, a.output)
    print(json.dumps({"phase": a.phase, "status": value.get("status", "prepared")}))


if __name__ == "__main__":
    main()
