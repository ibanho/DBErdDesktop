from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ConnectionSettings:
    dbms: str
    host: str
    port: int
    database: str
    username: str
    password: str
    mssql_driver: str = "ODBC Driver 18 for SQL Server"
    oracle_service_mode: str = "service"
    trust_server_certificate: bool = True


@dataclass(frozen=True)
class SshSettings:
    enabled: bool
    host: str
    port: int
    username: str
    password: str = ""
    key_file: str = ""
    key_passphrase: str = ""


@dataclass(frozen=True)
class SessionRecord:
    name: str
    db: ConnectionSettings
    ssh: SshSettings
    description: str = ""


@dataclass
class ColumnModel:
    name: str
    logical_name: str
    data_type: str
    nullable: bool
    default: str | None = None
    comment: str | None = None
    is_primary_key: bool = False
    foreign_key: str | None = None


@dataclass
class TableModel:
    name: str
    schema: str | None = None
    logical_name: str | None = None
    comment: str | None = None
    columns: list[ColumnModel] = field(default_factory=list)

    @property
    def qualified_name(self) -> str:
        return f"{self.schema}.{self.name}" if self.schema else self.name


@dataclass
class RelationshipModel:
    name: str
    from_table: str
    from_columns: tuple[str, ...]
    to_table: str
    to_columns: tuple[str, ...]


@dataclass
class DatabaseModel:
    dbms: str
    namespace: str
    tables: list[TableModel]
    relationships: list[RelationshipModel]

    def table_by_name(self) -> dict[str, TableModel]:
        return {table.qualified_name: table for table in self.tables}
