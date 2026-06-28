from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        summary="Backend service for the Strudel real-time voice sampling workflow.",
    )

    # The backend uses no cookies, auth headers, or any other credentials: the
    # control panel and Strudel assets are served same-origin (CORS does not even
    # apply there), and the only cross-origin callers are anonymous. Keep
    # allow_credentials False so the explicit origin allowlist actually takes
    # effect — enabling credentials would forbid wildcards and grant credentialed
    # cross-origin access this service never needs.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router, prefix=settings.api_prefix)
    settings.samples_root.mkdir(parents=True, exist_ok=True)
    app.mount("/samples", StaticFiles(directory=settings.samples_root), name="samples")
    strudel_dist = Path(__file__).resolve().parents[1] / "static" / "strudel"
    if strudel_dist.exists():
        app.mount("/strudel", StaticFiles(directory=strudel_dist, html=True), name="strudel")
    return app


app = create_app()
