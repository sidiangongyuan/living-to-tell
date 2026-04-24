"""Regression tests for the M3 verification fixes."""
from __future__ import annotations

from pathlib import Path

import pytest

from writer.app.container import build_container
from writer.app.settings import KEY_AI_BASE_URL
from writer.domain.models.ai_config import AiConfig


@pytest.fixture()
def container(isolated_data_dir: Path):
    c = build_container()
    yield c
    c.close()


# ---------------------------------------------------------------------------
# Fix 1: base_url can be cleared.
# ---------------------------------------------------------------------------
def test_clearing_base_url_removes_override(container):
    settings = container.settings
    settings.save_ai_config(AiConfig(base_url="https://custom.example/v1"))
    assert settings.ai_base_url == "https://custom.example/v1"

    settings.save_ai_config(AiConfig(base_url=None))
    # Setting key must be gone entirely — no stale empty-string residue.
    assert settings.ai_base_url is None
    assert "ai.base_url" not in container.settings_repository.get_all()

    cfg = settings.load_ai_config()
    assert cfg.base_url is None  # defaults back to SDK endpoint


def test_empty_string_base_url_also_clears(container):
    settings = container.settings
    settings.save_ai_config(AiConfig(base_url="https://custom.example/v1"))
    settings.save_ai_config(AiConfig(base_url="   "))
    assert settings.ai_base_url is None


# ---------------------------------------------------------------------------
# Fix 3: wire_api is validated.
# ---------------------------------------------------------------------------
def test_invalid_wire_api_is_rejected(container):
    with pytest.raises(ValueError):
        container.settings.save_ai_config(
            AiConfig(wire_api="chat_completions", model="m")
        )
    # Nothing should have been persisted.
    assert container.settings.ai_wire_api is None


def test_valid_wire_api_is_normalized(container):
    container.settings.save_ai_config(AiConfig(wire_api="RESPONSES", model="m"))
    assert container.settings.ai_wire_api == "responses"


# ---------------------------------------------------------------------------
# Fix 2: cancel drops stale success.
# ---------------------------------------------------------------------------
def test_worker_does_not_emit_after_interruption(qtbot, container):
    from writer.domain.enums import RewriteAction
    from writer.services.ai.interfaces import (
        AiProvider,
        RewriteRequest,
        RewriteResponse,
    )
    from writer.services.ai.rewrite_service import RewriteService
    from writer.ui.rewrite_worker import RewriteWorker

    class _SlowProvider(AiProvider):
        name = "slow"

        def rewrite(self, request):
            # Simulate a long in-flight call.
            QThread_msleep(50)
            return RewriteResponse(content="late", model="m", provider=self.name)

    service = RewriteService(
        container.entry_repository,
        container.version_repository,
        lambda: _SlowProvider(),
    )

    worker = RewriteWorker(
        service, RewriteRequest(action=RewriteAction.POLISH, text="hello")
    )
    received: list = []
    worker.succeeded.connect(lambda r: received.append(r))
    worker.failed.connect(lambda m: received.append(("fail", m)))

    # Request interruption *before* starting — simplest way to prove the
    # worker honours the flag without racing.
    worker.requestInterruption()
    worker.start()
    worker.wait(2000)

    assert received == [], "Interrupted worker must not emit succeeded/failed"


def QThread_msleep(ms: int) -> None:
    from PySide6.QtCore import QThread

    QThread.msleep(ms)


def test_main_window_cancel_blocks_compare_dialog(qtbot, container, monkeypatch):
    """Cancelling the rewrite must prevent the compare dialog from opening."""
    from writer.domain.enums import RewriteAction
    from writer.services.ai.interfaces import (
        AiProvider,
        RewriteRequest,
        RewriteResponse,
    )
    from writer.services.ai.rewrite_service import RewriteService
    from writer.ui import main_window as main_window_module
    from writer.ui.main_window import MainWindow

    class _ImmediateProvider(AiProvider):
        name = "immediate"

        def rewrite(self, request):
            return RewriteResponse(
                content="REWRITTEN", model="m", provider=self.name
            )

    # Swap in a fast rewrite service bound to the same repos.
    container.rewrite_service = RewriteService(  # type: ignore[attr-defined]
        container.entry_repository,
        container.version_repository,
        lambda: _ImmediateProvider(),
    )
    entry = container.entry_repository.create(title="t", body="hello world")

    window = MainWindow(container, autosave_debounce_ms=50)
    qtbot.addWidget(window)
    window._load_entry(entry.id)  # noqa: SLF001

    compare_calls: list = []

    class _FakeCompareDialog:
        DialogCode = type("DC", (), {"Accepted": 1})

        def __init__(self, *args, **kwargs):
            compare_calls.append(kwargs)

        def exec(self):
            return 0

        def accepted_text(self):
            return ""

    monkeypatch.setattr(main_window_module, "RewriteCompareDialog", _FakeCompareDialog)

    # Patch QProgressDialog.exec to cancel immediately before the worker
    # finishes, then process remaining events to drain queued signals.
    from PySide6.QtWidgets import QProgressDialog

    real_exec = QProgressDialog.exec

    def _cancel_exec(self):
        self.cancel()  # emits canceled
        return 0

    monkeypatch.setattr(QProgressDialog, "exec", _cancel_exec)

    window._on_rewrite(RewriteAction.POLISH)  # noqa: SLF001
    qtbot.wait(200)
    # Body must be unchanged; no compare dialog must have been constructed.
    reloaded = container.entry_repository.get(entry.id)
    assert reloaded.body == "hello world"
    assert compare_calls == []

    monkeypatch.setattr(QProgressDialog, "exec", real_exec)
