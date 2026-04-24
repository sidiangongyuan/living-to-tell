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

KEY_LANGUAGE = "ui.language"
DEFAULT_LANGUAGE = "en"

KEY_SPLITTER_SIZES = "ui.splitter_sizes"
KEY_SIDEBAR_COLLAPSED = "ui.sidebar_collapsed"

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

    # ------------------------------------------------------------------
    def load_ai_config(self) -> AiConfig:
        """Build an :class:`AiConfig` from persisted settings, with defaults."""
        defaults = AiConfig()
        return AiConfig(
            provider_name=defaults.provider_name,
            base_url=self._repo.get(KEY_AI_BASE_URL) or defaults.base_url,
            wire_api=self._repo.get(KEY_AI_WIRE_API) or defaults.wire_api,
            model=self._repo.get(KEY_AI_MODEL) or defaults.model,
            api_key_source=self._repo.get(KEY_AI_API_KEY_SOURCE) or defaults.api_key_source,
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
        self._repo.set(KEY_AI_WIRE_API, wire_api)
        self._repo.set(KEY_AI_MODEL, config.model)
        self._repo.set(KEY_AI_API_KEY_SOURCE, config.api_key_source)

    # ------------------------------------------------------------------
    @property
    def language(self) -> str:
        return self._repo.get(KEY_LANGUAGE, DEFAULT_LANGUAGE) or DEFAULT_LANGUAGE

    def save_language(self, locale: str) -> None:
        if locale not in SUPPORTED_LOCALES:
            raise ValueError(f"Unsupported language: {locale!r}")
        self._repo.set(KEY_LANGUAGE, locale)
