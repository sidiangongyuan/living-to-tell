"""Domain enums shared across layers."""
from __future__ import annotations

from enum import Enum


class EntryType(str, Enum):
    FRAGMENT = "fragment"


class VersionType(str, Enum):
    """Why a version row exists. Only ``ORIGINAL`` is used in M2;
    AI-generated variants land in M3; ``MANUAL_SNAPSHOT`` is written by
    the version-history restore flow (M5D) before overwriting the live body."""

    ORIGINAL = "original"
    AI_POLISH = "ai_polish"
    AI_EXPAND = "ai_expand"
    AI_CONTINUE = "ai_continue"
    MANUAL_SNAPSHOT = "manual_snapshot"


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

