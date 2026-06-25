"""App metadata and public release update-check routes."""
from __future__ import annotations

import json
import re
import time
from threading import Lock
from typing import Any, Optional
from urllib import error as urlerror
from urllib import request as urlrequest

from fastapi import APIRouter
from pydantic import BaseModel

from version_info import API_CAPABILITIES, API_VERSION, APP_DISPLAY_NAME, APP_VERSION

router = APIRouter(prefix="/api/app", tags=["app"])

GITHUB_LATEST_RELEASE_URL = (
    "https://api.github.com/repos/sidiangongyuan/living-to-tell/releases/latest"
)
UPDATE_SOURCE = "github_releases_latest"
UPDATE_CACHE_TTL_SECONDS = 1800
UPDATE_VERSION_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)")
UPDATE_CACHE_LOCK = Lock()
UPDATE_CACHE: dict[str, Any] = {
    "expires_at": 0.0,
    "payload": None,
}


class AppVersionOut(BaseModel):
    app_name: str
    version: str
    api_version: str
    capabilities: list[str]


class AppUpdateCheckOut(BaseModel):
    current_version: str
    latest_version: Optional[str] = None
    latest_tag: Optional[str] = None
    release_name: Optional[str] = None
    release_url: Optional[str] = None
    published_at: Optional[str] = None
    release_notes: str = ""
    source: str
    status: str
    message: str
    checked_at: str
    cached: bool = False
    download_url: Optional[str] = None
    download_name: Optional[str] = None


@router.get("/version", response_model=AppVersionOut)
def app_version() -> AppVersionOut:
    return AppVersionOut(
        app_name=APP_DISPLAY_NAME,
        version=APP_VERSION,
        api_version=API_VERSION,
        capabilities=API_CAPABILITIES,
    )


@router.get("/update-check", response_model=AppUpdateCheckOut)
def update_check(force: bool = False) -> AppUpdateCheckOut:
    now = time.time()
    if not force:
        with UPDATE_CACHE_LOCK:
            cached_payload = UPDATE_CACHE.get("payload")
            expires_at = float(UPDATE_CACHE.get("expires_at") or 0.0)
            if cached_payload and expires_at > now:
                payload = dict(cached_payload)
                payload["cached"] = True
                return AppUpdateCheckOut(**payload)

    payload = _fetch_update_payload()
    with UPDATE_CACHE_LOCK:
        UPDATE_CACHE["payload"] = payload
        UPDATE_CACHE["expires_at"] = now + UPDATE_CACHE_TTL_SECONDS
    return AppUpdateCheckOut(**payload)


def _fetch_update_payload() -> dict[str, Any]:
    checked_at = _utc_now()
    try:
        release = _fetch_latest_release()
    except Exception as exc:  # noqa: BLE001
        return {
            "current_version": APP_VERSION,
            "source": UPDATE_SOURCE,
            "status": "error",
            "message": _friendly_update_error(exc),
            "checked_at": checked_at,
            "cached": False,
        }

    latest_tag = _as_text(release.get("tag_name"))
    latest_version = _extract_version_text(latest_tag) or _extract_version_text(
        release.get("name")
    )
    release_name = _as_text(release.get("name")) or latest_tag or None
    release_url = _as_text(release.get("html_url")) or None
    published_at = _as_text(release.get("published_at")) or None
    release_notes = _clean_release_notes(release.get("body"))
    asset = _pick_windows_asset(release.get("assets"))

    if latest_version and _is_newer_version(APP_VERSION, latest_version):
        return {
            "current_version": APP_VERSION,
            "latest_version": latest_version,
            "latest_tag": latest_tag or None,
            "release_name": release_name,
            "release_url": release_url,
            "published_at": published_at,
            "release_notes": release_notes,
            "source": UPDATE_SOURCE,
            "status": "update_available",
            "message": "发现新版本。请下载最新安装包或点击下载安装包完成更新。",
            "checked_at": checked_at,
            "cached": False,
            "download_url": asset.get("browser_download_url") if asset else release_url,
            "download_name": asset.get("name") if asset else None,
        }

    return {
        "current_version": APP_VERSION,
        "latest_version": latest_version or APP_VERSION,
        "latest_tag": latest_tag or None,
        "release_name": release_name,
        "release_url": release_url,
        "published_at": published_at,
        "release_notes": release_notes,
        "source": UPDATE_SOURCE,
        "status": "up_to_date",
        "message": "当前已是最新版本。",
        "checked_at": checked_at,
        "cached": False,
        "download_url": asset.get("browser_download_url") if asset else release_url,
        "download_name": asset.get("name") if asset else None,
    }


def _fetch_latest_release() -> dict[str, Any]:
    request = urlrequest.Request(
        GITHUB_LATEST_RELEASE_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"LivingToTell/{APP_VERSION}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="GET",
    )
    try:
        with urlrequest.urlopen(request, timeout=15) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except urlerror.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except urlerror.URLError as exc:
        raise RuntimeError(str(exc.reason)) from exc

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("GitHub Release API did not return JSON.") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("GitHub Release API returned an unexpected payload.")
    return payload


def _pick_windows_asset(raw_assets: Any) -> Optional[dict[str, Any]]:
    if not isinstance(raw_assets, list):
        return None
    assets = [item for item in raw_assets if isinstance(item, dict)]
    if not assets:
        return None

    def sort_key(asset: dict[str, Any]) -> tuple[int, int, int]:
        name = _as_text(asset.get("name")).lower()
        return (
            0 if name.endswith("_x64-setup.exe") else 1,
            0 if name.endswith(".exe") else 1,
            0 if name.endswith(".msi") else 1,
        )

    return sorted(assets, key=sort_key)[0]


def _extract_version_text(raw_value: Any) -> Optional[str]:
    text = _as_text(raw_value)
    match = UPDATE_VERSION_RE.search(text)
    if not match:
        return None
    return ".".join(match.groups())


def _version_tuple(raw_value: str) -> Optional[tuple[int, int, int]]:
    match = UPDATE_VERSION_RE.search(raw_value or "")
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


def _is_newer_version(current: str, latest: str) -> bool:
    current_tuple = _version_tuple(current)
    latest_tuple = _version_tuple(latest)
    if current_tuple and latest_tuple:
        return latest_tuple > current_tuple
    return bool(latest and latest != current)


def _clean_release_notes(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()[:20000]


def _as_text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _friendly_update_error(exc: Exception) -> str:
    raw = str(exc).strip()
    lowered = raw.lower()
    if "http 404" in lowered:
        return "暂未找到公开发布版本。"
    if "http 403" in lowered or "rate limit" in lowered:
        return "暂时无法检查更新，可能是 GitHub API 限流或网络受限。"
    if "timed out" in lowered or "timeout" in lowered:
        return "检查更新超时，请稍后重试。"
    if "<html" in lowered or "<!doctype html" in lowered:
        return "检查更新时收到了网页错误页，请稍后重试。"
    if raw:
        return f"暂时无法检查更新：{raw}"
    return "暂时无法检查更新，请稍后重试。"
