"""Import safe fields from a local Codex ``config.toml``.

Only ``base_url``, ``model``, and ``wire_api`` are extracted. Credentials and
other private fields are deliberately ignored — the writer app owns its own
auth flow (see docs/codex-style-integration.md §5.3).

Supported Codex-style layout::

    model = "gpt-5"
    model_provider = "openai"

    [model_providers.openai]
    base_url = "https://example/v1"
    wire_api = "responses"

A flat fallback (top-level ``base_url`` / ``wire_api``) is also accepted.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union


@dataclass(frozen=True)
class CodexImportResult:
    base_url: Optional[str] = None
    model: Optional[str] = None
    wire_api: Optional[str] = None
    requires_openai_auth: bool = False

    def is_empty(self) -> bool:
        return not (self.base_url or self.model or self.wire_api)


class CodexConfigImporter:
    """Parses a Codex TOML file and returns only the safe fields."""

    def default_path(self) -> Path:
        return Path.home() / ".codex" / "config.toml"

    def import_from(self, path: Union[str, Path]) -> CodexImportResult:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Codex config not found: {p}")
        with p.open("rb") as fh:
            data = tomllib.load(fh)
        return self._extract(data)

    @staticmethod
    def _extract(data: dict) -> CodexImportResult:
        model = _as_str(data.get("model"))
        provider_key = _as_str(data.get("model_provider"))

        base_url: Optional[str] = None
        wire_api: Optional[str] = None
        requires_openai_auth = False

        providers = data.get("model_providers")
        if isinstance(providers, dict) and provider_key:
            chosen = providers.get(provider_key)
            if isinstance(chosen, dict):
                base_url = _as_str(chosen.get("base_url"))
                wire_api = _as_str(chosen.get("wire_api"))
                requires_openai_auth = bool(
                    chosen.get("requires_openai_auth", False)
                )

        if base_url is None:
            base_url = _as_str(data.get("base_url"))
        if wire_api is None:
            wire_api = _as_str(data.get("wire_api"))
        if not requires_openai_auth:
            requires_openai_auth = bool(data.get("requires_openai_auth", False))

        return CodexImportResult(
            base_url=base_url,
            model=model,
            wire_api=wire_api,
            requires_openai_auth=requires_openai_auth,
        )


def _as_str(value) -> Optional[str]:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None
