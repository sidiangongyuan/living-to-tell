"""Safe public diagnostics for provider and local-auth failures."""
from __future__ import annotations

import re
from typing import Any


_ENVIRONMENT_VARIABLE = re.compile(
    r"\benvironment variable\s+([A-Za-z_][A-Za-z0-9_]*)\b",
    re.IGNORECASE,
)


def safe_ai_diagnostic(value: Any) -> tuple[str, str]:
    raw = str(value or "").strip()
    lowered = raw.lower()
    if not raw:
        return "provider_error", "AI 请求失败，请稍后重试。"
    if "<html" in lowered or "<!doctype html" in lowered:
        return "html_response", "服务返回了网页错误页。请检查接口地址、协议和中转站状态。"
    if "missing_var" in lowered or "missing_key" in lowered or "environment variable" in lowered:
        match = _ENVIRONMENT_VARIABLE.search(raw)
        source_hint = f"（本机环境变量 {match.group(1)}）" if match else ""
        return (
            "missing_credential",
            f"未找到这个档案使用的 API Key{source_hint}。请重新保存密钥后再测试。",
        )
    if "missing_login" in lowered or "not logged" in lowered or ("登录" in raw and "未" in raw):
        return "missing_login", "未找到可复用的本机登录。请先在对应命令行工具中登录。"
    if (
        "codex auth" in lowered
        or "gemini env file" in lowered
        or "gemini cli" in lowered
        or "opencode" in lowered
    ) and ("not found" in lowered or "unavailable" in lowered or "missing" in lowered):
        return "missing_login", "未找到可复用的本机工具或登录。请先安装并登录对应命令行工具。"
    if "auth_list_timeout" in lowered:
        return "auth_timeout", "读取本机登录状态超时。请确认命令行工具可正常启动后重试。"
    if "401" in lowered or "unauthorized" in lowered:
        return "unauthorized", "认证失败。请检查 API Key、账号状态和接口地址。"
    if "403" in lowered or "forbidden" in lowered:
        return "forbidden", "服务拒绝了请求。请检查密钥权限、模型权限和账号分组。"
    if "404" in lowered or "not found" in lowered:
        return "endpoint_or_model_not_found", "接口或模型不存在。请检查地址、模型名称和协议。"
    if "429" in lowered or "rate limit" in lowered or "too many requests" in lowered:
        return "rate_limited", "请求过于频繁或额度不足。请稍后重试并检查账户额度。"
    if "timeout" in lowered or "timed out" in lowered or "超时" in raw:
        return "timeout", "请求超时。远端可能仍在生成并计费，请先检查中转站记录再决定是否重试。"
    if "failed to fetch" in lowered or ("connection" in lowered and "refused" in lowered):
        return "connection_failed", "无法连接 AI 服务。请检查网络、接口地址和服务状态。"
    if "traceback" in lowered or "stack trace" in lowered:
        return "provider_error", "AI 服务返回了异常信息。请检查配置后重试。"
    return "provider_error", "AI 请求失败。请检查档案配置、网络和服务商状态后重试。"


def friendly_ai_error(value: Any) -> str:
    return safe_ai_diagnostic(value)[1]
