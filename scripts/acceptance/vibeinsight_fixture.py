# SPDX-License-Identifier: Apache-2.0
"""Create a disposable TCP PostgreSQL fixture. Never accepts an existing database DSN."""
import argparse
from datetime import datetime, timedelta
import json
import ipaddress
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess

MARKER = "smm-isolated-vibeinsight-003-v1"


def run(args, *, data=None, env=None):
    p = subprocess.run(list(map(str, args)), input=data, text=True, encoding="utf-8",
                       capture_output=True, env=env, timeout=60)
    if p.returncode:
        raise RuntimeError(p.stderr or p.stdout)
    return p.stdout


def literal(value):
    return "'" + str(value).replace("'", "''") + "'"


class Fixture:
    def __init__(self, manifest, psql=None):
        self.config = json.loads(Path(manifest).read_text(encoding="utf-8"))
        if self.config.get("kind") != MARKER:
            raise ValueError("not a generated isolated fixture")
        self.psql = str(psql or self.config["psql"])
        # Check a random instance marker before allowing any write.
        marker = self.sql("SELECT marker FROM smm_fixture_instance", verify=False).strip()
        if marker != self.config["instance"]:
            raise ValueError("fixture instance differs; refusing writes")

    def sql(self, statement, *, verify=True):
        cfg = self.config
        env = {k: v for k, v in os.environ.items() if not k.startswith("PG")}
        env["PGPASSWORD"] = cfg["admin_password"]
        return run([self.psql, "-XqAt", "-v", "ON_ERROR_STOP=1", "-h", cfg["host"], "-p", cfg["port"],
                    "-U", "probe_admin", "-d", cfg["database"]], data=statement, env=env)

    def rows(self, start, end, *, session="turns", repo="C", created_start=None):
        records = []
        for n in range(start, end):
            timestamp = datetime(2026, 9, 10) + timedelta(minutes=n)
            created = (datetime.fromisoformat(created_start) + timedelta(seconds=n-start)
                       if created_start else timestamp)
            records.append({"id": f"E{n:06d}", "session": session, "repo": repo,
                            "trace": f"{session}-{n//2}", "role": "user" if n % 2 == 0 else "assistant",
                            "text": f"platform evidence {repo} {session} {n}",
                            "created_at": created.isoformat(), "timestamp": timestamp.isoformat()})
        values=[]
        for row in records:
            values.append("(" + ",".join(map(literal, [
                row["id"], "owner", "codex", row["session"], row["trace"],
                "trace.started" if row["role"] == "user" else "trace.completed", row["text"],
                "git.example", "0", "team/"+repo, row["timestamp"], row["created_at"]])) + ")")
        if values:self.sql("INSERT INTO fact_events VALUES " + ",".join(values))
        return records

    def reset(self):
        self.sql("TRUNCATE fact_events; DROP POLICY IF EXISTS visibility ON fact_events; "
                 "CREATE POLICY visibility ON fact_events FOR SELECT TO source_reader, replacement_reader "
                 "USING(repo_path <> 'team/hidden');")
        return self.rows(0, 6) + self.rows(100, 102, session="other", repo="D")


def create(root, *, pg_bin, host, allow_cidr="127.0.0.1/32"):
    network=str(ipaddress.ip_network(allow_cidr,strict=False))
    root = Path(root).resolve()
    if root.exists():
        raise ValueError("fixture root must be new; refusing to reuse or replace existing state")
    root.mkdir(parents=True, mode=0o700)
    pg_bin = Path(pg_bin)
    data = root / "pg"
    run([pg_bin/"initdb", "-D", data, "-U", "probe_admin", "-A", "scram-sha-256",
         "--pwfile", password_file(root), "--no-locale", "-E", "UTF8"])
    admin = (root/"admin-input").read_text().strip()
    (root/"admin-input").unlink()
    with socket.socket() as sock:
        sock.bind(("", 0)); port = sock.getsockname()[1]
    (data/"pg_hba.conf").write_text("host all all 127.0.0.1/32 scram-sha-256\n"+f"host all all {network} scram-sha-256\n")
    # Synthetic data only: statements provide server-side proof of explicit read-only Hub transactions.
    run([pg_bin/"pg_ctl", "-D", data, "-l", root/"postgres.log", "-o",
         f"-h 0.0.0.0 -p {port} -c log_statement=all -c log_connections=on -c log_line_prefix='%m %u@%d [%p] '", "-w", "start"])
    cfg = {"kind": MARKER, "instance": secrets.token_hex(16), "host": host, "port": port,
           "database": "postgres", "user": "source_reader", "password": secrets.token_urlsafe(24),
           "replacement_password": secrets.token_urlsafe(24), "admin_password": admin,
           "pg_data": str(data), "pg_bin": str(pg_bin), "psql": str(pg_bin/"psql")}
    manifest = root/"private-fixture.json"
    manifest.write_text(json.dumps(cfg, indent=2)); manifest.chmod(0o600)
    # Instance marker does not exist until this dedicated freshly initialized cluster is seeded.
    obj = object.__new__(Fixture); obj.config=cfg; obj.psql=cfg["psql"]
    obj.sql("CREATE TABLE smm_fixture_instance(marker text); INSERT INTO smm_fixture_instance VALUES ("+
            literal(cfg["instance"])+"); CREATE TABLE fact_events (id varchar(26) PRIMARY KEY,user_id varchar(26),"
            "platform_code text,session_id text,trace_id text,event_type text,message text,repo_hostname text,"
            "repo_port integer,repo_path text,event_timestamp timestamp,created_at timestamp); "
            "CREATE INDEX ON fact_events(created_at,id); "
            "CREATE ROLE source_reader LOGIN PASSWORD "+literal(cfg["password"])+"; "
            "CREATE ROLE replacement_reader LOGIN PASSWORD "+literal(cfg["replacement_password"])+"; "
            "CREATE ROLE limited_reader LOGIN PASSWORD "+literal(cfg["password"])+"; "
            "GRANT SELECT ON fact_events TO source_reader,replacement_reader; "
            "GRANT SELECT(id,created_at) ON fact_events TO limited_reader; "
            "ALTER ROLE source_reader SET default_transaction_read_only=on; "
            "ALTER ROLE replacement_reader SET default_transaction_read_only=on; "
            "ALTER TABLE fact_events ENABLE ROW LEVEL SECURITY;")
    Fixture(manifest).reset()
    return manifest


def password_file(root):
    path=root/"admin-input"; path.write_text(secrets.token_urlsafe(32)); path.chmod(0o600)
    return path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="action",required=True)
    c=sub.add_parser("create"); c.add_argument("--root",type=Path,required=True)
    c.add_argument("--pg-bin",type=Path,required=True); c.add_argument("--host",required=True)
    c.add_argument("--allow-cidr",default="127.0.0.1/32",help="fixture clients network; loopback only by default")
    stop=sub.add_parser("stop"); stop.add_argument("--manifest",type=Path,required=True)
    a=p.parse_args()
    if a.action=="create":
        print(create(a.root,pg_bin=a.pg_bin,host=a.host,allow_cidr=a.allow_cidr))
    else:
        f=Fixture(a.manifest)
        run([Path(f.config["pg_bin"])/"pg_ctl","-D",f.config["pg_data"],"-m","fast","-w","stop"])


if __name__=="__main__": main()
