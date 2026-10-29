"""Local Web UI and JSON API."""

from __future__ import annotations

import os
import threading
from contextlib import asynccontextmanager
from importlib.resources import files

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from .core import Archive


class SearchRequest(BaseModel):
    query: str
    scope: str = "all"
    project_id: int | None = None
    limit: int = Field(default=5, ge=1, le=50)
    current_session_id: str | None = None
    current_source: str | None = None
    include_current: bool = False


class MapRequest(BaseModel):
    path: str
    project_id: int


class LinkRequest(BaseModel):
    one: int
    other: int
    linked: bool = True


class MergeRequest(BaseModel):
    source_id: int
    target_id: int


class RenameRequest(BaseModel):
    name: str


class SettingsRequest(BaseModel):
    codex_root: str | None = None
    claude_root: str | None = None
    sync_interval_seconds: int | None = None


def create_app(archive: Archive | None = None, *, auto_sync: bool = True) -> FastAPI:
    db = archive or Archive()
    stop = threading.Event()
    run_lock = threading.Lock()
    state: dict[str, object] = {"running": False, "last_result": None}

    def run_sync() -> None:
        if not run_lock.acquire(blocking=False):
            return
        state["running"] = True
        try:
            state["last_result"] = db.sync_all()
        except Exception as exc:
            state["last_result"] = {"errors": [{"error": str(exc)}]}
        finally:
            state["running"] = False
            run_lock.release()

    def loop() -> None:
        run_sync()
        while not stop.wait(int(db.get_settings()["sync_interval_seconds"])):
            run_sync()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        worker = None
        if auto_sync:
            worker = threading.Thread(target=loop, name="smm-source-sync", daemon=True)
            worker.start()
        yield
        stop.set()
        if worker:
            worker.join(timeout=2)

    app = FastAPI(title="SMM Local", lifespan=lifespan)

    @app.exception_handler(ValueError)
    async def value_error_handler(request, exc: ValueError):
        return __import__("fastapi").responses.JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.get("/", response_class=HTMLResponse)
    def index():
        return files("smm_local").joinpath("static/index.html").read_text(encoding="utf-8")

    @app.get("/api/status")
    def status():
        return {**db.status(), "sync": dict(state)}

    @app.post("/api/sync")
    def sync():
        if run_lock.locked():
            return {"started": False, "reason": "同步已在进行"}
        thread = threading.Thread(target=run_sync, daemon=True)
        thread.start()
        return {"started": True}

    @app.get("/api/projects")
    def projects():
        return db.projects()

    @app.post("/api/projects/map")
    def map_path(req: MapRequest):
        db.map_path(req.path, req.project_id)
        return {"ok": True}

    @app.post("/api/projects/link")
    def link(req: LinkRequest):
        db.link_projects(req.one, req.other, req.linked)
        return {"ok": True}

    @app.post("/api/projects/merge")
    def merge(req: MergeRequest):
        db.merge_projects(req.source_id, req.target_id)
        return {"ok": True}

    @app.post("/api/projects/{project_id}/rename")
    def rename(project_id: int, req: RenameRequest):
        db.rename_project(project_id, req.name)
        return {"ok": True}

    @app.post("/api/search")
    def search(req: SearchRequest):
        return db.search(**req.model_dump())

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


app = create_app()
