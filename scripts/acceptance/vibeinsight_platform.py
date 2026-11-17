# SPDX-License-Identifier: Apache-2.0
"""Opt-in installed-package acceptance, using a generated disposable source only."""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import sqlite3
import ssl
import subprocess
import sys
import time
from urllib.request import Request, HTTPSHandler, ProxyHandler, build_opener

from vibeinsight_fixture import Fixture


def now():
    return datetime.now(timezone.utc).isoformat()


def eventually(check, seconds=45):
    deadline=time.monotonic()+seconds
    last=None
    while time.monotonic()<deadline:
        try:
            value=check()
            if value: return value
        except (OSError, ValueError, sqlite3.Error) as error:
            last=type(error).__name__
        time.sleep(.25)
    raise AssertionError(f"condition timed out ({last})")


class Run:
    def __init__(self, args):
        self.args=args
        self.target=json.loads(args.target_config.read_text(encoding="utf-8-sig"))
        self.root=Path(self.target["work"]).resolve()
        self.state=self.root/self.target.get("state_name", "standalone" if args.mode=="self-managed" else "state")
        self.output=args.output.resolve()
        if self.output.exists(): raise ValueError("output must be a new run directory")
        self.output.mkdir(parents=True)
        snapshots=self.output/"probe-source";snapshots.mkdir()
        self.probe_files_sha256={}
        for source in Path(__file__).parent.glob("vibeinsight_*.py"):
            content=source.read_bytes();(snapshots/source.name).write_bytes(content)
            self.probe_files_sha256[source.name]=hashlib.sha256(content).hexdigest()
        self.fixture=Fixture(args.fixture_manifest,self.target["psql"])
        self.cfg=self.fixture.config
        self.env={k:v for k,v in os.environ.items() if not k.startswith("PG") and k not in {"PYTHONPATH","VIRTUAL_ENV"}}
        self.env["PYTHONIOENCODING"]="utf-8"
        self.observed={}; self.commands=[]; self.started=now(); self.process=None
        self.password=self.root/"input-password"
        self.root.mkdir(parents=True,exist_ok=True)
        self.secrets=[self.cfg[k] for k in ("password","admin_password","replacement_password")]
        for key in ("hub_token_file",):
            if self.target.get(key):self.secrets.append(Path(self.target[key]).read_text().strip())
        self.service=None
        self.process_events=[]

    def installed_identity(self):
        candidate=self.target["candidate"]
        names=candidate["installed_hub"]
        code="import importlib.util,hashlib,json,pathlib,sys; root=pathlib.Path(importlib.util.find_spec('smm_hub').origin).parent.parent; print(json.dumps({n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in json.loads(sys.argv[1])}))"
        observed=json.loads(self.command([self.target["hub_python"],"-c",code,json.dumps(list(names))]).stdout)
        assert observed==names,"installed Hub differs from candidate wheel"
        self.save("installed-identity",{"candidate":candidate,"actual_installed_hub":observed,
                                       "psql_version":self.command([self.target["psql"],"--version"]).stdout})

    def redact(self, value):
        def current_ids(value):
            if isinstance(value,dict):
                return {k:("<current-session>" if k=="excluded_current_session_id" and v else current_ids(v)) for k,v in value.items()}
            if isinstance(value,list):return [current_ids(v) for v in value]
            return value
        encoded=json.dumps(current_ids(value),ensure_ascii=False,default=str)
        for secret in self.secrets: encoded=encoded.replace(secret,"<secret>")
        # Keep synthetic message bodies/IDs, remove machine-specific locations and source endpoint.
        for original,replacement in sorted([(str(self.root),"<task>"),(str(Path.home()),"<home>"),(self.target["address"],"<hub-address>"),(self.cfg["host"],"<fixture-host>"),
                (str(self.args.fixture_manifest),"<private-fixture>"),
                (str(self.args.target_config),"<private-target>")],key=lambda p:len(p[0]),reverse=True):
            encoded=encoded.replace(json.dumps(original)[1:-1],json.dumps(replacement)[1:-1])
        return json.loads(encoded)

    def save(self, name, value):
        path=self.output/(name+".json")
        path.write_text(json.dumps(self.redact(value),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        self.observed[name]=str(path.relative_to(self.output))

    def command(self, argv, *, expected=0, timeout=60, env=None):
        started=now()
        p=subprocess.run(list(map(str,argv)),env=env or self.env,capture_output=True,
                         text=True,encoding="utf-8",errors="replace",timeout=timeout)
        item=self.redact({"argv":argv,"started_at":started,"ended_at":now(),"exit_code":p.returncode,
                          "expected":expected,"stdout":p.stdout,"stderr":p.stderr})
        self.commands.append(item)
        (self.output/"commands.jsonl").write_text("".join(json.dumps(c,ensure_ascii=False)+"\n" for c in self.commands),encoding="utf-8")
        for secret in self.secrets:
            assert secret not in p.stdout+p.stderr,"secret leaked in product output"
        if expected is not None: assert p.returncode==expected,item
        return p

    def admin(self,*args,expected=0,timeout=60,env=None):
        p=self.command([self.target["hub_python"],"-m","smm_hub.cli","hub","--state-dir",str(self.state),*args],
                       expected=expected,timeout=timeout,env=env)
        return json.loads(p.stdout) if p.returncode==0 else p.stderr

    def configure(self, **changes):
        values=dict(self.cfg); values.update(changes)
        self.password.write_text(values["password"],encoding="utf-8"); self.password.chmod(0o600)
        argv=["vibeinsight","configure","--host",values["host"],"--port",str(values["port"]),
              "--database",values["database"],"--user",values["user"],"--password-file",str(self.password)]
        psql=changes.get("psql",self.target["psql"])
        if psql is not None:argv += ["--psql",psql]
        if "interval" in values: argv += ["--interval",str(values["interval"])]
        try: return self.admin(*argv,expected=values.get("expected",0),env=values.get("env"))
        finally: self.password.unlink(missing_ok=True)

    def api(self,route,payload=None):
        token=(self.state/"hub-token").read_text().strip()
        req=Request(self.target["address"]+"/v1/"+route,headers={"Content-Type":"application/json","Authorization":"Bearer "+token},
                    data=json.dumps(payload).encode() if payload is not None else None)
        opener=build_opener(ProxyHandler({}),HTTPSHandler(context=ssl.create_default_context(cafile=self.target["cert"])))
        with opener.open(req,timeout=3) as response:
            return json.load(response)

    def hits(self,word="platform"):
        return self.api("search",{"query":word,"limit":50})

    def read(self,hit):
        return self.api("read",{"hub_id":getattr(self,"expected_hub_id",None) or self.api("info")["hub_id"],"conversation_id":hit["id"]})

    def committed(self):
        return [self.read(hit) for hit in self.hits()["results"]]

    def assert_committed(self, records):
        observed=[]
        for old in records:
            current=self.api("read",{"hub_id":self.expected_hub_id,"conversation_id":old["id"]})
            assert current["messages"]==old["messages"]
            assert current["source_session_id"]==old["source_session_id"]
            exact_reads=[]
            for message in old["messages"]:
                exact=self.api("read",{"hub_id":self.expected_hub_id,"conversation_id":old["id"],"hub_message_id":message["hub_message_id"]})
                assert exact["messages"]==[message]
                exact_reads.append(exact)
            observed.append({"original_reference":{"hub_id":self.expected_hub_id,"conversation_id":old["id"]},"read":current,"exact_reads":exact_reads})
        self.retained_checks=getattr(self,"retained_checks",0)+1
        self.save("retained-originals-"+str(self.retained_checks),observed)

    def configuration_bytes(self):
        return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in self.state.glob("vibeinsight*") if p.is_file()}

    def assert_restart(self, before, label):
        after=self.service_identity()
        assert before["pid"]!=after["pid"]
        assert self.api("info")["hub_id"]==self.expected_hub_id
        self.save(label,{"before":before,"after":after})

    def session(self,name):
        return [h for h in self.hits()["results"] if h["source"]=="vibeinsight" and h["source_session_id"]==name]

    def checkpoints(self):
        with sqlite3.connect(self.state/"smm-hub.sqlite3") as con:
            con.row_factory=sqlite3.Row
            return [dict(row) for row in con.execute("SELECT * FROM hub_vibeinsight_cursors ORDER BY source_id,project")]

    def snapshot(self,name):
        data={"status":self.admin("vibeinsight","status"),"checkpoints":self.checkpoints(),"search":self.hits()}
        self.save(name,data); return data

    def start(self):
        if self.args.mode=="self-managed":
            out=(self.output/"standalone.log").open("a",encoding="utf-8")
            argv=[self.target["hub_python"],"-m","smm_hub.cli","serve-hub","--state-dir",str(self.state),
                  "--host","0.0.0.0","--port",str(self.target["port"]),"--token-file",str(self.state/"hub-token"),
                  "--tls-cert",self.target["cert"],"--tls-key",self.target["key"]]
            self.process=subprocess.Popen(argv,env=self.env,stdout=out,stderr=out)
            self.process_events.append({"action":"start","argv":argv,"pid":self.process.pid,"at":now()})
            self.save("P-process-events",self.process_events)
            out.close()
        else: self.admin("enable")
        eventually(lambda:self.api("info"))
        if self.args.mode=="self-managed":assert self.process.poll() is None

    def stop(self):
        if self.args.mode=="self-managed":
            if self.process and self.process.poll() is None:
                self.process.terminate()
                try:self.process.wait(timeout=20)
                except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=10);raise
                self.process_events.append({"action":"exit","pid":self.process.pid,"exit_code":self.process.returncode,"at":now()})
                self.save("P-process-events",self.process_events)
                assert self.process.returncode in (0,-15)
        else:self.admin("disable")

    def service_identity(self):
        if self.args.mode=="self-managed": return {"mode":"serve-hub","pid":self.process.pid}
        from smm_hub.hub_os import Service
        service=Service(self.state); self.service=service
        if sys.platform=="linux":
            unit=self.command(["systemctl","--user","show",service.unit,"-p","MainPID","-p","ActiveState","-p","ExecStart"]).stdout
            pid=int(next(line.split("=",1)[1] for line in unit.splitlines() if line.startswith("MainPID=")))
            assert pid>0
            process=self.command(["ps","-o","uid,pid,ppid,lstart,command","-p",str(pid)]).stdout
            assert os.stat(f"/proc/{pid}").st_uid==os.getuid()
            return {"mode":"systemd-user","unit":unit,"process":process,
                    "definition":self.command(["systemctl","--user","cat",service.unit]).stdout,"pid":pid}
        if sys.platform=="darwin":
            import plistlib
            d=plistlib.loads(service.plist.read_bytes())
            import pwd
            assert d["UserName"]==pwd.getpwuid(os.getuid()).pw_name and os.getuid()!=0
            text=self.command(["sudo","launchctl","print","system/"+service.launch_label]).stdout
            import re
            pid=int(re.search(r"\bpid = (\d+)",text)[1])
            return {"mode":"system-launchd","plist":d,"pid":pid,
                    "process":self.command(["ps","-o","uid,pid,ppid,lstart,command","-p",str(pid)]).stdout}
        result=self.command(["powershell","-NoProfile","-Command",
               f"$s=Get-CimInstance Win32_Service -Filter \"Name='{service.name}'\"; "
               "$p=Get-CimInstance Win32_Process -Filter ('ProcessId='+$s.ProcessId); "
               "@{service=$s|Select-Object Name,StartName,State,ProcessId,PathName;owner=Invoke-CimMethod -InputObject $p -MethodName GetOwner}|ConvertTo-Json -Depth 5"]).stdout
        data=json.loads(result)
        assert data["service"]["StartName"].lower()==r"nt authority\localservice"
        assert data["service"]["State"]=="Running"
        assert data["owner"]["User"].lower()=="local service" or data["owner"]["User"].lower()=="localservice"
        return {"mode":"LocalService",**data,"pid":data["service"]["ProcessId"]}

    def setup(self):
        self.fixture.reset()
        assert not self.state.exists(),"state must be a new dedicated directory"
        if self.args.mode=="self-managed":
            self.state.mkdir(mode=0o700)
            (self.state/"hub-token").write_text("synthetic-platform-token-"+"t"*40)
            self.missing_default_client()
            self.configure(interval=1); self.start()
        else:
            self.admin("setup","--address",self.target["address"],"--bind","0.0.0.0","--port",str(self.target["port"]),
                       "--tls-cert",self.target["cert"],"--tls-key",self.target["key"],"--ca-file",self.target["cert"])
            self.missing_default_client()
            self.configure()  # default 300, no --interval
        self.save("H1-service",self.service_identity())
        self.expected_hub_id=self.api("info")["hub_id"]
        eventually(lambda:len(self.session("turns"))==1)
        hit=self.session("turns")[0]; old=self.read(hit)
        assert [m["text"] for m in old["messages"]]==[f"platform evidence C turns {n}" for n in range(6)]
        self.save("H1-original",old)
        self.original=hit
        other=eventually(lambda:self.session("other"))
        other=self.read(other[0])
        assert [(m["role"],m["text"]) for m in other["messages"]]==[("user","platform evidence D other 100"),("assistant","platform evidence D other 101")]
        self.save("H1-other-project-original",other)

    def missing_default_client(self):
        empty=self.root/"empty-path";empty.mkdir(exist_ok=True)
        search=str(empty)
        if os.name=="nt":search += os.pathsep+str(Path(os.environ["SystemRoot"])/"System32")
        minimal=dict(self.env,PATH=search)
        error=self.configure(psql=None,env=minimal,expected=2,interval=1)
        assert "psql" in error
        assert not (self.state/"vibeinsight.json").exists()
        self.save("H1-missing-default-client",{"error":error,"terminal_search_path":minimal["PATH"]})

    def lifecycle(self):
        defaults=self.admin("vibeinsight","status")
        assert defaults["interval"]==(1 if self.args.mode=="self-managed" else 300)
        if self.args.mode!="self-managed":
            success=defaults["last_success"]
            # Real scheduling observation, no sleep/clock patch in the product.
            eventually(lambda:self.admin("vibeinsight","status")["last_success"]!=success,seconds=340)
        self.configure(interval=1)
        if self.args.mode != "self-managed":
            self.audit_psql_process()
        self.fixture.rows(104,106,session="scheduled",repo="D")
        eventually(lambda:len(self.session("scheduled"))==1)
        live=self.read(self.session("scheduled")[0])
        assert [m["text"] for m in live["messages"]]==[f"platform evidence D scheduled {n}" for n in (104,105)]
        self.save("H2-scheduled-original",live)
        cycle=self.admin("vibeinsight","status")["last_success"]
        eventually(lambda:self.admin("vibeinsight","status")["last_success"]!=cycle)
        profile=self.state/"vibeinsight.json"
        before=profile.read_bytes()
        protected=self.configuration_bytes()
        retained=self.committed(); saved_positions=self.checkpoints()
        for invalid in (0,-1,"1.5"):
            self.configure(interval=invalid,expected=2)
            assert profile.read_bytes()==before
            assert self.configuration_bytes()==protected and self.checkpoints()==saved_positions
            self.assert_committed(retained)
        self.snapshot("H2-status")
        for invalid in ({"password":"wrong-synthetic-password"},{"user":"limited_reader"},{"port":1}):
            self.configure(interval=1,expected=2,**invalid)
            assert profile.read_bytes()==before
            assert self.configuration_bytes()==protected and self.checkpoints()==saved_positions
            self.assert_committed(retained)
        self.snapshot("H3-status")
        saved=self.snapshot("H6-before"); old_id=self.original["id"]
        before_identity=self.service_identity()
        self.stop()
        if self.args.mode!="self-managed":assert not self.admin("status")["running"]
        self.save("H6-stopped",{"before_identity":before_identity,"checkpoints":self.checkpoints()})
        appended=self.fixture.rows(6,10)+self.fixture.rows(110,112,session="new",repo="D")
        self.save("H6-source-append",appended)
        assert not self.password.exists()
        self.start()
        self.assert_restart(before_identity,"H6-restarted")
        eventually(lambda:len(self.read(self.original)["messages"])==10)
        after=self.read(self.original)
        assert after["id"]==old_id
        assert [(m["role"],m["text"]) for m in after["messages"]]==[
            ("user" if n%2==0 else "assistant",f"platform evidence C turns {n}") for n in range(10)]
        assert len(self.session("new"))==1
        new=self.read(self.session("new")[0])
        assert [(m["role"],m["text"]) for m in new["messages"]]==[("user","platform evidence D new 110"),("assistant","platform evidence D new 111")]
        for n in range(6,10):
            assert any(m["text"]==f"platform evidence C turns {n}" for h in self.hits(f"turns {n}")["results"] for m in h["matched_messages"])
        self.save("H6-after-original",after); self.save("H6-new",self.read(self.session("new")[0]))
        done=self.admin("vibeinsight","status")["last_success"]
        eventually(lambda:self.admin("vibeinsight","status")["last_success"]!=done)
        assert len(self.read(self.original)["messages"])==10
        self.snapshot("H6-repeat")
        committed=self.committed(); no_new_positions=self.checkpoints(); identity=self.service_identity()
        self.stop(); self.start()
        self.assert_restart(identity,"H7-restarted")
        self.assert_committed(committed)
        assert self.checkpoints()==no_new_positions
        assert self.read(self.original)["messages"]==after["messages"]
        self.snapshot("H7-no-new-restart")
        prior=self.checkpoints()
        self.configure(interval=1,user="replacement_reader",password=self.cfg["replacement_password"])
        assert self.checkpoints()==prior
        identity=self.service_identity()
        self.stop(); self.start()
        self.assert_restart(identity,"H5-restarted")
        eventually(lambda:not self.admin("vibeinsight","status")["last_error"])
        assert self.checkpoints()==prior
        self.assert_committed(committed)
        assert len(self.read(self.original)["messages"])==10
        self.snapshot("H5-replaced-and-restarted")

    def failures(self):
        # Trigger tests an actual incomplete transaction in the service's archive.
        database=self.state/"smm-hub.sqlite3"
        before=self.checkpoints()
        retained=self.committed()
        with sqlite3.connect(database) as con:
            con.execute("""CREATE TRIGGER smm_fixture_abort BEFORE INSERT ON messages
                WHEN NEW.text='platform evidence C failed 121'
                 AND EXISTS(SELECT 1 FROM messages WHERE text='platform evidence C failed 120')
                BEGIN SELECT RAISE(ABORT,'fixture uncommitted batch'); END""")
        self.fixture.rows(120,122,session="failed")
        eventually(lambda:"fixture uncommitted batch" in str(self.admin("vibeinsight","status")["last_error"]))
        assert not self.session("failed")
        assert self.checkpoints()==before
        self.assert_committed(retained)
        self.snapshot("H8-failed")
        with sqlite3.connect(database) as con: con.execute("DROP TRIGGER smm_fixture_abort")
        eventually(lambda:len(self.session("failed"))==1)
        read=self.read(self.session("failed")[0]); assert len(read["messages"])==2
        assert [m["text"] for m in read["messages"]]==[f"platform evidence C failed {n}" for n in (120,121)]
        self.save("H8-recovered-original",read); self.snapshot("H8-recovered")
        retained=self.committed()
        # Only the task-owned client distribution is disrupted, never a system psql.
        binary=Path(self.target["psql"])
        if not binary.is_relative_to(self.root):
            raise ValueError("fault test psql must be a task-owned distribution")
        renamed=binary.with_name(binary.name+".fixture-hidden")
        binary.rename(renamed)
        try:
            eventually(lambda:self.admin("vibeinsight","status")["last_error"])
            self.observe_failure("H4-client-missing",retained)
            assert len(self.read(self.original)["messages"])==10
        finally: renamed.rename(binary)
        eventually(lambda:not self.admin("vibeinsight","status")["last_error"])
        self.recovery_increment(132, "recovery-1")
        if os.name=="nt":
            self.command(["icacls.exe",str(binary),"/deny","*S-1-5-19:RX"])
            try:
                eventually(lambda:self.admin("vibeinsight","status")["last_error"])
                self.observe_failure("H4-client-not-executable",retained)
            finally:self.command(["icacls.exe",str(binary),"/remove:d","*S-1-5-19"])
        else:
            mode=binary.stat().st_mode
            binary.chmod(0o600)
            try:
                eventually(lambda:self.admin("vibeinsight","status")["last_error"])
                self.observe_failure("H4-client-not-executable",retained)
            finally:binary.chmod(mode)
        eventually(lambda:not self.admin("vibeinsight","status")["last_error"])
        self.recovery_increment(134,"recovery-2")
        self.fixture.sql("ALTER ROLE replacement_reader NOLOGIN")
        try:
            eventually(lambda:self.admin("vibeinsight","status")["last_error"])
            self.observe_failure("H4-connection-failed",retained)
        finally:self.fixture.sql("ALTER ROLE replacement_reader LOGIN")
        eventually(lambda:not self.admin("vibeinsight","status")["last_error"])
        self.recovery_increment(136,"recovery-3")
        self.snapshot("H4-restored")


    def observe_failure(self,label,retained):
        self.assert_committed(retained)
        failure=self.snapshot(label)
        error=failure["status"]["last_error"].lower()
        assert "psql" in error or "role" in error
        success=failure["status"]["last_success"]
        time.sleep(1.1)
        assert self.admin("vibeinsight","status")["last_success"]==success

    def recovery_increment(self, number, name):
        expected=self.fixture.rows(number,number+2,session=name)
        eventually(lambda:len(self.session(name))==1)
        original=self.read(self.session(name)[0])
        assert [(m["role"],m["text"]) for m in original["messages"]]==[(m["role"],m["text"]) for m in expected]
        self.save("H4-"+name+"-new-original",original)

    def audit_psql_process(self):
        """Hold one fixture table lock so the real service child remains observable."""
        service=self.service_identity()
        parent=service["pid"]
        cfg=self.cfg
        env=dict(self.env,PGPASSWORD=cfg["admin_password"],PGAPPNAME="smm-fixture-process-audit")
        args=[self.target["psql"],"-XqAt","-v","ON_ERROR_STOP=1","-h",cfg["host"],"-p",str(cfg["port"]),
              "-U","probe_admin","-d",cfg["database"],"-c",
              "BEGIN; LOCK TABLE fact_events IN ACCESS EXCLUSIVE MODE; SELECT pg_sleep(15); COMMIT;"]
        lock=subprocess.Popen(args,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            eventually(lambda:self.fixture.sql("SELECT count(*) FROM pg_stat_activity WHERE application_name='smm-fixture-process-audit' AND wait_event='PgSleep'").strip()=="1",seconds=8)
            if os.name=="nt":
                query=("Get-CimInstance Win32_Process -Filter \"ParentProcessId="+str(parent)+"\" | "
                       "Where-Object Name -eq 'psql.exe' | Select-Object ProcessId,ParentProcessId,ExecutablePath,CommandLine | ConvertTo-Json")
                def observe():
                    data=self.command(["powershell","-NoProfile","-Command",query]).stdout.strip()
                    return json.loads(data) if data else None
                child=eventually(observe,seconds=10)
                if isinstance(child,list):child=child[0]
                assert child["ParentProcessId"]==parent
            else:
                def observe():
                    children=self.command(["pgrep","-P",str(parent)],expected=None).stdout.split()
                    for pid in children:
                        record=self.command(["ps","-p",pid,"-o","pid=,ppid=,uid=,command="],expected=None).stdout.strip()
                        if "psql" in record and int(record.split()[1])==parent:return record
                child=eventually(observe,seconds=10)
            self.save("H1-service-psql-process",{"service":service,"psql_child":child,
                "observation":"SELECT waits for a fixture-only table lock; controller uses probe_admin, service uses its configured read-only role"})
        finally:
            stdout,stderr=lock.communicate(timeout=25)
            assert lock.returncode==0,self.redact(stderr.decode(errors="replace"))

    def permissions(self):
        config=json.loads((self.state/"vibeinsight.json").read_text())
        secret=self.state/Path(config["credential_file"]).name
        assert secret.read_text()==self.cfg["replacement_password"]
        if os.name=="nt":
            self.save("H9-acl",{"state":self.command(["icacls.exe",str(self.state)]).stdout,
                                "credential":self.command(["icacls.exe",str(secret)]).stdout,
                                "runtime":self.command(["icacls.exe",str(Path(self.target["hub_python"]).parent)]).stdout})
        else:
            import stat
            assert not stat.S_IMODE(secret.stat().st_mode)&0o077
            assert not stat.S_IMODE(self.state.stat().st_mode)&0o077
            self.save("H9-permissions",{"credential_mode":oct(stat.S_IMODE(secret.stat().st_mode)),
                                        "directory_mode":oct(stat.S_IMODE(self.state.stat().st_mode)),"owner_uid":secret.stat().st_uid})
        helper=Path(__file__).with_name("vibeinsight_denied_read.py")
        if os.name=="nt":
            response=self.command([self.target["hub_python"],str(helper),str(secret)])
        elif sys.platform=="linux" and self.target.get("permission_method")=="posix-acl-audit":
            import re,stat
            evidence=[]
            for path in (self.state,secret):
                info=path.lstat()
                assert not stat.S_ISLNK(info.st_mode) and info.st_uid==os.getuid()
                assert not stat.S_IMODE(info.st_mode)&0o077
                acl=self.command([self.target["getfacl"],"--absolute-names","--numeric",str(path)]).stdout
                entries=[line for line in acl.splitlines() if line and not line.startswith("#")]
                assert not any(re.match(r"(?:user|group):[^:]+:",line) or line.startswith("default:") for line in entries)
                assert "group::---" in entries and "other::---" in entries
                evidence.append({"path":str(path),"uid":info.st_uid,"mode":oct(stat.S_IMODE(info.st_mode)),"acl":acl})
            self.save("H9-posix-access-audit",{"method":"actual owner, mode and complete POSIX ACL audit",
                "other_uid_open_executed":False,"evidence":evidence,
                "inference":"No named/default ACL grants; group and other have no access. Under Linux DAC, other unprivileged UIDs cannot read; authorized owner and privileged administration are outside that exclusion."})
            response=None
        else:
            response=self.command(["sudo","-n","-u","nobody","--","/usr/bin/python3","-c",helper.read_text(encoding="utf-8"),str(secret),"--owner-uid",str(secret.stat().st_uid)])
        if response is not None:
            negative=json.loads(response.stdout)
            assert negative["attempted"] and negative["denied"]
            self.save("H9-denied-read",negative)
        backup=self.output/"private-archive-scan.sqlite3"
        with closing(sqlite3.connect(self.state/"smm-hub.sqlite3")) as source, closing(sqlite3.connect(backup)) as dest:
            source.backup(dest)
        contents=backup.read_bytes()
        backup.unlink()
        logs="".join(path.read_text(encoding="utf-8",errors="replace") for path in self.state.glob("*.log"))
        assert all(password.encode() not in contents and password not in logs for password in self.secrets)
        self.save("H9-secret-scan",{"archive_hits":0,"log_hits":0})

    def standalone_compatibility(self):
        conflict=self.root/"conflicting.sqlite3"
        p=self.command([self.target["hub_python"],"-m","smm_hub.cli","--db",str(conflict),"serve-hub",
                        "--state-dir",str(self.state),"--token-file",str(self.state/"hub-token")],expected=2)
        assert "--db" in p.stderr and "--state-dir" in p.stderr and not conflict.exists()
        old=self.api("info")["hub_id"]
        self.stop()
        log=(self.output/"legacy.log").open("w")
        self.process=subprocess.Popen([self.target["hub_python"],"-m","smm_hub.cli","--db",str(self.root/"legacy.sqlite3"),
             "serve-hub","--host","0.0.0.0","--port",str(self.target["port"]),"--token-file",str(self.state/"hub-token"),
             "--tls-cert",self.target["cert"],"--tls-key",self.target["key"]],env=self.env,stdout=log,stderr=log)
        self.process_events.append({"action":"legacy-start","argv":self.process.args,"pid":self.process.pid,"at":now()})
        self.save("P-process-events",self.process_events)
        log.close()
        eventually(lambda:self.api("info"))
        assert self.process.poll() is None
        assert self.api("info")["hub_id"]!=old
        assert self.hits()["results"]==[]
        self.save("P-legacy",self.api("info"))
        self.stop();self.start()
        assert self.api("info")["hub_id"]==old
        assert len(self.read(self.original)["messages"])==10
        self.snapshot("P-original-retained")

    def finish(self, status, error=None):
        # A failed run has its own report; it cannot reuse a prior success file.
        report={"status":status,"started_at":self.started,"ended_at":now(),"mode":self.args.mode,
                "platform":platform.platform(),"python":sys.version,"observations":self.observed,"error":error,
                "candidate":self.target.get("candidate"),"fixture_kind":self.cfg["kind"],
                "probe_files_sha256":self.probe_files_sha256}
        self.save("result",report)
        for path in self.state.glob("*.log"):
            (self.output/path.name).write_text(json.dumps(self.redact(path.read_text(encoding="utf-8",errors="replace")),ensure_ascii=False),encoding="utf-8")
        return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode",choices=["hub","self-managed","client","shared"])
    p.add_argument("--target-config",type=Path,required=True); p.add_argument("--fixture-manifest",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    if a.mode=="client":
        from vibeinsight_client import client_main
        return client_main(a)
    run=Run(a)
    try:
        run.installed_identity()
        if a.mode=="shared":
            from vibeinsight_shared import shared
            shared(run)
        else:
            run.setup();run.lifecycle()
            if a.mode=="self-managed":run.standalone_compatibility()
            else:run.failures();run.permissions()
        run.save("final-service",run.service_identity())
        run.finish("passed")
    except BaseException as exc:
        run.finish("failed",type(exc).__name__+": "+str(exc)); raise
    finally:
        try:run.stop()
        except Exception as exc:
            run.save("cleanup-error",{"error":str(exc)})
            raise


if __name__=="__main__":main()
