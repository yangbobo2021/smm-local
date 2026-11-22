# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SubLang International <https://sublang.ai>
"""Manage the per-user macOS login service."""

import os
import plistlib
import subprocess
from pathlib import Path

LABEL = "ai.smm.local"


def location(label: str = LABEL) -> tuple[Path, str]:
    if not label or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-" for c in label):
        raise ValueError("登录服务 label 无效")
    return Path.home() / "Library/LaunchAgents" / f"{label}.plist", f"gui/{os.getuid()}"


def install(cli: Path, db: Path, *, label: str = LABEL, logs: Path | None = None) -> None:
    plist, domain = location(label)
    logs = logs or Path.home() / ".local/share/smm-local/logs"
    logs.mkdir(parents=True, exist_ok=True)
    plist.parent.mkdir(parents=True, exist_ok=True)
    previous = plist.read_bytes() if plist.exists() else None
    if previous is not None:
        subprocess.run(["launchctl", "bootout", domain, str(plist)], check=False, stdout=subprocess.DEVNULL)
    data = {"Label": label, "ProgramArguments": [str(cli), "--db", str(db), "serve"],
            "WorkingDirectory": str(cli.parent.parent), "RunAtLoad": True, "KeepAlive": True,
            "StandardOutPath": str(logs / "stdout.log"), "StandardErrorPath": str(logs / "stderr.log")}
    plist.write_bytes(plistlib.dumps(data))
    try:
        subprocess.run(["launchctl", "bootstrap", domain, str(plist)], check=True)
    except (OSError, subprocess.SubprocessError):
        if previous is None:
            plist.unlink(missing_ok=True)
        else:
            plist.write_bytes(previous)
            subprocess.run(["launchctl", "bootstrap", domain, str(plist)], check=False)
        raise


def uninstall(*, label: str = LABEL) -> None:
    plist, domain = location(label)
    if plist.exists():
        subprocess.run(["launchctl", "bootout", domain, str(plist)], check=False)
        plist.unlink()
