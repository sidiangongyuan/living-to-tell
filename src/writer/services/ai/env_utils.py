"""Environment variable resolution helpers with Windows User Registry fallback."""
from __future__ import annotations

import os
from typing import Mapping, Optional


def resolve_env_var(name: str, environ: Optional[Mapping[str, str]] = None) -> str:
    """Resolve an environment variable, falling back to Windows User Registry if unset."""
    env = environ if environ is not None else os.environ
    val = (env.get(name, "") or "").strip()
    if not val and (environ is None or environ is os.environ) and os.name == "nt":
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
                reg_val, _ = winreg.QueryValueEx(key, name)
                if isinstance(reg_val, str) and reg_val.strip():
                    val = reg_val.strip()
                    os.environ[name] = val
        except OSError:
            pass
    return val
