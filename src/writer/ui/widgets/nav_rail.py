"""Left navigation rail (M9A).

Vertical column with one button per top-level mode plus settings/theme
controls at the bottom. Buttons render as icon-glyph + label so unfamiliar
users still understand them at a glance.
"""
from __future__ import annotations

from typing import Callable, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class RailButton(QPushButton):
    """A vertical-stacked icon+label rail button."""

    def __init__(
        self,
        glyph: str,
        label: str,
        *,
        checkable: bool = True,
        parent: Optional[QWidget] = None,
    ) -> None:
        # Use a two-line text so we get glyph on top, label underneath.
        super().__init__(f"{glyph}\n{label}", parent)
        self.setObjectName("RailButton")
        self.setCheckable(checkable)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(56)
        self.setToolTip(label)


class NavigationRail(QWidget):
    """Vertical rail with mode buttons + bottom utility buttons.

    Emits ``mode_changed(int)`` when one of the registered mode buttons is
    activated (0=Fragments, 1=Works, 2=Collections by convention).
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
        works_label: str,
        collections_label: str,
        search_label: str,
        theme_label: str,
        settings_label: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("WriterRail")
        self.setFixedWidth(self.RAIL_WIDTH)

        self._brand = QLabel(brand_text)
        self._brand.setObjectName("RailBrand")

        self._frag_btn = RailButton("✎", fragments_label)
        self._works_btn = RailButton("📚", works_label)
        self._coll_btn = RailButton("⊞", collections_label)
        self._search_btn = RailButton("⌕", search_label, checkable=False)
        self._theme_btn = RailButton("◑", theme_label, checkable=False)
        self._settings_btn = RailButton("⚙", settings_label, checkable=False)

        self._mode_group = QButtonGroup(self)
        self._mode_group.setExclusive(True)
        for idx, btn in enumerate(
            (self._frag_btn, self._works_btn, self._coll_btn)
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
        layout.addWidget(self._frag_btn)
        layout.addWidget(self._works_btn)
        layout.addWidget(self._coll_btn)
        layout.addSpacing(12)
        layout.addWidget(self._search_btn)
        layout.addStretch(1)
        layout.addWidget(self._theme_btn)
        layout.addWidget(self._settings_btn)

        self._frag_btn.setChecked(True)

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
    def works_button(self) -> QPushButton:
        return self._works_btn

    @property
    def collections_button(self) -> QPushButton:
        return self._coll_btn

    @property
    def search_button(self) -> QPushButton:
        return self._search_btn

    @property
    def theme_button(self) -> QPushButton:
        return self._theme_btn

    @property
    def settings_button(self) -> QPushButton:
        return self._settings_btn
