"""Synchronous preflight checks for AI rewrite.

Run BEFORE opening any progress dialog so users get a clear, actionable
error instead of a progress window that flashes and disappears.

Checks, in order:
  1. Target text is non-empty.
  2. Model is configured.
  3. wire_api is supported.
  4. api_key_source is supported (env:VAR / codex / gemini / opencode).
    5. The selected runtime credential source is available.

Each failure carries a short user-facing message describing *what* is
missing and *where* to fix it.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional

from writer.app.settings import SUPPORTED_WIRE_APIS
from writer.domain.models.ai_config import AiConfig
from writer.services.ai.codex_auth import CODEX_AUTH_SOURCE, CodexAuthResolver
from writer.services.ai.gemini_cli_provider import (
    GEMINI_CLI_AUTH_SOURCE,
    GEMINI_CLI_PROVIDER,
    find_gemini_cli,
)
from writer.services.ai.gemini_auth import GEMINI_AUTH_SOURCE, GeminiAuthResolver
from writer.services.ai.opencode_cli_provider import (
    OPENCODE_AUTH_SOURCE,
    OPENCODE_PROVIDER,
    find_opencode_cli,
    opencode_auth_status,
)


@dataclass(frozen=True)
class PreflightIssue:
    code: str
    message: str


def preflight_rewrite(
    config: AiConfig,
    target_text: str,
    *,
    has_entry: bool = True,
    environ: Optional[dict] = None,
    codex_auth: Optional[CodexAuthResolver] = None,
    gemini_auth: Optional[GeminiAuthResolver] = None,
) -> List[PreflightIssue]:
    """Return a list of blocking issues for a rewrite call.

    An empty list means the call is cleared to proceed. ``environ`` and
    ``codex_auth`` are injected for tests; production callers leave them
    as ``None`` so the real ``os.environ`` / default Codex auth path are
    consulted.
    """
    env = environ if environ is not None else os.environ
    issues: List[PreflightIssue] = []

    if not has_entry:
        issues.append(
            PreflightIssue(
                "no_entry",
                "No fragment is open. Create or select a fragment first.",
            )
        )

    if not target_text or not target_text.strip():
        issues.append(
            PreflightIssue(
                "empty_text",
                "Nothing to rewrite — write some text or select a passage first.",
            )
        )

    if not (config.model or "").strip():
        issues.append(
            PreflightIssue(
                "no_model",
                "Model name is empty. Open AI → Settings and enter a model "
                "(for example gpt-4o-mini).",
            )
        )

    wire = (config.wire_api or "").strip().lower()
    if wire not in SUPPORTED_WIRE_APIS:
        issues.append(
            PreflightIssue(
                "bad_wire_api",
                f"Unsupported wire_api '{config.wire_api}'. "
                f"Supported values: {', '.join(SUPPORTED_WIRE_APIS)}. "
                "Open AI → Settings to change it.",
            )
        )

    source = (config.api_key_source or "").strip()
    if source.lower() == CODEX_AUTH_SOURCE:
        resolver = codex_auth if codex_auth is not None else CodexAuthResolver()
        status = resolver.status()
        if not status.available:
            reason_map = {
                "missing_file": (
                    f"Codex auth file was not found at {status.path}. "
                    "Run Codex once on this machine (or copy an existing "
                    "auth.json into that path) before relying on the codex "
                    "credential source. Alternatively switch API key source "
                    "back to env:VARNAME in AI → Settings."
                ),
                "missing_key": (
                    f"Codex auth file at {status.path} has no non-empty "
                    "OPENAI_API_KEY field. Re-run Codex so it refreshes "
                    "auth.json, or switch API key source to env:VARNAME."
                ),
                "unreadable": (
                    f"Codex auth file at {status.path} could not be parsed. "
                    "Check file permissions or re-run Codex."
                ),
            }
            issues.append(
                PreflightIssue(
                    "missing_codex_auth",
                    reason_map.get(
                        status.reason,
                        f"Codex auth at {status.path} is unavailable.",
                    ),
                )
            )
    elif source.lower() == GEMINI_AUTH_SOURCE:
        resolver = gemini_auth if gemini_auth is not None else GeminiAuthResolver()
        status = resolver.status()
        if not status.available:
            reason_map = {
                "missing_file": (
                    f"Gemini env file was not found at {status.path}. "
                    "Create ~/.gemini/.env (or re-run the Gemini CLI setup) "
                    "before relying on the gemini credential source. "
                    "Alternatively switch API key source back to env:VARNAME "
                    "in AI → Settings."
                ),
                "missing_key": (
                    f"Gemini env file at {status.path} has no non-empty "
                    "GEMINI_API_KEY entry. Refresh the Gemini CLI config, "
                    "or switch API key source to env:VARNAME."
                ),
                "unreadable": (
                    f"Gemini env file at {status.path} could not be parsed. "
                    "Check file permissions or regenerate the file."
                ),
            }
            issues.append(
                PreflightIssue(
                    "missing_gemini_auth",
                    reason_map.get(
                        status.reason,
                        f"Gemini auth at {status.path} is unavailable.",
                    ),
                )
            )
    elif source.lower() == GEMINI_CLI_AUTH_SOURCE or config.provider_key() == GEMINI_CLI_PROVIDER:
        configured = (env.get("WRITER_GEMINI_CLI_COMMAND", "") or "").strip()
        found = configured or find_gemini_cli()
        if not found:
            issues.append(
                PreflightIssue(
                    "missing_gemini_cli",
                    "Gemini CLI was not found. Install it with `npm install -g "
                    "@google/gemini-cli`, or add gemini.cmd to PATH before "
                    "using the Gemini CLI / OAuth provider.",
                )
            )
    elif source.lower() == OPENCODE_AUTH_SOURCE or config.provider_key() == OPENCODE_PROVIDER:
        configured = (env.get("WRITER_OPENCODE_COMMAND", "") or "").strip()
        found = configured or find_opencode_cli()
        if not found:
            issues.append(
                PreflightIssue(
                    "missing_opencode_cli",
                    "未检测到 opencode 命令。请先安装 OpenCode，并确认 opencode 在 PATH 中。",
                )
            )
        else:
            status = opencode_auth_status(command=found)
            if not status.available:
                issues.append(
                    PreflightIssue(
                        "missing_opencode_auth",
                        "OpenCode 尚未登录或登录状态不可用。请先在终端运行 opencode auth login。",
                    )
                )
    elif not source.startswith("env:"):
        issues.append(
            PreflightIssue(
                "bad_key_source",
                "API key source must be either env:VARNAME or the literal "
                "string 'codex', 'gemini', 'gemini-cli', or 'opencode'. Open AI → Settings and set, for example, "
                "env:OPENAI_API_KEY, or switch to 'codex' to reuse "
                "~/.codex/auth.json, 'gemini' to reuse ~/.gemini/.env, "
                "'gemini-cli' to reuse Gemini CLI OAuth, or 'opencode' "
                "to reuse OpenCode CLI local auth. You can also save a key "
                "from Settings, which stores it as a user environment variable.",
            )
        )
    else:
        var = source.split(":", 1)[1].strip()
        if not var:
            issues.append(
                PreflightIssue(
                    "empty_key_var",
                    "API key source is 'env:' with no variable name. "
                    "Open AI → Settings and write env:OPENAI_API_KEY "
                    "(or whichever variable holds your key).",
                )
            )
        elif not (env.get(var, "") or "").strip():
            issues.append(
                PreflightIssue(
                    "missing_env_var",
                    f"Environment variable {var} is not set. "
                    f"Export {var} in your shell (or System → Environment "
                    "Variables on Windows), or paste and save the key from "
                    "AI Settings before invoking AI rewrite.",
                )
            )

    return issues


def format_issues(issues: List[PreflightIssue]) -> str:
    """Render issues as a bullet list suitable for a QMessageBox."""
    if not issues:
        return ""
    if len(issues) == 1:
        return issues[0].message
    return "\n\n".join(f"• {issue.message}" for issue in issues)
