"""Remove SMM entry points while preserving the archive database."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-service", action="store_true", help="仅用于隔离验证")
    args = parser.parse_args()
    home = Path.home()
    manifest_path = home / ".local/share/smm-local/install.json"
    if not manifest_path.is_file():
        parser.error("未找到 SMM 安装清单")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cli = Path(manifest["cli_path"])
    if not args.no_service and cli.is_file():
        subprocess.run([str(cli), "stop-on-demand"], check=True)
    mcp_path = manifest.get("mcp_path", "")
    for agent in ("codex", "claude"):
        executable = shutil.which(agent)
        if executable:
            result = subprocess.run([executable, "mcp", "get", "smm-local"], text=True, capture_output=True)
            if result.returncode == 0 and mcp_path in result.stdout + result.stderr:
                command = [executable, "mcp", "remove", "smm-local"]
                if agent == "claude":
                    command += ["-s", "user"]
                subprocess.run(command, check=True)
        target = home / f".{agent}/skills/smm-search"
        existing = target / "SKILL.md"
        if existing.is_file() and existing.read_bytes() == (ROOT / "skills/smm-search/SKILL.md").read_bytes():
            shutil.rmtree(target)
    wrapper = Path(manifest.get("wrapper_path", ""))
    if wrapper.is_file() and wrapper.read_text(encoding="utf-8").startswith(
        ("#!/bin/sh\n# Managed by SMM Local\n", "@rem Managed by SMM Local\n")
    ):
        wrapper.unlink()
    if not args.no_service and sys.platform == "darwin" and manifest.get("service") == "已启动":
        subprocess.run([sys.executable, str(ROOT / "scripts/manage_service.py"), "uninstall"], check=True)
    manifest_path.unlink()
    print(json.dumps({"uninstalled": True, "database_preserved": True,
                      "database_path": str(manifest.get("db_path") or manifest_path.with_name("smm.sqlite3"))},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
