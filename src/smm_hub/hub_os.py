# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SubLang International <https://sublang.ai>
"""Native service registration for the aggregation server."""

from __future__ import annotations

import hashlib
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
import time


def command(*args, check=True):
    result = subprocess.run(args, capture_output=True, text=True, errors="replace", timeout=45)
    if check and result.returncode:
        details = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"{args[0]} 执行失败：{details}")
    return result


def systemd_arg(value):
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"').replace(
        "\n", "\\n").replace("\r", "\\r").replace("%", "%%").replace("$", "$$") + '"'


class Service:
    def __init__(self, root: Path):
        self.root = root
        suffix = hashlib.sha256(str(root).encode()).hexdigest()[:12]
        self.name = "smm-hub-" + suffix
        self.launch_label = "ai.smm.hub." + suffix
        self.args = [sys.executable, "-m", "smm_hub.cli", "hub", "--state-dir", str(root), "run"]
        self.unit = self.name + ".service"
        self.plist = Path("/Library/LaunchDaemons") / (self.launch_label + ".plist")

    def preflight(self):
        if sys.platform == "darwin":
            # Authenticate on the terminal before commands whose output is captured.
            if not subprocess.run(["sudo", "-v"]).returncode == 0:
                raise RuntimeError("注册 macOS 汇总服务需要管理员权限")
        elif sys.platform == "linux":
            import pwd
            import os
            self.user = pwd.getpwuid(os.getuid()).pw_name
            command("systemctl", "--user", "show-environment")
            result = command("loginctl", "show-user", self.user, "-p", "Linger", "--value")
            if result.stdout.strip() != "yes":
                command("loginctl", "enable-linger", self.user)
        elif sys.platform == "win32":
            import ctypes
            if not ctypes.windll.shell32.IsUserAnAdmin():
                raise RuntimeError("请在管理员终端中配置 Windows 汇总服务")
        else:
            raise RuntimeError("汇总服务管理支持 Linux、Windows 和 macOS")

    def protect_state(self):
        if sys.platform == "win32":
            # The archive and private key are readable only by administrators and the service account.
            command("icacls.exe", str(self.root), "/inheritance:r", "/grant:r",
                    "*S-1-5-32-544:(OI)(CI)F", "*S-1-5-18:(OI)(CI)F", "*S-1-5-19:(OI)(CI)M")
            self.claim_state_owner()

    def claim_state_owner(self):
        if sys.platform == "win32":
            from .document_storage_windows import Directories
            # Explicit root only, handle-bound; no child ACL/owner propagation.
            Directories(self.root).claim_owner()

    def new_runtime_directory(self):
        import os

        # Keep code outside the service-writable archive tree. ProgramData must
        # be the machine directory even when the administrator has a custom home.
        parent = Path(os.environ["ProgramData"]) / "SMM-Hub-Runtimes"
        parent.mkdir(exist_ok=True)
        if parent.is_symlink() or getattr(parent, "is_junction", lambda: False)():
            raise RuntimeError("Windows 汇总程序目录不能是链接")
        runtime = Path(tempfile.mkdtemp(prefix=self.name + "-", dir=parent))
        command("icacls.exe", str(runtime), "/inheritance:r", "/grant:r",
                "*S-1-5-32-544:(OI)(CI)F", "*S-1-5-18:(OI)(CI)F", "*S-1-5-19:(OI)(CI)RX")
        return runtime

    def install(self, config):
        if sys.platform == "linux":
            directory = Path.home() / ".config/systemd/user"
            directory.mkdir(parents=True, exist_ok=True)
            executable = " ".join(map(systemd_arg, self.args))
            (directory / self.unit).write_text(
                "[Unit]\nDescription=SMM aggregation server\n"
                f"[Service]\nExecStart={executable}\nRestart=on-failure\nRestartSec=2s\nUMask=0077\n"
                "[Install]\nWantedBy=default.target\n", encoding="utf-8")
            command("systemctl", "--user", "daemon-reload")
            command("systemctl", "--user", "enable", self.unit)
        elif sys.platform == "darwin":
            import os
            import pwd
            user = pwd.getpwuid(os.getuid()).pw_name
            if not os.getuid():
                raise ValueError("请以普通管理员账户运行 smm-hub，SMM 会单独请求 sudo")
            data = {"Label": self.launch_label, "ProgramArguments": self.args, "UserName": user,
                    "RunAtLoad": True, "KeepAlive": {"SuccessfulExit": False},
                    "StandardErrorPath": str(self.root / "launchd-error.log")}
            with tempfile.NamedTemporaryFile() as file:
                file.write(plistlib.dumps(data))
                file.flush()
                command("sudo", "install", "-o", "root", "-g", "wheel", "-m", "644", file.name, str(self.plist))
            command("sudo", "launchctl", "enable", f"system/{self.launch_label}")
        else:
            self.install_windows(config)

    def install_windows(self, config):
        runtime = Path(config.get("python", sys.executable))
        site = runtime.parent.parent / "Lib" / "site-packages"
        base = config.get("base_python") or str(Path(sys.base_prefix) / "python.exe")
        # The SCM starts the actual interpreter directly. The venv redirector
        # spawns a separate process before the service can register.
        worker = ("import sys; "
                  f"sys.path.insert(0, {str(site)!r}); "
                  "from smm_hub.windows_service import boot; boot()")
        image = subprocess.list2cmdline([base, "-I", "-S", "-c", worker, self.name, str(self.root)])
        present = command("sc.exe", "query", self.name, check=False).returncode == 0
        action = "config" if present else "create"
        command("sc.exe", action, self.name, "binPath=", image, "start=", "auto",
                "obj=", r"NT AUTHORITY\LocalService", "DisplayName=", "SMM aggregation server")
        command("sc.exe", "failure", self.name, "reset=", "86400", "actions=", "restart/3000/restart/5000")
        command("netsh.exe", "advfirewall", "firewall", "delete", "rule", f"name={self.name}", check=False)
        command("netsh.exe", "advfirewall", "firewall", "add", "rule", f"name={self.name}",
                "dir=in", "action=allow", "protocol=TCP", f"localport={config['port']}",
                "remoteip=localsubnet", "profile=any")

    def start(self):
        if sys.platform == "linux":
            command("systemctl", "--user", "start", self.unit)
        elif sys.platform == "darwin":
            name = f"system/{self.launch_label}"
            if command("sudo", "launchctl", "print", name, check=False).returncode:
                command("sudo", "launchctl", "bootstrap", "system", str(self.plist))
            command("sudo", "launchctl", "kickstart", name)
        else:
            from .windows_service import service_state
            if service_state(self.name) != 4:
                command("sc.exe", "start", self.name)

    def stop(self, *, disable):
        if sys.platform == "linux":
            if disable:
                command("systemctl", "--user", "disable", "--now", self.unit)
            else:
                command("systemctl", "--user", "stop", self.unit)
        elif sys.platform == "darwin":
            name = f"system/{self.launch_label}"
            if disable:
                command("sudo", "launchctl", "disable", name)
            if command("sudo", "launchctl", "print", name, check=False).returncode == 0:
                command("sudo", "launchctl", "bootout", name)
                deadline = time.monotonic() + 25
                while command("sudo", "launchctl", "print", name, check=False).returncode == 0:
                    if time.monotonic() >= deadline:
                        raise RuntimeError("等待 macOS 汇总服务卸载超时")
                    time.sleep(.25)
        else:
            from .windows_service import service_state
            if disable:
                command("sc.exe", "config", self.name, "start=", "disabled")
                command("netsh.exe", "advfirewall", "firewall", "delete", "rule", f"name={self.name}", check=False)
            state = service_state(self.name)
            if state not in (1, 3):
                command("sc.exe", "stop", self.name)
            deadline = time.monotonic() + 25
            while service_state(self.name) != 1:
                if time.monotonic() >= deadline:
                    raise RuntimeError("等待 Windows 汇总服务停止超时")
                time.sleep(.25)
