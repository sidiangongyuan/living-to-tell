from __future__ import annotations

from uuid import uuid4

from writer.app.single_instance import SingleInstanceCoordinator


def _server_name() -> str:
    return f"writer-test-{uuid4()}"


def test_single_instance_listens_when_no_existing(qtbot):
    coord = SingleInstanceCoordinator(server_name=_server_name())

    assert coord.notify_existing_or_listen(lambda: None) is True

    coord.close()


def test_single_instance_secondary_notifies_primary(qtbot):
    calls: list[str] = []
    name = _server_name()
    primary = SingleInstanceCoordinator(server_name=name)
    secondary = SingleInstanceCoordinator(server_name=name)

    assert primary.notify_existing_or_listen(lambda: calls.append("show")) is True
    assert secondary.notify_existing_or_listen(lambda: None) is False

    qtbot.waitUntil(lambda: calls == ["show"])

    primary.close()
    secondary.close()
