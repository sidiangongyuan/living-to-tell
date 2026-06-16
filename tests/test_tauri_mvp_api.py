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


def test_tauri_daily_quote_returns_full_reference_and_id(monkeypatch):
    client = _tauri_client(monkeypatch)

    created = client.post(
        "/api/library/references",
        json={
            "source_title": "测试书",
            "content": "第一句。\n第二句，应该完整保留。",
            "source_author": "作者",
            "tags": [],
            "kind": "excerpt",
            "usage_kind": "style",
            "personal_note": "",
        },
    )
    assert created.status_code == 201
    ref_id = created.json()["id"]

    quote = client.get("/api/dates/quote?date_str=2024-01-01")
    assert quote.status_code == 200
    data = quote.json()
    assert data["reference_id"] == ref_id
    assert data["text"] == "第一句。\n第二句，应该完整保留。"


def test_tauri_article_export_formats_keep_epigraph_rules(monkeypatch):
    client = _tauri_client(monkeypatch)

    body = "你必须先相信某种回声。\n——《夜航西飞》 柏瑞尔·马卡姆\n\n正文第一段。"
    entry = client.post(
        "/api/articles",
        json={"title": "题记文章", "body": body, "tags": []},
    ).json()

    txt = client.get(f"/api/articles/{entry['id']}/export?format=txt")
    assert txt.status_code == 200
    assert "——《夜航西飞》 柏瑞尔·马卡姆" in txt.text
    assert "正文第一段。" in txt.text

    md = client.get(f"/api/articles/{entry['id']}/export?format=md")
    assert md.status_code == 200
    assert "> 你必须先相信某种回声。" in md.text
    assert "> -- 《夜航西飞》 柏瑞尔·马卡姆" in md.text
    assert md.text.count("《夜航西飞》 柏瑞尔·马卡姆") == 1
    assert "正文第一段。" in md.text


def test_tauri_ai_current_thread_is_scope_aware(monkeypatch):
    client = _tauri_client(monkeypatch)

    entry = client.post(
        "/api/articles",
        json={"title": "会话文章", "body": "正文", "tags": []},
    ).json()

    created = client.get(
        f"/api/ai/threads/current?scope_kind=article&scope_id={entry['id']}&create=true"
    )
    assert created.status_code == 200
    payload = created.json()
    assert payload["thread"]["scope_kind"] == "article"
    assert payload["thread"]["scope_id"] == entry["id"]
    assert payload["messages"] == []

    from deps import get_container

    get_container().ai_thread_repository.add_message(
        thread_id=payload["thread"]["id"],
        role="user",
        content="讨论这个开头",
    )

    restored = client.get(
        f"/api/ai/threads/current?scope_kind=article&scope_id={entry['id']}"
    )
    assert restored.status_code == 200
    restored_payload = restored.json()
    assert restored_payload["thread"]["id"] == payload["thread"]["id"]
    assert restored_payload["messages"][0]["content"] == "讨论这个开头"


def test_tauri_ai_settings_read_save_and_validate(monkeypatch):
    client = _tauri_client(monkeypatch)

    initial = client.get("/api/settings/ai")
    assert initial.status_code == 200
    initial_payload = initial.json()
    assert initial_payload["provider_name"] in {"openai", "gemini", "gemini_cli"}
    assert "status" in initial_payload
    assert "model_presets" in initial_payload

    saved = client.put(
        "/api/settings/ai",
        json={
            "provider_name": "gemini",
            "base_url": "https://generativelanguage.googleapis.com",
            "wire_api": "responses",
            "model": "gemini-2.5-flash",
            "api_key_source": "env:GEMINI_API_KEY",
            "gemini_cli_proxy": "",
        },
    )
    assert saved.status_code == 200
    payload = saved.json()
    assert payload["provider_name"] == "gemini"
    assert payload["model"] == "gemini-2.5-flash"
    assert payload["api_key_source"] == "env:GEMINI_API_KEY"

    cli = client.put(
        "/api/settings/ai",
        json={
            "provider_name": "gemini_cli",
            "base_url": "https://should-be-cleared.example",
            "wire_api": "responses",
            "model": "",
            "api_key_source": "env:IGNORED",
            "gemini_cli_proxy": "http://127.0.0.1:7890",
        },
    )
    assert cli.status_code == 200
    cli_payload = cli.json()
    assert cli_payload["provider_name"] == "gemini_cli"
    assert cli_payload["api_key_source"] == "gemini-cli"
    assert cli_payload["model"] == "gemini-cli-default"

    invalid = client.put(
        "/api/settings/ai",
        json={
            "provider_name": "anthropic",
            "base_url": "",
            "wire_api": "responses",
            "model": "claude",
            "api_key_source": "env:ANTHROPIC_API_KEY",
        },
    )
    assert invalid.status_code == 400


def test_tauri_ai_settings_test_endpoint_uses_preflight(monkeypatch):
    client = _tauri_client(monkeypatch)

    failed = client.post(
        "/api/settings/ai/test",
        json={
            "provider_name": "openai",
            "base_url": "",
            "wire_api": "responses",
            "model": "gpt-4o-mini",
            "api_key_source": "env:WRITER_TEST_MISSING_KEY",
        },
    )
    assert failed.status_code == 200
    assert failed.json()["ok"] is False
    assert "WRITER_TEST_MISSING_KEY" in failed.json()["message"]

    monkeypatch.setenv("WRITER_TEST_PRESENT_KEY", "test-key")
    passed = client.post(
        "/api/settings/ai/test",
        json={
            "provider_name": "openai",
            "base_url": "",
            "wire_api": "responses",
            "model": "gpt-4o-mini",
            "api_key_source": "env:WRITER_TEST_PRESENT_KEY",
        },
    )
    assert passed.status_code == 200
    assert passed.json()["ok"] is True


def test_tauri_ai_settings_import_failures_are_explicit(monkeypatch):
    client = _tauri_client(monkeypatch)

    codex = client.post("/api/settings/ai/import-codex")
    assert codex.status_code in {200, 400, 404}
    if codex.status_code == 200:
        assert codex.json()["config"]["provider_name"] == "openai"

    gemini = client.post("/api/settings/ai/import-gemini")
    assert gemini.status_code in {200, 400, 404}
    if gemini.status_code == 200:
        assert gemini.json()["config"]["provider_name"] == "gemini"
