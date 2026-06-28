"""App metadata and public release update-check routes."""
from __future__ import annotations

import json
import hashlib
import os
import re
import tempfile
import time
from pathlib import Path
from threading import Lock
from typing import Any, Optional
from urllib import parse as urlparse
from urllib import error as urlerror
from urllib import request as urlrequest

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from version_info import API_CAPABILITIES, API_VERSION, APP_DISPLAY_NAME, APP_VERSION

router = APIRouter(prefix="/api/app", tags=["app"])

GITHUB_LATEST_RELEASE_URL = (
    "https://api.github.com/repos/sidiangongyuan/living-to-tell/releases/latest"
)
GITHUB_LATEST_RELEASE_REDIRECT_URL = (
    "https://github.com/sidiangongyuan/living-to-tell/releases/latest"
)
GITHUB_RELEASE_URL_PREFIX = "https://github.com/sidiangongyuan/living-to-tell/releases"
UPDATE_SOURCE = "github_releases_latest"
UPDATE_SOURCE_REDIRECT = "github_releases_latest_redirect"
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
    download_sha256: Optional[str] = None
    network_proxy: Optional[str] = None
    network_detail: Optional[str] = None


class AppUpdateDownloadRequest(BaseModel):
    download_url: str
    download_name: Optional[str] = None
    expected_sha256: Optional[str] = None


class AppUpdateDownloadOut(BaseModel):
    status: str
    message: str
    file_path: str
    file_name: str
    size_bytes: int
    sha256: str
    downloaded_at: str


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


@router.post("/update-download", response_model=AppUpdateDownloadOut)
def update_download(data: AppUpdateDownloadRequest) -> AppUpdateDownloadOut:
    try:
        url = _validate_update_download_url(data.download_url)
        file_name = _safe_update_file_name(data.download_name or Path(urlparse.urlparse(url).path).name)
        expected_sha256 = _normalise_sha256(data.expected_sha256)
        updates_dir = _updates_download_dir()
        updates_dir.mkdir(parents=True, exist_ok=True)
        _cleanup_old_update_downloads(updates_dir)
        target = updates_dir / file_name
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        size_bytes, sha256 = _download_update_file(url, target)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=_friendly_download_error(exc)) from exc

    if expected_sha256 and sha256.lower() != expected_sha256.lower():
        try:
            target.unlink()
        except OSError:
            pass
        raise HTTPException(status_code=502, detail="安装包校验失败：下载文件的 SHA256 与发布页不一致。")

    return AppUpdateDownloadOut(
        status="downloaded",
        message="安装包已下载，准备启动安装器。",
        file_path=str(target),
        file_name=file_name,
        size_bytes=size_bytes,
        sha256=sha256.upper(),
        downloaded_at=_utc_now(),
    )


def _fetch_update_payload() -> dict[str, Any]:
    checked_at = _utc_now()
    proxy_summary = _proxy_summary()
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
            "network_proxy": proxy_summary,
            "network_detail": _safe_error_detail(exc),
        }

    source = _as_text(release.get("_source")) or UPDATE_SOURCE
    latest_tag = _as_text(release.get("tag_name"))
    latest_version = _extract_version_text(latest_tag) or _extract_version_text(
        release.get("name")
    )
    release_name = _as_text(release.get("name")) or latest_tag or None
    release_url = _as_text(release.get("html_url")) or None
    published_at = _as_text(release.get("published_at")) or None
    release_notes = _clean_release_notes(release.get("body"))
    asset = _pick_windows_asset(release.get("assets"))
    download_sha256 = _asset_sha256(asset)

    if latest_version and _is_newer_version(APP_VERSION, latest_version):
        return {
            "current_version": APP_VERSION,
            "latest_version": latest_version,
            "latest_tag": latest_tag or None,
            "release_name": release_name,
            "release_url": release_url,
            "published_at": published_at,
            "release_notes": release_notes,
            "source": source,
            "status": "update_available",
            "message": "发现新版本。可以在应用内下载安装包并启动安装。",
            "checked_at": checked_at,
            "cached": False,
            "download_url": asset.get("browser_download_url") if asset else release_url,
            "download_name": asset.get("name") if asset else None,
            "download_sha256": download_sha256,
            "network_proxy": proxy_summary,
            "network_detail": None,
        }

    return {
        "current_version": APP_VERSION,
        "latest_version": latest_version or APP_VERSION,
        "latest_tag": latest_tag or None,
        "release_name": release_name,
        "release_url": release_url,
        "published_at": published_at,
        "release_notes": release_notes,
        "source": source,
        "status": "up_to_date",
        "message": "当前已是最新版本。",
        "checked_at": checked_at,
        "cached": False,
        "download_url": asset.get("browser_download_url") if asset else release_url,
        "download_name": asset.get("name") if asset else None,
        "download_sha256": download_sha256,
        "network_proxy": proxy_summary,
        "network_detail": None,
    }


def _fetch_latest_release() -> dict[str, Any]:
    try:
        return _fetch_latest_release_from_api()
    except Exception as api_exc:  # noqa: BLE001
        try:
            return _fetch_latest_release_from_redirect()
        except Exception as redirect_exc:  # noqa: BLE001
            raise RuntimeError(
                f"{api_exc}; fallback latest redirect failed: {redirect_exc}"
            ) from redirect_exc


def _fetch_latest_release_from_api() -> dict[str, Any]:
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
        with _open_url(request, timeout=15) as response:
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
    payload["_source"] = UPDATE_SOURCE
    return payload


def _fetch_latest_release_from_redirect() -> dict[str, Any]:
    request = urlrequest.Request(
        GITHUB_LATEST_RELEASE_REDIRECT_URL,
        headers={"User-Agent": f"LivingToTell/{APP_VERSION}"},
        method="GET",
    )
    try:
        with _open_url(request, timeout=15) as response:
            final_url = response.geturl()
    except urlerror.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code}") from exc
    except urlerror.URLError as exc:
        raise RuntimeError(str(exc.reason)) from exc

    latest_tag = _as_text(Path(urlparse.urlparse(final_url).path).name)
    latest_version = _extract_version_text(latest_tag)
    if not latest_tag or not latest_version:
        raise RuntimeError("GitHub latest release redirect did not include a version tag.")
    asset_name = f"LivingToTell_{latest_version}_x64-setup.exe"
    return {
        "_source": UPDATE_SOURCE_REDIRECT,
        "tag_name": latest_tag,
        "name": f"Living to Tell Preview {latest_version}",
        "html_url": f"{GITHUB_RELEASE_URL_PREFIX}/tag/{latest_tag}",
        "published_at": None,
        "body": "",
        "assets": [
            {
                "name": asset_name,
                "browser_download_url": f"{GITHUB_RELEASE_URL_PREFIX}/download/{latest_tag}/{asset_name}",
            }
        ],
    }


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


def _asset_sha256(asset: Optional[dict[str, Any]]) -> Optional[str]:
    if not asset:
        return None
    digest = _as_text(asset.get("digest"))
    if digest.lower().startswith("sha256:"):
        return _normalise_sha256(digest.split(":", 1)[1])
    value = _as_text(asset.get("sha256"))
    return _normalise_sha256(value)


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


def _open_url(request: urlrequest.Request, timeout: int):
    return urlrequest.urlopen(request, timeout=timeout)


def _validate_update_download_url(raw_url: str) -> str:
    value = raw_url.strip()
    parsed = urlparse.urlparse(value)
    if parsed.scheme != "https":
        raise RuntimeError("安装包下载地址必须使用 HTTPS。")
    if parsed.netloc.lower() != "github.com":
        raise RuntimeError("只允许从本项目 GitHub Release 下载更新。")
    if "/sidiangongyuan/living-to-tell/releases/download/" not in parsed.path:
        raise RuntimeError("下载地址不是 Living to Tell 的 Release 安装包。")
    name = Path(parsed.path).name.lower()
    if not (name.endswith(".exe") or name.endswith(".msi")):
        raise RuntimeError("更新文件必须是 Windows 安装包。")
    return value


def _safe_update_file_name(raw_name: str) -> str:
    name = Path(raw_name.strip()).name
    if not name:
        name = "LivingToTell_update_x64-setup.exe"
    lowered = name.lower()
    if not (lowered.endswith(".exe") or lowered.endswith(".msi")):
        raise RuntimeError("更新文件必须是 Windows 安装包。")
    return re.sub(r"[^A-Za-z0-9._-]", "_", name)


def _updates_download_dir() -> Path:
    root = os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
    return Path(root) / "LivingToTell" / "updates"


def _cleanup_old_update_downloads(updates_dir: Path) -> None:
    for item in updates_dir.glob("LivingToTell_*"):
        if item.is_file():
            try:
                item.unlink()
            except OSError:
                pass


def _download_update_file(url: str, target: Path) -> tuple[int, str]:
    request = urlrequest.Request(
        url,
        headers={"User-Agent": f"LivingToTell/{APP_VERSION}"},
        method="GET",
    )
    digest = hashlib.sha256()
    size = 0
    try:
        with _open_url(request, timeout=120) as response, target.open("wb") as handle:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
                digest.update(chunk)
                size += len(chunk)
    except urlerror.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except urlerror.URLError as exc:
        raise RuntimeError(str(exc.reason)) from exc
    if size <= 0:
        raise RuntimeError("下载到的安装包为空。")
    return size, digest.hexdigest()


def _normalise_sha256(value: Optional[str]) -> Optional[str]:
    text = _as_text(value)
    if text.lower().startswith("sha256:"):
        text = text.split(":", 1)[1]
    text = text.strip().lower()
    if re.fullmatch(r"[0-9a-f]{64}", text):
        return text
    return None


def _proxy_summary() -> Optional[str]:
    proxies = urlrequest.getproxies()
    if not proxies:
        return None
    safe_parts: list[str] = []
    for scheme in ("https", "http"):
        proxy = proxies.get(scheme)
        if not proxy:
            continue
        parsed = urlparse.urlparse(proxy)
        if parsed.hostname:
            host = parsed.hostname
            port = f":{parsed.port}" if parsed.port else ""
            safe_parts.append(f"{scheme}={host}{port}")
        else:
            safe_parts.append(f"{scheme}=configured")
    return ", ".join(safe_parts) or "configured"


def _safe_error_detail(exc: Exception) -> str:
    raw = str(exc).strip()
    return raw[:400] if raw else exc.__class__.__name__


def _friendly_update_error(exc: Exception) -> str:
    raw = str(exc).strip()
    lowered = raw.lower()
    if "http 404" in lowered:
        return "暂未找到公开发布版本。"
    if "http 403" in lowered or "rate limit" in lowered:
        return "暂时无法检查更新，可能是 GitHub API 限流或网络受限。"
    if "timed out" in lowered or "timeout" in lowered:
        return "检查更新超时，请稍后重试。"
    if "proxy" in lowered or "tunnel" in lowered:
        return "检查更新失败，可能是本机代理不可用或代理无法连接 GitHub。"
    if "ssl" in lowered or "certificate" in lowered:
        return "检查更新失败，可能是网络证书或代理证书拦截导致。"
    if "<html" in lowered or "<!doctype html" in lowered:
        return "检查更新时收到了网页错误页，请稍后重试。"
    if raw:
        return f"暂时无法检查更新：{raw}"
    return "暂时无法检查更新，请稍后重试。"


def _friendly_download_error(exc: Exception) -> str:
    raw = str(exc).strip()
    lowered = raw.lower()
    if "timed out" in lowered or "timeout" in lowered:
        return "下载安装包超时，请稍后重试。"
    if "http 404" in lowered:
        return "下载安装包失败：发布页上的安装包不存在。"
    if "http 403" in lowered:
        return "下载安装包失败：GitHub 拒绝了当前请求，可能是网络或代理限制。"
    if "proxy" in lowered or "tunnel" in lowered:
        return "下载安装包失败，可能是本机代理不可用或代理无法连接 GitHub。"
    if raw:
        return f"下载安装包失败：{raw[:300]}"
    return "下载安装包失败，请稍后重试。"
