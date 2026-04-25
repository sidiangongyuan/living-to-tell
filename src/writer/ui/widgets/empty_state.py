"""Empty-state card used across panels.

A consistent visual block with a title, description, and up to two CTA
buttons. Replaces the ad-hoc grey "No fragments yet" labels that made
the app feel unfinished.
"""
from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class EmptyStateCard(QFrame):
    """Card with a heading, description, and optional CTA buttons."""

    def __init__(
        self,
        title: str,
        description: str = "",
        *,
        primary_label: Optional[str] = None,
        primary_callback: Optional[Callable[[], None]] = None,
        secondary_label: Optional[str] = None,
        secondary_callback: Optional[Callable[[], None]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("EmptyStateCard")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

        self._title = QLabel(title)
        self._title.setObjectName("EmptyStateTitle")
        self._title.setWordWrap(True)
        self._title.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self._description = QLabel(description)
        self._description.setObjectName("EmptyStateDescription")
        self._description.setWordWrap(True)
        self._description.setVisible(bool(description))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        layout.addWidget(self._title)
        layout.addWidget(self._description)

        # CTA row
        self._primary_btn: Optional[QPushButton] = None
        self._secondary_btn: Optional[QPushButton] = None
        if primary_label or secondary_label:
            row = QHBoxLayout()
            row.setContentsMargins(0, 8, 0, 0)
            row.setSpacing(8)
            if primary_label:
                self._primary_btn = QPushButton(primary_label)
                self._primary_btn.setObjectName("PrimaryButton")
                if primary_callback is not None:
                    self._primary_btn.clicked.connect(primary_callback)
                row.addWidget(self._primary_btn)
            if secondary_label:
                self._secondary_btn = QPushButton(secondary_label)
                self._secondary_btn.setObjectName("GhostButton")
                if secondary_callback is not None:
                    self._secondary_btn.clicked.connect(secondary_callback)
                row.addWidget(self._secondary_btn)
            row.addStretch(1)
            layout.addLayout(row)

    # ------------------------------------------------------------------
    def set_text(self, title: str, description: str = "") -> None:
        self._title.setText(title)
        self._description.setText(description)
        self._description.setVisible(bool(description))

    @property
    def primary_button(self) -> Optional[QPushButton]:
        return self._primary_btn

    @property
    def secondary_button(self) -> Optional[QPushButton]:
        return self._secondary_btn
