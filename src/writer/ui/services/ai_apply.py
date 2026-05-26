"""Safe write-back helpers for the M10A AI workspace.

These helpers wrap the AI task service result around the existing safety
rails: a snapshot is always written before any destructive write, and the
caller picks the destination explicitly. The functions return small result
objects so the UI can show a clear acknowledgement.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from writer.app.container import AppContainer
from writer.domain.enums import (
    AiOutputAction,
    AiTaskType,
    RewriteAction,
    VersionType,
)


# Mapping AI tasks onto the legacy version-history action vocabulary so the
# fragment write-back path keeps producing a meaningful version label.
_TASK_TO_REWRITE_ACTION: dict[AiTaskType, RewriteAction] = {
    AiTaskType.POLISH: RewriteAction.POLISH,
    AiTaskType.EXPAND: RewriteAction.EXPAND,
    AiTaskType.CONTINUE: RewriteAction.CONTINUE,
}


@dataclass(frozen=True)
class ApplyOutcome:
    """Lightweight description of what the safe-apply helper did."""

    kind: str  # "selection" | "fragment" | "section" | "save_as_fragment"
    target_label: str
    snapshot_taken: bool
    restore_version_id: Optional[str] = None
    new_body: Optional[str] = None
    new_fragment_id: Optional[str] = None


def apply_to_fragment(
    container: AppContainer,
    *,
    entry_id: str,
    task_type: AiTaskType,
    original_full_body: str,
    selection_start: Optional[int],
    selection_end: Optional[int],
    generated_text: str,
    title: str,
    provider_name: str,
    model: str,
) -> ApplyOutcome:
    """Replace fragment text or selection, with version snapshots first.

    Re-uses the existing :class:`RewriteService.apply_acceptance` pathway
    when the task type maps onto a legacy rewrite action, so version
    history stays unified. For other task types we still snapshot before
    writing but tag the AI version with a generic ``AI_OTHER`` label.
    """

    rewrite_action = _TASK_TO_REWRITE_ACTION.get(task_type)
    if rewrite_action is not None:
        outcome = container.rewrite_service.apply_acceptance(
            entry_id=entry_id,
            action=rewrite_action,
            original_full_body=original_full_body,
            selection_start=selection_start,
            selection_end=selection_end,
            generated_text=generated_text,
            title=title,
            provider=provider_name,
            model=model,
        )
        kind = "selection" if selection_start is not None else "fragment"
        return ApplyOutcome(
            kind=kind,
            target_label=title or "(untitled)",
            snapshot_taken=True,
            restore_version_id=outcome.snapshot_version_id,
            new_body=outcome.new_body,
        )

    # Generic path: snapshot ORIGINAL then write the AI body without a
    # specialised version label.
    if selection_start is not None and selection_end is not None:
        new_body = (
            original_full_body[:selection_start]
            + generated_text
            + original_full_body[selection_end:]
        )
        kind = "selection"
    else:
        new_body = generated_text
        kind = "fragment"

    original_version = container.version_repository.add(
        entry_id=entry_id,
        version_type=VersionType.ORIGINAL.value,
        content=original_full_body,
    )
    container.version_repository.add(
        entry_id=entry_id,
        version_type=VersionType.AI_OTHER.value,
        content=generated_text,
        provider=provider_name,
        model=model,
    )
    container.entry_repository.update(entry_id, title=title, body=new_body)
    return ApplyOutcome(
        kind=kind,
        target_label=title or "(untitled)",
        snapshot_taken=True,
        restore_version_id=original_version.id,
        new_body=new_body,
    )


def apply_to_section(
    container: AppContainer,
    *,
    work_id: str,
    section_id: str,
    generated_text: str,
    original_section_body: Optional[str] = None,
    selection_start: Optional[int] = None,
    selection_end: Optional[int] = None,
    snapshot_label: str = "pre-ai",
) -> ApplyOutcome:
    """Replace a work section body or selected range after taking a snapshot."""

    container.work_service.save_manual_snapshot(work_id, label=snapshot_label)
    if (
        original_section_body is not None
        and selection_start is not None
        and selection_end is not None
    ):
        start = max(0, min(len(original_section_body), selection_start))
        end = max(start, min(len(original_section_body), selection_end))
        generated_text = (
            original_section_body[:start]
            + generated_text
            + original_section_body[end:]
        )
    section = container.work_section_repository.update_content(
        section_id, generated_text
    )
    label = section_id if section is None else section_id[:8]
    return ApplyOutcome(
        kind="selection" if selection_start is not None else "section",
        target_label=label,
        snapshot_taken=True,
    )


def save_as_new_fragment(
    container: AppContainer,
    *,
    title: str,
    body: str,
) -> ApplyOutcome:
    """Persist *body* as a brand-new fragment and return its identifier."""

    entry = container.entry_repository.create(title=title, body=body)
    return ApplyOutcome(
        kind="save_as_fragment",
        target_label=title or "(untitled)",
        snapshot_taken=False,
        new_fragment_id=entry.id,
    )
