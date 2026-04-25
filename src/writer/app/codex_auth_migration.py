"""One-shot, opportunistic migration from ``env:OPENAI_API_KEY`` to ``codex``.

Existing installs from before the codex credential source landed have
``api_key_source = env:OPENAI_API_KEY`` saved in their settings database. If
those users also already run Codex locally and have not exported the env
var, the AI feature would still report "OPENAI_API_KEY is not set" even
though a perfectly usable key sits in ``~/.codex/auth.json``.

This module performs a *single*, *narrow*, *idempotent* migration that
flips ``api_key_source`` to ``"codex"`` only when **all** of the following
hold:

1. The persisted source is exactly ``env:OPENAI_API_KEY`` (case-insensitive).
2. The current process has no non-empty ``OPENAI_API_KEY`` env var — i.e.
   the env path would fail right now.
3. ``~/.codex/config.toml`` exists, parses cleanly, and declares
   ``requires_openai_auth = true``.
4. The Codex config's ``base_url`` (when present) matches what is already
   stored in our settings — so we know we're talking about the *same*
   provider the user previously configured, not a different one whose key
   happens to live in the same env var.
5. ``~/.codex/auth.json`` exists, is parseable, and exposes a non-empty
   ``OPENAI_API_KEY`` field.

If any check fails, nothing is changed. The migration writes a small
sentinel (``ai.codex_auth_migrated_v1 = "1"``) so it never runs twice;
later changes through the Settings dialog stay authoritative.

The migration **never** reads the secret value, never logs it, and never
copies it into the settings database — it only changes a pointer.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping, Optional

from writer.app.settings import KEY_AI_API_KEY_SOURCE, Settings
from writer.services.ai.codex_auth import CODEX_AUTH_SOURCE, CodexAuthResolver
from writer.services.ai.codex_config_importer import CodexConfigImporter


# Stored as a settings key. The "_v1" suffix lets us re-run a *different*
# migration in the future without resetting this one.
KEY_MIGRATION_FLAG = "ai.codex_auth_migrated_v1"


@dataclass(frozen=True)
class MigrationOutcome:
    """Result of a migration attempt — purely structural, no secret bytes."""

    migrated: bool
    reason: str  # e.g. "ok", "already_done", "env_var_present", ...


def _normalize_url(url: Optional[str]) -> str:
    return (url or "").strip().rstrip("/").lower()


def maybe_migrate_to_codex_auth(
    settings: Settings,
    *,
    environ: Optional[Mapping[str, str]] = None,
    codex_auth: Optional[CodexAuthResolver] = None,
    importer: Optional[CodexConfigImporter] = None,
) -> MigrationOutcome:
    """Run the one-shot migration. Safe to call on every startup."""
    # Idempotency gate.
    if settings.get(KEY_MIGRATION_FLAG) == "1":
        return MigrationOutcome(False, "already_done")

    src = (settings.ai_api_key_source or "").strip().lower()
    if src != "env:openai_api_key":
        # Either default unset, already codex, or a different env var.
        # In all those cases we leave the user's choice alone.
        return MigrationOutcome(False, "source_not_default")

    env = environ if environ is not None else os.environ
    if (env.get("OPENAI_API_KEY") or "").strip():
        # User has the env var set — the existing path works; respect it.
        return MigrationOutcome(False, "env_var_present")

    importer = importer or CodexConfigImporter()
    codex_path = importer.default_path()
    if not codex_path.exists():
        return MigrationOutcome(False, "no_codex_config")

    try:
        result = importer.import_from(codex_path)
    except (OSError, ValueError, Exception):  # noqa: BLE001
        # Any parse failure → bail out silently. We must not crash startup
        # for a malformed Codex config we don't own.
        return MigrationOutcome(False, "codex_config_unreadable")

    if not result.requires_openai_auth:
        return MigrationOutcome(False, "auth_not_required")

    # Compatibility: if the Codex config specifies a base_url, it must match
    # the one Writer is already configured with. Otherwise we'd be silently
    # rewiring the user's provider on top of swapping the credential source.
    stored = settings.load_ai_config()
    if result.base_url and _normalize_url(result.base_url) != _normalize_url(
        stored.base_url
    ):
        return MigrationOutcome(False, "base_url_mismatch")

    resolver = codex_auth or CodexAuthResolver()
    if not resolver.status().available:
        return MigrationOutcome(False, "auth_file_unavailable")

    # All gates passed. Flip the *pointer* only — never the secret.
    settings.set(KEY_AI_API_KEY_SOURCE, CODEX_AUTH_SOURCE)
    settings.set(KEY_MIGRATION_FLAG, "1")
    return MigrationOutcome(True, "ok")
