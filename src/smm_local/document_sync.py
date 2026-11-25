"""Project opt-in document transfer, durable fences and withdrawal-only control.

All network calls occur after releasing SQLite transactions and control locks.
Only archived text is transferred; this module never scans an original source.
"""

from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import tempfile
from uuid import uuid4
from . import federation, references
from .archive_protocol import digest
from .document_protocol import DocumentGuard, identity, integer
from .documents import Documents


class DocumentSync:
    def __init__(self, db):
        self.db = db
        self.documents = Documents(db)
        with db.connect() as c:
            pristine = not c.execute(
                "SELECT 1 FROM sqlite_master WHERE name='local_document_sync'"
            ).fetchone()
            c.execute(
                "CREATE TABLE IF NOT EXISTS local_document_sync(target TEXT PRIMARY KEY,state TEXT NOT NULL)"
            )
        self.guard = DocumentGuard(db, ("local_document_sync",))
        self.guard.initialize(pristine)

    def _info(self):
        config = federation.hub_config(self.db)
        if not config:
            return None, None, "未配置Hub"
        try:
            info = federation._hub_info(config)
            if not any(
                c.startswith("documents-") for c in info.get("capabilities", [])
            ):
                return config, None, "Hub不支持文档同步"
            return config, info, None
        except federation.HubUnavailable as exc:
            return config, None, str(exc)

    def _prefix(self, config, hub_id):
        return (
            ":".join((hub_id, config["device_id"], references.material(self.db)[0]))
            + ":"
        )

    def _rows(self, config, hub_id):
        prefix = self._prefix(config, hub_id)
        with self.db.connect() as c:
            return {
                r["target"][len(prefix) :]: json.loads(r["state"])
                for r in c.execute(
                    "SELECT * FROM local_document_sync WHERE target LIKE ?",
                    (prefix + "%",),
                )
            }

    def _save(self, config, hub_id, key, value):
        with self.db.connect() as c:
            c.execute("BEGIN IMMEDIATE")
            c.execute(
                "INSERT INTO local_document_sync VALUES(?,?) ON CONFLICT(target) DO UPDATE SET state=excluded.state",
                (
                    self._prefix(config, hub_id) + key,
                    json.dumps(value, ensure_ascii=False),
                ),
            )

    @staticmethod
    def _default():
        return {
            "generation": 0,
            "enabled": False,
            "confirmed_generation": 0,
            "sequence": 0,
            "confirmed_sequence": 0,
            "control_digest": None,
            "known": {},
            "sources": {},
            "epoch": None,
            "blocked": False,
            "error": None,
            "dirty": False,
            "dirty_generation": 0,
        }

    def status(self):
        config, info, error = self._info()
        hub_id = info["hub_id"] if info else (config or {}).get("bound_hub_id")
        projects = self.db.projects()
        rows = self._rows(config, hub_id) if config and hub_id else {}
        protection = self.guard.status()
        result = []
        for p in projects:
            key = p["stable_key"]
            row = rows.pop(key, self._default())
            mismatch = bool(
                info and row["generation"] and row["epoch"] != info["document_epoch"]
            )
            blocked = bool(protection or row.get("blocked") or mismatch)
            pending = (
                row.get("dirty", False)
                or row["confirmed_generation"] != row["generation"]
                or row["confirmed_sequence"] != row["sequence"]
                or (
                    row["enabled"]
                    and any(
                        s.get("published") != s.get("signature")
                        for s in row["sources"].values()
                    )
                )
            )
            result.append(
                {
                    **row,
                    "project_id": p["id"],
                    "project_key": key,
                    "name": p["name"],
                    "hub_id": hub_id,
                    "pending": pending,
                    "conflict": blocked,
                    "state": (
                        "conflict"
                        if blocked
                        else (
                            "allowed"
                            if row["enabled"]
                            else ("paused" if row["generation"] else "default_off")
                        )
                    ),
                }
            )
        for key, row in rows.items():
            result.append(
                {
                    **row,
                    "project_id": None,
                    "project_key": key,
                    "name": row.get("name", "已删除项目"),
                    "hub_id": hub_id,
                    "pending": bool(row["known"])
                    or row["confirmed_generation"] != row["generation"],
                    "conflict": bool(protection or row.get("blocked")),
                    "state": "removed",
                }
            )
        return {
            "configured": bool(config),
            "hub_address": (config or {}).get("address"),
            "hub_id": hub_id,
            "projects": result,
            "pending": any(p["pending"] for p in result),
            "conflict": bool(protection),
            "project_conflicts": sum(bool(p["conflict"]) for p in result),
            "protection_error": protection,
            "error": error,
        }

    def choose(self, project_key, enabled, expected_hub_id, expected_generation):
        identity(project_key, "稳定项目键")
        integer(expected_generation, minimum=0)
        if type(enabled) is not bool:
            raise ValueError("enabled须为布尔值")
        config, info, error = self._info()
        hub_id = info["hub_id"] if info else (config or {}).get("bound_hub_id")
        if not config or not hub_id or expected_hub_id != hub_id:
            raise ValueError("Hub身份未知或已切换，请重新查看sync-status")
        projects = {p["stable_key"]: p for p in self.db.projects()}
        if project_key not in projects:
            raise ValueError("稳定项目身份已删除或被合并，请重新查看")
        remote_generation = 0
        if info:
            try:
                remote = federation._request(
                    config,
                    "/documents/status",
                    {
                        **{k: info[k] for k in ("hub_id", "document_epoch")},
                        "device_id": config["device_id"],
                        "archive_id": references.material(self.db)[0],
                    },
                )
                remote_generation = max(
                    (
                        r["generation"]
                        for r in remote["projects"]
                        if r["project_key"] == project_key
                    ),
                    default=0,
                )
            except federation.HubUnavailable:
                pass
        target = self._prefix(config, hub_id) + project_key
        with self.guard.hold(recover=True), self.db.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if federation.hub_config(self.db) != config:
                raise ValueError("Hub连接已改变，请重新查看")
            current_project = connection.execute(
                "SELECT p.name FROM projects p JOIN hub_local_project_keys k ON k.id=p.id WHERE k.remote_key=?",
                (project_key,),
            ).fetchone()
            if current_project is None:
                raise ValueError("稳定项目身份已删除或被合并，请重新查看")
            saved_row = connection.execute(
                "SELECT state FROM local_document_sync WHERE target=?", (target,)
            ).fetchone()
            row = json.loads(saved_row[0]) if saved_row else self._default()
            if row["generation"] != expected_generation:
                raise ValueError("本机文档选择已变化，请重新查看generation")
            if self.guard.status(locked=True):
                # Repair only the explicitly selected project. The independent
                # guard covers every saved Hub/device/archive target, so none of
                # the other restored choices can silently regain body access.
                saved = connection.execute(
                    "SELECT target,state FROM local_document_sync"
                ).fetchall()
                for entry in saved:
                    other = json.loads(entry["state"])
                    other["blocked"] = True
                    connection.execute(
                        "UPDATE local_document_sync SET state=? WHERE target=?",
                        (json.dumps(other, ensure_ascii=False), entry["target"]),
                    )
            row.update(
                generation=max(row["generation"], remote_generation) + 1,
                enabled=enabled,
                blocked=False,
                error=None,
                name=current_project["name"],
                epoch=info["document_epoch"] if info else row["epoch"],
            )
            connection.execute(
                "INSERT INTO local_document_sync VALUES(?,?) ON CONFLICT(target) DO UPDATE SET state=excluded.state",
                (target, json.dumps(row, ensure_ascii=False)),
            )
        self.sync(project_key=project_key)
        return self.status()

    def _valid(self, project_id):
        """Metadata only; a paused choice must not discover/send new bodies."""
        if project_id is None:
            return {}
        with self.db.connect() as c:
            c.execute("BEGIN")
            sources = {
                s["id"]: s
                for s in Documents._sources(c)
                if project_id in s["project_ids"]
                and s["status"] in {"ready", "partial"}
            }
            result = {}
            for r in c.execute(
                "SELECT m.*,d.id FROM document_memberships m JOIN documents d ON d.pk=m.document_pk WHERE m.status='ready' AND d.text IS NOT NULL"
            ):
                if r["source_id"] in sources:
                    result.setdefault(
                        r["source_id"],
                        {"revision": sources[r["source_id"]]["revision"], "files": {}},
                    )["files"][r["id"]] = r["qualification"]
            return result

    @staticmethod
    def _retained(row, valid):
        result = []
        for sid, known in row["known"].items():
            current = valid.get(sid)
            if not current or current["revision"] != known["revision"]:
                continue
            files = [
                {"document_id": ident, "qualification": q}
                for ident, q in known["files"].items()
                if current["files"].get(ident) == q
            ]
            if files:
                result.append(
                    {
                        "source_id": sid,
                        "revision": known["revision"],
                        "files": sorted(files, key=lambda f: f["document_id"]),
                    }
                )
        return sorted(result, key=lambda s: s["source_id"])

    def _control(self, config, info, key, project):
        hub_id = info["hub_id"]
        valid = self._valid(project["id"] if project else None)
        with self.guard.hold():
            row = deepcopy(self._rows(config, hub_id)[key])
            if row["blocked"] or row["epoch"] != info["document_epoch"]:
                raise ValueError("文档控制边界变化，请重新明确选择")
            retained = self._retained(row, valid)
            body = {
                **{k: info[k] for k in ("hub_id", "document_epoch")},
                "device_id": config["device_id"],
                "archive_id": references.material(self.db)[0],
                "project_key": key,
                "generation": row["generation"],
                "project_name": (
                    project["name"] if project else row.get("name", "已删除项目")
                ),
                "enabled": row["enabled"] if project else False,
                "retained": retained,
            }
            signature = digest(body)
            if signature != row["control_digest"]:
                row["sequence"] += 1
                row["control_digest"] = signature
            body["sequence"] = row["sequence"]
            row["known"] = {
                s["source_id"]: {
                    "revision": s["revision"],
                    "files": {f["document_id"]: f["qualification"] for f in s["files"]},
                }
                for s in retained
            }
            for sid, value in row["sources"].items():
                if sid not in valid:
                    value["published"] = value.get("signature")
            if not project:
                row["enabled"] = False
            self._save(config, hub_id, key, row)
        response = federation._request(config, "/documents/control", body)
        if (
            response.get("generation") != body["generation"]
            or response.get("sequence") != body["sequence"]
        ):
            raise federation.HubUnavailable("Hub未确认当前完整控制快照")
        with self.guard.hold():
            current = deepcopy(self._rows(config, hub_id)[key])
            if (
                current["generation"] == body["generation"]
                and current["sequence"] == body["sequence"]
            ):
                current.update(
                    confirmed_generation=body["generation"],
                    confirmed_sequence=body["sequence"],
                    error=None,
                )
                self._save(config, hub_id, key, current)
        return body

    def _snapshots(self, project_id, directory):
        """One archive read transaction; bounded per-file spool, not total-source cap."""
        result = []
        with self.db.connect() as c:
            c.execute("BEGIN")
            sources = [
                s
                for s in Documents._sources(c)
                if project_id in s["project_ids"]
                and s["status"] in {"ready", "partial"}
            ]
            for source in sources:
                files = []
                spools = {}
                for row in c.execute(
                    "SELECT d.*,m.relative_path,m.qualification FROM document_memberships m JOIN documents d ON d.pk=m.document_pk WHERE m.source_id=? AND m.status='ready' AND d.text IS NOT NULL ORDER BY d.id",
                    (source["id"],),
                ):
                    item = {
                        "document_id": row["id"],
                        "version": row["version"],
                        "sha256": row["sha256"],
                        "text_sha256": row["text_sha256"],
                        "path": row["path"],
                        "display_name": Documents._display_name(
                            c, row["id"], row["path"]
                        ),
                        "captured_at": row["captured_at"],
                        "captured_by_source_id": row["captured_by_source_id"],
                        "capture_sequence": row["publish_seq"],
                        "relative_path": row["relative_path"],
                        "qualification": row["qualification"],
                    }
                    state, processed = self.documents.snapshots.result(c, row['pk'])
                    if processed is not None:
                        from .document_results import sha, encode
                        raw = self.documents.snapshots.original(c, row['pk'])
                        result_raw = self.documents.snapshots.blob('results', state['result_sha256']).read_bytes()
                        item.update(schema=processed['schema'], format=processed['format'], raw_bytes=len(raw), result_bytes=len(result_raw),
                                    processing_version=state['processing_version'], result_sha256=state['result_sha256'],
                                    profile_sha256=sha(encode(processed['profile'])), capture_id=state['published_capture'])
                        pair = {}
                        for kind, data in (('raw', raw), ('results', result_raw)):
                            path = directory / uuid4().hex
                            path.write_bytes(data)
                            pair[kind] = path
                        spools[row['id']] = pair
                    else:
                        path = directory / uuid4().hex
                        path.write_text(row['text'], encoding='utf-8', newline='\n')
                        spools[row['id']] = path
                    files.append(item)
                result.append((source, files, spools))
        return result

    def _current(self, config, info, key, control, dirty_generation, *, locked=False):
        if federation.hub_config(self.db) != config:
            raise federation.HubUnavailable("Hub连接已改变，本轮旧目标传输已停止")
        problem = self.guard.status(locked=locked)
        if problem:
            raise ValueError(problem)
        row = self._rows(config, info["hub_id"]).get(key)
        with self.db.connect() as connection:
            project = connection.execute(
                "SELECT 1 FROM projects p JOIN hub_local_project_keys k ON k.id=p.id WHERE k.remote_key=?",
                (key,),
            ).fetchone()
        return bool(
            project
            and row
            and row["enabled"]
            and not row["blocked"]
            and row["generation"] == control["generation"]
            and row["sequence"] == control["sequence"]
            and row.get("dirty_generation", 0) == dirty_generation
        )


    def _stage_processed(self, config, info, key, control, manifest, file, spool, dirty_generation):
        from .document_results import sha
        from .document_transfers import BLOCK_LIMIT
        if 'processed_documents_v1' not in info.get('capabilities', []):
            raise federation.HubUnavailable('Hub不支持processed_documents_v1；保留待办，不降级为文本或在Hub处理')
        fields = ('document_id', 'version', 'sha256', 'text_sha256', 'path', 'display_name', 'captured_at', 'captured_by_source_id', 'capture_sequence', 'processing_version', 'result_sha256', 'result_bytes', 'raw_bytes', 'format', 'profile_sha256', 'capture_id', 'schema')
        begin = {**{name: manifest[name] for name in ('hub_id', 'document_epoch', 'device_id', 'archive_id', 'project_key', 'generation')},
                 'submission_id': digest([manifest['submission_id'], file['document_id'], file['version'], file['processing_version']])[:32],
                 'document': {name: file[name] for name in fields}}
        response = federation._request(config, '/documents/processed/begin', begin)
        transfer_id = identity(response.get('transfer_id'), '传输ID')
        if response.get('block_bytes') != BLOCK_LIMIT:
            raise federation.HubUnavailable('Hub返回不兼容的分块大小')
        for kind in ('raw', 'results'):
            offset = response.get('received', {}).get(kind)
            expected_size = file['raw_bytes'] if kind == 'raw' else file['result_bytes']
            if type(offset) is not int or not 0 <= offset <= expected_size or (offset != expected_size and offset % BLOCK_LIMIT):
                raise federation.HubUnavailable('Hub返回无效续传位置')
            with spool[kind].open('rb') as source:
                source.seek(offset)
                while offset < expected_size:
                    if not self._current(config, info, key, control, dirty_generation):
                        return False
                    raw = source.read(min(BLOCK_LIMIT, expected_size - offset))
                    if not raw:
                        raise ValueError('本轮冻结同步快照不完整')
                    received = federation._request_binary(config, '/documents/processed/' + transfer_id + '/' + kind + '/' + str(offset), raw, headers={'X-Content-SHA256': sha(raw)})
                    offset += len(raw)
                    if received.get('transfer_id') != transfer_id or received.get('received', {}).get(kind) != offset:
                        raise federation.HubUnavailable('Hub未确认当前传输块')
        if not self._current(config, info, key, control, dirty_generation):
            return False
        response = federation._request(config, '/documents/processed/commit', {'transfer_id': transfer_id})
        if response.get('staged') is not True or any(response.get(name) != file[name] for name in ('document_id', 'version', 'processing_version')):
            raise federation.HubUnavailable('Hub未确认成套原件/处理结果')
        return True

    def _publish(
        self, config, info, key, control, source, files, spools, dirty_generation
    ):
        hub_id = info["hub_id"]
        sid = source["id"]
        signature = digest(
            [control["generation"], control["sequence"], source["revision"], files]
        )
        with self.guard.hold():
            if not self._current(
                config, info, key, control, dirty_generation, locked=True
            ):
                return False
            row = deepcopy(self._rows(config, hub_id)[key])
            entry = row["sources"].get(sid, {})
            if (
                entry.get("signature") == signature
                and entry.get("published") == signature
            ):
                return
            if entry.get("signature") != signature:
                entry = {
                    "signature": signature,
                    "sequence": entry.get("sequence", 0) + 1,
                    "submission_id": uuid4().hex,
                    "published": None,
                }
            row["sources"][sid] = entry
            self._save(config, hub_id, key, row)
            manifest = {
                **{
                    k: v
                    for k, v in control.items()
                    if k
                    in {
                        "hub_id",
                        "document_epoch",
                        "device_id",
                        "archive_id",
                        "project_key",
                        "generation",
                    }
                },
                "control_sequence": control["sequence"],
                "source_id": sid,
                "revision": source["revision"],
                "sequence": entry["sequence"],
                "submission_id": entry["submission_id"],
                "files": files,
            }
        for file in files:
            # Recheck every body after the preceding network call, including
            # guard faults, project deletion and source changes while in flight.
            if not self._current(config, info, key, control, dirty_generation):
                return False
            if file.get('schema') == 'processed_documents_v1':
                if not self._stage_processed(config, info, key, control, manifest, file, spools[file['document_id']], dirty_generation):
                    return False
                continue
            body = {
                k: file[k]
                for k in (
                    "document_id",
                    "version",
                    "sha256",
                    "text_sha256",
                    "path",
                    "display_name",
                    "captured_at",
                    "captured_by_source_id",
                    "capture_sequence",
                )
            }
            body["text"] = spools[file["document_id"]].read_text(encoding="utf-8")
            body["text_length"] = len(body["text"])
            federation._request(
                config,
                "/documents/stage",
                {
                    **{
                        k: manifest[k]
                        for k in (
                            "hub_id",
                            "document_epoch",
                            "device_id",
                            "archive_id",
                            "project_key",
                            "generation",
                        )
                    },
                    "document": body,
                },
            )
        with self.guard.hold():
            if not self._current(
                config, info, key, control, dirty_generation, locked=True
            ):
                return False
            row = deepcopy(self._rows(config, hub_id)[key])
            known = (
                {
                    "revision": source["revision"],
                    "files": {f["document_id"]: f["qualification"] for f in files},
                }
                if files
                else None
            )
            # Publication can create new qualifications AFTER a control snapshot.
            # Even an identical later empty retention set must be a NEW control,
            # rather than an idempotent replay of the pre-publication withdrawal.
            if row["known"].get(sid) != known:
                row["control_digest"] = None
            if known is None:
                row["known"].pop(sid, None)
            else:
                row["known"][sid] = known
            # All member identities have actually been staged before adding
            # the manifest to the uncertain-attempt ledger. A pause between
            # files cannot send the never-staged siblings in retention control.
            self._save(config, hub_id, key, row)
        if not self._current(config, info, key, control, dirty_generation):
            return False
        response = federation._request(config, "/documents/publish", manifest)
        if any(
            response.get(k) != manifest[k]
            for k in (
                "source_id",
                "revision",
                "sequence",
                "generation",
                "submission_id",
            )
        ) or response.get("published") != len(files):
            raise federation.HubUnavailable("Hub未确认当前完整来源清单")
        with self.guard.hold():
            latest = deepcopy(self._rows(config, hub_id)[key])
            current = latest["sources"].get(sid, {})
            if (
                latest["generation"] == control["generation"]
                and latest["sequence"] == control["sequence"]
                and current.get("signature") == signature
            ):
                current["published"] = signature
                latest["error"] = None
                self._save(config, hub_id, key, latest)
                return True
        return False

    def sync(self, *, project_key=None, control_only=False):
        config, info, error = self._info()
        errors = []
        published = 0
        if not config or not info:
            return {"pending": True, "errors": [error], "published": 0}
        if self.guard.status():
            return {"pending": True, "errors": [self.guard.status()], "published": 0}
        hub_id = info["hub_id"]
        rows = self._rows(config, hub_id)
        projects = {p["stable_key"]: p for p in self.db.projects()}
        if project_key is not None and project_key not in rows:
            raise ValueError("项目尚未保存文档选择")
        try:
            federation._push_projects(self.db, config, hub_id, 0)
        except federation.HubUnavailable as exc:
            errors.append(str(exc))
        for key, old in rows.items():
            before_errors = len(errors)
            dirty_generation = old.get("dirty_generation", 0)
            if project_key is not None and key != project_key:
                continue
            project = projects.get(key)
            try:
                control = self._control(config, info, key, project)
                if project and control["enabled"] and not control_only:
                    self._sync_sources(
                        config, info, key, control, project, published_ref := []
                    )
                    published += len(published_ref)
                if len(errors) == before_errors:
                    with self.guard.hold():
                        current = deepcopy(self._rows(config, hub_id)[key])
                        if (
                            current["generation"] == control["generation"]
                            and current.get("dirty_generation", 0) == dirty_generation
                        ):
                            current["dirty"] = False
                            self._save(config, hub_id, key, current)
            except (OSError, ValueError, federation.HubUnavailable) as exc:
                errors.append(str(exc))
                if not self.guard.status():
                    with self.guard.hold():
                        current = deepcopy(self._rows(config, hub_id)[key])
                        if current["generation"] == old["generation"]:
                            current["error"] = str(exc)
                            self._save(config, hub_id, key, current)
        status = self.status()
        return {
            "pending": bool(errors or status["pending"] or status["conflict"]),
            "errors": errors,
            "published": published,
        }

    def _sync_sources(self, config, info, key, control, project, published):
        errors = []
        dirty_generation = self._rows(config, info["hub_id"])[key].get(
            "dirty_generation", 0
        )
        with tempfile.TemporaryDirectory(
            prefix=".documents-sync-", dir=self.db.db_path.parent
        ) as spool:
            for source, files, bodies in self._snapshots(project["id"], Path(spool)):
                try:
                    if self._publish(
                        config,
                        info,
                        key,
                        control,
                        source,
                        files,
                        bodies,
                        dirty_generation,
                    ):
                        published.append(source["id"])
                except (OSError, ValueError, federation.HubUnavailable) as exc:
                    errors.append(str(exc))
        if errors:
            raise federation.HubUnavailable("；".join(errors))


def schedule(db):
    """Retry existing choices only; fresh/off projects grant no implicit upload."""
    config = federation.hub_config(db)
    if not config or not config.get("bound_hub_id"):
        return None
    sync = DocumentSync(db)
    if not sync._rows(config, config["bound_hub_id"]):
        return None
    if sync.guard.status():
        return {"pending": True, "errors": [sync.guard.status()]}
    with sync.guard.hold():
        for key, row in sync._rows(config, config["bound_hub_id"]).items():
            row["dirty"] = True
            row["dirty_generation"] = row.get("dirty_generation", 0) + 1
            sync._save(config, config["bound_hub_id"], key, row)
    return {"pending": True}


def hub_sources(db):
    config = federation.hub_config(db)
    if not config:
        raise ValueError("尚未配置Hub")
    federation._hub_info(config)
    result = federation._request(config, "/documents/sources")
    if not isinstance(result, list):
        raise federation.HubUnavailable("Hub来源列表响应无效")
    return result


def hub_projects(db):
    config = federation.hub_config(db)
    if not config:
        raise ValueError("尚未配置Hub")
    federation._hub_info(config)
    result = federation._request(config, "/projects")
    if not isinstance(result, list):
        raise federation.HubUnavailable("Hub项目列表响应无效")
    return result


def combined_listing(db, *, sources=False, local=None):
    """Read both lists without losing the Local snapshot on Hub failure."""
    if local is None:
        local = Documents(db).sources() if sources else db.projects()
    remote = []
    reason = None
    coverage = "complete"
    try:
        remote = hub_sources(db) if sources else hub_projects(db)
    except (federation.HubUnavailable, OSError, ValueError) as exc:
        coverage = "unavailable"
        reason = str(exc)
    return {
        "local": local,
        "hub": remote,
        "coverage": {"local": "complete", "hub": coverage},
        "fallback_reason": reason,
    }
