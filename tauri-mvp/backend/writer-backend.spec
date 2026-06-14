# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Writer backend bundling.

Packages the FastAPI backend + full writer package into a single-directory
bundle that can be shipped with the Tauri app as a sidecar.
"""
from pathlib import Path
import os
import sys

block_cipher = None
backend_dir = Path(SPECPATH).resolve()
writer_pkg = backend_dir.parent.parent / "src" / "writer"
env_dir = Path(os.environ.get("CONDA_PREFIX") or sys.prefix)
library_bin = env_dir / "Library" / "bin"
extra_binaries = [
    (str(library_bin / name), ".")
    for name in ("libssl-3-x64.dll", "libcrypto-3-x64.dll", "libexpat.dll")
    if (library_bin / name).exists()
]
extra_datas = [
    (str(writer_pkg / "storage" / "schema.sql"), "writer/storage"),
]

a = Analysis(
    ['run.py'],
    pathex=[str(backend_dir), str(writer_pkg.parent)],
    binaries=extra_binaries,
    datas=extra_datas,
    hiddenimports=[
        'writer.app.container',
        'writer.storage.repositories.entry_repository',
        'writer.storage.repositories.work_repository',
        'writer.storage.repositories.collection_repository',
        'writer.storage.repositories.reference_repository',
        'writer.storage.repositories.version_repository',
        'writer.services.search_service',
        'writer.services.work_service',
        'writer.services.ai.openai_provider',
        'writer.services.ai.gemini_provider',
        'writer.services.ai.gemini_cli_provider',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='writer-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
