"""Install the coworker trial in the current user's home directory."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NAME = "smm-local"


def run(*args: str, env: dict[str, str] | None = None, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(args, text=True, capture_output=True, env=env, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"命令执行超过 {timeout} 秒：{Path(args[0]).name}；请检查网络或服务状态后重试") from exc


def owned_mcp(name: str, command: str, previous: str | None) -> bool:
    result = run(name, "mcp", "get", NAME)
    if result.returncode:
        return False
    output = result.stdout + result.stderr
    if command in output or (previous and previous in output):
        return True
    raise RuntimeError(f"{name} 中已有非本安装管理的 {NAME} MCP；请手工检查后再运行")


def register_mcp(name: str, command: str, previous: str | None) -> str:
    if not shutil.which(name):
        return "未安装"
    existed = owned_mcp(name, command, previous)
    if existed:
        current = run(name, "mcp", "get", NAME)
        if command in current.stdout + current.stderr:
            return "已配置"
        remove = [name, "mcp", "remove", NAME]
        if name == "claude":
            remove += ["-s", "user"]
        result = run(*remove)
        if result.returncode:
            raise RuntimeError(f"{name} MCP 更新失败：{result.stderr.strip()}")
    add = [name, "mcp", "add"]
    if name == "claude":
        add += ["--scope", "user", NAME, "--", command]
    else:
        add += [NAME, "--", command]
    result = run(*add)
    if result.returncode:
        raise RuntimeError(f"{name} MCP 注册失败：{result.stderr.strip()}")
    return "已更新" if existed else "已注册"


def install() -> None:
    parser = argparse.ArgumentParser(description="安装 SMM 同事试用版")
    parser.add_argument("--no-service", action="store_true", help="仅用于隔离验证：不安装登录启动服务")
    parser.add_argument("--no-mcp", action="store_true", help="仅用于隔离验证：不更改 Agent MCP 配置")
    args = parser.parse_args()
    if sys.version_info < (3, 11):
        parser.error("需要 Python 3.11+")
    home = Path.home()
    manifest_path = home / ".local/share/smm-local/install.json"
    previous = json.loads(manifest_path.read_text()) if manifest_path.is_file() else {}
    venv_path = ROOT / ".venv"
    if not (venv_path / "bin/python").is_file():
        print("创建独立 Python 环境…", flush=True)
        venv.EnvBuilder(with_pip=True).create(venv_path)
    pip = venv_path / "bin/python"
    setuptools_check = run(str(pip), "-c", "import setuptools")
    if setuptools_check.returncode:
        print("安装 Python 打包工具（首次安装可能需要几分钟）…", flush=True)
        result = run(str(pip), "-m", "pip", "install", "--disable-pip-version-check",
                     "--timeout", "10", "--retries", "1", "setuptools>=68", timeout=900)
        if result.returncode:
            raise RuntimeError(f"安装打包工具失败：{result.stderr[-1500:]}")
    print("安装 SMM 与运行依赖…", flush=True)
    result = run(str(pip), "-m", "pip", "install", "--disable-pip-version-check", "--no-build-isolation",
                 "--timeout", "10", "--retries", "1", "-e", str(ROOT), timeout=900)
    if result.returncode:
        raise RuntimeError(f"Python 安装失败：{result.stderr[-1500:]}")
    cli = str(venv_path / "bin/smm")
    mcp = str(venv_path / "bin/smm-mcp")
    skill = run(sys.executable, str(ROOT / "scripts/install_skill.py"), "--home", str(home), "--update")
    if skill.returncode:
        raise RuntimeError(skill.stderr.strip() or skill.stdout.strip())
    bin_dir = home / ".local/bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    wrapper = bin_dir / "smm"
    if wrapper.exists() and not wrapper.read_text().startswith("#!/bin/sh\n# Managed by SMM Local\n"):
        raise RuntimeError(f"已有非本安装管理的命令：{wrapper}")
    import shlex
    wrapper.write_text("#!/bin/sh\n# Managed by SMM Local\nexec " + shlex.quote(cli) + ' "$@"\n')
    wrapper.chmod(0o755)
    agents = {}
    if not args.no_mcp:
        print("注册 Agent MCP 与 Skill…", flush=True)
        for name in ("codex", "claude"):
            agents[name] = register_mcp(name, mcp, previous.get("mcp_path"))
    service = "跳过"
    if not args.no_service and sys.platform == "darwin":
        print("启动本机 Web 服务…", flush=True)
        result = run(sys.executable, str(ROOT / "scripts/manage_service.py"), "install")
        if result.returncode:
            raise RuntimeError("本地服务安装失败：" + result.stderr.strip())
        service = "已启动"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({"project_root": str(ROOT), "cli_path": cli, "mcp_path": mcp,
                                         "wrapper_path": str(wrapper), "agents": agents,
                                         "service": service}, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"installed": True, "web": "http://127.0.0.1:8766", "agents": agents,
                      "service": service, "diagnose": f"{wrapper} doctor"}, ensure_ascii=False))


if __name__ == "__main__":
    install()
