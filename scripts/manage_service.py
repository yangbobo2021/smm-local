"""Install or remove a per-user macOS launchd service for automatic sync."""

from __future__ import annotations

import argparse
import json
import sys
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from smm_local.login_service import LABEL, install, location, uninstall


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["install", "uninstall", "status"])
    args = parser.parse_args()
    plist, domain = location()
    if args.command == "install":
        cli = ROOT / ".venv/bin/smm"
        if not cli.is_file():
            parser.error("请先安装 Python 环境")
        manifest = Path.home() / ".local/share/smm-local/install.json"
        saved = json.loads(manifest.read_text(encoding="utf-8")) if manifest.is_file() else {}
        install(cli, Path(saved.get("db_path") or manifest.with_name("smm.sqlite3")).resolve())
        print(f"已安装并启动 {LABEL}：{plist}")
    elif args.command == "uninstall":
        uninstall()
        print(f"已停用 {LABEL}；知识库数据未删除")
    else:
        subprocess.run(["launchctl", "print", f"{domain}/{LABEL}"], check=False)


if __name__ == "__main__":
    main()
