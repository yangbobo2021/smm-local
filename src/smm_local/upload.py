"""Local upload choice, durable receipts, and policy reconciliation."""
from __future__ import annotations

import json
from uuid import uuid4

from .archive_protocol import (ControlConflict, ControlGuard, control_lock, digest,
                               legacy_message_key, message_version, normalize_policy, permits)


class LocalUpload:
    def __init__(self, db, config: dict, hub_id: str):
        self.db, self.config, self.hub_id = db, config, hub_id
        self.device = config["device_id"]
        self.key = hub_id + ":" + self.device
        self.guard = ControlGuard(db.db_path)
        with db.connect() as con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS local_upload_policies (
                    hub_id TEXT NOT NULL, device_id TEXT NOT NULL,
                    desired TEXT, generation INTEGER NOT NULL DEFAULT 0,
                    submission_id TEXT, ack_revision INTEGER NOT NULL DEFAULT 0,
                    ack_epoch TEXT, ack_generation INTEGER NOT NULL DEFAULT -1,
                    state TEXT NOT NULL DEFAULT 'needs_selection', problem TEXT,
                    remote TEXT, next_project TEXT,
                    PRIMARY KEY(hub_id,device_id)
                );
                CREATE TABLE IF NOT EXISTS local_upload_submissions (
                    hub_id TEXT NOT NULL, device_id TEXT NOT NULL, submission_id TEXT NOT NULL,
                    generation INTEGER NOT NULL, PRIMARY KEY(hub_id,device_id,submission_id)
                );
                CREATE TABLE IF NOT EXISTS upload_message_catalog (
                    message_id INTEGER PRIMARY KEY REFERENCES messages(id) ON DELETE CASCADE,
                    logical_id TEXT NOT NULL, version TEXT NOT NULL,
                    source_order INTEGER NOT NULL, occurrence INTEGER
                );
                CREATE TRIGGER IF NOT EXISTS invalidate_upload_catalog AFTER UPDATE OF source_key,role,text,timestamp,position ON messages
                BEGIN DELETE FROM upload_message_catalog WHERE message_id=new.id; END;
                CREATE TABLE IF NOT EXISTS local_upload_receipts (
                    hub_id TEXT NOT NULL, device_id TEXT NOT NULL,
                    logical_id TEXT NOT NULL, version TEXT NOT NULL, control_epoch TEXT NOT NULL,
                    PRIMARY KEY(hub_id,device_id,logical_id,version,control_epoch)
                );
                CREATE TABLE IF NOT EXISTS local_upload_origin_receipts (
                    hub_id TEXT NOT NULL, device_id TEXT NOT NULL,
                    logical_id TEXT NOT NULL, version TEXT NOT NULL, control_epoch TEXT NOT NULL,
                    source_position INTEGER NOT NULL, source_order INTEGER NOT NULL,
                    PRIMARY KEY(hub_id,device_id,logical_id,version,control_epoch,source_position,source_order)
                );
                CREATE TABLE IF NOT EXISTS local_upload_project_receipts (
                    hub_id TEXT NOT NULL, device_id TEXT NOT NULL,
                    logical_id TEXT NOT NULL, version TEXT NOT NULL, control_epoch TEXT NOT NULL,
                    project_key TEXT NOT NULL, source_position INTEGER NOT NULL, source_order INTEGER NOT NULL,
                    PRIMARY KEY(hub_id,device_id,logical_id,version,control_epoch,project_key,source_position,source_order)
                );
                CREATE TABLE IF NOT EXISTS local_upload_transfer (
                    hub_id TEXT NOT NULL, device_id TEXT NOT NULL,
                    last_attempt TEXT, last_success TEXT, problem TEXT,
                    PRIMARY KEY(hub_id,device_id)
                );
                CREATE TRIGGER IF NOT EXISTS invalidate_conversation_upload_identity
                AFTER UPDATE OF source,source_session_id ON conversations
                BEGIN DELETE FROM upload_message_catalog WHERE message_id IN
                    (SELECT id FROM messages WHERE conversation_id=new.id); END;
                CREATE TABLE IF NOT EXISTS local_upload_batches (
                    hub_id TEXT NOT NULL, device_id TEXT NOT NULL, batch_id TEXT NOT NULL,
                    generation INTEGER NOT NULL, control_epoch TEXT NOT NULL,
                    policy_revision INTEGER NOT NULL, digest TEXT NOT NULL,
                    payload TEXT, state TEXT NOT NULL,
                    PRIMARY KEY(hub_id,device_id,batch_id)
                );
            """)
            identity = con.execute("SELECT value FROM settings WHERE key='archive:identity'").fetchone()
            existing = con.execute("SELECT 1 FROM local_upload_policies WHERE hub_id=? AND device_id=?", (hub_id, self.device)).fetchone()
            if identity and existing:
                self.archive_id = json.loads(identity[0])
                return
        with control_lock(self.guard.lock):
            with db.connect() as con:
                con.execute("BEGIN IMMEDIATE")
                identity = con.execute("SELECT value FROM settings WHERE key='archive:identity'").fetchone()
                if not identity:
                    value = self.guard.read()["archive_id"] if self.guard.path.exists() else uuid4().hex
                    con.execute("INSERT INTO settings VALUES('archive:identity',?)", (json.dumps(value),))
                else:
                    value = json.loads(identity[0])
                self.archive_id = value
                existed = con.execute("SELECT 1 FROM local_upload_policies LIMIT 1").fetchone()
                con.execute("INSERT OR IGNORE INTO local_upload_policies(hub_id,device_id) VALUES(?,?)", (hub_id, self.device))
                if not self.guard.path.exists() and not existed:
                    self.guard.write({"format": 1, "archive_id": value, "control_epoch": uuid4().hex,
                                      "restore_pending": False, "devices": {}})
                if self.guard.path.exists():
                    guard = self.guard.read()
                    if guard["archive_id"] == value and self.key not in guard["devices"]:
                        guard["devices"][self.key] = {"generation": 0, "desired": None, "submission_id": None,
                                                       "reconciled_epoch": guard["control_epoch"]}
                        self.guard.write(guard)

    def row(self, con=None):
        if con is None:
            with self.db.connect() as connection:
                return self.row(connection)
        row = dict(con.execute("SELECT * FROM local_upload_policies WHERE hub_id=? AND device_id=?", (self.hub_id, self.device)).fetchone())
        for field in ("desired", "remote"):
            row[field] = json.loads(row[field]) if row[field] else None
        return row

    def _verify(self, row, *, allow_reconcile=False):
        try:
            guard = self.guard.read()
        except ControlConflict:
            if not allow_reconcile:
                raise
            guard = {"format": 1, "archive_id": self.archive_id, "control_epoch": uuid4().hex,
                     "restore_pending": True, "devices": {}}
        if guard["archive_id"] != self.archive_id:
            raise ControlConflict("档案身份不同，请恢复同一档案的完整备份集")
        entry = guard["devices"].get(self.key)
        if (guard["archive_id"] != self.archive_id or not entry
                or entry.get("pending") or any(entry.get(k) != row[k] for k in ("generation", "desired", "submission_id"))
                or (guard.get("restore_pending") and entry.get("reconciled_epoch") != guard["control_epoch"])):
            if not allow_reconcile:
                raise ControlConflict("本机恢复或规则状态不一致，正文已停止，请先查看上传差异")
        return guard

    def _verify_target(self):
        path = self.db.db_path.resolve().with_suffix(self.db.db_path.suffix + '.hub.json')
        try:
            same_target = json.loads(path.read_text(encoding='utf-8')) == self.config
        except (OSError, ValueError):
            same_target = False
        if not same_target:
            raise ValueError("Hub 连接已改变，请重新查看对账差异")

    def _save(self, policy, *, expected_generation=None, reconcile=False, expected_hub_revision=None):
        policy = normalize_policy(policy)
        with control_lock(self.guard.lock):
            with self.db.connect() as con:
                con.execute("BEGIN IMMEDIATE")
                row = self.row(con)
                guard = self._verify(row, allow_reconcile=reconcile)
                if reconcile:
                    self._verify_target()
                if expected_generation is not None and expected_generation != row["generation"]:
                    raise ValueError("本机规则已改变，请重新查看")
                generation = max(row["generation"], guard["devices"].get(self.key, {}).get("generation", 0)) + 1
                submission = uuid4().hex
                pending = {"generation": generation, "desired": policy, "submission_id": submission,
                           "reconciled_epoch": guard["control_epoch"]}
                guard["devices"].setdefault(self.key, {})["pending"] = pending
                self.guard.write(guard)
                con.execute("UPDATE local_upload_policies SET desired=?,generation=?,submission_id=?,state='pending',problem=NULL WHERE hub_id=? AND device_id=?",
                            (json.dumps(policy), generation, submission, self.hub_id, self.device))
                if expected_hub_revision is not None:
                    con.execute("UPDATE local_upload_policies SET ack_revision=? WHERE hub_id=? AND device_id=?",
                                (expected_hub_revision, self.hub_id, self.device))
                con.execute("INSERT INTO local_upload_submissions VALUES(?,?,?,?)", (self.hub_id, self.device, submission, generation))
            guard["devices"][self.key] = pending
            self.guard.write(guard)

    def choose(self, mode: str, project_ids: list[int], *, expected_generation=None):
        projects = {p["id"]: p for p in self.db.projects()}
        if any(type(i) is not int or i not in projects for i in project_ids):
            raise ValueError("请选择本机项目列表中的项目 ID")
        self._save({"mode": mode, "projects": [projects[i]["stable_key"] for i in project_ids]},
                   expected_generation=expected_generation)

    def _mark(self, state, problem=None):
        with self.db.connect() as con:
            con.execute("UPDATE local_upload_policies SET state=?,problem=? WHERE hub_id=? AND device_id=?",
                        (state, problem, self.hub_id, self.device))

    def sync_policy(self, request, *, reconcile=False, expected_hub_revision=None):
        """Control traffic is independent of pause and never carries dialogue."""
        for _ in range(5):
            with control_lock(self.guard.lock):
                row = self.row()
                self._verify(row)
                self._verify_target()
            remote = request(self.config, "/upload-policy/status", {"hub_id": self.hub_id, "device_id": self.device})
            if remote.get("hub_id") != self.hub_id or remote.get("device_id") != self.device:
                raise ControlConflict("Hub 规则确认的目标身份不匹配")
            with control_lock(self.guard.lock):
                with self.db.connect() as con:
                    con.execute("BEGIN IMMEDIATE")
                    current = self.row(con)
                    # Control dispatch fence: a later connection change is an
                    # in-flight request, not permission for another new send.
                    self._verify_target()
                    if current["generation"] != row["generation"]:
                        continue
                    self._verify(current)
                    con.execute("UPDATE local_upload_policies SET remote=? WHERE hub_id=? AND device_id=?",
                                (json.dumps(remote), self.hub_id, self.device))
                    if row["desired"] is None:
                        con.execute("UPDATE local_upload_policies SET state='needs_selection' WHERE hub_id=? AND device_id=?",
                                    (self.hub_id, self.device))
                        return remote
                    if (remote.get("submission_id") == row["submission_id"] and remote["policy"] == row["desired"]
                            and not remote.get("conflict")):
                        if row["ack_epoch"] != remote["control_epoch"] and con.execute("SELECT 1 FROM sqlite_master WHERE name='hub_metadata_uploads'").fetchone():
                            con.execute("DELETE FROM hub_metadata_uploads WHERE hub_id=? AND device_id=?", (self.hub_id, self.device))
                        con.execute("UPDATE local_upload_policies SET ack_revision=?,ack_epoch=?,ack_generation=?,state='confirmed',problem=NULL WHERE hub_id=? AND device_id=?",
                                    (remote["revision"], remote["control_epoch"], row["generation"], self.hub_id, self.device))
                        return remote
                    if expected_hub_revision is not None and remote["revision"] != expected_hub_revision:
                        raise ControlConflict("Hub 规则已改变，请重新查看差异")
                    known = con.execute("SELECT generation FROM local_upload_submissions WHERE hub_id=? AND device_id=? AND submission_id=?",
                                        (self.hub_id, self.device, remote.get("submission_id"))).fetchone()
                    compatible = (remote["revision"] == row["ack_revision"] and
                                  (not row["ack_epoch"] or row["ack_epoch"] == remote["control_epoch"]))
                    own_prior = known and known[0] < row["generation"] and not remote.get("conflict")
                    if not reconcile and (remote.get("conflict") or not (compatible or own_prior)):
                        con.execute("UPDATE local_upload_policies SET state='conflict',problem=? WHERE hub_id=? AND device_id=?",
                                    ("Hub 与本机规则不一致，请查看差异", self.hub_id, self.device))
                        return remote
            receipt = request(self.config, "/upload-policy/set", {
                "hub_id": self.hub_id, "device_id": self.device, "policy": row["desired"],
                "expected_revision": remote["revision"], "submission_id": row["submission_id"], "reconcile": reconcile})
            if (receipt.get("hub_id") != self.hub_id or receipt.get("device_id") != self.device
                    or receipt.get("submission_id") != row["submission_id"] or receipt.get("policy") != row["desired"]):
                raise ControlConflict("Hub 未确认当前规则")
            # Read the authoritative head again: a newer local save may already exist.
        self._mark("pending", "规则仍在协调，下一轮继续")
        return None

    def reconcile(self, request, use=None, expected_hub_revision=None, expected_local_generation=None):
        if use not in {None, "local", "hub"}:
            raise ValueError("请选择 local 或 hub")
        if use == "local" and (expected_hub_revision is None or expected_local_generation is None):
            raise ValueError("重新提交本机规则必须提供刚查看的 hub.revision 和 local.generation")
        for value, label in ((expected_hub_revision, "Hub 版本"), (expected_local_generation, "本机代次")):
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError(label + "必须为非负整数，请重新查看差异")
        local = self.row()
        if expected_local_generation is not None and expected_local_generation != local["generation"]:
            raise ValueError("本机规则已改变，请重新查看对账差异")
        remote = request(self.config, "/upload-policy/status", {"hub_id": self.hub_id, "device_id": self.device})
        if use is None:
            return {"local": self.status(), "hub": remote}
        if expected_hub_revision is not None and expected_hub_revision != remote["revision"]:
            raise ControlConflict("Hub 规则已改变，请重新查看差异")
        policy = remote["policy"] if use == "hub" else local["desired"]
        if policy is None and use == "hub":
            policy = {"mode": "none", "projects": []}
        if policy is None:
            raise ValueError("尚无可采用的规则，请先明确选择上传范围")
        self._save(policy, expected_generation=local["generation"], reconcile=True,
                   expected_hub_revision=remote["revision"])
        self.sync_policy(request, reconcile=True, expected_hub_revision=remote["revision"])
        return self.status()

    def catalog(self, limit=25000):
        """Index missing/changed identities, independently of every Hub cursor."""
        with self.db.connect() as con:
            missing = con.execute("SELECT m.id,m.conversation_id FROM messages m JOIN conversations c ON c.id=m.conversation_id LEFT JOIN upload_message_catalog u ON u.message_id=m.id WHERE c.source IN ('codex','claude-code') AND u.message_id IS NULL ORDER BY m.id LIMIT ?", (limit,)).fetchall()
            if not missing:
                return 0
            conversations = tuple(sorted({r[1] for r in missing}))
            for start in range(0, len(conversations), 400):
                group = conversations[start:start + 400]
                marks = ",".join("?" for _ in group)
                rows = con.execute(f"""
                SELECT m.*,c.source,c.source_session_id,
                    ROW_NUMBER() OVER (PARTITION BY c.id ORDER BY m.position,m.id) AS source_order,
                    ROW_NUMBER() OVER (PARTITION BY c.id,m.role,m.text,m.timestamp,
                        (m.source_key LIKE 'offset:%') ORDER BY m.position,m.id) AS occurrence
                FROM messages m JOIN conversations c ON c.id=m.conversation_id
                WHERE c.id IN ({marks})
                """, group).fetchall()
                for r in rows:
                    record = dict(r)
                    occurrence = r["occurrence"] if r["source_key"].startswith("offset:") else None
                    record["occurrence"] = occurrence
                    logical = digest([r["source"], r["source_session_id"], legacy_message_key(record)])
                    con.execute("INSERT OR REPLACE INTO upload_message_catalog VALUES(?,?,?,?,?)",
                                (r["id"], logical, message_version(record), r["source_order"], occurrence))
            return len(missing)

    def catalog_pending(self):
        with self.db.connect() as con:
            return bool(con.execute("SELECT 1 FROM messages m JOIN conversations c ON c.id=m.conversation_id LEFT JOIN upload_message_catalog u ON u.message_id=m.id WHERE c.source IN ('codex','claude-code') AND u.message_id IS NULL LIMIT 1").fetchone())

    def candidates(self, epoch, limit=100):
        row = self.row()
        if row["desired"] is None:
            return []
        projects = [p for p in self.db.projects() if permits(row["desired"], p["stable_key"])]
        projects.sort(key=lambda p: p["stable_key"])
        after = row["next_project"] or ""
        projects = [p for p in projects if p["stable_key"] > after] + [p for p in projects if p["stable_key"] <= after]
        with self.db.connect() as con:
            for project in projects:
                rows = con.execute("""
                    SELECT m.id AS seq,m.source_key,m.position,m.role,m.text,m.timestamp,
                           c.source,c.source_session_id,c.started_at,u.logical_id,u.version,u.source_order,u.occurrence
                    FROM upload_message_catalog u JOIN messages m ON m.id=u.message_id
                    JOIN conversations c ON c.id=m.conversation_id
                    LEFT JOIN local_upload_project_receipts a ON a.hub_id=? AND a.device_id=?
                        AND a.logical_id=u.logical_id AND a.version=u.version AND a.control_epoch=?
                        AND a.project_key=?
                        AND a.source_position=m.position AND a.source_order=u.source_order
                    WHERE c.project_id=? AND c.source IN ('codex','claude-code') AND a.logical_id IS NULL
                    ORDER BY m.id LIMIT ?
                """, (self.hub_id, self.device, epoch, project["stable_key"], project["id"], limit)).fetchall()
                if rows:
                    con.execute("UPDATE local_upload_policies SET next_project=? WHERE hub_id=? AND device_id=?",
                                (project["stable_key"], self.hub_id, self.device))
                    return [{**dict(r), "project_id": project["stable_key"]} for r in rows]
        return []

    def transfer_result(self, problem=None):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        with self.db.connect() as con:
            con.execute("""INSERT INTO local_upload_transfer VALUES(?,?,?,?,?)
                ON CONFLICT(hub_id,device_id) DO UPDATE SET last_attempt=excluded.last_attempt,
                last_success=COALESCE(excluded.last_success,local_upload_transfer.last_success),problem=excluded.problem""",
                (self.hub_id, self.device, now, None if problem else now, problem))

    def status(self):
        row = self.row()
        problem = row["problem"]
        state = row["state"]
        try:
            self._verify(row)
        except ControlConflict as exc:
            state, problem = "conflict", str(exc)
        with self.db.connect() as con:
            total = con.execute("SELECT COUNT(*) FROM messages m JOIN conversations c ON c.id=m.conversation_id WHERE c.source IN ('codex','claude-code')").fetchone()[0]
            confirmed = con.execute("SELECT COUNT(*) FROM upload_message_catalog u JOIN local_upload_receipts a ON a.logical_id=u.logical_id AND a.version=u.version WHERE a.hub_id=? AND a.device_id=? AND a.control_epoch=?",
                                    (self.hub_id, self.device, row["ack_epoch"])).fetchone()[0]
            acknowledged = {(r[0], r[1]) for r in con.execute("SELECT logical_id,version FROM local_upload_receipts WHERE hub_id=? AND device_id=? AND control_epoch=?", (self.hub_id, self.device, row["ack_epoch"]))}
            outstanding = set()
            for batch in con.execute("SELECT payload FROM local_upload_batches WHERE hub_id=? AND device_id=? AND state IN ('sending','unknown') AND payload IS NOT NULL", (self.hub_id, self.device)):
                outstanding.update((r["logical_id"], r["version"]) for r in json.loads(batch[0]))
            inflight = len(outstanding - acknowledged)
            pending = 0
            for record in con.execute("""SELECT m.id,k.remote_key,a.logical_id FROM messages m
                JOIN conversations c ON c.id=m.conversation_id
                LEFT JOIN hub_local_project_keys k ON k.id=c.project_id
                LEFT JOIN upload_message_catalog u ON u.message_id=m.id
                LEFT JOIN local_upload_project_receipts a ON a.hub_id=? AND a.device_id=?
                    AND a.logical_id=u.logical_id AND a.version=u.version AND a.control_epoch=?
                    AND a.project_key=k.remote_key
                    AND a.source_position=m.position AND a.source_order=u.source_order
                WHERE c.source IN ('codex','claude-code')""", (self.hub_id, self.device, row['ack_epoch'])):
                if record['logical_id'] is None and permits(row['desired'], record['remote_key']):
                    pending += 1
            transfer = con.execute("SELECT * FROM local_upload_transfer WHERE hub_id=? AND device_id=?",
                                   (self.hub_id, self.device)).fetchone()
        transfer_problem = transfer['problem'] if transfer else None
        transfer_state = ('paused' if self.db.get_settings()['sync_paused'] else
                          'blocked' if state != 'confirmed' else
                          'failed' if transfer_problem else 'unknown' if inflight else
                          'backfilling' if pending else 'complete')
        return {"configured": True, "hub_id": self.hub_id, "device_id": self.device,
                "hub_address": self.config["address"], "device_name": self.config["device_name"],
                "policy": row["desired"], "generation": row["generation"], "state": state,
                "hub_revision": row["ack_revision"], "control_epoch": row["ack_epoch"],
                "confirmed_messages": confirmed, "not_confirmed_messages": total - confirmed,
                "inflight_messages": inflight, "unsent_messages": max(0, total - confirmed - inflight),
                "problem": problem, "remote": row["remote"],
                "transfer_state": transfer_state, "transfer_problem": transfer_problem,
                "allowed_pending_messages": pending,
                "last_transfer_attempt": transfer['last_attempt'] if transfer else None,
                "last_transfer_success": transfer['last_success'] if transfer else None}

    def _eligible(self, con, row, rows, expected_generation=None):
        path = self.db.db_path.resolve().with_suffix(self.db.db_path.suffix + '.hub.json')
        try:
            current_config = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return False
        if (current_config != self.config or self.db.get_settings()['sync_paused']
                or row['state'] != 'confirmed' or row['ack_generation'] != row['generation']
                or (expected_generation is not None and row['generation'] != expected_generation)):
            return False
        for message in rows:
            actual = con.execute("""SELECT m.*,c.source,c.source_session_id,k.remote_key,
                u.logical_id,u.version,u.source_order,u.occurrence FROM messages m
                JOIN conversations c ON c.id=m.conversation_id
                LEFT JOIN hub_local_project_keys k ON k.id=c.project_id
                LEFT JOIN upload_message_catalog u ON u.message_id=m.id WHERE m.id=?""", (message['seq'],)).fetchone()
            if (actual is None or actual['remote_key'] != message['project_id']
                    or not permits(row['desired'], actual['remote_key'])
                    or any(actual[k] != message[k] for k in ('source', 'source_session_id', 'source_key',
                           'position', 'logical_id', 'version', 'source_order', 'occurrence'))
                    or message_version(dict(actual)) != message['version']):
                return False
            # A newly imported earlier turn can change existing offset occurrences.
            if con.execute("""SELECT 1 FROM messages m LEFT JOIN upload_message_catalog u ON u.message_id=m.id
                WHERE m.conversation_id=? AND u.message_id IS NULL LIMIT 1""", (actual['conversation_id'],)).fetchone():
                return False
        return True

    def eligible(self, rows, generation):
        with control_lock(self.guard.lock):
            with self.db.connect() as con:
                con.execute('BEGIN IMMEDIATE')
                row = self.row(con)
                self._verify(row)
                return self._eligible(con, row, rows, generation)

    def dispatch(self, rows):
        with control_lock(self.guard.lock):
            with self.db.connect() as con:
                con.execute("BEGIN IMMEDIATE")
                row = self.row(con)
                self._verify(row)
                if not self._eligible(con, row, rows):
                    return None
                batch = {"hub_id": self.hub_id, "device_id": self.device,
                         "device_name": self.config["device_name"], "batch_id": uuid4().hex,
                         "policy_revision": row["ack_revision"], "control_epoch": row["ack_epoch"],
                         "records": [wire_record(m) for m in rows]}
                con.execute("INSERT INTO local_upload_batches VALUES(?,?,?,?,?,?,?,?,?)",
                            (self.hub_id, self.device, batch["batch_id"], row["generation"], row["ack_epoch"],
                             row["ack_revision"], digest(batch["records"]), json.dumps(rows), "sending"))
                return batch

    def acknowledge(self, batch_id, receipt):
        with self.db.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            batch = con.execute("SELECT * FROM local_upload_batches WHERE hub_id=? AND device_id=? AND batch_id=?",
                                (self.hub_id, self.device, batch_id)).fetchone()
            if batch is None or batch["payload"] is None:
                return
            rows = json.loads(batch["payload"])
            if (receipt.get("hub_id") != self.hub_id or receipt.get("device_id") != self.device
                    or receipt.get("batch_id") != batch_id or receipt.get("accepted") != len(rows)
                    or receipt.get("control_epoch") != batch["control_epoch"]
                    or receipt.get("batch_digest") != batch["digest"]):
                raise ControlConflict("Hub 未确认本批次的准确身份及全部记录")
            self._record_receipts(con, rows, batch['control_epoch'])
            con.execute("UPDATE local_upload_batches SET state='confirmed',payload=NULL WHERE hub_id=? AND device_id=? AND batch_id=?",
                        (self.hub_id, self.device, batch_id))

    def _record_receipts(self, con, rows, epoch):
        con.executemany('INSERT OR IGNORE INTO local_upload_receipts VALUES(?,?,?,?,?)',
                        [(self.hub_id, self.device, r['logical_id'], r['version'], epoch) for r in rows])
        con.executemany('INSERT OR IGNORE INTO local_upload_project_receipts VALUES(?,?,?,?,?,?,?,?)',
                        [(self.hub_id, self.device, r['logical_id'], r['version'], epoch,
                          r['project_id'], r['position'], r['source_order']) for r in rows])

    def acknowledge_known(self, rows, verified, epoch):
        with self.db.connect() as con:
            self._record_receipts(con, [r for r in rows if (r['logical_id'], r['version']) in verified], epoch)

    def resolve_unknown(self, request):
        with self.db.connect() as con:
            batches = con.execute("SELECT * FROM local_upload_batches WHERE hub_id=? AND device_id=? AND state IN ('sending','unknown') ORDER BY rowid LIMIT 100", (self.hub_id, self.device)).fetchall()
        if not batches:
            return
        result = request(self.config, "/upload-receipts", {"hub_id": self.hub_id, "device_id": self.device,
                                                          "batch_ids": [b["batch_id"] for b in batches]})
        receipts = {r["batch_id"]: r for r in result["receipts"]}
        for batch in batches:
            receipt = receipts.get(batch["batch_id"])
            if receipt:
                self.acknowledge(batch["batch_id"], receipt)
            elif (result["control_epoch"] != batch["control_epoch"]
                  or result["revision"] > batch["policy_revision"]):
                with self.db.connect() as con:
                    con.execute("UPDATE local_upload_batches SET state='rejected',payload=NULL WHERE hub_id=? AND device_id=? AND batch_id=?",
                                (self.hub_id, self.device, batch["batch_id"]))

    def prepare_restore(self):
        with control_lock(self.guard.lock):
            try:
                value = self.guard.read()
            except ControlConflict:
                value = {"format": 1, "archive_id": self.archive_id, "devices": {}}
                with self.db.connect() as con:
                    for row in con.execute("SELECT * FROM local_upload_policies"):
                        value["devices"][row["hub_id"] + ":" + row["device_id"]] = {
                            "generation": row["generation"], "desired": json.loads(row["desired"]) if row["desired"] else None,
                            "submission_id": row["submission_id"]}
            if value["archive_id"] != self.archive_id:
                raise ValueError("档案与保护文件身份不同，请核对恢复目录")
            value.update(control_epoch=uuid4().hex, restore_pending=True)
            self.guard.write(value)
        return {"body_stopped": True, "archive_id": self.archive_id, "control_epoch": value["control_epoch"],
                "inflight_messages": self.status()["inflight_messages"],
                "restore_files": [str(self.db.db_path.resolve()), str(self.db.db_path.resolve()) + ".hub.json"],
                "do_not_restore": [str(self.guard.path), str(self.guard.lock)],
                "next": "已停止新正文发送；在途请求仍待确认。停止本机服务，按清单恢复一致性备份并重启，再查看 upload reconcile"}


def wire_record(record):
    return {key: record.get(key) for key in ("source", "source_session_id", "started_at", "source_key",
            "position", "role", "text", "timestamp", "occurrence", "source_order", "project_id")}
