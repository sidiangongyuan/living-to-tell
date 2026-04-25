"""Work-level orchestration service (M8).

Coordinates the four M8 work-side repositories (work / section / version
/ ref) plus the entry repository so the UI can call a single method for
each user intent. Two responsibilities matter most:

1. ``include_fragment`` is *atomic from the user's point of view*: insert
   the edited fragment text into a section, record the
   ``work_fragment_refs`` row, and bump the source entry's curation tag
   to ``included`` — all inside one ``with conn:`` transaction so a
   failure leaves no half-state.
2. ``save_manual_snapshot`` / ``restore_version`` serialise an entire
   work (header + ordered sections) to a JSON document so a restore can
   reconstruct the exact section structure, not just a flat body string.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import List, Optional

from writer.domain.enums import (
    CurationStatus,
    SectionType,
    WorkVersionType,
)
from writer.domain.models.work import Work
from writer.domain.models.work_fragment_ref import WorkFragmentRef
from writer.domain.models.work_section import WorkSection
from writer.domain.models.work_version import WorkVersion
from writer.storage.repositories.entry_repository import EntryRepository
from writer.storage.repositories.work_fragment_ref_repository import (
    WorkFragmentRefRepository,
)
from writer.storage.repositories.work_repository import WorkRepository
from writer.storage.repositories.work_section_repository import (
    WorkSectionRepository,
)
from writer.storage.repositories.work_version_repository import (
    WorkVersionRepository,
)


SNAPSHOT_FORMAT_VERSION = 1


@dataclass
class IncludeOutcome:
    section: WorkSection
    ref: WorkFragmentRef


@dataclass
class RestoreOutcome:
    work: Work
    sections: List[WorkSection]
    pre_restore_version: WorkVersion


class WorkService:
    def __init__(
        self,
        conn: sqlite3.Connection,
        work_repo: WorkRepository,
        section_repo: WorkSectionRepository,
        ref_repo: WorkFragmentRefRepository,
        version_repo: WorkVersionRepository,
        entry_repo: EntryRepository,
    ) -> None:
        self._conn = conn
        self._works = work_repo
        self._sections = section_repo
        self._refs = ref_repo
        self._versions = version_repo
        self._entries = entry_repo

    # ------------------------------------------------------------------
    # Word count
    # ------------------------------------------------------------------
    def compute_word_count(self, work_id: str) -> int:
        sections = self._sections.list_for_work(work_id)
        return sum(_word_count(s.content) for s in sections)

    # ------------------------------------------------------------------
    # Include-a-fragment: the M8 keystone flow.
    # ------------------------------------------------------------------
    def include_fragment(
        self,
        *,
        work_id: str,
        section_id: Optional[str],
        position: Optional[int],
        edited_text: str,
        entry_id: str,
    ) -> IncludeOutcome:
        """Insert ``edited_text`` into a work and register the link.

        - If ``section_id`` is ``None``, a new body section is appended.
        - If ``position`` is ``None``, the text is appended to the end of
          the section (with one blank line of separation when the
          section is non-empty).
        - The source entry's curation tag flips to ``included``.

        The whole operation is a single transaction.
        """
        if not edited_text:
            raise ValueError("edited_text must not be empty")

        work = self._works.get(work_id)
        if work is None:
            raise ValueError(f"unknown work: {work_id!r}")
        entry = self._entries.get(entry_id)
        if entry is None:
            raise ValueError(f"unknown entry: {entry_id!r}")

        with self._conn:  # commit-or-rollback transaction
            if section_id is None:
                section = self._sections.create(
                    work_id,
                    section_type=SectionType.BODY.value,
                    content=edited_text,
                )
            else:
                existing = self._sections.get(section_id)
                if existing is None or existing.work_id != work_id:
                    raise ValueError(
                        f"section {section_id!r} does not belong to work "
                        f"{work_id!r}"
                    )
                if position is None:
                    body = existing.content or ""
                    sep = "\n\n" if body and not body.endswith("\n") else ""
                    new_body = body + sep + edited_text
                    updated = self._sections.update_content(
                        section_id, new_body
                    )
                else:
                    updated = self._sections.insert_text_at(
                        section_id, position, edited_text
                    )
                assert updated is not None
                section = updated

            ref = self._refs.record(
                work_id=work_id,
                section_id=section.id,
                entry_id=entry_id,
                included_text=edited_text,
            )
            self._entries.set_curation_status(
                entry_id, CurationStatus.INCLUDED.value
            )

        return IncludeOutcome(section=section, ref=ref)

    # ------------------------------------------------------------------
    # Snapshots & restore.
    # ------------------------------------------------------------------
    def save_manual_snapshot(
        self, work_id: str, *, label: str = ""
    ) -> WorkVersion:
        return self._snapshot(
            work_id, version_type=WorkVersionType.MANUAL.value, label=label
        )

    def restore_version(
        self, work_id: str, version_id: str
    ) -> RestoreOutcome:
        target = self._versions.get(version_id)
        if target is None or target.work_id != work_id:
            raise ValueError(
                f"version {version_id!r} not found for work {work_id!r}"
            )
        try:
            payload = json.loads(target.content_json)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"version {version_id!r} has malformed content: {exc}"
            ) from exc

        with self._conn:
            pre = self._snapshot(
                work_id,
                version_type=WorkVersionType.PRE_RESTORE.value,
                label=f"pre-restore {version_id}",
            )
            self._apply_snapshot(work_id, payload)

        work = self._works.get(work_id)
        sections = self._sections.list_for_work(work_id)
        assert work is not None
        return RestoreOutcome(
            work=work, sections=sections, pre_restore_version=pre
        )

    # ------------------------------------------------------------------
    # Internal: serialise / deserialise a snapshot.
    # ------------------------------------------------------------------
    def _snapshot(
        self, work_id: str, *, version_type: str, label: str
    ) -> WorkVersion:
        work = self._works.get(work_id)
        if work is None:
            raise ValueError(f"unknown work: {work_id!r}")
        sections = self._sections.list_for_work(work_id)
        payload = {
            "format": SNAPSHOT_FORMAT_VERSION,
            "work": {
                "title": work.title,
                "summary": work.summary,
                "status": work.status,
                "tags": list(work.tags),
                "target_word_count": work.target_word_count,
            },
            "sections": [
                {
                    "section_type": s.section_type,
                    "content": s.content,
                    "sort_order": s.sort_order,
                }
                for s in sections
            ],
        }
        return self._versions.add(
            work_id=work_id,
            version_type=version_type,
            content_json=json.dumps(payload, ensure_ascii=False),
            label=label,
        )

    def _apply_snapshot(self, work_id: str, payload: dict) -> None:
        head = payload.get("work") or {}
        title = str(head.get("title", ""))
        summary = str(head.get("summary", ""))
        tags = list(head.get("tags") or [])
        status = head.get("status")
        target_wc = head.get("target_word_count")
        self._works.update(
            work_id, title=title, summary=summary, tags=tags
        )
        if isinstance(status, str):
            self._works.set_status(work_id, status)
        if target_wc is None or isinstance(target_wc, int):
            self._works.set_target_word_count(work_id, target_wc)

        for existing in self._sections.list_for_work(work_id):
            self._sections.delete(existing.id)
        for entry in payload.get("sections") or []:
            self._sections.create(
                work_id,
                section_type=str(
                    entry.get("section_type", SectionType.BODY.value)
                ),
                content=str(entry.get("content", "")),
            )


def _word_count(text: str) -> int:
    """Heuristic word counter that handles CJK and latin scripts.

    For latin scripts: count whitespace-separated tokens.
    For CJK: each character counts as one word (industry-standard for
    Chinese word counts in writing tools).
    """
    if not text:
        return 0
    total = 0
    for token in text.split():
        cjk = sum(1 for ch in token if _is_cjk(ch))
        if cjk:
            total += cjk
            # Non-CJK letters in the same token still count as one word
            # if any latin run exists.
            if any(ch.isalnum() and not _is_cjk(ch) for ch in token):
                total += 1
        else:
            total += 1
    return total


def _is_cjk(ch: str) -> bool:
    cp = ord(ch)
    return (
        0x3400 <= cp <= 0x9FFF
        or 0xF900 <= cp <= 0xFAFF
        or 0x20000 <= cp <= 0x2FFFF
    )
