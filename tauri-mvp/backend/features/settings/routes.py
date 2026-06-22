"""Settings API routes for the Tauri frontend."""
from __future__ import annotations

import os
import shutil
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from deps import get_container
from writer.app.paths import (
    DATABASE_FILENAME,
    ENV_DATA_DIR,
    default_user_data_directory,
    user_data_directory,
)
from writer.app.container import AppContainer
from writer.domain.models.ai_config import AiConfig
from writer.services.ai.codex_auth import CODEX_AUTH_SOURCE, CodexAuthResolver
from writer.services.ai.codex_config_importer import CodexConfigImporter
from writer.services.ai.gemini_auth import (
    GEMINI_AUTH_SOURCE,
    GeminiAuthResolver,
    GeminiConfigImporter,
)
from writer.services.ai.gemini_cli_provider import (
    GEMINI_CLI_AUTH_SOURCE,
    GEMINI_CLI_DEFAULT_MODEL,
    GeminiCliProvider,
    detect_gemini_cli_proxy,
    find_gemini_cli,
    gemini_cli_oauth_status,
)
from writer.services.ai.gemini_provider import GeminiProvider
from writer.services.ai.interfaces import AiError, AiProvider
from writer.services.ai.opencode_cli_provider import (
    OPENCODE_AUTH_SOURCE,
    OPENCODE_DEFAULT_MODEL,
    OPENCODE_MODEL_PRESETS,
    OpenCodeCliProvider,
    list_opencode_models,
    opencode_auth_status,
)
from writer.services.ai.openai_provider import OpenAiProvider
from writer.services.ai.preflight import format_issues, preflight_rewrite
from writer.services.ai.prompt_builder import PromptBuilder

router = APIRouter(prefix="/api/settings", tags=["settings"])

OPENAI_MODEL_PRESETS = ("gpt-4o-mini", "gpt-4.1-mini", "gpt-4.1")
GEMINI_MODEL_PRESETS = (
    "gemini-3.1-pro-preview",
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite-preview",
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
)
GEMINI_CLI_MODEL_PRESETS = (
    GEMINI_CLI_DEFAULT_MODEL,
    *GEMINI_MODEL_PRESETS,
)
PUBLIC_AI_PROVIDERS = {"openai", "gemini", "gemini_cli", "opencode"}


class AiCredentialStatus(BaseModel):
    available: bool
    path: Optional[str] = None
    reason: str = ""
    account: Optional[str] = None
    command: Optional[str] = None
    proxy: Optional[str] = None


class AiSettingsStatus(BaseModel):
    env: AiCredentialStatus
    codex: AiCredentialStatus
    gemini: AiCredentialStatus
    gemini_cli: AiCredentialStatus
    opencode: AiCredentialStatus


class AiSettingsOut(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    provider_name: str
    base_url: Optional[str] = None
    wire_api: str
    model: str
    api_key_source: str
    gemini_cli_proxy: Optional[str] = None
    status: AiSettingsStatus
    model_presets: dict[str, list[str]]


class AiSettingsUpdate(BaseModel):
    provider_name: str
    base_url: Optional[str] = None
    wire_api: str = "responses"
    model: str
    api_key_source: str = "env:OPENAI_API_KEY"
    gemini_cli_proxy: Optional[str] = None


class AiImportOut(BaseModel):
    config: AiSettingsOut
    imported: dict[str, Any]


class AiTestRequest(AiSettingsUpdate):
    pass


class AiTestOut(BaseModel):
    ok: bool
    message: str


class AiLiveTestOut(BaseModel):
    ok: bool
    message: str
    provider: str
    model: str
    transport: Optional[str] = None
    elapsed_ms: Optional[int] = None
    preview: str = ""
    cost: Optional[float] = None


class AiModelListOut(BaseModel):
    provider: str
    models: list[str]
    source: str
    message: str = ""


class DataLocationInfo(BaseModel):
    data_dir: str
    default_data_dir: str
    database_path: str
    default_database_path: str
    backup_dir: str
    checkpoint_dir: str
    is_custom: bool
    database_exists: bool
    warning: Optional[str] = None


class DataLocationMigrationRequest(BaseModel):
    target_dir: str
    replace_existing: bool = False


class DataLocationMigrationResult(BaseModel):
    target_dir: str
    target_database_path: str
    restart_required: bool
    message: str


def _container_database_path(container: AppContainer) -> Path:
    row = container.connection.execute("PRAGMA database_list").fetchone()
    if not row or not row[2]:
        raise HTTPException(500, "Current database path is unavailable")
    return Path(row[2]).expanduser().resolve()


def _data_location_info(container: AppContainer, warning: Optional[str] = None) -> DataLocationInfo:
    db_path = _container_database_path(container)
    data_dir = db_path.parent
    default_dir = default_user_data_directory(create=False).expanduser().resolve()
    return DataLocationInfo(
        data_dir=str(data_dir),
        default_data_dir=str(default_dir),
        database_path=str(db_path),
        default_database_path=str(default_dir / DATABASE_FILENAME),
        backup_dir=str(data_dir / "backups"),
        checkpoint_dir=str(data_dir / "checkpoints"),
        is_custom=bool(os.environ.get(ENV_DATA_DIR)),
        database_exists=db_path.exists(),
        warning=warning,
    )


def _is_same_or_nested(left: Path, right: Path) -> bool:
    try:
        left.relative_to(right)
        return True
    except ValueError:
        return False


def _prepare_target_dir(raw_target: str, current_dir: Path) -> Path:
    target = Path(raw_target).expanduser()
    if not str(target).strip():
        raise HTTPException(400, "target_dir is required")
    if not target.is_absolute():
        raise HTTPException(400, "target_dir must be an absolute path")
    target = target.resolve()
    current_dir = current_dir.resolve()
    if target == current_dir:
        raise HTTPException(400, "target_dir is already the current data directory")
    if _is_same_or_nested(target, current_dir) or _is_same_or_nested(current_dir, target):
        raise HTTPException(
            400,
            "target_dir must not be nested inside the current data directory or contain it",
        )
    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise HTTPException(400, f"target_dir cannot be created: {exc}") from exc
    if not target.is_dir():
        raise HTTPException(400, "target_dir is not a directory")
    probe = target / ".living-to-tell-write-test"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except OSError as exc:
        raise HTTPException(400, f"target_dir is not writable: {exc}") from exc
    return target


def _migration_backup_path(path: Path) -> Path:
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    base = path.with_name(f"{path.name}.before-migration-{timestamp}")
    candidate = base
    index = 1
    while candidate.exists():
        candidate = path.with_name(f"{base.name}-{index}")
        index += 1
    return candidate


def _backup_existing_database(target_db: Path) -> None:
    backup_db = _migration_backup_path(target_db)
    target_db.replace(backup_db)
    for suffix in ("-wal", "-shm", "-journal"):
        sidecar = Path(f"{target_db}{suffix}")
        if sidecar.exists():
            sidecar.replace(Path(f"{backup_db}{suffix}"))


def _preflight_auxiliary_dir(source: Path, target: Path, replace_existing: bool) -> None:
    if not source.exists() or not source.is_dir():
        return
    if target.exists() and any(target.iterdir()) and not replace_existing:
        raise HTTPException(
            400,
            f"{target.name} already exists in target_dir and is not empty",
        )


def _copy_auxiliary_dir(source: Path, target: Path, replace_existing: bool = False) -> None:
    if not source.exists() or not source.is_dir():
        return
    if target.exists() and any(target.iterdir()):
        if not replace_existing:
            raise HTTPException(
                400,
                f"{target.name} already exists in target_dir and is not empty",
            )
        target.rename(_migration_backup_path(target))
    shutil.copytree(source, target, dirs_exist_ok=target.exists())


def _copy_database(container: AppContainer, target_db: Path, replace_existing: bool = False) -> None:
    tmp_db = target_db.with_suffix(f"{target_db.suffix}.tmp")
    tmp_db.unlink(missing_ok=True)
    try:
        destination = sqlite3.connect(tmp_db)
        try:
            container.connection.backup(destination)
            integrity = destination.execute("PRAGMA integrity_check").fetchone()
            if not integrity or integrity[0] != "ok":
                raise HTTPException(500, "Migrated database failed integrity_check")
        finally:
            destination.close()
        if target_db.exists():
            if not replace_existing:
                raise HTTPException(400, f"{DATABASE_FILENAME} already exists in target_dir")
            _backup_existing_database(target_db)
        tmp_db.replace(target_db)
    except Exception:
        tmp_db.unlink(missing_ok=True)
        raise


def _env_status(source: str) -> AiCredentialStatus:
    if not source.startswith("env:"):
        return AiCredentialStatus(available=False, reason="not_env_source")
    var = source.split(":", 1)[1].strip()
    if not var:
        return AiCredentialStatus(available=False, reason="empty_var")
    return AiCredentialStatus(
        available=bool(os.environ.get(var, "").strip()),
        reason="" if os.environ.get(var, "").strip() else "missing_var",
        path=var,
    )


def _codex_status() -> AiCredentialStatus:
    status = CodexAuthResolver().status()
    return AiCredentialStatus(
        available=status.available,
        path=str(status.path),
        reason=status.reason,
    )


def _gemini_status() -> AiCredentialStatus:
    status = GeminiAuthResolver().status()
    return AiCredentialStatus(
        available=status.available,
        path=str(status.path),
        reason=status.reason,
    )


def _gemini_cli_status(proxy: Optional[str]) -> AiCredentialStatus:
    command = find_gemini_cli()
    oauth = gemini_cli_oauth_status()
    return AiCredentialStatus(
        available=bool(command and oauth.available),
        path=str(oauth.creds_path),
        reason="" if command and oauth.available else ("missing_command" if not command else oauth.reason),
        account=oauth.account,
        command=command,
        proxy=proxy or detect_gemini_cli_proxy(),
    )


def _opencode_status() -> AiCredentialStatus:
    status = opencode_auth_status()
    return AiCredentialStatus(
        available=status.available,
        path=str(status.path) if status.path else None,
        reason=status.reason,
        command=status.command,
    )


def _status_for(config: AiConfig) -> AiSettingsStatus:
    return AiSettingsStatus(
        env=_env_status(config.api_key_source or ""),
        codex=_codex_status(),
        gemini=_gemini_status(),
        gemini_cli=_gemini_cli_status(config.gemini_cli_proxy),
        opencode=_opencode_status(),
    )


def _model_presets() -> dict[str, list[str]]:
    return {
        "openai": list(OPENAI_MODEL_PRESETS),
        "gemini": list(GEMINI_MODEL_PRESETS),
        "gemini_cli": list(GEMINI_CLI_MODEL_PRESETS),
        "opencode": list(OPENCODE_MODEL_PRESETS),
    }


def _config_to_out(config: AiConfig) -> AiSettingsOut:
    return AiSettingsOut(
        provider_name=config.provider_key(),
        base_url=config.base_url,
        wire_api=config.wire_api,
        model=config.model,
        api_key_source=config.api_key_source,
        gemini_cli_proxy=config.gemini_cli_proxy,
        status=_status_for(config),
        model_presets=_model_presets(),
    )


def _request_to_config(data: AiSettingsUpdate) -> AiConfig:
    provider = data.provider_name.strip().lower()
    if provider not in PUBLIC_AI_PROVIDERS:
        raise HTTPException(400, f"Unsupported provider: {data.provider_name}")
    api_key_source = data.api_key_source.strip()
    model = data.model.strip()
    base_url = (data.base_url or "").strip() or None
    if provider == "gemini_cli":
        api_key_source = GEMINI_CLI_AUTH_SOURCE
        base_url = None
        if not model or model.lower() in {"gpt-4o-mini", "default", "auto"}:
            model = GEMINI_CLI_DEFAULT_MODEL
    if provider == "opencode":
        api_key_source = OPENCODE_AUTH_SOURCE
        base_url = None
        if not model or model.lower() in {"gpt-4o-mini", "default", "auto"}:
            model = OPENCODE_DEFAULT_MODEL
    return AiConfig(
        provider_name=provider,
        base_url=base_url,
        wire_api=(data.wire_api or "responses").strip().lower(),
        model=model,
        api_key_source=api_key_source,
        gemini_cli_proxy=(data.gemini_cli_proxy or "").strip() or None,
    )


def _provider_for_config(config: AiConfig) -> AiProvider:
    prompt_builder = PromptBuilder()
    if config.provider_key() == "opencode" or config.uses_opencode_auth():
        return OpenCodeCliProvider(config, prompt_builder)
    if config.provider_key() == "gemini_cli":
        return GeminiCliProvider(config, prompt_builder)
    if config.provider_key() == "gemini" or config.uses_gemini_auth():
        return GeminiProvider(config, prompt_builder)
    return OpenAiProvider(config, prompt_builder)


def _friendly_ai_test_error(exc: Exception) -> str:
    raw = str(exc).strip()
    if "HTTP 403" in raw:
        return (
            "AI 服务拒绝了当前请求。可能是中转接口协议不匹配、"
            "模型无权限或密钥无效。"
        )
    if "<html" in raw.lower() or "<!doctype html" in raw.lower():
        return "AI 服务返回了网页错误页，请检查中转地址、模型权限和密钥。"
    return raw or exc.__class__.__name__


def _live_test_message(provider: str, model: str, transport: Optional[str], elapsed_ms: int) -> str:
    transport_label = transport or "unknown"
    return (
        "真实 AI 请求成功。"
        f"provider={provider}, model={model}, transport={transport_label}, "
        f"elapsed={elapsed_ms}ms"
    )


def _preview_text(value: str) -> str:
    cleaned = " ".join((value or "").split())
    return cleaned[:160]


def _preset_model_list(provider: str, message: str = "") -> AiModelListOut:
    provider_key = provider.strip().lower()
    presets = _model_presets().get(provider_key)
    if presets is None:
        raise HTTPException(400, f"Unsupported provider: {provider}")
    return AiModelListOut(
        provider=provider_key,
        models=presets,
        source="preset",
        message=message or "当前 provider 暂未启用真实模型拉取，已显示内置预设。",
    )


def _live_test_messages() -> list[dict[str, str]]:
    return [
        {
            "role": "user",
            "content": "请轻微润色这句话，只返回润色后的句子：雨夜里，两个人在车站告别。",
        }
    ]


@router.get("/ai", response_model=AiSettingsOut)
def get_ai_settings(
    container: AppContainer = Depends(get_container),
) -> AiSettingsOut:
    return _config_to_out(container.settings.load_ai_config())


@router.get("/ai/models", response_model=AiModelListOut)
def get_ai_models(provider: str, refresh: bool = True) -> AiModelListOut:
    provider_key = provider.strip().lower()
    if provider_key not in PUBLIC_AI_PROVIDERS:
        raise HTTPException(400, f"Unsupported provider: {provider}")
    if provider_key != "opencode":
        return _preset_model_list(provider_key)
    try:
        models = list_opencode_models(refresh=refresh)
    except AiError as exc:
        return _preset_model_list(
            provider_key,
            message=f"OpenCode 模型列表真实拉取失败，已显示内置预设：{_friendly_ai_test_error(exc)}",
        )
    return AiModelListOut(
        provider=provider_key,
        models=models,
        source="live",
        message="已从 OpenCode 真实拉取模型列表。",
    )


@router.get("/data-location", response_model=DataLocationInfo)
def get_data_location(
    container: AppContainer = Depends(get_container),
) -> DataLocationInfo:
    return _data_location_info(container)


@router.post("/data-location/migrate", response_model=DataLocationMigrationResult)
def migrate_data_location(
    data: DataLocationMigrationRequest,
    container: AppContainer = Depends(get_container),
) -> DataLocationMigrationResult:
    current_db = _container_database_path(container)
    current_dir = current_db.parent
    target_dir = _prepare_target_dir(data.target_dir, current_dir)
    target_db = target_dir / DATABASE_FILENAME
    _preflight_auxiliary_dir(current_dir / "backups", target_dir / "backups", data.replace_existing)
    _preflight_auxiliary_dir(current_dir / "checkpoints", target_dir / "checkpoints", data.replace_existing)
    if target_db.exists() and not data.replace_existing:
        raise HTTPException(400, f"{DATABASE_FILENAME} already exists in target_dir")
    try:
        _copy_database(container, target_db, data.replace_existing)
        _copy_auxiliary_dir(current_dir / "backups", target_dir / "backups", data.replace_existing)
        _copy_auxiliary_dir(current_dir / "checkpoints", target_dir / "checkpoints", data.replace_existing)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"Failed to migrate data location: {exc}") from exc
    return DataLocationMigrationResult(
        target_dir=str(target_dir),
        target_database_path=str(target_db),
        restart_required=True,
        message="Data was copied. Restart Living to Tell to use the new location.",
    )


@router.get("/ai/status", response_model=AiSettingsStatus)
def get_ai_settings_status(
    container: AppContainer = Depends(get_container),
) -> AiSettingsStatus:
    return _status_for(container.settings.load_ai_config())


@router.put("/ai", response_model=AiSettingsOut)
def save_ai_settings(
    data: AiSettingsUpdate,
    container: AppContainer = Depends(get_container),
) -> AiSettingsOut:
    config = _request_to_config(data)
    try:
        container.settings.save_ai_config(config)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return _config_to_out(container.settings.load_ai_config())


@router.post("/ai/import-codex", response_model=AiImportOut)
def import_codex_settings(
    container: AppContainer = Depends(get_container),
) -> AiImportOut:
    importer = CodexConfigImporter()
    try:
        result = importer.import_from(importer.default_path())
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, str(exc)) from exc
    if result.is_empty():
        raise HTTPException(404, "No supported Codex fields found")

    current = container.settings.load_ai_config()
    auth_status = CodexAuthResolver().status()
    next_config = AiConfig(
        provider_name="openai",
        base_url=result.base_url or current.base_url,
        wire_api=result.wire_api or current.wire_api,
        model=result.model or current.model,
        api_key_source=CODEX_AUTH_SOURCE if result.requires_openai_auth and auth_status.available else current.api_key_source,
        gemini_cli_proxy=None,
    )
    container.settings.save_ai_config(next_config)
    return AiImportOut(
        config=_config_to_out(container.settings.load_ai_config()),
        imported={
            "base_url": result.base_url,
            "model": result.model,
            "wire_api": result.wire_api,
            "credential_source": CODEX_AUTH_SOURCE if result.requires_openai_auth and auth_status.available else None,
        },
    )


@router.post("/ai/import-gemini", response_model=AiImportOut)
def import_gemini_settings(
    container: AppContainer = Depends(get_container),
) -> AiImportOut:
    importer = GeminiConfigImporter()
    try:
        result = importer.import_default()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, str(exc)) from exc
    if result.is_empty():
        raise HTTPException(404, "No supported Gemini fields found")

    current = container.settings.load_ai_config()
    auth_status = GeminiAuthResolver().status()
    next_config = AiConfig(
        provider_name="gemini",
        base_url=result.base_url or current.base_url,
        wire_api=result.wire_api or current.wire_api,
        model=result.model or current.model,
        api_key_source=GEMINI_AUTH_SOURCE if auth_status.available else current.api_key_source,
        gemini_cli_proxy=None,
    )
    container.settings.save_ai_config(next_config)
    return AiImportOut(
        config=_config_to_out(container.settings.load_ai_config()),
        imported={
            "base_url": result.base_url,
            "model": result.model,
            "wire_api": result.wire_api,
            "credential_source": GEMINI_AUTH_SOURCE if auth_status.available else None,
        },
    )


@router.post("/ai/test", response_model=AiTestOut)
def test_ai_settings(data: AiTestRequest) -> AiTestOut:
    config = _request_to_config(data)
    issues = preflight_rewrite(config, target_text="_", has_entry=True)
    if issues:
        return AiTestOut(ok=False, message=format_issues(issues))
    return AiTestOut(ok=True, message="Local AI configuration check passed. This does not contact the provider.")


@router.post("/ai/test-live", response_model=AiLiveTestOut)
def test_ai_settings_live(data: AiTestRequest) -> AiLiveTestOut:
    config = _request_to_config(data)
    issues = preflight_rewrite(config, target_text="_", has_entry=True)
    if issues:
        return AiLiveTestOut(
            ok=False,
            message=format_issues(issues),
            provider=config.provider_key(),
            model=config.model,
        )

    provider = _provider_for_config(config)
    started = time.perf_counter()
    try:
        response = provider.chat(_live_test_messages(), model=config.model)
    except AiError as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return AiLiveTestOut(
            ok=False,
            message=_friendly_ai_test_error(exc),
            provider=config.provider_key(),
            model=config.model,
            elapsed_ms=elapsed_ms,
        )
    except Exception as exc:  # noqa: BLE001
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return AiLiveTestOut(
            ok=False,
            message=_friendly_ai_test_error(exc),
            provider=config.provider_key(),
            model=config.model,
            elapsed_ms=elapsed_ms,
        )

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return AiLiveTestOut(
        ok=True,
        message=_live_test_message(
            response.provider,
            response.model,
            response.transport,
            elapsed_ms,
        ),
        provider=response.provider,
        model=response.model,
        transport=response.transport,
        elapsed_ms=elapsed_ms,
        preview=_preview_text(response.content),
        cost=response.cost,
    )
