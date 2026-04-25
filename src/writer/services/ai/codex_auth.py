"""Runtime-only reader for a local Codex ``auth.json`` file.

Users who already run Codex on the same machine typically have a file at
``~/.codex/auth.json`` that contains ``OPENAI_API_KEY`` (and possibly
``tokens.id_token`` / ``tokens.refresh_token``). This module lets Writer
reuse that credential *at call time* without ever copying the secret into
Writer's own settings database.

Design rules (must not be violated):
- The resolver **reads** the file on demand and returns the string. It never
  caches, never logs, and never writes the value anywhere.
- Errors carry only structural information ("file missing", "no key field",
  "file unreadable") — never the secret or even a masked prefix of it.
- All public callers route user-facing text through ``status_text``,
  which intentionally says only "available" / "missing" / "unreadable".
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# Value stored as ``api_key_source`` when the user opts into Codex auth.
CODEX_AUTH_SOURCE = "codex"


@dataclass(frozen=True)
class CodexAuthStatus:
    """Small structural view of the auth file state — never carries the key."""

    available: bool
    path: Path
    reason: str = ""  # e.g. "missing_file", "missing_key", "unreadable"


class CodexAuthResolver:
    """Resolves the OpenAI API key from ``~/.codex/auth.json`` at call time."""

    def __init__(self, path: Optional[Path] = None) -> None:
        # The path is injectable for tests; production callers pass ``None``
        # and we compute the default under ``Path.home()``.
        self._path = path if path is not None else Path.home() / ".codex" / "auth.json"

    @property
    def path(self) -> Path:
        return self._path

    def status(self) -> CodexAuthStatus:
        """Report whether a usable key *would* be read, without returning it."""
        if not self._path.exists():
            return CodexAuthStatus(False, self._path, "missing_file")
        try:
            data = self._load()
        except (OSError, ValueError):
            return CodexAuthStatus(False, self._path, "unreadable")
        key = _extract_key(data)
        if not key:
            return CodexAuthStatus(False, self._path, "missing_key")
        return CodexAuthStatus(True, self._path, "")

    def read_api_key(self) -> str:
        """Return the API key string, raising :class:`CodexAuthError` on problems.

        The raised error message never contains the key or a prefix of it.
        """
        if not self._path.exists():
            raise CodexAuthError(
                f"Codex auth file not found at {self._path}. "
                "Run Codex once (or copy an existing auth.json into that "
                "location) before relying on the codex credential source."
            )
        try:
            data = self._load()
        except OSError as exc:
            raise CodexAuthError(
                f"Codex auth file at {self._path} could not be read: {exc}"
            ) from exc
        except ValueError as exc:
            raise CodexAuthError(
                f"Codex auth file at {self._path} is not valid JSON."
            ) from exc
        key = _extract_key(data)
        if not key:
            raise CodexAuthError(
                f"Codex auth file at {self._path} does not contain a non-empty "
                "OPENAI_API_KEY field."
            )
        return key

    def _load(self) -> dict:
        with self._path.open("r", encoding="utf-8") as fh:
            loaded = json.load(fh)
        if not isinstance(loaded, dict):
            raise ValueError("auth.json root is not an object")
        return loaded


class CodexAuthError(RuntimeError):
    """Raised when the Codex auth file is missing, unreadable, or empty."""


def _extract_key(data: dict) -> str:
    """Pull ``OPENAI_API_KEY`` out of the parsed auth.json structure."""
    raw = data.get("OPENAI_API_KEY")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    # Some Codex variants nest the key under "tokens" or similar. Accept a
    # small set of known layouts; do NOT accept arbitrary nested dicts that
    # could smuggle the token through places we didn't inspect.
    tokens = data.get("tokens")
    if isinstance(tokens, dict):
        nested = tokens.get("OPENAI_API_KEY")
        if isinstance(nested, str) and nested.strip():
            return nested.strip()
    return ""


def status_text(status: CodexAuthStatus) -> str:
    """Short, secret-free user-facing label for the auth status."""
    if status.available:
        return "available"
    mapping = {
        "missing_file": "file missing",
        "missing_key": "no OPENAI_API_KEY field",
        "unreadable": "unreadable",
    }
    return mapping.get(status.reason, "unavailable")
