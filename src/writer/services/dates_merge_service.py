"""Helpers for the M-Dates "merge fragments into one draft" flow.

Builds an :class:`AiTaskRequest` from a list of source entries plus the
caller's chosen output type, runs it through :class:`AiTaskService`, and
exposes a save helper that persists the result as a brand-new fragment
without mutating any of the source entries.

The output-type selector is intentionally a small enum local to this
module: prose-draft, work-section-draft, outline. We reuse existing
:class:`AiTaskType` values so we don't introduce new prompt scaffolding.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Sequence

from writer.domain.enums import AiOutputAction, AiTargetKind, AiTaskType
from writer.domain.models.entry import Entry
from writer.services.ai.task_service import AiTaskService
from writer.services.ai.task_types import AiTaskRequest, AiTaskResponse
from writer.storage.repositories.entry_repository import (
    EntryRepository,
    serialize_tags,
)


class MergeOutputType(str, Enum):
    PROSE = "prose"
    SECTION = "section"
    OUTLINE = "outline"


# Maps merge-output choice → underlying AiTaskType. The intent of each
# merge mode is encoded as ``extra_instructions`` so the prompt builder
# does the right thing without us having to add new prompt templates.
_OUTPUT_TO_TASK = {
    MergeOutputType.PROSE: AiTaskType.STYLE_TRANSFER,
    MergeOutputType.SECTION: AiTaskType.CONTINUE,
    MergeOutputType.OUTLINE: AiTaskType.OUTLINE,
}

_OUTPUT_INSTRUCTIONS = {
    MergeOutputType.PROSE: (
        "Merge the following dated fragments into one cohesive prose draft. "
        "Preserve the user's voice and ideas; do not invent new facts. "
        "Smooth transitions and unify tense. Output only the merged prose."
    ),
    MergeOutputType.SECTION: (
        "Merge the following dated fragments into one work-section draft "
        "suitable for inclusion in a longer manuscript. Keep the user's "
        "voice. Use scene-level paragraphs and a single coherent arc. "
        "Output only the merged section text."
    ),
    MergeOutputType.OUTLINE: (
        "Reorganise the following dated fragments into a structured outline. "
        "Group related ideas, surface the implied themes, and keep concrete "
        "lines under their parent bullets. Output a Markdown bullet outline "
        "(use '-' bullets, indentation for sub-points). Do NOT invent ideas "
        "the fragments don't contain."
    ),
}


@dataclass(frozen=True)
class MergeRequestPlan:
    """The data a merge invocation produces *before* it hits the provider.

    Exposed so tests can verify request construction without standing up
    a fake provider.
    """

    request: AiTaskRequest
    source_ids: tuple[str, ...]


def _format_concatenated_bodies(entries: Sequence[Entry]) -> str:
    parts: list[str] = []
    for e in entries:
        title = (e.title or "").strip() or "(untitled)"
        when = (e.created_at or "").split("T")[0]
        parts.append(f"### {title} ({when})\n{e.body or ''}".rstrip())
    return "\n\n".join(parts)


def build_merge_plan(
    entries: Sequence[Entry], output_type: MergeOutputType
) -> MergeRequestPlan:
    """Construct the AI request for merging ``entries`` into one draft."""
    if not entries:
        raise ValueError("no source entries to merge")
    text = _format_concatenated_bodies(entries)
    task_type = _OUTPUT_TO_TASK[output_type]
    instructions = _OUTPUT_INSTRUCTIONS[output_type]
    request = AiTaskRequest(
        task_type=task_type,
        target_kind=AiTargetKind.PASTE,
        text=text,
        extra_instructions=instructions,
        desired_output=AiOutputAction.PREVIEW_ONLY,
    )
    return MergeRequestPlan(
        request=request, source_ids=tuple(e.id for e in entries)
    )


def run_merge(
    service: AiTaskService,
    entries: Sequence[Entry],
    output_type: MergeOutputType,
) -> tuple[AiTaskResponse, MergeRequestPlan]:
    plan = build_merge_plan(entries, output_type)
    response = service.generate(plan.request)
    return response, plan


def save_merged_draft_as_fragment(
    repo: EntryRepository,
    body: str,
    *,
    title: str = "",
    source_ids: Sequence[str] = (),
    extra_tag: str = "merged",
) -> Entry:
    """Persist a merged draft as a new fragment.

    Source IDs are appended to the body in a small footer so we can keep
    provenance without introducing a new schema this milestone. A future
    milestone can replace the footer with a structured ``merge_sources``
    table; the footer format is intentionally easy to grep / migrate.
    """
    if source_ids:
        footer = "\n\n---\nSources: " + ", ".join(source_ids)
        full_body = (body or "").rstrip() + footer
    else:
        full_body = body or ""
    tags = [extra_tag] if extra_tag else []
    entry = repo.create(title=title, body=full_body, tags=tags)
    return entry


__all__ = [
    "MergeOutputType",
    "MergeRequestPlan",
    "build_merge_plan",
    "run_merge",
    "save_merged_draft_as_fragment",
]
