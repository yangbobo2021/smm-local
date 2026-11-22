"""Versioned, durable per-device upload decisions, independent of search."""
from contextlib import contextmanager
import json
from uuid import uuid4

from fastapi import HTTPException

from ._archive import ControlConflict, ControlGuard, control_lock, digest, normalize_policy, permits


def conflict(code: str, message: str):
    raise HTTPException(409, {"code": code, "message": message})


class HubUpload:
    def __init__(self, archive, hub_id):
        self.db = archive
        self.hub_id = hub_id
        self.guard = ControlGuard(archive.db_path)
        with archive.connect() as con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS hub_upload_policies (
                    device_id TEXT PRIMARY KEY, revision INTEGER NOT NULL,
                    policy TEXT NOT NULL, submission_id TEXT NOT NULL, control_epoch TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS hub_policy_submissions (
                    device_id TEXT NOT NULL, submission_id TEXT NOT NULL,
                    digest TEXT NOT NULL, receipt TEXT NOT NULL,
                    PRIMARY KEY(device_id,submission_id)
                );
                CREATE TABLE IF NOT EXISTS hub_upload_batches (
                    device_id TEXT NOT NULL, batch_id TEXT NOT NULL, digest TEXT NOT NULL,
                    accepted INTEGER NOT NULL, control_epoch TEXT NOT NULL,
                    PRIMARY KEY(device_id,batch_id)
                );
            """)
        with control_lock(self.guard.lock):
            if not self.guard.path.exists():
                with self.db.connect() as con:
                    adopted = con.execute("SELECT 1 FROM hub_upload_policies LIMIT 1").fetchone()
                if not adopted:
                    self.guard.write({"format": 1, "archive_id": hub_id, "control_epoch": uuid4().hex,
                                      "restore_pending": False, "devices": {}})

    def _guard(self):
        try:
            value = self.guard.read()
            if value["archive_id"] != self.hub_id:
                raise ControlConflict("Hub 与保护状态身份不一致")
            return value
        except ControlConflict as exc:
            conflict("control_conflict", str(exc))

    @staticmethod
    def _row(con, device):
        row = con.execute("SELECT * FROM hub_upload_policies WHERE device_id=?", (device,)).fetchone()
        if row is None:
            return {"revision": 0, "policy": None, "submission_id": None, "control_epoch": None}
        return {**dict(row), "policy": json.loads(row["policy"])}

    def _recover_committed(self, con, guard, device):
        protected = guard["devices"].get(device, {})
        pending = protected.get("pending")
        row = self._row(con, device)
        if pending and all(row[k] == pending[k] for k in ("revision", "policy", "submission_id", "control_epoch")):
            guard["devices"][device] = {**pending, "legacy_locked": True,
                                         "reconciled_epoch": guard["control_epoch"]}
            self.guard.write(guard)
        return row

    def _status(self, con, guard, device):
        row = self._recover_committed(con, guard, device)
        protected = guard["devices"].get(device, {})
        selected = protected if protected.get("revision", 0) > row["revision"] else row
        mismatch = bool(protected.get("pending") or (protected.get("revision", 0) != row["revision"])
                        or (row["revision"] and any(protected.get(k) != row[k]
                            for k in ("policy", "submission_id", "control_epoch"))))
        needs_restore = guard.get("restore_pending", False) and protected.get("reconciled_epoch") != guard["control_epoch"]
        return {"hub_id": self.hub_id, "device_id": device, "revision": selected["revision"],
                "policy": selected["policy"], "submission_id": selected.get("submission_id"),
                "control_epoch": guard["control_epoch"], "restore_pending": needs_restore,
                "conflict": mismatch or needs_restore}

    def status(self, device):
        with control_lock(self.guard.lock):
            guard = self._guard()
            with self.db.connect() as con:
                return self._status(con, guard, device)

    def set(self, device, policy, expected_revision, submission_id, *, reconcile=False):
        policy = normalize_policy(policy)
        with control_lock(self.guard.lock):
            guard = self._guard()
            with self.db.connect() as con:
                con.execute("BEGIN IMMEDIATE")
                current = self._status(con, guard, device)
                old = con.execute("SELECT digest,receipt FROM hub_policy_submissions WHERE device_id=? AND submission_id=?",
                                  (device, submission_id)).fetchone()
                if old:
                    if old[0] != digest(policy):
                        conflict("submission_conflict", "同一提交标识不能替换为另一条规则")
                    receipt = json.loads(old[1])
                    if receipt["control_epoch"] == guard["control_epoch"]:
                        return {**receipt, "head_revision": current["revision"]}
                if expected_revision != current["revision"]:
                    conflict("stale_policy", "上传规则已改变，请重新查看差异")
                if current["conflict"] and not reconcile:
                    pending = guard["devices"].get(device, {}).get("pending")
                    if not pending or pending["submission_id"] != submission_id:
                        conflict("restore_pending", "恢复或提交状态待确认，请明确对账")
                receipt = {"hub_id": self.hub_id, "device_id": device,
                           "revision": current["revision"] + 1, "policy": policy,
                           "submission_id": submission_id, "control_epoch": guard["control_epoch"]}
                protected = guard["devices"].setdefault(device, {})
                protected["pending"] = receipt
                self.guard.write(guard)
                con.execute("INSERT INTO hub_upload_policies VALUES(?,?,?,?,?) ON CONFLICT(device_id) DO UPDATE SET revision=excluded.revision,policy=excluded.policy,submission_id=excluded.submission_id,control_epoch=excluded.control_epoch",
                            (device, receipt["revision"], json.dumps(policy), submission_id, guard["control_epoch"]))
                con.execute("INSERT INTO hub_policy_submissions VALUES(?,?,?,?) ON CONFLICT(device_id,submission_id) DO UPDATE SET receipt=excluded.receipt",
                            (device, submission_id, digest(policy), json.dumps(receipt)))
            guard["devices"][device] = {**receipt, "legacy_locked": True,
                                         "reconciled_epoch": guard["control_epoch"]}
            self.guard.write(guard)
            return receipt

    def _check(self, con, guard, device, revision, epoch):
        row = self._recover_committed(con, guard, device)
        protected = guard["devices"].get(device, {})
        managed = bool(row["revision"] or protected.get("legacy_locked") or protected.get("pending"))
        if guard.get("restore_pending") and protected.get("reconciled_epoch") != guard["control_epoch"]:
            conflict("restore_pending", "Hub 恢复后须先对账，正文接收已停止")
        if not managed:
            return None
        if revision is None:
            conflict("policy_required", "此设备已采用上传规则，不能使用旧式正文请求")
        if (protected.get("pending") or any(protected.get(k) != row[k]
                for k in ("revision", "policy", "submission_id", "control_epoch"))
                or epoch != guard["control_epoch"] or row["control_epoch"] != epoch
                or revision != row["revision"]):
            conflict("stale_policy", "上传规则版本或恢复代次已改变，请先同步规则")
        return row["policy"]

    def prepare_restore(self):
        with control_lock(self.guard.lock):
            try:
                guard = self.guard.read()
            except ControlConflict:
                guard = {"format": 1, "archive_id": self.hub_id, "devices": {}}
            if guard["archive_id"] != self.hub_id:
                raise ValueError("Hub 与保护文件身份不同，请核对恢复目录")
            with self.db.connect() as con:
                for row in con.execute("SELECT * FROM hub_upload_policies"):
                    old = guard["devices"].get(row["device_id"], {})
                    if row["revision"] >= old.get("revision", 0):
                        guard["devices"][row["device_id"]] = {
                            **dict(row), "policy": json.loads(row["policy"]), "legacy_locked": True,
                            "reconciled_epoch": row["control_epoch"]}
            guard.update(control_epoch=uuid4().hex, restore_pending=True)
            self.guard.write(guard)
        return {"body_stopped": True, "hub_id": self.hub_id, "control_epoch": guard["control_epoch"],
                "restore_files": [str(self.db.db_path.resolve())],
                "do_not_restore": [str(self.guard.path), str(self.guard.lock)],
                "next": "停止 Hub 服务，按清单恢复一致性备份并重启；客户端查看 upload reconcile 后明确确认"}

    @contextmanager
    def transaction(self, batch, *, metadata=False):
        with control_lock(self.guard.lock):
            guard = self._guard()
            with self.db.connect() as con:
                con.execute("BEGIN IMMEDIATE")
                records = [] if metadata else batch.records
                memberships = batch.memberships if metadata else []
                # Empty device/project registration is independent of body permission.
                policy = None
                if records or memberships:
                    policy = self._check(con, guard, batch.device_id, batch.policy_revision, batch.control_epoch)
                if policy is not None:
                    for record in records or memberships:
                        key = str(record.project_id) if record.project_id is not None else None
                        if not permits(policy, key):
                            raise HTTPException(403, {"code": "project_disabled", "message": "该项目不允许上传"})
                        if not con.execute("SELECT 1 FROM hub_projects WHERE kind='device' AND owner=? AND source_key=?",
                                           (batch.device_id, key)).fetchone():
                            conflict("unknown_project", "设备需先登记稳定项目身份")
                if not metadata and batch.batch_id:
                    batch_digest = digest([r.model_dump() for r in records])
                    prior = con.execute("SELECT digest FROM hub_upload_batches WHERE device_id=? AND batch_id=?",
                                        (batch.device_id, batch.batch_id)).fetchone()
                    if prior and prior[0] != batch_digest:
                        conflict("batch_conflict", "同一批次标识不能替换为其他内容")
                yield con
                if not metadata and batch.batch_id:
                    con.execute("INSERT OR IGNORE INTO hub_upload_batches VALUES(?,?,?,?,?)",
                                (batch.device_id, batch.batch_id, batch_digest, len(records), guard["control_epoch"]))
