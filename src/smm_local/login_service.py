# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SubLang International <https://sublang.ai>
"""Manage the per-user macOS login service."""

import os
import plistlib
import subprocess
from pathlib import Path

LABEL = "ai.smm.local"


def location() -> tuple[Path, str]:
    return Path.home() / "Library/LaunchAgents" / f"{LABEL}.plist", f"gui/{os.getuid()}"


def install(cli: Path, db: Path) -> None:
    plist, domain = location()
    logs = Path.home() / ".local/share/smm-local/logs"
    logs.mkdir(parents=True, exist_ok=True)
    plist.parent.mkdir(parents=True, exist_ok=True)
    previous = plist.read_bytes() if plist.exists() else None
    if previous is not None:
        subprocess.run(["launchctl", "bootout", domain, str(plist)], check=False, stdout=subprocess.DEVNULL)
    data = {"Label": LABEL, "ProgramArguments": [str(cli), "--db", str(db), "serve"],
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


def uninstall() -> None:
    plist, domain = location()
    if plist.exists():
        subprocess.run(["launchctl", "bootout", domain, str(plist)], check=False)
        plist.unlink()
