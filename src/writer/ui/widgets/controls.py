"""Small shared control variants used across Writer's desktop UI."""

from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QDoubleSpinBox, QSpinBox


class NoWheelComboBox(QComboBox):
    """Combo box that ignores accidental wheel changes while scrolling."""

    def wheelEvent(self, event) -> None:  # noqa: N802
        event.ignore()


class NoWheelSpinBox(QSpinBox):
    """Spin box that ignores accidental wheel changes while scrolling."""

    def wheelEvent(self, event) -> None:  # noqa: N802
        event.ignore()


class NoWheelDoubleSpinBox(QDoubleSpinBox):
    """Double spin box that ignores accidental wheel changes while scrolling."""

    def wheelEvent(self, event) -> None:  # noqa: N802
        event.ignore()
