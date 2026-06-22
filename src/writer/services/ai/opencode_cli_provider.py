"""OpenCode CLI provider adapter.

Writer does not read or persist OpenCode credentials. It delegates generation
to the locally authenticated ``opencode`` command and parses its JSON event
stream. The command is always run in an empty temporary directory so OpenCode
does not inherit the user's current project context.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable, List, Optional

from writer.domain.models.ai_config import AiConfig
from writer.services.ai.interfaces import (
    AiError,
    AiProvider,
    ChatResponse,
    RewriteRequest,
    RewriteResponse,
)
from writer.services.ai.prompt_builder import PromptBuilder


OPENCODE_PROVIDER = "opencode"
OPENCODE_AUTH_SOURCE = "opencode"
OPENCODE_DEFAULT_MODEL = "opencode/deepseek-v4-flash-free"
OPENCODE_MODEL_PRESETS = (
    OPENCODE_DEFAULT_MODEL,
    "opencode/mimo-v2.5-free",
    "opencode/nemotron-3-ultra-free",
    "opencode/north-mini-code-free",
    "opencode/big-pickle",
)
OPENCODE_TIMEOUT_ENV = "WRITER_OPENCODE_TIMEOUT_SECONDS"
OPENCODE_DEFAULT_TIMEOUT_SECONDS = 120

_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
_MODEL_LINE_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.:-]+$")


@dataclass(frozen=True)
class OpenCodeAuthStatus:
    available: bool
    command: Optional[str] = None
    path: Optional[Path] = None
    reason: str = ""


@dataclass(frozen=True)
class OpenCodeRunResult:
    text: str
    model: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    finish_reason: Optional[str] = None
    cost: Optional[float] = None


class OpenCodeCliProvider(AiProvider):
    """Adapter that shells out to the locally authenticated OpenCode CLI."""

    name = OPENCODE_PROVIDER

    def __init__(
        self,
        config: AiConfig,
        prompt_builder: PromptBuilder,
        *,
        command: Optional[str] = None,
        runner: Optional[Callable[..., subprocess.CompletedProcess]] = None,
        timeout_seconds: Optional[int] = None,
        tempdir_factory: Optional[Callable[[], Any]] = None,
    ) -> None:
        self._config = config
        self._prompts = prompt_builder
        self._command = command
        self._runner = runner
        self._timeout_seconds = _resolve_timeout_seconds(timeout_seconds)
        self._tempdir_factory = tempdir_factory

    def rewrite(self, request: RewriteRequest) -> RewriteResponse:
        messages = self._prompts.build_messages(request)
        used_model = self._model_name(self._config.model)
        result = self._run_prompt(_messages_to_prompt(messages), model=used_model)
        return RewriteResponse(
            content=result.text,
            model=result.model,
            provider=self.name,
            transport="opencode_cli",
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            finish_reason=result.finish_reason,
            cost=result.cost,
        )

    def chat(self, messages, *, model=None) -> ChatResponse:
        used_model = self._model_name(model or self._config.model)
        result = self._run_prompt(_messages_to_prompt(list(messages)), model=used_model)
        return ChatResponse(
            content=result.text,
            model=result.model,
            provider=self.name,
            transport="opencode_cli",
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            finish_reason=result.finish_reason,
            cost=result.cost,
        )

    def _run_prompt(self, prompt: str, *, model: str) -> OpenCodeRunResult:
        command = self._resolve_command()
        full_prompt = _opencode_prompt(prompt)

        with self._safe_tempdir() as workdir:
            cmd = _command_prefix(command) + [
                "run",
                "--model",
                model,
                "--format",
                "json",
                "--dir",
                str(workdir),
                full_prompt,
            ]
            env = dict(os.environ)
            try:
                if self._runner is not None:
                    completed = self._runner(
                        cmd,
                        capture_output=True,
                        input="",
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        timeout=self._timeout_seconds,
                        env=env,
                    )
                else:
                    completed = _run_subprocess_tree(
                        cmd,
                        timeout_seconds=self._timeout_seconds,
                        env=env,
                    )
            except FileNotFoundError as exc:
                raise AiError(
                    "未检测到 opencode 命令。请先安装 OpenCode，并确认 opencode 在 PATH 中。"
                ) from exc
            except subprocess.TimeoutExpired as exc:
                raise AiError(
                    f"OpenCode 请求超时（{self._timeout_seconds} 秒）。"
                    "请稍后重试或换用其他模型。"
                ) from exc
            except Exception as exc:  # noqa: BLE001
                raise AiError(f"OpenCode 启动失败：{_clean_output(str(exc))}") from exc

        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        if completed.returncode != 0:
            raise AiError(_friendly_opencode_failure(stdout, stderr, completed.returncode))
        return _parse_run_output(stdout, model=model)

    def _safe_tempdir(self):
        if self._tempdir_factory is not None:
            return self._tempdir_factory()
        return tempfile.TemporaryDirectory(prefix="living-to-tell-opencode-")

    def _resolve_command(self) -> str:
        configured = (
            self._command
            or os.environ.get("WRITER_OPENCODE_COMMAND", "")
            or ""
        ).strip()
        if configured:
            return configured
        found = find_opencode_cli()
        if found:
            return found
        raise FileNotFoundError("opencode")

    @staticmethod
    def _model_name(value: Optional[str]) -> str:
        raw = (value or "").strip()
        if not raw or raw.lower() in {"default", "auto"}:
            return OPENCODE_DEFAULT_MODEL
        return raw


def find_opencode_cli() -> Optional[str]:
    """Return a usable OpenCode CLI command path if available."""
    command = (
        shutil.which("opencode.cmd")
        or shutil.which("opencode")
        or shutil.which("opencode.ps1")
    )
    if not command:
        return None
    if os.name == "nt":
        direct = _direct_windows_opencode_exe(Path(command))
        if direct is not None:
            return str(direct)
    return command


def _direct_windows_opencode_exe(command: Path) -> Optional[Path]:
    """Return the real OpenCode executable behind npm's lossy .cmd shim."""
    command_dir = command.parent
    candidates = [
        command_dir / "node_modules" / "opencode-ai" / "bin" / "opencode.exe",
        command_dir.parent / "node_modules" / "opencode-ai" / "bin" / "opencode.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def opencode_auth_status(
    *,
    command: Optional[str] = None,
    runner: Optional[Callable[..., subprocess.CompletedProcess]] = None,
    timeout_seconds: int = 10,
) -> OpenCodeAuthStatus:
    """Return non-secret OpenCode local auth status."""
    resolved = command or find_opencode_cli()
    path = default_opencode_auth_path()
    if not resolved:
        return OpenCodeAuthStatus(False, command=None, path=path, reason="missing_command")
    cmd = _command_prefix(resolved) + ["auth", "list"]
    try:
        if runner is not None:
            completed = runner(
                cmd,
                capture_output=True,
                input="",
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
            )
        else:
            completed = _run_subprocess_tree(
                cmd,
                timeout_seconds=timeout_seconds,
                env=dict(os.environ),
            )
    except FileNotFoundError:
        return OpenCodeAuthStatus(False, command=resolved, path=path, reason="missing_command")
    except subprocess.TimeoutExpired:
        return OpenCodeAuthStatus(False, command=resolved, path=path, reason="auth_list_timeout")
    except Exception:  # noqa: BLE001
        return OpenCodeAuthStatus(False, command=resolved, path=path, reason="auth_list_failed")

    text = _clean_output((completed.stdout or "") + "\n" + (completed.stderr or ""))
    if completed.returncode != 0:
        return OpenCodeAuthStatus(False, command=resolved, path=path, reason="auth_list_failed")
    if "opencode" not in text.lower() and not path.exists():
        return OpenCodeAuthStatus(False, command=resolved, path=path, reason="missing_login")
    return OpenCodeAuthStatus(True, command=resolved, path=path)


def list_opencode_models(
    *,
    refresh: bool = True,
    command: Optional[str] = None,
    runner: Optional[Callable[..., subprocess.CompletedProcess]] = None,
    timeout_seconds: int = 30,
) -> list[str]:
    """Fetch OpenCode models from the local CLI."""
    resolved = command or find_opencode_cli()
    if not resolved:
        raise AiError("未检测到 opencode 命令。请先安装 OpenCode。")
    cmd = _command_prefix(resolved) + ["models", "opencode"]
    if refresh:
        cmd.append("--refresh")
    try:
        if runner is not None:
            completed = runner(
                cmd,
                capture_output=True,
                input="",
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
            )
        else:
            completed = _run_subprocess_tree(
                cmd,
                timeout_seconds=timeout_seconds,
                env=dict(os.environ),
            )
    except FileNotFoundError as exc:
        raise AiError("未检测到 opencode 命令。请先安装 OpenCode。") from exc
    except subprocess.TimeoutExpired as exc:
        raise AiError("OpenCode 模型列表获取超时。") from exc
    except Exception as exc:  # noqa: BLE001
        raise AiError(f"OpenCode 模型列表获取失败：{_clean_output(str(exc))}") from exc
    if completed.returncode != 0:
        raise AiError(_friendly_opencode_failure(completed.stdout or "", completed.stderr or "", completed.returncode))
    models = parse_opencode_models(completed.stdout or "")
    if not models:
        raise AiError("OpenCode 没有返回可用模型。")
    return models


def parse_opencode_models(text: str) -> list[str]:
    models: list[str] = []
    seen: set[str] = set()
    for line in _clean_output(text).splitlines():
        value = line.strip()
        if not value or not _MODEL_LINE_RE.match(value):
            continue
        lowered = value.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        models.append(value)
    return models


def default_opencode_auth_path() -> Path:
    data_home = os.environ.get("XDG_DATA_HOME", "").strip()
    if data_home:
        return Path(data_home).expanduser() / "opencode" / "auth.json"
    return Path.home() / ".local" / "share" / "opencode" / "auth.json"


def _parse_run_output(stdout: str, *, model: str) -> OpenCodeRunResult:
    text_parts: list[str] = []
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    finish_reason: Optional[str] = None
    cost: Optional[float] = None
    saw_json = False
    for line in stdout.replace("\r\n", "\n").split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise AiError("OpenCode 返回了无法解析的 JSON 输出。") from exc
        if not isinstance(event, dict):
            continue
        saw_json = True
        part = event.get("part")
        if isinstance(part, dict) and part.get("type") == "text":
            part_text = part.get("text")
            if isinstance(part_text, str):
                text_parts.append(part_text)
        if isinstance(part, dict) and part.get("type") == "step-finish":
            finish_reason = _safe_str(part.get("reason"))
            tokens = part.get("tokens")
            if isinstance(tokens, dict):
                total_input = tokens.get("input")
                total_output = tokens.get("output")
                input_tokens = total_input if isinstance(total_input, int) else input_tokens
                output_tokens = total_output if isinstance(total_output, int) else output_tokens
            raw_cost = part.get("cost")
            if isinstance(raw_cost, (int, float)):
                cost = float(raw_cost)
    if not saw_json:
        raise AiError("OpenCode 没有返回 JSON 事件。")
    text = "".join(text_parts).strip()
    if not text:
        raise AiError("OpenCode 没有返回文本内容。")
    return OpenCodeRunResult(
        text=text,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        finish_reason=finish_reason,
        cost=cost,
    )


def _opencode_prompt(prompt: str) -> str:
    return (
        "You are being called from a writing application as a plain text AI provider.\n"
        "Do not inspect files. Do not use tools. Do not describe your process.\n"
        "Return only the answer requested by the user.\n\n"
        f"{prompt.strip()}"
    ).strip()


def _messages_to_prompt(messages: List[dict]) -> str:
    parts: List[str] = []
    for message in messages:
        role = str(message.get("role") or "user").strip().lower()
        text = _message_text(message.get("content"))
        if not text:
            continue
        label = {
            "system": "System",
            "assistant": "Assistant",
            "model": "Assistant",
            "user": "User",
        }.get(role, role.title())
        parts.append(f"{label}:\n{text}")
    return "\n\n".join(parts).strip()


def _message_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, dict) and isinstance(content.get("text"), str):
        return content["text"].strip()
    if isinstance(content, list):
        out: List[str] = []
        for item in content:
            if isinstance(item, str):
                out.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                out.append(item["text"])
        return "\n".join(part for part in out if part).strip()
    return ""


def _friendly_opencode_failure(stdout: str, stderr: str, returncode: int) -> str:
    raw = _clean_output("\n".join(part for part in (stderr, stdout) if part))
    lowered = raw.lower()
    if "provider not found" in lowered or "model not found" in lowered:
        return "OpenCode 模型不存在或当前账号不可用，请点击“获取模型”后重新选择。"
    if "auth" in lowered or "login" in lowered or "unauthorized" in lowered:
        return "OpenCode 尚未登录或登录已失效。请先运行 opencode auth login。"
    if "forbidden" in lowered or "permission" in lowered or "403" in lowered:
        return "OpenCode 拒绝了当前请求。可能是模型权限不足或登录状态失效。"
    if raw:
        return f"OpenCode 请求失败：{raw[:500]}"
    return f"OpenCode 请求失败：exit code {returncode}"


def _clean_output(text: str) -> str:
    text = _ANSI_RE.sub("", text or "")
    lines = []
    for line in text.replace("\r\n", "\n").split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        lines.append(line.rstrip())
    return "\n".join(lines).strip()


def _safe_str(value: Any) -> Optional[str]:
    return value if isinstance(value, str) and value.strip() else None


def _resolve_timeout_seconds(explicit: Optional[int]) -> int:
    if explicit is not None:
        return max(1, int(explicit))
    raw = os.environ.get(OPENCODE_TIMEOUT_ENV, "").strip()
    if raw:
        try:
            return max(1, int(raw))
        except ValueError:
            pass
    return OPENCODE_DEFAULT_TIMEOUT_SECONDS


def _command_prefix(command: str) -> List[str]:
    if command.lower().endswith(".ps1"):
        return ["powershell", "-ExecutionPolicy", "Bypass", "-File", command]
    return [command]


def _run_subprocess_tree(
    cmd: List[str],
    *,
    timeout_seconds: int,
    env: dict[str, str],
) -> subprocess.CompletedProcess:
    creationflags = 0
    if os.name == "nt":
        creationflags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        creationflags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        creationflags=creationflags,
    )
    try:
        stdout, stderr = proc.communicate(input="", timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        _kill_process_tree(proc.pid)
        try:
            proc.communicate(timeout=5)
        except Exception:  # noqa: BLE001
            pass
        raise
    return subprocess.CompletedProcess(
        cmd, proc.returncode, stdout=stdout, stderr=stderr
    )


def _kill_process_tree(pid: int) -> None:
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            return
        except Exception:  # noqa: BLE001
            pass
    try:
        os.kill(pid, 9)
    except Exception:  # noqa: BLE001
        pass
