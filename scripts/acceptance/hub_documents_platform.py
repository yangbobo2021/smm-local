"""Opt-in 007 E1 against independent wheels, real HTTPS/CLI/Web/stdio.

Only newly created task archives and synthetic sources are used. This runner
never accesses home ESXi, installs system services, or changes daily SMM.
"""

from __future__ import annotations
import argparse
import asyncio
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import socket
import ssl
import subprocess
import sys
import time
import traceback
from urllib.error import HTTPError
from urllib.request import Request, HTTPSHandler, ProxyHandler, build_opener

# Only sibling evidence helpers, never product source, enter this controller.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from hub_documents_checks import (
    document_set,
    exact_read,
    normalized,
    stopped,
    selfcheck,
)


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Probe:
    def __init__(self, config, out):
        assert not out.exists(), "use a fresh evidence directory"
        out.mkdir(parents=True, mode=0o700)
        self.out = out
        self.config = config
        self.calls = []
        self.processes = {}
        self.stops = []
        self.logs = []
        self.expected = {}
        self.stable_mcp = []
        self.started = now()
        self.phase = "prepare"
        self.identities = out / "process-identities.jsonl"
        self.audit = out / "source-opens.jsonl"
        self.fixtures = out / "资料 空格"
        self.fixtures.mkdir()
        self.empty = out / "empty-agent"
        self.empty.mkdir()
        self.db = {role: out / role / "local.sqlite3" for role in ("a", "b")}
        self.hub_state = out / "hub"
        self.hub_state.mkdir()
        self.hub_db = self.hub_state / "smm-hub.sqlite3"
        self.ports = {role: free_port() for role in ("a", "b", "hub")}
        self.address = {
            role: ("https" if role == "hub" else "http") + "://127.0.0.1:" + str(port)
            for role, port in self.ports.items()
        }
        self.token = "synthetic-007-e1-" + os.urandom(32).hex()
        self.token_file = out / "hub-token"
        self.token_file.write_text(self.token, encoding="ascii")
        self.token_file.chmod(0o600)
        self.ca = out / "tls.pem"
        self.key = out / "tls-key.pem"
        self.run(
            "openssl",
            [
                "openssl",
                "req",
                "-x509",
                "-newkey",
                "rsa:2048",
                "-nodes",
                "-keyout",
                self.key,
                "-out",
                self.ca,
                "-days",
                "2",
                "-subj",
                "/CN=localhost",
                "-addext",
                "subjectAltName=DNS:localhost,IP:127.0.0.1",
            ],
        )
        self.key.chmod(0o600)
        self.http = build_opener(
            ProxyHandler({}),
            HTTPSHandler(context=ssl.create_default_context(cafile=str(self.ca))),
        )
        # An observation-only hook. It records source opens and process identity,
        # then executes the installed module unchanged, without source PYTHONPATH.
        self.bootstrap = r"""import ctypes,json,os,pathlib,runpy,sys,time
identity={'pid':os.getpid(),'python':sys.executable,'platform':sys.platform,'argv':sys.argv[1:],'time':time.time()}
if os.name=='nt':
 sid=ctypes.c_ulong();assert ctypes.windll.kernel32.ProcessIdToSessionId(os.getpid(),ctypes.byref(sid));identity.update(is_admin=bool(ctypes.windll.shell32.IsUserAnAdmin()),session_id=sid.value)
else:identity['uid']=os.getuid()
with open(os.environ['SMM_007_IDENTITIES'],'a',encoding='utf-8') as f:f.write(json.dumps(identity)+'\n')
root=os.path.normcase(os.path.abspath(os.environ['SMM_007_FIXTURES']))
def hook(event,args):
 if event=='open' and isinstance(args[0],(str,bytes)):
  path=os.path.normcase(os.path.abspath(os.fsdecode(args[0])))
  if path==root or path.startswith(root+os.sep):
   phase=pathlib.Path(os.environ['SMM_007_PHASE']).read_text(encoding='utf-8')
   with open(os.environ['SMM_007_AUDIT'],'a',encoding='utf-8') as f:f.write(json.dumps({'pid':os.getpid(),'path':path,'phase':phase,'mode':args[1]})+'\n')
sys.addaudithook(hook)
module=sys.argv[1];sys.argv=sys.argv[1:];runpy.run_module(module,run_name='__main__')
"""
        self.save(
            "runner-bindings",
            {
                p.name: sha(p.read_bytes())
                for p in [
                    Path(__file__),
                    Path(__file__).with_name("hub_documents_checks.py"),
                    Path(__file__).with_name("local_documents_mcp_worker.py"),
                ]
            },
        )
        self.save("controller-identity", self.actor())
        selfcheck()

    @property
    def phase(self):
        return self._phase

    @phase.setter
    def phase(self, value):
        self._phase = value
        (self.out / "phase.txt").write_text(value, encoding="utf-8")

    def save(self, name, value):
        (self.out / (name + ".json")).write_text(
            json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def actor():
        value = {
            "pid": os.getpid(),
            "platform": sys.platform,
            "os": platform.platform(),
            "python": sys.executable,
        }
        if os.name == "nt":
            import ctypes

            value["is_admin"] = bool(ctypes.windll.shell32.IsUserAnAdmin())
            assert not value["is_admin"], "E1 requires an actual standard-user token"
        else:
            value["uid"] = os.getuid()
            assert value["uid"] != 0, "E1 requires an ordinary user"
        return value

    def env(self, role="a"):
        env = {
            **os.environ,
            "PYTHONUTF8": "1",
            "PYTHONIOENCODING": "utf-8",
            "SMM_CODEX_ROOT": str(self.empty),
            "SMM_CLAUDE_ROOT": str(self.empty),
            "SMM_SERVICE_PORT": str(self.ports.get(role, self.ports["a"])),
            "SSL_CERT_FILE": str(self.ca),
            "SMM_007_IDENTITIES": str(self.identities),
            "SMM_007_FIXTURES": str(self.fixtures),
            "SMM_007_PHASE": str(self.out / "phase.txt"),
            "SMM_007_AUDIT": str(self.audit),
        }
        env.pop("PYTHONPATH", None)
        env.pop("VIRTUAL_ENV", None)
        return env

    def argv(self, role, module, *args):
        return [
            self.config["hub_python" if role == "hub" else "local_python"],
            "-I",
            "-B",
            "-X",
            "utf8",
            "-c",
            self.bootstrap,
            module,
            *map(str, args),
        ]

    def run(self, label, argv, *, code=0, role="a", timeout=120):
        started = now()
        p = subprocess.run(
            list(map(str, argv)),
            capture_output=True,
            env=self.env(role) if hasattr(self, "ca") else os.environ,
            timeout=timeout,
        )
        record = {
            "label": label,
            "argv": list(map(str, argv)),
            "phase": self.phase,
            "started_at": started,
            "finished_at": now(),
            "exit_code": p.returncode,
            "stdout": p.stdout.decode("utf-8", errors="replace"),
            "stderr": p.stderr.decode("utf-8", errors="replace"),
            "stdout_bytes_base64": base64.b64encode(p.stdout).decode(),
            "stderr_bytes_base64": base64.b64encode(p.stderr).decode(),
        }
        self.calls.append(record)
        self.save("commands", self.calls)
        assert p.returncode == code, record
        return record["stdout"]

    def cli(self, role, *args, code=0):
        prefix = (
            ["hub", "--state-dir", self.hub_state]
            if role == "hub"
            else ["--db", self.db[role]]
        )
        out = self.run(
            role + "-cli",
            self.argv(
                role,
                "smm_hub.cli" if role == "hub" else "smm_local.cli",
                *prefix,
                *args,
            ),
            code=code,
            role=role,
        )
        return json.loads(out) if code == 0 else out

    def request(self, role, path, body=None, *, code=200, method=None):
        url = self.address[role] + path
        headers = {"Content-Type": "application/json", "X-SMM-UI": "1"}
        if role == "hub":
            headers["Authorization"] = "Bearer " + self.token
        request = Request(
            url,
            data=(
                None if body is None else json.dumps(body, ensure_ascii=False).encode()
            ),
            headers=headers,
            method=method,
        )
        try:
            with self.http.open(request, timeout=8) as response:
                status = response.status
                raw = response.read()
        except HTTPError as exc:
            status = exc.code
            raw = exc.read()
        value = json.loads(raw)
        self.calls.append(
            {
                "label": "http-" + role,
                "path": path,
                "phase": self.phase,
                "request": body,
                "status": status,
                "response": value,
            }
        )
        self.save("commands", self.calls)
        assert status == code, (path, status, value)
        return value

    def start(self, role):
        if role == "hub":
            args = self.argv(
                role,
                "smm_hub.cli",
                "serve-hub",
                "--state-dir",
                self.hub_state,
                "--token-file",
                self.token_file,
                "--host",
                "127.0.0.1",
                "--port",
                self.ports[role],
                "--tls-cert",
                self.ca,
                "--tls-key",
                self.key,
            )
        else:
            args = self.argv(
                role,
                "smm_local.cli",
                "--db",
                self.db[role],
                "serve",
                "--host",
                "127.0.0.1",
                "--port",
                self.ports[role],
                *(["--skip-initial-sync"] if self.phase == "prepare" else []),
            )
        log = open(self.out / (role + "-server-" + str(len(self.logs)) + ".log"), "wb")
        self.logs.append(log)
        process = subprocess.Popen(
            list(map(str, args)), stdout=log, stderr=log, env=self.env(role)
        )
        self.processes[role] = process
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline:
            assert process.poll() is None, (role, "server exited")
            try:
                self.request(role, "/v1/info" if role == "hub" else "/api/status")
                return
            except (OSError, TimeoutError):
                time.sleep(0.2)
        raise AssertionError("server not ready: " + role)

    def stop(self, role):
        process = self.processes.pop(role)
        pids = [process.pid]
        if os.name == "nt" and process.poll() is None:
            # A Windows venv executable can be a launcher for another real PID.
            script = (
                "$all=Get-CimInstance Win32_Process; $ids=@("
                + str(process.pid)
                + "); do {$next=@($all|Where-Object {$ids -contains $_.ParentProcessId -and $ids -notcontains $_.ProcessId}|ForEach-Object {$_.ProcessId}); $ids+=$next} while ($next.Count -gt 0); ConvertTo-Json -Compress -InputObject @($ids)"
            )
            pids = json.loads(
                self.run(
                    "owned-windows-tree",
                    ["powershell.exe", "-NoProfile", "-Command", script],
                    role=role,
                )
            )
            self.run(
                "stop-owned-windows-tree",
                ["taskkill.exe", "/PID", process.pid, "/T", "/F"],
                role=role,
            )
        elif process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
        stopped(pids, [("127.0.0.1", self.ports[role])])
        record = {
            "role": role,
            "pid": process.pid,
            "checked_tree_pids": pids,
            "exit_code": process.returncode,
            "alive": False,
        }
        self.stops.append(record)
        self.save("stopped-processes", self.stops)
        return record

    def check_install(self):
        for role in ("local", "hub"):
            manifest = Path(self.config[role + "_expected"])
            wheel = Path(self.config[role + "_wheel"])
            mapping = json.loads(manifest.read_text())
            code = """import hashlib,importlib.util,json,pathlib,sys
role=sys.argv[1];expected=json.loads(pathlib.Path(sys.argv[2]).read_text());module=importlib.util.find_spec('smm_'+role);root=pathlib.Path(module.origin).parent.parent
for name,sha in expected.items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==sha,name
if role=='hub':assert importlib.util.find_spec('smm_local') is None
print(json.dumps({'role':role,'python':sys.executable,'site_root':str(root),'module_sha256':expected}))
"""
            result = json.loads(
                self.run(
                    "installed-" + role,
                    [self.config[role + "_python"], "-I", "-c", code, role, manifest],
                )
            )
            self.save(
                role + "-installation",
                {
                    "wheel": str(wheel),
                    "wheel_sha256": sha(wheel.read_bytes()),
                    **result,
                },
            )

    def policy(self, role, project, enabled=True):
        status = self.cli(role, "documents", "sync-status")
        p = next(p for p in status["projects"] if p["project_id"] == project["id"])
        return self.cli(
            role,
            "documents",
            "sync-policy",
            p["project_key"],
            "--enabled",
            "yes" if enabled else "no",
            "--expected-hub-id",
            status["hub_id"],
            "--expected-generation",
            p["generation"],
        )

    def source(self, role, name, texts, project=None):
        root = self.fixtures / (role + " " + name)
        root.mkdir()
        raws = {}
        for name, raw in texts.items():
            path = root / name
            path.write_bytes(raw)
            raws[str(path.resolve())] = raw
        args = ["documents", "add", root] + (
            ["--project-id", project["id"]] if project else []
        )
        source = self.cli(role, *args)
        assert source["status"] == "pending"
        self.phase = "explicit-refresh"
        self.cli(role, "documents", "refresh", "--source-id", source["id"])
        self.phase = "archive-only"
        files = self.cli(role, "documents", "files", "--source-id", source["id"])
        assert {str(Path(f["path"]).resolve()) for f in files} == set(raws)
        if role == "hub":
            origin = self.hub_origin
        else:
            origin = self.origins[role]
        entries = [
            {
                "origin": {**origin, "document_id": f["id"]},
                "version": 1,
                "raw": raws[str(Path(f["path"]).resolve())],
            }
            for f in files
        ]
        self.expected.update(
            {
                (
                    e["origin"]["device_id"],
                    e["origin"]["archive_id"],
                    e["origin"]["document_id"],
                ): e
                for e in entries
            }
        )
        return source, entries, root

    def verify(self, role, result, expected):
        document_set(result["results"], expected)
        for hit in result["results"]:
            key = tuple(
                hit["origin"][k] for k in ("device_id", "archive_id", "document_id")
            )
            entry = next(
                e
                for e in expected
                if tuple(
                    e["origin"][k] for k in ("device_id", "archive_id", "document_id")
                )
                == key
                and e["version"] == hit["version"]
            )
            value = self.cli(role, "documents", "read", "--reference", hit["reference"])
            exact_read(value, entry["raw"], hit["start"], hit["end"])
        return result

    def identity(self, role):
        code = """import json,sys
from smm_local.core import Archive
from smm_local import references,federation
x=Archive(sys.argv[1]);print(json.dumps({'archive_id':references.material(x)[0],'device_id':federation.hub_config(x)['device_id']}))
"""
        return json.loads(
            self.run(
                "archive-" + role,
                [self.config["local_python"], "-I", "-c", code, self.db[role]],
                role=role,
            )
        )

    async def mcp(self, role, steps):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        number = len(list(self.out.glob("mcp-*.json"))) + 1
        receipt = self.out / ("mcp-" + str(number) + "-process.json")
        child = self.argv(role, "smm_local.mcp_server", "--db", self.db[role])
        args = [
            self.config["local_python"],
            "-I",
            str(Path(__file__).with_name("local_documents_mcp_worker.py")),
            str(receipt),
            json.dumps(child),
        ]
        answers = []
        records = []
        with open(
            self.out / ("mcp-" + str(number) + ".stderr"), "w", encoding="utf-8"
        ) as errors:
            async with stdio_client(
                StdioServerParameters(
                    command=args[0], args=args[1:], env=self.env(role)
                ),
                errlog=errors,
            ) as (reader, writer):
                async with ClientSession(reader, writer) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    for name in [
                        "list_document_sources",
                        "search_documents",
                        "read_document",
                    ]:
                        assert (
                            next(
                                t for t in tools.tools if t.name == name
                            ).annotations.readOnlyHint
                            is True
                        )
                    for name, body in steps:
                        response = await session.call_tool(name, body)
                        records.append(
                            {
                                "name": name,
                                "request": body,
                                "response": response.model_dump(mode="json"),
                            }
                        )
                        assert not response.isError
                        answers.append(json.loads(response.content[0].text))
        self.save(
            "mcp-" + str(number), {"transport": "actual stdio", "records": records}
        )
        process = json.loads(receipt.read_text())
        assert not process["alive"] and process["exit_code"] == 0
        stopped([process["pid"]], [])
        return answers

    def wait_idle(self, role):
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline:
            if not self.request(role, "/api/status")["sync"]["running"]:
                return
            time.sleep(0.2)
        raise AssertionError("local synchronization did not settle")

    async def mixed_batch(self, page, role, project_id):
        from playwright.async_api import expect

        prefix = "hub" if role == "hub" else "doc"
        endpoint = "/v1" if role == "hub" else "/api"
        actor = "hub" if role == "hub" else "a"
        originals = {
            "batch-A.txt": b"mixedbatchnonce original A",
            "batch-C.txt": "mixedbatchnonce 原件C😀\r\nsecond".encode(),
        }
        files = [
            {
                "name": "batch-A.txt",
                "mimeType": "text/plain",
                "buffer": originals["batch-A.txt"],
            },
            {"name": "batch-B.txt", "mimeType": "text/plain", "buffer": b"\xff"},
            {
                "name": "batch-C.txt",
                "mimeType": "text/plain",
                "buffer": originals["batch-C.txt"],
            },
        ]
        await page.locator("#" + prefix + "-upload-files").set_input_files(files)
        report = page.locator("#" + prefix + "-upload-results")
        await expect(report.locator("li")).to_have_count(3)
        for name, status in [
            ("batch-A.txt", "成功"),
            ("batch-B.txt", "失败"),
            ("batch-C.txt", "成功"),
        ]:
            row = report.locator("li").filter(has_text=name + "：")
            await expect(row).to_be_visible()
            assert status in await row.inner_text()
        library = self.request(
            actor, endpoint + "/documents/library?project_id=" + str(project_id)
        )
        assert {d["display_name"] for d in library} == set(originals) and len(
            library
        ) == 2
        result = self.request(
            actor,
            endpoint + "/documents/search",
            {
                **(self.hub_context if role == "hub" else {}),
                "query": "mixedbatchnonce",
                "limit": 50,
            },
        )
        source_origin = self.hub_origin if role == "hub" else self.origins["a"]
        expected = [
            {
                "origin": {**source_origin, "document_id": d["id"]},
                "version": 1,
                "raw": originals[d["display_name"]],
            }
            for d in library
        ]
        document_set(result["results"], expected)
        reads = []
        for hit in result["results"]:
            value = self.request(
                actor,
                endpoint + "/documents/read",
                {
                    **(self.hub_context if role == "hub" else {}),
                    "reference": hit["reference"],
                },
            )
            exact_read(value, originals[hit["display_name"]])
            reads.append(value)
        await page.screenshot(
            path=str(self.out / ("web-" + role + "-mixed-batch.png")), full_page=True
        )
        self.save(
            "mixed-batch-" + role,
            {
                "project_id": project_id,
                "report": await report.inner_text(),
                "library": library,
                "search": result,
                "reads": reads,
            },
        )
        for left in [1, 0]:
            async with page.expect_response(
                lambda r: "/documents/library/" in r.url
                and r.request.method == "DELETE"
            ) as response:
                await page.locator("#" + prefix + "-library-list").get_by_role(
                    "button", name="移除文档"
                ).first.click()
            assert (await response.value).status == 200
            await expect(
                page.locator("#" + prefix + "-library-list input[type=file]")
            ).to_have_count(left)
        assert (
            self.request(
                actor,
                endpoint + "/documents/search",
                {
                    **(self.hub_context if role == "hub" else {}),
                    "query": "mixedbatchnonce",
                    "limit": 50,
                },
            )["results"]
            == []
        )

    @staticmethod
    def literal_display_check(value):
        assert (
            value["window_marker_unset"] is True
            and value["legacy_marker_unset"] is True
        )
        assert value["embedded_nodes"] == 0
        assert value["trigger_requests"] == []

    @staticmethod
    def read_target_check(rows, expected):
        assert len(rows) == len(expected)
        assert {row["name"] for row in rows} == set(expected)
        assert len({row["name"] for row in rows}) == len(rows)
        for row in rows:
            assert row["id"] == expected[row["name"]]

    @staticmethod
    def ownership_equal(before, after):
        assert before == after, "rejected write changed persistent/API state"

    def ownership_state(self):
        value = {}
        for role, prefix in [("a", "/api"), ("hub", "/v1")]:
            value[role] = {
                resource: self.request(role, prefix + "/documents/" + resource)
                for resource in ["sources", "files", "library"]
            }
        # E1 owns both foreground archives. SCM's ordinary actor must never
        # gain direct state access; that E2 case has a separate identity gate.
        if "external_hub" not in self.config:
            code = r"""import hashlib,json,pathlib,sqlite3,sys
result={}
for db in sys.argv[1:]:
 c=sqlite3.connect(pathlib.Path(db).as_uri()+'?mode=ro',uri=True)
 tables=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%document%' ORDER BY name")]
 rows={name:sorted([list(r) for r in c.execute('SELECT * FROM "'+name.replace('"','""')+'"')],key=repr) for name in tables}
 raw=pathlib.Path(db).parent/'.documents'
 disk={str(p.relative_to(raw)):{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns} for p in sorted(raw.rglob('*')) if p.is_file()}
 encoded=lambda value:json.dumps(value,sort_keys=True,default=lambda item:{'sqlite_blob_hex':item.hex()}).encode()
 result[pathlib.Path(db).name]={'table_sha256':{name:hashlib.sha256(encoded(value)).hexdigest() for name,value in rows.items()},'managed_disk':disk};c.close()
print(json.dumps(result,sort_keys=True,default=lambda value:{'sqlite_blob_hex':value.hex()}))
"""
            for role, db in [("a", self.db["a"]), ("hub", self.hub_db)]:
                value[role]["persistent"] = json.loads(
                    self.run(
                        "ownership-readonly-snapshot-" + role,
                        [
                            self.config[
                                "local_python" if role == "a" else "hub_python"
                            ],
                            "-I",
                            "-X",
                            "utf8",
                            "-c",
                            code,
                            db,
                        ],
                    )
                )
        return value

    def forged_ownership(self, projected, replica_hit, native):
        known = {
            "api": {"files": ["one", "two"]},
            "db": {"table_sha256": "known"},
            "disk": {"file.txt": {"sha256": "original", "mtime_ns": 1}},
        }
        self.ownership_equal(known, known)
        for wrong in [
            {**known, "api": {"files": ["one"]}},
            {**known, "db": {"table_sha256": "changed"}},
            {**known, "disk": {"file.txt": {"sha256": "changed", "mtime_ns": 1}}},
            {**known, "disk": {"forged.txt": {"sha256": "original", "mtime_ns": 1}}},
        ]:
            try:
                self.ownership_equal(known, wrong)
            except AssertionError:
                pass
            else:
                raise AssertionError("ownership detector missed changed state")
        before = self.ownership_state()
        replica_source = next(
            s for s in before["hub"]["sources"] if s["id"] in replica_hit["source_ids"]
        )
        remote = {
            **self.hub_context,
            "project_id": projected["id"],
            "project_key": projected["source_key"],
        }
        replica = {
            **remote,
            "expected_version": replica_hit["version"],
            "expected_revision": replica_source["revision"],
        }
        payload = base64.b64encode(b"forged independent forbidden bytes").decode()
        assert len(native["project_ids"]) == 1
        native_project = native["project_ids"][0]
        assert native_project not in {p["id"] for p in self.cli("a", "projects")}
        operations = [
            (
                "hub",
                "POST",
                "/v1/documents/library",
                {
                    **remote,
                    "name": "forged.txt",
                    "submission_id": os.urandom(16).hex(),
                    "content_base64": payload,
                },
                400,
            ),
            (
                "hub",
                "PUT",
                "/v1/documents/library/" + replica_hit["id"],
                {
                    **replica,
                    "submission_id": os.urandom(16).hex(),
                    "content_base64": payload,
                },
                400,
            ),
            (
                "hub",
                "DELETE",
                "/v1/documents/library/" + replica_hit["id"],
                replica,
                400,
            ),
            (
                "hub",
                "PUT",
                "/v1/documents/sources/" + replica_source["id"],
                {
                    **remote,
                    "project_ids": [self.d["id"]],
                    "exclude": [],
                    "recursive": True,
                },
                400,
            ),
            (
                "a",
                "POST",
                "/api/documents/library",
                {
                    "project_id": native_project,
                    "name": "forged.txt",
                    "submission_id": os.urandom(16).hex(),
                    "content_base64": payload,
                },
                400,
            ),
            (
                "a",
                "PUT",
                "/api/documents/library/" + native["id"],
                {
                    "project_id": self.a["id"],
                    "expected_version": native["version"],
                    "expected_revision": native["source_revision"],
                    "submission_id": os.urandom(16).hex(),
                    "content_base64": payload,
                },
                400,
            ),
            (
                "a",
                "DELETE",
                "/api/documents/library/" + native["id"],
                {
                    "project_id": self.a["id"],
                    "expected_version": native["version"],
                    "expected_revision": native["source_revision"],
                },
                400,
            ),
            (
                "a",
                "PUT",
                "/api/documents/sources/" + native["source_id"],
                {"project_ids": [self.a["id"]], "exclude": [], "recursive": True},
                400,
            ),
        ]
        outcomes = []
        for role, method, route, body, status in operations:
            response = self.request(role, route, body, method=method, code=status)
            after = self.ownership_state()
            self.ownership_equal(before, after)
            outcomes.append(
                {
                    "role": role,
                    "method": method,
                    "path": route,
                    "expected_status": status,
                    "response": response,
                    "state_unchanged": True,
                }
            )
        self.save(
            "ownership-forged-management",
            {
                "before": before,
                "after": after,
                "operations": outcomes,
                "persistent_snapshot_taken": "external_hub" not in self.config,
                "known_valid_and_four_changed_states_checked": True,
            },
        )

    async def web(self, role):
        from playwright.async_api import async_playwright, expect

        pub = subprocess.run(
            ["openssl", "x509", "-in", str(self.ca), "-pubkey", "-noout"],
            capture_output=True,
            check=True,
        ).stdout
        der = subprocess.run(
            ["openssl", "pkey", "-pubin", "-outform", "der"],
            input=pub,
            capture_output=True,
            check=True,
        ).stdout
        pin = base64.b64encode(hashlib.sha256(der).digest()).decode()
        self.save(
            "browser-tls",
            {
                "trust": "only the generated task certificate SPKI; no blanket ignore_https_errors",
                "spki_sha256_base64": pin,
                "certificate_sha256": sha(self.ca.read_bytes()),
                "implementation_reference": "https://chromium.googlesource.com/chromium/src/+/d66160822607fe290bed888dc511a8664f11d9e1/content/public/common/content_switches.cc",
            },
        )
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=["--ignore-certificate-errors-spki-list=" + pin],
                **(
                    {"executable_path": self.config["browser"]}
                    if self.config.get("browser")
                    else {}
                ),
            )
            context = await browser.new_context(
                viewport={"width": 1280, "height": 1000}
            )
            await context.tracing.start(screenshots=True, snapshots=True, sources=True)
            page = await context.new_page()
            page.on("dialog", lambda d: d.accept())
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            network = []
            resource_requests = []
            literal_states = []
            page.on("request", lambda request: resource_requests.append(request.url))
            known = {
                "window_marker_unset": True,
                "legacy_marker_unset": True,
                "embedded_nodes": 0,
                "trigger_requests": [],
            }
            self.literal_display_check(known)
            for field, wrong in [
                ("window_marker_unset", False),
                ("legacy_marker_unset", False),
                ("embedded_nodes", 1),
                ("trigger_requests", ["/smm-document-executed"]),
            ]:
                try:
                    self.literal_display_check({**known, field: wrong})
                except AssertionError:
                    pass
                else:
                    raise AssertionError("literal-display detector missed " + field)
            self.save(
                "literal-selfcheck-" + role,
                {"known_valid": True, "four_invalid_states_rejected": True},
            )
            literal = '<script>window.__smm_document_executed=true</script>\n<img src="/smm-document-executed" onerror="window.__smm_document_executed=true">\n<script>window.SMM_007_EXECUTED=true</script>'
            project_name = (
                ("Web Hub" if role == "hub" else "Web Local")
                + ' <img src="/smm-document-executed" onerror="window.__smm_document_executed=true">'
            )

            async def literal_state(stage):
                await page.wait_for_load_state("networkidle")
                value = await page.evaluate(
                    "({window_marker_unset:window.__smm_document_executed===undefined,legacy_marker_unset:window.SMM_007_EXECUTED===undefined,embedded_nodes:document.querySelectorAll('main img, main script').length})"
                )
                value["trigger_requests"] = [
                    url for url in resource_requests if "/smm-document-executed" in url
                ]
                self.literal_display_check(value)
                literal_states.append({"stage": stage, **value})

            def response_seen(response):
                if "/api/" in response.url or "/v1/" in response.url:
                    network.append(
                        {
                            "url": response.url,
                            "method": response.request.method,
                            "status": response.status,
                        }
                    )

            page.on("response", response_seen)
            try:
                await page.goto(self.address["hub" if role == "hub" else "a"])
                prefix = "hub" if role == "hub" else "doc"
                if role == "hub":
                    assert await page.locator("#workspace").is_hidden()
                    assert not any(
                        "/v1/" in item["url"] for item in network
                    ), "anonymous root fetched archive metadata"
                    await page.locator("#credential").set_input_files(
                        str(self.token_file)
                    )
                    await expect(page.locator("#workspace")).to_be_visible()
                    await page.locator("#hub-project-name").fill(project_name)
                    await page.locator("#hub-project-create").click()
                    await expect(page.locator("#notice")).to_contain_text(
                        "已创建Hub项目"
                    )
                    project_id = int(await page.locator("#hub-project").input_value())
                else:
                    await page.locator("button[data-tab=documents]").click()
                    await expect(page.locator("#doc-hub-project")).to_contain_text(
                        "Hub D"
                    )
                    await page.locator("#doc-project-name").fill(project_name)
                    await page.locator("#doc-project-create").click()
                    await expect(page.locator("#notice")).to_contain_text(
                        "已创建文档可用"
                    )
                    option = page.locator("#doc-library-project option").filter(
                        has_text="Web Local"
                    )
                    project_id = int(await option.get_attribute("value"))
                    await page.locator("#doc-library-project").select_option(
                        str(project_id)
                    )
                project_option = page.locator(
                    "#hub-project option"
                    if role == "hub"
                    else "#doc-library-project option"
                ).filter(has_text=project_name)
                await expect(project_option).to_have_count(1)
                await expect(project_option).to_have_text(
                    project_name
                    + f" · #{project_id}"
                    + (" · hub" if role == "hub" else "")
                )
                await literal_state("new-project")
                await self.mixed_batch(page, role, project_id)
                raws = {
                    "chosen.txt": "webneedle 选择😀 e\u0301\r\n独立甲".encode(),
                    "dropped.md": ("webneedle dropped\n" + literal).encode(),
                }
                inputs = self.fixtures / ("web-" + role)
                inputs.mkdir()
                chosen = inputs / "chosen.txt"
                chosen.write_bytes(raws["chosen.txt"])
                original = sha(chosen.read_bytes())
                async with page.expect_response(
                    lambda r: r.url.endswith("/documents/library")
                    and r.request.method == "POST"
                ) as response:
                    await page.locator("#" + prefix + "-upload-files").set_input_files(
                        str(chosen)
                    )
                receipt1 = await (await response.value).json()
                transfer = await page.evaluate_handle(
                    "text=>{const value=new DataTransfer();value.items.add(new File([text],'dropped.md',{type:'text/markdown'}));return value}",
                    raws["dropped.md"].decode(),
                )
                async with page.expect_response(
                    lambda r: r.url.endswith("/documents/library")
                    and r.request.method == "POST"
                ) as response:
                    await page.dispatch_event(
                        "#hub-drop" if role == "hub" else "#doc-upload-drop",
                        "drop",
                        {"dataTransfer": transfer},
                    )
                receipt2 = await (await response.value).json()
                assert receipt1["id"] != receipt2["id"]
                await expect(
                    page.locator("#" + prefix + "-library-list input[type=file]")
                ).to_have_count(2)
                if role != "hub":
                    await page.locator("#doc-archive-mode").select_option("local")
                    await page.locator("#doc-scope").select_option("project")
                    await page.locator("#doc-search-project").select_option(
                        str(project_id)
                    )

                async def search(query="webneedle"):
                    await page.locator("#" + prefix + "-query").fill(query)
                    async with page.expect_response(
                        lambda r: r.url.endswith("/documents/search")
                        and r.request.method == "POST"
                    ) as response:
                        await page.locator("#" + prefix + "-search-form").evaluate(
                            "(f)=>f.requestSubmit()"
                        )
                    value = await (await response.value).json()
                    await expect(
                        page.locator("#" + prefix + "-results .result")
                    ).to_have_count(len(value["results"]))
                    return value

                result = await search()
                assert {h["id"] for h in result["results"]} == {
                    receipt1["id"],
                    receipt2["id"],
                }
                oldrefs = {h["id"]: h["reference"] for h in result["results"]}
                await expect(page.locator("#" + prefix + "-results")).to_contain_text(
                    literal
                )
                await literal_state("query-snippets")
                expected_targets = {
                    "chosen.txt": receipt1["id"],
                    "dropped.md": receipt2["id"],
                }
                observed_targets = []
                self.read_target_check(
                    [
                        {"name": name, "id": identity}
                        for name, identity in expected_targets.items()
                    ],
                    expected_targets,
                )
                for wrong in [
                    [{"name": "chosen.txt", "id": receipt1["id"]}] * 2,
                    [
                        {"name": "chosen.txt", "id": receipt1["id"]},
                        {"name": "dropped.md", "id": receipt1["id"]},
                    ],
                ]:
                    try:
                        self.read_target_check(wrong, expected_targets)
                    except AssertionError:
                        pass
                    else:
                        raise AssertionError(
                            "duplicate/misdirected browser read accepted"
                        )
                for i in range(2):
                    row = page.locator("#" + prefix + "-results .result").nth(i)
                    name = await row.locator("h3").inner_text()
                    assert name in raws
                    async with page.expect_response(
                        lambda r: r.url.endswith("/documents/read")
                        and r.request.method == "POST"
                    ) as response:
                        await row.get_by_role(
                            "button", name="读取原文", exact=True
                        ).click()
                    actual = await (await response.value).json()
                    assert actual["id"] == expected_targets[name]
                    observed_targets.append({"name": name, "id": actual["id"]})
                    exact_read(actual, raws[name])
                    await expect(
                        page.locator(
                            "#hub-read-text" if role == "hub" else "#doc-reader-text"
                        )
                    ).to_have_text(normalized(raws[name]))
                    await literal_state("original-" + name)
                    if name == "dropped.md":
                        await page.screenshot(
                            path=str(
                                self.out / ("web-" + role + "-literal-original.png")
                            ),
                            full_page=True,
                        )
                self.read_target_check(observed_targets, expected_targets)
                assert {v["stage"] for v in literal_states} == {
                    "new-project",
                    "query-snippets",
                    "original-chosen.txt",
                    "original-dropped.md",
                }
                assert (self.out / ("web-" + role + "-literal-original.png")).is_file()
                assert await page.evaluate("window.SMM_007_EXECUTED===undefined")
                self.save(
                    "literal-display-" + role,
                    {
                        "project_name": project_name,
                        "observed_targets": observed_targets,
                        "expected_targets": expected_targets,
                        "two_target_negative_controls_rejected": True,
                        "exact_upload": raws["dropped.md"].decode(),
                        "stages": literal_states,
                        "all_resource_requests": resource_requests,
                    },
                )
                await page.screenshot(
                    path=str(self.out / ("web-" + role + "-search-read.png")),
                    full_page=True,
                )
                replacement = b"webneedle updated independent first\nsecond line"
                changed = inputs / "replacement.txt"
                changed.write_bytes(replacement)
                async with page.expect_response(
                    lambda r: "/documents/library/" + receipt1["id"] in r.url
                    and r.request.method == "PUT"
                ) as response:
                    await page.locator(
                        "#" + prefix + "-library-list input[type=file]"
                    ).first.set_input_files(str(changed))
                updated = await (await response.value).json()
                assert (
                    updated["id"] == receipt1["id"]
                    and updated["version"] == receipt1["version"] + 1
                )
                await expect(page.locator("#notice")).to_contain_text(
                    "已更新" if role == "hub" else "副本已更新"
                )
                result = await search()
                hit = next(h for h in result["results"] if h["id"] == receipt1["id"])
                value = self.request(
                    "hub" if role == "hub" else "a",
                    "/v1/documents/read" if role == "hub" else "/api/documents/read",
                    {
                        **(self.hub_context if role == "hub" else {}),
                        "reference": hit["reference"],
                    },
                )
                exact_read(value, replacement)
                self.request(
                    "hub" if role == "hub" else "a",
                    "/v1/documents/read" if role == "hub" else "/api/documents/read",
                    {
                        **(self.hub_context if role == "hub" else {}),
                        "reference": oldrefs[receipt1["id"]],
                    },
                    code=400,
                )
                async with page.expect_response(
                    lambda r: "/documents/library/" + receipt1["id"] in r.url
                    and r.request.method == "DELETE"
                ) as response:
                    await page.locator("#" + prefix + "-library-list").get_by_role(
                        "button", name="移除文档"
                    ).first.click()
                assert (await response.value).status == 200
                await expect(
                    page.locator("#" + prefix + "-library-list input[type=file]")
                ).to_have_count(1)
                result = await search()
                assert {h["id"] for h in result["results"]} == {receipt2["id"]}
                assert sha(chosen.read_bytes()) == original
                if role != "hub":
                    status = self.cli("a", "documents", "sync-status")
                    p = next(
                        p for p in status["projects"] if p["project_id"] == project_id
                    )
                    assert not p["enabled"]
                    assert self.cli(
                        "hub", "documents", "search", "webneedle", "--limit", "50"
                    )[
                        "results"
                    ]  # only Hub's own Web document
                    self.policy("a", {"id": project_id})
                    self.cli("a", "documents", "sync")
                    projected = next(
                        p
                        for p in self.cli("hub", "project", "list")
                        if p["source"] == "device"
                        and p["owner"] == self.origins["a"]["device_id"]
                        and p["source_key"]
                        == next(
                            p
                            for p in self.cli("a", "projects")
                            if p["id"] == project_id
                        )["stable_key"]
                    )
                    found = self.cli(
                        "hub",
                        "documents",
                        "search",
                        "webneedle",
                        "--scope",
                        "project",
                        "--project-id",
                        projected["id"],
                        "--limit",
                        "50",
                    )
                    assert {h["origin"]["document_id"] for h in found["results"]} == {
                        receipt2["id"]
                    }
                    exact_read(
                        self.cli(
                            "hub",
                            "documents",
                            "read",
                            "--reference",
                            found["results"][0]["reference"],
                        ),
                        raws["dropped.md"],
                    )
                    await page.locator("#doc-archive-mode").select_option("combined")
                    await page.locator("#doc-scope").select_option("all")
                    await page.locator("#doc-limit").select_option("50")
                    mixed = await search("e1needle")
                    expected = (
                        self.a_entries
                        + self.b_entries
                        + self.private_entries
                        + self.global_entries
                        + self.unbound_entries
                        + self.d_entries
                        + self.e_entries
                    )
                    document_set(mixed["results"], expected)
                    reads = []
                    for i, hit in enumerate(mixed["results"]):
                        async with page.expect_response(
                            lambda r: r.url.endswith("/documents/read")
                            and r.request.method == "POST"
                        ) as response:
                            await page.locator("#doc-results .result").nth(
                                i
                            ).get_by_role("button", name="读取原文", exact=True).click()
                        value = await (await response.value).json()
                        raw = next(
                            e["raw"] for e in expected if e["origin"] == hit["origin"]
                        )
                        exact_read(value, raw)
                        await expect(page.locator("#doc-reader-text")).to_have_text(
                            normalized(raw)
                        )
                        reads.append(value)
                    await page.screenshot(
                        path=str(self.out / "web-local-joint-read.png"), full_page=True
                    )
                    await page.locator("#doc-scope").select_option("project")
                    await page.locator("#doc-root-kind").select_option("hub")
                    await page.locator("#doc-hub-project").select_option(
                        str(self.d["id"])
                    )
                    hub_root = await search("e1needle")
                    document_set(hub_root["results"], self.d_entries + self.e_entries)
                    await page.locator("#doc-root-kind").select_option("local")
                    await page.locator("#doc-search-project").select_option(
                        str(self.c["id"])
                    )
                    local_root = await search("e1needle")
                    document_set(local_root["results"], self.d_entries)
                    await page.screenshot(
                        path=str(self.out / "web-local-project-one-hop.png"),
                        full_page=True,
                    )
                    self.save(
                        "web-joint",
                        {
                            "all": mixed,
                            "exact_reads": reads,
                            "hub_root": hub_root,
                            "conversation_root": local_root,
                        },
                    )
                    hub_web = json.loads(
                        (self.out / "web-hub.json").read_text(encoding="utf-8")
                    )
                    native = self.request(
                        "hub",
                        "/v1/documents/library?project_id="
                        + str(hub_web["project_id"]),
                    )[0]
                    self.forged_ownership(projected, found["results"][0], native)
                    await page.goto(self.address["hub"])
                    await page.locator("#credential").set_input_files(
                        str(self.token_file)
                    )
                    await expect(page.locator("#workspace")).to_be_visible()
                    await page.locator("#hub-project").select_option(
                        str(projected["id"])
                    )
                    await expect(page.locator("#hub-write-controls")).to_be_hidden()
                    await page.screenshot(
                        path=str(self.out / "web-hub-device-readonly.png"),
                        full_page=True,
                    )
                else:
                    await page.locator("#hub-scope").select_option("all")
                    await page.locator("#hub-limit").select_option("50")
                    mixed = await search("e1needle")
                    document_set(
                        mixed["results"],
                        self.a_entries
                        + self.b_entries
                        + self.d_entries
                        + self.e_entries,
                    )
                    self.save("web-hub-all", mixed)
                    # A reload must erase credentials and must not fetch metadata.
                    network.clear()
                    await page.reload()
                    assert await page.locator("#workspace").is_hidden()
                    assert not any("/v1/" in item["url"] for item in network)
                assert not errors, errors
                self.save(
                    "web-" + role,
                    {
                        "project_id": project_id,
                        "created": [receipt1, receipt2],
                        "updated": updated,
                        "remaining": [receipt2["id"]],
                        "source_sha256_unchanged": original,
                        "literal_script_not_executed": True,
                        "page_errors": errors,
                        "network": network,
                    },
                )
            finally:
                await context.tracing.stop(
                    path=str(self.out / ("web-" + role + "-trace.zip"))
                )
                await context.close()
                await browser.close()

    def prepare(self):
        self.check_install()
        self.start("hub")
        info = self.request("hub", "/v1/info")
        self.hub_context = {k: info[k] for k in ("hub_id", "document_epoch")}
        identity = json.loads(
            self.run(
                "hub-archive",
                [
                    self.config["hub_python"],
                    "-I",
                    "-c",
                    "import json,sys;from smm_hub._archive import Archive,reference_material;print(json.dumps({'archive_id':reference_material(Archive(sys.argv[1]))[0]}))",
                    self.hub_db,
                ],
                role="hub",
            )
        )
        self.hub_origin = {
            "device_id": info["hub_id"],
            "archive_id": identity["archive_id"],
        }
        self.origins = {}
        for role in ("a", "b"):
            self.start(role)
            result = self.cli(
                role,
                "configure-hub",
                self.address["hub"],
                "E1 " + role,
                "--token-file",
                self.token_file,
            )
            assert result["connected"]
            self.wait_idle(role)
            self.request(
                role, "/api/settings", {"sync_interval_seconds": 3600}, method="PUT"
            )
            self.stop(role)
            self.start(role)
            self.origins[role] = self.identity(role)
        self.a = self.cli("a", "project", "create", "A")
        self.private = self.cli("a", "project", "create", "Private")
        self.globalp = self.cli("a", "project", "ensure-global")
        self.b = self.cli("b", "project", "create", "B")
        self.d = self.cli("hub", "project", "create", "Hub D")
        self.e = self.cli("hub", "project", "create", "Hub E")
        self.sa, self.a_entries, self.a_root = self.source(
            "a",
            "allowed",
            {
                "one.txt": "\ufeffe1needle A one😀\r\nline2".encode(),
                "two.md": b"e1needle A two\nindependent",
            },
            self.a,
        )
        overlap = self.cli(
            "a",
            "documents",
            "add",
            self.a_root / "one.txt",
            "--project-id",
            self.a["id"],
        )
        self.phase = "explicit-refresh"
        self.cli("a", "documents", "refresh", "--source-id", overlap["id"])
        self.phase = "archive-only"
        self.overlap = overlap
        self.sb, self.b_entries, self.b_root = self.source(
            "b",
            "allowed",
            {"one.txt": b"e1needle B one", "two.txt": b"e1needle B two"},
            self.b,
        )
        _, self.private_entries, _ = self.source(
            "a",
            "private",
            {"private.txt": b"e1needle private never uploaded"},
            self.private,
        )
        _, self.global_entries, _ = self.source(
            "a", "global", {"global.txt": b"e1needle global independent"}, self.globalp
        )
        _, self.unbound_entries, _ = self.source(
            "a", "unbound", {"unbound.txt": b"e1needle unbound local only"}
        )
        self.sd, self.d_entries, self.d_root = self.source(
            "hub",
            "native",
            {
                "one.txt": b"e1needle D native one",
                "two.md": "e1needle D native two😀\nend".encode(),
            },
            self.d,
        )
        self.se, self.e_entries, _ = self.source(
            "hub", "second-layer", {"negative.txt": b"e1needle E second layer"}, self.e
        )
        for role in ("a", "b"):
            assert all(
                not p["enabled"]
                for p in self.cli(role, "documents", "sync-status")["projects"]
            )
        self.policy("a", self.a)
        self.policy("b", self.b)
        for role in ("a", "b"):
            self.cli(role, "documents", "sync")
        self.ha = next(
            p
            for p in self.cli("hub", "project", "list")
            if p["source"] == "device"
            and p["owner"] == self.origins["a"]["device_id"]
            and p["source_key"] == self.a["stable_key"]
        )
        self.hb = next(
            p
            for p in self.cli("hub", "project", "list")
            if p["source"] == "device"
            and p["owner"] == self.origins["b"]["device_id"]
            and p["source_key"] == self.b["stable_key"]
        )
        self.cli("hub", "project", "link", self.ha["id"], self.hb["id"])
        self.request(
            "a",
            "/api/projects/link",
            {"one": self.a["id"], "other": self.private["id"]},
        )
        self.verify(
            "a",
            self.cli(
                "a",
                "documents",
                "search",
                "e1needle",
                "--scope",
                "project",
                "--project-id",
                self.a["id"],
                "--limit",
                "50",
            ),
            self.a_entries + self.b_entries,
        )
        self.verify(
            "a",
            self.cli(
                "a",
                "documents",
                "search",
                "e1needle",
                "--scope",
                "project",
                "--project-id",
                self.a["id"],
                "--local",
                "--limit",
                "50",
            ),
            self.a_entries + self.private_entries,
        )
        self.verify(
            "a",
            self.cli("a", "documents", "search", "e1needle", "--limit", "50"),
            self.a_entries
            + self.b_entries
            + self.private_entries
            + self.global_entries
            + self.unbound_entries
            + self.d_entries
            + self.e_entries,
        )

    def shared_conversation_range(self):
        root = self.fixtures / "conversation"
        root.mkdir()
        cwd = root / "Conversation C"
        cwd.mkdir()
        session = "e1-conversation-independent"
        events = [
            {"type": "session_meta", "payload": {"id": session, "cwd": str(cwd)}},
            {
                "type": "response_item",
                "ordinal": 1,
                "payload": {
                    "type": "message",
                    "id": "first-message",
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "e1chatneedle original discussion",
                        }
                    ],
                },
            },
        ]
        (root / "session.jsonl").write_text(
            "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in events),
            encoding="utf-8",
        )
        self.phase = "conversation-import"
        self.cli("a", "sync", "--source", "codex", "--root", root)
        self.phase = "archive-only"
        found = self.cli("a", "search", "e1chatneedle", "--local", "--include-current")[
            "results"
        ]
        assert len(found) == 1
        self.c = next(
            p for p in self.cli("a", "projects") if p["id"] == found[0]["project_id"]
        )
        self.cli("a", "upload", "set", "--mode", "only", "--project-id", self.c["id"])
        self.phase = "conversation-import"
        self.request("a", "/api/sync?wait=true", {})
        self.wait_idle("a")
        self.phase = "archive-only"
        hc = next(
            p
            for p in self.cli("hub", "project", "list")
            if p["source"] == "device"
            and p["owner"] == self.origins["a"]["device_id"]
            and p["source_key"] == self.c["stable_key"]
        )
        self.cli("hub", "project", "link", hc["id"], self.d["id"])
        self.cli("hub", "project", "link", self.d["id"], self.e["id"])
        self.verify(
            "a",
            self.cli(
                "a",
                "documents",
                "search",
                "e1needle",
                "--scope",
                "project",
                "--project-id",
                self.c["id"],
                "--limit",
                "50",
            ),
            self.d_entries,
        )
        chat = self.cli(
            "a",
            "search",
            "e1chatneedle",
            "--scope",
            "project",
            "--hub-project-id",
            self.d["id"],
            "--include-current",
        )
        assert (
            len(chat["results"]) == 1
            and chat["results"][0]["source_session_id"] == session
        )
        read = self.cli("a", "read", "--reference", chat["results"][0]["reference"])
        assert [m["text"] for m in read["messages"]] == [
            "e1chatneedle original discussion"
        ]
        self.save(
            "conversation-document-range",
            {
                "local_conversation_project": self.c,
                "hub_conversation_project": hc,
                "hub_document_project": self.d,
                "excluded_second_layer": self.e,
                "exact_chat": read,
            },
        )

    async def stdio_checks(self):
        values = await self.mcp(
            "a",
            [
                ("list_document_sources", {}),
                ("list_document_sources", {"include_hub": True}),
                ("list_projects", {"include_hub": True}),
                (
                    "search_documents",
                    {
                        "query": "e1needle",
                        "scope": "project",
                        "project_id": self.a["id"],
                        "limit": 50,
                    },
                ),
            ],
        )
        assert (
            values[1]["coverage"]
            == values[2]["coverage"]
            == {"local": "complete", "hub": "complete"}
        )
        assert values[1]["local"] == values[0]
        assert {s["origin"]["source_id"] for s in values[1]["hub"]} == {
            self.sa["id"],
            self.overlap["id"],
            self.sb["id"],
            self.sd["id"],
            self.se["id"],
        }
        assert {p["id"] for p in values[2]["local"]} == {
            self.a["id"],
            self.private["id"],
            self.globalp["id"],
            self.c["id"],
        }
        expected_projects = {
            ("device", self.origins[role]["device_id"], project["stable_key"])
            for role, project in [
                ("a", self.a),
                ("a", self.private),
                ("a", self.globalp),
                ("a", self.c),
                ("b", self.b),
            ]
        } | {
            ("hub", self.hub_context["hub_id"], p["source_key"])
            for p in [self.d, self.e]
        }
        assert {
            (p["source"], p["owner"], p["source_key"]) for p in values[2]["hub"]
        } == expected_projects
        result = values[-1]
        document_set(result["results"], self.a_entries + self.b_entries)
        reads = await self.mcp(
            "a",
            [
                ("read_document", {"reference": h["reference"]})
                for h in result["results"]
            ],
        )
        for hit, value in zip(result["results"], reads):
            expected = next(
                e
                for e in self.a_entries + self.b_entries
                if e["origin"] == hit["origin"]
            )
            exact_read(value, expected["raw"])
        all_documents = await self.mcp(
            "a", [("search_documents", {"query": "e1needle", "limit": 50})]
        )
        expected = (
            self.a_entries
            + self.b_entries
            + self.private_entries
            + self.global_entries
            + self.unbound_entries
            + self.d_entries
            + self.e_entries
        )
        document_set(all_documents[0]["results"], expected)
        complete_reads = await self.mcp("a", [
            ("read_document", {"reference": h["reference"]})
            for h in all_documents[0]["results"]])
        assert len(complete_reads) == len(expected)
        stable = self.private_entries + self.global_entries + self.unbound_entries + self.d_entries + self.e_entries
        for hit, actual in zip(all_documents[0]["results"], complete_reads):
            entry = next(e for e in expected if e["origin"] == hit["origin"])
            assert actual["origin"] == hit["origin"] and actual["version"] == hit["version"]
            exact_read(actual, entry["raw"])
            if any(e["origin"] == hit["origin"] for e in stable):
                self.stable_mcp.append({"hit": hit, "raw": entry["raw"]})
        assert len(self.stable_mcp) == len(stable)
        values = await self.mcp(
            "a",
            [
                (
                    "search_conversations",
                    {
                        "query": "e1chatneedle",
                        "scope": "project",
                        "hub_project_id": self.d["id"],
                        "include_current": True,
                    },
                )
            ],
        )
        assert len(values[0]["results"]) == 1
        reads = await self.mcp(
            "a",
            [
                (
                    "read_conversation",
                    {"reference": values[0]["results"][0]["reference"]},
                )
            ],
        )
        assert [m["text"] for m in reads[0]["messages"]] == [
            "e1chatneedle original discussion"
        ]

    async def restart_protocol_checks(self):
        from playwright.async_api import async_playwright, expect

        expected = self.private_entries + self.global_entries + self.unbound_entries + self.d_entries + self.e_entries
        values = await self.mcp("a", [
            ("search_documents", {"query": "e1needle", "limit": 50}),
            *[("read_document", {"reference": e["hit"]["reference"]}) for e in self.stable_mcp]])
        document_set(values[0]["results"], expected)
        assert len(values) == len(self.stable_mcp) + 1
        for before, actual in zip(self.stable_mcp, values[1:]):
            assert actual["origin"] == before["hit"]["origin"] and actual["version"] == before["hit"]["version"]
            exact_read(actual, before["raw"])
        self.save("restart-stdio", {"fresh_search": values[0], "old_reference_reads": values[1:],
            "old_references": [e["hit"]["reference"] for e in self.stable_mcp], "all_stable_originals_exact": True})
        pin = json.loads((self.out / "browser-tls.json").read_text(encoding="utf-8"))["spki_sha256_base64"]
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True,
                args=["--ignore-certificate-errors-spki-list=" + pin],
                **({"executable_path": self.config["browser"]} if self.config.get("browser") else {}))
            context = await browser.new_context(viewport={"width":1280,"height":1000})
            await context.tracing.start(screenshots=True,snapshots=True,sources=True)
            network = []; errors = []; observations = []
            try:
                for role in ["a", "hub"]:
                    page = await context.new_page()
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.on("request", lambda request: network.append({"url":request.url,"method":request.method}))
                    await page.goto(self.address[role])
                    prefix = "doc" if role == "a" else "hub"
                    entries = expected if role == "a" else self.d_entries + self.e_entries
                    if role == "hub":
                        await page.locator("#credential").set_input_files(str(self.token_file))
                        await expect(page.locator("#workspace")).to_be_visible()
                    else:
                        await page.locator("button[data-tab=documents]").click()
                        await page.locator("#doc-archive-mode").select_option("combined")
                    await page.locator("#"+prefix+"-scope").select_option("all")
                    await page.locator("#"+prefix+"-limit").select_option("50")
                    await page.locator("#"+prefix+"-query").fill("e1needle")
                    async with page.expect_response(lambda r:r.url.endswith("/documents/search") and r.request.method=="POST") as response:
                        await page.locator("#"+prefix+"-search-form").evaluate("f=>f.requestSubmit()")
                    result = await (await response.value).json()
                    document_set(result["results"], entries)
                    await expect(page.locator("#"+prefix+"-results .result")).to_have_count(len(entries))
                    reads = []
                    for i,hit in enumerate(result["results"]):
                        entry = next(e for e in entries if e["origin"]==hit["origin"])
                        async with page.expect_response(lambda r:r.url.endswith("/documents/read") and r.request.method=="POST") as response:
                            await page.locator("#"+prefix+"-results .result").nth(i).get_by_role("button",name="读取原文",exact=True).click()
                        actual = await (await response.value).json()
                        assert actual["origin"]==hit["origin"] and actual["version"]==hit["version"]
                        exact_read(actual, entry["raw"])
                        await expect(page.locator("#doc-reader-text" if role=="a" else "#hub-read-text")).to_have_text(normalized(entry["raw"]))
                        reads.append(actual)
                    await page.screenshot(path=str(self.out/("restart-web-"+role+".png")),full_page=True)
                    observations.append({"role":role,"search":result,"exact_reads":reads})
                    await page.close()
                assert not errors, errors
                self.save("restart-web", {"observations":observations,"requests":network,"page_errors":errors})
            finally:
                await context.tracing.stop(path=str(self.out/"restart-web-trace.zip"))
                await context.close(); await browser.close()

    async def lifecycle(self):
        from copy import deepcopy

        baseline = self.verify(
            "hub",
            self.cli(
                "hub",
                "documents",
                "search",
                "e1needle",
                "--scope",
                "project",
                "--project-id",
                self.ha["id"],
                "--limit",
                "50",
            ),
            self.a_entries + self.b_entries,
        )
        invalid = self.b_root / "invalid-UTF8.txt"
        invalid.write_bytes(b"e1needle invalid \xff")
        self.phase = "explicit-refresh"
        self.cli("b", "documents", "refresh", "--source-id", self.sb["id"])
        self.phase = "archive-only"
        source = next(
            s for s in self.cli("b", "documents", "sources") if s["id"] == self.sb["id"]
        )
        assert source["status"] == "partial", source
        files = self.cli("b", "documents", "files", "--source-id", self.sb["id"])
        assert (
            next(f for f in files if Path(f["path"]).name == invalid.name)["status"]
            == "failed"
        )
        self.cli("b", "documents", "sync")
        self.save("actual-invalid-utf8", {"source": source, "files": files})
        self.verify(
            "hub",
            self.cli(
                "hub",
                "documents",
                "search",
                "e1needle",
                "--scope",
                "project",
                "--project-id",
                self.ha["id"],
                "--limit",
                "50",
            ),
            self.a_entries + self.b_entries,
        )
        old = {h["origin"]["document_id"]: h for h in baseline["results"]}
        self.policy("a", self.a, False)
        original = {e["origin"]["document_id"]: deepcopy(e) for e in self.a_entries}
        self.phase = "fixture-edit"
        (self.a_root / "one.txt").write_bytes("e1needle A one version2😀\nnew".encode())
        (self.a_root / "two.md").write_bytes(b"e1needle A two version2")
        (self.a_root / "new.txt").write_bytes(
            b"e1needle A new must not upload during pause"
        )
        self.phase = "explicit-refresh"
        self.cli("a", "documents", "refresh", "--source-id", self.sa["id"])
        self.phase = "archive-only"
        self.cli("a", "documents", "sync")
        self.verify(
            "hub",
            self.cli(
                "hub",
                "documents",
                "search",
                "e1needle",
                "--scope",
                "project",
                "--project-id",
                self.ha["id"],
                "--limit",
                "50",
            ),
            list(original.values()) + self.b_entries,
        )
        # Real Unix permission failure; actual junction on Windows is checked below.
        victim = self.a_root / "two.md"
        victim_id = next(
            f["id"]
            for f in self.cli("a", "documents", "files", "--source-id", self.sa["id"])
            if Path(f["path"]).name == "two.md"
        )
        if os.name != "nt":
            victim.chmod(0)
            self.phase = "explicit-refresh"
            self.cli("a", "documents", "refresh", "--source-id", self.sa["id"])
            self.phase = "archive-only"
            self.cli("a", "documents", "sync")
            self.cli(
                "hub",
                "documents",
                "read",
                "--reference",
                old[victim_id]["reference"],
                code=2,
            )
            victim.chmod(0o600)
            self.phase = "explicit-refresh"
            self.cli("a", "documents", "refresh", "--source-id", self.sa["id"])
            self.phase = "archive-only"
            self.cli("a", "documents", "sync")
            self.cli(
                "hub",
                "documents",
                "read",
                "--reference",
                old[victim_id]["reference"],
                code=2,
            )
        else:
            victim.unlink()
            self.phase = "explicit-refresh"
            self.cli("a", "documents", "refresh", "--source-id", self.sa["id"])
            self.phase = "archive-only"
            self.cli("a", "documents", "sync")
            self.cli(
                "hub",
                "documents",
                "read",
                "--reference",
                old[victim_id]["reference"],
                code=2,
            )
            victim.write_bytes(b"e1needle A two version2")
            self.phase = "explicit-refresh"
            self.cli("a", "documents", "refresh", "--source-id", self.sa["id"])
            self.phase = "archive-only"
        self.policy("a", self.a)
        self.cli("a", "documents", "sync")
        current = []
        for f in self.cli("a", "documents", "files", "--source-id", self.sa["id"]):
            path = Path(f["path"])
            current.append(
                {
                    "origin": {**self.origins["a"], "document_id": f["id"]},
                    "version": f["version"],
                    "raw": path.read_bytes(),
                }
            )
        assert len(current) == 3
        self.verify(
            "hub",
            self.cli(
                "hub",
                "documents",
                "search",
                "e1needle",
                "--scope",
                "project",
                "--project-id",
                self.ha["id"],
                "--limit",
                "50",
            ),
            current + self.b_entries,
        )
        for hit in old.values():
            if hit["origin"]["device_id"] == self.origins["a"]["device_id"]:
                self.cli(
                    "hub", "documents", "read", "--reference", hit["reference"], code=2
                )
        latest = self.cli(
            "hub",
            "documents",
            "search",
            "e1needle",
            "--scope",
            "project",
            "--project-id",
            self.ha["id"],
            "--limit",
            "50",
        )["results"]
        one_id = next(
            f["id"]
            for f in self.cli("a", "documents", "files", "--source-id", self.sa["id"])
            if Path(f["path"]).name == "one.txt"
        )
        continuous = next(h for h in latest if h["origin"]["document_id"] == one_id)
        self.policy("a", self.a, False)
        self.cli("a", "documents", "remove", self.sa["id"])
        self.cli("a", "documents", "sync")
        expected = next(e for e in current if e["origin"]["document_id"] == one_id)
        exact_read(
            self.cli(
                "hub", "documents", "read", "--reference", continuous["reference"]
            ),
            expected["raw"],
        )
        self.cli("a", "documents", "remove", self.overlap["id"])
        self.cli("a", "documents", "sync")
        self.cli(
            "hub", "documents", "read", "--reference", continuous["reference"], code=2
        )
        self.verify(
            "hub",
            self.cli(
                "hub",
                "documents",
                "search",
                "e1needle",
                "--scope",
                "project",
                "--project-id",
                self.ha["id"],
                "--limit",
                "50",
            ),
            self.b_entries,
        )
        link = self.fixtures / "actual-link"
        if os.name == "nt":
            self.run(
                "actual-junction", ["cmd", "/c", "mklink", "/J", link, self.b_root]
            )
        else:
            link.symlink_to(self.b_root, target_is_directory=True)
        self.cli("a", "documents", "add", link, code=2)
        if os.name == "nt":
            os.rmdir(link)
        else:
            link.unlink()
        # Native source files become unreachable without an explicit refresh;
        # the new Hub process must still read the captured same qualifications.
        native = self.cli(
            "hub",
            "documents",
            "search",
            "e1needle",
            "--scope",
            "project",
            "--project-id",
            self.d["id"],
            "--limit",
            "50",
        )["results"]
        self.d_root.rename(self.d_root.with_name(self.d_root.name + " moved"))
        self.stop("hub")
        self.cli("b", "documents", "remove", self.sb["id"])
        pending = self.cli("b", "documents", "sync")
        assert pending["pending"] and pending["errors"]
        self.stop("b")
        self.start("b")
        assert self.cli("b", "documents", "sync-status")["pending"]
        fallback = self.cli(
            "a",
            "documents",
            "search",
            "e1needle",
            "--scope",
            "project",
            "--hub-project-id",
            self.d["id"],
        )
        assert fallback["results"] == [] and fallback["fallback_reason"]
        self.start("hub")
        assert (
            self.request("hub", "/v1/info")["document_epoch"]
            == self.hub_context["document_epoch"]
        )
        self.cli("b", "documents", "sync")
        assert (
            self.cli(
                "hub",
                "documents",
                "search",
                "e1needle",
                "--scope",
                "project",
                "--project-id",
                self.hb["id"],
            )["results"]
            == []
        )
        for hit in native:
            expected = next(
                e
                for e in self.d_entries + self.e_entries
                if e["origin"] == hit["origin"]
            )
            exact_read(
                self.cli("hub", "documents", "read", "--reference", hit["reference"]),
                expected["raw"],
            )
        self.stop("a")
        self.start("a")
        self.verify(
            "a",
            self.cli(
                "a",
                "documents",
                "search",
                "e1needle",
                "--scope",
                "project",
                "--project-id",
                self.c["id"],
                "--limit",
                "50",
            ),
            self.d_entries,
        )
        await self.restart_protocol_checks()
        self.cli("hub", "documents", "remove", self.sd["id"])
        for hit in native:
            if any(e["origin"] == hit["origin"] for e in self.d_entries):
                self.cli(
                    "hub", "documents", "read", "--reference", hit["reference"], code=2
                )
            else:
                exact_read(
                    self.cli(
                        "hub", "documents", "read", "--reference", hit["reference"]
                    ),
                    next(
                        e["raw"] for e in self.e_entries if e["origin"] == hit["origin"]
                    ),
                )
        assert (
            self.cli(
                "a",
                "documents",
                "search",
                "e1needle",
                "--scope",
                "project",
                "--project-id",
                self.c["id"],
                "--limit",
                "50",
            )["results"]
            == []
        )
        self.save(
            "lifecycle",
            {
                "old_versions": list(original.values()),
                "updated": current,
                "remaining_overlap_read_succeeded": True,
                "last_qualification_rejected": True,
                "offline_withdrawal": pending,
                "native_cached_after_process_restart": True,
            },
        )

    async def execute(self):
        self.prepare()
        original_sources = {
            str(path): {
                "sha256": sha(path.read_bytes()),
                "mtime_ns": path.stat().st_mtime_ns,
            }
            for path in self.fixtures.rglob("*")
            if path.is_file()
        }
        self.shared_conversation_range()
        await self.stdio_checks()
        await self.web("hub")
        await self.web("a")
        after = {
            name: {
                "sha256": sha(Path(name).read_bytes()),
                "mtime_ns": Path(name).stat().st_mtime_ns,
            }
            for name in original_sources
        }
        assert (
            after == original_sources
        ), "query/Web/MCP changed an explicitly collected source"
        self.save(
            "unchanged-source-fingerprints",
            {"before": original_sources, "after": after},
        )
        await self.lifecycle()
        entries = (
            [json.loads(line) for line in self.audit.read_text().splitlines()]
            if self.audit.exists()
            else []
        )
        assert all(
            e["phase"] in {"explicit-refresh", "conversation-import"} for e in entries
        ), entries
        identities = [
            json.loads(line) for line in self.identities.read_text().splitlines()
        ]
        assert identities
        for actor in identities:
            self.verify_actor(actor)
        self.save(
            "source-open-audit", {"entries": entries, "only_explicit_collection": True}
        )
        return {
            "status": "passed",
            "kind": "E1 actual installed ordinary-user foreground Hub",
            "platform": sys.platform,
            "started_at": self.started,
            "finished_at": now(),
            "all_source_open_audited": True,
        }

    def verify_actor(self, actor):
        if os.name == "nt":
            assert actor["is_admin"] is False
        else:
            assert actor["uid"] == os.getuid()

    def cleanup(self):
        records = []
        for role in list(self.processes):
            records.append(self.stop(role))
        for log in self.logs:
            log.close()
        self.save(
            "cleanup", {"owned_services": self.stops, "all_current_ports_closed": True}
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.target_config.read_text(encoding="utf-8-sig"))
    assert sys.platform == config["expected_platform"]
    probe = Probe(config, args.output.resolve())
    result = None
    try:
        result = asyncio.run(probe.execute())
    except BaseException:
        probe.save(
            "failure",
            {
                "traceback": traceback.format_exc(),
                "phase": probe.phase,
                "finished_at": now(),
            },
        )
        raise
    finally:
        probe.cleanup()
    probe.save("result", result)
    print(
        json.dumps(
            {
                "status": result["status"],
                "platform": sys.platform,
                "output": str(probe.out),
            }
        )
    )


if __name__ == "__main__":
    main()
