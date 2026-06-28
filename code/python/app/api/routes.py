import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Path as ApiPath, Query, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from app.core.config import settings
from app.models.session import (
    ApiMessage,
    SessionResponse,
    StartSessionRequest,
    StatusResponse,
    StopSessionRequest,
)
from app.services.errors import SessionNotFoundError
from app.services.panel import control_panel_script
from app.services.session_service import SessionService

router = APIRouter()
logger = logging.getLogger(__name__)
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


@router.get("/runtime", tags=["system"])
async def runtime_info() -> dict[str, object]:
    return session_service.get_runtime_diagnostics()


@router.post("/transcriber/model", tags=["system"])
async def set_transcriber_model(
    model: str = Query(..., description="faster-whisper model: tiny|base|small|medium|large-v2|large-v3"),
) -> dict[str, object]:
    try:
        return await session_service.set_transcriber_model(model)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to switch transcriber model to '%s'", model)
        raise HTTPException(status_code=500, detail=f"failed to load model '{model}': {exc}") from exc


@router.get("/storage", tags=["system"])
async def storage_info(
    session_id: str | None = Query(default=None, description="Optional session id for resolved storage paths"),
) -> dict[str, str | None]:
    root = session_service.samples_root
    normalized = session_id.strip() if session_id else ""
    if normalized:
        workspace_dir = (root / normalized).resolve()
        raw_dir = (root / ".internal" / normalized / "raw").resolve()
    else:
        workspace_dir = None
        raw_dir = None
    return {
        "samples_root": str(root),
        "session_id": normalized or None,
        "workspace_dir": None if workspace_dir is None else str(workspace_dir),
        "raw_dir": None if raw_dir is None else str(raw_dir),
    }


@router.post("/storage/open", response_model=ApiMessage, tags=["system"])
async def open_storage_path(
    session_id: str | None = Query(default=None, description="Optional session id for resolved storage paths"),
) -> ApiMessage:
    root = session_service.samples_root
    normalized = session_id.strip() if session_id else ""
    target = (root / normalized).resolve() if normalized else root
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid storage path") from exc
    if normalized and not target.exists():
        target.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        root.mkdir(parents=True, exist_ok=True)
        target = root
    if sys.platform == "win32":
        os.startfile(target)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.run(["open", str(target)], check=False)
    else:
        subprocess.run(["xdg-open", str(target)], check=False)
    return ApiMessage(message=f"opened storage path: {target}")


@router.post("/start", response_model=SessionResponse, tags=["session"])
async def start_session(payload: StartSessionRequest) -> SessionResponse:
    try:
        session = await session_service.start(payload.session_id)
    except RuntimeError as exc:
        logger.warning("Failed to start session '%s': %s", payload.session_id, exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to start session '%s'", payload.session_id)
        raise HTTPException(
            status_code=500,
            detail=f"failed to start session '{payload.session_id}': {exc}",
        ) from exc
    return SessionResponse(message="session started", session=session)


@router.post("/stop", response_model=SessionResponse, tags=["session"])
async def stop_session(payload: StopSessionRequest) -> SessionResponse:
    try:
        session = await session_service.stop(payload.session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"session '{payload.session_id}' not found") from exc
    return SessionResponse(message="solicitud de parada enviada", session=session)


@router.post("/browser/chunk", tags=["session"])
async def upload_browser_chunk(
    request: Request,
    session_id: str = Query(..., description="Session id for browser-captured audio"),
) -> dict[str, int | str]:
    audio_bytes = await request.body()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="browser audio chunk is empty")
    try:
        return await session_service.submit_browser_chunk(session_id, audio_bytes)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"session '{session_id}' not found") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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


def _read_artifact_bytes(path: Path) -> bytes:
    # These JSON/JS artifacts are rewritten on every processed chunk while the
    # control panel polls them. Read the whole file into memory in one shot and
    # let the Response derive Content-Length from the exact bytes returned. Using
    # FileResponse here races the concurrent rewrite (it stats the size first,
    # then streams) and triggers "Response content longer than Content-Length".
    return path.read_bytes()


@router.get("/strudel/{session_id}", tags=["artifacts"])
async def get_strudel_script(session_id: str) -> Response:
    try:
        script_path = session_service.get_strudel_script_path(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"session '{session_id}' not found") from exc
    if not script_path.exists():
        raise HTTPException(status_code=404, detail=f"strudel artifact for '{session_id}' not found")
    return Response(content=_read_artifact_bytes(script_path), media_type="application/javascript")


@router.get("/samples/{session_id}/manifest", tags=["artifacts"])
async def get_samples_manifest(session_id: str) -> Response:
    try:
        manifest_path = session_service.get_samples_manifest_path(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"session '{session_id}' not found") from exc
    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail=f"samples manifest for '{session_id}' not found")
    return Response(content=_read_artifact_bytes(manifest_path), media_type="application/json")


@router.get("/samples/{session_id}/{sample_group}/{file_name}", tags=["artifacts"])
async def get_sample_file(
    session_id: str,
    sample_group: str = ApiPath(pattern="^(sentences|phrases|words|syllables|letters)$"),
    file_name: str = ApiPath(pattern=r"^[\w.-]+\.wav$"),
) -> FileResponse:
    root = session_service.samples_root
    sample_path = (root / session_id / sample_group / file_name).resolve()
    try:
        sample_path.relative_to(root)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="sample not found") from exc
    if not sample_path.is_file():
        raise HTTPException(status_code=404, detail="sample not found")
    return FileResponse(sample_path, media_type="audio/wav", filename=file_name)


@router.get("/metadata/{session_id}", tags=["artifacts"])
async def get_metadata(session_id: str) -> Response:
    try:
        metadata_path = session_service.get_metadata_path(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"session '{session_id}' not found") from exc
    if not metadata_path.exists():
        raise HTTPException(status_code=404, detail=f"metadata for '{session_id}' not found")
    return Response(content=_read_artifact_bytes(metadata_path), media_type="application/json")


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


_SAFE_SESSION_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")


@router.get("/index.html", include_in_schema=False)
async def strudel_index(request: Request) -> Response:
    index_file = _resolve_strudel_asset("index.html")
    if index_file is None:
        raise HTTPException(status_code=404, detail="strudel index not found")
    raw = request.query_params.get("svSession", "demo01")
    session_id = raw if _SAFE_SESSION_ID.fullmatch(raw) else "demo01"
    html = index_file.read_text(encoding="utf-8")
    panel_js = control_panel_script(session_id)
    injection = f"\n<script>\n{panel_js}\n</script>"
    if "</body>" in html:
        html = html.replace("</body>", f"{injection}\n</body>", 1)
    else:
        html += injection
    return HTMLResponse(html, media_type="text/html")


# Strudel ships a Workbox service worker that precaches index.html and serves it
# offline-first. That bypasses the server-side control-panel injection in
# strudel_index (the cached page never gets the panel/Voice button). Override the
# service worker endpoints so existing registrations self-destruct and no new
# ones are created, ensuring every navigation hits the injecting route.
_NO_STORE = {"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"}

_KILL_SWITCH_SW = """
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    try {
      const keys = await caches.keys();
      await Promise.all(keys.map((key) => caches.delete(key)));
    } catch (error) {}
    try {
      await self.registration.unregister();
    } catch (error) {}
    const clients = await self.clients.matchAll({ type: "window" });
    for (const client of clients) {
      try { client.navigate(client.url); } catch (error) {}
    }
  })());
});
""".strip()


@router.get("/sw.js", include_in_schema=False)
async def service_worker_kill_switch() -> Response:
    return Response(
        content=_KILL_SWITCH_SW,
        media_type="application/javascript",
        headers=_NO_STORE,
    )


@router.get("/registerSW.js", include_in_schema=False)
async def register_sw_noop() -> Response:
    return Response(
        content="/* service worker registration disabled by Strudel Voice */",
        media_type="application/javascript",
        headers=_NO_STORE,
    )


@router.get("/{asset_path:path}", include_in_schema=False)
async def strudel_asset_fallback(asset_path: str) -> Response:
    asset = _resolve_strudel_asset(asset_path)
    if asset is None:
        raise HTTPException(status_code=404, detail="resource not found")
    return FileResponse(asset)
