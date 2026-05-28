"""M9A theme system: tokens, modes, persistence, and global QSS.

A single place to define the colours, radii, spacing, and font sizes used
across the UI. The rest of the app should never inline ``setStyleSheet``
with raw hex colours — instead it asks this module for either a token or
the ready-built application stylesheet.

Three modes are supported:

* ``ThemeMode.LIGHT`` — explicit light tokens.
* ``ThemeMode.DARK``  — explicit dark tokens.
* ``ThemeMode.SYSTEM`` — pick one of the above by inspecting the running
  application's palette / system colour scheme. If detection fails for
  any reason we fall back to ``LIGHT`` so the UI is always readable.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------
class ThemeMode(str, Enum):
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"

    @classmethod
    def parse(cls, value: Optional[str]) -> "ThemeMode":
        if not value:
            return cls.SYSTEM
        try:
            return cls(value.strip().lower())
        except ValueError:
            return cls.SYSTEM


# ---------------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Tokens:
    """Theme tokens. All colours are CSS hex strings."""

    # Surfaces
    bg_window: str
    bg_rail: str
    bg_list: str        # second column / list surface
    bg_main: str        # main work area
    bg_context: str     # right context pane
    bg_input: str
    bg_card: str
    bg_soft: str
    bg_preview: str
    bg_done: str
    bg_search: str

    # Text
    text_primary: str
    text_secondary: str
    text_muted: str
    text_on_accent: str

    # Borders
    border: str
    border_strong: str

    # Accent + states
    accent: str
    accent_hover: str
    accent_pressed: str
    selected_bg: str
    hover_bg: str

    # Semantic
    danger: str
    danger_hover: str
    archived_bg: str
    archived_fg: str

    # Geometry (shared between modes)
    radius_sm: int = 8
    radius_md: int = 10
    radius_lg: int = 14
    radius_xl: int = 18
    space_xs: int = 4
    space_sm: int = 8
    space_md: int = 12
    space_lg: int = 16
    space_xl: int = 24
    space_xxl: int = 32
    control_height: int = 36
    list_row_height: int = 42

    # Typography (point sizes — Qt scales by DPI on its own)
    font_family: str = (
        "'Segoe UI Variable', 'Segoe UI', 'Microsoft YaHei UI', "
        "'PingFang SC', 'Noto Sans CJK SC', 'Helvetica Neue', sans-serif"
    )
    font_serif: str = (
        "'Source Serif Pro', 'Source Han Serif SC', 'Songti SC', "
        "'Noto Serif CJK SC', 'Cambria', Georgia, serif"
    )
    fs_mode_title: int = 20
    fs_panel_title: int = 15
    fs_button: int = 13
    fs_list_main: int = 13
    fs_meta: int = 12
    fs_editor_body: int = 16
    fs_editor_work_body: int = 17


LIGHT_TOKENS = Tokens(
    bg_window="#F1ECE2",
    bg_rail="#E5DDD0",
    bg_list="#FFFFFF",
    bg_main="#F4EEE2",
    bg_context="#EFE7D8",
    bg_input="#FFFDF8",
    bg_card="#FBF7EF",
    bg_soft="#F8F1E5",
    bg_preview="#FFF9EF",
    bg_done="#F1E8D9",
    bg_search="#FFF7E8",
    text_primary="#2D2418",
    text_secondary="#625443",
    text_muted="#9A8872",
    text_on_accent="#FFFFFF",
    border="#DCCFB9",
    border_strong="#C8B596",
    accent="#7C8B6A",
    accent_hover="#68765A",
    accent_pressed="#56624A",
    selected_bg="#EBE1CB",
    hover_bg="#F5ECDD",
    danger="#B2553F",
    danger_hover="#8F4332",
    archived_bg="#F4E5CF",
    archived_fg="#916235",
)


DARK_TOKENS = Tokens(
    bg_window="#11161C",
    bg_rail="#161D24",
    bg_list="#1B232C",
    bg_main="#202A34",
    bg_context="#18212A",
    bg_input="#1F2933",
    bg_card="#1E2731",
    bg_soft="#18212A",
    bg_preview="#202B35",
    bg_done="#232A2F",
    bg_search="#232D36",
    text_primary="#E9EEF5",
    text_secondary="#A9B3C2",
    text_muted="#7D8898",
    text_on_accent="#0E1418",
    border="#2B3744",
    border_strong="#3A4654",
    accent="#48B7B8",
    accent_hover="#62C7C8",
    accent_pressed="#7AD2D3",
    selected_bg="#14373B",
    hover_bg="#222D38",
    danger="#E07060",
    danger_hover="#EE8472",
    archived_bg="#3B2B1D",
    archived_fg="#E2B37A",
)


# ---------------------------------------------------------------------------
# Mode resolution
# ---------------------------------------------------------------------------
_active_tokens: Tokens = LIGHT_TOKENS
_active_mode: ThemeMode = ThemeMode.SYSTEM


def _detect_system_dark(app: Optional[QApplication]) -> bool:
    """Return True if the OS / Qt palette is currently dark.

    Falls back to False (light) on any error.
    """
    if app is None:
        return False
    # Qt 6.5+ exposes Qt.ColorScheme via styleHints().colorScheme().
    try:
        from PySide6.QtCore import Qt as _Qt

        scheme = app.styleHints().colorScheme()
        dark = getattr(_Qt.ColorScheme, "Dark", None)
        if dark is not None and scheme == dark:
            return True
        light = getattr(_Qt.ColorScheme, "Light", None)
        if light is not None and scheme == light:
            return False
    except Exception:  # noqa: BLE001
        pass
    # Final heuristic: compare window vs. text lightness in the palette.
    try:
        pal: QPalette = app.palette()
        win = pal.color(QPalette.ColorRole.Window)
        txt = pal.color(QPalette.ColorRole.WindowText)
        return win.lightness() < txt.lightness()
    except Exception:  # noqa: BLE001
        return False


def resolve_tokens(mode: ThemeMode, app: Optional[QApplication] = None) -> Tokens:
    if mode is ThemeMode.LIGHT:
        return LIGHT_TOKENS
    if mode is ThemeMode.DARK:
        return DARK_TOKENS
    return DARK_TOKENS if _detect_system_dark(app) else LIGHT_TOKENS


def current_tokens() -> Tokens:
    return _active_tokens


def current_mode() -> ThemeMode:
    return _active_mode


# ---------------------------------------------------------------------------
# QSS
# ---------------------------------------------------------------------------
def build_qss(t: Tokens) -> str:
    """Compose the application-wide stylesheet from tokens.

    Object-name selectors (``QWidget#WriterRail`` etc.) let panels opt in
    to specific surfaces without affecting unrelated widgets.
    """
    return f"""
* {{
    font-family: {t.font_family};
}}

QMainWindow, QWidget#WriterShell {{
    background: {t.bg_window};
    color: {t.text_primary};
}}

QMenuBar {{
    background: {t.bg_window};
    color: {t.text_primary};
    border-bottom: 1px solid {t.border};
    padding: 2px 4px;
}}
QMenuBar::item {{
    background: transparent;
    padding: 4px 10px;
    border-radius: {t.radius_sm}px;
}}
QMenuBar::item:selected {{
    background: {t.hover_bg};
}}
QMenu {{
    background: {t.bg_card};
    color: {t.text_primary};
    border: 1px solid {t.border};
    border-radius: {t.radius_md}px;
    padding: 6px;
}}
QMenu::item {{
    padding: 6px 14px;
    border-radius: {t.radius_sm}px;
}}
QMenu::item:selected {{
    background: {t.hover_bg};
    color: {t.text_primary};
}}
QMenu::separator {{
    height: 1px;
    background: {t.border};
    margin: 4px 6px;
}}

QStatusBar {{
    background: {t.bg_window};
    color: {t.text_secondary};
    border-top: 1px solid {t.border};
}}
QStatusBar QLabel {{
    color: {t.text_secondary};
    padding: 0 8px;
}}

QToolBar {{
    background: {t.bg_window};
    border: none;
    spacing: 6px;
    padding: 4px 8px;
}}
QToolBar::separator {{
    background: {t.border};
    width: 1px;
    margin: 4px 4px;
}}

/* ------- Navigation rail (left) ------- */
QWidget#WriterRail {{
    background: {t.bg_rail};
    border-right: 1px solid {t.border};
}}
QPushButton#RailButton {{
    background: transparent;
    color: {t.text_secondary};
    border: none;
    border-radius: {t.radius_md}px;
    padding: 8px 4px;
    font-size: {t.fs_meta}px;
    font-weight: 500;
    text-align: center;
}}
QPushButton#RailButton:hover {{
    background: {t.hover_bg};
    color: {t.text_primary};
}}
QPushButton#RailButton:checked {{
    background: {t.selected_bg};
    color: {t.accent};
    font-weight: 600;
}}
QLabel#RailBrand {{
    color: {t.accent};
    font-size: 13px;
    font-weight: 700;
    padding: 12px 0 16px 0;
    qproperty-alignment: AlignCenter;
}}

/* ------- List column (second pane) ------- */
QWidget#WriterListColumn {{
    background: {t.bg_list};
    border-right: 1px solid {t.border};
}}
QLabel#ColumnTitle {{
    color: {t.text_primary};
    font-size: {t.fs_panel_title}px;
    font-weight: 600;
    padding: 4px 4px 8px 4px;
}}

/* ------- Main work area ------- */
QWidget#WriterMain {{
    background: {t.bg_main};
}}

/* ------- Right context pane ------- */
QWidget#WriterContext {{
    background: {t.bg_context};
    border-left: 1px solid {t.border};
}}
QLabel#ContextTitle {{
    color: {t.text_primary};
    font-size: {t.fs_panel_title}px;
    font-weight: 600;
    padding: 4px 0 8px 0;
}}
QLabel#ContextLabel {{
    color: {t.text_muted};
    font-size: {t.fs_meta}px;
}}
QLabel#ContextValue {{
    color: {t.text_primary};
    font-size: 13px;
}}

/* ------- Inputs ------- */
QLineEdit, QPlainTextEdit, QTextEdit, QComboBox, QSpinBox {{
    background: {t.bg_input};
    color: {t.text_primary};
    border: 1px solid {t.border};
    border-radius: {t.radius_md}px;
    padding: 6px 10px;
    selection-background-color: {t.accent};
    selection-color: {t.text_on_accent};
}}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus,
QComboBox:focus, QSpinBox:focus {{
    border: 1px solid {t.accent};
}}
QLineEdit:disabled, QPlainTextEdit:disabled, QTextEdit:disabled,
QComboBox:disabled, QSpinBox:disabled {{
    color: {t.text_muted};
    background: {t.bg_window};
}}
QComboBox::drop-down {{
    border: none;
    width: 22px;
}}

/* ------- Buttons ------- */
QPushButton {{
    background: {t.bg_input};
    color: {t.text_primary};
    border: 1px solid {t.border};
    border-radius: {t.radius_md}px;
    padding: 7px 14px;
    font-size: {t.fs_button}px;
    font-weight: 500;
    min-height: 30px;
}}
QPushButton:hover {{
    background: {t.hover_bg};
    border-color: {t.border_strong};
}}
QPushButton:pressed {{
    background: {t.selected_bg};
}}
QPushButton:disabled {{
    color: {t.text_muted};
    background: {t.bg_window};
    border-color: {t.border};
}}
QPushButton#PrimaryButton {{
    background: {t.accent};
    color: {t.text_on_accent};
    border: 1px solid {t.accent};
    font-weight: 600;
}}
QPushButton#PrimaryButton:hover {{
    background: {t.accent_hover};
    border-color: {t.accent_hover};
}}
QPushButton#PrimaryButton:pressed {{
    background: {t.accent_pressed};
    border-color: {t.accent_pressed};
}}
QPushButton#DangerButton {{
    background: transparent;
    color: {t.danger};
    border: 1px solid {t.border};
}}
QPushButton#DangerButton:hover {{
    background: {t.hover_bg};
    border-color: {t.danger};
    color: {t.danger_hover};
}}
QPushButton#GhostButton {{
    background: transparent;
    border: 1px solid transparent;
    color: {t.text_secondary};
}}
QPushButton#GhostButton:hover {{
    background: {t.hover_bg};
    color: {t.text_primary};
}}

/* ------- Lists ------- */
QListWidget {{
    background: {t.bg_list};
    color: {t.text_primary};
    border: none;
    padding: 4px;
    outline: 0;
}}
QListWidget::item {{
    padding: 8px 12px;
    margin: 2px 0;
    border-radius: {t.radius_md}px;
    color: {t.text_primary};
}}
QListWidget::item:hover {{
    background: {t.hover_bg};
}}
QListWidget::item:selected {{
    background: {t.selected_bg};
    color: {t.text_primary};
}}
QListWidget#ReferenceLibraryList,
QListWidget#SpecimenCardList,
QListWidget#SpecimenShelfList,
QListWidget#ReferenceShelfList {{
    background: {t.bg_list};
    border: 1px solid {t.border};
    border-radius: {t.radius_lg}px;
    padding: 6px;
}}
QListWidget#ReferenceLibraryList::item,
QListWidget#SpecimenCardList::item,
QListWidget#SpecimenShelfList::item,
QListWidget#ReferenceShelfList::item {{
    background: transparent;
    padding: 0;
    margin: 3px 0;
}}
QListWidget#ReferenceLibraryList::item:hover,
QListWidget#SpecimenCardList::item:hover,
QListWidget#SpecimenShelfList::item:hover,
QListWidget#ReferenceShelfList::item:hover,
QListWidget#ReferenceLibraryList::item:selected,
QListWidget#SpecimenCardList::item:selected,
QListWidget#SpecimenShelfList::item:selected,
QListWidget#ReferenceShelfList::item:selected {{
    background: transparent;
}}

/* ------- Splitter handle ------- */
QSplitter::handle {{
    background: {t.bg_window};
}}
QSplitter::handle:horizontal {{
    width: 1px;
}}
QSplitter::handle:vertical {{
    height: 1px;
}}

/* ------- Scroll bars ------- */
QScrollBar:vertical {{
    background: {t.hover_bg};
    width: 10px;
    margin: 2px 2px 2px 0;
    border-radius: 5px;
}}
QScrollBar::handle:vertical {{
    background: {t.border_strong};
    border: 2px solid {t.hover_bg};
    border-radius: 5px;
    min-height: 36px;
}}
QScrollBar::handle:vertical:hover {{
    background: {t.accent};
}}
QScrollBar:horizontal {{
    background: {t.hover_bg};
    height: 10px;
    margin: 0 2px 2px 2px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal {{
    background: {t.border_strong};
    border: 2px solid {t.hover_bg};
    border-radius: 5px;
    min-width: 36px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {t.accent};
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    background: transparent;
    border: none;
    width: 0;
    height: 0;
}}
QScrollBar::add-page, QScrollBar::sub-page {{
    background: transparent;
    border: none;
}}

/* ------- Editor surfaces (object-name driven) ------- */
QPlainTextEdit#FragmentBody, QTextEdit#WorkBody {{
    background: {t.bg_main};
    border: 1px solid {t.border};
    border-radius: {t.radius_lg}px;
    padding: 24px 32px;
    font-size: {t.fs_editor_body}px;
    line-height: 160%;
}}
QPlainTextEdit#FragmentBody[focusMode="true"] {{
    background: {t.bg_card};
    border-color: {t.border_strong};
}}
QTextEdit#WorkBody {{
    font-size: {t.fs_editor_work_body}px;
    font-family: {t.font_serif};
}}
QLineEdit#EditorTitle {{
    background: transparent;
    border: none;
    border-bottom: 1px solid {t.border};
    border-radius: 0;
    padding: 6px 2px;
    font-size: 18px;
    font-weight: 600;
    color: {t.text_primary};
}}
QLineEdit#EditorTitle:focus {{
    border-bottom: 1px solid {t.accent};
}}
QFrame#EditorFindBar {{
    background: {t.bg_card};
    border: 1px solid {t.border};
    border-radius: {t.radius_lg}px;
}}
QLineEdit#EditorFindInput {{
    background: {t.bg_search};
    border: 1px solid {t.border};
    border-radius: {t.radius_md}px;
    padding: 7px 12px;
}}
QLabel#EditorFindCount {{
    color: {t.text_secondary};
    font-size: {t.fs_meta}px;
    min-width: 52px;
    qproperty-alignment: AlignCenter;
}}
QLabel#EditorFindCount[noResults="true"] {{
    color: {t.danger};
}}
QFrame#EditorPageControls {{
    background: transparent;
    border: none;
}}
QLabel#EditorPageLabel {{
    color: {t.text_muted};
    font-size: {t.fs_meta}px;
    min-width: 78px;
}}
QPushButton#EditorPageButton {{
    background: {t.bg_card};
    color: {t.text_secondary};
    border: 1px solid {t.border};
    border-radius: {t.radius_md}px;
    padding: 4px 10px;
}}
QPushButton#EditorPageButton:hover {{
    color: {t.text_primary};
    border-color: {t.accent};
}}
QPushButton#EditorPageButton:disabled {{
    color: {t.text_muted};
    background: transparent;
}}

/* ------- Empty state card ------- */
QFrame#EmptyStateCard {{
    background: {t.bg_card};
    border: 1px solid {t.border};
    border-radius: {t.radius_lg}px;
}}
QLabel#EmptyStateTitle {{
    color: {t.text_primary};
    font-size: 17px;
    font-weight: 600;
}}
QLabel#EmptyStateDescription {{
    color: {t.text_secondary};
    font-size: {t.fs_list_main}px;
}}

/* ------- Daily quote card ------- */
QFrame#DailyQuoteCard {{
    background: {t.bg_card};
    border: 1px solid {t.border};
    border-radius: {t.radius_lg}px;
}}
QFrame#DailyQuoteCard QLabel:first-child {{
    color: {t.text_primary};
    font-size: {t.fs_panel_title}px;
    font-weight: 600;
}}
QLabel#DailyQuoteBody {{
    color: {t.text_primary};
    font-size: {t.fs_editor_body}px;
    line-height: 155%;
}}
QLabel#DailyQuoteMeta,
QLabel#DailyQuoteEmptyDesc {{
    color: {t.text_secondary};
    font-size: {t.fs_list_main}px;
}}
QLabel#DailyQuoteEmptyTitle {{
    color: {t.text_primary};
    font-size: {t.fs_panel_title}px;
    font-weight: 600;
}}

/* ------- Epigraph card ------- */
QFrame#EpigraphCard {{
    background: {t.bg_card};
    border: 1px solid {t.border};
    border-radius: {t.radius_lg}px;
}}
QLabel#EpigraphCardLabel {{
    color: {t.text_muted};
    font-size: {t.fs_meta}px;
    letter-spacing: 0.4px;
}}
QLabel#EpigraphQuote {{
    color: {t.text_primary};
    font-family: {t.font_serif};
    font-size: {t.fs_editor_body - 1}px;
    line-height: 165%;
}}
QLabel#EpigraphAttribution {{
    color: {t.text_secondary};
    font-family: {t.font_serif};
    font-size: {t.fs_meta + 1}px;
    padding-top: 4px;
}}

/* ------- Fragment writing notes ------- */
QFrame#WritingNotesCard {{
    background: {t.bg_card};
    border: 1px solid {t.border};
    border-left: 4px solid {t.accent};
    border-radius: {t.radius_lg}px;
}}
QLabel#WritingNotesTitle {{
    color: {t.text_primary};
    font-family: {t.font_serif};
    font-weight: 700;
}}
QLabel#WritingNotesCount,
QLabel#WritingNotesHint {{
    color: {t.text_muted};
    font-size: {t.fs_meta}px;
}}
QScrollArea#WritingNotesRowsScroll {{
    background: transparent;
    border: none;
}}
QScrollArea#WritingNotesRowsScroll QWidget {{
    background: transparent;
}}
QLabel#WritingNoteState {{
    color: {t.text_muted};
    font-size: {t.fs_meta}px;
    font-weight: 600;
}}
QFrame#WritingNoteRow,
QFrame#WritingNoteRowPinned,
QFrame#WritingNoteRowDone {{
    background: {t.bg_input};
    border: 1px solid {t.border};
    border-radius: {t.radius_md}px;
}}
QFrame#WritingNoteRowPinned {{
    border-left: 3px solid {t.accent};
}}
QFrame#WritingNoteRowDone {{
    background: {t.bg_done};
    border-style: dashed;
}}
QFrame#WritingNoteAccent {{
    background: {t.accent};
    border: none;
    border-radius: 2px;
}}
QLabel#WritingNoteBody {{
    color: {t.text_primary};
    font-family: {t.font_serif};
    line-height: 150%;
}}
QLabel#WritingNoteDoneSection {{
    color: {t.text_muted};
    font-size: {t.fs_meta}px;
    padding: 6px 2px 2px 2px;
}}
QLineEdit#WritingNoteInput {{
    background: {t.bg_search};
}}

/* ------- CheckBox ------- */
QCheckBox {{
    color: {t.text_secondary};
    spacing: 6px;
    padding: 4px 0;
    font-size: 12px;
}}
QCheckBox:hover {{
    color: {t.text_primary};
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {t.border_strong};
    border-radius: 4px;
    background: {t.bg_input};
}}
QCheckBox::indicator:checked {{
    background: {t.accent};
    border-color: {t.accent};
}}

/* ------- Tooltips ------- */
QToolTip {{
    background: {t.bg_card};
    color: {t.text_primary};
    border: 1px solid {t.border};
    padding: 4px 8px;
    border-radius: {t.radius_sm}px;
}}

/* ------- Meta / status / dialog notice labels (formerly hardcoded grey) ------- */
QLabel#MetaLabel {{
    color: {t.text_muted};
    font-size: {t.fs_meta}px;
}}
QLabel#StatusLabel {{
    color: {t.text_muted};
    padding: 0 8px;
}}
QLabel#DialogNote {{
    color: {t.text_muted};
}}
QLabel#NoResultsLabel {{
    color: {t.text_muted};
    font-size: {t.fs_meta}px;
    padding: 16px;
}}

/* ------- AI workspace ------- */
QWidget#AIWorkspacePanel,
QWidget#AIToolsTab,
QWidget#AIChatTab,
QWidget#AIToolsRight,
QWidget#AIToolsViewport {{
    background: {t.bg_main};
    color: {t.text_primary};
}}
QTabWidget#AIWorkspaceTabs::pane {{
    background: {t.bg_main};
    border: 1px solid {t.border};
    border-radius: {t.radius_lg}px;
    top: -1px;
}}
QTabWidget#AIWorkspaceTabs QTabBar::tab {{
    background: {t.bg_window};
    color: {t.text_secondary};
    border: 1px solid {t.border};
    border-bottom: none;
    border-top-left-radius: {t.radius_md}px;
    border-top-right-radius: {t.radius_md}px;
    padding: 7px 16px;
    margin-right: 4px;
}}
QTabWidget#AIWorkspaceTabs QTabBar::tab:selected {{
    background: {t.bg_main};
    color: {t.text_primary};
    font-weight: 600;
}}
QScrollArea#AIToolsScroll {{
    background: {t.bg_main};
    border: none;
}}
QFrame#AIParamsBox,
QFrame#AIAdvancedBox,
QFrame#AISelectionCard,
QFrame#AIWritingNotesBox {{
    background: {t.bg_card};
    border: 1px solid {t.border};
    border-radius: {t.radius_lg}px;
    padding: 10px;
}}
QFrame#AIParamsBox QLabel,
QFrame#AIAdvancedBox QLabel {{
    color: {t.text_secondary};
}}
QLabel#AIWritingNotesStatus {{
    color: {t.text_primary};
    font-weight: 600;
}}
QLabel#AISelectionTitle {{
    color: {t.text_primary};
    font-weight: 600;
}}
QLabel#AISelectionMeta {{
    color: {t.text_muted};
    font-size: {t.fs_meta}px;
}}
QPlainTextEdit#AISelectionPreview {{
    background: {t.bg_preview};
    color: {t.text_primary};
    border: 1px solid {t.border};
    border-radius: {t.radius_md}px;
    padding: 8px;
    font-family: {t.font_serif};
}}
QPlainTextEdit#AIWritingNotesPreview {{
    background: {t.bg_preview};
    color: {t.text_secondary};
    border: 1px solid {t.border};
    border-radius: {t.radius_md}px;
    padding: 8px;
    font-family: {t.font_serif};
}}
QWidget#AIWorkspacePanel QCheckBox {{
    color: {t.text_primary};
}}
QLabel#AIScopeLabel,
QLabel#AIChatScope,
QLabel#AIAttachLabel,
QLabel#AIResultLabel {{
    color: {t.text_primary};
    font-weight: 600;
}}
QLabel#AITaskDesc {{
    color: {t.text_secondary};
    background: {t.bg_card};
    border: 1px solid {t.border};
    border-radius: {t.radius_md}px;
    padding: 8px 10px;
    font-size: {t.fs_meta}px;
}}
QLabel#AIStyleHint,
QLabel#AIStylePresetLabel,
QLabel#AIAttachEmpty,
QLabel#AIAttachTotal,
QLabel#AIStatusLabel,
QLabel#AIResultMeta,
QLabel#AICitationsLabel,
QLabel#AIChatThreadInfo,
QLabel#AIChatAttach {{
    color: {t.text_muted};
    font-size: {t.fs_meta}px;
}}
QPushButton#AIStylePresetButton {{
    background: {t.bg_window};
    color: {t.text_secondary};
    border: 1px solid {t.border};
    padding: 5px 10px;
    min-height: 26px;
}}
QPushButton#AIStylePresetButton:hover {{
    background: {t.hover_bg};
    color: {t.text_primary};
}}
QPushButton#AIRunButton {{
    background: {t.accent};
    color: {t.text_on_accent};
    border-color: {t.accent};
    font-weight: 600;
}}
QPushButton#AIRunButton:hover {{
    background: {t.accent_hover};
    border-color: {t.accent_hover};
}}
QTextEdit#AIResultView,
QTextEdit#AIChatMessages {{
    background: {t.bg_input};
    color: {t.text_primary};
    border: 1px solid {t.border};
    border-radius: {t.radius_lg}px;
}}
QPlainTextEdit#AIExtraInstructions {{
    background: {t.bg_input};
    color: {t.text_primary};
    border: 1px solid {t.border};
    border-radius: {t.radius_md}px;
}}
QWidget#AIWorkspacePanel QComboBox QAbstractItemView {{
    background: {t.bg_card};
    color: {t.text_primary};
    border: 1px solid {t.border};
    selection-background-color: {t.selected_bg};
    selection-color: {t.text_primary};
}}

/* ------- Reference library ------- */
QFrame#RefStatsBox {{
    background: {t.bg_card};
    border: 1px solid {t.border};
    border-radius: {t.radius_lg}px;
}}
QPushButton#RefStatTab {{
    background: transparent;
    color: {t.text_secondary};
    border: 1px solid {t.border};
    border-radius: {t.radius_md}px;
    padding: 5px 12px;
    min-height: 28px;
}}
QPushButton#RefStatTab:hover {{
    background: {t.hover_bg};
    color: {t.text_primary};
    border-color: {t.border_strong};
}}
QPushButton#RefStatTab:checked {{
    background: {t.selected_bg};
    color: {t.accent};
    border-color: {t.accent};
    font-weight: 600;
}}
QLabel#RefStatScope {{
    color: {t.text_muted};
    font-size: {t.fs_meta}px;
}}
QFrame#RefStatCard {{
    background: {t.bg_card};
    border: 1px solid {t.border};
    border-radius: {t.radius_md}px;
}}
QFrame#RefStatMetricCard {{
    background: {t.bg_window};
    border: 1px solid {t.border};
    border-radius: {t.radius_md}px;
}}
QLabel#RefStatTitle {{
    color: {t.text_muted};
    font-size: {t.fs_meta}px;
    font-weight: 600;
}}
QLabel#RefStatValue {{
    color: {t.text_primary};
    font-size: {t.fs_meta}px;
}}
QLabel#RefStatMetricValue {{
    color: {t.text_primary};
    font-size: {t.fs_panel_title}px;
    font-weight: 700;
}}
QLabel#RefStatMetricLabel,
QLabel#RefBarLabel,
QLabel#RefBarValue {{
    color: {t.text_secondary};
    font-size: {t.fs_meta}px;
}}
QLabel#AIAttachTotal[overBudget="true"] {{
    color: {t.danger};
    font-weight: 600;
}}
QProgressBar#RefStatBar {{
    background: {t.hover_bg};
    border: 1px solid {t.border};
    border-radius: {t.radius_sm}px;
    min-height: 10px;
}}
QProgressBar#RefStatBar::chunk {{
    background: {t.accent};
    border-radius: {t.radius_sm}px;
}}
QLabel#RefTagCloudChip {{
    background: {t.hover_bg};
    color: {t.text_primary};
    border: 1px solid {t.border};
    border-radius: {t.radius_md}px;
    padding: 6px 10px;
    font-size: {t.fs_meta}px;
}}
QLabel#SpecimenDuplicateLabel {{
    color: {t.text_secondary};
    font-size: {t.fs_meta}px;
    padding: 4px 0;
}}
QFrame#SpecimenPreviewCard {{
    background: {t.bg_card};
    border: 1px solid {t.border_strong};
    border-radius: {t.radius_lg}px;
}}
QWidget#SpecimenShelfCard,
QWidget#ReferenceShelfCard,
QWidget#ReferenceGroupHeader,
QWidget#ReferenceSectionHeader {{
    background: transparent;
}}
QWidget#SpecimenShelfCard[current="true"],
QWidget#ReferenceShelfCard[current="true"] {{
    background: {t.selected_bg};
    border: 1px solid {t.border_strong};
    border-radius: {t.radius_md}px;
}}
QLabel#SpecimenSectionTitle,
QLabel#ReferenceGroupTitle {{
    color: {t.text_primary};
    font-size: {t.fs_panel_title}px;
    font-weight: 600;
}}
QLabel#SpecimenShelfTitle,
QLabel#ReferenceSectionTitle,
QLabel#ReferenceShelfTitle {{
    color: {t.text_primary};
    font-size: {t.fs_list_main}px;
    font-weight: 600;
}}
QLabel#SpecimenShelfMeta,
QLabel#ReferenceGroupMeta,
QLabel#ReferenceShelfMeta {{
    color: {t.text_muted};
    font-size: {t.fs_meta}px;
}}
QFrame#ReferenceBookHeader {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {t.bg_card}, stop:1 {t.bg_context});
    border: 1px solid {t.border};
    border-radius: {t.radius_lg}px;
}}
QLabel#ReferenceBookTitle {{
    color: {t.text_primary};
    font-family: {t.font_serif};
    font-size: 22px;
    font-weight: 700;
}}
QLabel#ReferenceBookAuthor {{
    color: {t.text_secondary};
    font-size: {t.fs_list_main}px;
}}
QLabel#ReferenceBookMeta,
QLabel#ReferenceBookSummary {{
    color: {t.text_muted};
    font-size: {t.fs_meta}px;
}}
QWidget#ReferenceListCard,
QWidget#SpecimenListCard {{
    background: {t.bg_card};
    border: 1px solid {t.border};
    border-radius: {t.radius_md}px;
}}
QWidget#ReferenceListCard:hover,
QWidget#SpecimenListCard:hover {{
    border-color: {t.border_strong};
}}
QWidget#ReferenceListCard[current="true"],
QWidget#SpecimenListCard[current="true"] {{
    border-color: {t.accent};
}}
QWidget#SpecimenListCard[checked="true"] {{
    background: {t.selected_bg};
    border-color: {t.accent};
}}
QLabel#ReferenceCardTitle,
QLabel#SpecimenPreviewTitle {{
    color: {t.text_primary};
    font-size: {t.fs_panel_title}px;
    font-weight: 600;
}}
QLabel#ReferenceCardSource {{
    color: {t.text_primary};
    font-family: {t.font_serif};
    font-size: {t.fs_panel_title}px;
    font-weight: 700;
}}
QLabel#ReferenceCardAuthor,
QLabel#SpecimenListAuthor {{
    color: {t.text_muted};
    font-size: {t.fs_meta}px;
}}
QLabel#ReferenceCardExcerpt {{
    color: {t.text_primary};
    font-family: {t.font_serif};
    font-size: {t.fs_list_main}px;
}}
QLabel#ReferenceQuoteText,
QLabel#SpecimenListExcerpt {{
    color: {t.text_primary};
    font-family: {t.font_serif};
    font-size: {t.fs_editor_body}px;
}}
QLabel#ReferenceCardMeta,
QLabel#SpecimenListMeta,
QLabel#SpecimenPreviewMeta,
QLabel#SpecimenPreviewNote {{
    color: {t.text_muted};
    font-size: {t.fs_meta}px;
}}
QLabel#ReferenceCardNote {{
    color: {t.text_secondary};
    font-size: {t.fs_meta}px;
}}
QLabel#SpecimenListTitle {{
    color: {t.text_primary};
    font-size: {t.fs_panel_title}px;
    font-weight: 600;
}}
QLabel#SpecimenListNote {{
    color: {t.text_secondary};
    font-size: {t.fs_meta}px;
}}
QPushButton#SpecimenSelectBadge {{
    background: transparent;
    color: {t.accent};
    border: 1px solid {t.border_strong};
    border-radius: {t.radius_sm}px;
    padding: 4px 10px;
    min-height: 24px;
    font-size: {t.fs_meta}px;
    font-weight: 600;
}}
QPushButton#SpecimenSelectBadge:hover {{
    background: {t.hover_bg};
    border-color: {t.accent};
}}
QPushButton#SpecimenSelectBadge:checked {{
    background: {t.accent};
    color: {t.text_on_accent};
    border-color: {t.accent};
}}
QLabel#SpecimenSoftChip {{
    background: {t.hover_bg};
    color: {t.text_secondary};
    border: 1px solid {t.border};
    border-radius: {t.radius_sm}px;
    padding: 2px 8px;
    font-size: {t.fs_meta}px;
}}
QPlainTextEdit#ReferenceQuoteEditor {{
    background: {t.bg_input};
    color: {t.text_primary};
    font-family: {t.font_serif};
    font-size: {t.fs_editor_body}px;
    border: 1px solid {t.border};
    border-radius: {t.radius_lg}px;
    padding: 14px 16px;
}}
QTextEdit#SpecimenPreviewBody {{
    background: {t.bg_input};
    color: {t.text_primary};
    border: 1px solid {t.border};
    border-radius: {t.radius_md}px;
}}

/* ------- Workspace-area overlay cards (welcome / unselected) ------- */
QWidget#WriterWorkspaceOverlay {{
    background: {t.bg_main};
}}

/* ------- Dates panel ------- */
QWidget#DatesPanel {{
    background: {t.bg_main};
    color: {t.text_primary};
}}
QCalendarWidget#DatesCalendar {{
    background: {t.bg_card};
    border: 1px solid {t.border};
    border-radius: {t.radius_lg}px;
    selection-background-color: {t.accent};
    selection-color: {t.text_on_accent};
    alternate-background-color: {t.bg_list};
}}
QCalendarWidget#DatesCalendar QWidget {{
    color: {t.text_primary};
}}
QCalendarWidget#DatesCalendar QToolButton {{
    background: transparent;
    color: {t.text_primary};
    border: none;
    padding: 4px 10px;
    border-radius: {t.radius_sm}px;
}}
QCalendarWidget#DatesCalendar QToolButton:hover {{
    background: {t.hover_bg};
}}
QCalendarWidget#DatesCalendar QAbstractItemView:enabled {{
    background: {t.bg_card};
    color: {t.text_primary};
    selection-background-color: {t.accent};
    selection-color: {t.text_on_accent};
}}
QCalendarWidget#DatesCalendar QAbstractItemView:disabled {{
    color: {t.text_muted};
}}
QListWidget#DatesEntryList {{
    background: {t.bg_list};
    border: 1px solid {t.border};
    border-radius: {t.radius_md}px;
}}
QLabel#DatesHeader {{
    color: {t.text_primary};
    font-size: {t.fs_panel_title}px;
    font-weight: 600;
    padding: 4px 0;
}}
QLabel#DatesSummary {{
    color: {t.text_muted};
    font-size: {t.fs_meta}px;
}}
QPushButton#DatesGoTodayBtn {{
    background: transparent;
    color: {t.accent};
    border: 1px solid {t.border};
}}
QPushButton#DatesGoTodayBtn:hover {{
    background: {t.hover_bg};
    border-color: {t.accent};
}}
QPushButton#DatesNewTodayBtn {{
    background: {t.accent};
    color: {t.text_on_accent};
    border-color: {t.accent};
    font-weight: 600;
}}
QPushButton#DatesNewTodayBtn:hover {{
    background: {t.accent_hover};
    border-color: {t.accent_hover};
}}

/* ------- Merge-to-draft dialog ------- */
QDialog#MergeToDraftDialog,
QDialog#AppendTagsDialog {{
    background: {t.bg_window};
    color: {t.text_primary};
}}
QPlainTextEdit#MergePreview {{
    background: {t.bg_input};
    color: {t.text_primary};
    border: 1px solid {t.border};
    border-radius: {t.radius_md}px;
    padding: 12px 14px;
    font-size: {t.fs_list_main}px;
    line-height: 150%;
}}
""".strip()


# ---------------------------------------------------------------------------
# Apply
# ---------------------------------------------------------------------------
def apply_theme(app: QApplication, mode: ThemeMode) -> Tokens:
    """Resolve and install the theme on ``app``.

    Returns the active tokens so callers can re-style ad-hoc widgets.
    """
    global _active_tokens, _active_mode
    _active_mode = mode
    tokens = resolve_tokens(mode, app)
    _active_tokens = tokens
    app.setStyleSheet(build_qss(tokens))
    # Also push a basic palette so native widgets without QSS coverage
    # (e.g. native dialogs) read the right text colour.
    pal = app.palette()
    pal.setColor(QPalette.ColorRole.Window, QColor(tokens.bg_window))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(tokens.text_primary))
    pal.setColor(QPalette.ColorRole.Base, QColor(tokens.bg_input))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor(tokens.bg_list))
    pal.setColor(QPalette.ColorRole.Text, QColor(tokens.text_primary))
    pal.setColor(QPalette.ColorRole.Button, QColor(tokens.bg_input))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(tokens.text_primary))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(tokens.accent))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(tokens.text_on_accent))
    pal.setColor(QPalette.ColorRole.ToolTipBase, QColor(tokens.bg_card))
    pal.setColor(QPalette.ColorRole.ToolTipText, QColor(tokens.text_primary))
    app.setPalette(pal)
    return tokens
