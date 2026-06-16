"""FastAPI application factory."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Importing deps triggers configure_data_dir() before any writer.* import.
from deps import get_container
from features.ai.routes import router as ai_router
from features.ai_cards.routes import router as ai_cards_router
from features.articles.routes import router as articles_router
from features.backup.routes import router as backup_router
from features.collections.routes import router as collections_router
from features.dates.routes import router as dates_router
from features.library.routes import router as library_router
from features.settings.routes import router as settings_router


_FEATURE_ROUTERS = (
    articles_router,
    collections_router,
    ai_router,
    ai_cards_router,
    dates_router,
    library_router,
    backup_router,
    settings_router,
)


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
    for router in _FEATURE_ROUTERS:
        app.include_router(router)


app = create_app()
