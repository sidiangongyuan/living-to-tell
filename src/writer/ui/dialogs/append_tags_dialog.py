"""Tiny dialog: append a comma-separated tag list to N selected entries."""
from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from writer.ui.i18n import TR


class AppendTagsDialog(QDialog):
    def __init__(
        self, count: int, parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(TR("dates.append_tags_title"))
        self.setObjectName("AppendTagsDialog")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(TR("dates.append_tags_msg").format(count=count)))
        self._edit = QLineEdit()
        self._edit.setPlaceholderText("tag1, tag2")
        layout.addWidget(self._edit)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def tags(self) -> list[str]:
        raw = self._edit.text()
        return [t.strip() for t in raw.split(",") if t.strip()]

    # Test-friendly setter so unit tests don't need to simulate keyboard input.
    def set_tags_text(self, text: str) -> None:
        self._edit.setText(text)
