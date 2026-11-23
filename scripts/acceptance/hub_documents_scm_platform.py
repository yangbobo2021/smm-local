"""Opt-in 007 actual SCM/LocalService Hub with a separate standard Local actor.

An administrator manages only this task's Hub and fixed Hub CLI operations.
The ordinary worker has no Hub-state permissions. IPC never accepts executable
code, state directories, upgrades, service names or paths outside its fixtures.
"""

from __future__ import annotations
import argparse
import asyncio
import ctypes
import hashlib
import json
import os
from pathlib import Path
import ssl
import subprocess
import sys
import time
import traceback
from urllib.parse import urlsplit
from urllib.request import build_opener, HTTPSHandler, ProxyHandler

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hub_documents_platform import Probe, now
from hub_documents_checks import stopped


def atomic_json(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


class Administrator(Probe):
    @staticmethod
    def actor():
        assert os.name == "nt" and ctypes.windll.shell32.IsUserAnAdmin()
        return {
            "pid": os.getpid(),
            "is_admin": True,
            "role": "only task Hub administrator",
            "platform": sys.platform,
            "python": sys.executable,
        }

    def env(self, role="a"):
        value = super().env(role)
        child = getattr(self, "child_output", None)
        if role == "hub" and child and (child / "phase.txt").exists():
            value.update(
                SMM_007_IDENTITIES=str(child / "process-identities.jsonl"),
                SMM_007_FIXTURES=str(child / "资料 空格"),
                SMM_007_PHASE=str(child / "phase.txt"),
                SMM_007_AUDIT=str(child / "source-opens.jsonl"),
            )
        return value

    def service_identity(self):
        name = self.service_name
        script = (
            "$s=Get-CimInstance Win32_Service -Filter \"Name='"
            + name
            + "'\"; $p=Get-CimInstance Win32_Process -Filter ('ProcessId='+$s.ProcessId); @{service=$s|Select-Object Name,StartName,State,ProcessId,PathName;owner=Invoke-CimMethod -InputObject $p -MethodName GetOwner;sid=Invoke-CimMethod -InputObject $p -MethodName GetOwnerSid;session=(Get-Process -Id $s.ProcessId).SessionId}|ConvertTo-Json -Depth 5"
        )
        value = json.loads(
            self.run(
                "actual-scm-identity",
                ["powershell.exe", "-NoProfile", "-Command", script],
                role="hub",
            )
        )
        assert (
            value["service"]["State"] == "Running"
            and value["sid"]["Sid"] == "S-1-5-19"
            and value["session"] == 0
        ), value
        self.service_pid = value["service"]["ProcessId"]
        self.service_events.append({"at": now(), **value})
        self.save("service-events", self.service_events)
        return value

    def rpc(self, request):
        operation = request["operation"]
        if operation == "enable":
            self.cli("hub", "enable")
            return self.service_identity()
        if operation == "disable":
            pid = self.service_pid
            self.cli("hub", "disable")
            stopped([pid], [("127.0.0.1", self.ports["hub"])])
            self.service_pid = None
            return {"stopped_pid": pid}
        if operation == "archive_identity":
            code = "import json,sys;from smm_hub._archive import Archive,reference_material;print(json.dumps({'archive_id':reference_material(Archive(sys.argv[1]))[0]}))"
            return json.loads(
                self.run(
                    "hub-archive-identity",
                    [
                        self.config["hub_python"],
                        "-I",
                        "-X",
                        "utf8",
                        "-c",
                        code,
                        self.hub_db,
                    ],
                    role="hub",
                )
            )
        assert operation == "hub_cli"
        args = request["args"]
        assert isinstance(args, list) and all(isinstance(a, str) for a in args)
        assert len(args) >= 2 and "--state-dir" not in args
        assert (
            args[0] == "project"
            and args[1] in {"list", "create", "ensure-global", "link", "unlink"}
        ) or (
            args[0] == "documents"
            and args[1]
            in {"add", "set", "remove", "refresh", "sources", "files", "search", "read"}
        )
        if args[:2] == ["documents", "add"]:
            path = Path(args[2]).resolve()
            fixtures = (self.child_output / "资料 空格").resolve()
            assert path.is_relative_to(fixtures)
        expected = request.get("code", 0)
        assert expected in {0, 2}
        return self.cli("hub", *args, code=expected)


class OrdinaryScmClient(Probe):
    def __init__(self, config, out):
        super().__init__(config, out)
        remote = config["external_hub"]
        self.control = Path(remote["control"])
        self.serial = 0
        self.address["hub"] = remote["address"]
        self.ports["hub"] = urlsplit(remote["address"]).port
        self.ca = Path(remote["ca"])
        self.http = build_opener(
            ProxyHandler({}),
            HTTPSHandler(context=ssl.create_default_context(cafile=str(self.ca))),
        )
        self.token = Path(remote["token_file"]).read_text().strip()
        self.token_file.write_text(self.token, encoding="ascii")
        self.hub_state = Path(remote["state"])
        self.hub_db = self.hub_state / "smm-hub.sqlite3"
        self.managed_hub_started = False
        try:
            with self.hub_db.open("rb") as stream:
                stream.read(1)
        except PermissionError:
            self.save(
                "scm-client-boundary",
                {"hub_state_read_denied": True, "ordinary_actor": self.actor()},
            )
        else:
            raise AssertionError(
                "ordinary Local actor unexpectedly can read protected Hub state"
            )

    def rpc(self, operation, **args):
        self.serial += 1
        name = f"{self.serial:04d}"
        request = self.control / (name + ".request.json")
        answer = self.control / (name + ".response.json")
        atomic_json(request, {"operation": operation, **args})
        deadline = time.monotonic() + 120
        while not answer.exists():
            assert time.monotonic() < deadline, "task Hub administrator RPC timed out"
            time.sleep(0.1)
        value = json.loads(answer.read_text())
        assert value["ok"], value
        self.calls.append(
            {
                "label": "task-hub-admin-rpc",
                "operation": operation,
                "args": args,
                "response": value["result"],
            }
        )
        self.save("commands", self.calls)
        return value["result"]

    def cli(self, role, *args, code=0):
        if role == "hub":
            return self.rpc("hub_cli", args=list(map(str, args)), code=code)
        return super().cli(role, *args, code=code)

    def run(self, label, argv, **kwargs):
        if label == "hub-archive":
            return json.dumps(self.rpc("archive_identity"))
        return super().run(label, argv, **kwargs)

    def start(self, role):
        if role == "hub":
            self.rpc("enable")
            self.managed_hub_started = True
            return
        return super().start(role)

    def stop(self, role):
        if role == "hub":
            value = self.rpc("disable")
            self.managed_hub_started = False
            return value
        return super().stop(role)

    def verify_actor(self, actor):
        if actor["argv"] and actor["argv"][0] == "smm_hub.cli":
            assert actor["is_admin"] is True
        else:
            super().verify_actor(actor)

    def cleanup(self):
        try:
            if getattr(self, "managed_hub_started", False):
                self.stop("hub")
        finally:
            super().cleanup()


def ordinary_worker(config, out):
    probe = OrdinaryScmClient(config, out)
    result = None
    try:
        result = asyncio.run(probe.execute())
        result["kind"] = (
            "E2 actual SCM LocalService Hub with separate standard Local; same-host, no physical cross-OS claim"
        )
    except BaseException:
        probe.save("failure", {"traceback": traceback.format_exc(), "at": now()})
        raise
    finally:
        probe.cleanup()
    probe.save("result", result)


def administrator(config, out):
    manager = Administrator(config, out)
    manager.service_name = (
        "smm-hub-"
        + hashlib.sha256(str(manager.hub_state.resolve()).encode()).hexdigest()[:12]
    )
    manager.service_pid = None
    manager.service_events = []
    client = out / "ordinary-client"
    client.mkdir()
    (client / "control").mkdir()
    manager.child_output = client / "platform"
    # The only program-code ACL relaxation is read/execute. The ordinary actor
    # cannot modify the Hub's interpreter or modules and cannot read Hub state.
    packages = Path(config["hub_python"]).parent.parent.parent
    manager.run(
        "protect-task-programs",
        [
            "icacls.exe",
            packages,
            "/inheritance:r",
            "/grant:r",
            "*S-1-5-32-544:(OI)(CI)F",
            "*S-1-5-18:(OI)(CI)F",
            "*S-1-5-19:(OI)(CI)RX",
        ],
    )
    # Set inheritable rights on the task directory only; children must inherit
    # it instead of having their inheritance removed file by file.
    manager.run(
        "inherit-task-programs", ["icacls.exe", str(packages / "*"), "/reset", "/T"]
    )
    manager.run("task-program-file-acl", ["icacls.exe", config["hub_python"]])
    access = json.loads(
        manager.run(
            "task-program-access",
            [
                config["hub_python"],
                "-I",
                "-X",
                "utf8",
                "-c",
                "import ctypes,hashlib,importlib.util,json,pathlib,sys; expected=json.loads(pathlib.Path(sys.argv[1]).read_text()); root=pathlib.Path(importlib.util.find_spec('smm_hub').origin).parent.parent; assert all(hashlib.sha256((root/name).read_bytes()).hexdigest()==digest for name,digest in expected.items()); print(json.dumps({'is_admin':bool(ctypes.windll.shell32.IsUserAnAdmin()),'python':sys.executable,'verified_modules':len(expected),'readable_expected_modules':True}))",
                config["hub_expected"],
            ],
            role="hub",
        )
    )
    assert access["is_admin"] is True and access["readable_expected_modules"] is True
    manager.save("program-access", access)
    process = None
    installed = False
    failures = []
    try:
        installed = True
        manager.cli(
            "hub",
            "setup",
            "--address",
            manager.address["hub"],
            "--bind",
            "127.0.0.1",
            "--port",
            manager.ports["hub"],
            "--tls-cert",
            manager.ca,
            "--tls-key",
            manager.key,
            "--ca-file",
            manager.ca,
        )
        manager.token = (manager.hub_state / "hub-token").read_text().strip()
        manager.token_file.write_text(manager.token, encoding="ascii")
        manager.service_identity()
        (client / "hub-ca.pem").write_bytes(manager.ca.read_bytes())
        (client / "hub-token").write_text(manager.token, encoding="ascii")
        worker = {
            **config,
            "external_hub": {
                "address": manager.address["hub"],
                "ca": str(client / "hub-ca.pem"),
                "token_file": str(client / "hub-token"),
                "state": str(manager.hub_state),
                "control": str(client / "control"),
            },
        }
        target = client / "target.json"
        target.write_text(json.dumps(worker), encoding="utf-8")
        wrapper = Path(__file__).with_name("hub_documents_ci_standard_user.ps1")
        log = open(out / "standard-user.stdout", "wb")
        error = open(out / "standard-user.stderr", "wb")
        args = [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(wrapper),
            "-Python",
            sys.executable,
            "-Runner",
            str(Path(__file__).resolve()),
            "-Config",
            str(target),
            "-Work",
            str(client),
            "-Workspace",
            str(Path(__file__).resolve().parents[2]),
            "-ReadPath",
            str(packages),
        ]
        process = subprocess.Popen(args, stdout=log, stderr=error, env=manager.env())
        seen = set()
        deadline = time.monotonic() + 660
        while process.poll() is None:
            assert time.monotonic() < deadline, "ordinary SCM client timed out"
            for request in sorted((client / "control").glob("*.request.json")):
                if request.name in seen:
                    continue
                seen.add(request.name)
                try:
                    value = {
                        "ok": True,
                        "result": manager.rpc(json.loads(request.read_text())),
                    }
                except BaseException:
                    value = {"ok": False, "error": traceback.format_exc()}
                atomic_json(
                    request.with_name(
                        request.name.replace(".request.json", ".response.json")
                    ),
                    value,
                )
            time.sleep(0.05)
        log.close()
        error.close()
        assert process.returncode == 0, process.returncode
        result = json.loads((manager.child_output / "result.json").read_text())
        assert result["status"] == "passed"
        manager.save("result", result)
    finally:
        if process and process.poll() is None:
            subprocess.run(
                ["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
                capture_output=True,
            )
            process.wait(timeout=20)
        if installed:
            try:
                manager.cli("hub", "disable")
                if manager.service_pid:
                    stopped(
                        [manager.service_pid], [("127.0.0.1", manager.ports["hub"])]
                    )
            except Exception as exc:
                failures.append(str(exc))
            deleted = subprocess.run(
                ["sc.exe", "delete", manager.service_name], capture_output=True
            )
            if deleted.returncode:
                failures.append(deleted.stdout.decode(errors="replace"))
            subprocess.run(
                [
                    "netsh.exe",
                    "advfirewall",
                    "firewall",
                    "delete",
                    "rule",
                    "name=" + manager.service_name,
                ],
                capture_output=True,
            )
        manager.save(
            "service-cleanup",
            {"service": manager.service_name, "failures": failures, "at": now()},
        )
        assert not failures, failures


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--target-config", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    assert sys.platform == "win32"
    config = json.loads(args.target_config.read_text(encoding="utf-8-sig"))
    if config.get("external_hub"):
        ordinary_worker(config, args.output.resolve())
    else:
        administrator(config, args.output.resolve())


if __name__ == "__main__":
    main()
