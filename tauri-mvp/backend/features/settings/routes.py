"""Settings API routes for the Tauri frontend."""
from __future__ import annotations

import os
import json
import shutil
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional
from urllib import error as urlerror
from urllib.parse import urlparse
from urllib import request as urlrequest

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


def _resolve_api_key_for_source(source: str) -> str:
    normalized = (source or "").strip()
    if normalized.startswith("env:"):
        var = normalized.split(":", 1)[1].strip()
        if not var:
            raise AiError("环境变量名称为空。")
        key = os.environ.get(var, "").strip()
        if not key:
            raise AiError(f"环境变量 {var} 未配置。")
        return key
    if normalized.lower() == CODEX_AUTH_SOURCE:
        return CodexAuthResolver().read_api_key()
    if normalized.lower() == GEMINI_AUTH_SOURCE:
        return GeminiAuthResolver().read_api_key()
    raise AiError("当前凭据来源不能用于远程模型列表拉取。")


def _openai_compatible_models_url(base_url: str) -> str:
    base = (base_url or "").strip().rstrip("/")
    if not base:
        raise AiError("模型列表拉取需要配置 Base URL。")
    lower = base.lower()
    if lower.endswith("/models"):
        return base
    if lower.endswith("/v1") or lower.endswith("/v1beta") or lower.endswith("/openai"):
        return f"{base}/models"
    return f"{base}/v1/models"


def _extract_model_ids(payload: Any) -> list[str]:
    if isinstance(payload, dict):
        candidates = payload.get("data")
        if candidates is None:
            candidates = payload.get("models")
    else:
        candidates = payload
    if not isinstance(candidates, list):
        return []
    models: list[str] = []
    for item in candidates:
        if isinstance(item, str) and item.strip():
            models.append(item.strip())
        elif isinstance(item, dict):
            raw = item.get("id") or item.get("name") or item.get("model") or item.get("model_name")
            if isinstance(raw, str) and raw.strip():
                models.append(raw.strip())
    return list(dict.fromkeys(models))


def _fetch_openai_compatible_models(base_url: str, api_key: str) -> list[str]:
    url = _openai_compatible_models_url(base_url)
    req = urlrequest.Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "LivingToTell/0.1",
        },
        method="GET",
    )
    try:
        with urlrequest.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urlerror.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        raise AiError(f"HTTP {exc.code}: {detail}") from exc
    except urlerror.URLError as exc:
        raise AiError(str(exc.reason)) from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AiError("模型列表接口没有返回 JSON。") from exc
    models = _extract_model_ids(payload)
    if not models:
        raise AiError("模型列表接口没有返回可识别的模型 id。")
    return models


def _pricing_model_list_urls(base_url: str) -> list[str]:
    parsed = urlparse((base_url or "").strip())
    if not parsed.scheme or not parsed.netloc:
        return []
    origin = f"{parsed.scheme}://{parsed.netloc}"
    urls = [f"{origin}/api/pricing"]
    if parsed.netloc.lower() == "elysia.h-e.top":
        urls.append("https://elysiver.h-e.top/api/pricing")
    return list(dict.fromkeys(urls))


def _fetch_public_pricing_models(base_url: str) -> list[str]:
    errors: list[str] = []
    for url in _pricing_model_list_urls(base_url):
        req = urlrequest.Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0 LivingToTell/0.1",
            },
            method="GET",
        )
        try:
            with urlrequest.urlopen(req, timeout=20) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            payload = json.loads(raw)
            models = _extract_model_ids(payload)
            if models:
                return models
            errors.append(f"{url}: no model_name/id fields")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{url}: {_friendly_model_fetch_error(exc)}")
    raise AiError("; ".join(errors) or "没有可用的模型广场接口。")


def _friendly_model_fetch_error(exc: Exception) -> str:
    raw = str(exc).strip()
    lowered = raw.lower()
    if "http 403" in lowered:
        return "模型列表接口拒绝访问，可能是密钥权限、模型广场接口权限或中转站不开放 /v1/models。"
    if "<html" in lowered or "<!doctype html" in lowered:
        return "模型列表接口返回了网页错误页，请检查中转地址和密钥权限。"
    return raw or exc.__class__.__name__


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
def get_ai_models(
    provider: str,
    refresh: bool = True,
    base_url: Optional[str] = None,
    api_key_source: Optional[str] = None,
    container: AppContainer = Depends(get_container),
) -> AiModelListOut:
    provider_key = provider.strip().lower()
    if provider_key not in PUBLIC_AI_PROVIDERS:
        raise HTTPException(400, f"Unsupported provider: {provider}")
    if provider_key == "opencode":
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

    current = container.settings.load_ai_config()
    effective_base_url = (base_url or "").strip() or (
        current.base_url if current.provider_key() == provider_key else ""
    )
    effective_api_key_source = (api_key_source or "").strip() or (
        current.api_key_source if current.provider_key() == provider_key else ""
    )

    if provider_key == "gemini" and (
        not effective_base_url
        or "generativelanguage.googleapis.com" in effective_base_url.lower()
    ):
        return _preset_model_list(
            provider_key,
            message="Google 原生 Gemini 模型列表暂未启用真实拉取；已显示内置预设。自定义中转地址会尝试 /v1/models。",
        )

    if provider_key == "openai" and not effective_base_url:
        effective_base_url = "https://api.openai.com/v1"

    if provider_key in {"openai", "gemini"}:
        try:
            api_key = _resolve_api_key_for_source(effective_api_key_source)
            models = _fetch_openai_compatible_models(effective_base_url, api_key)
        except Exception as exc:  # noqa: BLE001
            if provider_key == "gemini" and effective_base_url:
                try:
                    models = _fetch_public_pricing_models(effective_base_url)
                except Exception as pricing_exc:  # noqa: BLE001
                    return _preset_model_list(
                        provider_key,
                        message=(
                            "模型列表真实拉取失败，已显示内置预设："
                            f"{_friendly_model_fetch_error(exc)}；模型广场也不可用："
                            f"{_friendly_model_fetch_error(pricing_exc)}"
                        ),
                    )
                return AiModelListOut(
                    provider=provider_key,
                    models=models,
                    source="live",
                    message="兼容 /v1/models 被中转拒绝；已从公开模型广场真实拉取模型列表。请注意：模型广场列表不等于当前密钥一定有权限调用每个模型。",
                )
            return _preset_model_list(
                provider_key,
                message=f"模型列表真实拉取失败，已显示内置预设：{_friendly_model_fetch_error(exc)}",
            )
        return AiModelListOut(
            provider=provider_key,
            models=models,
            source="live",
            message="已从兼容模型列表接口真实拉取模型。",
        )

    if provider_key != "opencode":
        return _preset_model_list(provider_key)


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
