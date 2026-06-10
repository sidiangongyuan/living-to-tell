"""Left navigation rail (M9A; icon system refreshed for the Apple-style UI).

Vertical column with one button per top-level mode plus settings/theme
controls at the bottom. Each button renders as a line icon above a short
text label so unfamiliar users still understand them at a glance.

Icons use **Segoe Fluent Icons** (the Win11 system icon font) when present,
falling back to **Segoe MDL2 Assets** (Win10) and finally to plain Unicode
glyphs, so the rail never renders as tofu boxes on a machine missing the
icon font. The icon lives in its own ``QLabel`` with the icon font pinned via
a per-widget stylesheet — the app-wide ``* { font-family }`` rule overrides
``setFont()``, and only a widget-level stylesheet outranks the app sheet.
Selected/hover states still recolour the glyph through app-QSS descendant
selectors (``#RailButton:checked QLabel#RailIcon``).
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import (
    QButtonGroup,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


# ---------------------------------------------------------------------------
# Icon font resolution + glyph maps
# ---------------------------------------------------------------------------
_FLUENT = "Segoe Fluent Icons"
_MDL2 = "Segoe MDL2 Assets"

# Segoe Fluent Icons / MDL2 share most code points for these basic glyphs, so
# one map serves both. Keys are stable role names used below.
_ICON_GLYPHS = {
    "dates": "",      # Calendar
    "fragments": "",  # Edit (pencil)
    "collections": "",  # Library
    "ai": "",         # Lightbulb / idea (EA80)
    "search": "",     # Search
    "theme": "",      # Brightness
    "settings": "",   # Settings (gear)
}

# Plain-Unicode fallback when no Segoe icon font is installed. These are the
# original glyphs the rail shipped with, kept readable on any font.
_FALLBACK_GLYPHS = {
    "dates": "\U0001F4C5",  # 📅
    "fragments": "✎",   # ✎
    "collections": "⊞",  # ⊞
    "ai": "✦",          # ✦
    "search": "⌕",      # ⌕
    "theme": "◑",       # ◑
    "settings": "⚙",    # ⚙
}

_resolved_icon_family: Optional[str] = None
_resolved_icon_checked = False


def _icon_font_family() -> Optional[str]:
    """Return the best available Segoe icon-font family, or None.

    Cached after first lookup. ``None`` means neither Fluent nor MDL2 is
    installed and the caller should use the plain-Unicode fallback glyphs.
    """
    global _resolved_icon_family, _resolved_icon_checked
    if _resolved_icon_checked:
        return _resolved_icon_family
    _resolved_icon_checked = True
    try:
        families = set(QFontDatabase.families())
    except Exception:  # noqa: BLE001 — font DB must never break the rail
        families = set()
    if _FLUENT in families:
        _resolved_icon_family = _FLUENT
    elif _MDL2 in families:
        _resolved_icon_family = _MDL2
    else:
        _resolved_icon_family = None
    return _resolved_icon_family


def _glyph_for(role: str) -> str:
    if _icon_font_family() is not None:
        return _ICON_GLYPHS.get(role, _FALLBACK_GLYPHS.get(role, "?"))
    return _FALLBACK_GLYPHS.get(role, "?")


class RailButton(QPushButton):
    """A vertical icon+label rail button.

    Subclasses ``QPushButton`` so it can still join the mode ``QButtonGroup``
    and be exposed through the same property accessors as before. The button
    carries no text itself; an icon ``QLabel`` and a text ``QLabel`` are laid
    out inside it. The icon label pins the icon font through its own widget
    stylesheet because the application stylesheet's ``*`` font-family rule
    overrides a plain ``setFont()`` (which would leave glyph rendering to the
    OS font fallback instead of the font this module actually selected).
    """

    ICON_POINT_SIZE = 18

    def __init__(
        self,
        role: str,
        label: str,
        *,
        checkable: bool = True,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("RailButton")
        self.setCheckable(checkable)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(56)
        self.setToolTip(label)

        self._icon = QLabel(_glyph_for(role))
        self._icon.setObjectName("RailIcon")
        self._icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        icon_font = QFont()
        family = _icon_font_family()
        if family is not None:
            icon_font.setFamily(family)
            # The app stylesheet's `* { font-family }` rule beats setFont();
            # a widget-level stylesheet is the only thing that beats the app
            # sheet, so pin the family here. Colour still comes from app-QSS
            # descendant selectors (only conflicting properties are overridden).
            self._icon.setStyleSheet(f'font-family: "{family}";')
        icon_font.setPointSize(self.ICON_POINT_SIZE)
        self._icon.setFont(icon_font)

        self._label = QLabel(label)
        self._label.setObjectName("RailLabel")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 6)
        layout.setSpacing(2)
        layout.addWidget(self._icon)
        layout.addWidget(self._label)

    def setText(self, text: str) -> None:  # noqa: N802 — keep label in sync
        """Keep the visible text label in sync if callers set text."""
        self._label.setText(text)
        self.setToolTip(text)


class NavigationRail(QWidget):
    """Vertical rail with mode buttons + bottom utility buttons.

    Emits ``mode_changed(int)`` when one of the registered mode buttons is
    activated. Mode index convention after the article-model refactor:
      0=Dates, 1=Articles, 2=Collections, 3=AI.
    """

    mode_changed = Signal(int)
    search_clicked = Signal()
    theme_clicked = Signal()
    settings_clicked = Signal()

    RAIL_WIDTH = 80

    def __init__(
        self,
        *,
        brand_text: str,
        fragments_label: str,
        collections_label: str,
        search_label: str,
        theme_label: str,
        settings_label: str,
        ai_label: str = "AI",
        dates_label: str = "Dates",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("WriterRail")
        self.setFixedWidth(self.RAIL_WIDTH)

        self._brand = QLabel(brand_text)
        self._brand.setObjectName("RailBrand")

        self._dates_btn = RailButton("dates", dates_label)
        self._frag_btn = RailButton("fragments", fragments_label)
        self._coll_btn = RailButton("collections", collections_label)
        self._ai_btn = RailButton("ai", ai_label)
        self._search_btn = RailButton("search", search_label, checkable=False)
        self._theme_btn = RailButton("theme", theme_label, checkable=False)
        self._settings_btn = RailButton("settings", settings_label, checkable=False)

        self._mode_group = QButtonGroup(self)
        self._mode_group.setExclusive(True)
        for idx, btn in enumerate(
            (
                self._dates_btn,
                self._frag_btn,
                self._coll_btn,
                self._ai_btn,
            )
        ):
            self._mode_group.addButton(btn, idx)
        self._mode_group.idClicked.connect(self.mode_changed.emit)

        self._search_btn.clicked.connect(self.search_clicked.emit)
        self._theme_btn.clicked.connect(self.theme_clicked.emit)
        self._settings_btn.clicked.connect(self.settings_clicked.emit)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        layout.addWidget(self._brand)
        layout.addWidget(self._dates_btn)
        layout.addWidget(self._frag_btn)
        layout.addWidget(self._coll_btn)
        layout.addWidget(self._ai_btn)
        layout.addSpacing(12)
        layout.addWidget(self._search_btn)
        layout.addStretch(1)
        layout.addWidget(self._theme_btn)
        layout.addWidget(self._settings_btn)

        self._dates_btn.setChecked(True)

    # ------------------------------------------------------------------
    def set_active_mode(self, mode: int) -> None:
        btn = self._mode_group.button(mode)
        if btn is not None:
            btn.setChecked(True)

    def active_mode(self) -> int:
        return self._mode_group.checkedId()

    @property
    def fragments_button(self) -> QPushButton:
        return self._frag_btn

    @property
    def dates_button(self) -> QPushButton:
        return self._dates_btn

    @property
    def collections_button(self) -> QPushButton:
        return self._coll_btn

    @property
    def ai_button(self) -> QPushButton:
        return self._ai_btn

    @property
    def search_button(self) -> QPushButton:
        return self._search_btn

    @property
    def theme_button(self) -> QPushButton:
        return self._theme_btn

    @property
    def settings_button(self) -> QPushButton:
        return self._settings_btn
