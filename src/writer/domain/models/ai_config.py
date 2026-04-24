"""AI provider configuration value object.

Mirrors the small subset of fields the writer app needs from a Codex-style
configuration. Credentials are not stored in this object — the API key is
resolved at call time from the ``api_key_source`` (only ``env:VAR`` is
supported in M3).
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
