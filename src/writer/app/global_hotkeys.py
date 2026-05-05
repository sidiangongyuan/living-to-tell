"""Windows-first global hotkey registration.

The manager keeps the Win32 surface small and mockable so tests can cover
registration success/failure without depending on real system hotkeys.
"""
from __future__ import annotations

import ctypes
import sys
from dataclasses import dataclass
from typing import Callable, Dict, Optional

from PySide6.QtCore import QObject, Signal

if sys.platform == "win32":
    from ctypes import wintypes
else:  # pragma: no cover - type-only fallback for non-Windows test/import
    wintypes = None  # type: ignore[assignment]


MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
WM_HOTKEY = 0x0312

_MODIFIERS = {
    "ALT": MOD_ALT,
    "CTRL": MOD_CONTROL,
    "CONTROL": MOD_CONTROL,
    "SHIFT": MOD_SHIFT,
    "WIN": MOD_WIN,
    "META": MOD_WIN,
}

_VK_F_KEYS = {f"F{i}": 0x6F + i for i in range(1, 25)}


@dataclass
class _Binding:
    hotkey_id: int
    sequence: str
    callback: Callable[[], None]
    registered: bool = False


def _default_register(hwnd: int, hotkey_id: int, modifiers: int, vk: int) -> int:
    assert sys.platform == "win32"
    return int(ctypes.windll.user32.RegisterHotKey(hwnd, hotkey_id, modifiers, vk))


def _default_unregister(hwnd: int, hotkey_id: int) -> int:
    assert sys.platform == "win32"
    return int(ctypes.windll.user32.UnregisterHotKey(hwnd, hotkey_id))


class GlobalHotkeyManager(QObject):
    registration_failed = Signal(str, str)
    activated = Signal(str)

    def __init__(
        self,
        *,
        register_hotkey: Optional[Callable[[int, int, int, int], int]] = None,
        unregister_hotkey: Optional[Callable[[int, int], int]] = None,
        supported: Optional[bool] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._supported = (sys.platform == "win32") if supported is None else supported
        self._register = register_hotkey or _default_register
        self._unregister = unregister_hotkey or _default_unregister
        self._bindings: Dict[str, _Binding] = {}
        self._bindings_by_id: Dict[int, str] = {}
        self._next_hotkey_id = 1
        self._hwnd = 0
        self.last_error: Optional[str] = None

    @property
    def supported(self) -> bool:
        return self._supported

    def set_host_window(self, window) -> None:
        self._hwnd = int(window.winId())

    def register_hotkey(
        self,
        *,
        name: str,
        sequence: str,
        callback: Callable[[], None],
    ) -> bool:
        if not self._supported:
            self.last_error = "Global hotkeys are not supported on this platform."
            self.registration_failed.emit(name, self.last_error)
            return False
        if not self._hwnd:
            self.last_error = "Global hotkey host window is not ready."
            self.registration_failed.emit(name, self.last_error)
            return False

        try:
            modifiers, vk = self.parse_hotkey(sequence)
        except ValueError as exc:
            self.last_error = str(exc)
            self.registration_failed.emit(name, self.last_error)
            return False

        binding = _Binding(
            hotkey_id=self._next_hotkey_id,
            sequence=sequence,
            callback=callback,
        )
        self._next_hotkey_id += 1

        ok = bool(self._register(self._hwnd, binding.hotkey_id, modifiers, vk))
        if not ok:
            self.last_error = f"RegisterHotKey failed for {sequence}."
            self.registration_failed.emit(name, self.last_error)
            return False

        binding.registered = True
        self._bindings[name] = binding
        self._bindings_by_id[binding.hotkey_id] = name
        self.last_error = None
        return True

    def unregister_all(self) -> None:
        if not self._hwnd:
            self._bindings.clear()
            self._bindings_by_id.clear()
            return
        for binding in list(self._bindings.values()):
            if binding.registered:
                try:
                    self._unregister(self._hwnd, binding.hotkey_id)
                except Exception:  # noqa: BLE001
                    pass
        self._bindings.clear()
        self._bindings_by_id.clear()

    def handle_native_message(self, message: int, wparam: int) -> bool:
        if message != WM_HOTKEY:
            return False
        name = self._bindings_by_id.get(int(wparam))
        if name is None:
            return False
        binding = self._bindings.get(name)
        if binding is None:
            return False
        binding.callback()
        self.activated.emit(name)
        return True

    @staticmethod
    def parse_hotkey(sequence: str) -> tuple[int, int]:
        if not sequence or not sequence.strip():
            raise ValueError("Hotkey sequence is empty.")

        parts = [part.strip().upper() for part in sequence.split("+") if part.strip()]
        if len(parts) < 2:
            raise ValueError(f"Unsupported hotkey sequence: {sequence!r}")

        modifiers = 0
        for token in parts[:-1]:
            if token not in _MODIFIERS:
                raise ValueError(f"Unsupported modifier {token!r} in {sequence!r}")
            modifiers |= _MODIFIERS[token]
        key = parts[-1]
        if len(key) == 1 and key.isalnum():
            return modifiers, ord(key)
        if key in _VK_F_KEYS:
            return modifiers, _VK_F_KEYS[key]
        raise ValueError(f"Unsupported hotkey key {key!r} in {sequence!r}")