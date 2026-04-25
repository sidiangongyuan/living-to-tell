"""Side-by-side compare dialog for AI rewrites.

Shows the original text on the left and the AI-generated rewrite on the
right. The user must explicitly click *Accept* to apply the change; *Cancel*
discards the rewrite without touching the entry. This is the safety gate
that keeps the original text from being silently overwritten.

*Accept Selection* allows accepting only the text currently selected in the
generated pane — enabling partial adoption of AI output.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from writer.ui.i18n import TR


class AcceptMode(Enum):
    FULL = "full"
    PARTIAL = "partial"


class RewriteCompareDialog(QDialog):
    def __init__(
        self,
        *,
        original_text: str,
        generated_text: str,
        action_label: str,
        provider_label: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(TR("dlg.review_title").format(action=action_label))
        self.resize(900, 540)

        self._accept_mode: AcceptMode = AcceptMode.FULL
        self._accepted_selection: str = ""

        self._generated_edit = QPlainTextEdit(generated_text)

        original_view = QPlainTextEdit(original_text)
        original_view.setReadOnly(True)

        left_box = QVBoxLayout()
        left_box.addWidget(QLabel(TR("compare.original_label")))
        left_box.addWidget(original_view, 1)

        right_box = QVBoxLayout()
        right_label = TR("compare.generated_label_base")
        if provider_label:
            right_label += f"  —  {provider_label}"
        right_box.addWidget(QLabel(right_label))
        right_box.addWidget(self._generated_edit, 1)

        compare_row = QHBoxLayout()
        compare_row.addLayout(left_box, 1)
        compare_row.addLayout(right_box, 1)

        notice = QLabel(TR("compare.notice"))
        notice.setWordWrap(True)
        notice.setObjectName("DialogNote")

        # Button row (manual layout for three buttons)
        self._accept_btn = QPushButton(TR("compare.accept_btn"))
        self._accept_selection_btn = QPushButton(TR("compare.accept_selection_btn"))
        self._accept_selection_btn.setEnabled(False)
        self._accept_selection_btn.setToolTip(TR("compare.accept_selection_tooltip"))
        cancel_btn = QPushButton(TR("compare.cancel_btn"))

        self._accept_btn.clicked.connect(self._on_accept_full)
        self._accept_selection_btn.clicked.connect(self._on_accept_selection)
        cancel_btn.clicked.connect(self.reject)

        self._generated_edit.selectionChanged.connect(
            self._update_accept_selection_btn
        )

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(self._accept_selection_btn)
        btn_row.addWidget(self._accept_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(compare_row, 1)
        layout.addWidget(notice)
        layout.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_accept_full(self) -> None:
        self._accept_mode = AcceptMode.FULL
        self.accept()

    def _on_accept_selection(self) -> None:
        cursor = self._generated_edit.textCursor()
        self._accepted_selection = cursor.selectedText().replace("\u2029", "\n")
        self._accept_mode = AcceptMode.PARTIAL
        self.accept()

    def _update_accept_selection_btn(self) -> None:
        has_sel = self._generated_edit.textCursor().hasSelection()
        self._accept_selection_btn.setEnabled(has_sel)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def accept_mode(self) -> AcceptMode:
        """Return which accept button was clicked."""
        return self._accept_mode

    def accepted_text(self) -> str:
        """Full generated pane text (for full accept)."""
        return self._generated_edit.toPlainText()

    def accepted_selection_text(self) -> str:
        """Selected portion of the generated pane (for partial accept)."""
        return self._accepted_selection
