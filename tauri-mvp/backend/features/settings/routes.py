"""Settings API routes for the Tauri frontend."""
from __future__ import annotations

import os
import json
import shutil
import sqlite3
import time
import uuid
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib import error as urlerror
from urllib.parse import urlparse
from urllib import request as urlrequest

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from deps import get_container
from features.ai.error_messages import safe_ai_diagnostic
from writer.app.settings import RUNTIME_AUTH_SOURCES, SUPPORTED_WIRE_APIS, Settings
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
from writer.services.ai.interfaces import AiError, AiProvider
from writer.services.ai.opencode_cli_provider import (
    OPENCODE_AUTH_SOURCE,
    OPENCODE_DEFAULT_MODEL,
    OPENCODE_MODEL_PRESETS,
    OpenCodeCliProvider,
    list_opencode_models,
    opencode_auth_status,
)
from writer.services.ai.preflight import format_issues, preflight_rewrite
from writer.services.ai.provider_factory import provider_for_config
from writer.services.ai.prompt_builder import PromptBuilder

router = APIRouter(prefix="/api/settings", tags=["settings"])

OPENAI_MODEL_PRESETS = (
    "gpt-4o-mini",
    "gpt-4.1-mini",
    "gpt-4.1",
    "deepseek-v4-pro",
    "glm-5.2",
)
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


class AiProfileBase(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    name: str
    provider_name: str
    base_url: Optional[str] = None
    wire_api: str = "responses"
    model: str
    api_key_source: str = "env:OPENAI_API_KEY"
    gemini_cli_proxy: Optional[str] = None
    enabled: bool = True
    source_key: Optional[str] = None


class AiProfileCreate(AiProfileBase):
    pass


class AiProfileUpdate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    name: Optional[str] = None
    provider_name: Optional[str] = None
    base_url: Optional[str] = None
    wire_api: Optional[str] = None
    model: Optional[str] = None
    api_key_source: Optional[str] = None
    gemini_cli_proxy: Optional[str] = None
    enabled: Optional[bool] = None
    source_key: Optional[str] = None


class AiProfileOut(AiProfileBase):
    id: str
    created_at: str
    updated_at: str
    is_default: bool = False
    test_status: str = "untested"
    last_tested_at: Optional[str] = None
    last_test_transport: Optional[str] = None
    last_test_elapsed_ms: Optional[int] = None
    diagnostic_code: str = ""
    diagnostic_message: str = ""


class AiProfileListOut(BaseModel):
    profiles: list[AiProfileOut]
    default_profile_id: Optional[str] = None


class AiDefaultProfileUpdate(BaseModel):
    profile_id: str


class AiProfileCheckRequest(BaseModel):
    profile_ids: list[str] = Field(default_factory=list)


class AiDiscoveredProfileOut(AiProfileBase):
    source_key: str
    source_label: str
    available: bool
    reason: str = ""
    existing_profile_id: Optional[str] = None
    live_test_supported: bool = True


class AiProfileImportLocalRequest(BaseModel):
    source_keys: list[str] = []
    update_existing: bool = True


class AiProfileImportLocalOut(BaseModel):
    profiles: list[AiProfileOut]
    imported_count: int
    updated_count: int
    skipped: list[str] = []


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


class AiProfileLiveTestOut(BaseModel):
    profile: AiProfileOut
    test: AiLiveTestOut


class AiModelListOut(BaseModel):
    provider: str
    models: list[str]
    source: str
    message: str = ""


class AiLocalKeySaveRequest(BaseModel):
    api_key: str
    provider_name: str = "openai"
    model: str = ""
    profile_id: Optional[str] = None
    label: Optional[str] = None
    env_var: Optional[str] = None


class AiLocalKeySaveOut(BaseModel):
    api_key_source: str
    env_var: str
    message: str
    persisted: bool


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


_ENV_VAR_RE = re.compile(r"^[A-Z_][A-Z0-9_]{1,80}$")


def _local_key_env_name(data: AiLocalKeySaveRequest, profiles: Optional[list[AiProfileOut]] = None) -> str:
    requested = (data.env_var or "").strip().upper()
    if requested:
        if not _ENV_VAR_RE.match(requested):
            raise HTTPException(400, "环境变量名只能包含大写字母、数字和下划线，且不能以数字开头。")
        return requested

    profile_id = (data.profile_id or "").strip()
    if profile_id:
        for profile in profiles or []:
            if profile.id != profile_id:
                continue
            source = (profile.api_key_source or "").strip()
            if source.startswith("env:LTT_AI_"):
                existing = source.split(":", 1)[1].strip().upper()
                if existing and _ENV_VAR_RE.match(existing):
                    return existing
        cleaned = re.sub(r"[^A-Za-z0-9]", "", profile_id).upper()[:12]
        if cleaned:
            return f"LTT_AI_PROFILE_{cleaned}_KEY"

    label = (data.label or "").strip()
    provider = re.sub(r"[^A-Za-z0-9]", "_", (data.provider_name or "AI").upper()).strip("_")
    if label.lower() == "default":
        return f"LTT_AI_{provider or 'DEFAULT'}_KEY"

    seed = "|".join(
        [
            label,
            data.provider_name or "",
            data.model or "",
            uuid.uuid4().hex,
        ]
    )
    suffix = uuid.uuid5(uuid.NAMESPACE_URL, seed).hex[:10].upper()
    return f"LTT_AI_KEY_{suffix}"


def _broadcast_environment_change() -> None:
    if os.name != "nt":
        return
    try:
        import ctypes

        hwnd_broadcast = 0xFFFF
        wm_settingchange = 0x001A
        smto_abortifhung = 0x0002
        result = ctypes.c_ulong()
        ctypes.windll.user32.SendMessageTimeoutW(
            hwnd_broadcast,
            wm_settingchange,
            0,
            "Environment",
            smto_abortifhung,
            5000,
            ctypes.byref(result),
        )
    except Exception:  # noqa: BLE001
        pass


def _set_user_environment_variable(name: str, value: str) -> bool:
    os.environ[name] = value
    if os.name != "nt":
        return False

    try:
        import winreg

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
        _broadcast_environment_change()
        return True
    except OSError as exc:
        raise HTTPException(500, f"无法写入 Windows 用户环境变量：{exc}") from exc


def _delete_user_environment_variable(name: str) -> bool:
    if os.name != "nt":
        os.environ.pop(name, None)
        return False
    try:
        import winreg

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            try:
                winreg.DeleteValue(key, name)
            except FileNotFoundError:
                pass
        os.environ.pop(name, None)
        _broadcast_environment_change()
        return True
    except OSError as exc:
        raise HTTPException(500, "无法删除 Windows 用户环境变量，请稍后重试。") from exc


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
    wire_api = (data.wire_api or "responses").strip().lower()
    if wire_api not in SUPPORTED_WIRE_APIS:
        raise HTTPException(
            400,
            f"Unsupported wire_api: {data.wire_api}. Supported values: {', '.join(SUPPORTED_WIRE_APIS)}",
        )
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
    if api_key_source.startswith("literal:"):
        raise HTTPException(
            400,
            "literal:<key> is not supported. Use an environment variable, save the key locally from Settings, or use a local auth source.",
        )
    if (
        api_key_source
        and api_key_source.lower() not in RUNTIME_AUTH_SOURCES
        and not api_key_source.startswith("env:")
    ):
        raise HTTPException(
            400,
            "Unsupported api_key_source. Use env:VARNAME, codex, gemini, gemini-cli, or opencode.",
        )
    return AiConfig(
        provider_name=provider,
        base_url=base_url,
        wire_api=wire_api,
        model=model,
        api_key_source=api_key_source,
        gemini_cli_proxy=(data.gemini_cli_proxy or "").strip() or None,
    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _config_to_profile_payload(
    *,
    profile_id: str,
    name: str,
    config: AiConfig,
    enabled: bool,
    created_at: str,
    updated_at: str,
    source_key: Optional[str] = None,
) -> dict[str, Any]:
    cleaned_source_key = (source_key or "").strip() or None
    return {
        "id": profile_id,
        "name": name.strip()[:80],
        "provider_name": config.provider_key(),
        "base_url": config.base_url,
        "wire_api": config.wire_api,
        "model": config.model,
        "api_key_source": config.api_key_source,
        "gemini_cli_proxy": config.gemini_cli_proxy,
        "enabled": bool(enabled),
        "source_key": cleaned_source_key,
        "created_at": created_at,
        "updated_at": updated_at,
    }


def _profile_base_to_payload(
    data: AiProfileBase,
    *,
    profile_id: str,
    created_at: str,
    updated_at: str,
) -> dict[str, Any]:
    name = data.name.strip()
    if not name:
        raise HTTPException(400, "Profile name is required")
    config = _request_to_config(
        AiSettingsUpdate(
            provider_name=data.provider_name,
            base_url=data.base_url,
            wire_api=data.wire_api,
            model=data.model,
            api_key_source=data.api_key_source,
            gemini_cli_proxy=data.gemini_cli_proxy,
        )
    )
    if not (config.model or "").strip():
        raise HTTPException(400, "Model is required")
    return _config_to_profile_payload(
        profile_id=profile_id,
        name=name,
        config=config,
        enabled=data.enabled,
        created_at=created_at,
        updated_at=updated_at,
        source_key=data.source_key,
    )


def _profile_out_from_raw(
    raw: dict[str, Any],
    *,
    default_profile_id: Optional[str] = None,
    health: Optional[dict[str, Any]] = None,
) -> Optional[AiProfileOut]:
    profile_id = str(raw.get("id") or "").strip()
    name = str(raw.get("name") or "").strip()
    if not profile_id or not name:
        return None
    try:
        payload = _profile_base_to_payload(
            AiProfileBase(
                name=name,
                provider_name=str(raw.get("provider_name") or "openai"),
                base_url=raw.get("base_url") if raw.get("base_url") is not None else None,
                wire_api=str(raw.get("wire_api") or "responses"),
                model=str(raw.get("model") or ""),
                api_key_source=str(raw.get("api_key_source") or "env:OPENAI_API_KEY"),
                gemini_cli_proxy=raw.get("gemini_cli_proxy")
                if raw.get("gemini_cli_proxy") is not None
                else None,
                enabled=bool(raw.get("enabled", True)),
                source_key=str(raw.get("source_key") or "").strip() or None,
            ),
            profile_id=profile_id,
            created_at=str(raw.get("created_at") or _utc_now()),
            updated_at=str(raw.get("updated_at") or raw.get("created_at") or _utc_now()),
        )
    except HTTPException:
        return None
    health_data = dict(health or {})
    fingerprint = str(health_data.get("fingerprint") or "")
    current_fingerprint = Settings.ai_profile_fingerprint(payload)
    test_status = str(health_data.get("test_status") or "untested")
    if fingerprint and fingerprint != current_fingerprint and test_status != "untested":
        test_status = "stale"
    if test_status not in {"untested", "passed", "failed", "stale"}:
        test_status = "untested"
    return AiProfileOut(
        **payload,
        is_default=profile_id == default_profile_id,
        test_status=test_status,
        last_tested_at=health_data.get("last_tested_at"),
        last_test_transport=health_data.get("last_test_transport"),
        last_test_elapsed_ms=health_data.get("last_test_elapsed_ms"),
        diagnostic_code=str(health_data.get("diagnostic_code") or ""),
        diagnostic_message=str(health_data.get("diagnostic_message") or ""),
    )


def _load_ai_profiles(container: AppContainer) -> list[AiProfileOut]:
    raw_profiles, default_profile_id = container.settings.ensure_ai_profile_defaults()
    health = container.settings.load_ai_profile_health()
    profiles: list[AiProfileOut] = []
    seen: set[str] = set()
    for raw in raw_profiles:
        profile_id = str(raw.get("id") or "").strip()
        profile = _profile_out_from_raw(
            raw,
            default_profile_id=default_profile_id,
            health=health.get(profile_id),
        )
        if profile is None or profile.id in seen:
            continue
        seen.add(profile.id)
        profiles.append(profile)
    return profiles


def _save_ai_profiles(container: AppContainer, profiles: list[AiProfileOut]) -> None:
    fields = set(AiProfileBase.model_fields) | {"id", "created_at", "updated_at"}
    container.settings.save_ai_provider_profiles(
        [
            {
                key: value
                for key, value in profile.model_dump().items()
                if key in fields
            }
            for profile in profiles
        ]
    )


def _profile_signature(profile: AiProfileOut) -> tuple[str, str, str, str, str]:
    return (
        profile.provider_name,
        profile.base_url or "",
        profile.wire_api or "",
        profile.model or "",
        profile.api_key_source or "",
    )


def _existing_profile_id_for_candidate(
    candidate: AiDiscoveredProfileOut,
    profiles: list[AiProfileOut],
) -> Optional[str]:
    if candidate.source_key:
        for profile in profiles:
            if (profile.source_key or "") == candidate.source_key:
                return profile.id
    candidate_sig = _profile_signature(AiProfileOut(
        id="candidate",
        created_at=_utc_now(),
        updated_at=_utc_now(),
        **candidate.model_dump(),
    ))
    for profile in profiles:
        if _profile_signature(profile) == candidate_sig:
            return profile.id
    return None


def _discovery_reason(prefix: str, exc: Exception) -> str:
    _code, message = _safe_ai_diagnostic(exc)
    return f"{prefix}：{message}"


def _discovered_opencode_profile() -> AiDiscoveredProfileOut:
    status = opencode_auth_status()
    return AiDiscoveredProfileOut(
        name="OpenCode · DeepSeek v4 Flash Free",
        provider_name="opencode",
        base_url=None,
        wire_api="responses",
        model=OPENCODE_DEFAULT_MODEL,
        api_key_source=OPENCODE_AUTH_SOURCE,
        gemini_cli_proxy=None,
        enabled=True,
        source_key="local:opencode",
        source_label="OpenCode 本机登录",
        available=status.available,
        reason="" if status.available else _safe_ai_diagnostic(status.reason or "missing_login")[1],
    )


def _discovered_codex_profile() -> AiDiscoveredProfileOut:
    importer = CodexConfigImporter()
    auth_status = CodexAuthResolver().status()
    try:
        result = importer.import_from(importer.default_path())
    except Exception as exc:  # noqa: BLE001
        return AiDiscoveredProfileOut(
            name="Codex / OpenAI 本机配置",
            provider_name="openai",
            base_url=None,
            wire_api="responses",
            model="gpt-4o-mini",
            api_key_source=CODEX_AUTH_SOURCE,
            gemini_cli_proxy=None,
            enabled=True,
            source_key="local:codex",
            source_label="Codex 本机配置",
            available=False,
            reason=_discovery_reason("未找到可导入的 Codex 配置", exc),
        )
    model = result.model or "gpt-4o-mini"
    wire_api = result.wire_api if result.wire_api in SUPPORTED_WIRE_APIS else "responses"
    return AiDiscoveredProfileOut(
        name=f"Codex / OpenAI · {model}",
        provider_name="openai",
        base_url=result.base_url,
        wire_api=wire_api,
        model=model,
        api_key_source=CODEX_AUTH_SOURCE if auth_status.available else "env:OPENAI_API_KEY",
        gemini_cli_proxy=None,
        enabled=True,
        source_key="local:codex",
        source_label="Codex 本机配置",
        available=auth_status.available and not result.is_empty(),
        reason="" if auth_status.available else _safe_ai_diagnostic(auth_status.reason or "missing_login")[1],
    )


def _discovered_gemini_profile() -> AiDiscoveredProfileOut:
    importer = GeminiConfigImporter()
    auth_status = GeminiAuthResolver().status()
    try:
        result = importer.import_default()
    except Exception as exc:  # noqa: BLE001
        return AiDiscoveredProfileOut(
            name="Gemini 本机配置",
            provider_name="gemini",
            base_url=None,
            wire_api="responses",
            model="gemini-2.5-flash",
            api_key_source=GEMINI_AUTH_SOURCE,
            gemini_cli_proxy=None,
            enabled=True,
            source_key="local:gemini",
            source_label="Gemini .env",
            available=False,
            reason=_discovery_reason("未找到可导入的 Gemini 配置", exc),
        )
    model = result.model or "gemini-2.5-flash"
    return AiDiscoveredProfileOut(
        name=f"Gemini · {model}",
        provider_name="gemini",
        base_url=result.base_url,
        wire_api=result.wire_api or "responses",
        model=model,
        api_key_source=GEMINI_AUTH_SOURCE,
        gemini_cli_proxy=None,
        enabled=True,
        source_key="local:gemini",
        source_label="Gemini .env",
        available=auth_status.available and not result.is_empty(),
        reason="" if auth_status.available else _safe_ai_diagnostic(auth_status.reason or "missing_var")[1],
    )


def _discover_local_ai_profiles(container: AppContainer) -> list[AiDiscoveredProfileOut]:
    profiles = _load_ai_profiles(container)
    discovered = [
        _discovered_opencode_profile(),
        _discovered_codex_profile(),
        _discovered_gemini_profile(),
    ]
    out: list[AiDiscoveredProfileOut] = []
    for candidate in discovered:
        payload = candidate.model_dump()
        payload["existing_profile_id"] = _existing_profile_id_for_candidate(candidate, profiles)
        out.append(AiDiscoveredProfileOut(**payload))
    return out


def _provider_for_config(config: AiConfig) -> AiProvider:
    return provider_for_config(config, PromptBuilder())


def _profile_config(profile: AiProfileOut) -> AiConfig:
    return AiConfig(
        provider_name=profile.provider_name,
        base_url=profile.base_url,
        wire_api=profile.wire_api,
        model=profile.model,
        api_key_source=profile.api_key_source,
        gemini_cli_proxy=profile.gemini_cli_proxy,
    )


def _safe_ai_diagnostic(value: Any) -> tuple[str, str]:
    return safe_ai_diagnostic(value)


def _friendly_ai_test_error(exc: Exception | str) -> str:
    return _safe_ai_diagnostic(exc)[1]


def _profile_health_entry(
    profile: AiProfileOut,
    *,
    status: str,
    diagnostic_code: str = "",
    diagnostic_message: str = "",
    transport: Optional[str] = None,
    elapsed_ms: Optional[int] = None,
    tested: bool = False,
) -> dict[str, Any]:
    return {
        "fingerprint": Settings.ai_profile_fingerprint(profile.model_dump()),
        "test_status": status,
        "last_tested_at": _utc_now() if tested else profile.last_tested_at,
        "last_test_transport": transport if tested else profile.last_test_transport,
        "last_test_elapsed_ms": elapsed_ms if tested else profile.last_test_elapsed_ms,
        "diagnostic_code": diagnostic_code,
        "diagnostic_message": diagnostic_message,
    }


def _save_profile_health(
    container: AppContainer,
    profile: AiProfileOut,
    entry: dict[str, Any],
) -> AiProfileOut:
    health = container.settings.load_ai_profile_health()
    health[profile.id] = entry
    container.settings.save_ai_profile_health(health)
    return next(item for item in _load_ai_profiles(container) if item.id == profile.id)


def _profile_list_out(container: AppContainer) -> AiProfileListOut:
    profiles = _load_ai_profiles(container)
    return AiProfileListOut(
        profiles=profiles,
        default_profile_id=container.settings.load_ai_default_profile_id(),
    )


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
    code, message = safe_ai_diagnostic(exc)
    if code == "forbidden":
        return "模型列表接口拒绝访问，可能是密钥权限、模型广场接口权限或中转站不开放 /v1/models。"
    if code == "html_response":
        return "模型列表接口返回了网页错误页，请检查中转地址和密钥权限。"
    return message


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


@router.get("/ai/profiles", response_model=AiProfileListOut)
def list_ai_profiles(
    container: AppContainer = Depends(get_container),
) -> AiProfileListOut:
    return _profile_list_out(container)


@router.put("/ai/default-profile", response_model=AiProfileListOut)
def set_default_ai_profile(
    data: AiDefaultProfileUpdate,
    container: AppContainer = Depends(get_container),
) -> AiProfileListOut:
    profile_id = (data.profile_id or "").strip()
    profiles = _load_ai_profiles(container)
    selected = next((item for item in profiles if item.id == profile_id), None)
    if selected is None:
        raise HTTPException(404, "AI 配置档案不存在，请刷新后重试。")
    if not selected.enabled:
        raise HTTPException(400, "已停用的档案不能设为默认，请先启用它。")
    container.settings.save_ai_default_profile_id(selected.id)
    container.settings.save_ai_config(_profile_config(selected))
    return _profile_list_out(container)


@router.post("/ai/profiles/check", response_model=AiProfileListOut)
def check_ai_profiles(
    data: AiProfileCheckRequest,
    container: AppContainer = Depends(get_container),
) -> AiProfileListOut:
    selected_ids = {str(item).strip() for item in data.profile_ids if str(item).strip()}
    profiles = _load_ai_profiles(container)
    health = container.settings.load_ai_profile_health()
    for profile in profiles:
        if selected_ids and profile.id not in selected_ids:
            continue
        issues = preflight_rewrite(_profile_config(profile), target_text="_", has_entry=True)
        if issues:
            code, message = _safe_ai_diagnostic(format_issues(issues))
            health[profile.id] = _profile_health_entry(
                profile,
                status="failed",
                diagnostic_code=code,
                diagnostic_message=message,
            )
        elif profile.test_status != "passed":
            health[profile.id] = _profile_health_entry(profile, status="untested")
    container.settings.save_ai_profile_health(health)
    return _profile_list_out(container)


@router.post("/ai/profiles/{profile_id}/test-live", response_model=AiProfileLiveTestOut)
def test_ai_profile_live(
    profile_id: str,
    container: AppContainer = Depends(get_container),
) -> AiProfileLiveTestOut:
    profile = next((item for item in _load_ai_profiles(container) if item.id == profile_id), None)
    if profile is None:
        raise HTTPException(404, "AI 配置档案不存在，请刷新后重试。")
    config = _profile_config(profile)
    issues = preflight_rewrite(config, target_text="_", has_entry=True)
    if issues:
        code, message = _safe_ai_diagnostic(format_issues(issues))
        updated = _save_profile_health(
            container,
            profile,
            _profile_health_entry(
                profile,
                status="failed",
                diagnostic_code=code,
                diagnostic_message=message,
                tested=True,
            ),
        )
        return AiProfileLiveTestOut(
            profile=updated,
            test=AiLiveTestOut(ok=False, message=message, provider=config.provider_key(), model=config.model),
        )

    started = time.perf_counter()
    try:
        response = _provider_for_config(config).chat(_live_test_messages(), model=config.model)
    except Exception as exc:  # noqa: BLE001
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        code, message = _safe_ai_diagnostic(exc)
        updated = _save_profile_health(
            container,
            profile,
            _profile_health_entry(
                profile,
                status="failed",
                diagnostic_code=code,
                diagnostic_message=message,
                elapsed_ms=elapsed_ms,
                tested=True,
            ),
        )
        return AiProfileLiveTestOut(
            profile=updated,
            test=AiLiveTestOut(
                ok=False,
                message=message,
                provider=config.provider_key(),
                model=config.model,
                elapsed_ms=elapsed_ms,
            ),
        )

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    updated = _save_profile_health(
        container,
        profile,
        _profile_health_entry(
            profile,
            status="passed",
            transport=response.transport,
            elapsed_ms=elapsed_ms,
            tested=True,
        ),
    )
    return AiProfileLiveTestOut(
        profile=updated,
        test=AiLiveTestOut(
            ok=True,
            message="真实请求已通过。",
            provider=response.provider or config.provider_key(),
            model=response.model or config.model,
            transport=response.transport,
            elapsed_ms=elapsed_ms,
            preview=_preview_text(response.content),
            cost=response.cost,
        ),
    )


@router.post("/ai/local-key", response_model=AiLocalKeySaveOut)
def save_ai_local_key(
    data: AiLocalKeySaveRequest,
    container: AppContainer = Depends(get_container),
) -> AiLocalKeySaveOut:
    key = (data.api_key or "").strip()
    if not key:
        raise HTTPException(400, "API Key 不能为空。")
    if "\n" in key or "\r" in key:
        raise HTTPException(400, "API Key 不能包含换行。")

    profiles = _load_ai_profiles(container)
    env_var = _local_key_env_name(data, profiles)
    persisted = _set_user_environment_variable(env_var, key)
    profile_id = (data.profile_id or "").strip()
    profile = next((item for item in profiles if item.id == profile_id), None)
    if profile is not None:
        health = container.settings.load_ai_profile_health()
        previous = dict(health.get(profile.id) or {})
        previous.update(
            {
                "fingerprint": Settings.ai_profile_fingerprint(profile.model_dump()),
                "test_status": "stale",
                "diagnostic_code": "",
                "diagnostic_message": "凭据已更新，请重新发送真实测试。",
            }
        )
        health[profile.id] = previous
        container.settings.save_ai_profile_health(health)
    return AiLocalKeySaveOut(
        api_key_source=f"env:{env_var}",
        env_var=env_var,
        persisted=persisted,
        message=(
            f"密钥已保存到 Windows 用户环境变量 {env_var}。"
            if persisted
            else f"密钥已写入当前应用进程环境变量 {env_var}；当前系统不支持自动持久化，请在重启应用前手动同步。"
        ),
    )


@router.get("/ai/profiles/discover", response_model=list[AiDiscoveredProfileOut])
def discover_ai_profiles(
    container: AppContainer = Depends(get_container),
) -> list[AiDiscoveredProfileOut]:
    return _discover_local_ai_profiles(container)


@router.post("/ai/profiles/import-local", response_model=AiProfileImportLocalOut)
def import_local_ai_profiles(
    data: AiProfileImportLocalRequest,
    container: AppContainer = Depends(get_container),
) -> AiProfileImportLocalOut:
    selected = {item.strip() for item in data.source_keys if item.strip()}
    discovered = [
        item for item in _discover_local_ai_profiles(container)
        if (not selected or item.source_key in selected)
    ]
    profiles = _load_ai_profiles(container)
    now = _utc_now()
    imported_count = 0
    updated_count = 0
    skipped: list[str] = []

    for candidate in discovered:
        if not candidate.available:
            skipped.append(f"{candidate.source_label}: {candidate.reason or '不可用'}")
            continue
        payload = _profile_base_to_payload(
            AiProfileBase(**candidate.model_dump()),
            profile_id=candidate.existing_profile_id or uuid.uuid4().hex,
            created_at=now,
            updated_at=now,
        )
        next_profile = AiProfileOut(**payload)
        existing_index = next(
            (
                index for index, profile in enumerate(profiles)
                if profile.id == next_profile.id
                or ((profile.source_key or "") and profile.source_key == next_profile.source_key)
            ),
            -1,
        )
        if existing_index >= 0:
            if not data.update_existing:
                skipped.append(f"{candidate.source_label}: 已存在")
                continue
            existing = profiles[existing_index]
            payload["id"] = existing.id
            payload["created_at"] = existing.created_at
            payload["updated_at"] = now
            profiles[existing_index] = AiProfileOut(**payload)
            updated_count += 1
        else:
            profiles.append(next_profile)
            imported_count += 1

    _save_ai_profiles(container, profiles)
    if profiles and not container.settings.load_ai_default_profile_id():
        first_enabled = next((item for item in profiles if item.enabled), None)
        if first_enabled is not None:
            container.settings.save_ai_default_profile_id(first_enabled.id)
            container.settings.save_ai_config(_profile_config(first_enabled))
    return AiProfileImportLocalOut(
        profiles=_load_ai_profiles(container),
        imported_count=imported_count,
        updated_count=updated_count,
        skipped=skipped,
    )


@router.post("/ai/profiles", response_model=AiProfileOut, status_code=201)
def create_ai_profile(
    data: AiProfileCreate,
    container: AppContainer = Depends(get_container),
) -> AiProfileOut:
    profiles = _load_ai_profiles(container)
    now = _utc_now()
    payload = _profile_base_to_payload(
        data,
        profile_id=uuid.uuid4().hex,
        created_at=now,
        updated_at=now,
    )
    profile = AiProfileOut(**payload)
    profiles.append(profile)
    _save_ai_profiles(container, profiles)
    if profile.enabled and not container.settings.load_ai_default_profile_id():
        container.settings.save_ai_default_profile_id(profile.id)
        container.settings.save_ai_config(_profile_config(profile))
    return next(item for item in _load_ai_profiles(container) if item.id == profile.id)


@router.put("/ai/profiles/{profile_id}", response_model=AiProfileOut)
def update_ai_profile(
    profile_id: str,
    data: AiProfileUpdate,
    container: AppContainer = Depends(get_container),
) -> AiProfileOut:
    profiles = _load_ai_profiles(container)
    existing_index = next((index for index, item in enumerate(profiles) if item.id == profile_id), -1)
    if existing_index < 0:
        raise HTTPException(404, "AI 配置档案不存在，请刷新后重试。")

    existing = profiles[existing_index]
    merged = existing.model_dump()
    for field in data.model_fields_set:
        merged[field] = getattr(data, field)
    payload = _profile_base_to_payload(
        AiProfileBase(
            name=str(merged.get("name") or ""),
            provider_name=str(merged.get("provider_name") or "openai"),
            base_url=merged.get("base_url"),
            wire_api=str(merged.get("wire_api") or "responses"),
            model=str(merged.get("model") or ""),
            api_key_source=str(merged.get("api_key_source") or "env:OPENAI_API_KEY"),
            gemini_cli_proxy=merged.get("gemini_cli_proxy"),
            enabled=bool(merged.get("enabled", True)),
            source_key=str(merged.get("source_key") or "").strip() or None,
        ),
        profile_id=existing.id,
        created_at=existing.created_at,
        updated_at=_utc_now(),
    )
    updated = AiProfileOut(**payload)
    if container.settings.load_ai_default_profile_id() == updated.id and not updated.enabled:
        raise HTTPException(400, "默认档案不能停用，请先选择另一个默认档案。")
    profiles[existing_index] = updated
    _save_ai_profiles(container, profiles)
    health = container.settings.load_ai_profile_health()
    previous_health = health.get(updated.id)
    if previous_health and str(previous_health.get("fingerprint") or "") != Settings.ai_profile_fingerprint(updated.model_dump()):
        previous_health["test_status"] = "stale"
        previous_health["diagnostic_code"] = ""
        previous_health["diagnostic_message"] = "配置已变更，请重新发送真实测试。"
        health[updated.id] = previous_health
        container.settings.save_ai_profile_health(health)
    if container.settings.load_ai_default_profile_id() == updated.id:
        container.settings.save_ai_config(_profile_config(updated))
    return next(item for item in _load_ai_profiles(container) if item.id == updated.id)


@router.delete("/ai/profiles/{profile_id}", status_code=204)
def delete_ai_profile(
    profile_id: str,
    replacement_profile_id: Optional[str] = Query(None),
    delete_local_key: bool = Query(False),
    container: AppContainer = Depends(get_container),
):
    profiles = _load_ai_profiles(container)
    target = next((item for item in profiles if item.id == profile_id), None)
    if target is None:
        raise HTTPException(404, "AI 配置档案不存在，请刷新后重试。")
    replacement_id = (replacement_profile_id or "").strip()
    replacement = next((item for item in profiles if item.id == replacement_id), None)
    is_default = container.settings.load_ai_default_profile_id() == profile_id
    agent_refs = container.collection_agent_repository.collection_ids_for_profile(profile_id)
    if (is_default or agent_refs) and replacement is None:
        reason = "默认档案" if is_default else "作品集 Agent 正在使用这个档案"
        raise HTTPException(400, f"{reason}，删除前请选择替代档案。")
    if replacement is not None and (replacement.id == profile_id or not replacement.enabled):
        raise HTTPException(400, "替代档案必须是另一个已启用档案。")

    env_name = ""
    if delete_local_key:
        source = (target.api_key_source or "").strip()
        env_name = source.split(":", 1)[1].strip() if source.startswith("env:") else ""
        shared = any(
            item.id != target.id and item.api_key_source == target.api_key_source
            for item in profiles
        )
        if not env_name.startswith("LTT_AI_") or shared:
            raise HTTPException(400, "这个密钥不是档案专属的 LTT_AI_* 变量，或仍被其他档案使用，不能自动删除。")

    remaining = [item for item in profiles if item.id != profile_id]
    if agent_refs and replacement is not None:
        container.collection_agent_repository.replace_profile(profile_id, replacement.id)
    if is_default and replacement is not None:
        container.settings.save_ai_default_profile_id(replacement.id)
        container.settings.save_ai_config(_profile_config(replacement))
    if delete_local_key:
        _delete_user_environment_variable(env_name)

    _save_ai_profiles(container, remaining)
    health = container.settings.load_ai_profile_health()
    health.pop(profile_id, None)
    container.settings.save_ai_profile_health(health)


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
        default_profile_id = container.settings.load_ai_default_profile_id()
        if default_profile_id:
            raw_profiles = container.settings.load_ai_provider_profiles()
            for raw in raw_profiles:
                if str(raw.get("id") or "").strip() != default_profile_id:
                    continue
                raw.update(
                    {
                        "provider_name": config.provider_key(),
                        "base_url": config.base_url,
                        "wire_api": config.wire_api,
                        "model": config.model,
                        "api_key_source": config.api_key_source,
                        "gemini_cli_proxy": config.gemini_cli_proxy,
                        "updated_at": _utc_now(),
                    }
                )
                container.settings.save_ai_provider_profiles(raw_profiles)
                break
        container.settings.save_ai_config(config)
        profiles, migrated_default_id = container.settings.ensure_ai_profile_defaults()
        if not migrated_default_id:
            now = _utc_now()
            raw = _config_to_profile_payload(
                profile_id=uuid.uuid4().hex,
                name="原默认配置",
                config=config,
                enabled=True,
                created_at=now,
                updated_at=now,
            )
            profiles.append(raw)
            container.settings.save_ai_provider_profiles(profiles)
            container.settings.save_ai_default_profile_id(str(raw["id"]))
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
        return AiTestOut(ok=False, message=_friendly_ai_test_error(format_issues(issues)))
    return AiTestOut(ok=True, message="Local AI configuration check passed. This does not contact the provider.")


@router.post("/ai/test-live", response_model=AiLiveTestOut)
def test_ai_settings_live(data: AiTestRequest) -> AiLiveTestOut:
    config = _request_to_config(data)
    issues = preflight_rewrite(config, target_text="_", has_entry=True)
    if issues:
        return AiLiveTestOut(
            ok=False,
            message=_friendly_ai_test_error(format_issues(issues)),
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
