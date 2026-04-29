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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
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
