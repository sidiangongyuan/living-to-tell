from __future__ import annotations

from http.client import HTTPConnection
import json
from pathlib import Path
import urllib.parse
from unittest.mock import MagicMock

import pytest

from writer.app.container import build_container
from writer.services.ai.gemini_oauth import (
    GOOGLE_AUTH_ENDPOINT,
    OAUTH_SCOPES,
    GeminiOAuthFlow,
    GeminiOAuthResult,
)
from writer.ui.dialogs.settings_dialog import SettingsDialog
from writer.ui.i18n import TR


def test_gemini_oauth_builds_valid_auth_url():
    flow = GeminiOAuthFlow(
        client_id="test-client-id",
        client_secret="test-client-secret",
    )
    redirect_uri = "http://127.0.0.1:54321/oauth2callback"
    url = flow._build_auth_url(redirect_uri)

    assert url.startswith(GOOGLE_AUTH_ENDPOINT)
    parsed = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed.query)

    assert params["client_id"] == ["test-client-id"]
    assert params["redirect_uri"] == [redirect_uri]
    assert params["response_type"] == ["code"]
    assert params["access_type"] == ["offline"]
    assert params["prompt"] == ["consent"]
    assert params["state"] == [flow._state]
    assert params["scope"] == [" ".join(OAUTH_SCOPES)]


def test_gemini_oauth_local_server_success_callback():
    flow = GeminiOAuthFlow()
    port = flow._start_local_server()
    try:
        conn = HTTPConnection("127.0.0.1", port, timeout=5)
        path = f"/oauth2callback?code=mock_auth_code_123&state={flow._state}"
        conn.request("GET", path)
        resp = conn.getresponse()
        assert resp.status == 200
        body = resp.read().decode("utf-8")
        assert "Google 账号授权成功" in body

        assert flow._callback_received.is_set()
        assert flow._auth_code == "mock_auth_code_123"
        assert flow._auth_error is None
    finally:
        flow._shutdown_server()


def test_gemini_oauth_local_server_error_callback():
    flow = GeminiOAuthFlow()
    port = flow._start_local_server()
    try:
        conn = HTTPConnection("127.0.0.1", port, timeout=5)
        path = f"/oauth2callback?error=access_denied&state={flow._state}"
        conn.request("GET", path)
        resp = conn.getresponse()
        assert resp.status == 400
        body = resp.read().decode("utf-8")
        assert "授权未完成" in body

        assert flow._callback_received.is_set()
        assert flow._auth_error == "access_denied"
        assert flow._auth_code is None
    finally:
        flow._shutdown_server()


def test_gemini_oauth_local_server_state_mismatch():
    flow = GeminiOAuthFlow()
    port = flow._start_local_server()
    try:
        conn = HTTPConnection("127.0.0.1", port, timeout=5)
        path = "/oauth2callback?code=mock_code&state=wrong_state"
        conn.request("GET", path)
        resp = conn.getresponse()
        assert resp.status == 400
        body = resp.read().decode("utf-8")
        assert "CSRF" in body

        assert flow._callback_received.is_set()
        assert flow._auth_error == "state_mismatch"
    finally:
        flow._shutdown_server()


def test_gemini_oauth_local_server_not_found():
    flow = GeminiOAuthFlow()
    port = flow._start_local_server()
    try:
        conn = HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", "/invalid_path")
        resp = conn.getresponse()
        assert resp.status == 404
        assert not flow._callback_received.is_set()
    finally:
        flow._shutdown_server()


def test_gemini_oauth_cancel():
    flow = GeminiOAuthFlow()
    flow._start_local_server()
    assert flow._server is not None
    flow.cancel()
    assert flow.is_cancelled
    assert flow._server is None


def test_gemini_oauth_save_credentials(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    flow = GeminiOAuthFlow()
    tokens = {
        "access_token": "mock_access_token",
        "refresh_token": "mock_refresh_token",
        "expires_in": 3600,
        "scope": "test_scope",
        "token_type": "Bearer",
        "id_token": "mock_id_token",
    }
    email = "writer_user@example.com"

    flow._save_credentials(tokens, email)

    creds_file = tmp_path / ".gemini" / "oauth_creds.json"
    assert creds_file.exists()
    saved_creds = json.loads(creds_file.read_text(encoding="utf-8"))
    assert saved_creds["access_token"] == "mock_access_token"
    assert saved_creds["refresh_token"] == "mock_refresh_token"
    assert "expiry_date" in saved_creds

    accounts_file = tmp_path / ".gemini" / "google_accounts.json"
    assert accounts_file.exists()
    saved_accounts = json.loads(accounts_file.read_text(encoding="utf-8"))
    assert saved_accounts["active"] == "writer_user@example.com"


def test_settings_dialog_gemini_cli_login_button_toggle(isolated_data_dir: Path, qtbot):
    container = build_container()
    try:
        dlg = SettingsDialog(container.settings)
        qtbot.addWidget(dlg)
        dlg.show()
        qtbot.waitUntil(dlg.isVisible)

        # Initially or if provider is openai: login button hidden
        idx_openai = dlg._provider_combo.findData("openai")
        if idx_openai >= 0:
            dlg._provider_combo.setCurrentIndex(idx_openai)
            assert not dlg._gemini_login_button.isVisible()

        # When switched to gemini_cli: login button visible
        idx_gemini_cli = dlg._provider_combo.findData("gemini_cli")
        assert idx_gemini_cli >= 0
        dlg._provider_combo.setCurrentIndex(idx_gemini_cli)
        assert dlg._gemini_login_button.isVisible()
    finally:
        container.close()
