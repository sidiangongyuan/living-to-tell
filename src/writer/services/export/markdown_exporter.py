"""Markdown exporter (M5).

Produces a Markdown document from either a single fragment or a whole
project. Only the currently accepted body (``entries.body``) is emitted —
AI version history stored in ``entry_versions`` is never included.

Project export order
--------------------
* Chapters are emitted in ``chapters.sort_order`` ascending.
* Inside a chapter, entries follow ``entries.sequence_order`` ascending
  (an explicit order the user can reshuffle in the Projects dialog).
* Entries that have no chapter are gathered into a final "Unchaptered"
  section, also ordered by ``sequence_order``.
* The exporter never uses ``updated_at`` as a sort key — editing the
  body or title of an entry must not change where it appears in an
  exported manuscript.
"""
from __future__ import annotations

from typing import List, Optional

from writer.domain.models.chapter import Chapter
from writer.domain.models.entry import Entry
from writer.domain.models.project import Project
from writer.storage.repositories.chapter_repository import ChapterRepository
from writer.storage.repositories.entry_repository import EntryRepository


UNCHAPTERED_HEADING = "Unchaptered"


class MarkdownExporter:
    def __init__(
        self,
        entry_repo: EntryRepository,
        chapter_repo: ChapterRepository,
    ) -> None:
        self._entries = entry_repo
        self._chapters = chapter_repo

    def export_entry(self, entry: Entry) -> str:
        return self._render_entry(entry, heading_level=1) + "\n"

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

        lines: list[str] = [f"# {project.name}"]
        if project.description.strip():
            lines.append("")
            lines.append(project.description.strip())

        for chapter in chapters_:
            chapter_entries = self._entries.list_for_chapter(chapter.id)
            if not chapter_entries and not chapter.title.strip():
                continue
            lines.append("")
            lines.append(f"## {chapter.title.strip() or 'Untitled chapter'}")
            for entry in chapter_entries:
                lines.append("")
                lines.append(self._render_entry(entry, heading_level=3))

        orphans = self._entries.list_unchaptered_for_project(project.id)
        if orphans:
            lines.append("")
            lines.append(f"## {UNCHAPTERED_HEADING}")
            for entry in orphans:
                lines.append("")
                lines.append(self._render_entry(entry, heading_level=3))

        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def _render_entry(entry: Entry, *, heading_level: int) -> str:
        heading_prefix = "#" * max(1, min(6, heading_level))
        title = entry.title.strip() or "Untitled"
        body = entry.body.rstrip()
        parts = [f"{heading_prefix} {title}"]
        if body:
            parts.append("")
            parts.append(body)
        return "\n".join(parts)
