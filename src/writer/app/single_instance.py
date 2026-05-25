"""Single-process coordination for the desktop app."""
from __future__ import annotations

from collections.abc import Callable
from typing import Optional

from PySide6.QtCore import QIODevice, QObject, QTimer
from PySide6.QtNetwork import QLocalServer, QLocalSocket


SINGLE_INSTANCE_SERVER_NAME = "writer-desktop-single-instance-v1"
SHOW_MAIN_COMMAND = b"SHOW_MAIN\n"


class SingleInstanceCoordinator(QObject):
    """Notify an existing Writer process or become the primary instance."""

    def __init__(
        self,
        server_name: str = SINGLE_INSTANCE_SERVER_NAME,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._server_name = server_name
        self._server: Optional[QLocalServer] = None
        self._on_show_main: Optional[Callable[[], None]] = None
        self._connections: list[QLocalSocket] = []

    def notify_existing_or_listen(self, on_show_main: Callable[[], None]) -> bool:
        """Return True for the primary instance, False for a notified secondary."""
        if self._notify_existing():
            return False

        self._on_show_main = on_show_main
        server = QLocalServer(self)
        if not server.listen(self._server_name):
            QLocalServer.removeServer(self._server_name)
            if not server.listen(self._server_name):
                # Fail open: startup should not be blocked by IPC issues.
                return True
        server.newConnection.connect(self._on_new_connection)
        self._server = server
        return True

    def close(self) -> None:
        if self._server is not None:
            self._server.close()
            self._server = None
        QLocalServer.removeServer(self._server_name)

    def _notify_existing(self) -> bool:
        socket = QLocalSocket(self)
        socket.connectToServer(
            self._server_name,
            QIODevice.OpenModeFlag.ReadWrite,
        )
        if not socket.waitForConnected(180):
            socket.deleteLater()
            return False
        socket.write(SHOW_MAIN_COMMAND)
        socket.flush()
        socket.waitForBytesWritten(180)
        socket.disconnectFromServer()
        socket.deleteLater()
        return True

    def _on_new_connection(self) -> None:
        if self._server is None:
            return
        while self._server.hasPendingConnections():
            socket = self._server.nextPendingConnection()
            if socket is None:
                continue
            socket.setParent(self)
            self._connections.append(socket)
            socket.readyRead.connect(lambda sock=socket: self._read_command(sock))
            socket.disconnected.connect(lambda sock=socket: self._drop_connection(sock))
            QTimer.singleShot(0, lambda sock=socket: self._read_command(sock))

    def _read_command(self, socket: QLocalSocket) -> None:
        data = bytes(socket.readAll())
        if not data:
            return
        if data.startswith(SHOW_MAIN_COMMAND.strip()) and self._on_show_main is not None:
            QTimer.singleShot(0, self._on_show_main)
        socket.disconnectFromServer()
        socket.deleteLater()
        self._drop_connection(socket)

    def _drop_connection(self, socket: QLocalSocket) -> None:
        try:
            self._connections.remove(socket)
        except ValueError:
            pass
