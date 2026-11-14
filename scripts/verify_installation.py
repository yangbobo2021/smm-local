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
import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VERSION = "0.2.0-rc2"
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
MCP_SMOKE = '''import asyncio,json,os
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client

async def check():
    alternate=os.environ["SMM_TEST_DB"]+".ignored"
    params=StdioServerParameters(command=os.environ["SMM_MCP_ENTRY"],args=[],env={**os.environ,"SMM_DB":alternate})
    async with stdio_client(params) as (reader,writer):
        async with ClientSession(reader,writer) as session:
            await session.initialize()
            result=await session.call_tool("search_conversations",{"query":"晨星 恢复"})
            data=json.loads(result.content[0].text)
            hit=next(x for x in data["results"] if x["source_session_id"]=="rc2-release-smoke")
            message=next(x for x in hit["matched_messages"] if x["position"]==3)
            assert message["preview_truncated"] and len(message["preview"])<=600
            assert "text" not in message
            original=await session.call_tool("read_conversation",{"conversation_id":hit["id"],"start":3,"end":3})
            full=json.loads(original.content[0].text)["messages"][0]["text"]
            assert full==os.environ["SMM_EXPECTED_FULL_TEXT"]
            assert not os.path.exists(alternate)
            print(json.dumps({"conversation_found":True,"preview_truncated":True,"full_read":True}))

asyncio.run(check())
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default=DEFAULT_VERSION)
    args = parser.parse_args()
    archive_path = ROOT / "dist" / f"smm-local-{args.version}.tar.gz"
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
        with tarfile.open(archive_path) as archive:
            archive.extractall(base, filter="data")
        original = base / f"smm-local-{args.version}"
        check(not list(original.rglob("*.sqlite3")), "archive contains a database")
        check(not (original / ".git").exists(), "archive contains .git")
        run(original, env, "install.py", "--no-service")
        manifest = home / ".local/share/smm-local/install.json"
        first = json.loads(manifest.read_text())
        check(first["mcp_path"].startswith(str(original.resolve())), "first MCP path")
        check(first["db_path"] == str((home / ".local/share/smm-local/smm.sqlite3").resolve()), "shared archive path")
        for name in ("codex", "claude"):
            check((home / f".{name}/skills/smm-search/SKILL.md").is_file(), f"{name} skill")
            check((home / "fake-mcp" / f"{name}.json").is_file(), f"{name} MCP")
        run(original, env, "install.py", "--no-service")
        moved = base / "relocated-package"
        shutil.move(original, moved)
        run(moved, env, "install.py", "--no-service")
        second = json.loads(manifest.read_text())
        check(second["mcp_path"].startswith(str(moved.resolve())), "relocated MCP path")
        check(second["db_path"] == first["db_path"], "relocation preserves shared archive path")
        wrapper = home / ".local/bin/smm"
        check(str(moved.resolve()) in wrapper.read_text(), "relocated CLI wrapper")
        db = home / ".local/share/smm-local/smm.sqlite3"
        status = subprocess.run([str(wrapper), "status"], env=env, text=True, capture_output=True, timeout=30)
        check(status.returncode == 0, "relocated CLI execution")
        source = home / ".codex/sessions/release-smoke.jsonl"
        source.parent.mkdir(parents=True, exist_ok=True)
        long_text = "普通诊断记录。" * 140 + "晨星恢复需要先停止写入，再核对索引。"
        source.write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in (
            {"type": "session_meta", "timestamp": "2026-10-29T08:00:00Z", "payload": {"id": "rc2-release-smoke", "cwd": str(base / "project")}},
            {"type": "response_item", "ordinal": 2, "timestamp": "2026-10-29T08:01:00Z", "payload": {"type": "message", "id": "rc2-user", "role": "user", "content": [{"type": "input_text", "text": "晨星恢复的步骤是什么？"}]}},
            {"type": "response_item", "ordinal": 3, "timestamp": "2026-10-29T08:02:00Z", "payload": {"type": "message", "id": "rc2-assistant", "role": "assistant", "content": [{"type": "output_text", "text": long_text}]}},
        )) + "\n", encoding="utf-8")
        imported = subprocess.run([str(wrapper), "sync", "--source", "codex", "--root", str(source.parent)], env=env, text=True, capture_output=True, timeout=30)
        check(imported.returncode == 0 and json.loads(imported.stdout)["messages_new"] == 2, "release sample import")
        source.unlink()
        smoke_env = {**env, "SMM_MCP_ENTRY": str(moved / ".venv/bin/smm-mcp"), "SMM_TEST_DB": str(db), "SMM_EXPECTED_FULL_TEXT": long_text}
        smoke_env.pop("SMM_SEARCH_PREVIEW_CHARS", None)
        smoke = subprocess.run([str(moved / ".venv/bin/python"), "-c", MCP_SMOKE], env=smoke_env, text=True, capture_output=True, timeout=30)
        check(smoke.returncode == 0, f"installed MCP preview and full read: {smoke.stderr[-700:]}")
        check(json.loads(smoke.stdout)["full_read"], "installed MCP full evidence")
        before = hashlib.sha256(db.read_bytes()).hexdigest()
        run(moved, env, "uninstall.py", "--no-service")
        check(db.exists() and hashlib.sha256(db.read_bytes()).hexdigest() == before, "archive was not preserved")
        check(not manifest.exists() and not wrapper.exists(), "entry points remain")
        print(json.dumps({"clean_install": True, "reinstall": True, "relocation": True,
                          "codex_mcp": True, "claude_mcp": True, "deleted_source_preserved": True,
                          "default_preview": True, "full_read": True, "uninstall_preserves_db": True}, ensure_ascii=False))


if __name__ == "__main__":
    main()
