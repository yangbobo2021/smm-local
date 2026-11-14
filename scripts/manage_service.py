"""Install or remove a per-user macOS launchd service for automatic sync."""

from __future__ import annotations

import argparse
import json
import os
import plistlib
import subprocess
from pathlib import Path


LABEL = "ai.smm.local"
ROOT = Path(__file__).resolve().parents[1]
PLIST = Path.home() / "Library/LaunchAgents" / f"{LABEL}.plist"
DOMAIN = f"gui/{os.getuid()}"


def plist_data() -> dict:
    data_dir = Path.home() / ".local/share/smm-local"
    manifest = data_dir / "install.json"
    installation = json.loads(manifest.read_text(encoding="utf-8")) if manifest.is_file() else {}
    db_path = Path(installation.get("db_path") or data_dir / "smm.sqlite3").resolve()
    log_dir = data_dir / "logs"
    return {
        "Label": LABEL,
        "ProgramArguments": [str(ROOT / ".venv/bin/smm"), "--db", str(db_path), "serve"],
        "WorkingDirectory": str(ROOT),
        "RunAtLoad": True,
        "KeepAlive": True,
        "StandardOutPath": str(log_dir / "stdout.log"),
        "StandardErrorPath": str(log_dir / "stderr.log"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["install", "uninstall", "status"])
    args = parser.parse_args()
    if args.command == "install":
        if not (ROOT / ".venv/bin/smm").is_file():
            parser.error("请先安装 Python 环境")
        PLIST.parent.mkdir(parents=True, exist_ok=True)
        Path.home().joinpath(".local/share/smm-local/logs").mkdir(parents=True, exist_ok=True)
        if PLIST.exists():
            subprocess.run(["launchctl", "bootout", DOMAIN, str(PLIST)], check=False)
        PLIST.write_bytes(plistlib.dumps(plist_data()))
        subprocess.run(["launchctl", "bootstrap", DOMAIN, str(PLIST)], check=True)
        print(f"已安装并启动 {LABEL}：{PLIST}")
    elif args.command == "uninstall":
        if PLIST.exists():
            subprocess.run(["launchctl", "bootout", DOMAIN, str(PLIST)], check=False)
            PLIST.unlink()
        print(f"已停用 {LABEL}；知识库数据未删除")
    else:
        subprocess.run(["launchctl", "print", f"{DOMAIN}/{LABEL}"], check=False)


if __name__ == "__main__":
    main()
