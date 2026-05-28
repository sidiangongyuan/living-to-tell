"""Save-selection dialog for style specimens (M-StyleSpecimen)."""
from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from writer.domain.models.reference_passage import (
    USAGE_KINDS,
    ReferencePassage,
    normalise_usage_kind,
)
from writer.storage.repositories.reference_repository import ReferenceRepository
from writer.ui.dialogs.specimen_similarity import rank_similar_passages
from writer.ui.i18n import TR
from writer.ui.widgets.controls import NoWheelComboBox

_USAGE_LABEL_KEYS = {
    "style": "reflib.usage_kind_style",
    "imagery": "reflib.usage_kind_imagery",
    "technique": "reflib.usage_kind_technique",
    "character": "reflib.usage_kind_character",
    "setting": "reflib.usage_kind_setting",
    "psychology": "reflib.usage_kind_psychology",
    "philosophy": "reflib.usage_kind_philosophy",
    "reflection": "reflib.usage_kind_reflection",
    "other": "reflib.usage_kind_other",
}


def _usage_kind_label(value: str) -> str:
    return TR(_USAGE_LABEL_KEYS.get(value, "reflib.usage_kind_style"))


class SaveSpecimenDialog(QDialog):
    def __init__(
        self,
        repo: ReferenceRepository,
        *,
        default_body: str,
        default_source_title: str = "",
        default_source_author: str = "",
        default_tags: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._repo = repo
        self.saved_passage: Optional[ReferencePassage] = None

        self.setWindowTitle(TR("specimen.save_dialog_title"))
        self.resize(720, 620)

        self._title_edit = QLineEdit(default_source_title)
        self._author_edit = QLineEdit(default_source_author)
        self._tags_edit = QLineEdit(default_tags)
        self._usage_kind_combo = NoWheelComboBox()
        for usage_kind in USAGE_KINDS:
            self._usage_kind_combo.addItem(_usage_kind_label(usage_kind), usage_kind)
        self._note_edit = QPlainTextEdit()
        self._note_edit.setPlaceholderText(TR("reflib.personal_note_label"))
        self._note_edit.setMaximumHeight(90)
        self._body_edit = QPlainTextEdit(default_body)
        self._body_edit.setMinimumHeight(180)
        self._duplicate_label = QLabel("")
        self._duplicate_label.setObjectName("SpecimenDuplicateLabel")
        self._duplicate_label.setWordWrap(True)

        self._similar_list = QListWidget()
        self._similar_list.setObjectName("SpecimenSimilarList")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(TR("specimen.save_btn"))
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        title_row = QHBoxLayout()
        title_row.addWidget(QLabel(TR("rlp.source_title_label")))
        title_row.addWidget(self._title_edit, 1)

        author_row = QHBoxLayout()
        author_row.addWidget(QLabel(TR("rlp.author_label")))
        author_row.addWidget(self._author_edit, 1)

        tags_row = QHBoxLayout()
        tags_row.addWidget(QLabel(TR("rlp.tags_label")))
        tags_row.addWidget(self._tags_edit, 1)

        usage_row = QHBoxLayout()
        usage_row.addWidget(QLabel(TR("reflib.usage_kind_label")))
        usage_row.addWidget(self._usage_kind_combo, 1)

        layout = QVBoxLayout(self)
        layout.addLayout(title_row)
        layout.addLayout(author_row)
        layout.addLayout(tags_row)
        layout.addLayout(usage_row)
        layout.addWidget(QLabel(TR("reflib.personal_note_label")))
        layout.addWidget(self._note_edit)
        layout.addWidget(QLabel(TR("specimen.body_label")))
        layout.addWidget(self._body_edit, 1)
        layout.addWidget(self._duplicate_label)
        layout.addWidget(QLabel(TR("specimen.similar_label")))
        layout.addWidget(self._similar_list, 1)
        layout.addWidget(buttons)

        self._body_edit.textChanged.connect(self._refresh_similar)
        self._refresh_similar()

    def _refresh_similar(self) -> None:
        text = self._body_edit.toPlainText().strip()
        self._similar_list.clear()
        if not text:
            self._duplicate_label.setText("")
            return

        duplicate = self._repo.find_exact_duplicate(text)
        if duplicate is not None:
            self._duplicate_label.setText(
                TR("specimen.duplicate_exact").format(title=duplicate.display_label())
            )
        else:
            self._duplicate_label.setText(TR("specimen.duplicate_clear"))

        results = rank_similar_passages(self._repo.list_recent(limit=500), text, limit=6)

        for passage in results:
            item = QListWidgetItem(
                f"{passage.display_label()}  [{_usage_kind_label(passage.usage_kind)}]"
            )
            tip = passage.content[:280]
            if passage.personal_note:
                tip += f"\n\nNote: {passage.personal_note[:180]}"
            item.setToolTip(tip)
            item.setData(0x0100, passage.id)
            self._similar_list.addItem(item)

    def _on_accept(self) -> None:
        title = self._title_edit.text().strip()
        body = self._body_edit.toPlainText()
        if not title:
            QMessageBox.warning(self, TR("rlp.missing_title"), TR("rlp.missing_title_msg"))
            return
        if not body.strip():
            QMessageBox.warning(self, TR("rlp.missing_content"), TR("rlp.missing_content_msg"))
            return
        duplicate = self._repo.find_exact_duplicate(body)
        if duplicate is not None:
            QMessageBox.warning(
                self,
                TR("specimen.duplicate_title"),
                TR("specimen.duplicate_msg").format(title=duplicate.display_label()),
            )
            return
        try:
            self.saved_passage = self._repo.create(
                source_title=title,
                source_author=self._author_edit.text(),
                content=body,
                tags=self._tags_edit.text(),
                usage_kind=normalise_usage_kind(self._usage_kind_combo.currentData()),
                personal_note=self._note_edit.toPlainText(),
            )
        except ValueError as exc:
            QMessageBox.warning(self, TR("rlp.invalid_ref"), str(exc))
            return
        self.accept()
