"""Generic AI task DTOs (M10A).

The legacy ``RewriteRequest`` / ``RewriteResponse`` in :mod:`interfaces`
remain for backward compatibility — the existing fragment polish/expand/
continue menu still uses them, and the task service adapts polish/expand/
continue tasks down to the same provider call.

This module introduces the wider task model used by the AI workspace:
arbitrary task type, target kind, parameter bag, attachments, structured
result.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from writer.domain.enums import (
    AiCostTier,
    AiOutputAction,
    AiTargetKind,
    AiTaskType,
)


@dataclass
class AiContextAttachment:
    """A piece of context the user explicitly attached to a task or message.

    ``size_chars`` is the rough character count we use as a token-budget
    proxy. Attachments are user-controlled — nothing is auto-injected.
    """

    kind: str  # 'fragment' | 'work' | 'work_section' | 'card_style' |
               # 'card_character' | 'card_setting' | 'reference'
    ref_id: str  # the source object id (or card id)
    name: str
    body: str

    @property
    def size_chars(self) -> int:
        return len(self.body)


@dataclass
class AiTaskRequest:
    task_type: AiTaskType
    target_kind: AiTargetKind
    text: str  # the primary subject text (selection / fragment body / section / pasted)
    target_ref_id: Optional[str] = None  # source object id when applicable
    style: Optional[str] = None
    intensity: Optional[str] = None  # 'light' | 'medium' | 'strong'
    extra_instructions: Optional[str] = None
    max_output_chars: Optional[int] = None
    preserve_meaning: bool = True
    preserve_voice: bool = True
    forbid_terms: List[str] = field(default_factory=list)
    must_keep_terms: List[str] = field(default_factory=list)
    attachments: List[AiContextAttachment] = field(default_factory=list)
    cost_tier: AiCostTier = AiCostTier.BALANCED
    desired_output: AiOutputAction = AiOutputAction.PREVIEW_ONLY
    expect_structured: bool = False

    def estimated_context_chars(self) -> int:
        size = len(self.text)
        for a in self.attachments:
            size += a.size_chars
        if self.extra_instructions:
            size += len(self.extra_instructions)
        return size


@dataclass
class AiCitation:
    """A 'where this answer came from' anchor for library QA."""

    kind: str  # 'fragment' | 'work' | 'work_section' | 'reference'
    ref_id: str
    name: str
    excerpt: str


@dataclass
class AiTaskResponse:
    content: str  # primary text result (always populated)
    structured: Optional[Dict[str, Any]] = None  # parsed JSON for diagnostic / qa tasks
    citations: List[AiCitation] = field(default_factory=list)
    model: str = ""
    provider: str = ""
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    finish_reason: Optional[str] = None
    transport: Optional[str] = None
    cost: Optional[float] = None


@dataclass
class AiRunMetadata:
    """Runtime info attached to messages / results for replay / inspection."""

    task_type: Optional[str] = None
    target_kind: Optional[str] = None
    target_ref_id: Optional[str] = None
    cost_tier: Optional[str] = None
    model: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    cost: Optional[float] = None
    citations: List[Dict[str, str]] = field(default_factory=list)
