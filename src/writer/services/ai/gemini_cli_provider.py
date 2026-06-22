"""Gemini CLI provider adapter.

Experimental bridge for users who authenticate the official/local Gemini CLI
with OAuth. Writer does not read OAuth tokens directly; instead it delegates a
single prompt to the installed ``gemini`` command and captures the text output.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Callable, List, Optional

from writer.domain.models.ai_config import AiConfig
from writer.services.ai.interfaces import (
    AiError,
    AiProvider,
    ChatResponse,
    RewriteRequest,
    RewriteResponse,
)
from writer.services.ai.prompt_builder import PromptBuilder


GEMINI_CLI_PROVIDER = "gemini_cli"
GEMINI_CLI_AUTH_SOURCE = "gemini-cli"
GEMINI_CLI_DEFAULT_MODEL = "gemini-cli-default"
GEMINI_CLI_MODEL_PRESETS = (
    GEMINI_CLI_DEFAULT_MODEL,
    "gemini-3.1-pro-preview",
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite-preview",
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
)
GEMINI_CLI_PROXY_ENV = "WRITER_GEMINI_CLI_PROXY"
GEMINI_CLI_TIMEOUT_ENV = "WRITER_GEMINI_CLI_TIMEOUT_SECONDS"
GEMINI_CLI_OAUTH_CLIENT_ID_ENV = "WRITER_GEMINI_CLI_OAUTH_CLIENT_ID"
GEMINI_CLI_OAUTH_CLIENT_SECRET_ENV = "WRITER_GEMINI_CLI_OAUTH_CLIENT_SECRET"
GEMINI_CLI_DEFAULT_TIMEOUT_SECONDS = 120
_GOOGLE_OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
_CODE_ASSIST_ENDPOINT = "https://cloudcode-pa.googleapis.com"
_CODE_ASSIST_API_VERSION = "v1internal"
_CODE_ASSIST_DEFAULT_MODEL = "gemini-2.5-pro"

_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
_OAUTH_CLIENT_ID_RE = re.compile(
    r'\bOAUTH_CLIENT_ID\s*=\s*["\']([^"\']+\.apps\.googleusercontent\.com)["\']'
)
_OAUTH_CLIENT_SECRET_RE = re.compile(
    r'\bOAUTH_CLIENT_SECRET\s*=\s*["\']([^"\']+)["\']'
)
_GOOGLE_CLIENT_ID_RE = re.compile(
    r'["\']([0-9]+-[a-z0-9]+\.apps\.googleusercontent\.com)["\']',
    re.IGNORECASE,
)
_GOOGLE_CLIENT_SECRET_RE = re.compile(r'["\'](GOCSPX-[A-Za-z0-9_-]+)["\']')
_NOISE_PREFIXES = (
    "Ripgrep is not available. Falling back to GrepTool.",
)
_AUTH_PROMPT_MARKERS = (
    "Opening authentication page in your browser",
    "Do you want to continue? [Y/n]",
    "Waiting for authentication",
    "Manual authorization is required",
    "Authentication timed out",
)
_PROXY_ENV_KEYS = (
    "HTTPS_PROXY",
    "HTTP_PROXY",
    "ALL_PROXY",
    "https_proxy",
    "http_proxy",
    "all_proxy",
)
_OPENAI_DEFAULT_MODELS = {"gpt-4o-mini"}


@dataclass(frozen=True)
class GeminiCliOAuthStatus:
    available: bool
    creds_path: Path
    account: Optional[str] = None
    reason: str = ""


@dataclass(frozen=True)
class GeminiCliQuotaStatus:
    available: bool
    account: Optional[str] = None
    project_id: Optional[str] = None
    current_tier: Optional[str] = None
    paid_tier: Optional[str] = None
    credits: Optional[str] = None
    manage_subscription_uri: Optional[str] = None
    reason: str = ""


@dataclass(frozen=True)
class _GeminiCliRunResult:
    text: str
    model: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None


@dataclass(frozen=True)
class _OAuthClient:
    client_id: str
    client_secret: str


class GeminiCliProvider(AiProvider):
    """Adapter that shells out to the local Gemini CLI."""

    name = GEMINI_CLI_PROVIDER

    def __init__(
        self,
        config: AiConfig,
        prompt_builder: PromptBuilder,
        *,
        command: Optional[str] = None,
        runner: Optional[Callable[..., subprocess.CompletedProcess]] = None,
        timeout_seconds: Optional[int] = None,
    ) -> None:
        self._config = config
        self._prompts = prompt_builder
        self._command = command
        self._runner = runner
        self._timeout_seconds = _resolve_timeout_seconds(timeout_seconds)

    def rewrite(self, request_obj: RewriteRequest) -> RewriteResponse:
        messages = self._prompts.build_messages(request_obj)
        used_model = self._model_name(self._config.model)
        result = self._run_prompt(_messages_to_prompt(messages), model=used_model)
        return RewriteResponse(
            content=result.text,
            model=result.model,
            provider=self.name,
            transport="gemini_cli",
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
        )

    def chat(self, messages, *, model=None) -> ChatResponse:
        used_model = self._model_name(model or self._config.model)
        result = self._run_prompt(_messages_to_prompt(list(messages)), model=used_model)
        return ChatResponse(
            content=result.text,
            model=result.model,
            provider=self.name,
            transport="gemini_cli",
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
        )

    def _run_prompt(self, prompt: str, *, model: Optional[str]) -> _GeminiCliRunResult:
        command = self._resolve_command()
        cmd = _command_prefix(command) + ["--skip-trust"]
        if model:
            cmd.extend(["--model", model])
        cmd.extend(["--prompt", prompt])

        env = dict(os.environ)
        env.setdefault("GEMINI_CLI_TRUST_WORKSPACE", "true")
        proxy_url = _apply_gemini_cli_proxy_env(
            env, getattr(self._config, "gemini_cli_proxy", None)
        )
        direct_output = _try_run_code_assist_prompt(
            prompt,
            model=model,
            proxy_url=proxy_url,
            timeout_seconds=self._timeout_seconds,
        )
        if direct_output is not None:
            return direct_output

        oauth_token_injected = _try_apply_gemini_cli_oauth_env(
            env, proxy_url=proxy_url
        )
        try:
            if self._runner is not None:
                completed = self._runner(
                    cmd,
                    capture_output=True,
                    input="",
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=self._timeout_seconds,
                    env=env,
                )
            else:
                completed = _run_subprocess_tree(
                    cmd, timeout_seconds=self._timeout_seconds, env=env
                )
        except FileNotFoundError as exc:
            raise AiError(
                "Gemini CLI was not found. Install it with `npm install -g "
                "@google/gemini-cli`, or add gemini.cmd to PATH."
            ) from exc
        except subprocess.TimeoutExpired as exc:
            if oauth_token_injected:
                proxy_note = f" via proxy {proxy_url}" if proxy_url else ""
                raise AiError(
                    f"Gemini CLI timed out after {self._timeout_seconds} seconds "
                    "after Writer injected a refreshed OAuth access token"
                    f"{proxy_note}. "
                    "This usually means Gemini Code Assist could not reach "
                    "cloudcode-pa.googleapis.com, or the service is very slow. "
                    "Check the network/proxy/VPN path to cloudcode-pa.googleapis.com, "
                    f"or increase {GEMINI_CLI_TIMEOUT_ENV}."
                ) from exc
            raise AiError(
                f"Gemini CLI timed out after {self._timeout_seconds} seconds. "
                "Writer uses Gemini CLI headless mode (`gemini --skip-trust "
                "--prompt ...`). Interactive Gemini CLI chat can work while "
                "headless mode still waits for OAuth/browser authentication. "
                "Run that exact headless command in a normal terminal and fix "
                "any login/page error there before retrying Writer. If the "
                "browser callback page fails, run `set NO_BROWSER=true`, then "
                "run `gemini`, use `/auth`, open the printed URL manually, "
                "and paste the authorization code back into Gemini CLI. To "
                f"allow more time, set {GEMINI_CLI_TIMEOUT_ENV}."
            ) from exc
        except Exception as exc:  # noqa: BLE001
            raise AiError(f"Gemini CLI failed to start: {exc}") from exc

        raw_stdout = completed.stdout or ""
        raw_stderr = completed.stderr or ""
        stdout = _clean_output(raw_stdout)
        stderr = _clean_output(raw_stderr)
        combined_raw = "\n".join(part for part in (raw_stdout, raw_stderr) if part)
        if _looks_like_auth_prompt(combined_raw) and not _has_non_auth_output(combined_raw):
            raise AiError(_auth_prompt_message())
        if completed.returncode != 0:
            message = stderr or stdout or f"exit code {completed.returncode}"
            raise AiError(f"Gemini CLI request failed: {message}")
        if not stdout.strip():
            raise AiError("Gemini CLI returned no text output.")
        return _GeminiCliRunResult(
            text=stdout.strip(),
            model=model or GEMINI_CLI_DEFAULT_MODEL,
        )

    def _resolve_command(self) -> str:
        configured = (self._command or os.environ.get("WRITER_GEMINI_CLI_COMMAND") or "").strip()
        if configured:
            return configured
        found = find_gemini_cli()
        if found:
            return found
        raise FileNotFoundError("gemini")

    @staticmethod
    def _model_name(value: Optional[str]) -> Optional[str]:
        raw = (value or "").strip()
        if not raw or raw.lower() in {
            "default",
            "auto",
            GEMINI_CLI_DEFAULT_MODEL,
            *_OPENAI_DEFAULT_MODELS,
        }:
            return None
        return raw


def find_gemini_cli() -> Optional[str]:
    """Return a usable Gemini CLI command path if available."""
    return (
        shutil.which("gemini.cmd")
        or shutil.which("gemini")
        or shutil.which("gemini.ps1")
    )


def _default_oauth_creds_path() -> Path:
    return Path.home() / ".gemini" / "oauth_creds.json"


def gemini_cli_oauth_status() -> GeminiCliOAuthStatus:
    """Return non-secret Gemini CLI OAuth status for UI display."""
    path = _default_oauth_creds_path()
    if not path.exists():
        return GeminiCliOAuthStatus(False, path, reason="missing_file")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return GeminiCliOAuthStatus(False, path, reason="unreadable")
    refresh_token = raw.get("refresh_token")
    if not isinstance(refresh_token, str) or not refresh_token.strip():
        return GeminiCliOAuthStatus(False, path, reason="missing_refresh_token")
    return GeminiCliOAuthStatus(True, path, account=_read_gemini_cli_account_email())


def gemini_cli_quota_status(
    *,
    proxy_url: Optional[str] = None,
    timeout_seconds: int = 20,
) -> GeminiCliQuotaStatus:
    """Fetch non-secret Gemini Code Assist tier/quota status for UI display."""
    account = _read_gemini_cli_account_email()
    access_token = _refresh_gemini_cli_access_token(proxy_url=proxy_url)
    if not access_token:
        return GeminiCliQuotaStatus(False, account=account, reason="missing_oauth")
    try:
        load_res = _load_code_assist(
            access_token=access_token,
            proxy_url=proxy_url,
            timeout_seconds=timeout_seconds,
        )
    except AiError as exc:
        return GeminiCliQuotaStatus(False, account=account, reason=str(exc))
    return _quota_status_from_load_response(load_res, account=account)


def detect_gemini_cli_proxy(env: Optional[dict[str, str]] = None) -> Optional[str]:
    """Detect the proxy Writer should pass to Gemini CLI, if any."""
    source = env if env is not None else os.environ
    configured = (source.get(GEMINI_CLI_PROXY_ENV) or "").strip()
    if configured:
        return _normalise_proxy_url(configured)
    existing = _first_proxy_from_env(source)
    if existing:
        return _normalise_proxy_url(existing)
    return _windows_system_proxy_url()


def _try_apply_gemini_cli_oauth_env(
    env: dict[str, str], *, proxy_url: Optional[str] = None
) -> bool:
    """Inject a short-lived OAuth access token for Gemini CLI Code Assist.

    Gemini CLI's headless mode can ask to open a browser even when the old
    ``~/.gemini/oauth_creds.json`` refresh token is still valid. The CLI also
    has a documented-in-code bypass for Google Code Assist: when
    ``GOOGLE_GENAI_USE_GCA`` and ``GOOGLE_CLOUD_ACCESS_TOKEN`` are present, it
    uses the provided bearer token instead of launching browser OAuth. Writer
    refreshes the access token at call time only and never persists it.
    """
    if env.get("GOOGLE_CLOUD_ACCESS_TOKEN"):
        env.setdefault("GOOGLE_GENAI_USE_GCA", "true")
        return True
    access_token = _refresh_gemini_cli_access_token(proxy_url=proxy_url)
    if not access_token:
        return False
    env["GOOGLE_GENAI_USE_GCA"] = "true"
    env["GOOGLE_CLOUD_ACCESS_TOKEN"] = access_token
    return True


def _refresh_gemini_cli_access_token(
    creds_path: Optional[Path] = None,
    *,
    proxy_url: Optional[str] = None,
) -> Optional[str]:
    path = creds_path or _default_oauth_creds_path()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    refresh_token = raw.get("refresh_token")
    if not isinstance(refresh_token, str) or not refresh_token.strip():
        return None
    oauth_client = _resolve_gemini_cli_oauth_client()
    if oauth_client is None:
        return None
    body = urllib.parse.urlencode(
        {
            "client_id": oauth_client.client_id,
            "client_secret": oauth_client.client_secret,
            "refresh_token": refresh_token.strip(),
            "grant_type": "refresh_token",
        }
    ).encode("utf-8")
    req = urllib.request.Request(_GOOGLE_OAUTH_TOKEN_URL, data=body, method="POST")
    opener = (
        urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url})
        )
        if proxy_url
        else urllib.request.build_opener()
    )
    try:
        with opener.open(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, ValueError, json.JSONDecodeError):
        return None
    access_token = payload.get("access_token")
    return access_token.strip() if isinstance(access_token, str) else None


def _resolve_gemini_cli_oauth_client() -> Optional[_OAuthClient]:
    """Discover Gemini CLI OAuth client metadata without storing it in Writer.

    Gemini CLI OAuth refresh tokens are bound to Gemini CLI's installed-app
    OAuth client. Writer first honors explicit environment overrides, then
    reads the already-installed Gemini CLI bundle to find those public client
    metadata values at runtime. No OAuth tokens are persisted by Writer.
    """
    env_client_id = os.environ.get(GEMINI_CLI_OAUTH_CLIENT_ID_ENV, "").strip()
    env_client_secret = os.environ.get(GEMINI_CLI_OAUTH_CLIENT_SECRET_ENV, "").strip()
    if env_client_id and env_client_secret:
        return _OAuthClient(env_client_id, env_client_secret)

    for path in _gemini_cli_bundle_candidate_files():
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        client = _extract_gemini_cli_oauth_client_from_text(text)
        if client is not None:
            return client
    return None


def _extract_gemini_cli_oauth_client_from_text(text: str) -> Optional[_OAuthClient]:
    id_match = _OAUTH_CLIENT_ID_RE.search(text)
    secret_match = _OAUTH_CLIENT_SECRET_RE.search(text)
    if id_match and secret_match:
        return _OAuthClient(id_match.group(1).strip(), secret_match.group(1).strip())

    # Fallback for future/minified bundle layouts where names are changed but
    # the installed-app OAuth client literals remain in the bundle.
    id_match = _GOOGLE_CLIENT_ID_RE.search(text)
    secret_match = _GOOGLE_CLIENT_SECRET_RE.search(text)
    if id_match and secret_match:
        return _OAuthClient(id_match.group(1).strip(), secret_match.group(1).strip())
    return None


def _gemini_cli_bundle_candidate_files() -> list[Path]:
    files: list[Path] = []
    seen: set[Path] = set()

    def add_file(path: Path) -> None:
        try:
            resolved = path.resolve()
        except OSError:
            resolved = path
        if resolved in seen or not path.is_file():
            return
        seen.add(resolved)
        files.append(path)

    def add_dir(path: Path) -> None:
        if not path.is_dir():
            return
        for name in ("gemini.js", "index.js"):
            add_file(path / name)
        for candidate in sorted(path.glob("chunk-*.js")):
            add_file(candidate)
        for candidate in sorted(path.glob("*.js"))[:40]:
            add_file(candidate)

    command = find_gemini_cli()
    if command:
        command_path = Path(command)
        command_dir = command_path.parent
        add_dir(command_dir / "node_modules" / "@google" / "gemini-cli" / "bundle")
        add_dir(command_dir / "node_modules" / "@google" / "gemini-cli" / "dist")
        add_dir(command_dir.parent / "lib" / "node_modules" / "@google" / "gemini-cli" / "bundle")
        add_dir(command_dir.parent / "lib" / "node_modules" / "@google" / "gemini-cli" / "dist")
        try:
            resolved = command_path.resolve()
        except OSError:
            resolved = command_path
        if resolved.suffix.lower() == ".js":
            add_file(resolved)
            add_dir(resolved.parent)

    if os.name == "nt":
        appdata = os.environ.get("APPDATA", "").strip()
        if appdata:
            root = Path(appdata) / "npm" / "node_modules" / "@google" / "gemini-cli"
            add_dir(root / "bundle")
            add_dir(root / "dist")
    return files


def _try_run_code_assist_prompt(
    prompt: str,
    *,
    model: Optional[str],
    proxy_url: Optional[str],
    timeout_seconds: int,
) -> Optional[_GeminiCliRunResult]:
    """Run a prompt directly against Gemini Code Assist using CLI OAuth.

    This avoids invoking ``gemini --prompt``. The CLI command is a coding
    agent with its own project/tool system prompt; direct Code Assist calls are
    plain text generation and therefore a better fit for Writer.
    """
    access_token = _refresh_gemini_cli_access_token(proxy_url=proxy_url)
    if not access_token:
        return None
    load_res = _load_code_assist(
        access_token=access_token,
        proxy_url=proxy_url,
        timeout_seconds=timeout_seconds,
    )
    project_id = load_res.get("cloudaicompanionProject")
    if not isinstance(project_id, str) or not project_id.strip():
        raise AiError(
            "Gemini OAuth is present, but Gemini Code Assist has no project "
            "for this account yet. Open Gemini CLI once in a terminal and "
            "finish any onboarding/validation prompt, then retry Writer."
        )
    request_body = {
        "model": model or _CODE_ASSIST_DEFAULT_MODEL,
        "project": project_id.strip(),
        "user_prompt_id": str(uuid.uuid4()),
        "request": {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {"temperature": 0.7},
            "session_id": str(uuid.uuid4()),
        },
    }
    gen_res = _post_code_assist_json(
        "generateContent",
        request_body,
        access_token=access_token,
        proxy_url=proxy_url,
        timeout_seconds=timeout_seconds,
    )
    text = _extract_code_assist_text(gen_res)
    if not text:
        raise AiError("Gemini Code Assist returned no text output.")
    usage = _extract_code_assist_usage(gen_res)
    return _GeminiCliRunResult(
        text=text,
        model=_extract_code_assist_model(gen_res) or model or _CODE_ASSIST_DEFAULT_MODEL,
        input_tokens=usage[0],
        output_tokens=usage[1],
    )


def _load_code_assist(
    *,
    access_token: str,
    proxy_url: Optional[str],
    timeout_seconds: int,
) -> dict[str, Any]:
    return _post_code_assist_json(
        "loadCodeAssist",
        {
            "metadata": {
                "ideType": "IDE_UNSPECIFIED",
                "platform": "PLATFORM_UNSPECIFIED",
                "pluginType": "GEMINI",
            }
        },
        access_token=access_token,
        proxy_url=proxy_url,
        timeout_seconds=timeout_seconds,
    )


def _post_code_assist_json(
    method: str,
    body: dict[str, Any],
    *,
    access_token: str,
    proxy_url: Optional[str],
    timeout_seconds: int,
) -> dict[str, Any]:
    url = f"{_CODE_ASSIST_ENDPOINT}/{_CODE_ASSIST_API_VERSION}:{method}"
    opener = (
        urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url})
        )
        if proxy_url
        else urllib.request.build_opener()
    )
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        },
        method="POST",
    )
    try:
        with opener.open(req, timeout=timeout_seconds) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise AiError(
            f"Gemini Code Assist request failed: {_extract_http_error(exc)}"
        ) from exc
    except urllib.error.URLError as exc:
        raise AiError(f"Gemini Code Assist request failed: {exc.reason}") from exc
    except TimeoutError as exc:
        raise AiError(
            f"Gemini Code Assist timed out after {timeout_seconds} seconds."
        ) from exc
    except OSError as exc:
        raise AiError(f"Gemini Code Assist request failed: {exc}") from exc
    try:
        parsed = json.loads(raw) if raw else {}
    except json.JSONDecodeError as exc:
        raise AiError(f"Gemini Code Assist returned invalid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise AiError("Gemini Code Assist response JSON was not an object.")
    return parsed


def _extract_http_error(exc: urllib.error.HTTPError) -> str:
    try:
        raw = exc.read().decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        raw = ""
    if raw:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return raw.strip() or f"HTTP {exc.code}"
        error_obj = parsed.get("error") if isinstance(parsed, dict) else None
        if isinstance(error_obj, dict) and isinstance(error_obj.get("message"), str):
            return error_obj["message"]
        return raw.strip()
    return f"HTTP {exc.code}"


def _extract_code_assist_text(data: dict[str, Any]) -> str:
    response = data.get("response")
    if not isinstance(response, dict):
        return ""
    candidates = response.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return ""
    first = candidates[0]
    if not isinstance(first, dict):
        return ""
    content = first.get("content")
    if not isinstance(content, dict):
        return ""
    parts = content.get("parts")
    if not isinstance(parts, list):
        return ""
    out: list[str] = []
    for part in parts:
        if isinstance(part, dict) and isinstance(part.get("text"), str):
            out.append(part["text"])
    return "".join(out).strip()


def _extract_code_assist_model(data: dict[str, Any]) -> Optional[str]:
    response = data.get("response")
    if not isinstance(response, dict):
        return None
    value = response.get("modelVersion")
    return value.strip() if isinstance(value, str) and value.strip() else None


def _extract_code_assist_usage(data: dict[str, Any]) -> tuple[Optional[int], Optional[int]]:
    response = data.get("response")
    if not isinstance(response, dict):
        return None, None
    usage = response.get("usageMetadata")
    if not isinstance(usage, dict):
        return None, None
    prompt = usage.get("promptTokenCount")
    candidates = usage.get("candidatesTokenCount")
    return (
        prompt if isinstance(prompt, int) else None,
        candidates if isinstance(candidates, int) else None,
    )


def _quota_status_from_load_response(
    data: dict[str, Any], *, account: Optional[str]
) -> GeminiCliQuotaStatus:
    current_tier = _tier_name(data.get("currentTier"))
    paid_tier_obj = data.get("paidTier")
    paid_tier = _tier_name(paid_tier_obj)
    project_id = data.get("cloudaicompanionProject")
    manage_uri = data.get("manageSubscriptionUri")
    credits = _credits_summary(paid_tier_obj)
    if not credits:
        credits = "included / not itemized"
    return GeminiCliQuotaStatus(
        True,
        account=account,
        project_id=project_id if isinstance(project_id, str) else None,
        current_tier=current_tier,
        paid_tier=paid_tier,
        credits=credits,
        manage_subscription_uri=manage_uri if isinstance(manage_uri, str) else None,
    )


def _tier_name(value: Any) -> Optional[str]:
    if not isinstance(value, dict):
        return None
    name = value.get("name")
    tier_id = value.get("id")
    if isinstance(name, str) and name.strip():
        return name.strip()
    if isinstance(tier_id, str) and tier_id.strip():
        return tier_id.strip()
    return None


def _credits_summary(value: Any) -> Optional[str]:
    if not isinstance(value, dict):
        return None
    credits = value.get("availableCredits")
    if not isinstance(credits, list) or not credits:
        return None
    parts: list[str] = []
    for item in credits:
        if not isinstance(item, dict):
            continue
        credit_type = item.get("creditType") or item.get("type") or "credit"
        amount = item.get("creditAmount") or item.get("amount")
        if amount is None:
            continue
        parts.append(f"{credit_type}: {amount}")
    return ", ".join(parts) or None


def _read_gemini_cli_account_email() -> Optional[str]:
    path = Path.home() / ".gemini" / "google_accounts.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    for key in ("active", "activeAccount"):
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _apply_gemini_cli_proxy_env(
    env: dict[str, str], configured_proxy: Optional[str]
) -> Optional[str]:
    proxy_url = _normalise_proxy_url(configured_proxy) if configured_proxy else None
    if not proxy_url:
        proxy_url = detect_gemini_cli_proxy(env)
    if not proxy_url:
        return None
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
        env[key] = proxy_url
    for key in ("http_proxy", "https_proxy", "all_proxy"):
        env.setdefault(key, proxy_url)
    env.setdefault("NO_PROXY", "localhost,127.0.0.1")
    env.setdefault("no_proxy", env["NO_PROXY"])
    env[GEMINI_CLI_PROXY_ENV] = proxy_url
    return proxy_url


def _first_proxy_from_env(env: dict[str, str]) -> Optional[str]:
    for key in _PROXY_ENV_KEYS:
        value = env.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _normalise_proxy_url(value: Optional[str]) -> Optional[str]:
    raw = (value or "").strip().strip('"').strip("'")
    if not raw:
        return None
    if ";" in raw and "=" in raw:
        raw = _proxy_from_windows_proxy_server(raw) or raw
    if "://" not in raw:
        raw = "http://" + raw
    return raw.rstrip("/")


def _windows_system_proxy_url() -> Optional[str]:
    if os.name != "nt":
        return None
    try:
        import winreg  # type: ignore[import-not-found]

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
        ) as key:
            enabled, _ = winreg.QueryValueEx(key, "ProxyEnable")
            if not int(enabled):
                return None
            raw, _ = winreg.QueryValueEx(key, "ProxyServer")
    except Exception:  # noqa: BLE001
        return None
    return _proxy_from_windows_proxy_server(str(raw))


def _proxy_from_windows_proxy_server(raw: str) -> Optional[str]:
    value = (raw or "").strip()
    if not value:
        return None
    if ";" not in value and "=" not in value:
        return _normalise_proxy_url(value)
    parts: dict[str, str] = {}
    for chunk in value.split(";"):
        if "=" not in chunk:
            continue
        key, item = chunk.split("=", 1)
        if key.strip() and item.strip():
            parts[key.strip().lower()] = item.strip()
    return _normalise_proxy_url(parts.get("https") or parts.get("http"))


def _command_prefix(command: str) -> List[str]:
    if command.lower().endswith(".ps1"):
        return ["powershell", "-ExecutionPolicy", "Bypass", "-File", command]
    return [command]


def _resolve_timeout_seconds(explicit: Optional[int]) -> int:
    if explicit is not None:
        return max(1, int(explicit))
    raw = os.environ.get(GEMINI_CLI_TIMEOUT_ENV, "").strip()
    if raw:
        try:
            return max(1, int(raw))
        except ValueError:
            pass
    return GEMINI_CLI_DEFAULT_TIMEOUT_SECONDS


def _run_subprocess_tree(
    cmd: List[str],
    *,
    timeout_seconds: int,
    env: dict[str, str],
) -> subprocess.CompletedProcess:
    creationflags = 0
    if os.name == "nt":
        creationflags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        # Writer is packaged as a GUI app. Without CREATE_NO_WINDOW, running
        # gemini.cmd can briefly show a black console window; if Gemini CLI
        # asks for OAuth consent there, the app appears to hang behind it.
        creationflags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        creationflags=creationflags,
    )
    try:
        stdout, stderr = proc.communicate(input="", timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        _kill_process_tree(proc.pid)
        try:
            proc.communicate(timeout=5)
        except Exception:  # noqa: BLE001
            pass
        raise
    return subprocess.CompletedProcess(
        cmd, proc.returncode, stdout=stdout, stderr=stderr
    )


def _kill_process_tree(pid: int) -> None:
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            return
        except Exception:  # noqa: BLE001
            pass
    try:
        os.kill(pid, 9)
    except Exception:  # noqa: BLE001
        pass


def _looks_like_auth_prompt(text: str) -> bool:
    return any(marker in (text or "") for marker in _AUTH_PROMPT_MARKERS)


def _has_non_auth_output(text: str) -> bool:
    cleaned = _clean_output(text)
    return bool(cleaned.strip()) and not _looks_like_auth_prompt(cleaned)


def _auth_prompt_message() -> str:
    return (
        "Gemini CLI is asking for OAuth authentication, so Writer cannot use "
        "it headlessly yet. In a normal terminal, run `set NO_BROWSER=true`, "
        "then run `gemini`, use `/auth`, open the printed URL manually, and "
        "paste the authorization code back into Gemini CLI. After that, verify "
        "`gemini --skip-trust --prompt \"Reply with exactly: pong\"` works "
        "before retrying Writer."
    )


def _messages_to_prompt(messages: List[dict]) -> str:
    parts: List[str] = []
    for message in messages:
        role = str(message.get("role") or "user").strip().lower()
        text = _message_text(message.get("content"))
        if not text:
            continue
        label = {
            "system": "System",
            "assistant": "Assistant",
            "model": "Assistant",
            "user": "User",
        }.get(role, role.title())
        parts.append(f"{label}:\n{text}")
    return "\n\n".join(parts).strip()


def _message_text(content) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, dict) and isinstance(content.get("text"), str):
        return content["text"].strip()
    if isinstance(content, list):
        out: List[str] = []
        for item in content:
            if isinstance(item, str):
                out.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                out.append(item["text"])
        return "\n".join(part for part in out if part).strip()
    return ""


def _clean_output(text: str) -> str:
    text = _ANSI_RE.sub("", text or "")
    lines = []
    for line in text.replace("\r\n", "\n").split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if any(stripped.startswith(prefix) for prefix in _NOISE_PREFIXES):
            continue
        if any(marker in stripped for marker in _AUTH_PROMPT_MARKERS):
            continue
        lines.append(line.rstrip())
    return "\n".join(lines).strip()
