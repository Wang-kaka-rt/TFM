from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from app.core.config import settings
from app.models.session import (
    ApiMessage,
    ReloadSessionRequest,
    SessionResponse,
    StartSessionRequest,
    StatusResponse,
    StopSessionRequest,
)
from app.services.errors import SessionNotFoundError
from app.services.session_service import SessionService

router = APIRouter()
session_service = SessionService(settings)
STATIC_DIR = Path(__file__).resolve().parents[2] / "static"
STRUDEL_DIR = STATIC_DIR / "strudel"
STRUDEL_INDEX = STRUDEL_DIR / "index.html"
FAVICON_PATH = STRUDEL_DIR / "favicon.ico"


@router.get("/", response_class=HTMLResponse, tags=["system"])
async def home(request: Request) -> Response:
    if STRUDEL_INDEX.exists():
        base_url = str(request.base_url).rstrip("/")
        redirect_url = f"/index.html?svSession=demo01&svBase={quote(base_url, safe='')}"
        return RedirectResponse(url=redirect_url, status_code=307)
    return HTMLResponse("<h1>Strudel static assets are not packaged.</h1>", status_code=200)


@router.get("/favicon.ico", tags=["system"])
async def favicon() -> Response:
    if FAVICON_PATH.exists():
        return FileResponse(FAVICON_PATH, media_type="image/x-icon")
    return Response(status_code=204)


@router.get("/health", response_model=ApiMessage, tags=["system"])
async def healthcheck() -> ApiMessage:
    return ApiMessage(message="backend is healthy")


@router.post("/start", response_model=SessionResponse, tags=["session"])
async def start_session(payload: StartSessionRequest) -> SessionResponse:
    session = await session_service.start(payload.session_id)
    return SessionResponse(message="session started", session=session)


@router.post("/stop", response_model=SessionResponse, tags=["session"])
async def stop_session(payload: StopSessionRequest) -> SessionResponse:
    try:
        session = await session_service.stop(payload.session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"session '{payload.session_id}' not found") from exc
    return SessionResponse(message="session stopped", session=session)


@router.post("/reload", response_model=SessionResponse, tags=["session"])
async def reload_session(payload: ReloadSessionRequest) -> SessionResponse:
    try:
        session = await session_service.reload(payload.session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"session '{payload.session_id}' not found") from exc
    return SessionResponse(message="session reloaded", session=session)


@router.get("/status", response_model=StatusResponse, tags=["session"])
async def session_status(
    session_id: str | None = Query(default=None, description="Optional session id"),
) -> StatusResponse:
    if session_id is not None:
        session = session_service.get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail=f"session '{session_id}' not found")
        return StatusResponse(
            message="session status loaded",
            active_session=session_service.active(),
            sessions=[session],
        )

    return StatusResponse(
        message="all session statuses loaded",
        active_session=session_service.active(),
        sessions=session_service.all(),
    )


@router.get("/strudel/{session_id}", tags=["artifacts"])
async def get_strudel_script(session_id: str) -> FileResponse:
    try:
        script_path = session_service.get_strudel_script_path(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"session '{session_id}' not found") from exc
    if not script_path.exists():
        raise HTTPException(status_code=404, detail=f"strudel artifact for '{session_id}' not found")
    return FileResponse(script_path, media_type="application/javascript", filename="strudel.js")


@router.get("/samples/{session_id}/manifest", tags=["artifacts"])
async def get_samples_manifest(session_id: str) -> FileResponse:
    try:
        manifest_path = session_service.get_samples_manifest_path(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"session '{session_id}' not found") from exc
    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail=f"samples manifest for '{session_id}' not found")
    return FileResponse(manifest_path, media_type="application/json", filename="samples.json")


@router.get("/metadata/{session_id}", tags=["artifacts"])
async def get_metadata(session_id: str) -> FileResponse:
    try:
        metadata_path = session_service.get_metadata_path(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"session '{session_id}' not found") from exc
    if not metadata_path.exists():
        raise HTTPException(status_code=404, detail=f"metadata for '{session_id}' not found")
    return FileResponse(metadata_path, media_type="application/json", filename="metadata.json")


@router.get("/metrics", tags=["system"])
async def metrics() -> dict[str, int]:
    return session_service.get_metrics()


def _resolve_strudel_asset(asset_path: str) -> Path | None:
    if not STRUDEL_DIR.exists():
        return None
    rel_path = asset_path.lstrip("/")
    candidate = (STRUDEL_DIR / rel_path).resolve()
    try:
        candidate.relative_to(STRUDEL_DIR.resolve())
    except ValueError:
        return None
    if candidate.is_file():
        return candidate
    # Support directory-style URLs like "/bakery" -> "/bakery/index.html"
    if candidate.is_dir():
        index_file = candidate / "index.html"
        if index_file.is_file():
            return index_file
    if candidate.suffix == "":
        index_file = (candidate / "index.html").resolve()
        try:
            index_file.relative_to(STRUDEL_DIR.resolve())
        except ValueError:
            return None
        if index_file.is_file():
            return index_file
    return None


@router.get("/index.html", include_in_schema=False)
async def strudel_index() -> Response:
    index_file = _resolve_strudel_asset("index.html")
    if index_file is None:
        raise HTTPException(status_code=404, detail="strudel index not found")
    return FileResponse(index_file, media_type="text/html")


@router.get("/{asset_path:path}", include_in_schema=False)
async def strudel_asset_fallback(asset_path: str) -> Response:
    asset = _resolve_strudel_asset(asset_path)
    if asset is None:
        raise HTTPException(status_code=404, detail="resource not found")
    return FileResponse(asset)
