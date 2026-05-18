"""High-level settings facade.

Wraps :class:`writer.storage.repositories.settings_repository.SettingsRepository`
and exposes the typed setting keys the rest of the app cares about. UI code
should depend on this facade, not on the repository directly.

Milestone 1 only needs a tiny surface; real getters/setters for AI provider
configuration will land alongside the settings dialog in a later milestone.
"""
from __future__ import annotations

from dataclasses import dataclass
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
KEY_REFERENCE_LIBRARY_DEFAULT_GROUP_MODE = "reference_library.default_group_mode"
KEY_SPECIMEN_PICKER_DEFAULT_GROUP_MODE = "specimen_picker.default_group_mode"
DEFAULT_REFERENCE_LIBRARY_GROUP_MODE = "source"
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
KEY_EDITOR_FONT_FAMILY = "editor.font_family"
KEY_EDITOR_VISUAL_FIRST_LINE_INDENT_ENABLED = (
    "editor.visual_first_line_indent_enabled"
)
KEY_EDITOR_TYPEWRITER_MODE_ENABLED = "editor.typewriter_mode_enabled"
KEY_EDITOR_AUTO_PARAGRAPH_INDENT_ENABLED = "editor.auto_paragraph_indent_enabled"
KEY_REDUCED_MOTION_ENABLED = "ui.reduced_motion_enabled"
DEFAULT_EDITOR_FONT_SIZE = 18
DEFAULT_EDITOR_LINE_HEIGHT = 1.8
DEFAULT_EDITOR_PARAGRAPH_SPACING = 0.8
DEFAULT_EDITOR_CONTENT_WIDTH = 1000
MAX_EDITOR_CONTENT_WIDTH = 1600
DEFAULT_EDITOR_FONT_FAMILY = (
    "Noto Serif SC, Source Han Serif SC, Songti SC, 华文宋体, 宋体, Georgia, Cambria"
)
DEFAULT_EDITOR_VISUAL_FIRST_LINE_INDENT_ENABLED = True
DEFAULT_EDITOR_TYPEWRITER_MODE_ENABLED = True
DEFAULT_EDITOR_AUTO_PARAGRAPH_INDENT_ENABLED = True
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

SUPPORTED_WIRE_APIS = ("responses",)
DEFAULT_WIRE_API = "responses"


@dataclass(frozen=True)
class EditorDisplaySettings:
    font_size: int = DEFAULT_EDITOR_FONT_SIZE
    line_height: float = DEFAULT_EDITOR_LINE_HEIGHT
    paragraph_spacing: float = DEFAULT_EDITOR_PARAGRAPH_SPACING
    content_width: int = DEFAULT_EDITOR_CONTENT_WIDTH
    font_family: str = DEFAULT_EDITOR_FONT_FAMILY
    visual_first_line_indent_enabled: bool = (
        DEFAULT_EDITOR_VISUAL_FIRST_LINE_INDENT_ENABLED
    )
    typewriter_mode_enabled: bool = DEFAULT_EDITOR_TYPEWRITER_MODE_ENABLED
    auto_paragraph_indent_enabled: bool = DEFAULT_EDITOR_AUTO_PARAGRAPH_INDENT_ENABLED


DEFAULT_EDITOR_DISPLAY_SETTINGS = EditorDisplaySettings()


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
        )

    def save_editor_display_settings(self, settings: EditorDisplaySettings) -> None:
        self._repo.set(KEY_EDITOR_FONT_SIZE, str(settings.font_size))
        self._repo.set(KEY_EDITOR_LINE_HEIGHT, f"{settings.line_height:.2f}")
        self._repo.set(
            KEY_EDITOR_PARAGRAPH_SPACING, f"{settings.paragraph_spacing:.2f}"
        )
        self._repo.set(KEY_EDITOR_CONTENT_WIDTH, str(settings.content_width))
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
