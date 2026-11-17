# SPDX-License-Identifier: Apache-2.0
"""Optional prior-archive migration acceptance using synthetic records."""

import json, os, socket, sqlite3, subprocess, time
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import Request, urlopen

from vibeinsight_probe_support import (
    arguments,
    executable,
    export_baseline,
    installed_identity,
    save_report,
)

args = arguments("Validate a prior Hub archive and its references after upgrade")
old = [str(executable(args.local_env, "python"))]
hub_new = [str(executable(args.hub_env, "smm-hub"))]
identities = installed_identity(args)
observed = {}
with TemporaryDirectory(prefix="smm-upgrade-") as directory:
    home = Path(directory)
    old_root = str(export_baseline(home / "baseline"))
    token = home / "token"
    token.write_text("u" * 40)
    dev_a, dev_b = "1" * 32, "2" * 32
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    db = home / "hub.sqlite3"
    process = None
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env.update(SMM_SERVICE_PORT="0", SMM_LOGIN_SERVICE="0")
    old_env = {**env, "PYTHONPATH": old_root}

    def call(route, payload=None):
        request = Request(
            f"http://127.0.0.1:{port}/v1/{route}",
            data=json.dumps(payload).encode() if payload is not None else None,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + "u" * 40,
            },
        )
        with urlopen(request, timeout=2) as reply:
            return json.load(reply)

    def start(argv, runtime):
        process = subprocess.Popen(
            argv
            + [
                "--db",
                str(db),
                "serve-hub",
                "--port",
                str(port),
                "--token-file",
                str(token),
            ],
            env=runtime,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(100):
            try:
                call("info")
                return process
            except OSError:
                if process.poll() is not None:
                    raise RuntimeError("Hub exited")
                time.sleep(0.1)
        raise RuntimeError("Hub did not start")

    def stop():
        if process is not None and process.poll() is None:
            process.terminate()
            process.wait(timeout=10)

    try:
        process = start(old + ["-m", "smm_hub.cli"], old_env)
        hub_id = call("info")["hub_id"]
        for device, word in [(dev_a, "laptop"), (dev_b, "desktop")]:
            payload = {
                "device_id": device,
                "device_name": word,
                "hub_id": hub_id,
                "records": [
                    {
                        "source": "codex",
                        "source_session_id": word,
                        "started_at": None,
                        "source_key": word,
                        "position": 1,
                        "source_order": 1,
                        "timestamp": None,
                        "role": "user",
                        "text": "shared " + word,
                    }
                ],
            }
            assert call("upload", payload)["accepted"] == 1
        old = call("search", {"query": "shared"})
        observed["before_upgrade"] = old
        origins = {
            hit["id"]: hit["matched_messages"][0]["hub_message_id"]
            for hit in old["results"]
        }
        stop()
        with sqlite3.connect(db) as con:
            assert (
                con.execute(
                    "SELECT 1 FROM sqlite_master WHERE name='hub_projects'"
                ).fetchone()
                is None
            )

        process = start(hub_new, env)
        upgraded = call("search", {"query": "shared"})
        observed["after_upgrade"] = upgraded
        assert upgraded["hub_id"] == hub_id
        assert origins == {
            hit["id"]: hit["matched_messages"][0]["hub_message_id"]
            for hit in upgraded["results"]
        }
        for device, word in [(dev_a, "laptop"), (dev_b, "desktop")]:
            batch = {
                "device_id": device,
                "device_name": word,
                "hub_id": hub_id,
                "projects": [{"id": 1, "name": "same name"}],
                "memberships": [
                    {"source": "codex", "source_session_id": word, "project_id": 1}
                ],
            }
            assert call("project-metadata", batch)["memberships"] == 1
        observed["project_scopes"] = {}
        for device, word in [(dev_a, "laptop"), (dev_b, "desktop")]:
            scoped = call(
                "search", {"query": "shared", "device_id": device, "project_id": 1}
            )
            assert {hit["source_session_id"] for hit in scoped["results"]} == {word}
            observed["project_scopes"][word] = scoped
        observed["old_references"] = []
        for conversation_id, message_id in origins.items():
            original = call(
                "read",
                {
                    "hub_id": hub_id,
                    "conversation_id": conversation_id,
                    "message_id": message_id,
                },
            )
            assert (
                len(original["messages"]) == 1
                and original["messages"][0]["hub_message_id"] == message_id
            )
            observed["old_references"].append(original)
        print(
            "PASS: real prior Hub archive migrated in place; distinct scope, identities and old message references verified."
        )
    finally:
        stop()

save_report(args, observed, identities)
