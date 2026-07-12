"""High-level settings facade.

Wraps :class:`writer.storage.repositories.settings_repository.SettingsRepository`
and exposes the typed setting keys the rest of the app cares about. UI code
should depend on this facade, not on the repository directly.

Milestone 1 only needs a tiny surface; real getters/setters for AI provider
configuration will land alongside the settings dialog in a later milestone.
"""
from __future__ import annotations

import json
import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from writer.app.locale import SUPPORTED_LOCALES
from writer.domain.models.ai_config import AiConfig
from writer.storage.repositories.settings_repository import SettingsRepository


KEY_AI_BASE_URL = "ai.base_url"
KEY_AI_MODEL = "ai.model"
KEY_AI_API_KEY_SOURCE = "ai.api_key_source"
KEY_AI_WIRE_API = "ai.wire_api"
KEY_AI_PROVIDER = "ai.provider"
KEY_AI_GEMINI_CLI_PROXY = "ai.gemini_cli_proxy"
KEY_AI_CUSTOM_TASK_PRESETS = "ai.custom_task_presets"
KEY_AI_PROVIDER_PROFILES = "ai.provider_profiles.v1"
KEY_AI_DEFAULT_PROFILE_ID = "ai.default_profile_id.v1"
KEY_AI_PROFILE_HEALTH = "ai.profile_health.v1"
KEY_AI_PROFILE_MIGRATED = "ai.profile_defaults_migrated.v1"

DEFAULT_GEMINI_CLI_MODEL = "gemini-cli-default"
DEFAULT_OPENCODE_MODEL = "opencode/deepseek-v4-flash-free"
OPENAI_DEFAULT_MODELS = ("gpt-4o-mini",)

RUNTIME_AUTH_SOURCES = ("codex", "gemini", "gemini-cli", "opencode")
SUPPORTED_AI_PROVIDERS = ("openai", "gemini", "gemini_cli", "opencode")

KEY_LANGUAGE = "ui.language"
DEFAULT_LANGUAGE = "en"

KEY_SPLITTER_SIZES = "ui.splitter_sizes"
KEY_SIDEBAR_COLLAPSED = "ui.sidebar_collapsed"
KEY_REFERENCE_LIBRARY_DEFAULT_GROUP_MODE = "reference_library.default_group_mode"
KEY_REFERENCE_LIBRARY_STATS_COLLAPSED = "reference_library.stats_collapsed"
KEY_REFERENCE_LIBRARY_SHELF_COLLAPSED = "reference_library.shelf_collapsed"
KEY_REFERENCE_LIBRARY_EDITOR_DRAWER_VISIBLE = (
    "reference_library.editor_drawer_visible"
)
KEY_REFERENCE_LIBRARY_SPLITTER_SIZES = "reference_library.splitter_sizes"
KEY_SPECIMEN_PICKER_DEFAULT_GROUP_MODE = "specimen_picker.default_group_mode"
DEFAULT_REFERENCE_LIBRARY_GROUP_MODE = "source"
DEFAULT_REFERENCE_LIBRARY_STATS_COLLAPSED = True
DEFAULT_REFERENCE_LIBRARY_SHELF_COLLAPSED = False
DEFAULT_REFERENCE_LIBRARY_EDITOR_DRAWER_VISIBLE = False
DEFAULT_SPECIMEN_PICKER_GROUP_MODE = "source_usage"

# M9A — visual shell upgrade
KEY_THEME_MODE = "ui.theme_mode"
KEY_CONTEXT_PANE_VISIBLE = "ui.context_pane_visible"
KEY_ACTIVE_MODE = "ui.active_mode"
DEFAULT_THEME_MODE = "system"

# Editor comfort / writing layout
KEY_EDITOR_FONT_SIZE = "editor.font_size"
KEY_EDITOR_LINE_HEIGHT = "editor.line_height"
KEY_EDITOR_PARAGRAPH_SPACING = "editor.paragraph_spacing"
KEY_EDITOR_CONTENT_WIDTH = "editor.content_width"
KEY_EDITOR_PAGE_VERTICAL_PADDING = "editor.page_vertical_padding"
KEY_EDITOR_PAGE_GAP = "editor.page_gap"
KEY_EDITOR_FONT_FAMILY = "editor.font_family"
KEY_EDITOR_VISUAL_FIRST_LINE_INDENT_ENABLED = (
    "editor.visual_first_line_indent_enabled"
)
KEY_EDITOR_TYPEWRITER_MODE_ENABLED = "editor.typewriter_mode_enabled"
KEY_EDITOR_AUTO_PARAGRAPH_INDENT_ENABLED = "editor.auto_paragraph_indent_enabled"
KEY_EDITOR_SOFT_PAGE_GUIDES_ENABLED = "editor.soft_page_guides_enabled"
KEY_EDITOR_WRITING_NOTES_CARD_COLLAPSED_BY_DEFAULT = (
    "editor.writing_notes_card_collapsed_by_default"
)
KEY_REDUCED_MOTION_ENABLED = "ui.reduced_motion_enabled"
DEFAULT_EDITOR_FONT_SIZE = 18
DEFAULT_EDITOR_LINE_HEIGHT = 1.8
DEFAULT_EDITOR_PARAGRAPH_SPACING = 0.8
DEFAULT_EDITOR_CONTENT_WIDTH = 1000
DEFAULT_EDITOR_PAGE_VERTICAL_PADDING = 28
DEFAULT_EDITOR_PAGE_GAP = 34
MAX_EDITOR_CONTENT_WIDTH = 1600
DEFAULT_EDITOR_FONT_FAMILY = (
    "Noto Serif SC, Source Han Serif SC, Songti SC, 华文宋体, 宋体, Georgia, Cambria"
)
DEFAULT_EDITOR_VISUAL_FIRST_LINE_INDENT_ENABLED = True
DEFAULT_EDITOR_TYPEWRITER_MODE_ENABLED = True
DEFAULT_EDITOR_AUTO_PARAGRAPH_INDENT_ENABLED = True
DEFAULT_EDITOR_SOFT_PAGE_GUIDES_ENABLED = True
DEFAULT_EDITOR_WRITING_NOTES_CARD_COLLAPSED_BY_DEFAULT = True
DEFAULT_REDUCED_MOTION_ENABLED = False

# Quick capture / tray
KEY_QUICK_CAPTURE_CLOSE_TO_TRAY_ENABLED = "quick_capture.close_to_tray_enabled"
KEY_QUICK_CAPTURE_GLOBAL_HOTKEY = "quick_capture.global_hotkey"
KEY_QUICK_CAPTURE_MAIN_WINDOW_HOTKEY = "quick_capture.main_window_hotkey"
KEY_QUICK_CAPTURE_LAST_ENTRY_ID = "quick_capture.last_entry_id"
DEFAULT_QUICK_CAPTURE_CLOSE_TO_TRAY_ENABLED = True
LEGACY_QUICK_CAPTURE_GLOBAL_HOTKEY = "Ctrl+Alt+W"
DEFAULT_QUICK_CAPTURE_GLOBAL_HOTKEY = "Ctrl+Alt+`"
DEFAULT_QUICK_CAPTURE_MAIN_WINDOW_HOTKEY = "Ctrl+Alt+M"

SUPPORTED_WIRE_APIS = ("responses", "chat_completions")
DEFAULT_WIRE_API = "responses"


@dataclass(frozen=True)
class EditorDisplaySettings:
    font_size: int = DEFAULT_EDITOR_FONT_SIZE
    line_height: float = DEFAULT_EDITOR_LINE_HEIGHT
    paragraph_spacing: float = DEFAULT_EDITOR_PARAGRAPH_SPACING
    content_width: int = DEFAULT_EDITOR_CONTENT_WIDTH
    page_vertical_padding: int = DEFAULT_EDITOR_PAGE_VERTICAL_PADDING
    page_gap: int = DEFAULT_EDITOR_PAGE_GAP
    font_family: str = DEFAULT_EDITOR_FONT_FAMILY
    visual_first_line_indent_enabled: bool = (
        DEFAULT_EDITOR_VISUAL_FIRST_LINE_INDENT_ENABLED
    )
    typewriter_mode_enabled: bool = DEFAULT_EDITOR_TYPEWRITER_MODE_ENABLED
    auto_paragraph_indent_enabled: bool = DEFAULT_EDITOR_AUTO_PARAGRAPH_INDENT_ENABLED
    soft_page_guides_enabled: bool = DEFAULT_EDITOR_SOFT_PAGE_GUIDES_ENABLED


DEFAULT_EDITOR_DISPLAY_SETTINGS = EditorDisplaySettings()


class Settings:
    """Thin typed facade over the settings repository."""

    def __init__(self, repository: SettingsRepository) -> None:
        self._repo = repository

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return self._repo.get(key, default)

    def set(self, key: str, value: str) -> None:
        self._repo.set(key, value)

    def delete(self, key: str) -> None:
        self._repo.delete(key)

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
        if provider_name == "opencode" and (
            not model.strip()
            or model.strip().lower() in {"default", "auto", *OPENAI_DEFAULT_MODELS}
        ):
            model = DEFAULT_OPENCODE_MODEL
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

        # M7B: reject legacy literal:<key> syntax. Inline API keys are never
        # stored in the app settings database. The UI may save a key to a
        # user environment variable, but this setting still stores only the
        # resulting env:VARNAME source.
        api_key_source = (config.api_key_source or "").strip()
        if api_key_source.startswith("literal:"):
            raise ValueError(
                "literal:<key> is not supported. The API key is never stored "
                "inline in app settings — set api_key_source to env:VARNAME "
                "(and export the key in your shell or save it from Settings), "
                "or to 'codex' to reuse ~/.codex/auth.json."
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
                "(to reuse Gemini CLI OAuth), or 'opencode' "
                "(to reuse OpenCode CLI local auth)."
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

    def load_ai_provider_profiles(self) -> list[dict[str, Any]]:
        raw = self._repo.get(KEY_AI_PROVIDER_PROFILES)
        if not raw:
            return []
        try:
            data = json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            return []
        if not isinstance(data, list):
            return []
        return [item for item in data if isinstance(item, dict)]

    def save_ai_provider_profiles(self, profiles: list[dict[str, Any]]) -> None:
        if not profiles:
            self._repo.delete(KEY_AI_PROVIDER_PROFILES)
            return
        self._repo.set(
            KEY_AI_PROVIDER_PROFILES,
            json.dumps(profiles, ensure_ascii=False, sort_keys=True),
        )

    def load_ai_default_profile_id(self) -> Optional[str]:
        value = (self._repo.get(KEY_AI_DEFAULT_PROFILE_ID) or "").strip()
        return value or None

    def save_ai_default_profile_id(self, profile_id: Optional[str]) -> None:
        value = (profile_id or "").strip()
        if value:
            self._repo.set(KEY_AI_DEFAULT_PROFILE_ID, value)
        else:
            self._repo.delete(KEY_AI_DEFAULT_PROFILE_ID)

    def load_ai_profile_health(self) -> dict[str, dict[str, Any]]:
        raw = self._repo.get(KEY_AI_PROFILE_HEALTH)
        if not raw:
            return {}
        try:
            data = json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}
        if not isinstance(data, dict):
            return {}
        return {
            str(profile_id): value
            for profile_id, value in data.items()
            if isinstance(value, dict)
        }

    def save_ai_profile_health(self, health: dict[str, dict[str, Any]]) -> None:
        cleaned = {
            str(profile_id): value
            for profile_id, value in health.items()
            if str(profile_id).strip() and isinstance(value, dict)
        }
        if not cleaned:
            self._repo.delete(KEY_AI_PROFILE_HEALTH)
            return
        self._repo.set(
            KEY_AI_PROFILE_HEALTH,
            json.dumps(cleaned, ensure_ascii=False, sort_keys=True),
        )

    @staticmethod
    def ai_profile_fingerprint(profile: dict[str, Any]) -> str:
        payload = {
            "provider_name": str(profile.get("provider_name") or "").strip().lower(),
            "base_url": str(profile.get("base_url") or "").strip().rstrip("/"),
            "wire_api": str(profile.get("wire_api") or "responses").strip().lower(),
            "model": str(profile.get("model") or "").strip(),
            "api_key_source": str(profile.get("api_key_source") or "").strip(),
            "gemini_cli_proxy": str(profile.get("gemini_cli_proxy") or "").strip(),
        }
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def ensure_ai_profile_defaults(self) -> tuple[list[dict[str, Any]], Optional[str]]:
        """Migrate the legacy global AI config to profiles exactly once.

        A fresh install has no explicitly persisted legacy fields, so it stays
        empty. Existing installs either select an exact matching profile or
        receive a lossless ``原默认配置`` profile. The selected profile is then
        mirrored back to the legacy fields for old desktop/backend callers.
        """
        profiles = self.load_ai_provider_profiles()
        default_id = self.load_ai_default_profile_id()
        migrated = self._repo.get(KEY_AI_PROFILE_MIGRATED) == "1"

        default_profile = next(
            (
                item for item in profiles
                if str(item.get("id") or "").strip() == default_id
            ),
            None,
        )
        if default_id and (default_profile is None or not bool(default_profile.get("enabled", True))):
            default_id = None
            self.save_ai_default_profile_id(None)

        if not migrated:
            legacy_keys = (
                KEY_AI_PROVIDER,
                KEY_AI_BASE_URL,
                KEY_AI_WIRE_API,
                KEY_AI_MODEL,
                KEY_AI_API_KEY_SOURCE,
                KEY_AI_GEMINI_CLI_PROXY,
            )
            has_explicit_legacy = any(self._repo.get(key) is not None for key in legacy_keys)
            if has_explicit_legacy:
                legacy = self.load_ai_config()
                legacy_payload = {
                    "provider_name": legacy.provider_key(),
                    "base_url": legacy.base_url,
                    "wire_api": legacy.wire_api,
                    "model": legacy.model,
                    "api_key_source": legacy.api_key_source,
                    "gemini_cli_proxy": legacy.gemini_cli_proxy,
                }
                legacy_fingerprint = self.ai_profile_fingerprint(legacy_payload)
                match = next(
                    (
                        item for item in profiles
                        if self.ai_profile_fingerprint(item) == legacy_fingerprint
                    ),
                    None,
                )
                if match is None:
                    now = datetime.now(timezone.utc).isoformat()
                    match = {
                        "id": uuid.uuid4().hex,
                        "name": "原默认配置",
                        **legacy_payload,
                        "enabled": True,
                        "source_key": None,
                        "created_at": now,
                        "updated_at": now,
                    }
                    profiles.append(match)
                    self.save_ai_provider_profiles(profiles)
                elif not bool(match.get("enabled", True)):
                    match["enabled"] = True
                    match["updated_at"] = datetime.now(timezone.utc).isoformat()
                    self.save_ai_provider_profiles(profiles)
                default_id = str(match.get("id") or "").strip() or None
            elif profiles:
                first_enabled = next(
                    (item for item in profiles if bool(item.get("enabled", True))),
                    None,
                )
                default_id = (
                    str(first_enabled.get("id") or "").strip() or None
                    if first_enabled is not None
                    else None
                )

            self.save_ai_default_profile_id(default_id)
            self._repo.set(KEY_AI_PROFILE_MIGRATED, "1")

        if not default_id:
            first_enabled = next(
                (item for item in profiles if bool(item.get("enabled", True))),
                None,
            )
            if first_enabled is not None:
                default_id = str(first_enabled.get("id") or "").strip() or None
                self.save_ai_default_profile_id(default_id)

        if default_id:
            selected = next(
                (item for item in profiles if str(item.get("id") or "").strip() == default_id),
                None,
            )
            if selected is not None:
                try:
                    self.save_ai_config(
                        AiConfig(
                            provider_name=str(selected.get("provider_name") or "openai"),
                            base_url=str(selected.get("base_url") or "").strip() or None,
                            wire_api=str(selected.get("wire_api") or "responses"),
                            model=str(selected.get("model") or "").strip(),
                            api_key_source=str(selected.get("api_key_source") or "").strip(),
                            gemini_cli_proxy=str(selected.get("gemini_cli_proxy") or "").strip() or None,
                        )
                    )
                except ValueError:
                    # Invalid historical profiles remain visible for repair;
                    # never guess a different protocol or model during migration.
                    pass
        return profiles, default_id

    def load_ai_default_profile(self) -> Optional[dict[str, Any]]:
        profiles, default_id = self.ensure_ai_profile_defaults()
        if not default_id:
            return None
        return next(
            (
                item for item in profiles
                if str(item.get("id") or "").strip() == default_id
                and bool(item.get("enabled", True))
            ),
            None,
        )

    def load_ai_default_profile_config(self) -> Optional[AiConfig]:
        profile = self.load_ai_default_profile()
        if profile is None:
            return None
        provider_name = str(profile.get("provider_name") or "").strip().lower()
        wire_api = str(profile.get("wire_api") or "responses").strip().lower()
        model = str(profile.get("model") or "").strip()
        if (
            provider_name not in SUPPORTED_AI_PROVIDERS
            or wire_api not in SUPPORTED_WIRE_APIS
            or not model
        ):
            return None
        return AiConfig(
            provider_name=provider_name,
            base_url=str(profile.get("base_url") or "").strip() or None,
            wire_api=wire_api,
            model=model,
            api_key_source=str(profile.get("api_key_source") or "").strip(),
            gemini_cli_proxy=str(profile.get("gemini_cli_proxy") or "").strip() or None,
        )

    def load_ai_custom_task_presets(self) -> dict[str, list[str]]:
        raw = self._repo.get(KEY_AI_CUSTOM_TASK_PRESETS)
        if not raw:
            return {}
        try:
            data = json.loads(raw)
        except (TypeError, ValueError):
            return {}
        if not isinstance(data, dict):
            return {}
        cleaned: dict[str, list[str]] = {}
        for task_name, values in data.items():
            if not isinstance(task_name, str) or not isinstance(values, list):
                continue
            seen: set[str] = set()
            presets: list[str] = []
            for raw_value in values:
                if not isinstance(raw_value, str):
                    continue
                value = raw_value.strip()
                if not value:
                    continue
                lowered = value.lower()
                if lowered in seen:
                    continue
                seen.add(lowered)
                presets.append(value)
            if presets:
                cleaned[task_name] = presets
        return cleaned

    def save_ai_custom_task_presets(self, presets: dict[str, list[str]]) -> None:
        cleaned: dict[str, list[str]] = {}
        for task_name, values in presets.items():
            if not isinstance(task_name, str) or not isinstance(values, list):
                continue
            seen: set[str] = set()
            unique_values: list[str] = []
            for raw_value in values:
                if not isinstance(raw_value, str):
                    continue
                value = raw_value.strip()
                if not value:
                    continue
                lowered = value.lower()
                if lowered in seen:
                    continue
                seen.add(lowered)
                unique_values.append(value)
            if unique_values:
                cleaned[task_name] = unique_values
        if not cleaned:
            self._repo.delete(KEY_AI_CUSTOM_TASK_PRESETS)
            return
        self._repo.set(
            KEY_AI_CUSTOM_TASK_PRESETS,
            json.dumps(cleaned, ensure_ascii=False, sort_keys=True),
        )

    # ------------------------------------------------------------------
    @property
    def language(self) -> str:
        return self._repo.get(KEY_LANGUAGE, DEFAULT_LANGUAGE) or DEFAULT_LANGUAGE

    def save_language(self, locale: str) -> None:
        if locale not in SUPPORTED_LOCALES:
            raise ValueError(f"Unsupported language: {locale!r}")
        self._repo.set(KEY_LANGUAGE, locale)

    def load_editor_display_settings(self) -> EditorDisplaySettings:
        return EditorDisplaySettings(
            font_size=_coerce_int(
                self._repo.get(KEY_EDITOR_FONT_SIZE),
                default=DEFAULT_EDITOR_FONT_SIZE,
                minimum=12,
                maximum=32,
            ),
            line_height=_coerce_float(
                self._repo.get(KEY_EDITOR_LINE_HEIGHT),
                default=DEFAULT_EDITOR_LINE_HEIGHT,
                minimum=1.2,
                maximum=2.6,
            ),
            paragraph_spacing=_coerce_float(
                self._repo.get(KEY_EDITOR_PARAGRAPH_SPACING),
                default=DEFAULT_EDITOR_PARAGRAPH_SPACING,
                minimum=0.0,
                maximum=2.0,
            ),
            content_width=_coerce_int(
                self._repo.get(KEY_EDITOR_CONTENT_WIDTH),
                default=DEFAULT_EDITOR_CONTENT_WIDTH,
                minimum=520,
                maximum=MAX_EDITOR_CONTENT_WIDTH,
            ),
            page_vertical_padding=_coerce_int(
                self._repo.get(KEY_EDITOR_PAGE_VERTICAL_PADDING),
                default=DEFAULT_EDITOR_PAGE_VERTICAL_PADDING,
                minimum=12,
                maximum=96,
            ),
            page_gap=_coerce_int(
                self._repo.get(KEY_EDITOR_PAGE_GAP),
                default=DEFAULT_EDITOR_PAGE_GAP,
                minimum=0,
                maximum=96,
            ),
            font_family=_coerce_font_family(
                self._repo.get(KEY_EDITOR_FONT_FAMILY),
                default=DEFAULT_EDITOR_FONT_FAMILY,
            ),
            visual_first_line_indent_enabled=_coerce_bool(
                self._repo.get(KEY_EDITOR_VISUAL_FIRST_LINE_INDENT_ENABLED),
                default=DEFAULT_EDITOR_VISUAL_FIRST_LINE_INDENT_ENABLED,
            ),
            typewriter_mode_enabled=_coerce_bool(
                self._repo.get(KEY_EDITOR_TYPEWRITER_MODE_ENABLED),
                default=DEFAULT_EDITOR_TYPEWRITER_MODE_ENABLED,
            ),
            auto_paragraph_indent_enabled=_coerce_bool(
                self._repo.get(KEY_EDITOR_AUTO_PARAGRAPH_INDENT_ENABLED),
                default=DEFAULT_EDITOR_AUTO_PARAGRAPH_INDENT_ENABLED,
            ),
            soft_page_guides_enabled=_coerce_bool(
                self._repo.get(KEY_EDITOR_SOFT_PAGE_GUIDES_ENABLED),
                default=DEFAULT_EDITOR_SOFT_PAGE_GUIDES_ENABLED,
            ),
        )

    def save_editor_display_settings(self, settings: EditorDisplaySettings) -> None:
        self._repo.set(KEY_EDITOR_FONT_SIZE, str(settings.font_size))
        self._repo.set(KEY_EDITOR_LINE_HEIGHT, f"{settings.line_height:.2f}")
        self._repo.set(
            KEY_EDITOR_PARAGRAPH_SPACING, f"{settings.paragraph_spacing:.2f}"
        )
        self._repo.set(KEY_EDITOR_CONTENT_WIDTH, str(settings.content_width))
        self._repo.set(
            KEY_EDITOR_PAGE_VERTICAL_PADDING, str(settings.page_vertical_padding)
        )
        self._repo.set(KEY_EDITOR_PAGE_GAP, str(settings.page_gap))
        self._repo.set(
            KEY_EDITOR_FONT_FAMILY,
            _coerce_font_family(
                settings.font_family,
                default=DEFAULT_EDITOR_FONT_FAMILY,
            ),
        )
        self._repo.set(
            KEY_EDITOR_VISUAL_FIRST_LINE_INDENT_ENABLED,
            "true" if settings.visual_first_line_indent_enabled else "false",
        )
        self._repo.set(
            KEY_EDITOR_TYPEWRITER_MODE_ENABLED,
            "true" if settings.typewriter_mode_enabled else "false",
        )
        self._repo.set(
            KEY_EDITOR_AUTO_PARAGRAPH_INDENT_ENABLED,
            "true" if settings.auto_paragraph_indent_enabled else "false",
        )
        self._repo.set(
            KEY_EDITOR_SOFT_PAGE_GUIDES_ENABLED,
            "true" if settings.soft_page_guides_enabled else "false",
        )

    def writing_notes_card_collapsed_by_default(self) -> bool:
        return _coerce_bool(
            self._repo.get(KEY_EDITOR_WRITING_NOTES_CARD_COLLAPSED_BY_DEFAULT),
            default=DEFAULT_EDITOR_WRITING_NOTES_CARD_COLLAPSED_BY_DEFAULT,
        )

    def save_writing_notes_card_collapsed_by_default(self, enabled: bool) -> None:
        self._repo.set(
            KEY_EDITOR_WRITING_NOTES_CARD_COLLAPSED_BY_DEFAULT,
            "true" if enabled else "false",
        )

    def reduced_motion_enabled(self) -> bool:
        return _coerce_bool(
            self._repo.get(KEY_REDUCED_MOTION_ENABLED),
            default=DEFAULT_REDUCED_MOTION_ENABLED,
        )

    def save_reduced_motion_enabled(self, enabled: bool) -> None:
        self._repo.set(KEY_REDUCED_MOTION_ENABLED, "true" if enabled else "false")

    def reference_library_default_group_mode(self) -> str:
        return (
            self._repo.get(
                KEY_REFERENCE_LIBRARY_DEFAULT_GROUP_MODE,
                DEFAULT_REFERENCE_LIBRARY_GROUP_MODE,
            )
            or DEFAULT_REFERENCE_LIBRARY_GROUP_MODE
        )

    def save_reference_library_default_group_mode(self, mode: str) -> None:
        self._repo.set(KEY_REFERENCE_LIBRARY_DEFAULT_GROUP_MODE, mode)

    def reference_library_stats_collapsed(self) -> bool:
        return _coerce_bool(
            self._repo.get(KEY_REFERENCE_LIBRARY_STATS_COLLAPSED),
            default=DEFAULT_REFERENCE_LIBRARY_STATS_COLLAPSED,
        )

    def save_reference_library_stats_collapsed(self, collapsed: bool) -> None:
        self._repo.set(
            KEY_REFERENCE_LIBRARY_STATS_COLLAPSED,
            "true" if collapsed else "false",
        )

    def reference_library_shelf_collapsed(self) -> bool:
        return _coerce_bool(
            self._repo.get(KEY_REFERENCE_LIBRARY_SHELF_COLLAPSED),
            default=DEFAULT_REFERENCE_LIBRARY_SHELF_COLLAPSED,
        )

    def save_reference_library_shelf_collapsed(self, collapsed: bool) -> None:
        self._repo.set(
            KEY_REFERENCE_LIBRARY_SHELF_COLLAPSED,
            "true" if collapsed else "false",
        )

    def reference_library_editor_drawer_visible(self) -> bool:
        return _coerce_bool(
            self._repo.get(KEY_REFERENCE_LIBRARY_EDITOR_DRAWER_VISIBLE),
            default=DEFAULT_REFERENCE_LIBRARY_EDITOR_DRAWER_VISIBLE,
        )

    def save_reference_library_editor_drawer_visible(self, visible: bool) -> None:
        self._repo.set(
            KEY_REFERENCE_LIBRARY_EDITOR_DRAWER_VISIBLE,
            "true" if visible else "false",
        )

    def reference_library_splitter_sizes(self) -> list[int]:
        raw = self._repo.get(KEY_REFERENCE_LIBRARY_SPLITTER_SIZES)
        if not raw:
            return []
        try:
            values = json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            return []
        if not isinstance(values, list):
            return []
        sizes: list[int] = []
        for value in values[:3]:
            try:
                size = int(value)
            except (TypeError, ValueError):
                return []
            if size < 0:
                return []
            sizes.append(size)
        return sizes if len(sizes) == 3 else []

    def save_reference_library_splitter_sizes(self, sizes: list[int]) -> None:
        clean = [max(0, int(size)) for size in sizes[:3]]
        if len(clean) == 3:
            self._repo.set(KEY_REFERENCE_LIBRARY_SPLITTER_SIZES, json.dumps(clean))

    def specimen_picker_default_group_mode(self) -> str:
        return (
            self._repo.get(
                KEY_SPECIMEN_PICKER_DEFAULT_GROUP_MODE,
                DEFAULT_SPECIMEN_PICKER_GROUP_MODE,
            )
            or DEFAULT_SPECIMEN_PICKER_GROUP_MODE
        )

    def save_specimen_picker_default_group_mode(self, mode: str) -> None:
        self._repo.set(KEY_SPECIMEN_PICKER_DEFAULT_GROUP_MODE, mode)


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
    if source == "opencode":
        return "opencode"
    return default


def _coerce_bool(raw: Optional[str], *, default: bool) -> bool:
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return default


def _coerce_int(
    raw: Optional[str], *, default: int, minimum: int, maximum: int
) -> int:
    try:
        value = int(raw) if raw is not None else default
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(maximum, value))


def _coerce_float(
    raw: Optional[str], *, default: float, minimum: float, maximum: float
) -> float:
    try:
        value = float(raw) if raw is not None else default
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(maximum, value))


def _coerce_font_family(raw: Optional[str], *, default: str) -> str:
    value = (raw or "").strip()
    if not value:
        return default
    parts = [part.strip().strip("'\"") for part in value.split(",")]
    cleaned = [part for part in parts if part]
    return ", ".join(cleaned) if cleaned else default
