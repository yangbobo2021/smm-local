"""Install the coworker trial in the current user's home directory."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from smm_local.installation import install_wrapper, register_mcp, run


def install() -> None:
    parser = argparse.ArgumentParser(description="安装 SMM 同事试用版")
    parser.add_argument("--no-service", action="store_true", help="仅用于隔离验证：不安装登录启动服务")
    parser.add_argument("--no-mcp", action="store_true", help="仅用于隔离验证：不更改 Agent MCP 配置")
    parser.add_argument("--keep-skills", action="store_true", help="保留触发安装的 Skill 副本")
    args = parser.parse_args()
    if sys.version_info < (3, 11):
        parser.error("需要 Python 3.11+")
    home = Path.home()
    manifest_path = home / ".local/share/smm-local/install.json"
    previous = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
    db_path = Path(previous.get("db_path") or manifest_path.with_name("smm.sqlite3")).resolve()
    venv_path = ROOT / ".venv"
    windows = sys.platform == "win32"
    venv_bin = venv_path / ("Scripts" if windows else "bin")
    suffix = ".exe" if windows else ""
    pip = venv_bin / f"python{suffix}"
    if not pip.is_file():
        print("创建独立 Python 环境…", flush=True)
        venv.EnvBuilder(with_pip=True).create(venv_path)
    print("安装 SMM 与运行依赖…", flush=True)
    result = run(str(pip), "-m", "pip", "install", "--disable-pip-version-check",
                 "--timeout", "10", "--retries", "1", "-e", str(ROOT), timeout=900)
    if result.returncode:
        raise RuntimeError(f"Python 安装失败：{result.stderr[-1500:]}")
    cli = str(venv_bin / f"smm{suffix}")
    mcp = str(venv_bin / f"smm-mcp{suffix}")
    if not args.keep_skills:
        skill = run(sys.executable, str(ROOT / "scripts/install_skill.py"), "--home", str(home), "--update")
        if skill.returncode:
            raise RuntimeError(skill.stderr.strip() or skill.stdout.strip())
    wrapper = install_wrapper(cli)
    agents = {}
    if not args.no_mcp:
        print("注册 Agent MCP 与 Skill…", flush=True)
        for name in ("codex", "claude"):
            try:
                agents[name] = register_mcp(name, mcp, previous.get("mcp_path"))
            except RuntimeError as exc:
                if not args.keep_skills:
                    raise
                agents[name] = "注册失败"
                print(f"{exc}。Skill 可以继续使用本机命令。", file=sys.stderr)
    service = "跳过"
    if args.keep_skills and previous.get("cli_path") and sys.platform != "darwin":
        try:
            stopped = run(cli, "--db", str(db_path), "stop-on-demand")
            if stopped.returncode:
                print("无法更新已运行的后台服务：" + stopped.stderr.strip(), file=sys.stderr)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
    if not args.no_service and sys.platform == "darwin":
        print("启动本机 Web 服务…", flush=True)
        result = run(cli, "--db", str(db_path), "stop-on-demand")
        if not result.returncode:
            result = run(sys.executable, str(ROOT / "scripts/manage_service.py"), "install")
        if result.returncode:
            message = "登录自启配置失败：" + result.stderr.strip()
            if not args.keep_skills:
                raise RuntimeError(message)
            print(message + "。本次继续使用按需启动。", file=sys.stderr)
        else:
            service = "已启动"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=manifest_path.parent,
                                     delete=False) as stream:
        json.dump({"project_root": str(ROOT), "cli_path": cli, "mcp_path": mcp, "db_path": str(db_path),
                   "wrapper_path": str(wrapper), "agents": agents, "service": service},
                  stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    temporary = Path(stream.name)
    try:
        temporary.replace(manifest_path)
    finally:
        temporary.unlink(missing_ok=True)
    print(json.dumps({"installed": True, "web": "http://127.0.0.1:8766", "agents": agents,
                      "service": service, "diagnose": f"{wrapper} doctor"}, ensure_ascii=False))


if __name__ == "__main__":
    install()
