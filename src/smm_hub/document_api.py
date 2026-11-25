"""Bounded authenticated document HTTP surface and anonymous connection shell."""

from importlib.resources import files
import hmac, json
from fastapi import Body, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from ._archive import DocumentGuard


def install(app, documents, token):
    @app.middleware("http")
    async def boundary(request: Request, call_next):
        if not (request.method == "GET" and request.url.path == "/"):
            if not hmac.compare_digest(
                request.headers.get("Authorization", "").encode("utf-8"),
                ("Bearer " + token).encode("ascii"),
            ):
                return JSONResponse(
                    {"detail": "需要有效的汇总服务凭证"}, status_code=401
                )
        if request.method in {"POST", "PUT", "DELETE"} and request.url.path.startswith(
            "/v1/documents/"
        ):
            chunks = []
            size = 0
            async for chunk in request.stream():
                size += len(chunk)
                if size > 16 * 1024 * 1024:
                    return JSONResponse(
                        {"detail": "文档写请求超过16MiB"}, status_code=413
                    )
                chunks.append(chunk)
            request._body = b"".join(chunks)
        return await call_next(request)

    def invoke(fn, *args, **kw):
        try:
            return fn(*args, **kw)
        except (OSError, ValueError, TypeError) as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.get("/", response_class=HTMLResponse)
    def root():
        return (
            files("smm_hub").joinpath("static/index.html").read_text(encoding="utf-8")
        )

    @app.get("/v1/projects")
    def projects():
        return documents.projects.list()

    @app.post("/v1/projects")
    def project_create(body: dict = Body(...)):
        return invoke(documents.project_create, body)

    @app.get("/v1/documents/sources")
    def sources():
        return invoke(documents.sources)

    @app.put("/v1/documents/sources/{source_id}")
    def set_source(source_id: str, body: dict = Body(...)):
        return invoke(documents.native, "set", body, source_id)

    @app.delete("/v1/documents/sources/{source_id}")
    def remove_source(source_id: str, body: dict = Body(...)):
        return invoke(documents.native, "remove", body, source_id)

    @app.get("/v1/documents/files")
    def document_files(source_id: str | None = None):
        return invoke(documents.files, source_id)

    @app.get("/v1/documents/library")
    def library(project_id: int | None = None):
        return invoke(documents.library.list, project_id)

    @app.post("/v1/documents/library")
    def library_add(body: dict = Body(...)):
        return invoke(documents.managed, "create", body)

    @app.put("/v1/documents/library/{document_id}")
    def library_update(document_id: str, body: dict = Body(...)):
        return invoke(documents.managed, "update", body, document_id)

    @app.delete("/v1/documents/library/{document_id}")
    def library_remove(document_id: str, body: dict = Body(...)):
        return invoke(documents.managed, "remove", body, document_id)

    @app.post("/v1/documents/status")
    def document_status(body: dict = Body(...)):
        def status():
            documents._context(body)
            from ._archive import document_identity

            document_identity(body.get("device_id"))
            document_identity(body.get("archive_id"))
            with documents.db.connect() as c:
                rows = [
                    dict(r)
                    for r in c.execute(
                        "SELECT project_key,generation,enabled,sequence,blocked_generation FROM hub_document_controls WHERE device_id=? AND archive_id=?",
                        (body["device_id"], body["archive_id"]),
                    )
                ]
            return {
                "projects": rows,
                "conflict": bool(documents.guard.status()),
                **documents.context(),
            }

        return invoke(status)

    @app.post("/v1/documents/control")
    def control(body: dict = Body(...)):
        return invoke(documents.control, body)

    @app.post("/v1/documents/stage")
    def stage(body: dict = Body(...)):
        return invoke(documents.stage, body)

    @app.post("/v1/documents/publish")
    def publish(body: dict = Body(...)):
        return invoke(documents.publish, body)

    @app.post("/v1/documents/search")
    def search(body: dict = Body(...)):
        return invoke(documents.search, body)

    @app.post("/v1/documents/read")
    def read(body: dict = Body(...)):
        return invoke(documents.read, body)

    @app.post('/v1/documents/processed/begin')
    def processed_begin(body: dict = Body(...)):
        return invoke(documents.processed.begin, body)

    @app.put('/v1/documents/processed/{transfer_id}/{kind}/{offset}')
    async def processed_part(transfer_id: str, kind: str, offset: int, request: Request):
        raw = await request.body()
        return invoke(documents.processed.part, transfer_id, kind, offset, raw, request.headers.get('X-Content-SHA256'))

    @app.post('/v1/documents/processed/commit')
    def processed_commit(body: dict = Body(...)):
        return invoke(documents.processed.commit, body)

    @app.post('/v1/documents/original')
    def original(body: dict = Body(...)):
        return Response(invoke(documents.original, body), media_type='application/octet-stream', headers={'Cache-Control':'no-store'})
