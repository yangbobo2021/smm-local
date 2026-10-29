"""Exercise the release bundle in a clean fake home, including relocation."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "dist/smm-local-0.2.0-rc1.tar.gz"
FAKE_AGENT = '''#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
name=Path(sys.argv[0]).name
path=Path.home()/"fake-mcp"/(name+".json")
path.parent.mkdir(parents=True,exist_ok=True)
args=sys.argv[1:]
if args[:2]==["mcp","get"]:
    if not path.exists(): sys.exit(1)
    data=json.loads(path.read_text()); print("command: "+data["command"]); sys.exit(0)
if args[:2]==["mcp","add"]:
    path.write_text(json.dumps({"command":args[-1]})); sys.exit(0)
if args[:2]==["mcp","remove"]:
    path.unlink(missing_ok=True); sys.exit(0)
sys.exit(2)
'''


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run(source: Path, env: dict[str, str], *args: str) -> str:
    result = subprocess.run([sys.executable, str(source / "scripts" / args[0]), *args[1:]],
                            env=env, text=True, capture_output=True, timeout=900)
    if result.returncode:
        raise AssertionError(f"{' '.join(args)} failed: {result.stderr[-1000:]}")
    return result.stdout


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="smm-release-check-") as directory:
        base = Path(directory)
        home = base / "home"
        home.mkdir()
        fake_bin = base / "fake-bin"
        fake_bin.mkdir()
        for name in ("codex", "claude"):
            file = fake_bin / name
            file.write_text(FAKE_AGENT)
            file.chmod(0o755)
        env = {**os.environ, "HOME": str(home), "PATH": str(fake_bin) + os.pathsep + os.environ["PATH"],
               "PIP_CACHE_DIR": str(Path.home() / ".cache/pip")}
        with tarfile.open(ARCHIVE) as archive:
            archive.extractall(base, filter="data")
        original = base / "smm-local-0.2.0-rc1"
        check(not list(original.rglob("*.sqlite3")), "archive contains a database")
        check(not (original / ".git").exists(), "archive contains .git")
        run(original, env, "install.py", "--no-service")
        manifest = home / ".local/share/smm-local/install.json"
        first = json.loads(manifest.read_text())
        check(first["mcp_path"].startswith(str(original.resolve())), "first MCP path")
        for name in ("codex", "claude"):
            check((home / f".{name}/skills/smm-search/SKILL.md").is_file(), f"{name} skill")
            check((home / "fake-mcp" / f"{name}.json").is_file(), f"{name} MCP")
        run(original, env, "install.py", "--no-service")
        moved = base / "relocated-package"
        shutil.move(original, moved)
        run(moved, env, "install.py", "--no-service")
        second = json.loads(manifest.read_text())
        check(second["mcp_path"].startswith(str(moved.resolve())), "relocated MCP path")
        wrapper = home / ".local/bin/smm"
        check(str(moved.resolve()) in wrapper.read_text(), "relocated CLI wrapper")
        db = home / ".local/share/smm-local/smm.sqlite3"
        status = subprocess.run([str(wrapper), "status"], env=env, text=True, capture_output=True, timeout=30)
        check(status.returncode == 0, "relocated CLI execution")
        before = hashlib.sha256(db.read_bytes()).hexdigest()
        run(moved, env, "uninstall.py", "--no-service")
        check(db.exists() and hashlib.sha256(db.read_bytes()).hexdigest() == before, "archive was not preserved")
        check(not manifest.exists() and not wrapper.exists(), "entry points remain")
        print(json.dumps({"clean_install": True, "reinstall": True, "relocation": True,
                          "codex_mcp": True, "claude_mcp": True, "uninstall_preserves_db": True}, ensure_ascii=False))


if __name__ == "__main__":
    main()
