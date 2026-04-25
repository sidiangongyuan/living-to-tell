"""Deterministic tag colour palette.

Given a tag name, ``get_tag_color`` returns a ``(background_hex, text_hex)``
pair drawn from a hand-curated set of soft pastel tokens. The mapping is
stable: the same name always returns the same colour regardless of run order
or locale.

Design goals
------------
* Consistent   — the same tag looks the same everywhere in the UI.
* Readable     — all (bg, text) pairs have sufficient contrast for body text.
* Unobtrusive  — low saturation, pale backgrounds, dark text; never neon.
* Deterministic — based on a stable hash of the normalised tag name.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Palette — 12 soft tokens (background_hex, text_hex)
# ---------------------------------------------------------------------------

_PALETTE: list[tuple[str, str]] = [
    ("#E8F4FD", "#1A5276"),  # sky blue
    ("#EAF7EA", "#1E6B2E"),  # sage green
    ("#FEF9E7", "#7D6608"),  # warm amber
    ("#F4ECF7", "#6C3483"),  # soft violet
    ("#FDEDEC", "#922B21"),  # dusty rose
    ("#E8F8F5", "#1A5E44"),  # seafoam teal
    ("#FDF2E9", "#784212"),  # terracotta
    ("#EBF5FB", "#1A4F72"),  # cornflower blue
    ("#F9EBEA", "#7B241C"),  # muted crimson
    ("#E9F7EF", "#145A32"),  # fern green
    ("#FEF5E7", "#6E2F0A"),  # peach ochre
    ("#F0F3F4", "#2E4053"),  # cool slate
]


def _stable_index(tag: str) -> int:
    """Return a stable palette index for *tag*.

    Normalises the tag to lowercase stripped form so ``"Python"`` and
    ``"python"`` map to the same colour.
    """
    normalised = tag.strip().lower()
    # Use a simple but stable polynomial hash; avoids relying on Python's
    # hash() which is randomised across interpreter invocations.
    h = 0
    for ch in normalised:
        h = (h * 31 + ord(ch)) & 0xFFFF_FFFF
    return h % len(_PALETTE)


def get_tag_color(tag: str) -> tuple[str, str]:
    """Return ``(background_color, text_color)`` for *tag*.

    The pair is always a valid CSS hex colour string (e.g. ``"#E8F4FD"``).
    An empty *tag* returns a neutral grey pair.
    """
    if not tag or not tag.strip():
        return ("#F0F0F0", "#555555")
    idx = _stable_index(tag)
    return _PALETTE[idx]


def tag_style_sheet(tag: str) -> str:
    """Return a QSS snippet suitable for a small tag badge label.

    Theme-aware: in light mode we use the pastel background + dark text
    pair from the palette; in dark mode we invert (deep tinted background
    + light text) and add a subtle border so the chip stays legible
    against the dark surface.
    """
    bg, fg = get_tag_color(tag)
    try:
        from writer.ui.theme import ThemeMode, current_mode, current_tokens

        if current_mode() is ThemeMode.DARK:
            tokens = current_tokens()
            # Use the original "text" hex as the chip background (a deep
            # saturated tone that holds up against the dark surface) and
            # the original pastel as foreground text.
            return (
                f"background-color: {fg}; color: {bg}; "
                f"border: 1px solid {tokens.border}; "
                "border-radius: 3px; padding: 1px 5px; font-size: 11px;"
            )
    except Exception:  # noqa: BLE001 — never let a chip break the UI
        pass
    return (
        f"background-color: {bg}; color: {fg}; "
        "border-radius: 3px; padding: 1px 5px; font-size: 11px;"
    )
