"""Shared helpers for the quick-capture workflow."""
from __future__ import annotations

from typing import Optional

from writer.app.locale import LOCALE_ZH_CN, current_locale

QUICK_CAPTURE_TAG_EN = "quick"
QUICK_CAPTURE_TAG_ZH = "速记"
QUICK_CAPTURE_TAGS = (QUICK_CAPTURE_TAG_EN, QUICK_CAPTURE_TAG_ZH)


def quick_capture_tag() -> str:
    return QUICK_CAPTURE_TAG_ZH if current_locale() == LOCALE_ZH_CN else QUICK_CAPTURE_TAG_EN


def is_quick_capture_tag(tag: str) -> bool:
    candidate = (tag or "").strip().lower()
    return candidate == QUICK_CAPTURE_TAG_EN or (tag or "").strip() == QUICK_CAPTURE_TAG_ZH


def is_quick_capture_entry(entry) -> bool:
    return any(is_quick_capture_tag(tag) for tag in getattr(entry, "tags", []))


def derive_quick_capture_title(body: str, *, fallback: Optional[str] = None) -> str:
    for line in (body or "").splitlines():
        candidate = line.strip()
        if candidate:
            return candidate[:40].strip()
    if fallback:
        return fallback
    return "未命名片段" if current_locale() == LOCALE_ZH_CN else "Untitled fragment"