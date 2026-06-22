"""Domain enums shared across layers."""
from __future__ import annotations

from enum import Enum


class EntryType(str, Enum):
    FRAGMENT = "fragment"


class VersionType(str, Enum):
    """Why a version row exists. Only ``ORIGINAL`` is used in M2;
    AI-generated variants land in M3; ``MANUAL_SNAPSHOT`` is written by
    the version-history restore flow (M5D) before overwriting the live body;
    ``MANUAL_CHECKPOINT`` is an explicit user-created fragment snapshot."""

    ORIGINAL = "original"
    AI_POLISH = "ai_polish"
    AI_EXPAND = "ai_expand"
    AI_CONTINUE = "ai_continue"
    AI_OTHER = "ai_other"
    MANUAL_SNAPSHOT = "manual_snapshot"
    MANUAL_CHECKPOINT = "manual_checkpoint"


class RewriteAction(str, Enum):
    """Placeholder for M3."""

    POLISH = "polish"
    EXPAND = "expand"
    CONTINUE = "continue"


# ---------------------------------------------------------------------------
# Milestone 8 — works, sections, curation status.
# ---------------------------------------------------------------------------


class WorkStatus(str, Enum):
    """Lifecycle states for a finished-piece "work" (M8)."""

    IDEA = "idea"          # 构思中
    DRAFT = "draft"        # 草稿
    REVISING = "revising"  # 修改中
    FINAL = "final"        # 定稿
    ARCHIVED = "archived"  # 归档

    @classmethod
    def values(cls) -> list[str]:
        return [m.value for m in cls]


class SectionType(str, Enum):
    """Section block kinds inside a work (M8 v1)."""

    BODY = "body"        # 正文块
    HEADING = "heading"  # 小标题块


class WorkVersionType(str, Enum):
    """Why a work version row exists (M8)."""

    MANUAL = "manual"          # 手动保存
    AI_ACCEPTED = "ai_accepted"  # 接受 AI 改写
    PRE_RESTORE = "pre_restore"  # 恢复前自动快照（防丢）


class CurationStatus(str, Enum):
    """Lightweight per-fragment curation tag (M8 §10)."""

    UNSORTED = "unsorted"    # 未整理
    INCLUDED = "included"    # 已纳入
    PARKING = "parking"      # 暂存
    DISCARDED = "discarded"  # 废弃

    @classmethod
    def values(cls) -> list[str]:
        return [m.value for m in cls]



# ---------------------------------------------------------------------------
# Milestone 10A — AI workspace task model.
# ---------------------------------------------------------------------------


class AiTaskType(str, Enum):
    """Structured AI task taxonomy used by the AI workspace.

    ``polish``/``expand``/``continue`` are kept aligned with
    :class:`RewriteAction` so the legacy quick-rewrite menu can dispatch
    through the same engine without breaking compatibility.
    """

    POLISH = "polish"
    EXPAND = "expand"
    CONTINUE = "continue"
    STYLE_TRANSFER = "style_transfer"
    SUMMARIZE = "summarize"
    OUTLINE = "outline"
    TITLE = "title"
    STRUCTURE_DIAGNOSE = "structure_diagnose"
    CONSISTENCY_CHECK = "consistency_check"
    LIBRARY_QA = "library_qa"


class AiTargetKind(str, Enum):
    """What the task operates on."""

    SELECTION = "selection"            # current text selection inside a fragment
    FRAGMENT = "fragment"              # entire fragment body
    WORK_SECTION = "work_section"      # one section inside a work
    WORK = "work"                      # whole work (read-only by default)
    COLLECTION = "collection"          # whole collection (read-only)
    PASTE = "paste"                    # ad-hoc text the user pastes in


class AiOutputAction(str, Enum):
    """Where a task's primary result is allowed to land."""

    PREVIEW_ONLY = "preview_only"
    REPLACE_SELECTION = "replace_selection"
    REPLACE_FRAGMENT = "replace_fragment"
    REPLACE_SECTION = "replace_section"
    SAVE_AS_FRAGMENT = "save_as_fragment"
    REPORT = "report"  # structured diagnostic report; never auto-applies


class AiCardKind(str, Enum):
    STYLE = "style"
    CHARACTER = "character"
    SCENE = "scene"


class AiThreadScope(str, Enum):
    FRAGMENT = "fragment"
    WORK = "work"
    COLLECTION = "collection"
    GLOBAL = "global"


class AiCostTier(str, Enum):
    """Three-tier model template selector."""

    THRIFTY = "thrifty"   # 省
    BALANCED = "balanced"  # 平衡
    STRONG = "strong"     # 强
