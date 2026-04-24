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
