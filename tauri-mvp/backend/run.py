"""Backend entry point with dynamic port + stdout handshake.

Tauri launches this as a sidecar. We bind to an OS-assigned free port, then
print a single line ``WRITER_PORT=<n>`` to stdout so the Tauri shell can read
it and point the frontend at the right URL. Falls back to 8000 when run
standalone for development.
"""
from __future__ import annotations

import os
import socket
import sys

import uvicorn


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main() -> None:
    # Honour an explicit port (dev), else pick a free one (sidecar).
    port_env = os.environ.get("WRITER_PORT")
    if port_env and port_env.isdigit():
        port = int(port_env)
    elif "--dev" in sys.argv:
        port = 8000
    else:
        port = _pick_free_port()

    # Handshake line — Tauri reads this from the sidecar's stdout.
    print(f"WRITER_PORT={port}", flush=True)

    from app import app

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    main()
