"""FastAPI application factory."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from features.app_meta.routes import router as app_meta_router
from features.ai.routes import router as ai_router
from features.ai_cards.routes import router as ai_cards_router
from features.articles.routes import router as articles_router
from features.backup.routes import router as backup_router
from features.collections.routes import router as collections_router
from features.dates.routes import router as dates_router
from features.library.routes import router as library_router
from features.motifs.routes import router as motifs_router
from features.notes.routes import router as notes_router
from features.onboarding.routes import router as onboarding_router
from features.settings.routes import router as settings_router
from version_info import API_VERSION


_FEATURE_ROUTERS = (
    app_meta_router,
    articles_router,
    collections_router,
    ai_router,
    ai_cards_router,
    dates_router,
    library_router,
    motifs_router,
    notes_router,
    onboarding_router,
    backup_router,
    settings_router,
)


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

    _mount_feature_routers(app)

    return app


def _mount_feature_routers(app: FastAPI) -> None:
    for router in _FEATURE_ROUTERS:
        app.include_router(router)


app = create_app()
