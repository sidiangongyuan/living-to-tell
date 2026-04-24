# writer.spec — PyInstaller one-folder build for Writer (Windows)
#
# Usage:
#   pyinstaller writer.spec
#
# Output: dist\Writer\Writer.exe
#   (bundled data lands in dist\Writer\_internal\ as per PyInstaller 6.x)
#
# The schema.sql is included as package data and is accessed at runtime via
# importlib.resources.files(), which works correctly in packaged builds.

import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Locate the schema.sql file from the installed package
# ---------------------------------------------------------------------------
import writer.storage as _ws
_schema_src = str(Path(_ws.__file__).parent / "schema.sql")


def _extra_runtime_binaries() -> list[tuple[str, str]]:
    """Collect Conda-only runtime DLLs when they exist.

    PyInstaller's default analysis on this project can miss a few DLLs that
    live under ``<env>/Library/bin`` in Conda environments.  On machines where
    those DLLs are only available via the active environment PATH, the built
    GUI app may fail to start outside that shell.  We add them opportunistically
    when present, while keeping the spec compatible with plain venv/pip setups
    where those files do not exist.
    """
    prefix = os.environ.get("CONDA_PREFIX")
    candidates: list[Path] = []
    if prefix:
        candidates.append(Path(prefix) / "Library" / "bin")
    candidates.append(Path(sys.executable).resolve().parent / "Library" / "bin")

    dll_names = (
        "libssl-3-x64.dll",
        "libcrypto-3-x64.dll",
        "libexpat.dll",
    )
    seen: set[str] = set()
    binaries: list[tuple[str, str]] = []
    for base in candidates:
        if not base.exists():
            continue
        for dll_name in dll_names:
            dll_path = base / dll_name
            if dll_path.exists() and dll_name not in seen:
                binaries.append((str(dll_path), "."))
                seen.add(dll_name)
    return binaries

block_cipher = None

a = Analysis(
    ["src/writer/main.py"],
    pathex=["."],
    binaries=_extra_runtime_binaries(),
    datas=[
        # Bundle schema.sql so the packaged app can initialise the DB.
        (_schema_src, "writer/storage"),
    ],
    hiddenimports=[
        # PySide6 submodules that PyInstaller may miss on some builds.
        "PySide6.QtSvg",
        "PySide6.QtXml",
    ],
    hookspath=["hooks"],
    hooksconfig={},
    runtime_hooks=["hooks/rthook_pyside6_dlls.py"],
    excludes=[
        # Keep the bundle lean — dev / test tooling is not needed at runtime.
        "pytest",
        "ruff",
        "pyinstaller",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Writer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # UPX can cause false-positive AV hits on Windows
    console=False,      # no terminal window for a GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon="assets/writer.ico",  # TODO: add an icon file when available
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Writer",
)
