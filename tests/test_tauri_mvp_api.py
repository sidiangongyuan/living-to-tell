from __future__ import annotations

import json
import hashlib
import sqlite3
import time
from types import SimpleNamespace
import sys
import uuid
from pathlib import Path
from urllib import error as urlerror


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


def test_tauri_app_version_capabilities(monkeypatch):
    client = _tauri_client(monkeypatch)
    from version_info import APP_VERSION

    response = client.get("/api/app/version")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["app_name"] == "Living to Tell"
    assert payload["version"] == APP_VERSION
    assert payload["api_version"] == "2.0.0"
    assert {
        "data_location",
        "ai_chat_settings",
        "ai_task_presets",
        "ai_profiles",
        "ai_task_compare",
        "ai_jobs",
        "motif_star_map",
        "motif_ai_enrichment",
        "motif_ai_enrichment_jobs",
        "update_check",
        "article_versions",
        "collection_outline",
        "sample_project",
    }.issubset(
        set(payload["capabilities"])
    )

def test_tauri_onboarding_sample_project_is_explicit_and_disposable(monkeypatch):
    client = _tauri_client(monkeypatch)

    # Start from a clean sample marker without assuming an empty user database.
    client.delete("/api/onboarding/sample-project")
    user_article = client.post(
        "/api/articles",
        json={"title": "用户自己的文章", "body": "不要被示例项目清理。", "tags": ["用户数据"]},
    )
    assert user_article.status_code == 201, user_article.text
    user_article_id = user_article.json()["id"]

    initial = client.get("/api/onboarding/sample-project")
    assert initial.status_code == 200, initial.text
    assert initial.json()["installed"] is False

    created = client.post("/api/onboarding/sample-project")
    assert created.status_code == 201, created.text
    created_payload = created.json()
    assert created_payload["action"] == "created"
    assert created_payload["installed"] is True
    assert len(created_payload["entry_ids"]) == 2
    assert len(created_payload["reference_ids"]) == 1
    assert len(created_payload["ai_card_ids"]) == 1
    assert len(created_payload["note_ids"]) == 1

    again = client.post("/api/onboarding/sample-project")
    assert again.status_code == 201, again.text
    assert again.json()["action"] == "already_installed"
    assert again.json()["entry_ids"] == created_payload["entry_ids"]

    removed = client.delete("/api/onboarding/sample-project")
    assert removed.status_code == 200, removed.text
    assert removed.json()["action"] == "removed"
    assert removed.json()["installed"] is False

    user_still_exists = client.get(f"/api/articles/{user_article_id}")
    assert user_still_exists.status_code == 200, user_still_exists.text
    assert user_still_exists.json()["title"] == "用户自己的文章"


def test_tauri_onboarding_sample_project_rolls_back_partial_create(monkeypatch):
    client = _tauri_client(monkeypatch)
    from deps import get_container

    client.delete("/api/onboarding/sample-project")
    container = get_container()

    def fail_collection_create(*_args, **_kwargs):
        raise RuntimeError("simulated collection failure")

    monkeypatch.setattr(container.collection_repository, "create", fail_collection_create)

    response = client.post("/api/onboarding/sample-project")

    assert response.status_code == 500, response.text
    assert "已回滚" in response.json()["detail"]

    entries = client.get("/api/articles?limit=500")
    assert entries.status_code == 200, entries.text
    assert all(not item["title"].startswith("示例｜") for item in entries.json())


def test_tauri_app_update_check_reports_latest_release(monkeypatch):
    client = _tauri_client(monkeypatch)
    from features.app_meta import routes as app_routes
    from version_info import APP_VERSION

    app_routes.UPDATE_CACHE["payload"] = None
    app_routes.UPDATE_CACHE["expires_at"] = 0.0
    calls = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(
                {
                    "tag_name": "living-to-tell-v0.1.99",
                    "name": "Living to Tell Preview 0.1.99",
                    "html_url": "https://github.com/sidiangongyuan/living-to-tell/releases/tag/living-to-tell-v0.1.99",
                    "published_at": "2026-06-26T01:02:03Z",
                    "body": "## 0.1.99\n\nAdded update notifications.",
                    "assets": [
                        {
                            "name": "LivingToTell_0.1.99_x64_zh-CN.msi",
                            "browser_download_url": "https://example.test/LivingToTell_0.1.99_x64_zh-CN.msi",
                            "digest": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                        },
                        {
                            "name": "LivingToTell_0.1.99_x64-setup.exe",
                            "browser_download_url": "https://example.test/LivingToTell_0.1.99_x64-setup.exe",
                            "digest": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                        },
                    ],
                }
            ).encode("utf-8")

    def fake_urlopen(req, timeout):
        calls.append(
            {
                "url": req.full_url,
                "timeout": timeout,
                "accept": req.headers.get("Accept"),
            }
        )
        return FakeResponse()

    monkeypatch.setattr(app_routes.urlrequest, "urlopen", fake_urlopen)

    response = client.get("/api/app/update-check?force=true")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "update_available"
    assert payload["current_version"] == APP_VERSION
    assert payload["latest_version"] == "0.1.99"
    assert payload["release_name"] == "Living to Tell Preview 0.1.99"
    assert payload["download_name"] == "LivingToTell_0.1.99_x64-setup.exe"
    assert payload["download_url"] == "https://example.test/LivingToTell_0.1.99_x64-setup.exe"
    assert payload["download_sha256"] == "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    assert "应用内" in payload["message"]
    assert calls == [
        {
            "url": app_routes.GITHUB_LATEST_RELEASE_URL,
            "timeout": 15,
            "accept": "application/vnd.github+json",
        }
    ]


def test_tauri_app_update_check_returns_friendly_error(monkeypatch):
    client = _tauri_client(monkeypatch)
    from features.app_meta import routes as app_routes
    from version_info import APP_VERSION

    app_routes.UPDATE_CACHE["payload"] = None
    app_routes.UPDATE_CACHE["expires_at"] = 0.0

    def fake_urlopen(req, timeout):
        raise urlerror.URLError("offline")

    monkeypatch.setattr(app_routes.urlrequest, "urlopen", fake_urlopen)

    response = client.get("/api/app/update-check?force=true")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["current_version"] == APP_VERSION
    assert "暂时无法检查更新" in payload["message"]


def test_tauri_app_update_check_falls_back_to_latest_redirect(monkeypatch):
    client = _tauri_client(monkeypatch)
    from features.app_meta import routes as app_routes

    app_routes.UPDATE_CACHE["payload"] = None
    app_routes.UPDATE_CACHE["expires_at"] = 0.0

    class FakeRedirectResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def geturl(self):
            return "https://github.com/sidiangongyuan/living-to-tell/releases/tag/living-to-tell-v0.1.99"

    def fake_urlopen(req, timeout):
        if req.full_url == app_routes.GITHUB_LATEST_RELEASE_URL:
            raise urlerror.URLError("api offline")
        return FakeRedirectResponse()

    monkeypatch.setattr(app_routes.urlrequest, "urlopen", fake_urlopen)

    response = client.get("/api/app/update-check?force=true")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "update_available"
    assert payload["source"] == "github_releases_latest_redirect"
    assert payload["latest_version"] == "0.1.99"
    assert payload["download_name"] == "LivingToTell_0.1.99_x64-setup.exe"
    assert payload["download_url"].endswith(
        "/releases/download/living-to-tell-v0.1.99/LivingToTell_0.1.99_x64-setup.exe"
    )


def test_tauri_app_update_download_saves_and_verifies_installer(monkeypatch, tmp_path):
    client = _tauri_client(monkeypatch)
    from features.app_meta import routes as app_routes

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    installer_bytes = b"fake installer bytes"
    expected_sha = hashlib.sha256(installer_bytes).hexdigest()

    class FakeDownloadResponse:
        def __init__(self):
            self._offset = 0

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self, size=-1):
            if self._offset >= len(installer_bytes):
                return b""
            if size is None or size < 0:
                size = len(installer_bytes)
            chunk = installer_bytes[self._offset : self._offset + size]
            self._offset += len(chunk)
            return chunk

    def fake_open_url(req, timeout):
        assert req.full_url.endswith("/LivingToTell_0.1.25_x64-setup.exe")
        assert timeout == 120
        return FakeDownloadResponse()

    monkeypatch.setattr(app_routes, "_open_url", fake_open_url)

    response = client.post(
        "/api/app/update-download",
        json={
            "download_url": "https://github.com/sidiangongyuan/living-to-tell/releases/download/living-to-tell-v0.1.25/LivingToTell_0.1.25_x64-setup.exe",
            "download_name": "LivingToTell_0.1.25_x64-setup.exe",
            "expected_sha256": expected_sha,
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "downloaded"
    assert payload["sha256"] == expected_sha.upper()
    assert Path(payload["file_path"]).read_bytes() == installer_bytes


def test_tauri_article_versions_create_restore_clone(monkeypatch):
    client = _tauri_client(monkeypatch)

    created = client.post(
        "/api/articles",
        json={"title": "版本测试", "body": "第一版正文", "tags": ["历史"]},
    )
    assert created.status_code == 201, created.text
    article = created.json()

    version = client.post(
        f"/api/articles/{article['id']}/versions",
        json={"version_type": "manual_checkpoint", "label": "第一版"},
    )
    assert version.status_code == 201, version.text
    payload = version.json()
    assert payload["content"] == "第一版正文"
    assert payload["title_snapshot"] == "版本测试"
    assert payload["tags"] == ["历史"]
    assert payload["label"] == "第一版"

    updated = client.put(
        f"/api/articles/{article['id']}",
        json={"title": "版本测试", "body": "第二版正文", "tags": ["历史"]},
    )
    assert updated.status_code == 200, updated.text

    restore = client.post(f"/api/articles/{article['id']}/versions/{payload['id']}/restore")
    assert restore.status_code == 200, restore.text
    restore_payload = restore.json()
    assert restore_payload["entry"]["body"] == "第一版正文"
    assert restore_payload["snapshot_version_id"]

    clone = client.post(f"/api/articles/{article['id']}/versions/{payload['id']}/clone")
    assert clone.status_code == 201, clone.text
    clone_payload = clone.json()
    assert clone_payload["body"] == "第一版正文"
    assert clone_payload["tags"] == ["历史"]
    assert clone_payload["id"] != article["id"]


def test_tauri_collection_outline_crud(monkeypatch):
    client = _tauri_client(monkeypatch)

    collection = client.post(
        "/api/collections",
        json={"title": "长篇项目测试", "description": "大纲容器"},
    )
    assert collection.status_code == 201, collection.text
    collection_id = collection.json()["id"]
    article = client.post(
        "/api/articles",
        json={"title": "雨夜来信", "body": "正文", "tags": []},
    ).json()

    created = client.post(
        f"/api/collections/{collection_id}/outline",
        json={
            "title": "雨夜来信",
            "item_type": "scene",
            "status": "drafting",
            "summary": "一封信推动关系。",
            "entry_id": article["id"],
            "tags": ["爱情", "等待"],
            "target_word_count": 2500,
        },
    )
    assert created.status_code == 201, created.text
    item = created.json()
    assert item["tags"] == ["爱情", "等待"]
    assert item["entry_id"] == article["id"]

    listed = client.get(f"/api/collections/{collection_id}/outline")
    assert listed.status_code == 200, listed.text
    assert [row["id"] for row in listed.json()] == [item["id"]]

    updated = client.put(
        f"/api/collections/{collection_id}/outline/{item['id']}",
        json={
            **item,
            "title": "雨夜来信修订",
            "item_type": "chapter",
            "status": "revising",
            "tags": ["等待"],
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["title"] == "雨夜来信修订"
    assert updated.json()["item_type"] == "chapter"

    delete = client.delete(f"/api/collections/{collection_id}/outline/{item['id']}")
    assert delete.status_code == 204, delete.text
    assert client.get(f"/api/collections/{collection_id}/outline").json() == []


def test_tauri_ai_cards_do_not_seed_samples_and_crud_tags(monkeypatch):
    client = _tauri_client(monkeypatch)
    from deps import get_container

    container = get_container()
    container.connection.execute("DELETE FROM ai_cards")
    container.settings_repository.delete("tauri.ai_cards.seeded_presets_v1")

    first = client.get("/api/ai-cards")
    assert first.status_code == 200
    first_cards = first.json()
    assert first_cards == []

    second = client.get("/api/ai-cards")
    assert second.status_code == 200
    assert second.json() == []

    preset_list = client.get("/api/ai-cards/presets/list")
    assert preset_list.status_code == 200
    assert preset_list.json() == []

    preset_generate = client.post("/api/ai-cards/presets/generate")
    assert preset_generate.status_code == 410
    assert client.get("/api/ai-cards").json() == []

    created = client.post(
        "/api/ai-cards",
        json={
            "title": "测试卡",
            "content": "内容",
            "card_type": "style",
            "tags": ["节奏", "节奏", "结构"],
        },
    )
    assert created.status_code == 201
    assert created.json()["tags"] == ["节奏", "结构"]
    card_id = created.json()["id"]

    updated = client.put(
        f"/api/ai-cards/{card_id}",
        json={
            "title": "测试卡2",
            "content": "内容2",
            "card_type": "character",
            "tags": ["人物"],
        },
    )
    assert updated.status_code == 200
    assert updated.json()["id"] == card_id
    assert updated.json()["card_type"] == "character"
    assert updated.json()["tags"] == ["人物"]

    scene = client.post(
        "/api/ai-cards",
        json={
            "title": "等待回应",
            "content": "【场景原型】\n等待关系回应",
            "card_type": "scene",
            "tags": [],
        },
    )
    assert scene.status_code == 201

    search = client.get("/api/ai-cards/search?q=等待&card_type=scene&limit=10")
    assert search.status_code == 200
    search_payload = search.json()
    assert search_payload
    assert all(card["card_type"] == "scene" for card in search_payload)
    assert any(card["id"] == scene.json()["id"] for card in search_payload)

    tag_search = client.get("/api/ai-cards/search?q=人物&limit=10")
    assert tag_search.status_code == 200
    assert any(card["id"] == card_id for card in tag_search.json())

    rejected = client.post(
        "/api/ai-cards",
        json={
            "title": "旧设定",
            "content": "不再支持",
            "card_type": "setting",
            "tags": [],
        },
    )
    assert rejected.status_code == 400

    deleted = client.delete(f"/api/ai-cards/{card_id}")
    assert deleted.status_code == 204


def test_tauri_ai_cards_delete_legacy_setting_cards_once(monkeypatch):
    client = _tauri_client(monkeypatch)
    from deps import get_container

    container = get_container()
    container.settings_repository.delete("tauri.ai_cards.deleted_setting_cards_v1")
    legacy = container.ai_card_repository.create(
        kind="setting",
        name="旧设定卡",
        body="旧内容",
    )

    response = client.get("/api/ai-cards")
    assert response.status_code == 200
    assert all(card["id"] != legacy.id for card in response.json())
    assert all(card["card_type"] != "setting" for card in response.json())
    assert container.ai_card_repository.get(legacy.id) is None
    assert container.settings_repository.get("tauri.ai_cards.deleted_setting_cards_v1") == "1"


def test_tauri_ai_card_generate_draft_uses_strict_json(monkeypatch):
    client = _tauri_client(monkeypatch)
    from deps import get_container

    class FakeTaskService:
        def __init__(self):
            self.calls = []

        def generate_from_messages(self, messages, *, cost_tier):
            self.calls.append({"messages": messages, "cost_tier": cost_tier})
            return SimpleNamespace(
                content=json.dumps(
                    {
                        "title": "赌注式情书",
                        "card_type": "scene",
                        "content": "【场景原型】\n用带赌注的表达推动关系。\n\n【参考原文（可选）】\n无",
                    },
                    ensure_ascii=False,
                )
            )

    fake = FakeTaskService()
    get_container().ai_task_service = fake

    response = client.post(
        "/api/ai-cards/generate-draft",
        json={
            "card_type": "scene",
            "source_text": "长期暧昧后，主角写下一封带赌注的信。",
            "keep_source_quotes": False,
            "cost_tier": "strong",
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["title"] == "赌注式情书"
    assert payload["card_type"] == "scene"
    assert "【场景原型】" in payload["content"]
    assert fake.calls[-1]["cost_tier"].value == "strong"
    assert "不要保留原文摘录" in fake.calls[-1]["messages"][1]["content"]


def test_tauri_ai_card_generate_draft_rejects_bad_json(monkeypatch):
    client = _tauri_client(monkeypatch)
    from deps import get_container

    class FakeTaskService:
        def generate_from_messages(self, messages, *, cost_tier):
            return SimpleNamespace(content="not json")

    get_container().ai_task_service = FakeTaskService()

    response = client.post(
        "/api/ai-cards/generate-draft",
        json={
            "card_type": "scene",
            "source_text": "一段材料",
        },
    )

    assert response.status_code == 502


def test_tauri_ai_card_generate_draft_sanitizes_html_errors(monkeypatch):
    client = _tauri_client(monkeypatch)
    from deps import get_container

    class FakeTaskService:
        def generate_from_messages(self, messages, *, cost_tier):
            raise RuntimeError(
                "AI request failed: <!doctype html><html><title>403 | Forbidden</title></html>"
            )

    get_container().ai_task_service = FakeTaskService()

    response = client.post(
        "/api/ai-cards/generate-draft",
        json={
            "card_type": "scene",
            "source_text": "一段材料",
        },
    )

    assert response.status_code == 500
    detail = response.json()["detail"]
    assert "AI 卡片生成失败" in detail
    assert "网页错误页" in detail
    assert "<!doctype html>" not in detail


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


def test_tauri_article_writing_notes_crud(monkeypatch):
    client = _tauri_client(monkeypatch)

    entry = client.post(
        "/api/articles",
        json={"title": "便签文章", "body": "正文", "tags": []},
    ).json()
    other = client.post(
        "/api/articles",
        json={"title": "另一篇", "body": "正文", "tags": []},
    ).json()

    created = client.post(
        f"/api/articles/{entry['id']}/notes",
        json={"body": "下一段写雨声。", "pinned": True},
    )
    assert created.status_code == 201
    note = created.json()
    assert note["entry_id"] == entry["id"]
    assert note["body"] == "下一段写雨声。"
    assert note["pinned"] is True
    assert note["status"] == "open"

    listed = client.get(f"/api/articles/{entry['id']}/notes")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [note["id"]]

    other_listed = client.get(f"/api/articles/{other['id']}/notes")
    assert other_listed.status_code == 200
    assert other_listed.json() == []

    updated = client.put(
        f"/api/articles/{entry['id']}/notes/{note['id']}",
        json={"body": "下一段写雨声和旧楼梯。"},
    )
    assert updated.status_code == 200
    assert updated.json()["body"] == "下一段写雨声和旧楼梯。"

    unpinned = client.put(
        f"/api/articles/{entry['id']}/notes/{note['id']}/pinned",
        json={"pinned": False},
    )
    assert unpinned.status_code == 200
    assert unpinned.json()["pinned"] is False

    done = client.put(
        f"/api/articles/{entry['id']}/notes/{note['id']}/done",
        json={"done": True},
    )
    assert done.status_code == 200
    assert done.json()["status"] == "done"

    open_only = client.get(f"/api/articles/{entry['id']}/notes?include_done=false")
    assert open_only.status_code == 200
    assert open_only.json() == []

    restored = client.put(
        f"/api/articles/{entry['id']}/notes/{note['id']}/done",
        json={"done": False},
    )
    assert restored.status_code == 200
    assert restored.json()["status"] == "open"

    wrong_article = client.put(
        f"/api/articles/{other['id']}/notes/{note['id']}",
        json={"body": "不该能改"},
    )
    assert wrong_article.status_code == 404

    deleted = client.delete(f"/api/articles/{entry['id']}/notes/{note['id']}")
    assert deleted.status_code == 204
    assert client.get(f"/api/articles/{entry['id']}/notes").json() == []


def test_tauri_library_allows_draft_reference_without_source(monkeypatch):
    client = _tauri_client(monkeypatch)

    created = client.post(
        "/api/library/references",
        json={
            "source_title": "",
            "content": "新标本",
            "source_author": "",
            "tags": [],
            "kind": "excerpt",
            "usage_kind": "style",
            "personal_note": "",
        },
    )
    assert created.status_code == 201
    data = created.json()
    assert data["source_title"] == ""
    assert data["content"] == "新标本"

    updated = client.put(
        f"/api/library/references/{data['id']}",
        json={
            "source_title": "",
            "content": "后来补正文",
            "source_author": "",
            "tags": [],
            "kind": "excerpt",
            "usage_kind": "imagery",
            "personal_note": "先不填来源",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["source_title"] == ""
    assert updated.json()["usage_kind"] == "imagery"

    empty_body = client.post(
        "/api/library/references",
        json={
            "source_title": "",
            "content": "   ",
            "source_author": "",
            "tags": [],
        },
    )
    assert empty_body.status_code == 400
    assert "content is required" in empty_body.json()["detail"]


def test_tauri_library_round_trips_frontend_usage_kinds(monkeypatch):
    client = _tauri_client(monkeypatch)
    frontend_usage_kinds = [
        "style",
        "imagery",
        "structure",
        "rhetoric",
        "diction",
        "reflection",
        "setting",
        "technique",
        "other",
    ]

    created = client.post(
        "/api/library/references",
        json={
            "source_title": "用途测试",
            "content": "标本正文",
            "source_author": "",
            "tags": [],
            "kind": "excerpt",
            "usage_kind": "style",
            "personal_note": "",
        },
    )
    assert created.status_code == 201
    ref_id = created.json()["id"]

    for usage_kind in frontend_usage_kinds:
        updated = client.put(
            f"/api/library/references/{ref_id}",
            json={
                "source_title": "用途测试",
                "content": "标本正文",
                "source_author": "",
                "tags": [],
                "kind": "excerpt",
                "usage_kind": usage_kind,
                "personal_note": "",
            },
        )
        assert updated.status_code == 200
        assert updated.json()["usage_kind"] == usage_kind


def test_tauri_motifs_create_excerpt_and_graph(monkeypatch):
    client = _tauri_client(monkeypatch)

    entry = client.post(
        "/api/articles",
        json={"title": "花园", "body": "玫瑰在夜里像血一样醒着。", "tags": []},
    ).json()

    created = client.post(
        "/api/motifs/excerpts",
        json={
            "source_kind": "article",
            "source_id": entry["id"],
            "excerpt_text": "玫瑰在夜里像血一样醒着。",
            "selection_start": 0,
            "selection_end": 13,
            "motif_names": ["玫瑰", "血"],
        },
    )
    assert created.status_code == 201, created.text
    excerpt = created.json()
    assert excerpt["source_exists"] is True
    assert excerpt["source_current_title"] == "花园"
    assert excerpt["motif_names"] == ["玫瑰", "血"]

    motifs = client.get("/api/motifs").json()
    by_name = {motif["name"]: motif for motif in motifs}
    assert set(by_name) >= {"玫瑰", "血"}
    assert by_name["玫瑰"]["excerpt_count"] == 1

    graph = client.get("/api/motifs/graph?limit=20").json()
    assert {node["name"] for node in graph["nodes"]} >= {"玫瑰", "血"}
    assert graph["edges"][0]["shared_excerpts"] == 1
    assert graph["edges"][0]["shared_sources"] == 1

    rose_id = by_name["玫瑰"]["id"]
    listed = client.get(f"/api/motifs/{rose_id}/excerpts").json()
    assert [item["id"] for item in listed] == [excerpt["id"]]

    local_graph = client.get(f"/api/motifs/{rose_id}/graph").json()
    assert local_graph["nodes"][0]["id"] == rose_id
    assert local_graph["nodes"][0]["is_center"] is True


def test_tauri_motifs_enrich_draft_uses_context_and_does_not_mutate(monkeypatch):
    client = _tauri_client(monkeypatch)
    from deps import get_container

    entry = client.post(
        "/api/articles",
        json={"title": "神话", "body": "他在归来时发现村庄已经把他当作一个传说。", "tags": []},
    ).json()
    motif = client.post(
        "/api/motifs",
        json={
            "name": "神话模式",
            "aliases": ["mythic pattern"],
            "note": "已有笔记：循环、归来与仪式。",
            "tags": ["写作手法"],
        },
    ).json()
    client.post(
        "/api/motifs/excerpts",
        json={
            "source_kind": "article",
            "source_id": entry["id"],
            "source_title_snapshot": entry["title"],
            "excerpt_text": "他在归来时发现村庄已经把他当作一个传说。",
            "selection_start": 0,
            "selection_end": 22,
            "motif_ids": [motif["id"]],
        },
    )

    class FakeTaskService:
        def __init__(self):
            self.calls = []

        def generate_from_messages(self, messages, *, cost_tier, model_override=None):
            self.calls.append(
                {"messages": messages, "cost_tier": cost_tier, "model_override": model_override}
            )
            return SimpleNamespace(
                content=json.dumps(
                    {
                        "title": "神话模式短卡",
                        "concept": "神话模式",
                        "aliases": ["神话结构", "原型叙事"],
                        "tags": ["写作手法", "叙事模式"],
                        "note": (
                            "【一句话定义】\n把个人遭遇放进近似仪式或原型的轨道。\n\n"
                            "【核心张力】\n个人选择与古老结构互相挤压。\n\n"
                            "【写作功能】\n让普通事件带上命运感。\n\n"
                            "【场景触发】\n归来、牺牲、试炼、命名。\n\n"
                            "【人物表现】\n人物像在重复一个比自己更老的动作。\n\n"
                            "【意象转译】\n门槛、火、面具、河流。\n\n"
                            "【短例子】\n他回到村口时，所有人都沉默。"
                            "孩子们喊出的不是他的名字，而是旧故事里的称号。"
                            "他这才意识到，归来不是结束，而是被推上祭台。\n\n"
                            "【关联建议】\n原型、仪式、牺牲。\n\n"
                            "【误用提醒】\n不要把神话感写成空洞宏大词。\n\n"
                            "【微练习】\n把一次回家写成一次试炼。\n\n"
                            "【来源线索（需核对）】\n- 未能联网核对。"
                        ),
                        "related_suggestions": ["原型", "仪式", "牺牲"],
                        "source_hints": [
                            {
                                "title": "未能联网核对",
                                "url": None,
                                "note": "模型未返回可核对来源。",
                            }
                        ],
                        "reference_candidates": [
                            {
                                "text": "所谓神话，就是对世界的一种叙事秩序。",
                                "source_author": "测试作者",
                                "source_title": "测试书名",
                                "source_note": "AI 候选，需核对。",
                                "reason": "用于测试候选句结构。",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                provider="fake",
                model="fake-strong",
                transport="fake",
            )

    fake = FakeTaskService()
    get_container().ai_task_service = fake

    response = client.post(
        "/api/motifs/enrich-draft",
        json={
            "motif_id": motif["id"],
            "concept": "神话模式",
            "direction": "作为写作手法",
            "include_excerpts": True,
            "request_web_context": True,
            "profile_id": "default",
            "cost_tier": "strong",
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["title"] == "神话模式短卡"
    assert "【短例子】" in payload["note"]
    assert payload["aliases"] == ["神话结构", "原型叙事"]
    assert payload["profile"]["definition"] == "把个人遭遇放进近似仪式或原型的轨道。"
    assert payload["related_suggestions"] == ["原型", "仪式", "牺牲"]
    assert payload["source_hints"][0]["title"] == "未能联网核对"
    assert payload["reference_candidates"][0]["source_author"] == "测试作者"
    prompt = fake.calls[-1]["messages"][1]["content"]
    assert "已有笔记：循环、归来与仪式" in prompt
    assert "他在归来时发现村庄已经把他当作一个传说" in prompt
    assert "请求“联网补充”" in prompt
    assert "他人评论" in prompt
    assert "后世引用" in prompt
    assert "文学或影视作品中对该意象/概念的使用方式" in prompt
    assert "如果请求联网补充，可以给 4-10 条" in prompt
    assert fake.calls[-1]["cost_tier"].value == "strong"
    unchanged = client.get(f"/api/motifs/{motif['id']}").json()
    assert unchanged["note"] == "已有笔记：循环、归来与仪式。"
    assert unchanged["profile"]["definition"] == ""


def test_tauri_motifs_apply_reference_candidates_imports_reference_excerpt(monkeypatch):
    client = _tauri_client(monkeypatch)

    suffix = uuid.uuid4().hex[:8]
    motif = client.post(
        "/api/motifs",
        json={
            "name": f"测试意象｜常人｜{suffix}",
            "tags": ["哲学概念"],
            "profile": {
                "definition": "人在公共意见中失去自己的判断。",
                "core_tension": "",
                "writing_functions": [],
                "scene_triggers": [],
                "character_signals": [],
                "imagery_translations": [],
                "short_examples": [],
                "misuse_warnings": [],
                "micro_exercises": [],
                "source_hints": [],
            },
        },
    )
    assert motif.status_code == 201, motif.text
    motif_payload = motif.json()

    candidate = {
        "text": f"测试句子 {suffix}：大家都这样说，于是他也这样说。",
        "source_author": "测试作者",
        "source_title": "测试书名",
        "source_note": "AI 候选，需核对。",
        "reason": "体现常人状态。",
    }
    response = client.post(
        f"/api/motifs/{motif_payload['id']}/reference-candidates",
        json={
            "candidates": [
                candidate,
                {
                    "text": "来源不足的句子",
                    "source_author": "",
                    "source_title": "",
                    "source_note": "",
                    "reason": "",
                },
            ]
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert len(payload["imported"]) == 1
    assert payload["skipped"]
    assert payload["imported"][0]["source_author"] == "测试作者"

    again = client.post(
        f"/api/motifs/{motif_payload['id']}/reference-candidates",
        json={"candidates": [candidate]},
    )
    assert again.status_code == 200, again.text
    assert again.json()["imported"][0]["reused_reference"] is True
    assert again.json()["imported"][0]["excerpt_id"] == payload["imported"][0]["excerpt_id"]

    excerpts = client.get(f"/api/motifs/{motif_payload['id']}/excerpts")
    assert excerpts.status_code == 200, excerpts.text
    listed = excerpts.json()
    assert len(listed) == 1
    assert listed[0]["source_kind"] == "reference"
    assert listed[0]["excerpt_text"] == candidate["text"]
    assert listed[0]["source_current_title"] == "测试书名"


def test_tauri_motifs_enrich_draft_new_concept_does_not_create_node(monkeypatch):
    client = _tauri_client(monkeypatch)
    from deps import get_container

    suffix = uuid.uuid4().hex[:8]
    concept = f"海德格尔的常人-{suffix}"

    class FakeTaskService:
        def generate_from_messages(self, messages, *, cost_tier, model_override=None):
            return SimpleNamespace(
                content=json.dumps(
                    {
                        "title": concept,
                        "concept": concept,
                        "aliases": ["das Man"],
                        "tags": ["哲学概念"],
                        "note": (
                            "【一句话定义】\n人在公共意见中失去自己的判断。\n\n"
                            "【核心张力】\n自我选择与平均化生活互相拉扯。\n\n"
                            "【写作功能】\n制造人物被日常吞没的压力。\n\n"
                            "【场景触发】\n所有人都说这样才正常。\n\n"
                            "【人物表现】\n人物不断引用别人说的话。\n\n"
                            "【意象转译】\n走廊、广播、统一制服。\n\n"
                            "【短例子】\n他没有被命令沉默。"
                            "只是每个人都替他准备好了该说的话。"
                            "他说出口时，甚至听不出那是不是自己的声音。\n\n"
                            "【关联建议】\n异化、从众、日常性。\n\n"
                            "【误用提醒】\n不要把常人简单写成庸俗群众。\n\n"
                            "【微练习】\n写一个人物被“大家都这样”逼退的瞬间。\n\n"
                            "【来源线索（需核对）】\n- 未请求联网补充。"
                        ),
                        "related_suggestions": ["异化", "从众"],
                        "source_hints": [],
                    },
                    ensure_ascii=False,
                )
            )

    get_container().ai_task_service = FakeTaskService()

    response = client.post(
        "/api/motifs/enrich-draft",
        json={"concept": concept, "include_excerpts": False},
    )

    assert response.status_code == 200, response.text
    assert response.json()["concept"] == concept
    found = client.get(f"/api/motifs?q={suffix}&limit=10")
    assert found.status_code == 200
    assert all(item["name"] != concept for item in found.json())


def test_tauri_motifs_enrichment_job_runs_in_background_and_keeps_result(monkeypatch):
    client = _tauri_client(monkeypatch)
    from deps import get_container
    import threading

    concept = f"后台任务概念-{uuid.uuid4().hex[:8]}"
    release_provider = threading.Event()

    class BlockingTaskService:
        def generate_from_messages(self, messages, *, cost_tier, model_override=None):
            assert release_provider.wait(3), "provider was not released by the test"
            return SimpleNamespace(
                content=json.dumps(
                    {
                        "title": concept,
                        "concept": concept,
                        "aliases": ["后台别名"],
                        "tags": ["后台任务"],
                        "note": (
                            "【一句话定义】\n后台任务定义。\n\n"
                            "【核心张力】\n等待与恢复。\n\n"
                            "【写作功能】\n让长请求可被找回。\n\n"
                            "【场景触发】\n模型迟迟不返回。\n\n"
                            "【人物表现】\n人物继续做别的事。\n\n"
                            "【意象转译】\n灯、队列、回声。\n\n"
                            "【短例子】\n他关上窗，炉火还在慢慢烧。\n\n"
                            "【关联建议】\n等待、回声。\n\n"
                            "【误用提醒】\n不要把进度写成假百分比。\n\n"
                            "【微练习】\n写一个关闭界面后仍在发生的动作。\n\n"
                            "【来源线索（需核对）】\n- 未请求联网补充。"
                        ),
                        "related_suggestions": ["等待", "回声"],
                        "source_hints": [],
                        "reference_candidates": [],
                    },
                    ensure_ascii=False,
                ),
                provider="fake",
                model="fake-model",
                transport="fake",
            )

    get_container().ai_task_service = BlockingTaskService()

    created = client.post(
        "/api/ai/jobs/motif-enrichment",
        json={"concept": concept, "include_excerpts": False, "profile_id": "default"},
    )
    assert created.status_code == 200, created.text
    payload = created.json()
    assert payload["job_id"]
    assert payload["kind"] == "motif_enrichment"
    assert payload["concept"] == concept
    assert payload["status"] in {
        "queued",
        "preparing_context",
        "sending_request",
        "waiting_model",
    }
    assert payload["result"] is None

    release_provider.set()
    deadline = time.time() + 4
    final = None
    while time.time() < deadline:
        response = client.get(f"/api/ai/jobs/{payload['job_id']}")
        assert response.status_code == 200, response.text
        final = response.json()
        if final["status"] == "succeeded":
            break
        time.sleep(0.05)

    assert final is not None
    assert final["status"] == "succeeded"
    assert final["stage_label"] == "已完成"
    assert final["result"]["concept"] == concept
    assert final["result"]["profile"]["definition"] == "后台任务定义。"
    assert final["provider"] == "fake"
    assert final["model"] == "fake-model"

    found = client.get(f"/api/motifs?q={concept}&limit=10")
    assert found.status_code == 200
    assert found.json() == []


def test_tauri_motifs_enrichment_job_cancel_discards_late_result(monkeypatch):
    client = _tauri_client(monkeypatch)
    from deps import get_container
    import threading

    concept = f"取消后台任务-{uuid.uuid4().hex[:8]}"
    release_provider = threading.Event()

    class BlockingTaskService:
        def generate_from_messages(self, messages, *, cost_tier, model_override=None):
            assert release_provider.wait(3), "provider was not released by the test"
            return SimpleNamespace(
                content=json.dumps(
                    {
                        "title": concept,
                        "concept": concept,
                        "aliases": [],
                        "tags": [],
                        "note": (
                            "【一句话定义】\n取消后不采用。\n\n"
                            "【核心张力】\n本地中断与远端计费。\n\n"
                            "【写作功能】\n说明取消语义。\n\n"
                            "【场景触发】\n用户关闭等待。\n\n"
                            "【人物表现】\n人物停止倾听。\n\n"
                            "【意象转译】\n断线。\n\n"
                            "【短例子】\n他摘下耳机，但远处还在说话。\n\n"
                            "【关联建议】\n断线。\n\n"
                            "【误用提醒】\n不要承诺远端停止。\n\n"
                            "【微练习】\n写一个本地停止但远处仍继续的瞬间。\n\n"
                            "【来源线索（需核对）】\n- 未请求联网补充。"
                        ),
                        "related_suggestions": [],
                        "source_hints": [],
                        "reference_candidates": [],
                    },
                    ensure_ascii=False,
                ),
                provider="fake",
                model="fake-model",
                transport="fake",
            )

    get_container().ai_task_service = BlockingTaskService()
    created = client.post(
        "/api/ai/jobs/motif-enrichment",
        json={"concept": concept, "include_excerpts": False},
    )
    assert created.status_code == 200, created.text
    job_id = created.json()["job_id"]

    cancelled = client.post(f"/api/ai/jobs/{job_id}/cancel")
    assert cancelled.status_code == 200, cancelled.text
    cancelled_payload = cancelled.json()
    assert cancelled_payload["status"] == "cancelled"
    assert "远端仍可能完成并计费" in cancelled_payload["error"]

    release_provider.set()
    time.sleep(0.15)
    after = client.get(f"/api/ai/jobs/{job_id}")
    assert after.status_code == 200, after.text
    assert after.json()["status"] == "cancelled"
    assert after.json()["result"] is None


def test_tauri_motifs_enrichment_job_failure_is_sanitized(monkeypatch):
    client = _tauri_client(monkeypatch)
    from deps import get_container

    class HtmlErrorTaskService:
        def generate_from_messages(self, messages, *, cost_tier, model_override=None):
            raise RuntimeError(
                "AI request failed: <!doctype html><html><title>403 | Forbidden</title></html>"
            )

    get_container().ai_task_service = HtmlErrorTaskService()
    created = client.post("/api/ai/jobs/motif-enrichment", json={"concept": "神话模式"})
    assert created.status_code == 200, created.text
    job_id = created.json()["job_id"]

    deadline = time.time() + 3
    final = None
    while time.time() < deadline:
        response = client.get(f"/api/ai/jobs/{job_id}")
        assert response.status_code == 200, response.text
        final = response.json()
        if final["status"] == "failed":
            break
        time.sleep(0.05)

    assert final is not None
    assert final["status"] == "failed"
    assert "AI 丰富意象失败" in final["error"]
    assert "<html" not in final["error"].lower()
    assert "traceback" not in final["error"].lower()

    missing = client.get("/api/ai/jobs/does-not-exist")
    assert missing.status_code == 404
    assert "后台任务已不存在" in missing.json()["detail"]


def test_tauri_motifs_enrich_draft_keeps_user_concept_name(monkeypatch):
    client = _tauri_client(monkeypatch)
    from deps import get_container

    concept = "神话模式"

    class FakeTaskService:
        def generate_from_messages(self, messages, *, cost_tier, model_override=None):
            return SimpleNamespace(
                content=json.dumps(
                    {
                        "title": "模型改写后的标题",
                        "concept": "将神话叙事转译为日常行动的长定义",
                        "aliases": ["神话结构"],
                        "tags": ["写作手法"],
                        "note": (
                            "【一句话定义】\n把普通经验放入原型结构。\n\n"
                            "【核心张力】\n日常与命运互相拉扯。\n\n"
                            "【写作功能】\n让事件具有回声。\n\n"
                            "【场景触发】\n归来、试炼、牺牲。\n\n"
                            "【人物表现】\n人物像重复古老动作。\n\n"
                            "【意象转译】\n门槛、火、河流。\n\n"
                            "【短例子】\n他推开门。所有人都像等候一个旧预言。\n\n"
                            "【关联建议】\n原型、仪式。\n\n"
                            "【误用提醒】\n不要堆砌宏大词。\n\n"
                            "【微练习】\n把一次回家写成试炼。\n\n"
                            "【来源线索（需核对）】\n- 未请求联网补充。"
                        ),
                        "related_suggestions": ["原型"],
                        "source_hints": [],
                    },
                    ensure_ascii=False,
                )
            )

    get_container().ai_task_service = FakeTaskService()

    response = client.post(
        "/api/motifs/enrich-draft",
        json={"concept": concept, "include_excerpts": False},
    )

    assert response.status_code == 200, response.text
    assert response.json()["concept"] == concept


def test_tauri_motifs_enrich_draft_uses_profile_model(monkeypatch):
    client = _tauri_client(monkeypatch)
    from deps import get_container
    from features.motifs import routes as motif_routes
    from writer.services.ai.interfaces import ChatResponse

    profile_id = "profile-test"
    get_container().settings.save_ai_provider_profiles(
        [
            {
                "id": profile_id,
                "name": "DeepSeek",
                "provider_name": "openai",
                "base_url": "https://api.example/v1",
                "wire_api": "chat_completions",
                "model": "deepseek-v4-pro",
                "api_key_source": "env:WRITER_TEST_PRESENT_KEY",
                "gemini_cli_proxy": "",
                "enabled": True,
            }
        ]
    )
    seen = {}

    class FakeProvider:
        def chat(self, messages, *, model=None):
            seen["model"] = model
            seen["messages"] = messages
            return ChatResponse(
                content=json.dumps(
                    {
                        "title": "奴隶道德",
                        "concept": "奴隶道德",
                        "aliases": ["slave morality"],
                        "tags": ["哲学概念"],
                        "note": (
                            "【一句话定义】\n弱者以价值重估保护自身。\n\n"
                            "【核心张力】\n力量、怨恨与道德评价互相纠缠。\n\n"
                            "【写作功能】\n让角色的善恶判断带有反击结构。\n\n"
                            "【场景触发】\n无力者重新命名强者。\n\n"
                            "【人物表现】\n人物把不能做说成不屑做。\n\n"
                            "【意象转译】\n锁、镜子、冷房间。\n\n"
                            "【短例子】\n他没有赢过那个人。"
                            "于是他开始教育孩子，赢本身就是粗鄙。"
                            "多年后，他终于相信这是一种高贵。\n\n"
                            "【关联建议】\n怨恨、价值重估。\n\n"
                            "【误用提醒】\n不要把它写成简单的弱者邪恶。\n\n"
                            "【微练习】\n写一个角色把失败改名为美德。\n\n"
                            "【来源线索（需核对）】\n- 未请求联网补充。"
                        ),
                        "related_suggestions": ["怨恨", "价值重估"],
                        "source_hints": [],
                    },
                    ensure_ascii=False,
                ),
                provider="openai",
                model=model,
                transport="chat_completions",
            )

    monkeypatch.setattr(motif_routes, "provider_for_config", lambda config, prompt_builder: FakeProvider())
    monkeypatch.setenv("WRITER_TEST_PRESENT_KEY", "test-key")

    response = client.post(
        "/api/motifs/enrich-draft",
        json={
            "concept": "奴隶道德",
            "profile_id": profile_id,
            "cost_tier": "balanced",
        },
    )

    assert response.status_code == 200, response.text
    assert seen["model"] == "deepseek-v4-pro"
    assert response.json()["model"] == "deepseek-v4-pro"


def test_tauri_motifs_enrich_draft_rejects_bad_json_and_sanitizes_html(monkeypatch):
    client = _tauri_client(monkeypatch)
    from deps import get_container

    class TemplateTextTaskService:
        def generate_from_messages(self, messages, *, cost_tier, model_override=None):
            return SimpleNamespace(
                content=(
                    "【一句话定义】\n把普通经验放入原型结构。\n\n"
                    "【核心张力】\n日常行动与古老结构互相拉扯。\n\n"
                    "【写作功能】\n让普通事件带上命运感。\n\n"
                    "【场景触发】\n归来、牺牲、试炼、命名。\n\n"
                    "【人物表现】\n人物像在重复一个比自己更老的动作。\n\n"
                    "【意象转译】\n门槛、火、面具、河流。\n\n"
                    "【短例子】\n他回到村口时，所有人都沉默。"
                    "孩子们喊出的不是他的名字，而是旧故事里的称号。"
                    "他这才意识到，归来不是结束，而是被推上祭台。\n\n"
                    "【关联建议】\n原型、仪式、牺牲\n\n"
                    "【误用提醒】\n不要把神话感写成空洞宏大词。\n\n"
                    "【微练习】\n把一次回家写成一次试炼。\n\n"
                    "【来源线索（需核对）】\n- 未请求联网补充。"
                ),
                provider="fake",
                model="fake-strong",
                transport="fake",
            )

    get_container().ai_task_service = TemplateTextTaskService()
    template_text = client.post("/api/motifs/enrich-draft", json={"concept": "神话模式"})
    assert template_text.status_code == 200, template_text.text
    template_payload = template_text.json()
    assert template_payload["title"] == "神话模式"
    assert "【短例子】" in template_payload["note"]
    assert template_payload["related_suggestions"] == ["原型", "仪式", "牺牲"]

    class BadJsonTaskService:
        def generate_from_messages(self, messages, *, cost_tier, model_override=None):
            return SimpleNamespace(content="not json")

    get_container().ai_task_service = BadJsonTaskService()
    bad_json = client.post("/api/motifs/enrich-draft", json={"concept": "神话模式"})
    assert bad_json.status_code == 502

    class HtmlErrorTaskService:
        def generate_from_messages(self, messages, *, cost_tier, model_override=None):
            raise RuntimeError(
                "AI request failed: <!doctype html><html><title>403 | Forbidden</title></html>"
            )

    get_container().ai_task_service = HtmlErrorTaskService()
    html_error = client.post("/api/motifs/enrich-draft", json={"concept": "神话模式"})
    assert html_error.status_code == 500
    detail = html_error.json()["detail"]
    assert "AI 丰富意象失败" in detail
    assert "<html" not in detail.lower()


def test_tauri_motifs_excerpt_lookup_merge_and_unlink(monkeypatch):
    client = _tauri_client(monkeypatch)

    sentence = "岁月穿过城市。"
    entry = client.post(
        "/api/articles",
        json={"title": "城市", "body": f"{sentence}{sentence}", "tags": []},
    ).json()

    first = client.post(
        "/api/motifs/excerpts",
        json={
            "source_kind": "article",
            "source_id": entry["id"],
            "excerpt_text": sentence,
            "selection_start": 0,
            "selection_end": len(sentence),
            "motif_names": ["岁月"],
        },
    )
    assert first.status_code == 201, first.text
    first_excerpt = first.json()

    lookup = client.post(
        "/api/motifs/excerpts/lookup",
        json={
            "source_kind": "article",
            "source_id": entry["id"],
            "excerpt_text": sentence,
            "selection_start": 0,
            "selection_end": len(sentence),
        },
    )
    assert lookup.status_code == 200, lookup.text
    assert lookup.json()["id"] == first_excerpt["id"]

    merged = client.post(
        "/api/motifs/excerpts",
        json={
            "source_kind": "article",
            "source_id": entry["id"],
            "excerpt_text": sentence,
            "selection_start": 0,
            "selection_end": len(sentence),
            "motif_names": ["城市"],
        },
    )
    assert merged.status_code == 201, merged.text
    assert merged.json()["id"] == first_excerpt["id"]
    assert set(merged.json()["motif_names"]) == {"岁月", "城市"}

    linked = client.post(
        f"/api/motifs/excerpts/{first_excerpt['id']}/motifs",
        json={"motif_names": ["消息"]},
    )
    assert linked.status_code == 200, linked.text
    assert set(linked.json()["motif_names"]) == {"岁月", "城市", "消息"}

    motif_by_name = {motif["name"]: motif for motif in client.get("/api/motifs").json()}
    years_id = motif_by_name["岁月"]["id"]
    city_id = motif_by_name["城市"]["id"]
    message_id = motif_by_name["消息"]["id"]

    unlink_years = client.delete(f"/api/motifs/excerpts/{first_excerpt['id']}/motifs/{years_id}")
    assert unlink_years.status_code == 204
    assert client.get(f"/api/motifs/{years_id}/excerpts").json() == []
    assert [item["id"] for item in client.get(f"/api/motifs/{city_id}/excerpts").json()] == [first_excerpt["id"]]

    assert client.delete(f"/api/motifs/excerpts/{first_excerpt['id']}/motifs/{city_id}").status_code == 204
    assert client.delete(f"/api/motifs/excerpts/{first_excerpt['id']}/motifs/{message_id}").status_code == 204
    missing = client.post(
        "/api/motifs/excerpts/lookup",
        json={
            "source_kind": "article",
            "source_id": entry["id"],
            "excerpt_text": sentence,
            "selection_start": 0,
            "selection_end": len(sentence),
        },
    )
    assert missing.status_code == 404


def test_tauri_motifs_lookup_and_create_reuse_excerpt_after_position_drift(monkeypatch):
    client = _tauri_client(monkeypatch)

    sentence = "裙摆在移动间带起一阵微弱的风，那股苦杏仁的味道随之变得浓郁，又迅速在空气中稀释。"
    entry = client.post(
        "/api/articles",
        json={"title": "苦杏仁、凉面与那一阵风", "body": sentence, "tags": []},
    ).json()
    created = client.post(
        "/api/motifs/excerpts",
        json={
            "source_kind": "article",
            "source_id": entry["id"],
            "excerpt_text": sentence,
            "selection_start": 0,
            "selection_end": len(sentence),
            "motif_names": ["测试意象｜往事"],
        },
    )
    assert created.status_code == 201, created.text
    excerpt_id = created.json()["id"]

    new_body = f"前面新增了一些文字。\n\n{sentence}\n\n后文。"
    current_start = new_body.index(sentence)
    current_end = current_start + len(sentence)
    updated = client.put(
        f"/api/articles/{entry['id']}",
        json={"title": entry["title"], "body": new_body, "tags": []},
    )
    assert updated.status_code == 200, updated.text

    lookup = client.post(
        "/api/motifs/excerpts/lookup",
        json={
            "source_kind": "article",
            "source_id": entry["id"],
            "excerpt_text": sentence,
            "selection_start": current_start,
            "selection_end": current_end,
            "before_context": new_body[max(0, current_start - 90):current_start],
            "after_context": new_body[current_end:current_end + 90],
        },
    )
    assert lookup.status_code == 200, lookup.text
    assert lookup.json()["id"] == excerpt_id
    assert lookup.json()["selection_start"] == current_start
    assert lookup.json()["selection_end"] == current_end

    merged = client.post(
        "/api/motifs/excerpts",
        json={
            "source_kind": "article",
            "source_id": entry["id"],
            "excerpt_text": sentence,
            "selection_start": current_start,
            "selection_end": current_end,
            "before_context": new_body[max(0, current_start - 90):current_start],
            "after_context": new_body[current_end:current_end + 90],
            "motif_names": ["测试意象｜风"],
        },
    )
    assert merged.status_code == 201, merged.text
    assert merged.json()["id"] == excerpt_id
    assert set(merged.json()["motif_names"]) == {"测试意象｜往事", "测试意象｜风"}
    source_excerpts = client.get(f"/api/motifs/excerpts/source/article/{entry['id']}")
    assert source_excerpts.status_code == 200, source_excerpts.text
    assert [item["id"] for item in source_excerpts.json()] == [excerpt_id]


def test_tauri_motifs_source_list_merges_historical_duplicate_rows(monkeypatch):
    client = _tauri_client(monkeypatch)

    sentence = "裙摆在移动间带起一阵微弱的风，那股苦杏仁的味道随之变得浓郁，又迅速在空气中稀释。"
    body = f"前文。\n\n{sentence}\n\n后文。"
    entry = client.post(
        "/api/articles",
        json={"title": "苦杏仁、凉面与那一阵风", "body": body, "tags": []},
    ).json()
    current_start = body.index(sentence)
    current_end = current_start + len(sentence)
    first = client.post(
        "/api/motifs/excerpts",
        json={
            "source_kind": "article",
            "source_id": entry["id"],
            "excerpt_text": sentence,
            "selection_start": current_start,
            "selection_end": current_end,
            "motif_names": ["测试意象｜往事"],
            "note": "第一条备注",
        },
    )
    assert first.status_code == 201, first.text
    first_excerpt = first.json()

    container = sys.modules["deps"].get_container()
    wind = (
        container.motif_repository.find_node_by_name("测试意象｜风")
        or container.motif_repository.create_node(name="测试意象｜风")
    )
    duplicate_id = str(uuid.uuid4())
    container.connection.execute(
        """
        INSERT INTO motif_excerpts
            (id, source_kind, source_id, source_title_snapshot, excerpt_text, note,
             selection_start, selection_end, before_context, after_context)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            duplicate_id,
            "article",
            entry["id"],
            entry["title"],
            sentence,
            "第二条备注",
            current_start + 40,
            current_end + 40,
            "",
            "",
        ),
    )
    container.connection.execute(
        "INSERT INTO motif_excerpt_links (id, motif_id, excerpt_id) VALUES (?, ?, ?)",
        (str(uuid.uuid4()), wind.id, duplicate_id),
    )
    container.connection.commit()

    source_excerpts = client.get(f"/api/motifs/excerpts/source/article/{entry['id']}")
    assert source_excerpts.status_code == 200, source_excerpts.text
    payload = source_excerpts.json()
    assert len(payload) == 1
    assert payload[0]["id"] == first_excerpt["id"]
    assert payload[0]["selection_start"] == current_start
    assert payload[0]["selection_end"] == current_end
    assert set(payload[0]["motif_names"]) == {"测试意象｜往事", "测试意象｜风"}
    assert "第一条备注" in payload[0]["note"]
    assert "第二条备注" in payload[0]["note"]


def test_tauri_motifs_set_excerpt_motifs_and_list_by_source(monkeypatch):
    client = _tauri_client(monkeypatch)

    sentence = "城市有一封没有寄出的消息。"
    entry = client.post(
        "/api/articles",
        json={"title": "消息", "body": sentence, "tags": []},
    ).json()
    created = client.post(
        "/api/motifs/excerpts",
        json={
            "source_kind": "article",
            "source_id": entry["id"],
            "excerpt_text": sentence,
            "selection_start": 0,
            "selection_end": len(sentence),
            "motif_names": ["城市", "消息"],
        },
    )
    assert created.status_code == 201, created.text
    excerpt = created.json()

    source_excerpts = client.get(
        f"/api/motifs/excerpts/source/article/{entry['id']}"
    )
    assert source_excerpts.status_code == 200
    assert [item["id"] for item in source_excerpts.json()] == [excerpt["id"]]

    updated = client.put(
        f"/api/motifs/excerpts/{excerpt['id']}/motifs",
        json={"motif_names": ["消息"], "note": "只保留消息"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["deleted"] is False
    assert updated.json()["excerpt"]["motif_names"] == ["消息"]
    motif_by_name = {motif["name"]: motif for motif in client.get("/api/motifs").json()}
    assert client.get(f"/api/motifs/{motif_by_name['城市']['id']}/excerpts").json() == []
    assert [item["id"] for item in client.get(f"/api/motifs/{motif_by_name['消息']['id']}/excerpts").json()] == [excerpt["id"]]

    deleted = client.put(
        f"/api/motifs/excerpts/{excerpt['id']}/motifs",
        json={"motif_names": []},
    )
    assert deleted.status_code == 200, deleted.text
    assert deleted.json() == {"excerpt": None, "deleted": True}
    assert client.get(f"/api/motifs/excerpts/source/article/{entry['id']}").json() == []


def test_tauri_motifs_crud_reference_source_density_and_delete(monkeypatch):
    client = _tauri_client(monkeypatch)

    created_node = client.post(
        "/api/motifs",
        json={
            "name": "月亮",
            "aliases": ["月"],
            "note": "冷光。",
            "tags": ["天体"],
            "pinned": True,
        },
    )
    assert created_node.status_code == 201, created_node.text
    node = created_node.json()
    assert node["name"] == "月亮"
    assert node["aliases"] == ["月"]
    assert node["pinned"] is True

    updated_node = client.put(
        f"/api/motifs/{node['id']}",
        json={
            "name": "月光",
            "aliases": ["月亮"],
            "note": "更偏向照明和凝视。",
            "tags": ["光"],
            "pinned": False,
        },
    )
    assert updated_node.status_code == 200, updated_node.text
    node = updated_node.json()
    assert node["name"] == "月光"
    assert node["tags"] == ["光"]

    reference = client.post(
        "/api/library/references",
        json={
            "source_title": "",
            "content": "井口收着一点月光。",
            "source_author": "",
            "tags": [],
            "kind": "excerpt",
            "usage_kind": "imagery",
            "personal_note": "",
        },
    ).json()
    excerpt_response = client.post(
        "/api/motifs/excerpts",
        json={
            "source_kind": "reference",
            "source_id": reference["id"],
            "excerpt_text": "井口收着一点月光。",
            "motif_ids": [node["id"]],
            "motif_names": ["井"],
            "selection_start": 0,
            "selection_end": 9,
        },
    )
    assert excerpt_response.status_code == 201, excerpt_response.text
    excerpt = excerpt_response.json()
    assert excerpt["source_kind"] == "reference"
    assert excerpt["source_exists"] is True
    assert set(excerpt["motif_names"]) == {"月光", "井"}

    dense_graph = client.get("/api/motifs/graph?limit=2&density=0")
    assert dense_graph.status_code == 200
    assert len(dense_graph.json()["nodes"]) <= 2

    delete_excerpt = client.delete(f"/api/motifs/excerpts/{excerpt['id']}")
    assert delete_excerpt.status_code == 204
    assert client.get(f"/api/motifs/{node['id']}/excerpts").json() == []

    delete_node = client.delete(f"/api/motifs/{node['id']}")
    assert delete_node.status_code == 204
    assert client.get(f"/api/library/references/{reference['id']}").status_code == 200


def test_tauri_motifs_list_search_limit_and_pinned_order(monkeypatch):
    client = _tauri_client(monkeypatch)
    suffix = uuid.uuid4().hex[:8]
    rose = f"排序玫瑰-{suffix}"
    pinned_rose = f"排序血玫瑰-{suffix}"
    moon = f"排序月亮-{suffix}"

    for name, pinned in [(rose, False), (pinned_rose, True), (moon, False)]:
        response = client.post(
            "/api/motifs",
            json={
                "name": name,
                "aliases": [],
                "note": "花园线索" if "玫瑰" in name else "",
                "tags": ["植物"] if "玫瑰" in name else ["天体"],
                "pinned": pinned,
            },
        )
        assert response.status_code == 201

    searched = client.get(f"/api/motifs?q={suffix}&limit=1")
    assert searched.status_code == 200
    data = searched.json()
    assert [item["name"] for item in data] == [pinned_rose]
    assert data[0]["pinned"] is True


def test_tauri_motifs_reject_invalid_excerpt_payloads(monkeypatch):
    client = _tauri_client(monkeypatch)
    entry = client.post(
        "/api/articles",
        json={"title": "风", "body": "一阵风。", "tags": []},
    ).json()

    empty_text = client.post(
        "/api/motifs/excerpts",
        json={
            "source_kind": "article",
            "source_id": entry["id"],
            "excerpt_text": " ",
            "motif_names": ["风"],
        },
    )
    assert empty_text.status_code == 400
    assert "Excerpt text is required" in empty_text.json()["detail"]

    empty_motifs = client.post(
        "/api/motifs/excerpts",
        json={
            "source_kind": "article",
            "source_id": entry["id"],
            "excerpt_text": "一阵风。",
            "motif_names": [],
        },
    )
    assert empty_motifs.status_code == 400
    assert "At least one motif is required" in empty_motifs.json()["detail"]

    invalid_source_kind = client.post(
        "/api/motifs/excerpts",
        json={
            "source_kind": "collection",
            "source_id": entry["id"],
            "excerpt_text": "一阵风。",
            "motif_names": ["风"],
        },
    )
    assert invalid_source_kind.status_code == 422


def test_tauri_motifs_reject_missing_source(monkeypatch):
    client = _tauri_client(monkeypatch)

    response = client.post(
        "/api/motifs/excerpts",
        json={
            "source_kind": "article",
            "source_id": "missing",
            "excerpt_text": "失去来源的句子。",
            "motif_names": ["失踪"],
        },
    )

    assert response.status_code == 400
    assert "Source not found" in response.json()["detail"]


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


def test_tauri_ai_chat_settings_are_injected_into_chat(monkeypatch):
    client = _tauri_client(monkeypatch)

    saved = client.put(
        "/api/ai/chat-settings",
        json={"system_prompt": f"  {'要克制。' * 1000}  "},
    )
    assert saved.status_code == 200
    assert len(saved.json()["system_prompt"]) == 4000

    saved = client.put(
        "/api/ai/chat-settings",
        json={"system_prompt": "回答要具体、克制。"},
    )
    assert saved.status_code == 200
    assert saved.json()["system_prompt"] == "回答要具体、克制。"

    restored = client.get("/api/ai/chat-settings")
    assert restored.status_code == 200
    assert restored.json()["system_prompt"] == "回答要具体、克制。"

    entry = client.post(
        "/api/articles",
        json={"title": "AI 对话文章", "body": "文章正文。", "tags": []},
    ).json()

    from deps import get_container
    from writer.services.ai.interfaces import ChatResponse

    class FakeProvider:
        name = "fake"

        def __init__(self):
            self.calls = []

        def chat(self, messages, *, model=None):
            self.calls.append({"messages": list(messages), "model": model})
            return ChatResponse(
                content="建议写成便签。",
                model=model or "fake-model",
                provider=self.name,
                input_tokens=1,
                output_tokens=1,
            )

    provider = FakeProvider()
    get_container().ai_thread_service._provider_factory = lambda: provider  # noqa: SLF001

    response = client.post(
        "/api/ai/chat",
        json={
            "message": "这一段怎么改？",
            "scope_kind": "article",
            "scope_id": entry["id"],
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["assistant_message"]["content"] == "建议写成便签。"
    messages = provider.calls[-1]["messages"]
    assert "回答要具体、克制。" in messages[0]["content"]
    assert "文章正文。" in messages[-1]["content"]

    cleared = client.put("/api/ai/chat-settings", json={"system_prompt": "  "})
    assert cleared.status_code == 200
    assert cleared.json()["system_prompt"] == ""


def test_tauri_ai_task_accepts_controls_and_attachments(monkeypatch):
    client = _tauri_client(monkeypatch)

    from deps import get_container

    captured = {}

    class FakeTaskService:
        def generate(self, request):
            captured["request"] = request
            return SimpleNamespace(content="处理结果")

    get_container().ai_task_service = FakeTaskService()

    response = client.post(
        "/api/ai/task",
        json={
            "task_type": "polish",
            "target_kind": "selection",
            "target_ref_id": "entry-1",
            "text": "原文",
            "style": "自然",
            "intensity": "strong",
            "extra_instructions": "保留尾句。",
            "preserve_voice": True,
            "attachments": [
                {
                    "kind": "writing_note",
                    "ref_id": "entry-1",
                    "name": "文章便签 · 1",
                    "body": "下一段写雨。",
                },
                {
                    "kind": "reference",
                    "ref_id": "ref-1",
                    "name": "《测试书》 作者",
                    "body": "标本正文",
                },
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["result"] == "处理结果"
    request = captured["request"]
    assert request.target_kind.value == "selection"
    assert request.target_ref_id == "entry-1"
    assert request.intensity == "strong"
    assert request.extra_instructions == "保留尾句。"
    assert [attachment.kind for attachment in request.attachments] == [
        "writing_note",
        "reference",
    ]


def test_tauri_ai_task_presets_roundtrip(monkeypatch):
    client = _tauri_client(monkeypatch)

    saved = client.put(
        "/api/ai/task-presets",
        json={
            "polish": [
                {
                    "id": "preset-1",
                    "task_type": "polish",
                    "name": "克制润色",
                    "controls": {
                        "polishIntensity": "light",
                        "preserveVoice": True,
                    },
                }
            ],
            "unknown": [
                {
                    "id": "bad",
                    "task_type": "unknown",
                    "name": "不应保存",
                    "controls": {},
                }
            ],
        },
    )
    assert saved.status_code == 200
    assert list(saved.json().keys()) == ["polish"]
    assert saved.json()["polish"][0]["name"] == "克制润色"

    restored = client.get("/api/ai/task-presets")
    assert restored.status_code == 200
    assert restored.json()["polish"][0]["controls"]["polishIntensity"] == "light"


def test_tauri_ai_task_compare_uses_profile_models(monkeypatch):
    client = _tauri_client(monkeypatch)
    from features.ai import routes as ai_routes
    from writer.services.ai.interfaces import ChatResponse

    monkeypatch.setenv("WRITER_TEST_PRESENT_KEY", "test-key")

    saved_default = client.put(
        "/api/settings/ai",
        json={
            "provider_name": "openai",
            "base_url": "https://api.example/v1",
            "wire_api": "chat_completions",
            "model": "default-model",
            "api_key_source": "env:WRITER_TEST_PRESENT_KEY",
        },
    )
    assert saved_default.status_code == 200, saved_default.text

    profile_a = client.post(
        "/api/settings/ai/profiles",
        json={
            "name": "Profile A",
            "provider_name": "openai",
            "base_url": "https://api-a.example/v1",
            "wire_api": "chat_completions",
            "model": "profile-a-model",
            "api_key_source": "env:WRITER_TEST_PRESENT_KEY",
        },
    ).json()
    profile_b = client.post(
        "/api/settings/ai/profiles",
        json={
            "name": "Profile B",
            "provider_name": "gemini",
            "base_url": "https://relay.example",
            "wire_api": "responses",
            "model": "profile-b-model",
            "api_key_source": "env:WRITER_TEST_PRESENT_KEY",
        },
    ).json()

    class FakeProvider:
        def __init__(self, config):
            self.config = config

        def chat(self, messages, *, model=None):
            used_model = model or self.config.model
            return ChatResponse(
                content=f"{used_model}: ok",
                model=used_model,
                provider=self.config.provider_key(),
                transport=f"fake_{self.config.wire_api}",
                input_tokens=3,
                output_tokens=4,
                cost=0.01,
            )

    monkeypatch.setattr(
        ai_routes,
        "provider_for_config",
        lambda config, prompt_builder=None: FakeProvider(config),
    )

    response = client.post(
        "/api/ai/task/compare",
        json={
            "task_type": "polish",
            "text": "雨夜里，两个人在车站告别。",
            "target_kind": "paste",
            "profile_ids": ["default", profile_a["id"], profile_b["id"]],
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert [item["model"] for item in payload["results"]] == [
        "default-model",
        "profile-a-model",
        "profile-b-model",
    ]
    assert all(item["status"] == "success" for item in payload["results"])
    assert payload["results"][0]["stats"]["input_chars"] == len("雨夜里，两个人在车站告别。")
    assert payload["results"][0]["input_tokens"] == 3
    assert payload["results"][0]["cost"] == 0.01

    specific_only = client.post(
        "/api/ai/task/compare",
        json={
            "task_type": "polish",
            "text": "雨夜里，两个人在车站告别。",
            "target_kind": "paste",
            "profile_ids": [profile_a["id"], profile_b["id"]],
        },
    )

    assert specific_only.status_code == 200, specific_only.text
    assert [item["profile_id"] for item in specific_only.json()["results"]] == [
        profile_a["id"],
        profile_b["id"],
    ]
    assert "default-model" not in [item["model"] for item in specific_only.json()["results"]]


def test_tauri_ai_task_compare_allows_many_profiles_and_sanitizes_partial_failure(monkeypatch):
    client = _tauri_client(monkeypatch)
    from features.ai import routes as ai_routes
    from writer.services.ai.interfaces import AiError, ChatResponse

    monkeypatch.setenv("WRITER_TEST_PRESENT_KEY", "test-key")

    created_profiles = []
    for index, model in enumerate(["ok-model", "bad-model", "extra-model", "fourth-model"], start=1):
        response = client.post(
            "/api/settings/ai/profiles",
            json={
                "name": f"Profile {index}",
                "provider_name": "openai",
                "base_url": "https://api.example/v1",
                "wire_api": "chat_completions",
                "model": model,
                "api_key_source": "env:WRITER_TEST_PRESENT_KEY",
            },
        )
        assert response.status_code == 201, response.text
        created_profiles.append(response.json())

    empty = client.post(
        "/api/ai/task/compare",
        json={
            "task_type": "polish",
            "text": "hello",
            "target_kind": "paste",
            "profile_ids": [],
        },
    )
    assert empty.status_code == 400
    assert "至少一个" in empty.text

    class FakeProvider:
        def __init__(self, config):
            self.config = config

        def chat(self, messages, *, model=None):
            used_model = model or self.config.model
            if used_model == "bad-model":
                raise AiError("AI request failed: <!doctype html><html>403 forbidden</html>")
            return ChatResponse(
                content="ok",
                model=used_model,
                provider="openai",
                transport="fake",
            )

    monkeypatch.setattr(
        ai_routes,
        "provider_for_config",
        lambda config, prompt_builder=None: FakeProvider(config),
    )

    response = client.post(
        "/api/ai/task/compare",
        json={
            "task_type": "polish",
            "text": "hello",
            "target_kind": "paste",
            "profile_ids": [profile["id"] for profile in created_profiles],
        },
    )

    assert response.status_code == 200, response.text
    results = response.json()["results"]
    assert [item["status"] for item in results] == ["success", "error", "success", "success"]
    assert "网页错误页" in results[1]["error"]
    assert "<!doctype html>" not in results[1]["error"]


def test_tauri_ai_task_compare_streams_individual_results(monkeypatch):
    client = _tauri_client(monkeypatch)
    from features.ai import routes as ai_routes
    from writer.services.ai.interfaces import AiError, ChatResponse

    monkeypatch.setenv("WRITER_TEST_PRESENT_KEY", "test-key")

    profiles = []
    for name, model in [
        ("Slow", "slow-model"),
        ("Fast", "fast-model"),
        ("Bad", "bad-model"),
    ]:
        response = client.post(
            "/api/settings/ai/profiles",
            json={
                "name": name,
                "provider_name": "openai",
                "base_url": "https://api.example/v1",
                "wire_api": "chat_completions",
                "model": model,
                "api_key_source": "env:WRITER_TEST_PRESENT_KEY",
            },
        )
        assert response.status_code == 201, response.text
        profiles.append(response.json())

    class FakeProvider:
        def __init__(self, config):
            self.config = config

        def chat(self, messages, *, model=None):
            used_model = model or self.config.model
            if used_model == "slow-model":
                time.sleep(0.05)
            if used_model == "bad-model":
                time.sleep(0.02)
                raise AiError("provider failed: <html>403 forbidden</html>")
            return ChatResponse(
                content=f"{used_model}: ok",
                model=used_model,
                provider="openai",
                transport="fake",
            )

    monkeypatch.setattr(
        ai_routes,
        "provider_for_config",
        lambda config, prompt_builder=None: FakeProvider(config),
    )

    response = client.post(
        "/api/ai/task/compare/stream",
        json={
            "task_type": "polish",
            "text": "hello",
            "target_kind": "paste",
            "profile_ids": [profile["id"] for profile in profiles],
        },
    )

    assert response.status_code == 200, response.text
    events = [json.loads(line) for line in response.text.splitlines() if line.strip()]
    assert events[0]["event"] == "started"
    assert [profile["profile_id"] for profile in events[0]["profiles"]] == [profile["id"] for profile in profiles]
    assert events[-1]["event"] == "done"

    result_events = [event for event in events if event["event"] in {"result", "error"}]
    assert result_events[0]["result"]["model"] == "fast-model"
    assert {event["result"]["model"] for event in result_events} == {"slow-model", "fast-model", "bad-model"}
    bad_event = next(event for event in result_events if event["result"]["model"] == "bad-model")
    assert bad_event["event"] == "error"
    assert "网页错误页" in bad_event["result"]["error"]
    assert "<html>" not in bad_event["result"]["error"]


def test_tauri_ai_settings_read_save_and_validate(monkeypatch):
    client = _tauri_client(monkeypatch)

    initial = client.get("/api/settings/ai")
    assert initial.status_code == 200
    initial_payload = initial.json()
    assert initial_payload["provider_name"] in {"openai", "gemini", "gemini_cli", "opencode"}
    assert "status" in initial_payload
    assert "opencode" in initial_payload["status"]
    assert "model_presets" in initial_payload
    assert "deepseek-v4-pro" in initial_payload["model_presets"]["openai"]
    assert "glm-5.2" in initial_payload["model_presets"]["openai"]
    assert "opencode/deepseek-v4-flash-free" in initial_payload["model_presets"]["opencode"]
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

    opencode = client.put(
        "/api/settings/ai",
        json={
            "provider_name": "opencode",
            "base_url": "https://should-be-cleared.example",
            "wire_api": "responses",
            "model": "",
            "api_key_source": "env:IGNORED",
            "gemini_cli_proxy": "http://127.0.0.1:7890",
        },
    )
    assert opencode.status_code == 200
    opencode_payload = opencode.json()
    assert opencode_payload["provider_name"] == "opencode"
    assert opencode_payload["api_key_source"] == "opencode"
    assert opencode_payload["model"] == "opencode/deepseek-v4-flash-free"
    assert opencode_payload["base_url"] is None

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


def test_tauri_ai_settings_save_local_key_returns_env_source(monkeypatch):
    client = _tauri_client(monkeypatch)
    from features.settings import routes as settings_routes

    saved = {}

    def fake_set_user_environment_variable(name, value):
        saved[name] = value
        monkeypatch.setenv(name, value)
        return True

    monkeypatch.setattr(
        settings_routes,
        "_set_user_environment_variable",
        fake_set_user_environment_variable,
    )

    response = client.post(
        "/api/settings/ai/local-key",
        json={
            "api_key": "test-local-api-key",
            "provider_name": "openai",
            "model": "deepseek-v4-pro",
            "label": "default",
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["api_key_source"] == "env:LTT_AI_OPENAI_KEY"
    assert payload["env_var"] == "LTT_AI_OPENAI_KEY"
    assert payload["persisted"] is True
    assert saved == {"LTT_AI_OPENAI_KEY": "test-local-api-key"}
    assert "test-local-api-key" not in response.text

    check = client.post(
        "/api/settings/ai/test",
        json={
            "provider_name": "openai",
            "base_url": "https://relay.example",
            "wire_api": "chat_completions",
            "model": "deepseek-v4-pro",
            "api_key_source": payload["api_key_source"],
        },
    )

    assert check.status_code == 200
    assert check.json()["ok"] is True


def test_tauri_ai_local_key_profile_sources_are_distinct_and_reused(monkeypatch):
    client = _tauri_client(monkeypatch)
    from features.settings import routes as settings_routes
    from deps import get_container

    get_container().settings.save_ai_provider_profiles([])
    saved = {}

    def fake_set_user_environment_variable(name, value):
        saved[name] = value
        monkeypatch.setenv(name, value)
        return True

    monkeypatch.setattr(
        settings_routes,
        "_set_user_environment_variable",
        fake_set_user_environment_variable,
    )

    glm = client.post(
        "/api/settings/ai/local-key",
        json={
            "api_key": "test-glm-key-not-real",
            "provider_name": "openai",
            "model": "glm-5.2",
            "label": "GLM 5.2 Relay",
        },
    )
    deepseek = client.post(
        "/api/settings/ai/local-key",
        json={
            "api_key": "test-deepseek-key-not-real",
            "provider_name": "openai",
            "model": "deepseek-v4-pro",
            "label": "DeepSeek v4 Pro Relay",
        },
    )

    assert glm.status_code == 200, glm.text
    assert deepseek.status_code == 200, deepseek.text
    glm_payload = glm.json()
    deepseek_payload = deepseek.json()
    assert glm_payload["api_key_source"].startswith("env:LTT_AI_")
    assert deepseek_payload["api_key_source"].startswith("env:LTT_AI_")
    assert glm_payload["api_key_source"] != deepseek_payload["api_key_source"]
    assert "test-glm-key-not-real" not in glm.text
    assert "test-deepseek-key-not-real" not in deepseek.text

    profile = client.post(
        "/api/settings/ai/profiles",
        json={
            "name": "GLM 5.2 Relay",
            "provider_name": "openai",
            "base_url": "https://elysiver.h-e.top/",
            "wire_api": "chat_completions",
            "model": "glm-5.2",
            "api_key_source": glm_payload["api_key_source"],
            "enabled": True,
        },
    )
    assert profile.status_code == 201, profile.text

    reused = client.post(
        "/api/settings/ai/local-key",
        json={
            "api_key": "test-glm-replacement-key-not-real",
            "provider_name": "openai",
            "model": "glm-5.2",
            "profile_id": profile.json()["id"],
            "label": "GLM 5.2 Relay",
        },
    )

    assert reused.status_code == 200, reused.text
    assert reused.json()["api_key_source"] == glm_payload["api_key_source"]
    assert reused.json()["env_var"] == glm_payload["env_var"]
    assert saved[glm_payload["env_var"]] == "test-glm-replacement-key-not-real"
    assert saved[deepseek_payload["env_var"]] == "test-deepseek-key-not-real"
    assert "test-glm-replacement-key-not-real" not in reused.text


def test_tauri_ai_live_test_uses_requested_profile_credential_source(monkeypatch):
    client = _tauri_client(monkeypatch)
    from features.settings import routes as settings_routes
    from writer.services.ai.interfaces import ChatResponse

    monkeypatch.setenv("LTT_AI_DEEPSEEK_PROFILE_KEY", "test-profile-key-not-real")
    seen = {}

    class FakeProvider:
        def chat(self, messages, *, model=None):
            return ChatResponse(
                content="OK",
                model=model or "deepseek-v4-pro",
                provider="openai",
                transport="openai_chat_completions",
            )

    def fake_provider_for_config(config):
        seen["api_key_source"] = config.api_key_source
        seen["model"] = config.model
        seen["base_url"] = config.base_url
        return FakeProvider()

    monkeypatch.setattr(settings_routes, "_provider_for_config", fake_provider_for_config)

    response = client.post(
        "/api/settings/ai/test-live",
        json={
            "provider_name": "openai",
            "base_url": "https://elysiver.h-e.top/",
            "wire_api": "chat_completions",
            "model": "deepseek-v4-pro",
            "api_key_source": "env:LTT_AI_DEEPSEEK_PROFILE_KEY",
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["ok"] is True
    assert payload["model"] == "deepseek-v4-pro"
    assert payload["transport"] == "openai_chat_completions"
    assert seen == {
        "api_key_source": "env:LTT_AI_DEEPSEEK_PROFILE_KEY",
        "model": "deepseek-v4-pro",
        "base_url": "https://elysiver.h-e.top/",
    }


def test_tauri_ai_profiles_crud_and_validation(monkeypatch):
    client = _tauri_client(monkeypatch)

    literal = client.post(
        "/api/settings/ai/profiles",
        json={
            "name": "Bad literal key",
            "provider_name": "openai",
            "base_url": "https://api.example/v1",
            "wire_api": "chat_completions",
            "model": "deepseek-chat",
            "api_key_source": "literal:secret",
        },
    )
    assert literal.status_code == 400

    created = client.post(
        "/api/settings/ai/profiles",
        json={
            "name": "DeepSeek test",
            "provider_name": "openai",
            "base_url": "https://api.deepseek.com/v1",
            "wire_api": "chat_completions",
            "model": "deepseek-chat",
            "api_key_source": "env:WRITER_TEST_PRESENT_KEY",
            "enabled": True,
            "source_key": "local:codex",
        },
    )
    assert created.status_code == 201, created.text
    profile = created.json()
    assert profile["id"]
    assert profile["wire_api"] == "chat_completions"
    assert profile["api_key_source"] == "env:WRITER_TEST_PRESENT_KEY"
    assert profile["source_key"] == "local:codex"

    listed = client.get("/api/settings/ai/profiles")
    assert listed.status_code == 200
    assert any(item["id"] == profile["id"] for item in listed.json()["profiles"])

    updated = client.put(
        f"/api/settings/ai/profiles/{profile['id']}",
        json={"enabled": False, "name": "DeepSeek disabled"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["enabled"] is False
    assert updated.json()["name"] == "DeepSeek disabled"
    assert updated.json()["source_key"] == "local:codex"

    deleted = client.delete(f"/api/settings/ai/profiles/{profile['id']}")
    assert deleted.status_code == 204


def test_tauri_ai_profiles_discover_and_import_local(monkeypatch):
    client = _tauri_client(monkeypatch)
    from features.settings import routes as settings_routes
    from deps import get_container

    get_container().settings.save_ai_provider_profiles([])

    def fake_discover(container):
        return [
            settings_routes.AiDiscoveredProfileOut(
                name="OpenCode · DeepSeek v4 Flash Free",
                provider_name="opencode",
                base_url=None,
                wire_api="responses",
                model="opencode/deepseek-v4-flash-free",
                api_key_source="opencode",
                gemini_cli_proxy=None,
                enabled=True,
                source_key="local:opencode",
                source_label="OpenCode 本机登录",
                available=True,
                reason="",
            ),
            settings_routes.AiDiscoveredProfileOut(
                name="Gemini · gemini-3.1-pro",
                provider_name="gemini",
                base_url="https://elysia.h-e.top",
                wire_api="responses",
                model="gemini-3.1-pro",
                api_key_source="gemini",
                gemini_cli_proxy=None,
                enabled=True,
                source_key="local:gemini",
                source_label="Gemini .env",
                available=False,
                reason="AI 服务拒绝了当前请求。",
            ),
        ]

    monkeypatch.setattr(settings_routes, "_discover_local_ai_profiles", fake_discover)

    discovered = client.get("/api/settings/ai/profiles/discover")
    assert discovered.status_code == 200, discovered.text
    assert [item["source_key"] for item in discovered.json()] == [
        "local:opencode",
        "local:gemini",
    ]

    imported = client.post(
        "/api/settings/ai/profiles/import-local",
        json={"source_keys": [], "update_existing": True},
    )
    assert imported.status_code == 200, imported.text
    payload = imported.json()
    assert payload["imported_count"] == 1
    assert payload["updated_count"] == 0
    assert payload["profiles"][0]["source_key"] == "local:opencode"
    assert "Gemini .env" in payload["skipped"][0]

    imported_again = client.post(
        "/api/settings/ai/profiles/import-local",
        json={"source_keys": ["local:opencode"], "update_existing": True},
    )
    assert imported_again.status_code == 200, imported_again.text
    payload_again = imported_again.json()
    assert payload_again["imported_count"] == 0
    assert payload_again["updated_count"] == 1
    assert len([p for p in payload_again["profiles"] if p["source_key"] == "local:opencode"]) == 1


def test_tauri_ai_settings_models_endpoint_fetches_opencode_live(monkeypatch):
    client = _tauri_client(monkeypatch)
    from features.settings import routes as settings_routes

    monkeypatch.setattr(
        settings_routes,
        "list_opencode_models",
        lambda refresh=True: [
            "opencode/deepseek-v4-flash-free",
            "opencode/mimo-v2.5-free",
        ],
    )

    response = client.get("/api/settings/ai/models?provider=opencode&refresh=true")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["provider"] == "opencode"
    assert payload["source"] == "live"
    assert payload["models"] == [
        "opencode/deepseek-v4-flash-free",
        "opencode/mimo-v2.5-free",
    ]


def test_tauri_ai_settings_models_endpoint_uses_presets_for_native_gemini(monkeypatch):
    client = _tauri_client(monkeypatch)

    response = client.get("/api/settings/ai/models?provider=gemini")

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "gemini"
    assert payload["source"] == "preset"
    assert "Google 原生 Gemini" in payload["message"]


def test_tauri_ai_settings_models_endpoint_fetches_custom_gemini_relay_live(monkeypatch):
    client = _tauri_client(monkeypatch)
    from features.settings import routes as settings_routes

    calls = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(
                {
                    "data": [
                        {"id": "gemini-3.1-pro"},
                        {"id": "gemini-3.1-flash"},
                    ]
                }
            ).encode("utf-8")

    def fake_urlopen(req, timeout):
        calls.append(
            {
                "url": req.full_url,
                "auth": req.headers.get("Authorization"),
                "timeout": timeout,
            }
        )
        return FakeResponse()

    monkeypatch.setattr(settings_routes.urlrequest, "urlopen", fake_urlopen)
    monkeypatch.setenv("WRITER_TEST_PRESENT_KEY", "sk-test")

    response = client.get(
        "/api/settings/ai/models"
        "?provider=gemini"
        "&base_url=https%3A%2F%2Frelay.example"
        "&api_key_source=env%3AWRITER_TEST_PRESENT_KEY"
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["provider"] == "gemini"
    assert payload["source"] == "live"
    assert payload["models"] == ["gemini-3.1-pro", "gemini-3.1-flash"]
    assert calls == [
        {
            "url": "https://relay.example/v1/models",
            "auth": "Bearer sk-test",
            "timeout": 20,
        }
    ]


def test_tauri_ai_settings_models_endpoint_falls_back_to_public_pricing(monkeypatch):
    client = _tauri_client(monkeypatch)
    from features.settings import routes as settings_routes

    monkeypatch.setattr(
        settings_routes,
        "_fetch_openai_compatible_models",
        lambda base_url, api_key: (_ for _ in ()).throw(settings_routes.AiError("HTTP 403: forbidden")),
    )
    monkeypatch.setattr(
        settings_routes,
        "_fetch_public_pricing_models",
        lambda base_url: ["gemini-3.1-pro", "deepseek-v4-flash"],
    )
    monkeypatch.setenv("WRITER_TEST_PRESENT_KEY", "sk-test")

    response = client.get(
        "/api/settings/ai/models"
        "?provider=gemini"
        "&base_url=https%3A%2F%2Felysia.h-e.top"
        "&api_key_source=env%3AWRITER_TEST_PRESENT_KEY"
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["source"] == "live"
    assert payload["models"] == ["gemini-3.1-pro", "deepseek-v4-flash"]
    assert "模型广场" in payload["message"]


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


def test_tauri_ai_settings_live_test_uses_provider_and_reports_transport(monkeypatch):
    client = _tauri_client(monkeypatch)
    from features.settings import routes as settings_routes
    from writer.services.ai.interfaces import ChatResponse

    class FakeProvider:
        def chat(self, messages, *, model=None):
            assert "请轻微润色这句话" in messages[-1]["content"]
            return ChatResponse(
                content="雨夜车站，两个人就此告别。",
                model=model or "gemini-3.1-pro",
                provider="gemini",
                transport="gateway_compatible",
            )

    monkeypatch.setattr(settings_routes, "_provider_for_config", lambda config: FakeProvider())
    monkeypatch.setenv("WRITER_TEST_PRESENT_KEY", "test-key")

    response = client.post(
        "/api/settings/ai/test-live",
        json={
            "provider_name": "gemini",
            "base_url": "https://proxy.example",
            "wire_api": "responses",
            "model": "gemini-3.1-pro",
            "api_key_source": "env:WRITER_TEST_PRESENT_KEY",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["provider"] == "gemini"
    assert payload["model"] == "gemini-3.1-pro"
    assert payload["transport"] == "gateway_compatible"
    assert payload["preview"] == "雨夜车站，两个人就此告别。"


def test_tauri_ai_settings_live_test_sanitizes_html_errors(monkeypatch):
    client = _tauri_client(monkeypatch)
    from features.settings import routes as settings_routes
    from writer.services.ai.interfaces import AiError

    class FakeProvider:
        def chat(self, messages, *, model=None):
            raise AiError(
                "AI request failed: <!doctype html><html><title>403 | Forbidden</title></html>"
            )

    monkeypatch.setattr(settings_routes, "_provider_for_config", lambda config: FakeProvider())
    monkeypatch.setenv("WRITER_TEST_PRESENT_KEY", "test-key")

    response = client.post(
        "/api/settings/ai/test-live",
        json={
            "provider_name": "gemini",
            "base_url": "https://proxy.example",
            "wire_api": "responses",
            "model": "gemini-3.1-pro",
            "api_key_source": "env:WRITER_TEST_PRESENT_KEY",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is False
    assert "网页错误页" in payload["message"]
    assert "<!doctype html>" not in payload["message"]


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


def test_tauri_data_location_reports_current_paths(monkeypatch):
    client = _tauri_client(monkeypatch)

    response = client.get("/api/settings/data-location")

    assert response.status_code == 200
    data = response.json()
    assert data["data_dir"]
    assert data["database_path"].endswith("living-to-tell.sqlite3")
    assert data["backup_dir"].endswith("backups")
    assert data["checkpoint_dir"].endswith("checkpoints")
    assert data["database_exists"] is True


def test_tauri_data_location_migrate_copies_database_and_auxiliary_dirs(
    monkeypatch, tmp_path
):
    client = _tauri_client(monkeypatch)
    title = "迁移验证文章"
    created = client.post(
        "/api/articles",
        json={"title": title, "body": "迁移正文", "tags": []},
    )
    assert created.status_code == 201

    info = client.get("/api/settings/data-location").json()
    backup_dir = Path(info["backup_dir"])
    backup_dir.mkdir(parents=True, exist_ok=True)
    marker = backup_dir / "migration-marker.txt"
    marker.write_text("keep", encoding="utf-8")

    target = tmp_path / "living-to-tell-data"
    migrated = client.post(
        "/api/settings/data-location/migrate",
        json={"target_dir": str(target)},
    )

    assert migrated.status_code == 200
    result = migrated.json()
    assert result["restart_required"] is True
    target_db = target / "living-to-tell.sqlite3"
    assert target_db.exists()
    assert (target / "backups" / marker.name).read_text(encoding="utf-8") == "keep"

    with sqlite3.connect(target_db) as conn:
        row = conn.execute("SELECT title FROM entries WHERE title = ?", (title,)).fetchone()
    assert row == (title,)
    assert Path(info["database_path"]).exists()


def test_tauri_data_location_migrate_rejects_existing_database_by_default(
    monkeypatch, tmp_path
):
    client = _tauri_client(monkeypatch)
    target = tmp_path / "existing"
    target.mkdir()
    (target / "living-to-tell.sqlite3").write_text("existing", encoding="utf-8")

    response = client.post(
        "/api/settings/data-location/migrate",
        json={"target_dir": str(target)},
    )

    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_tauri_data_location_migrate_rejects_existing_auxiliary_dirs(
    monkeypatch, tmp_path
):
    client = _tauri_client(monkeypatch)
    target = tmp_path / "existing-auxiliary"
    existing_backups = target / "backups"
    existing_backups.mkdir(parents=True)
    (existing_backups / "keep.sqlite3").write_text("existing", encoding="utf-8")

    response = client.post(
        "/api/settings/data-location/migrate",
        json={"target_dir": str(target)},
    )

    assert response.status_code == 400
    assert "backups already exists" in response.json()["detail"]


def test_tauri_data_location_migrate_replace_existing_backups_auxiliary_dirs(
    monkeypatch, tmp_path
):
    client = _tauri_client(monkeypatch)
    client.post(
        "/api/articles",
        json={"title": "替换迁移文章", "body": "正文", "tags": []},
    )
    info = client.get("/api/settings/data-location").json()
    source_backup_dir = Path(info["backup_dir"])
    source_backup_dir.mkdir(parents=True, exist_ok=True)
    (source_backup_dir / "source.sqlite3").write_text("source", encoding="utf-8")

    target = tmp_path / "replace-existing"
    target.mkdir()
    conn = sqlite3.connect(target / "living-to-tell.sqlite3")
    conn.execute("CREATE TABLE old_data (id INTEGER)")
    conn.close()
    existing_backups = target / "backups"
    existing_backups.mkdir()
    (existing_backups / "old.sqlite3").write_text("old", encoding="utf-8")

    response = client.post(
        "/api/settings/data-location/migrate",
        json={"target_dir": str(target), "replace_existing": True},
    )

    assert response.status_code == 200, response.text
    assert (target / "living-to-tell.sqlite3").exists()
    assert (target / "backups" / "source.sqlite3").read_text(encoding="utf-8") == "source"
    assert list(target.glob("living-to-tell.sqlite3.before-migration-*"))
    assert list(target.glob("backups.before-migration-*"))


def test_tauri_data_location_copy_database_cleans_tmp_on_failure(monkeypatch, tmp_path):
    root = Path(__file__).resolve().parents[1]
    backend = root / "tauri-mvp" / "backend"
    sys.path.insert(0, str(backend))
    try:
        from features.settings.routes import _copy_database

        class BrokenConnection:
            def backup(self, destination):
                destination.execute("CREATE TABLE partial (id INTEGER)")
                raise sqlite3.Error("copy failed")

        target_db = tmp_path / "living-to-tell.sqlite3"
        try:
            _copy_database(SimpleNamespace(connection=BrokenConnection()), target_db)
        except sqlite3.Error:
            pass
        else:  # pragma: no cover - defensive
            raise AssertionError("copy failure was not raised")

        assert not target_db.exists()
        assert not (tmp_path / "living-to-tell.sqlite3.tmp").exists()
    finally:
        try:
            sys.path.remove(str(backend))
        except ValueError:
            pass


def test_tauri_backup_service_handles_single_quote_paths(monkeypatch, tmp_path):
    root = Path(__file__).resolve().parents[1]
    backend = root / "tauri-mvp" / "backend"
    data_dir = tmp_path / "O'Brien data"
    monkeypatch.setenv("WRITER_DATA_DIR", str(data_dir))
    sys.path.insert(0, str(backend))
    try:
        from features.backup.service import BackupService
        from writer.app.paths import DATABASE_FILENAME
        from writer.storage.database import open_and_initialize

        db_path = data_dir / DATABASE_FILENAME
        conn = open_and_initialize(db_path)
        conn.execute(
            "INSERT INTO entries (title, body, entry_type) VALUES (?, ?, ?)",
            ("quote path", "body", "fragment"),
        )
        conn.close()

        service = BackupService(str(db_path))
        backup_path = Path(service.create_auto_backup())
        checkpoint_path = Path(service.create_checkpoint("checkpoint", "desc"))

        assert backup_path.exists()
        assert checkpoint_path.exists()
    finally:
        try:
            sys.path.remove(str(backend))
        except ValueError:
            pass


def test_tauri_backup_restore_rejects_unmanaged_source(monkeypatch, tmp_path):
    root = Path(__file__).resolve().parents[1]
    backend = root / "tauri-mvp" / "backend"
    data_dir = tmp_path / "restore-data"
    monkeypatch.setenv("WRITER_DATA_DIR", str(data_dir))
    sys.path.insert(0, str(backend))
    try:
        from features.backup.service import BackupService
        from writer.app.paths import DATABASE_FILENAME
        from writer.storage.database import open_and_initialize

        db_path = data_dir / DATABASE_FILENAME
        conn = open_and_initialize(db_path)
        conn.execute(
            "INSERT INTO entries (title, body, entry_type) VALUES (?, ?, ?)",
            ("current", "body", "fragment"),
        )
        conn.commit()
        conn.close()

        unmanaged = tmp_path / "unmanaged.sqlite3"
        with sqlite3.connect(unmanaged) as conn:
            conn.execute("CREATE TABLE unrelated (id INTEGER)")

        service = BackupService(str(db_path))
        try:
            service.restore_from_backup(str(unmanaged))
        except ValueError as exc:
            assert "not managed" in str(exc)
        else:  # pragma: no cover - defensive
            raise AssertionError("unmanaged restore source was accepted")

        with sqlite3.connect(db_path) as conn:
            row = conn.execute("SELECT title FROM entries WHERE title = ?", ("current",)).fetchone()
        assert row == ("current",)
    finally:
        try:
            sys.path.remove(str(backend))
        except ValueError:
            pass


def test_tauri_backup_restore_api_rejects_unmanaged_file(monkeypatch, tmp_path):
    client = _tauri_client(monkeypatch)
    unmanaged = tmp_path / "outside.txt"
    unmanaged.write_text("not a backup", encoding="utf-8")

    response = client.post(
        "/api/backup/restore",
        json={"backup_path": str(unmanaged)},
    )

    assert response.status_code == 400
    assert "not managed" in response.json()["detail"]


def test_tauri_backup_restore_copy_failure_keeps_current_database(
    monkeypatch, tmp_path
):
    root = Path(__file__).resolve().parents[1]
    backend = root / "tauri-mvp" / "backend"
    data_dir = tmp_path / "restore-copy-failure"
    monkeypatch.setenv("WRITER_DATA_DIR", str(data_dir))
    sys.path.insert(0, str(backend))
    try:
        from features.backup import service as backup_module
        from features.backup.service import BackupService
        from writer.app.paths import DATABASE_FILENAME
        from writer.storage.database import open_and_initialize

        db_path = data_dir / DATABASE_FILENAME
        conn = open_and_initialize(db_path)
        conn.execute(
            "INSERT INTO entries (title, body, entry_type) VALUES (?, ?, ?)",
            ("backup version", "body", "fragment"),
        )
        conn.commit()
        conn.close()

        service = BackupService(str(db_path))
        backup_path = service.create_auto_backup()

        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE entries SET title = ?", ("current version",))
            conn.commit()

        def broken_copy(_source, destination):
            Path(destination).write_text("partial", encoding="utf-8")
            raise OSError("disk full")

        monkeypatch.setattr(backup_module.shutil, "copy2", broken_copy)
        try:
            service.restore_from_backup(backup_path)
        except OSError:
            pass
        else:  # pragma: no cover - defensive
            raise AssertionError("copy failure was not raised")

        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                "SELECT title FROM entries WHERE title = ?",
                ("current version",),
            ).fetchone()
        assert row == ("current version",)
        assert not list(data_dir.glob("*.restore-*.tmp"))
    finally:
        try:
            sys.path.remove(str(backend))
        except ValueError:
            pass


def test_tauri_docx_export_cleans_temp_file_on_generation_failure(
    monkeypatch, tmp_path
):
    client = _tauri_client(monkeypatch)
    entry = client.post(
        "/api/articles",
        json={"title": "失败导出", "body": "正文", "tags": []},
    ).json()

    import features.articles.routes as article_routes

    original_named_temp = article_routes.tempfile.NamedTemporaryFile

    def named_temp_in_tmp(*args, **kwargs):
        kwargs["dir"] = tmp_path
        return original_named_temp(*args, **kwargs)

    def fail_export(_entry, output_path):
        Path(output_path).write_text("partial", encoding="utf-8")
        raise RuntimeError("docx failed")

    monkeypatch.setattr(article_routes.tempfile, "NamedTemporaryFile", named_temp_in_tmp)
    monkeypatch.setattr(article_routes, "_export_entry_docx", fail_export)

    try:
        client.get(f"/api/articles/{entry['id']}/export?format=docx")
    except RuntimeError:
        pass
    else:  # pragma: no cover - defensive
        raise AssertionError("docx export failure was not raised")

    assert not list(tmp_path.glob("*.docx"))


def test_tauri_collection_docx_export_cleans_temp_file_on_generation_failure(
    monkeypatch, tmp_path
):
    client = _tauri_client(monkeypatch)
    collection = client.post(
        "/api/collections",
        json={"title": "失败作品集", "description": ""},
    ).json()

    import features.collections.routes as collection_routes
    from writer.services.export.collection_exporter import CollectionExportService

    original_named_temp = collection_routes.tempfile.NamedTemporaryFile

    def named_temp_in_tmp(*args, **kwargs):
        kwargs["dir"] = tmp_path
        return original_named_temp(*args, **kwargs)

    def fail_export(self, collection_id, output_path):
        Path(output_path).write_text("partial", encoding="utf-8")
        raise RuntimeError("collection docx failed")

    monkeypatch.setattr(collection_routes.tempfile, "NamedTemporaryFile", named_temp_in_tmp)
    monkeypatch.setattr(CollectionExportService, "export_collection_docx", fail_export)

    try:
        client.get(f"/api/collections/{collection['id']}/export?format=docx")
    except RuntimeError:
        pass
    else:  # pragma: no cover - defensive
        raise AssertionError("collection docx export failure was not raised")

    assert not list(tmp_path.glob("*.docx"))
