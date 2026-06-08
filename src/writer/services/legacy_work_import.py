"""One-shot import from legacy Works into article collections."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Optional

from writer.domain.enums import SectionType
from writer.storage.repositories.collection_repository import CollectionRepository
from writer.storage.repositories.entry_repository import EntryRepository
from writer.storage.repositories.settings_repository import SettingsRepository


LEGACY_WORK_IMPORT_SENTINEL = "legacy_works.imported_to_articles_v1"


@dataclass(frozen=True)
class LegacyWorkImportSummary:
    works_seen: int
    sections_seen: int
    entries_created: int
    collections_created: int


class LegacyWorkImportService:
    def __init__(
        self,
        conn: sqlite3.Connection,
        settings: SettingsRepository,
        entries: EntryRepository,
        collections: CollectionRepository,
    ) -> None:
        self._conn = conn
        self._settings = settings
        self._entries = entries
        self._collections = collections

    def already_imported(self) -> bool:
        return self._settings.get(LEGACY_WORK_IMPORT_SENTINEL) == "1"

    def needs_import(self) -> bool:
        if self.already_imported():
            return False
        row = self._conn.execute("SELECT COUNT(*) AS n FROM works").fetchone()
        return int(row["n"]) > 0

    def mark_skipped(self) -> None:
        self._settings.set(LEGACY_WORK_IMPORT_SENTINEL, "1")

    def import_once(self) -> LegacyWorkImportSummary:
        if self.already_imported():
            return LegacyWorkImportSummary(0, 0, 0, 0)

        works = self._conn.execute(
            "SELECT * FROM works ORDER BY created_at ASC, updated_at ASC"
        ).fetchall()
        work_collection_ids: dict[str, str] = {}
        section_entry_ids: dict[str, str] = {}
        entries_created = 0
        collections_created = 0
        sections_seen = 0

        for work in works:
            collection_name = work["title"] or "Untitled collection"
            collection = self._collections.create(
                name=collection_name,
                description=work["summary"] or "",
            )
            collections_created += 1
            work_collection_ids[work["id"]] = collection.id

            sections = self._conn.execute(
                "SELECT * FROM work_sections WHERE work_id = ? "
                "ORDER BY sort_order ASC, created_at ASC",
                (work["id"],),
            ).fetchall()
            for index, section in enumerate(sections, start=1):
                sections_seen += 1
                title = _section_title(work["title"] or "", section["content"] or "", index)
                entry = self._entries.create(
                    title=title,
                    body=section["content"] or "",
                    tags=_parse_tags(work["tags_text"] or ""),
                )
                entries_created += 1
                section_entry_ids[section["id"]] = entry.id
                self._collections.add_entry(collection.id, entry.id)

        legacy_collections = self._conn.execute(
            "SELECT * FROM collections ORDER BY created_at ASC"
        ).fetchall()
        for legacy in legacy_collections:
            legacy_items = self._conn.execute(
                "SELECT work_id FROM collection_items WHERE collection_id = ? "
                "ORDER BY sort_order ASC, created_at ASC",
                (legacy["id"],),
            ).fetchall()
            if not legacy_items:
                continue
            target = self._find_or_create_collection(
                legacy["name"] or "Untitled collection",
                legacy["description"] or "",
                exclude_id=legacy["id"],
            )
            if target[1]:
                collections_created += 1
            for item in legacy_items:
                for entry_id in self._entry_ids_for_work(item["work_id"], section_entry_ids):
                    self._collections.add_entry(target[0], entry_id)

        self._settings.set(LEGACY_WORK_IMPORT_SENTINEL, "1")
        return LegacyWorkImportSummary(
            works_seen=len(works),
            sections_seen=sections_seen,
            entries_created=entries_created,
            collections_created=collections_created,
        )

    def _find_or_create_collection(
        self,
        name: str,
        description: str,
        *,
        exclude_id: Optional[str] = None,
    ) -> tuple[str, bool]:
        rows = self._conn.execute(
            "SELECT * FROM collections WHERE name = ? ORDER BY created_at ASC",
            (name,),
        ).fetchall()
        for row in rows:
            if row["id"] != exclude_id:
                return row["id"], False
        collection = self._collections.create(name=name, description=description)
        return collection.id, True

    def _entry_ids_for_work(
        self,
        work_id: str,
        section_entry_ids: dict[str, str],
    ) -> list[str]:
        sections = self._conn.execute(
            "SELECT id FROM work_sections WHERE work_id = ? "
            "ORDER BY sort_order ASC, created_at ASC",
            (work_id,),
        ).fetchall()
        return [
            section_entry_ids[row["id"]]
            for row in sections
            if row["id"] in section_entry_ids
        ]


def _section_title(work_title: str, content: str, index: int) -> str:
    compact = content.strip()
    first_line = compact.splitlines()[0].strip() if compact else ""
    if first_line and len(first_line) <= 42 and not first_line.endswith(("。", ".", "！", "?", "？")):
        return first_line
    base = work_title.strip() or "Untitled work"
    return f"{base} · {index}"


def _parse_tags(tags_text: str) -> list[str]:
    seen: set[str] = set()
    tags: list[str] = []
    for raw in tags_text.split(","):
        tag = raw.strip()
        if tag and tag.lower() not in seen:
            seen.add(tag.lower())
            tags.append(tag)
    return tags
