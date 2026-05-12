from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket


class SingleInstanceGuard(QObject):
    activation_requested = Signal()

    def __init__(self, server_name: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._server_name = server_name
        self._server: QLocalServer | None = None

    def try_acquire(self) -> bool:
        socket = QLocalSocket(self)
        socket.connectToServer(self._server_name)
        if socket.waitForConnected(150):
            socket.write(b"activate")
            socket.flush()
            socket.waitForBytesWritten(150)
            socket.disconnectFromServer()
            return False

        QLocalServer.removeServer(self._server_name)
        server = QLocalServer(self)
        if not server.listen(self._server_name):
            return False

        server.newConnection.connect(self._on_new_connection)
        self._server = server
        return True

    def _on_new_connection(self) -> None:
        if self._server is None:
            return

        while self._server.hasPendingConnections():
            connection = self._server.nextPendingConnection()
            if connection is not None:
                connection.disconnectFromServer()
                connection.deleteLater()

        self.activation_requested.emit()
