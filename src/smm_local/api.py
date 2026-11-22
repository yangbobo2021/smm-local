"""Local Web UI and JSON API."""

from __future__ import annotations

import threading
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from importlib.resources import files
from typing import Callable

from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from .core import Archive, shared_db_path, utcnow
from .federation import (HubUnavailable, push_pending, upload_status, choose_upload, upload_control,
                         search_archive, read_archive, hub_config, project_status, _request)
from .upload import LocalUpload
from .project_control import change as change_project
from . import references


class SearchRequest(BaseModel):
    query: str
    scope: str = "all"
    project_id: int | None = None
    limit: int = Field(default=5, ge=1, le=50)
    current_session_id: str | None = None
    current_source: str | None = None
    include_current: bool = False
    local: bool = False


class MapRequest(BaseModel):
    path: str
    project_id: int
    confirmation: str | None = None


class LinkRequest(BaseModel):
    one: int
    other: int
    linked: bool = True


class MergeRequest(BaseModel):
    source_id: int
    target_id: int
    confirmation: str | None = None


class UploadChoice(BaseModel):
    mode: str
    project_ids: list[int] = Field(default_factory=list)
    expected_generation: int | None = None


class ReconcileRequest(BaseModel):
    use: str | None = None
    expected_hub_revision: int | None = Field(default=None, ge=0, strict=True)
    expected_local_generation: int | None = Field(default=None, ge=0, strict=True)


class AssignRequest(BaseModel):
    conversation_id: int
    project_id: int
    confirmation: str | None = None


class ReadRequest(BaseModel):
    conversation_id: int | None = None
    reference: str | None = None
    start: int | None = None
    end: int | None = None
    hub_id: str | None = None
    hub_message_id: int | None = None


class RenameRequest(BaseModel):
    name: str


class SettingsRequest(BaseModel):
    codex_root: str | None = None
    claude_root: str | None = None
    sync_interval_seconds: int | None = None


class PauseRequest(BaseModel):
    paused: bool


@dataclass
class SyncJob:
    source: str | None = None
    covered: frozenset[str] = frozenset()
    automatic: bool = False
    done: threading.Event = field(default_factory=threading.Event)
    result: dict | None = None


def create_app(archive: Archive | None = None, *, auto_sync: bool = True,
               sync_on_start: bool = True, service_token: str | None = None,
               shutdown: Callable[[], None] | None = None) -> FastAPI:
    db = archive or Archive(shared_db_path())
    references.material(db)
    stop = threading.Event()
    run_lock = threading.Lock()
    active: SyncJob | None = None
    pending: dict[str | None, SyncJob] = {}

    def run_sync(job: SyncJob) -> None:
        nonlocal active
        try:
            try:
                result = db.sync_all(job.source, eligible=job.covered)
            except Exception as exc:
                result = {"finished_at": utcnow(), "errors": [{"error": str(exc)}]}
            try:
                remote = push_pending(db)
                if remote is not None:
                    result["hub"] = remote
            except (HubUnavailable, OSError, ValueError) as exc:
                result["hub"] = {"pending": True, "reason": str(exc)}
            db.record_sync_result(result)
        except Exception as exc:
            result["errors"].append({"error": f"无法保存同步结果：{exc}"})
        finally:
            with run_lock:
                job.result = result
                active = None
                job.done.set()
                while pending and not stop.is_set():
                    next_job = pending.pop(next(iter(pending)))
                    if next_job.automatic and db.get_settings()["sync_paused"]:
                        next_job.done.set()
                        continue
                    launch(next_job)
                    break

    def launch(job: SyncJob) -> None:
        nonlocal active
        job.covered = frozenset(name for name, source in db.configured_sources().items()
                                if source["enabled"] or name == job.source)
        active = job
        threading.Thread(target=run_sync, args=(job,), daemon=True).start()

    def start_sync(*, automatic: bool = False, source: str | None = None,
                   queue: bool = False) -> tuple[bool, SyncJob | None]:
        # The caller holds run_lock so checking pause and scheduling are atomic.
        if stop.is_set() or (automatic and db.get_settings()["sync_paused"]):
            return False, None
        if active is not None:
            if (active.source == source or (active.source is None and source in active.covered)
                    or (automatic and not queue)):
                return False, active
            if None in pending and source is not None:
                job = pending[None]
            else:
                job = pending.setdefault(source, SyncJob(source, automatic=automatic))
            if not automatic:
                job.automatic = False
            return False, job
        job = SyncJob(source, automatic=automatic)
        launch(job)
        return True, job

    def loop() -> None:
        while not stop.wait(int(db.get_settings()["sync_interval_seconds"])):
            if db.get_settings()["sync_paused"]:
                try:
                    push_pending(db, control_only=True)
                except (HubUnavailable, OSError, RuntimeError, ValueError):
                    pass
                continue
            with run_lock:
                start_sync(automatic=True)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        stop.clear()
        worker = None
        if auto_sync:
            if sync_on_start:
                with run_lock:
                    start_sync(automatic=True)
            worker = threading.Thread(target=loop, name="smm-source-sync", daemon=True)
            worker.start()
        try:
            yield
        finally:
            with run_lock:
                stop.set()
                pending.clear()
                job = active
            if worker:
                worker.join(timeout=2)
            if job:
                job.done.wait(5)

    app = FastAPI(title="SMM Local", lifespan=lifespan)

    @app.exception_handler(HubUnavailable)
    async def hub_unavailable(request: Request, exc: HubUnavailable):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.exception_handler(ValueError)
    async def value_error_handler(request, exc: ValueError):
        return __import__("fastapi").responses.JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.get("/", response_class=HTMLResponse)
    def index():
        return files("smm_local").joinpath("static/index.html").read_text(encoding="utf-8")

    @app.get("/api/status")
    def status():
        with run_lock:
            running = active is not None
        info = db.status()
        sources = db.source_status(info["by_source"])
        return {**info, "upload": upload_status(db), "sync": {"running": running, "paused": info["settings"]["sync_paused"],
                                 "last_result": db.last_sync_result(), "sources": sources}}

    @app.post("/api/sync")
    def sync(wait: bool = False, source: str | None = None):
        with run_lock:
            if source is not None:
                sources = db.configured_sources()
                if source not in sources:
                    raise HTTPException(404, "未知对话来源")
                if not sources[source]["enabled"]:
                    raise HTTPException(409, "来源已停用")
            started, job = start_sync(source=source)
        if job is None:
            raise HTTPException(503, "同步服务正在停止")
        if wait and job.done.wait(15):
            return {"started": started, "running": False, "result": job.result}
        return {"started": started, "running": True, "result": None}

    def require_local_control(request: Request) -> None:
        if service_token is None or request.headers.get("X-SMM-Service") == service_token:
            return
        if (request.url.hostname not in {"127.0.0.1", "::1", "localhost"}
                or request.headers.get("Origin") != f"{request.url.scheme}://{request.url.netloc}"
                or request.headers.get("X-SMM-UI") != "1"):
            raise HTTPException(403, "请从本机状态页执行此操作")

    @app.put("/api/sources/{source}/enabled")
    def enable_source(source: str, request: Request, enabled: bool = Body(embed=True)):
        require_local_control(request)
        with run_lock:
            db.set_source_enabled(source, enabled)
        return {"id": source, "enabled": enabled}

    @app.put("/api/sync/pause")
    def pause(req: PauseRequest, request: Request):
        require_local_control(request)
        with run_lock:
            db.set_settings(sync_paused=req.paused)
            if not req.paused:
                start_sync(automatic=True, queue=True)
            return {"paused": req.paused, "running": active is not None}

    if service_token is not None:
        @app.get("/api/service", include_in_schema=False)
        def service(request: Request):
            if request.headers.get("X-SMM-Service") != service_token:
                raise HTTPException(404)
            return {"service": "smm-local"}

        @app.put("/api/service/stop", include_in_schema=False)
        def stop_service(request: Request):
            if shutdown is None or request.headers.get("X-SMM-Service") != service_token:
                raise HTTPException(404)
            shutdown()
            return {"stopping": True}

    @app.get("/api/projects")
    def projects():
        return project_status(db)

    @app.get("/api/upload")
    def upload_info():
        return upload_status(db)

    @app.put("/api/upload")
    def set_upload(req: UploadChoice, request: Request):
        require_local_control(request)
        return choose_upload(db, req.mode, req.project_ids, req.expected_generation)

    @app.post("/api/upload/reconcile")
    def reconcile_upload(req: ReconcileRequest, request: Request):
        require_local_control(request)
        if req.use is not None and (req.expected_hub_revision is None or req.expected_local_generation is None):
            raise ValueError("请提供刚查看的 hub.revision 和 local.generation，再确认对账")
        return upload_control(db).reconcile(_request, use=req.use, expected_hub_revision=req.expected_hub_revision,
                                           expected_local_generation=req.expected_local_generation)

    @app.post("/api/upload/prepare-restore")
    def prepare_local_restore(request: Request):
        require_local_control(request)
        config = hub_config(db)
        controller = LocalUpload(db, config, config["bound_hub_id"]) if config.get("bound_hub_id") else upload_control(db)
        return controller.prepare_restore()

    @app.post("/api/projects/global")
    def global_project(request: Request):
        require_local_control(request)
        return db.ensure_global_project()

    @app.post("/api/projects/assign")
    def assign_project(req: AssignRequest, request: Request):
        require_local_control(request)
        return change_project(db, "assign", {"conversation_id": req.conversation_id, "target_id": req.project_id},
                              req.confirmation, always_preview=True)

    @app.post("/api/projects/map")
    def map_path(req: MapRequest, request: Request):
        require_local_control(request)
        return {"ok": True, **change_project(db, "map", {"path": req.path, "target_id": req.project_id}, req.confirmation)}

    @app.post("/api/projects/link")
    def link(req: LinkRequest):
        db.link_projects(req.one, req.other, req.linked)
        return {"ok": True}

    @app.post("/api/projects/merge")
    def merge(req: MergeRequest, request: Request):
        require_local_control(request)
        return {"ok": True, **change_project(db, "merge", {"source_id": req.source_id, "target_id": req.target_id}, req.confirmation)}

    @app.post("/api/projects/{project_id}/rename")
    def rename(project_id: int, req: RenameRequest):
        db.rename_project(project_id, req.name)
        return {"ok": True}

    @app.post("/api/search")
    def search(req: SearchRequest):
        return search_archive(db, **req.model_dump())

    @app.post("/api/read")
    def read_reference(req: ReadRequest):
        return read_archive(db, **req.model_dump())

    @app.get("/api/conversations/{conversation_id}")
    def read(conversation_id: int, start: int | None = None, end: int | None = None):
        return db.read(conversation_id, start=start, end=end)

    @app.get("/api/settings")
    def settings():
        return db.get_settings()

    @app.put("/api/settings")
    def set_settings(req: SettingsRequest):
        return db.set_settings(**req.model_dump())

    return app


def __getattr__(name: str):
    if name == "app":
        return create_app()
    raise AttributeError(name)
