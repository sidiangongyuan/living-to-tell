"""AI Card API for reusable style / character / setting context cards."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

from deps import get_container
from writer.app.container import AppContainer
from writer.domain.models.ai_card import AiCard as DomainCard

from .presets import get_preset_cards

router = APIRouter(prefix="/api/ai-cards", tags=["ai-cards"])
PRESET_SEED_KEY = "tauri.ai_cards.seeded_presets_v1"


class AiCardOut(BaseModel):
    id: str
    title: str
    content: str
    card_type: str
    tags: list[str] = Field(default_factory=list)
    created_at: Optional[str]
    updated_at: Optional[str]


class AiCardCreate(BaseModel):
    title: str
    content: str = ""
    card_type: str = "style"
    tags: list[str] = Field(default_factory=list)


class AiCardUpdate(BaseModel):
    title: str
    content: str
    card_type: str = "style"
    tags: list[str] = Field(default_factory=list)


def _card_to_dto(card: DomainCard) -> AiCardOut:
    return AiCardOut(
        id=card.id,
        title=card.name or "",
        content=card.body or "",
        card_type=card.kind or "style",
        tags=[],
        created_at=card.created_at,
        updated_at=card.updated_at,
    )


def _preset_signature(preset: dict) -> tuple[str, str]:
    return (str(preset.get("title", "")).strip(), str(preset.get("card_type", "style")).strip())


def _seed_presets(container: AppContainer, *, force: bool = False) -> None:
    """Seed built-in samples as normal editable cards once.

    The current repository does not have a system-card flag, so idempotency is
    based on title + kind. This keeps the samples editable/deletable while
    avoiding duplicates on every startup/request.
    """
    if not force and container.settings_repository.get(PRESET_SEED_KEY) == "1":
        return
    existing = {
        (card.name.strip(), card.kind.strip())
        for card in container.ai_card_repository.list_all()
    }
    for preset in get_preset_cards():
        title, kind = _preset_signature(preset)
        if not title or (title, kind) in existing:
            continue
        container.ai_card_repository.create(
            kind=kind or "style",
            name=title,
            body=str(preset.get("content", "")),
        )
        existing.add((title, kind))
    container.settings_repository.set(PRESET_SEED_KEY, "1")


@router.get("", response_model=list[AiCardOut])
def list_cards(
    limit: int = Query(200, ge=1, le=1000),
    card_type: Optional[str] = None,
    container: AppContainer = Depends(get_container),
) -> list[AiCardOut]:
    _seed_presets(container)
    if card_type:
        cards = container.ai_card_repository.list_by_kind(card_type)
    else:
        cards = container.ai_card_repository.list_all()
    return [_card_to_dto(card) for card in cards[:limit]]


@router.get("/search", response_model=list[AiCardOut])
def search_cards(
    q: str,
    limit: int = Query(100, ge=1, le=500),
    container: AppContainer = Depends(get_container),
) -> list[AiCardOut]:
    _seed_presets(container)
    needle = q.strip().lower()
    if not needle:
        return []
    cards = [
        card
        for card in container.ai_card_repository.list_all()
        if needle in (card.name or "").lower()
        or needle in (card.body or "").lower()
        or needle in (card.kind or "").lower()
    ]
    return [_card_to_dto(card) for card in cards[:limit]]


@router.get("/presets/list", response_model=list[dict])
def list_presets() -> list[dict]:
    return get_preset_cards()


@router.post("/presets/generate", status_code=201)
def generate_from_presets(
    container: AppContainer = Depends(get_container),
) -> dict:
    before = len(container.ai_card_repository.list_all())
    _seed_presets(container, force=True)
    cards = container.ai_card_repository.list_all()
    return {
        "created": max(0, len(cards) - before),
        "cards": [_card_to_dto(card).model_dump() for card in cards],
    }


@router.get("/{card_id}", response_model=AiCardOut)
def get_card(
    card_id: str,
    container: AppContainer = Depends(get_container),
) -> AiCardOut:
    card = container.ai_card_repository.get(card_id)
    if not card:
        raise HTTPException(404, "AI Card not found")
    return _card_to_dto(card)


@router.post("", response_model=AiCardOut, status_code=201)
def create_card(
    data: AiCardCreate,
    container: AppContainer = Depends(get_container),
) -> AiCardOut:
    card = container.ai_card_repository.create(
        kind=data.card_type or "style",
        name=data.title,
        body=data.content,
    )
    return _card_to_dto(card)


@router.put("/{card_id}", response_model=AiCardOut)
def update_card(
    card_id: str,
    data: AiCardUpdate,
    container: AppContainer = Depends(get_container),
) -> AiCardOut:
    existing = container.ai_card_repository.get(card_id)
    if not existing:
        raise HTTPException(404, "AI Card not found")
    card = container.ai_card_repository.update(
        card_id,
        kind=data.card_type or existing.kind or "style",
        name=data.title,
        body=data.content,
    )
    if not card:
        raise HTTPException(404, "AI Card not found")
    return _card_to_dto(card)


@router.delete("/{card_id}", status_code=204, response_class=Response)
def delete_card(
    card_id: str,
    container: AppContainer = Depends(get_container),
):
    if not container.ai_card_repository.get(card_id):
        raise HTTPException(404, "AI Card not found")
    container.ai_card_repository.delete(card_id)
