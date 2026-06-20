"""FastAPI application factory."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from features.ai.routes import router as ai_router
from features.ai_cards.routes import router as ai_cards_router
from features.articles.routes import router as articles_router
from features.backup.routes import router as backup_router
from features.collections.routes import router as collections_router
from features.dates.routes import router as dates_router
from features.library.routes import router as library_router
from features.motifs.routes import router as motifs_router
from features.notes.routes import router as notes_router
from features.settings.routes import router as settings_router


_FEATURE_ROUTERS = (
    articles_router,
    collections_router,
    ai_router,
    ai_cards_router,
    dates_router,
    library_router,
    motifs_router,
    notes_router,
    backup_router,
    settings_router,
)

APP_DISPLAY_NAME = "Living to Tell"
APP_VERSION = "0.1.7"
API_VERSION = "2.0.0"
API_CAPABILITIES = [
    "data_location",
    "ai_chat_settings",
    "ai_task_presets",
    "motif_star_map",
]


def create_app() -> FastAPI:
    app = FastAPI(title="Living to Tell API", version=API_VERSION)

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

    @app.get("/api/app/version")
    def app_version() -> dict:
        return {
            "app_name": APP_DISPLAY_NAME,
            "version": APP_VERSION,
            "api_version": API_VERSION,
            "capabilities": API_CAPABILITIES,
        }

    _mount_feature_routers(app)

    return app


def _mount_feature_routers(app: FastAPI) -> None:
    for router in _FEATURE_ROUTERS:
        app.include_router(router)


app = create_app()
