from __future__ import annotations

from writer.app.global_hotkeys import (
    GlobalHotkeyManager,
    MOD_ALT,
    MOD_CONTROL,
    VK_OEM_3,
    WM_HOTKEY,
)


class _FakeWindow:
    def __init__(self, hwnd: int = 1234) -> None:
        self._hwnd = hwnd

    def winId(self) -> int:
        return self._hwnd


def test_parse_hotkey_ctrl_alt_letter() -> None:
    modifiers, vk = GlobalHotkeyManager.parse_hotkey("Ctrl+Alt+W")

    assert modifiers == MOD_CONTROL | MOD_ALT
    assert vk == ord("W")


def test_parse_hotkey_ctrl_alt_backquote_key() -> None:
    for sequence in ("Ctrl+Alt+`", "Ctrl+Alt+·", "Ctrl+Alt+Backquote"):
        modifiers, vk = GlobalHotkeyManager.parse_hotkey(sequence)

        assert modifiers == MOD_CONTROL | MOD_ALT
        assert vk == VK_OEM_3


def test_register_hotkey_success_and_dispatch() -> None:
    calls: list[tuple[int, int, int, int]] = []
    activated: list[str] = []

    def fake_register(hwnd: int, hotkey_id: int, modifiers: int, vk: int) -> int:
        calls.append((hwnd, hotkey_id, modifiers, vk))
        return 1

    manager = GlobalHotkeyManager(register_hotkey=fake_register, supported=True)
    manager.set_host_window(_FakeWindow())

    assert manager.register_hotkey(
        name="quick_capture",
        sequence="Ctrl+Alt+`",
        callback=lambda: activated.append("quick_capture"),
    )

    assert calls == [(1234, 1, MOD_CONTROL | MOD_ALT, VK_OEM_3)]
    assert manager.handle_native_message(WM_HOTKEY, 1) is True
    assert activated == ["quick_capture"]


def test_register_hotkey_failure_emits_diagnostic(qtbot) -> None:
    failures: list[tuple[str, str]] = []

    manager = GlobalHotkeyManager(
        register_hotkey=lambda *_args: 0,
        supported=True,
    )
    manager.registration_failed.connect(lambda name, msg: failures.append((name, msg)))
    manager.set_host_window(_FakeWindow())

    ok = manager.register_hotkey(
        name="main_window",
        sequence="Ctrl+Alt+M",
        callback=lambda: None,
    )

    assert ok is False
    assert failures
    assert failures[0][0] == "main_window"
    assert "RegisterHotKey failed" in failures[0][1]


def test_unregister_all_unregisters_registered_ids() -> None:
    unregistered: list[tuple[int, int]] = []

    manager = GlobalHotkeyManager(
        register_hotkey=lambda *_args: 1,
        unregister_hotkey=lambda hwnd, hotkey_id: unregistered.append((hwnd, hotkey_id)) or 1,
        supported=True,
    )
    manager.set_host_window(_FakeWindow(hwnd=99))
    manager.register_hotkey(name="a", sequence="Ctrl+Alt+W", callback=lambda: None)
    manager.register_hotkey(name="b", sequence="Ctrl+Alt+M", callback=lambda: None)

    manager.unregister_all()

    assert unregistered == [(99, 1), (99, 2)]


def test_register_hotkey_unsupported_platform_path() -> None:
    failures: list[tuple[str, str]] = []
    manager = GlobalHotkeyManager(supported=False)
    manager.registration_failed.connect(lambda name, msg: failures.append((name, msg)))

    ok = manager.register_hotkey(name="quick", sequence="Ctrl+Alt+W", callback=lambda: None)

    assert ok is False
    assert failures == [(
        "quick",
        "Global hotkeys are not supported on this platform.",
    )]