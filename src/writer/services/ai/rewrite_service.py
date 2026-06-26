"""Coordinates a rewrite call.

The service does **not** silently overwrite ``entries.body``. Per the M3
contract (docs/agent-kickoff-prompt.md §10 and basic-design), the original
text must remain visible until the user explicitly accepts a generated
rewrite. Therefore this service only generates text; persistence happens in
``apply_acceptance``, which the UI calls **after** the user clicks Accept.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from writer.domain.enums import RewriteAction, VersionType
from writer.services.ai.interfaces import (
    AiProvider,
    RewriteRequest,
    RewriteResponse,
)
from writer.storage.repositories.entry_repository import EntryRepository
from writer.storage.repositories.version_repository import VersionRepository


_ACTION_TO_VERSION: dict[RewriteAction, VersionType] = {
    RewriteAction.POLISH: VersionType.AI_POLISH,
    RewriteAction.EXPAND: VersionType.AI_EXPAND,
    RewriteAction.CONTINUE: VersionType.AI_CONTINUE,
}


@dataclass
class AcceptanceOutcome:
    new_body: str
    version_id: str
    snapshot_version_id: str


class RewriteService:
    def __init__(
        self,
        entry_repository: EntryRepository,
        version_repository: VersionRepository,
        provider_factory,
    ) -> None:
        self._entries = entry_repository
        self._versions = version_repository
        self._provider_factory = provider_factory

    def generate(self, request: RewriteRequest) -> RewriteResponse:
        provider: AiProvider = self._provider_factory()
        return provider.rewrite(request)

    def apply_acceptance(
        self,
        *,
        entry_id: str,
        action: RewriteAction,
        original_full_body: str,
        selection_start: Optional[int],
        selection_end: Optional[int],
        generated_text: str,
        title: str,
        provider: str,
        model: str,
    ) -> AcceptanceOutcome:
        """Replace original text with ``generated_text`` and record versions.

        Behaviour:
        * ``CONTINUE`` with no selection: append generated text to the body.
        * Selection range given: replace only that span.
        * Otherwise: replace the whole body.

        A snapshot of the original body is always written to
        ``entry_versions`` first, so the original remains recoverable.
        """
        if action is RewriteAction.CONTINUE and selection_start is None:
            new_body = original_full_body + generated_text
        elif selection_start is not None and selection_end is not None:
            new_body = (
                original_full_body[:selection_start]
                + generated_text
                + original_full_body[selection_end:]
            )
        else:
            new_body = generated_text

        original_version = self._versions.add(
            entry_id=entry_id,
            version_type=VersionType.ORIGINAL.value,
            content=original_full_body,
            title_snapshot=title,
            reason="ai_original",
        )
        ai_version = self._versions.add(
            entry_id=entry_id,
            version_type=_ACTION_TO_VERSION[action].value,
            content=generated_text,
            provider=provider,
            model=model,
        )
        self._entries.update(entry_id, title=title, body=new_body)
        return AcceptanceOutcome(
            new_body=new_body,
            version_id=ai_version.id,
            snapshot_version_id=original_version.id,
        )
