# SPDX-License-Identifier: Apache-2.0
"""Optional PostgreSQL, HTTPS, installed-wheel and legacy-client acceptance."""

import json
import socket
import ssl
import subprocess
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import URLError
from urllib.request import Request, urlopen

from vibeinsight_probe_support import (
    arguments,
    clean_environment,
    executable,
    export_baseline,
    installed_identity,
    save_report,
)

args = arguments(
    "Validate installed wheels against an isolated local PostgreSQL fixture"
)
hub = executable(args.hub_env, "smm-hub")
local = executable(args.local_env, "smm")
local_python = executable(args.local_env, "python")
env = clean_environment()
identities = installed_identity(args)
observed = {}


def run(*args, **kwargs):
    result = subprocess.run(
        args, capture_output=True, text=True, env=env, timeout=45, **kwargs
    )
    if result.returncode:
        raise RuntimeError(result.stderr)
    return result.stdout


with TemporaryDirectory(prefix="smm-wheel-pg-", dir="/tmp") as workspace:
    root = Path(workspace)
    old_source = export_baseline(root / "baseline")
    pg = root / "pg"
    sock = root / "socket"
    sock.mkdir()
    run(
        "initdb",
        "-D",
        str(pg),
        "-U",
        "probe_admin",
        "-A",
        "trust",
        "--no-locale",
        "-E",
        "UTF8",
    )
    pg_port = "55430"
    hba = pg / "pg_hba.conf"
    hba.write_text(
        "local all source_reader scram-sha-256\n"
        "local all discovery_only scram-sha-256\n" + hba.read_text()
    )
    run(
        "pg_ctl",
        "-D",
        str(pg),
        "-l",
        str(root / "pg.log"),
        "-o",
        f"-c listen_addresses='' -k {sock} -p {pg_port}",
        "-w",
        "start",
    )
    process = None
    try:

        def sql(statement):
            return run(
                "psql",
                "-XqAt",
                "-v",
                "ON_ERROR_STOP=1",
                "-h",
                str(sock),
                "-p",
                pg_port,
                "-U",
                "probe_admin",
                "-d",
                "postgres",
                input=statement,
            )

        sql("""
        CREATE TABLE fact_events (
           id varchar(26) PRIMARY KEY, user_id varchar(26), platform_code varchar(255) NOT NULL,
           session_id varchar(255) NOT NULL, trace_id varchar(255), event_type varchar(255),
           message text, repo_hostname varchar(255), repo_port integer, repo_path varchar(1024),
           event_timestamp timestamp NOT NULL, created_at timestamp NOT NULL
        );
        CREATE INDEX fact_events_created_at_id ON fact_events(created_at,id);
        CREATE INDEX fact_events_session_id ON fact_events(session_id);
        CREATE ROLE source_reader LOGIN PASSWORD 'synthetic-wheel-probe';
        GRANT SELECT ON fact_events TO source_reader;
        ALTER TABLE fact_events ENABLE ROW LEVEL SECURITY;
        CREATE POLICY visible ON fact_events FOR SELECT TO source_reader USING (session_id <> 'third');
        """)

        def event(
            identifier,
            session,
            trace,
            kind,
            second,
            text,
            project=None,
            *,
            hostname="git.example",
            port=None,
        ):
            port_sql = "NULL" if port is None else str(port)
            repo = (
                f"'{hostname}',{port_sql},'team/{project}'"
                if project
                else "NULL,NULL,NULL"
            )
            sql(f"""INSERT INTO fact_events VALUES ('{identifier}','owner','codex',
               '{session}','{trace}','{kind}','{text}',{repo},'2026-09-14 00:00:{second:02}',
               '2026-09-14 00:00:{second:02}');""")

        event("E001", "third", "3", "trace.started", 1, "historical needle", "third")
        event("E005", "main", "1", "trace.started", 10, "first needle", "alpha")
        event("E006", "main", "1", "trace.completed", 11, "first response")
        event(
            "E010", "spare", "2", "trace.started", 20, "second-project marker", "beta"
        )

        state = root / "state"
        state.mkdir()
        password = root / "password.txt"
        password.write_text("synthetic-wheel-probe", encoding="utf-8")
        with socket.socket() as selected:
            selected.bind(("127.0.0.1", 0))
            port = selected.getsockname()[1]
        cert, key = state / "tls.pem", state / "tls-key.pem"
        openssl_conf = root / "openssl.cnf"
        openssl_conf.write_text(
            "[req]\ndistinguished_name=dn\nx509_extensions=extensions\nprompt=no\n"
            "[dn]\nCN=127.0.0.1\n[extensions]\nsubjectAltName=IP:127.0.0.1\n"
        )
        run(
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-days",
            "1",
            "-config",
            str(openssl_conf),
            "-keyout",
            str(key),
            "-out",
            str(cert),
        )
        base = [str(hub), "hub", "--state-dir", str(state)]
        address = f"https://127.0.0.1:{port}"
        (state / "hub.json").write_text(
            json.dumps(
                {"address": address, "bind": "127.0.0.1", "port": port, "enabled": True}
            )
        )
        (state / "hub-token").write_text("w" * 40)
        result = json.loads(
            run(
                *base,
                "vibeinsight",
                "configure",
                "--host",
                str(sock),
                "--port",
                pg_port,
                "--database",
                "postgres",
                "--user",
                "source_reader",
                "--interval",
                "1",
                "--password-file",
                str(password),
            )
        )
        assert result["credential_saved"]
        observed["configured"] = {
            key: result[key] for key in ("enabled", "credential_saved")
        }
        config_before = (state / "vibeinsight.json").read_bytes()
        sql(
            "CREATE ROLE discovery_only LOGIN PASSWORD 'synthetic-wheel-probe'; GRANT SELECT (id,created_at,event_type,message,"
            "repo_hostname,repo_port,repo_path) ON fact_events TO discovery_only;"
        )
        invalid = subprocess.run(
            base
            + [
                "vibeinsight",
                "configure",
                "--host",
                str(sock),
                "--port",
                pg_port,
                "--database",
                "postgres",
                "--user",
                "discovery_only",
                "--interval",
                "1",
                "--password-file",
                str(password),
            ],
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )
        assert (
            invalid.returncode != 0
            and (state / "vibeinsight.json").read_bytes() == config_before
        )
        assert "synthetic-wheel-probe" not in invalid.stdout + invalid.stderr
        password.unlink()

        def start():
            return subprocess.Popen(
                base + ["run"],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        def stop(proc):
            if proc.poll() is None:
                proc.terminate()
            proc.wait(timeout=15)

        def read_api(route, payload):
            request = Request(
                address + "/v1/" + route,
                data=json.dumps(payload).encode() if payload is not None else None,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + "w" * 40,
                },
            )
            with urlopen(
                request, timeout=2, context=ssl.create_default_context(cafile=str(cert))
            ) as reply:
                return json.load(reply)

        def eventually(check):
            for _ in range(120):
                try:
                    if result := check():
                        return result
                except (OSError, URLError):
                    pass
                time.sleep(0.1)
            raise AssertionError((state / "hub.log").read_text()[-4000:])

        def hits(word):
            return read_api("search", {"query": word, "limit": 20})["results"]

        process = start()
        first = eventually(lambda: hits("needle"))
        observed["initial_search"] = first
        assert {x["source_session_id"] for x in first} == {"main"}
        identity = read_api("info", None)["hub_id"]
        original_id = first[0]["id"]
        sql("ALTER POLICY visible ON fact_events USING (true);")
        eventually(
            lambda: {x["source_session_id"] for x in hits("needle")}
            == {"main", "third"}
        )
        assert len(json.loads(run(*base, "project", "list"))) == 3
        observed["after_project_discovery"] = hits("needle")
        stop(process)
        event("E011", "main", "2", "trace.started", 20, "second needle", "alpha")
        event("E014", "spare", "3", "trace.started", 25, "advances upper bound", "beta")
        process = start()
        eventually(
            lambda: len(
                read_api("read", {"hub_id": identity, "conversation_id": original_id})[
                    "messages"
                ]
            )
            == 3
        )
        sql("UPDATE fact_events SET message='historical direct edit' WHERE id='E006';")
        event("E012", "main", "2", "trace.completed", 21, "late response")
        result = eventually(
            lambda: (
                result
                if len(
                    (
                        result := read_api(
                            "read", {"hub_id": identity, "conversation_id": original_id}
                        )
                    )["messages"]
                )
                == 4
                else None
            )
        )
        assert [m["text"] for m in result["messages"]] == [
            "first needle",
            "first response",
            "second needle",
            "late response",
        ]
        assert result["messages"][-1]["origins"][0]["source_event_id"] == "E012"

        observed["resumed_read"] = result
        event("E020", "main", "4", "trace.started", 27, "beta realm prompt", "beta")
        event("E021", "main", "4", "trace.completed", 27, "beta realm reply")
        event(
            "E022",
            "spare",
            "different-fallback",
            "trace.completed",
            28,
            "unmatched fallback reply",
        )
        mixed = eventually(lambda: rows if (rows := hits("realm")) else None)
        assert mixed[0]["source_session_id"] == "main"
        assert {
            m["origins"][0]["project_name"] for m in mixed[0]["matched_messages"]
        } == {"git.example/team/beta"}
        assert {project["name"] for project in mixed[0]["projects"]} == {
            "git.example/team/beta"
        }
        entire = read_api("read", {"hub_id": identity, "conversation_id": original_id})
        assert {project["name"] for project in entire["projects"]} == {
            "git.example/team/alpha",
            "git.example/team/beta",
        }
        fallback = eventually(lambda: rows if (rows := hits("unmatched")) else None)
        assert fallback[0]["source_session_id"] == "spare"
        assert (
            fallback[0]["matched_messages"][0]["origins"][0]["project_name"]
            == "git.example/team/beta"
        )
        event(
            "E040",
            "changed-host",
            "host",
            "trace.started",
            40,
            "identity hostname",
            "alpha",
            hostname="other.example",
        )
        event(
            "E041",
            "changed-port",
            "port",
            "trace.started",
            41,
            "identity port",
            "alpha",
            port=2222,
        )
        event(
            "E042",
            "changed-path",
            "path",
            "trace.started",
            42,
            "identity path",
            "renamed",
        )
        query_driver = """
import json, shutil, sys
from smm_hub.vibeinsight import PostgresSource, event_position
source = PostgresSource(dict(host=sys.argv[1],port=int(sys.argv[2]),database='postgres',user='source_reader',
                             psql=shutil.which('psql')),'synthetic-wheel-probe')
end = source.upper()
previous = None
seen = []
while page := source.page('git.example/team/beta',previous,end,1):
    seen.extend(event['id'] for event in page)
    previous = event_position(page[-1])
mode = source._query("SELECT to_json(current_setting('transaction_read_only'))")[0]
print(json.dumps({'events': seen, 'projects': source.projects(end), 'transaction_read_only': mode}))
"""
        driver = str(executable(args.hub_env, "python"))
        query_evidence = json.loads(run(driver, "-c", query_driver, str(sock), pg_port))
        assert query_evidence["transaction_read_only"] == "on"
        assert {
            "other.example/team/alpha",
            "git.example:2222/team/alpha",
            "git.example/team/renamed",
        }.issubset(query_evidence["projects"])
        observed["source_query"] = query_evidence
        exact_pages = query_evidence["events"]
        observed["sql_pages"] = exact_pages
        assert exact_pages[-3:] == ["E020", "E021", "E022"], exact_pages
        print(
            "PASS: SQL page boundary with equal created_at, mixed-repository and unpaired trace attribution, and unsafe credential replacement refusal."
        )

        event(
            "E030",
            "main",
            "late-trace",
            "trace.completed",
            29,
            "provisional delayed reply",
        )
        early = eventually(lambda: rows if (rows := hits("provisional")) else None)

        def event_project(result, event_id):
            return next(
                origin["project_name"]
                for message in result["matched_messages"]
                for origin in message["origins"]
                if origin["source_event_id"] == event_id
            )

        assert event_project(early[0], "E030") == "(无仓库)"
        event(
            "E031",
            "main",
            "late-trace",
            "trace.started",
            30,
            "late matching prompt",
            "beta",
        )
        event("E032", "main", "missing-repo", "trace.started", 31, "inferrepo prompt")
        event(
            "E033",
            "main",
            "missing-repo",
            "trace.completed",
            32,
            "inferrepo reply",
            "beta",
        )

        def corrected():
            rows = hits("provisional")
            return (
                rows
                if rows and event_project(rows[0], "E030") == "git.example/team/beta"
                else None
            )

        assert eventually(corrected)[0]["id"] == original_id
        inferred = eventually(
            lambda: (
                rows
                if (rows := hits("inferrepo")) and len(rows[0]["matched_messages"]) == 2
                else None
            )
        )
        assert len(inferred[0]["matched_messages"]) == 2
        assert {
            m["origins"][0]["project_name"] for m in inferred[0]["matched_messages"]
        } == {"git.example/team/beta"}
        print(
            "PASS: PostgreSQL SCRAM credentials and late repository provenance without changing the archived message."
        )

        codex_root = root / "client-codex"
        claude_root = root / "client-claude"
        codex_root.mkdir()
        claude_root.mkdir()
        env.update(
            SSL_CERT_FILE=str(cert),
            SMM_SERVICE_PORT="0",
            SMM_LOGIN_SERVICE="0",
            SMM_CODEX_ROOT=str(codex_root),
            SMM_CLAUDE_ROOT=str(claude_root),
        )
        local_db = root / "client.sqlite3"
        configured = json.loads(
            run(
                str(local),
                "--db",
                str(local_db),
                "configure-hub",
                address,
                "wheel client",
                "--token-file",
                str(state / "hub-token"),
            )
        )
        assert configured["connected"], configured
        try:
            result = json.loads(
                run(str(local), "--db", str(local_db), "search", "needle")
            )
            assert {h["source_session_id"] for h in result["results"]} == {
                "main",
                "third",
            }
            mcp_program = """
import asyncio, json, os, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
async def main():
    params = StdioServerParameters(command=sys.executable,
       args=['-m','smm_local.mcp_server','--db',sys.argv[1]], env=dict(os.environ))
    async with stdio_client(params) as (sender, receiver):
        async with ClientSession(sender,receiver) as session:
            await session.initialize()
            result = await session.call_tool('search_conversations',{'query':'needle'})
            assert not result.isError
            print(result.content[0].text)
asyncio.run(main())
"""
            via_mcp = json.loads(
                run(str(local_python), "-c", mcp_program, str(local_db))
            )
            assert {h["source_session_id"] for h in via_mcp["results"]} == {
                "main",
                "third",
            }
            observed["cli_search"] = result
            observed["mcp_search"] = via_mcp
            print(
                "PASS: independently installed Hub wheel with PostgreSQL 14 and managed HTTPS lifecycle."
            )
            print(
                "PASS: read-only source, later-visible older history, same-timestamp restart, late completion, original edit preserved, original event reference."
            )
            print(
                "PASS: independently installed Local wheel used CLI and stdio MCP to query Hub."
            )
            (codex_root / "legacy.jsonl").write_text(
                json.dumps(
                    {
                        "type": "session_meta",
                        "payload": {"id": "legacy-session", "cwd": str(codex_root)},
                    }
                )
                + "\n"
                + json.dumps(
                    {
                        "type": "response_item",
                        "payload": {
                            "type": "message",
                            "id": "legacy-message",
                            "role": "user",
                            "content": [
                                {
                                    "type": "input_text",
                                    "text": "legacy compatibility marker",
                                }
                            ],
                        },
                    }
                )
                + "\n"
            )
            legacy_db = root / "legacy.sqlite3"
            env["PYTHONPATH"] = str(old_source)
            legacy_cli = [
                str(local_python),
                "-m",
                "smm_local.cli",
                "--db",
                str(legacy_db),
            ]
            try:
                assert json.loads(
                    run(
                        *legacy_cli,
                        "configure-hub",
                        address,
                        "old client",
                        "--token-file",
                        str(state / "hub-token"),
                    )
                )["connected"]
                run(*legacy_cli, "maintenance", "sync")
                legacy_search = json.loads(run(*legacy_cli, "search", "legacy"))
                (legacy_hit,) = legacy_search["results"]
                assert legacy_hit["source_session_id"] == "legacy-session"
                original = json.loads(
                    run(
                        *legacy_cli,
                        "read",
                        str(legacy_hit["id"]),
                        "--hub-id",
                        legacy_search["hub_id"],
                    )
                )
                assert original["messages"][0]["text"] == "legacy compatibility marker"
                observed["legacy_client_search"] = legacy_search
                observed["legacy_client_read"] = original
                print(
                    "PASS: actual client from baseline d2dee18 uploaded, searched and read via the new Hub."
                )
            finally:
                run(*legacy_cli, "stop-on-demand")
                env.pop("PYTHONPATH")
        finally:
            run(str(local), "--db", str(local_db), "stop-on-demand")
    finally:
        if process is not None:
            stop(process)
        run("pg_ctl", "-D", str(pg), "-m", "fast", "-w", "stop")

save_report(args, observed, identities)
