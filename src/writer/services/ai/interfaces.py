"""Provider-agnostic AI interfaces and DTOs.

The rest of the app talks to ``AiProvider`` only. Provider-specific code
(SDK quirks, transport details) lives in concrete adapters under this
package, never in UI or storage layers.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional

from writer.domain.enums import RewriteAction


class AiError(RuntimeError):
    """Raised by any provider adapter when a call cannot be completed."""


@dataclass
class RewriteRequest:
    action: RewriteAction
    text: str
    references: List[str] = field(default_factory=list)
    preserve_voice: bool = True
    max_output_chars: Optional[int] = None


@dataclass
class RewriteResponse:
    content: str
    model: str
    provider: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    finish_reason: Optional[str] = None


class AiProvider(ABC):
    """Minimal interface every provider adapter must implement."""

    name: str = "abstract"

    @abstractmethod
    def rewrite(self, request: RewriteRequest) -> RewriteResponse:
        """Run a single rewrite call and return the generated text."""

    def chat(
        self,
        messages: List[dict],
        *,
        model: Optional[str] = None,
    ) -> "ChatResponse":
        """Run a generic message-list call.

        Default implementation raises ``NotImplementedError`` so legacy
        providers can opt in. M10A's :class:`AiTaskService` requires it.
        """
        raise NotImplementedError("This provider does not implement chat().")


@dataclass
class ChatResponse:
    content: str
    model: str
    provider: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    finish_reason: Optional[str] = None

