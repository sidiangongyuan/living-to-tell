"""High-level settings facade.

Wraps :class:`writer.storage.repositories.settings_repository.SettingsRepository`
and exposes the typed setting keys the rest of the app cares about. UI code
should depend on this facade, not on the repository directly.

Milestone 1 only needs a tiny surface; real getters/setters for AI provider
configuration will land alongside the settings dialog in a later milestone.
"""
from __future__ import annotations

from typing import Optional

from writer.app.locale import SUPPORTED_LOCALES
from writer.domain.models.ai_config import AiConfig
from writer.storage.repositories.settings_repository import SettingsRepository


KEY_AI_BASE_URL = "ai.base_url"
KEY_AI_MODEL = "ai.model"
KEY_AI_API_KEY_SOURCE = "ai.api_key_source"
KEY_AI_WIRE_API = "ai.wire_api"
KEY_AI_PROVIDER = "ai.provider"
KEY_AI_GEMINI_CLI_PROXY = "ai.gemini_cli_proxy"

DEFAULT_GEMINI_CLI_MODEL = "gemini-cli-default"
OPENAI_DEFAULT_MODELS = ("gpt-4o-mini",)

RUNTIME_AUTH_SOURCES = ("codex", "gemini", "gemini-cli")
SUPPORTED_AI_PROVIDERS = ("openai", "gemini", "gemini_cli")

KEY_LANGUAGE = "ui.language"
DEFAULT_LANGUAGE = "en"

KEY_SPLITTER_SIZES = "ui.splitter_sizes"
KEY_SIDEBAR_COLLAPSED = "ui.sidebar_collapsed"

# M9A — visual shell upgrade
KEY_THEME_MODE = "ui.theme_mode"
KEY_CONTEXT_PANE_VISIBLE = "ui.context_pane_visible"
KEY_ACTIVE_MODE = "ui.active_mode"
DEFAULT_THEME_MODE = "system"

# Quick capture / tray
KEY_QUICK_CAPTURE_CLOSE_TO_TRAY_ENABLED = "quick_capture.close_to_tray_enabled"
KEY_QUICK_CAPTURE_GLOBAL_HOTKEY = "quick_capture.global_hotkey"
KEY_QUICK_CAPTURE_MAIN_WINDOW_HOTKEY = "quick_capture.main_window_hotkey"
KEY_QUICK_CAPTURE_LAST_ENTRY_ID = "quick_capture.last_entry_id"
DEFAULT_QUICK_CAPTURE_CLOSE_TO_TRAY_ENABLED = True
DEFAULT_QUICK_CAPTURE_GLOBAL_HOTKEY = "Ctrl+Alt+W"
DEFAULT_QUICK_CAPTURE_MAIN_WINDOW_HOTKEY = "Ctrl+Alt+M"

SUPPORTED_WIRE_APIS = ("responses",)
DEFAULT_WIRE_API = "responses"


class Settings:
    """Thin typed facade over the settings repository."""

    def __init__(self, repository: SettingsRepository) -> None:
        self._repo = repository

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return self._repo.get(key, default)

    def set(self, key: str, value: str) -> None:
        self._repo.set(key, value)

    @property
    def ai_base_url(self) -> Optional[str]:
        return self._repo.get(KEY_AI_BASE_URL)

    @property
    def ai_model(self) -> Optional[str]:
        return self._repo.get(KEY_AI_MODEL)

    @property
    def ai_api_key_source(self) -> Optional[str]:
        return self._repo.get(KEY_AI_API_KEY_SOURCE)

    @property
    def ai_wire_api(self) -> Optional[str]:
        return self._repo.get(KEY_AI_WIRE_API)

    @property
    def ai_provider(self) -> Optional[str]:
        return self._repo.get(KEY_AI_PROVIDER)

    @property
    def ai_gemini_cli_proxy(self) -> Optional[str]:
        return self._repo.get(KEY_AI_GEMINI_CLI_PROXY)

    # ------------------------------------------------------------------
    def load_ai_config(self) -> AiConfig:
        """Build an :class:`AiConfig` from persisted settings, with defaults."""
        defaults = AiConfig()
        provider_name = _normalize_provider_name(
            self._repo.get(KEY_AI_PROVIDER),
            api_key_source=self._repo.get(KEY_AI_API_KEY_SOURCE),
            default=defaults.provider_name,
        )
        model = self._repo.get(KEY_AI_MODEL) or defaults.model
        if provider_name == "gemini_cli" and model.strip().lower() in OPENAI_DEFAULT_MODELS:
            model = DEFAULT_GEMINI_CLI_MODEL
        return AiConfig(
            provider_name=provider_name,
            base_url=self._repo.get(KEY_AI_BASE_URL) or defaults.base_url,
            wire_api=self._repo.get(KEY_AI_WIRE_API) or defaults.wire_api,
            model=model,
            api_key_source=self._repo.get(KEY_AI_API_KEY_SOURCE) or defaults.api_key_source,
            gemini_cli_proxy=self._repo.get(KEY_AI_GEMINI_CLI_PROXY) or None,
        )

    def save_ai_config(self, config: AiConfig) -> None:
        # Fix 1: empty/None base_url deletes the stored override so we fall
        # back to the SDK default endpoint instead of a stale custom URL.
        if config.base_url is None or not config.base_url.strip():
            self._repo.delete(KEY_AI_BASE_URL)
        else:
            self._repo.set(KEY_AI_BASE_URL, config.base_url.strip())

        # Fix 3: refuse to persist a wire_api the app cannot actually speak.
        wire_api = (config.wire_api or "").strip().lower()
        if wire_api not in SUPPORTED_WIRE_APIS:
            raise ValueError(
                f"Unsupported wire_api '{config.wire_api}'. "
                f"Supported values: {SUPPORTED_WIRE_APIS}."
            )

        # M7B: reject legacy literal:<key> syntax. API keys are *never*
        # stored on disk — only the name of the env var that holds one,
        # or the sentinel "codex" meaning "read ~/.codex/auth.json".
        api_key_source = (config.api_key_source or "").strip()
        if api_key_source.startswith("literal:"):
            raise ValueError(
                "literal:<key> is not supported. The API key is never stored "
                "on disk — set api_key_source to env:VARNAME (and export the "
                "key in your shell), or to 'codex' to reuse ~/.codex/auth.json."
            )
        if (
            api_key_source
            and api_key_source.lower() not in RUNTIME_AUTH_SOURCES
            and not api_key_source.startswith("env:")
        ):
            raise ValueError(
                "api_key_source must be either env:VARNAME "
                "(for example env:OPENAI_API_KEY), the literal string "
                "'codex' (to reuse ~/.codex/auth.json), 'gemini' "
                "(to reuse ~/.gemini/.env), or 'gemini-cli' "
                "(to reuse Gemini CLI OAuth)."
            )

        provider_name = _normalize_provider_name(
            config.provider_name,
            api_key_source=config.api_key_source,
            default=AiConfig().provider_name,
        )
        if provider_name not in SUPPORTED_AI_PROVIDERS:
            raise ValueError(
                f"provider_name must be one of {SUPPORTED_AI_PROVIDERS}."
            )

        self._repo.set(KEY_AI_PROVIDER, provider_name)
        self._repo.set(KEY_AI_WIRE_API, wire_api)
        self._repo.set(KEY_AI_MODEL, config.model)
        self._repo.set(KEY_AI_API_KEY_SOURCE, config.api_key_source)
        proxy = (config.gemini_cli_proxy or "").strip()
        if proxy:
            self._repo.set(KEY_AI_GEMINI_CLI_PROXY, proxy)
        else:
            self._repo.delete(KEY_AI_GEMINI_CLI_PROXY)

    # ------------------------------------------------------------------
    @property
    def language(self) -> str:
        return self._repo.get(KEY_LANGUAGE, DEFAULT_LANGUAGE) or DEFAULT_LANGUAGE

    def save_language(self, locale: str) -> None:
        if locale not in SUPPORTED_LOCALES:
            raise ValueError(f"Unsupported language: {locale!r}")
        self._repo.set(KEY_LANGUAGE, locale)


def _normalize_provider_name(
    provider_name: Optional[str],
    *,
    api_key_source: Optional[str],
    default: str,
) -> str:
    raw = (provider_name or "").strip().lower()
    if raw in SUPPORTED_AI_PROVIDERS:
        return raw
    source = (api_key_source or "").strip().lower()
    if source == "gemini-cli":
        return "gemini_cli"
    if source == "gemini":
        return "gemini"
    return default
