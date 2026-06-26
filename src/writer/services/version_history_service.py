"""Service layer for reading and safely restoring entry version history.

Design rules (M5D):
  * Restore only replaces ``entry.body``; title, project_id, chapter_id, and
    sequence_order are never touched.
  * Before overwriting the live body the service writes a
    ``MANUAL_SNAPSHOT`` version so the user can undo the restore.
  * Restoring a version whose content is identical to the current body is a
    no-op — no duplicate snapshot is written.
  * Restoring a non-existent version_id raises ``ValueError``.
  * This service never mutates existing version rows; history is append-only.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from writer.domain.enums import VersionType
from writer.domain.models.entry_version import EntryVersion
from writer.storage.repositories.entry_repository import EntryRepository
from writer.storage.repositories.version_repository import VersionRepository


# Human-readable labels for each version type shown in the history UI.
_VERSION_LABELS: dict[str, str] = {
    VersionType.ORIGINAL.value: "Original",
    VersionType.AI_POLISH.value: "AI Polish",
    VersionType.AI_EXPAND.value: "AI Expand",
    VersionType.AI_CONTINUE.value: "AI Continue",
    VersionType.AI_BEFORE_APPLY.value: "Before AI Apply",
    VersionType.MANUAL_CHECKPOINT.value: "Checkpoint",
    VersionType.MANUAL_SNAPSHOT.value: "Snapshot (pre-restore)",
}


@dataclass
class RestoreOutcome:
    """Result of a successful restore operation."""

    new_body: str
    snapshot_version_id: Optional[str]
    """ID of the protective snapshot written before restore.
    ``None`` if the restore was a no-op (content identical)."""
    was_noop: bool


class VersionHistoryService:
    def __init__(
        self,
        entry_repository: EntryRepository,
        version_repository: VersionRepository,
    ) -> None:
        self._entries = entry_repository
        self._versions = version_repository

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def list_history(self, entry_id: str) -> List[EntryVersion]:
        """Return all versions for *entry_id* newest-first."""
        return self._versions.list_for_entry(entry_id)

    @staticmethod
    def version_type_label(version_type: str) -> str:
        """Return a user-friendly label for a raw version_type string."""
        return _VERSION_LABELS.get(version_type, version_type)

    def save_manual_checkpoint(self, entry_id: str, *, label: str = "") -> EntryVersion:
        """Persist the current live body as a user-requested checkpoint."""
        entry = self._entries.get(entry_id)
        if entry is None:
            raise ValueError(f"Entry {entry_id!r} not found")
        return self._versions.add(
            entry_id=entry_id,
            version_type=VersionType.MANUAL_CHECKPOINT.value,
            content=entry.body,
            title_snapshot=entry.title,
            tags_snapshot=", ".join(entry.tags),
            label=label,
            reason="manual",
        )

    def save_ai_before_apply(
        self,
        entry_id: str,
        *,
        label: str = "",
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> EntryVersion:
        """Persist the live body before an AI result is written back."""
        entry = self._entries.get(entry_id)
        if entry is None:
            raise ValueError(f"Entry {entry_id!r} not found")
        return self._versions.add(
            entry_id=entry_id,
            version_type=VersionType.AI_BEFORE_APPLY.value,
            content=entry.body,
            title_snapshot=entry.title,
            tags_snapshot=", ".join(entry.tags),
            label=label,
            reason="ai_before_apply",
            provider=provider,
            model=model,
        )

    def delete_version(self, entry_id: str, version_id: str) -> None:
        """Delete one stored version row for *entry_id*."""
        if not self._versions.delete(version_id, entry_id=entry_id):
            raise ValueError(
                f"Version {version_id!r} not found for entry {entry_id!r}"
            )

    # ------------------------------------------------------------------
    # Restore
    # ------------------------------------------------------------------

    def restore(self, entry_id: str, version_id: str) -> RestoreOutcome:
        """Restore the body from *version_id* to the live entry.

        Raises
        ------
        ValueError
            If *version_id* does not exist or does not belong to *entry_id*.
        """
        version = self._versions.get(version_id)
        if version is None or version.entry_id != entry_id:
            raise ValueError(
                f"Version {version_id!r} not found for entry {entry_id!r}"
            )

        entry = self._entries.get(entry_id)
        if entry is None:
            raise ValueError(f"Entry {entry_id!r} not found")

        target_body = version.content

        # No-op: live body already matches the target.
        if entry.body == target_body:
            return RestoreOutcome(
                new_body=entry.body,
                snapshot_version_id=None,
                was_noop=True,
            )

        # Protect the current live body in a MANUAL_SNAPSHOT before overwriting.
        snapshot = self._versions.add(
            entry_id=entry_id,
            version_type=VersionType.MANUAL_SNAPSHOT.value,
            content=entry.body,
            title_snapshot=entry.title,
            tags_snapshot=", ".join(entry.tags),
            reason="pre_restore",
        )

        # Write the restored body; title stays unchanged.
        self._entries.update(entry_id, title=entry.title, body=target_body)

        return RestoreOutcome(
            new_body=target_body,
            snapshot_version_id=snapshot.id,
            was_noop=False,
        )
