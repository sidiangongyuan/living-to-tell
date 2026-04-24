"""Runtime hook: add PySide6 and shiboken6 subdirectories to the Windows DLL
search path before any Qt modules are imported.

Root cause
----------
PyInstaller 6.x one-folder builds place Qt DLLs under::

    dist/Writer/_internal/PySide6/

The bootloader calls ``SetDllDirectoryW(_internal/)`` but that only covers
the top-level ``_internal/`` directory, **not** its subdirectories.

Python 3.8+ changed extension-module (.pyd) loading on Windows to use
``LOAD_LIBRARY_SEARCH_DEFAULT_DIRS``, which honours ``AddDllDirectory()``
entries (exposed as ``os.add_dll_directory()``) but **ignores** the legacy
``PATH`` environment variable.  The stock ``pyi_rth_pyside6.py`` hook only
adds ``_MEIPASS`` to ``PATH``, which is therefore ignored, leaving Qt DLLs
unfindable.

Fix
---
Call ``os.add_dll_directory()`` for both ``PySide6/`` and ``shiboken6/``
subdirectories *inside* ``_MEIPASS`` before the bootloader hands control to
``main.py``. Store the returned handles for the lifetime of the process,
otherwise Python immediately removes those directories again.

We also preload the Windows system ICU runtime. Conda can place an ICU build
on the path that exports version-suffixed symbols (for example
``ucnv_open_58``), while Qt6 expects the unversioned Windows ICU exports
(``ucnv_open``). Preloading the system ICU by absolute path ensures Qt binds
against the compatible copy before it tries to load ``Qt6Core.dll``.
"""
import ctypes
import os
import sys

_DLL_DIR_HANDLES = []


if sys.platform == "win32" and getattr(sys, "frozen", False):
    _meipass = sys._MEIPASS  # _internal/ directory
    _system_icu = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "System32", "icuuc.dll")
    if os.path.isfile(_system_icu):
        ctypes.WinDLL(_system_icu)

    for _sub in ("PySide6", "shiboken6"):
        _d = os.path.join(_meipass, _sub)
        if os.path.isdir(_d):
            _DLL_DIR_HANDLES.append(os.add_dll_directory(_d))
