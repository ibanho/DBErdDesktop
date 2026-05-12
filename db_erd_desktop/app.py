from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlApplicationEngine

from .backend import AppBackend
from .single_instance import SingleInstanceGuard


SINGLE_INSTANCE_SERVER_NAME = "DBErdDesktopSingleInstance"


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("DB ERD Desktop")

    single_instance = SingleInstanceGuard(SINGLE_INSTANCE_SERVER_NAME, app)
    if not single_instance.try_acquire():
        return 0

    backend = AppBackend()
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend", backend)

    qml_path = Path(__file__).resolve().parent / "qml" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        return 1

    window = engine.rootObjects()[0]
    single_instance.activation_requested.connect(lambda: activate_window(window))
    exit_code = app.exec()
    backend.shutdown()
    return exit_code


def activate_window(window) -> None:
    modal = QApplication.activeModalWidget()
    target = modal or window
    if hasattr(target, "showNormal") and target.isMinimized():
        target.showNormal()
    elif hasattr(target, "show") and not target.isVisible():
        target.show()
    if hasattr(target, "raise_"):
        target.raise_()
    if hasattr(target, "requestActivate"):
        target.requestActivate()
    elif hasattr(target, "activateWindow"):
        target.activateWindow()
