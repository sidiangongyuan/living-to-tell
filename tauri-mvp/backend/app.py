"""FastAPI application factory.

Routers are auto-discovered from ``features/<name>/routes.py`` — each must
expose a module-level ``router = APIRouter(...)``. This keeps feature agents
from ever editing this shared file: they only add their own feature folder.
"""
from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Importing deps triggers configure_data_dir() before any writer.* import.
from deps import get_container


def create_app() -> FastAPI:
    app = FastAPI(title="Writer API (Tauri MVP)", version="2.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    _mount_feature_routers(app)

    @app.on_event("startup")
    def _warm_container() -> None:
        # Build the container eagerly so the first real request is fast and
        # any wiring error surfaces at startup, not mid-request.
        get_container()

    return app


def _mount_feature_routers(app: FastAPI) -> None:
    features_dir = Path(__file__).parent / "features"
    if not features_dir.is_dir():
        return
    for mod in pkgutil.iter_modules([str(features_dir)]):
        if not mod.ispkg:
            continue
        try:
            routes = importlib.import_module(f"features.{mod.name}.routes")
        except ModuleNotFoundError:
            continue
        router = getattr(routes, "router", None)
        if router is not None:
            app.include_router(router)


app = create_app()
