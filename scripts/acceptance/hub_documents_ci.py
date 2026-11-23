"""Run the opt-in 007 wheel probe on an isolated hosted runner.

Windows delegates business actions to a newly created standard account. The
administrator only provisions that account and its task-directory permissions.
"""

from __future__ import annotations
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import traceback

ROOT = Path(__file__).resolve().parents[2]


def export(source, target):
    target.mkdir(parents=True, exist_ok=False)
    manifest = []
    unavailable = []
    for p in sorted(source.rglob("*")):
        if not p.is_file() or p.is_symlink():
            continue
        relative = p.relative_to(source)
        if any(
            part.endswith("-env")
            or part
            in {"wheels", ".documents", "python-cache", "empty-agent", "资料 空格"}
            for part in relative.parts
        ):
            continue
        # Raw archives, credentials, keys and traces stay in the task directory.
        allowed = (
            p.suffix in {".stdout", ".stderr", ".png", ".log"}
            or p.name
            in {
                "commands.json",
                "result.json",
                "failure.json",
                "cleanup.json",
                "stopped-processes.json",
                "controller-identity.json",
                "process-identities.jsonl",
                "source-open-audit.json",
                "runner-bindings.json",
                "local-installation.json",
                "hub-installation.json",
                "web-hub.json",
                "web-a.json",
                "browser-tls.json",
                "lifecycle.json",
                "conversation-document-range.json",
                "standard-user-controller.json",
                "local-expected.json",
                "hub-expected.json",
                "web-joint.json",
                "web-hub-all.json",
                "mixed-batch-a.json",
                "mixed-batch-hub.json",
                "unchanged-source-fingerprints.json",
                "actual-invalid-utf8.json",
                "service-events.json",
                "service-cleanup.json",
                "scm-client-boundary.json",
                "program-access.json",
            }
            or p.name.startswith("mcp-")
            and p.suffix == ".json"
        )
        if p.suffix == ".zip" and "trace" in p.name:
            certificate = os.environ.get("SMM_007_EVIDENCE_CERTIFICATE")
            if certificate:
                certificate_path = source / "evidence-public-certificate.pem"
                if not certificate_path.exists():
                    certificate_path.write_bytes(
                        base64.b64decode(certificate, validate=True)
                    )
                encrypted = (
                    target
                    / "private-traces"
                    / relative.with_suffix(relative.suffix + ".cms")
                )
                encrypted.parent.mkdir(parents=True, exist_ok=True)
                result = subprocess.run(
                    [
                        "openssl",
                        "cms",
                        "-encrypt",
                        "-binary",
                        "-aes256",
                        "-in",
                        str(p),
                        "-out",
                        str(encrypted),
                        "-outform",
                        "DER",
                        str(certificate_path),
                    ],
                    capture_output=True,
                    timeout=30,
                )
                assert result.returncode == 0, result.stderr.decode(errors="replace")
                manifest.append(
                    {
                        "path": encrypted.relative_to(target).as_posix(),
                        "bytes": encrypted.stat().st_size,
                        "sha256": hashlib.sha256(encrypted.read_bytes()).hexdigest(),
                        "format": "CMS encrypted original trace",
                        "original_path": relative.as_posix(),
                        "original_bytes": p.stat().st_size,
                        "original_sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                    }
                )
            else:
                (target / "private-traces-unavailable.json").write_text(
                    json.dumps(
                        {
                            "reason": "No evidence public certificate provided; original traces remain only on ephemeral runner. Not complete formal evidence."
                        }
                    ),
                    encoding="utf-8",
                )
            continue
        if not allowed:
            continue
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copyfile(p, destination)
        except OSError as error:
            # Preserve later readable diagnostics as well as the original
            # business failure; do not relax source ACLs to collect evidence.
            destination.unlink(missing_ok=True)
            unavailable.append(
                {
                    "path": relative.as_posix(),
                    "error_type": type(error).__name__,
                    "errno": error.errno,
                }
            )
            continue
        manifest.append(
            {
                "path": relative.as_posix(),
                "bytes": destination.stat().st_size,
                "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
            }
        )
    if unavailable:
        report = target / "evidence-unavailable.json"
        report.write_text(
            json.dumps({"files": unavailable}, indent=2), encoding="utf-8"
        )
        manifest.append(
            {
                "path": report.name,
                "bytes": report.stat().st_size,
                "sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
            }
        )
    (target / "sha256.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    if unavailable:
        raise RuntimeError("Evidence export incomplete; see evidence-unavailable.json")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--hub-service",
        action="store_true",
        help="Ubuntu actual user-systemd Hub; same-host Local, not physical cross-OS",
    )
    args = parser.parse_args()
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=False)
    env = {**os.environ, "UV_LINK_MODE": "copy"}
    uv = shutil.which("uv")
    assert uv

    def run(label, argv):
        with (
            open(work / (label + ".stdout"), "wb") as stdout,
            open(work / (label + ".stderr"), "wb") as stderr,
        ):
            p = subprocess.run(
                list(map(str, argv)),
                cwd=ROOT,
                env=env,
                stdout=stdout,
                stderr=stderr,
                timeout=900,
            )
        assert p.returncode == 0, (label, p.returncode)

    try:
        packages = work / "packages"
        run(
            "packages",
            [
                sys.executable,
                ROOT / "scripts/acceptance/hub_documents_packages.py",
                "--uv",
                uv,
                "--output",
                packages,
            ],
        )
        interpreter = "Scripts/python.exe" if os.name == "nt" else "bin/python"
        config = {"expected_platform": sys.platform}
        for role in ["local", "hub"]:
            config.update(
                {
                    role + "_python": str(packages / (role + "-env") / interpreter),
                    role + "_expected": str(packages / (role + "-expected.json")),
                    role
                    + "_wheel": str(
                        next((packages / "wheels").glob("smm_" + role + "-*.whl"))
                    ),
                }
            )
        browsers = (
            [
                Path(os.environ.get("PROGRAMFILES", "C:/Program Files"))
                / "Google/Chrome/Application/chrome.exe",
                Path(os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)"))
                / "Microsoft/Edge/Application/msedge.exe",
            ]
            if os.name == "nt"
            else [
                Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
                Path("/usr/bin/google-chrome"),
            ]
        )
        browser = next((p for p in browsers if p.is_file()), None)
        if browser:
            config["browser"] = str(browser)
        path = work / "target.json"
        path.write_text(json.dumps(config, indent=2), encoding="utf-8")
        runner = ROOT / (
            (
                "scripts/acceptance/hub_documents_scm_platform.py"
                if os.name == "nt"
                else "scripts/acceptance/hub_documents_service_platform.py"
            )
            if args.hub_service
            else "scripts/acceptance/hub_documents_platform.py"
        )
        if args.hub_service:
            assert sys.platform in {"linux", "win32"}
        if os.name == "nt" and not args.hub_service:
            run(
                "standard-user",
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    ROOT / "scripts/acceptance/hub_documents_ci_standard_user.ps1",
                    "-Python",
                    sys.executable,
                    "-Runner",
                    runner,
                    "-Config",
                    path,
                    "-Work",
                    work,
                    "-Workspace",
                    ROOT,
                ],
            )
        else:
            run(
                "platform",
                [
                    sys.executable,
                    runner,
                    "--target-config",
                    path,
                    "--output",
                    work / "platform",
                ],
            )
        result = json.loads((work / "platform/result.json").read_text())
        assert result["status"] == "passed"
    except BaseException:
        (work / "failure.json").write_text(
            json.dumps({"traceback": traceback.format_exc()}, indent=2),
            encoding="utf-8",
        )
        raise
    finally:
        export(work, args.output.resolve())


if __name__ == "__main__":
    main()
