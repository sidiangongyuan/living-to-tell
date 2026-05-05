"""Runtime-only reader for local Gemini CLI configuration.

Writer can reuse the user's ``~/.gemini/.env`` file at call time without
copying the Gemini API key into Writer's own settings database.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


GEMINI_AUTH_SOURCE = "gemini"
_BASE_URL_KEYS = ("GOOGLE_GEMINI_BASE_URL", "GEMINI_BASE_URL")
_MODEL_KEYS = ("GEMINI_MODEL", "GOOGLE_GEMINI_MODEL")
_API_KEY_KEYS = ("GEMINI_API_KEY", "GOOGLE_GEMINI_API_KEY")


@dataclass(frozen=True)
class GeminiAuthStatus:
    available: bool
    path: Path
    reason: str = ""


@dataclass(frozen=True)
class GeminiImportResult:
    base_url: Optional[str] = None
    model: Optional[str] = None
    wire_api: Optional[str] = None

    def is_empty(self) -> bool:
        return not (self.base_url or self.model or self.wire_api)


class GeminiAuthResolver:
    """Resolves the Gemini API key from ``~/.gemini/.env`` at call time."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self._path = path if path is not None else Path.home() / ".gemini" / ".env"

    @property
    def path(self) -> Path:
        return self._path

    def status(self) -> GeminiAuthStatus:
        if not self._path.exists():
            return GeminiAuthStatus(False, self._path, "missing_file")
        try:
            data = _load_env_file(self._path)
        except (OSError, ValueError):
            return GeminiAuthStatus(False, self._path, "unreadable")
        key = _first_present(data, _API_KEY_KEYS)
        if not key:
            return GeminiAuthStatus(False, self._path, "missing_key")
        return GeminiAuthStatus(True, self._path, "")

    def read_api_key(self) -> str:
        if not self._path.exists():
            raise GeminiAuthError(
                f"Gemini env file not found at {self._path}. "
                "Run the Gemini CLI once (or recreate ~/.gemini/.env) "
                "before relying on the gemini credential source."
            )
        try:
            data = _load_env_file(self._path)
        except OSError as exc:
            raise GeminiAuthError(
                f"Gemini env file at {self._path} could not be read: {exc}"
            ) from exc
        except ValueError as exc:
            raise GeminiAuthError(
                f"Gemini env file at {self._path} is not a valid .env file."
            ) from exc
        key = _first_present(data, _API_KEY_KEYS)
        if not key:
            raise GeminiAuthError(
                f"Gemini env file at {self._path} does not contain a non-empty "
                "GEMINI_API_KEY entry."
            )
        return key


class GeminiConfigImporter:
    """Extract safe endpoint/model fields from ``~/.gemini/.env``."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self._path = path if path is not None else Path.home() / ".gemini" / ".env"

    def default_path(self) -> Path:
        return self._path

    def import_default(self) -> GeminiImportResult:
        if not self._path.exists():
            raise FileNotFoundError(f"Gemini env file not found: {self._path}")
        data = _load_env_file(self._path)
        base_url = _first_present(data, _BASE_URL_KEYS)
        model = _first_present(data, _MODEL_KEYS)
        wire_api = "responses" if (base_url or model) else None
        return GeminiImportResult(
            base_url=base_url,
            model=model,
            wire_api=wire_api,
        )


class GeminiAuthError(RuntimeError):
    """Raised when the Gemini env file is missing, unreadable, or empty."""


def _load_env_file(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    with path.open("r", encoding="utf-8") as fh:
        for line_no, raw_line in enumerate(fh, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            if "=" not in line:
                raise ValueError(f"Invalid .env line {line_no}")
            key, value = line.split("=", 1)
            key = key.strip()
            if not key:
                raise ValueError(f"Invalid .env line {line_no}")
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                value = value[1:-1]
            data[key] = value.strip()
    return data


def _first_present(data: dict[str, str], keys: tuple[str, ...]) -> Optional[str]:
    for key in keys:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None