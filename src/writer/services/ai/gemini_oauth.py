"""In-app Google OAuth 2.0 flow for Gemini CLI / Code Assist.

Starts a local loopback server on 127.0.0.1, opens the system browser to the
official Google OAuth authorization endpoint, and captures the authorization
code on redirect. It then exchanges the code for tokens and persists them into
``~/.gemini/oauth_creds.json`` and ``~/.gemini/google_accounts.json`` so that
Writer (and the official Gemini CLI) can immediately reuse the credentials.
"""
from __future__ import annotations

from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import secrets
import threading
import time
from typing import Optional
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

from writer.services.ai.gemini_cli_provider import (
    _normalise_proxy_url,
    _resolve_gemini_cli_oauth_client,
    detect_gemini_cli_proxy,
)

GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_ENDPOINT = "https://www.googleapis.com/oauth2/v2/userinfo"

OAUTH_SCOPES = (
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
)

SUCCESS_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="utf-8">
    <title>Google 账号授权成功</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
            margin: 0;
            background: #f8fafc;
            color: #1e293b;
        }
        .card {
            background: #ffffff;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            text-align: center;
            max-width: 420px;
        }
        .icon {
            font-size: 48px;
            color: #10b981;
            margin-bottom: 16px;
        }
        h2 {
            margin: 0 0 12px;
            font-size: 22px;
        }
        p {
            margin: 0 0 24px;
            color: #64748b;
            font-size: 14px;
            line-height: 1.5;
        }
        .badge {
            display: inline-block;
            background: #f1f5f9;
            color: #334155;
            padding: 6px 12px;
            border-radius: 6px;
            font-family: monospace;
            font-size: 13px;
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">✓</div>
        <h2>Google 账号授权成功</h2>
        <p>Writer 软件已成功连接您的 Google 账号。您可以关闭此浏览器窗口并返回软件继续使用。</p>
        <div class="badge">Living to Tell · 活着为了讲述</div>
    </div>
</body>
</html>
"""

FAILURE_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="utf-8">
    <title>Google 账号授权失败</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
            margin: 0;
            background: #f8fafc;
            color: #1e293b;
        }
        .card {
            background: #ffffff;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            text-align: center;
            max-width: 420px;
        }
        .icon {
            font-size: 48px;
            color: #ef4444;
            margin-bottom: 16px;
        }
        h2 {
            margin: 0 0 12px;
            font-size: 22px;
        }
        p {
            margin: 0;
            color: #64748b;
            font-size: 14px;
            line-height: 1.5;
        }
        .error-box {
            margin-top: 16px;
            background: #fef2f2;
            color: #b91c1c;
            padding: 10px;
            border-radius: 6px;
            font-size: 13px;
            word-break: break-word;
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">✕</div>
        <h2>授权未完成</h2>
        <p>未能成功获取 Google 授权，请返回 Writer 软件重新尝试。</p>
        <div class="error-box">{error_message}</div>
    </div>
</body>
</html>
"""


@dataclass(frozen=True)
class GeminiOAuthResult:
    success: bool
    email: Optional[str] = None
    error: Optional[str] = None
    cancelled: bool = False


class GeminiOAuthFlow:
    """Manages an interactive OAuth 2.0 loopback authentication session."""

    def __init__(
        self,
        *,
        proxy_url: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        timeout_seconds: int = 180,
    ) -> None:
        self._proxy_url = (
            _normalise_proxy_url(proxy_url) if proxy_url else detect_gemini_cli_proxy()
        )
        resolved_client = _resolve_gemini_cli_oauth_client()
        self._client_id = (
            client_id
            or (resolved_client.client_id if resolved_client else None)
        )
        self._client_secret = (
            client_secret
            or (resolved_client.client_secret if resolved_client else None)
        )
        self._timeout_seconds = max(30, int(timeout_seconds))

        self._server: Optional[HTTPServer] = None
        self._server_thread: Optional[threading.Thread] = None
        self._state: str = secrets.token_hex(32)
        self._callback_received = threading.Event()
        self._auth_code: Optional[str] = None
        self._auth_error: Optional[str] = None
        self._cancelled: bool = False

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled

    def cancel(self) -> None:
        """Cancel the ongoing flow and shut down the local server."""
        self._cancelled = True
        self._callback_received.set()
        self._shutdown_server()

    def run(self, *, open_browser: bool = True) -> GeminiOAuthResult:
        """Execute the OAuth login flow synchronously.

        Returns a ``GeminiOAuthResult`` with the status and authenticated email.
        """
        if not self._client_id or not self._client_secret:
            return GeminiOAuthResult(
                success=False,
                error="未找到 Gemini CLI 客户端凭据。请确保已安装 @google/gemini-cli 或设置 GEMINI_CLI_OAUTH_CLIENT_ID 环境变量。",
            )

        port = self._start_local_server()
        redirect_uri = f"http://127.0.0.1:{port}/oauth2callback"
        auth_url = self._build_auth_url(redirect_uri)

        if open_browser:
            try:
                webbrowser.open(auth_url)
            except Exception as exc:  # noqa: BLE001
                self.cancel()
                return GeminiOAuthResult(
                    success=False,
                    error=f"无法打开系统浏览器: {exc}",
                )

        # Wait for the browser redirect callback
        finished = self._callback_received.wait(timeout=self._timeout_seconds)
        self._shutdown_server()

        if self._cancelled:
            return GeminiOAuthResult(success=False, cancelled=True)

        if not finished:
            return GeminiOAuthResult(
                success=False,
                error=f"授权超时（超过 {self._timeout_seconds} 秒无响应）",
            )

        if self._auth_error:
            return GeminiOAuthResult(
                success=False,
                error=f"Google 授权返回错误: {self._auth_error}",
            )

        if not self._auth_code:
            return GeminiOAuthResult(
                success=False,
                error="未能获取授权码",
            )

        # Exchange authorization code for tokens
        try:
            tokens = self._exchange_code_for_tokens(self._auth_code, redirect_uri)
        except Exception as exc:  # noqa: BLE001
            return GeminiOAuthResult(
                success=False,
                error=f"换取令牌失败: {exc}",
            )

        # Fetch email
        access_token = tokens.get("access_token")
        email = None
        if access_token:
            try:
                email = self._fetch_user_email(access_token)
            except Exception:  # noqa: BLE001
                email = None

        # Persist credentials
        try:
            self._save_credentials(tokens, email)
        except Exception as exc:  # noqa: BLE001
            return GeminiOAuthResult(
                success=False,
                error=f"保存授权文件失败: {exc}",
            )

        return GeminiOAuthResult(success=True, email=email)

    def _start_local_server(self) -> int:
        handler_cls = self._create_request_handler()
        # Bind to 127.0.0.1 with port 0 for automatic OS port assignment
        server = HTTPServer(("127.0.0.1", 0), handler_cls)
        self._server = server
        port = server.server_port

        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self._server_thread = thread
        return port

    def _shutdown_server(self) -> None:
        if self._server:
            try:
                self._server.shutdown()
                self._server.server_close()
            except Exception:  # noqa: BLE001
                pass
            self._server = None

    def _build_auth_url(self, redirect_uri: str) -> str:
        params = {
            "client_id": self._client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(OAUTH_SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "state": self._state,
        }
        return f"{GOOGLE_AUTH_ENDPOINT}?{urllib.parse.urlencode(params)}"

    def _create_request_handler(self):
        flow = self

        class _OAuthCallbackHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):  # noqa: A002
                # Suppress default server access logging
                pass

            def do_GET(self):  # noqa: N802
                url_parts = urllib.parse.urlparse(self.path)
                if url_parts.path != "/oauth2callback":
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(b"Not Found")
                    return

                params = urllib.parse.parse_qs(url_parts.query)
                error_param = params.get("error", [None])[0]
                state_param = params.get("state", [None])[0]
                code_param = params.get("code", [None])[0]

                if error_param:
                    flow._auth_error = error_param
                    self._send_html(
                        FAILURE_HTML_TEMPLATE.replace(
                            "{error_message}", f"错误代码: {error_param}"
                        ),
                        status=400,
                    )
                    flow._callback_received.set()
                    return

                if state_param != flow._state:
                    flow._auth_error = "state_mismatch"
                    self._send_html(
                        FAILURE_HTML_TEMPLATE.replace(
                            "{error_message}", "安全校验失败 (CSRF State Mismatch)"
                        ),
                        status=400,
                    )
                    flow._callback_received.set()
                    return

                if not code_param:
                    flow._auth_error = "missing_code"
                    self._send_html(
                        FAILURE_HTML_TEMPLATE.replace(
                            "{error_message}", "未收到授权码 (Missing code)"
                        ),
                        status=400,
                    )
                    flow._callback_received.set()
                    return

                flow._auth_code = code_param
                self._send_html(SUCCESS_HTML, status=200)
                flow._callback_received.set()

            def _send_html(self, html_content: str, status: int = 200) -> None:
                body = html_content.encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        return _OAuthCallbackHandler

    def _exchange_code_for_tokens(self, code: str, redirect_uri: str) -> dict:
        body = urllib.parse.urlencode(
            {
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            GOOGLE_TOKEN_ENDPOINT,
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        opener = self._build_opener()
        with opener.open(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Token response was not a JSON object")
        return data

    def _fetch_user_email(self, access_token: str) -> Optional[str]:
        req = urllib.request.Request(
            GOOGLE_USERINFO_ENDPOINT,
            headers={"Authorization": f"Bearer {access_token}"},
            method="GET",
        )
        opener = self._build_opener()
        with opener.open(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if isinstance(data, dict) and isinstance(data.get("email"), str):
            return data["email"].strip()
        return None

    def _build_opener(self) -> urllib.request.OpenerDirector:
        if self._proxy_url:
            return urllib.request.build_opener(
                urllib.request.ProxyHandler(
                    {"http": self._proxy_url, "https": self._proxy_url}
                )
            )
        return urllib.request.build_opener()

    def _save_credentials(self, tokens: dict, email: Optional[str]) -> None:
        gemini_dir = Path.home() / ".gemini"
        gemini_dir.mkdir(parents=True, exist_ok=True)

        creds_path = gemini_dir / "oauth_creds.json"
        existing: dict = {}
        if creds_path.exists():
            try:
                existing = json.loads(creds_path.read_text(encoding="utf-8"))
                if not isinstance(existing, dict):
                    existing = {}
            except Exception:  # noqa: BLE001
                existing = {}

        # Calculate expiry_date in milliseconds since epoch
        expires_in = tokens.get("expires_in")
        expiry_date = None
        if isinstance(expires_in, (int, float)):
            expiry_date = int((time.time() + expires_in) * 1000)

        saved_data = {
            "access_token": tokens.get("access_token") or existing.get("access_token", ""),
            "refresh_token": tokens.get("refresh_token") or existing.get("refresh_token", ""),
            "scope": tokens.get("scope") or existing.get("scope", " ".join(OAUTH_SCOPES)),
            "token_type": tokens.get("token_type") or existing.get("token_type", "Bearer"),
            "id_token": tokens.get("id_token") or existing.get("id_token", ""),
        }
        if expiry_date:
            saved_data["expiry_date"] = expiry_date

        creds_path.write_text(
            json.dumps(saved_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        if email:
            accounts_path = gemini_dir / "google_accounts.json"
            accounts_data: dict = {}
            if accounts_path.exists():
                try:
                    accounts_data = json.loads(accounts_path.read_text(encoding="utf-8"))
                    if not isinstance(accounts_data, dict):
                        accounts_data = {}
                except Exception:  # noqa: BLE001
                    accounts_data = {}
            active = accounts_data.get("active")
            old_list = accounts_data.get("old", [])
            if not isinstance(old_list, list):
                old_list = []
            if active and active != email and active not in old_list:
                old_list.insert(0, active)
            accounts_data["active"] = email
            accounts_data["old"] = [acc for acc in old_list if acc != email]
            accounts_path.write_text(
                json.dumps(accounts_data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
