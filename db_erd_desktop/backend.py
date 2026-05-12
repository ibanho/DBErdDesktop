from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import Any

from PySide6.QtCore import QCoreApplication, QObject, Property, QUrl, Signal, Slot
from .db import create_db_engine, list_namespaces, list_tables, list_views, reflect_database, test_connection
from .documents import export_document
from .erd_scene import ErdSceneBuilder
from .models import ConnectionSettings, DatabaseModel, SessionRecord, SshSettings
from .session_store import SessionStore
from .tunnel import SshTunnel


DEFAULT_PORTS = {
    "MySQL": 3306,
    "PostgreSQL": 5432,
    "MSSQL": 1433,
    "Oracle": 1521,
}


class AppBackend(QObject):
    sessionsChanged = Signal()
    currentSessionNameChanged = Signal()
    connectionSettingsChanged = Signal()
    connectedChanged = Signal()
    dbInfoChanged = Signal()
    tableRowsChanged = Signal()
    erdImagesChanged = Signal()
    hasErdChanged = Signal()
    statusMessageChanged = Signal()
    busyChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.session_store = SessionStore()
        self.sessions: list[SessionRecord] = []
        self.current_session_name = ""
        self.db_settings = self._default_db_settings()
        self.ssh_settings = self._default_ssh_settings()
        self.engine = None
        self.raw_db_settings: ConnectionSettings | None = None
        self.active_db_settings: ConnectionSettings | None = None
        self.model: DatabaseModel | None = None
        self.logical_scene = None
        self.physical_scene = None
        self.scene_builder = ErdSceneBuilder()
        self.ssh_tunnel = SshTunnel()
        self.table_rows: list[dict[str, Any]] = []
        self.db_info = "Not connected."
        self.logical_image_url = ""
        self.physical_image_url = ""
        self.status_message = ""
        self.busy = False
        self.cache_dir = Path(tempfile.gettempdir()) / "db_erd_desktop"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.reloadSessions()

    @Property("QVariantList", notify=sessionsChanged)
    def sessionList(self) -> list[dict[str, str]]:
        return [{"name": session.name, "description": session.description} for session in self.sessions]

    @Property(str, notify=currentSessionNameChanged)
    def currentSessionName(self) -> str:
        return self.current_session_name

    @Property("QVariantMap", notify=connectionSettingsChanged)
    def connectionSettings(self) -> dict[str, Any]:
        return {
            "dbms": self.db_settings.dbms,
            "host": self.db_settings.host,
            "port": self.db_settings.port,
            "database": self.db_settings.database,
            "username": self.db_settings.username,
            "password": self.db_settings.password,
            "mssqlDriver": self.db_settings.mssql_driver,
            "oracleMode": self.db_settings.oracle_service_mode,
            "trustServerCertificate": self.db_settings.trust_server_certificate,
            "sshEnabled": self.ssh_settings.enabled,
            "sshHost": self.ssh_settings.host,
            "sshPort": self.ssh_settings.port,
            "sshUsername": self.ssh_settings.username,
            "sshPassword": self.ssh_settings.password,
            "sshKeyFile": self.ssh_settings.key_file,
            "sshKeyPassphrase": self.ssh_settings.key_passphrase,
        }

    @Property(bool, notify=connectedChanged)
    def connected(self) -> bool:
        return self.engine is not None and self.active_db_settings is not None

    @Property(str, notify=dbInfoChanged)
    def databaseInfo(self) -> str:
        return self.db_info

    @Property("QVariantList", notify=tableRowsChanged)
    def tableRowsModel(self) -> list[dict[str, Any]]:
        return self.table_rows

    @Property(str, notify=erdImagesChanged)
    def logicalImageUrl(self) -> str:
        return self.logical_image_url

    @Property(str, notify=erdImagesChanged)
    def physicalImageUrl(self) -> str:
        return self.physical_image_url

    @Property(bool, notify=hasErdChanged)
    def hasErd(self) -> bool:
        return bool(self.logical_image_url and self.physical_image_url)

    @Property(str, notify=statusMessageChanged)
    def statusMessage(self) -> str:
        return self.status_message

    @Property(bool, notify=busyChanged)
    def isBusy(self) -> bool:
        return self.busy

    @Slot()
    def reloadSessions(self) -> None:
        try:
            self.sessions = self.session_store.load()
            self.sessionsChanged.emit()
        except Exception as exc:
            self.sessions = []
            self.sessionsChanged.emit()
            self._set_status(f"세션 로드 실패: {exc}")

    @Slot(str, result=bool)
    def openSession(self, name: str) -> bool:
        session = self._session_by_name(name)
        if session is None:
            self._set_status("선택한 세션을 찾을 수 없습니다.")
            return False
        self._close_connections()
        self.current_session_name = session.name
        self.db_settings = session.db
        self.ssh_settings = session.ssh
        self.currentSessionNameChanged.emit()
        self.connectionSettingsChanged.emit()
        self._set_status(f"Session loaded: {session.name}")
        return True

    @Slot(str, str, result=bool)
    def createSession(self, name: str, description: str = "") -> bool:
        name = name.strip()
        if not name:
            self._set_status("세션명을 입력하세요.")
            return False
        if self._session_by_name(name) is not None:
            self._set_status("이미 같은 이름의 세션이 있습니다.")
            return False
        session = SessionRecord(name, self._default_db_settings(), self._default_ssh_settings(), description.strip())
        try:
            self.session_store.upsert(session)
            self.reloadSessions()
            return self.openSession(name)
        except Exception as exc:
            self._set_status(f"세션 생성 실패: {exc}")
            return False

    @Slot("QVariantMap")
    def updateConnectionSettings(self, values: dict[str, Any]) -> None:
        self._close_connections()
        dbms = str(values.get("dbms") or "MySQL")
        self.db_settings = ConnectionSettings(
            dbms=dbms,
            host=str(values.get("host") or "localhost").strip(),
            port=self._int_value(values.get("port"), DEFAULT_PORTS.get(dbms, 3306)),
            database=str(values.get("database") or "").strip(),
            username=str(values.get("username") or "").strip(),
            password=str(values.get("password") or ""),
            mssql_driver=str(values.get("mssqlDriver") or "ODBC Driver 18 for SQL Server").strip(),
            oracle_service_mode=str(values.get("oracleMode") or "service"),
            trust_server_certificate=bool(values.get("trustServerCertificate", True)),
        )
        self.ssh_settings = SshSettings(
            enabled=bool(values.get("sshEnabled", False)),
            host=str(values.get("sshHost") or "").strip(),
            port=self._int_value(values.get("sshPort"), 22),
            username=str(values.get("sshUsername") or "").strip(),
            password=str(values.get("sshPassword") or ""),
            key_file=str(values.get("sshKeyFile") or "").strip(),
            key_passphrase=str(values.get("sshKeyPassphrase") or ""),
        )
        self.connectionSettingsChanged.emit()
        self._set_status("Connection settings updated. Save the current session to keep these values.")

    @Slot(result=bool)
    def saveCurrentSession(self) -> bool:
        name = self.current_session_name.strip()
        if not name:
            self._set_status("저장할 세션이 없습니다.")
            return False
        existing = self._session_by_name(name)
        description = existing.description if existing else ""
        try:
            self.session_store.upsert(SessionRecord(name, self.db_settings, self.ssh_settings, description))
            self.reloadSessions()
            self._set_status(f"Session saved: {name}")
            return True
        except Exception as exc:
            self._set_status(f"세션 저장 실패: {exc}")
            return False

    @Slot(result=bool)
    def connectCurrentSession(self) -> bool:
        return self._with_busy(self._connect_current_session)

    @Slot(result=bool)
    def reloadTree(self) -> bool:
        return self._with_busy(self._load_tree)

    @Slot(int, bool)
    def setRowChecked(self, index: int, checked: bool) -> None:
        if index < 0 or index >= len(self.table_rows):
            return
        row = self.table_rows[index]
        namespace = row.get("namespace")
        if not namespace or not row.get("checkable", True):
            return

        row_type = row.get("type")
        if row_type == "namespace":
            for item in self.table_rows:
                if item.get("namespace") == namespace and item.get("checkable", True):
                    item["checked"] = checked
            self._sync_tree_checks(str(namespace))
        elif row_type == "table_group":
            for item in self.table_rows:
                if item.get("type") == "table" and item.get("namespace") == namespace:
                    item["checked"] = checked
            row["checked"] = checked
            self._sync_tree_checks(str(namespace))
        elif row_type == "table":
            row["checked"] = checked
            self._sync_tree_checks(str(namespace))
        else:
            return
        self.tableRowsChanged.emit()

    def _sync_tree_checks(self, namespace: str) -> None:
        table_rows = [item for item in self.table_rows if item.get("type") == "table" and item.get("namespace") == namespace]
        any_checked = any(item.get("checked") for item in table_rows)
        for item in self.table_rows:
            if item.get("namespace") != namespace:
                continue
            if item.get("type") in {"namespace", "table_group"}:
                item["checked"] = any_checked
                item["checkable"] = bool(table_rows)

    @Slot(result=bool)
    def generateErd(self) -> bool:
        return self._with_busy(self._generate_erd)

    @Slot("QVariant", result=bool)
    def saveDocumentation(self, selected_file) -> bool:
        return self._with_busy(lambda: self._save_documentation(selected_file))

    @Slot()
    def shutdown(self) -> None:
        self._close_connections()

    def _connect_current_session(self) -> bool:
        try:
            self._close_connections()
            self.raw_db_settings = self.db_settings
            self.active_db_settings = self.ssh_tunnel.open(self.ssh_settings, self.db_settings)
            self.engine = create_db_engine(self.active_db_settings)
            test_connection(self.engine)
            if not self._load_tree():
                return False
            tunnel_status = f" via SSH tunnel :{self.ssh_tunnel.local_port}" if self.ssh_tunnel.is_active else ""
            self._set_status(f"Connected{tunnel_status}.")
            self.connectedChanged.emit()
            return True
        except Exception as exc:
            self._close_connections()
            self._set_status(f"연결 실패: {exc}")
            return False

    def _load_tree(self) -> bool:
        if self.engine is None or self.active_db_settings is None:
            self._set_status("먼저 세션 연결을 수행하세요.")
            return False
        try:
            namespaces = list_namespaces(self.engine, self.active_db_settings)
            rows: list[dict[str, Any]] = []
            total_tables = 0
            total_views = 0
            for namespace in namespaces:
                engine, should_dispose = self._engine_for_namespace(self.active_db_settings, namespace)
                try:
                    tables = list_tables(engine, self.active_db_settings, namespace)
                    views = list_views(engine, self.active_db_settings, namespace)
                finally:
                    if should_dispose:
                        engine.dispose()
                total_tables += len(tables)
                total_views += len(views)

                has_tables = bool(tables)
                rows.append(
                    {
                        "type": "namespace",
                        "namespace": namespace,
                        "table": "",
                        "view": "",
                        "label": namespace,
                        "badge": "DB",
                        "level": 0,
                        "checked": has_tables,
                        "checkable": has_tables,
                    }
                )
                rows.append(
                    {
                        "type": "table_group",
                        "namespace": namespace,
                        "table": "",
                        "view": "",
                        "label": f"Tables ({len(tables)})",
                        "badge": "T",
                        "level": 1,
                        "checked": has_tables,
                        "checkable": has_tables,
                    }
                )
                for table in tables:
                    rows.append(
                        {
                            "type": "table",
                            "namespace": namespace,
                            "table": table,
                            "view": "",
                            "label": table,
                            "badge": "T",
                            "level": 2,
                            "checked": True,
                            "checkable": True,
                        }
                    )
                rows.append(
                    {
                        "type": "view_group",
                        "namespace": namespace,
                        "table": "",
                        "view": "",
                        "label": f"Views ({len(views)})",
                        "badge": "V",
                        "level": 1,
                        "checked": False,
                        "checkable": False,
                    }
                )
                for view in views:
                    rows.append(
                        {
                            "type": "view",
                            "namespace": namespace,
                            "table": "",
                            "view": view,
                            "label": view,
                            "badge": "V",
                            "level": 2,
                            "checked": False,
                            "checkable": False,
                        }
                    )
            self.table_rows = rows
            self.tableRowsChanged.emit()
            self._set_db_info(len(namespaces), total_tables, total_views)
            self._set_status(
                f"Loaded {len(namespaces)} database/schema node(s), {total_tables} table(s), {total_views} view(s)."
            )
            return True
        except Exception as exc:
            self._set_status(f"DB 트리 조회 실패: {exc}")
            return False

    def _set_db_info(self, namespace_count: int, table_count: int, view_count: int) -> None:
        if self.active_db_settings is None:
            self.db_info = "Not connected."
        else:
            mode = (
                f"SSH tunnel active, local port {self.ssh_tunnel.local_port}"
                if self.ssh_tunnel.is_active
                else "Direct connection"
            )
            self.db_info = "\n".join(
                [
                    f"DBMS: {self.active_db_settings.dbms}",
                    f"Mode: {mode}",
                    f"Database/Schema nodes: {namespace_count}",
                    f"Tables: {table_count}",
                    f"Views: {view_count}",
                ]
            )
        self.dbInfoChanged.emit()

    def _generate_erd(self) -> bool:
        if self.engine is None or self.active_db_settings is None:
            self._set_status("먼저 세션 연결을 수행하세요.")
            return False
        selections = self._selected_tables_by_namespace()
        if not selections:
            self._set_status("하나 이상의 테이블을 선택하세요.")
            return False

        try:
            all_tables = []
            all_relationships = []
            for namespace, tables in selections.items():
                engine, should_dispose = self._engine_for_namespace(self.active_db_settings, namespace)
                try:
                    partial = reflect_database(engine, self.active_db_settings, namespace, tables)
                    all_tables.extend(partial.tables)
                    all_relationships.extend(partial.relationships)
                finally:
                    if should_dispose:
                        engine.dispose()

            self.model = DatabaseModel(
                self.active_db_settings.dbms,
                ", ".join(selections.keys()),
                all_tables,
                all_relationships,
            )
            self.logical_scene = self.scene_builder.build(self.model, "logical")
            self.physical_scene = self.scene_builder.build(self.model, "physical")
            stamp = int(time.time() * 1000)
            logical_png = self.cache_dir / "logical_preview.png"
            physical_png = self.cache_dir / "physical_preview.png"
            self.scene_builder.export_png(self.logical_scene, logical_png)
            self.scene_builder.export_png(self.physical_scene, physical_png)
            self.logical_image_url = f"{QUrl.fromLocalFile(str(logical_png)).toString()}?v={stamp}"
            self.physical_image_url = f"{QUrl.fromLocalFile(str(physical_png)).toString()}?v={stamp}"
            self.erdImagesChanged.emit()
            self.hasErdChanged.emit()
            self._set_status("ERD generated.")
            return True
        except Exception as exc:
            self._set_status(f"ERD 생성 실패: {exc}")
            return False

    def _save_documentation(self, selected_file: str) -> bool:
        if self.model is None or self.logical_scene is None or self.physical_scene is None:
            self._set_status("먼저 ERD를 생성하세요.")
            return False
        output_path = self._path_from_url(selected_file)
        if output_path is None:
            return False
        if output_path.suffix.lower() not in {".docx", ".hwpx", ".pptx"}:
            output_path = output_path.with_suffix(".docx")

        logical_png = output_path.with_name(f"{output_path.stem}_logical.png")
        physical_png = output_path.with_name(f"{output_path.stem}_physical.png")
        try:
            self.scene_builder.export_png(self.logical_scene, logical_png)
            self.scene_builder.export_png(self.physical_scene, physical_png)
            export_document(self.model, output_path, logical_png, physical_png)
            self._set_status(f"Saved: {output_path}")
            return True
        except Exception as exc:
            self._set_status(f"저장 실패: {exc}")
            return False

    def _selected_tables_by_namespace(self) -> dict[str, list[str]]:
        selections: dict[str, list[str]] = {}
        for row in self.table_rows:
            if row.get("type") != "table" or not row.get("checked"):
                continue
            selections.setdefault(str(row["namespace"]), []).append(str(row["table"]))
        return selections

    def _engine_for_namespace(self, settings: ConnectionSettings, namespace: str):
        if settings.dbms in {"MySQL", "MSSQL"}:
            return create_db_engine(settings, database=namespace), True
        return self.engine, False

    def _session_by_name(self, name: str) -> SessionRecord | None:
        for session in self.sessions:
            if session.name == name:
                return session
        return None

    def _default_db_settings(self) -> ConnectionSettings:
        return ConnectionSettings("MySQL", "localhost", DEFAULT_PORTS["MySQL"], "", "", "")

    def _default_ssh_settings(self) -> SshSettings:
        return SshSettings(False, "", 22, "")

    def _close_connections(self) -> None:
        if self.engine is not None:
            self.engine.dispose()
            self.engine = None
        self.raw_db_settings = None
        self.active_db_settings = None
        self.model = None
        self.logical_scene = None
        self.physical_scene = None
        self.logical_image_url = ""
        self.physical_image_url = ""
        self.table_rows = []
        self.db_info = "Not connected."
        self.ssh_tunnel.close()
        self.connectedChanged.emit()
        self.tableRowsChanged.emit()
        self.dbInfoChanged.emit()
        self.erdImagesChanged.emit()
        self.hasErdChanged.emit()

    def _with_busy(self, action) -> bool:
        self._set_busy(True)
        try:
            return bool(action())
        finally:
            self._set_busy(False)

    def _set_busy(self, value: bool) -> None:
        if self.busy == value:
            return
        self.busy = value
        self.busyChanged.emit()
        QCoreApplication.processEvents()

    def _set_status(self, message: str) -> None:
        self.status_message = message
        self.statusMessageChanged.emit()

    def _path_from_url(self, value) -> Path | None:
        if not value:
            return None
        url = value if isinstance(value, QUrl) else QUrl(str(value))
        path = url.toLocalFile() if url.isLocalFile() else value
        if not path:
            return None
        return Path(str(path))

    def _int_value(self, value: Any, fallback: int) -> int:
        try:
            number = int(value)
        except (TypeError, ValueError):
            return fallback
        return number if number > 0 else fallback
