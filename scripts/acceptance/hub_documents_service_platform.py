"""Opt-in 007 installed-package flow with an actual Ubuntu user-systemd Hub.

The only service unit touched is derived from this fresh task state directory.
No ESXi host or daily SMM state is accessed.
"""

from __future__ import annotations
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hub_documents_platform import Probe, now
from hub_documents_checks import stopped


class UserServiceProbe(Probe):
    def __init__(self, config, out):
        assert sys.platform == "linux"
        super().__init__(config, out)
        self.unit = (
            "smm-hub-"
            + hashlib.sha256(str(self.hub_state.resolve()).encode()).hexdigest()[:12]
            + ".service"
        )
        self.unit_path = Path.home() / ".config/systemd/user" / self.unit
        assert not self.unit_path.exists()
        self.service_installed = False
        self.service_pid = None
        self.service_events = []
        self.linger_before = None

    def env(self, role="a"):
        env = super().env(role)
        env.update(
            XDG_RUNTIME_DIR="/run/user/" + str(os.getuid()),
            DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/" + str(os.getuid()) + "/bus",
        )
        return env

    def start(self, role):
        if role != "hub":
            return super().start(role)
        if not self.service_installed:
            self.linger_before = self.run(
                "initial-linger",
                ["loginctl", "show-user", os.getuid(), "-p", "Linger", "--value"],
            ).strip()
            self.run(
                "enable-user-linger",
                ["sudo", "-n", "loginctl", "enable-linger", os.getuid()],
            )
            self.run(
                "ensure-user-manager",
                [
                    "sudo",
                    "-n",
                    "systemctl",
                    "start",
                    "user@" + str(os.getuid()) + ".service",
                ],
            )
            self.service_installed = True
            self.cli(
                "hub",
                "setup",
                "--address",
                self.address["hub"],
                "--bind",
                "127.0.0.1",
                "--port",
                self.ports["hub"],
                "--tls-cert",
                self.ca,
                "--tls-key",
                self.key,
                "--ca-file",
                self.ca,
            )
            self.service_installed = True
            self.token = (self.hub_state / "hub-token").read_text().strip()
            self.token_file.write_text(self.token, encoding="ascii")
            self.token_file.chmod(0o600)
        else:
            self.cli("hub", "enable")
        status = self.run(
            "actual-user-service",
            [
                "systemctl",
                "--user",
                "show",
                self.unit,
                "-p",
                "MainPID",
                "-p",
                "ActiveState",
                "-p",
                "ExecStart",
            ],
        )
        pid = int(
            next(
                line.split("=", 1)[1]
                for line in status.splitlines()
                if line.startswith("MainPID=")
            )
        )
        assert pid > 0 and "ActiveState=active" in status
        uid = os.stat("/proc/" + str(pid)).st_uid
        assert uid == os.getuid() and uid != 0
        self.service_pid = pid
        self.service_events.append(
            {
                "action": "started",
                "at": now(),
                "unit": self.unit,
                "pid": pid,
                "actual_uid": uid,
                "systemctl_show": status,
                "definition": self.unit_path.read_text(),
            }
        )
        self.save("service-events", self.service_events)
        self.request("hub", "/v1/info")

    def stop(self, role):
        if role != "hub":
            return super().stop(role)
        pid = self.service_pid
        assert pid
        self.cli("hub", "disable")
        stopped([pid], [("127.0.0.1", self.ports["hub"])])
        self.service_pid = None
        record = {
            "action": "stopped",
            "unit": self.unit,
            "pid": pid,
            "alive": False,
            "at": now(),
        }
        self.service_events.append(record)
        self.save("service-events", self.service_events)
        return record

    def cleanup(self):
        failures = []
        try:
            if self.service_pid:
                self.stop("hub")
            elif self.unit_path.exists():
                value = self.run(
                    "cleanup-owned-user-pid",
                    [
                        "systemctl",
                        "--user",
                        "show",
                        self.unit,
                        "-p",
                        "MainPID",
                        "--value",
                    ],
                ).strip()
                pid = int(value) if value else 0
                self.cli("hub", "disable")
                if pid:
                    stopped([pid], [("127.0.0.1", self.ports["hub"])])
        except Exception as exc:
            failures.append(str(exc))
        try:
            super().cleanup()
        except Exception as exc:
            failures.append(str(exc))
        if self.service_installed:
            try:
                assert (
                    self.unit_path.name == self.unit
                    and self.unit_path.parent == Path.home() / ".config/systemd/user"
                )
                self.unit_path.unlink(missing_ok=True)
                self.run("reload-user-units", ["systemctl", "--user", "daemon-reload"])
                assert not self.unit_path.exists()
            except Exception as exc:
                failures.append(str(exc))
        if self.linger_before is not None and self.linger_before != "yes":
            try:
                self.run(
                    "restore-linger",
                    ["sudo", "-n", "loginctl", "disable-linger", os.getuid()],
                )
            except Exception as exc:
                failures.append(str(exc))
        self.save(
            "service-cleanup",
            {
                "unit": self.unit,
                "unit_removed": not self.unit_path.exists(),
                "linger_initial": self.linger_before,
                "failures": failures,
                "at": now(),
            },
        )
        assert not failures, failures


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--target-config", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    config = json.loads(args.target_config.read_text())
    probe = UserServiceProbe(config, args.output.resolve())
    result = None
    try:
        result = asyncio.run(probe.execute())
        result.update(
            kind="E2 actual Ubuntu user-systemd Hub; same-host Local archives, no physical cross-OS claim"
        )
    except BaseException:
        probe.save("failure", {"traceback": traceback.format_exc(), "at": now()})
        raise
    finally:
        probe.cleanup()
    probe.save("result", result)
    print(json.dumps({"status": result["status"], "output": str(probe.out)}))


if __name__ == "__main__":
    main()
