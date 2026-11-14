# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SubLang International <https://sublang.ai>
"""Register or remove the per-account installation of the local package."""

import argparse
import json
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

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


def install_wrapper(cli: str) -> Path:
    home = Path.home()
    windows = sys.platform == "win32"
    bin_dir = home / ".local/bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    wrapper = bin_dir / ("smm.cmd" if windows else "smm")
    header = "@rem Managed by SMM Local\n" if windows else "#!/bin/sh\n# Managed by SMM Local\n"
    if wrapper.exists() and not wrapper.read_text(encoding="utf-8").startswith(header):
        raise RuntimeError(f"已有非本安装管理的命令：{wrapper}")
    command = f'@"{cli.replace("%", "%%")}" %*\n' if windows else "exec " + shlex.quote(cli) + ' "$@"\n'
    wrapper.write_text(header + command, encoding="utf-8")
    if not windows:
        wrapper.chmod(0o755)
    return wrapper


def register_online(manifest: Path, *, no_service: bool = False) -> None:
    from .core import shared_db_path
    from .login_service import install as install_login_service

    previous = json.loads(manifest.read_text(encoding="utf-8")) if manifest.is_file() else {}
    db = shared_db_path()
    bin_dir = Path(sys.executable).parent
    suffix = ".exe" if sys.platform == "win32" else ""
    cli, mcp = (str(bin_dir / (name + suffix)) for name in ("smm", "smm-mcp"))
    if not all(Path(path).is_file() for path in (cli, mcp)):
        raise RuntimeError("安装的 SMM 包缺少本机命令")
    run(cli, "--help").check_returncode()
    agents = {}
    for agent in ("codex", "claude"):
        try:
            agents[agent] = register_mcp(agent, mcp, previous.get("mcp_path"))
        except (OSError, RuntimeError) as exc:
            agents[agent] = "注册失败"
            print(f"{exc}。Skill 可以继续使用本机命令。", file=sys.stderr)
    installation = {**previous, "cli_path": cli, "mcp_path": mcp, "db_path": str(db),
                    "agents": agents, "package_environment": str(Path(sys.prefix))}
    if previous.get("wrapper_path"):
        try:
            installation["wrapper_path"] = str(install_wrapper(cli))
        except (OSError, RuntimeError) as exc:
            print(f"旧命令入口更新失败：{exc}", file=sys.stderr)
    if sys.platform == "darwin" and not no_service:
        try:
            run(cli, "--db", str(db), "stop-on-demand").check_returncode()
            install_login_service(Path(cli), db)
            installation["service"] = "已启动"
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            print(f"登录自启配置失败：{exc}。本次继续使用按需启动。", file=sys.stderr)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=manifest.parent,
                                     delete=False) as stream:
        json.dump(installation, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    staged = Path(stream.name)
    try:
        staged.replace(manifest)
    finally:
        staged.unlink(missing_ok=True)


def uninstall_online(manifest: Path) -> None:
    installation = json.loads(manifest.read_text(encoding="utf-8"))
    if Path(installation.get("package_environment", "")).resolve() != Path(sys.prefix).resolve():
        raise ValueError("请使用安装清单所指向的 Python 环境卸载")
    if sys.platform == "darwin" and installation.get("service") == "已启动":
        from .login_service import uninstall

        uninstall()
    run(installation["cli_path"], "stop-on-demand").check_returncode()
    for agent in ("codex", "claude"):
        if not shutil.which(agent):
            continue
        result = run(agent, "mcp", "get", NAME)
        if result.returncode == 0 and installation["mcp_path"] in result.stdout + result.stderr:
            command = [agent, "mcp", "remove", NAME]
            if agent == "claude":
                command += ["-s", "user"]
            run(*command).check_returncode()
    wrapper = Path(installation.get("wrapper_path", ""))
    if wrapper.is_file() and wrapper.read_text(encoding="utf-8").startswith(
        ("#!/bin/sh\n# Managed by SMM Local\n", "@rem Managed by SMM Local\n")
    ):
        wrapper.unlink()
    # Retain the archive path for the next installation, including a migrated archive.
    manifest.write_text(json.dumps({"db_path": installation["db_path"]}, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    print(json.dumps({"uninstalled": True, "database_preserved": True,
                      "database_path": installation["db_path"]}, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["install", "uninstall"])
    parser.add_argument("--no-service", action="store_true", help="使用按需服务，供隔离验收")
    args = parser.parse_args()
    manifest = Path.home() / ".local/share/smm-local/install.json"
    try:
        if args.action == "install":
            register_online(manifest, no_service=args.no_service)
        else:
            uninstall_online(manifest)
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
