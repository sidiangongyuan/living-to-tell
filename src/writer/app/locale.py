"""Application-level locale tracking.

This module is imported by both the UI layer (for string translation) and the
service layer (e.g. PromptBuilder for AI prompt language). Keeping it in
``writer.app`` avoids circular imports between UI and services.

The locale is loaded once at application startup from persisted settings and
stays constant until the application is restarted. Hot-switching is not
supported.
"""
from __future__ import annotations

LOCALE_EN = "en"
LOCALE_ZH_CN = "zh_CN"
SUPPORTED_LOCALES = (LOCALE_EN, LOCALE_ZH_CN)

_CURRENT_LOCALE: str = LOCALE_EN


def set_locale(locale: str) -> None:
    """Set the active locale. Call once during bootstrap before any UI is built."""
    global _CURRENT_LOCALE
    if locale in SUPPORTED_LOCALES:
        _CURRENT_LOCALE = locale
    else:
        _CURRENT_LOCALE = LOCALE_EN


def current_locale() -> str:
    """Return the currently active locale string (e.g. ``"en"`` or ``"zh_CN"``)."""
    return _CURRENT_LOCALE
