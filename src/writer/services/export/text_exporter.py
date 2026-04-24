"""Plain-text exporter (M5).

Mirrors :class:`MarkdownExporter` but emits plain text with
underline-style separators. No Markdown syntax, no rich styling.
"""
from __future__ import annotations

from typing import List, Optional

from writer.domain.models.chapter import Chapter
from writer.domain.models.entry import Entry
from writer.domain.models.project import Project
from writer.storage.repositories.chapter_repository import ChapterRepository
from writer.storage.repositories.entry_repository import EntryRepository


UNCHAPTERED_HEADING = "Unchaptered"


class TextExporter:
    def __init__(
        self,
        entry_repo: EntryRepository,
        chapter_repo: ChapterRepository,
    ) -> None:
        self._entries = entry_repo
        self._chapters = chapter_repo

    def export_entry(self, entry: Entry) -> str:
        return self._render_entry(entry, underline="=") + "\n"

    def export_project(
        self,
        project: Project,
        *,
        chapters: Optional[List[Chapter]] = None,
    ) -> str:
        chapters_ = (
            chapters
            if chapters is not None
            else self._chapters.list_for_project(project.id)
        )

        sections: list[str] = []
        header = project.name
        sections.append(f"{header}\n{'=' * max(1, len(header))}")
        if project.description.strip():
            sections.append(project.description.strip())

        for chapter in chapters_:
            chapter_entries = self._entries.list_for_chapter(chapter.id)
            if not chapter_entries and not chapter.title.strip():
                continue
            chapter_title = chapter.title.strip() or "Untitled chapter"
            sections.append(f"{chapter_title}\n{'-' * max(1, len(chapter_title))}")
            for entry in chapter_entries:
                sections.append(self._render_entry(entry, underline="~"))

        orphans = self._entries.list_unchaptered_for_project(project.id)
        if orphans:
            sections.append(f"{UNCHAPTERED_HEADING}\n{'-' * len(UNCHAPTERED_HEADING)}")
            for entry in orphans:
                sections.append(self._render_entry(entry, underline="~"))

        return "\n\n".join(sections).rstrip() + "\n"

    @staticmethod
    def _render_entry(entry: Entry, *, underline: str) -> str:
        title = entry.title.strip() or "Untitled"
        body = entry.body.rstrip()
        parts = [title, underline * max(1, len(title))]
        if body:
            parts.append("")
            parts.append(body)
        return "\n".join(parts)
