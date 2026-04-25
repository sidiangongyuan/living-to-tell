"""AI provider configuration value object.

Mirrors the small subset of fields the writer app needs from a Codex-style
configuration. Credentials are not stored in this object — the API key is
resolved at call time from the ``api_key_source``.

Supported values for ``api_key_source``:
- ``env:VARNAME`` — read from ``os.environ[VARNAME]`` at request time.
- ``codex``       — read from ``~/.codex/auth.json`` at request time.

Both paths read the secret strictly at runtime; Writer never persists the
key itself on disk.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AiConfig:
    provider_name: str = "OpenAI"
    base_url: Optional[str] = None
    wire_api: str = "responses"
    model: str = "gpt-4o-mini"
    api_key_source: str = "env:OPENAI_API_KEY"

    def env_var_name(self) -> Optional[str]:
        if self.api_key_source and self.api_key_source.startswith("env:"):
            return self.api_key_source.split(":", 1)[1].strip() or None
        return None

    def uses_codex_auth(self) -> bool:
        """True when the key should be read from a local Codex auth file."""
        return (self.api_key_source or "").strip().lower() == "codex"
