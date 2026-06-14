from __future__ import annotations

import sys
from pathlib import Path


def _tauri_client(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    backend = root / "tauri-mvp" / "backend"
    monkeypatch.setenv("WRITER_USE_DEV_DB", "1")
    sys.path.insert(0, str(backend))
    try:
        from fastapi.testclient import TestClient
        from app import create_app

        return TestClient(create_app())
    finally:
        try:
            sys.path.remove(str(backend))
        except ValueError:
            pass


def test_tauri_ai_cards_seed_and_crud(monkeypatch):
    client = _tauri_client(monkeypatch)

    first = client.get("/api/ai-cards")
    assert first.status_code == 200
    first_cards = first.json()
    assert len(first_cards) >= 5

    second = client.get("/api/ai-cards")
    assert second.status_code == 200
    assert len(second.json()) == len(first_cards)

    created = client.post(
        "/api/ai-cards",
        json={
            "title": "测试卡",
            "content": "内容",
            "card_type": "style",
            "tags": [],
        },
    )
    assert created.status_code == 201
    card_id = created.json()["id"]

    updated = client.put(
        f"/api/ai-cards/{card_id}",
        json={
            "title": "测试卡2",
            "content": "内容2",
            "card_type": "character",
            "tags": [],
        },
    )
    assert updated.status_code == 200
    assert updated.json()["id"] == card_id
    assert updated.json()["card_type"] == "character"

    deleted = client.delete(f"/api/ai-cards/{card_id}")
    assert deleted.status_code == 204


def test_tauri_article_collection_flow(monkeypatch):
    client = _tauri_client(monkeypatch)

    entry_a = client.post(
        "/api/articles",
        json={"title": "A", "body": "甲乙丙", "tags": ["t"]},
    ).json()
    entry_b = client.post(
        "/api/articles",
        json={"title": "B", "body": "hello world", "tags": []},
    ).json()
    collection = client.post(
        "/api/collections",
        json={"title": "C", "description": "D"},
    ).json()

    added = client.post(
        f"/api/collections/{collection['id']}/articles",
        json={"entry_ids": [entry_a["id"], entry_b["id"], entry_a["id"]]},
    )
    assert added.status_code == 201
    assert [article["id"] for article in added.json()] == [entry_a["id"], entry_b["id"]]

    reordered = client.put(
        f"/api/collections/{collection['id']}/articles/order",
        json={"entry_ids": [entry_b["id"], entry_a["id"]]},
    )
    assert reordered.status_code == 200
    assert [article["id"] for article in reordered.json()] == [entry_b["id"], entry_a["id"]]

    containing = client.get(f"/api/collections/for-entry/{entry_a['id']}")
    assert containing.status_code == 200
    assert containing.json()[0]["id"] == collection["id"]

    exported = client.get(f"/api/collections/{collection['id']}/export?format=md")
    assert exported.status_code == 200
    assert "# C" in exported.text
    assert "## A" in exported.text

    removed = client.delete(
        f"/api/collections/{collection['id']}/articles/{entry_a['id']}"
    )
    assert removed.status_code == 204
