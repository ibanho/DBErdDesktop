from __future__ import annotations

from dataclasses import replace
from importlib.util import find_spec
from typing import Iterable
from urllib.parse import quote_plus

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import NoSuchModuleError

from .models import ColumnModel, ConnectionSettings, DatabaseModel, RelationshipModel, TableModel
from .naming import infer_logical_name


SYSTEM_NAMESPACES = {
    "information_schema",
    "performance_schema",
    "mysql",
    "sys",
    "pg_catalog",
    "pg_toast",
    "dbo",  # kept visible by SQL Server-specific handling below
}


DRIVER_HINTS = {
    "MySQL": "PyMySQL 드라이버가 필요합니다. 예: python -m pip install PyMySQL",
    "PostgreSQL": "psycopg 드라이버가 필요합니다. 예: python -m pip install \"psycopg[binary]\"",
    "MSSQL": "pyodbc와 Microsoft ODBC Driver 17/18 for SQL Server가 필요합니다.",
    "Oracle": "oracledb 드라이버가 필요합니다. 예: python -m pip install oracledb",
}


def ensure_driver_available(dbms: str) -> None:
    module = {
        "MySQL": "pymysql",
        "PostgreSQL": "psycopg",
        "MSSQL": "pyodbc",
        "Oracle": "oracledb",
    }[dbms]
    if find_spec(module) is None:
        raise RuntimeError(DRIVER_HINTS[dbms])


def build_url(settings: ConnectionSettings) -> str:
    user = quote_plus(settings.username)
    password = quote_plus(settings.password)
    host = settings.host.strip() or "localhost"
    database = settings.database.strip()

    if settings.dbms == "MySQL":
        db_part = f"/{quote_plus(database)}" if database else ""
        return f"mysql+pymysql://{user}:{password}@{host}:{settings.port}{db_part}?charset=utf8mb4"

    if settings.dbms == "PostgreSQL":
        db_name = quote_plus(database or "postgres")
        return f"postgresql+psycopg://{user}:{password}@{host}:{settings.port}/{db_name}"

    if settings.dbms == "MSSQL":
        driver = quote_plus(settings.mssql_driver)
        db_part = f"Database={database};" if database else ""
        trust = "yes" if settings.trust_server_certificate else "no"
        odbc = (
            f"Driver={{{settings.mssql_driver}}};"
            f"Server={host},{settings.port};"
            f"{db_part}"
            f"UID={settings.username};"
            f"PWD={settings.password};"
            "Encrypt=yes;"
            f"TrustServerCertificate={trust};"
        )
        return f"mssql+pyodbc:///?odbc_connect={quote_plus(odbc)}&driver={driver}"

    if settings.dbms == "Oracle":
        if settings.oracle_service_mode == "sid":
            dsn = f"{host}:{settings.port}/{quote_plus(database)}"
        else:
            dsn = f"{host}:{settings.port}?service_name={quote_plus(database)}"
        return f"oracle+oracledb://{user}:{password}@{dsn}"

    raise ValueError(f"지원하지 않는 DBMS입니다: {settings.dbms}")


def create_db_engine(settings: ConnectionSettings, *, database: str | None = None) -> Engine:
    ensure_driver_available(settings.dbms)
    selected = replace(settings, database=database) if database is not None else settings
    try:
        engine = create_engine(build_url(selected), pool_pre_ping=True, future=True)
    except NoSuchModuleError as exc:
        raise RuntimeError(DRIVER_HINTS[selected.dbms]) from exc
    return engine


def test_connection(engine: Engine) -> None:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))


def list_namespaces(engine: Engine, settings: ConnectionSettings) -> list[str]:
    with engine.connect() as conn:
        if settings.dbms == "MySQL":
            rows = conn.execute(text("SHOW DATABASES")).scalars().all()
            return [name for name in rows if name.lower() not in SYSTEM_NAMESPACES]
        if settings.dbms == "MSSQL":
            rows = conn.execute(
                text(
                    "SELECT name FROM sys.databases "
                    "WHERE database_id > 4 AND state_desc = 'ONLINE' "
                    "ORDER BY name"
                )
            ).scalars().all()
            return list(rows)

    inspector = inspect(engine)
    names = inspector.get_schema_names()
    if settings.dbms == "Oracle":
        hidden = {"SYS", "SYSTEM", "XDB", "MDSYS", "ORDSYS", "CTXSYS", "DBSNMP"}
        return [name for name in names if name.upper() not in hidden]
    return [name for name in names if name.lower() not in SYSTEM_NAMESPACES]


def list_tables(engine: Engine, settings: ConnectionSettings, namespace: str) -> list[str]:
    inspector = inspect(engine)
    schema = _metadata_schema(settings, namespace)
    return sorted(inspector.get_table_names(schema=schema))


def list_views(engine: Engine, settings: ConnectionSettings, namespace: str) -> list[str]:
    inspector = inspect(engine)
    schema = _metadata_schema(settings, namespace)
    try:
        return sorted(inspector.get_view_names(schema=schema))
    except NotImplementedError:
        return []


def reflect_database(
    engine: Engine,
    settings: ConnectionSettings,
    namespace: str,
    selected_tables: Iterable[str],
) -> DatabaseModel:
    inspector = inspect(engine)
    schema = _metadata_schema(settings, namespace)
    display_schema = _display_schema(settings, namespace)
    table_names = list(selected_tables)
    table_set = set(table_names)

    tables: list[TableModel] = []
    relationships: list[RelationshipModel] = []

    for table_name in table_names:
        columns = inspector.get_columns(table_name, schema=schema)
        pk = inspector.get_pk_constraint(table_name, schema=schema) or {}
        pk_columns = set(pk.get("constrained_columns") or [])
        fks = inspector.get_foreign_keys(table_name, schema=schema) or []
        fk_by_column = _foreign_key_map(fks)
        table_comment = _table_comment(inspector, table_name, schema)

        column_models = [
            ColumnModel(
                name=column["name"],
                logical_name=infer_logical_name(_string_or_none(column.get("comment")), column["name"]),
                data_type=str(column.get("type", "")),
                nullable=bool(column.get("nullable", True)),
                default=_string_or_none(column.get("default")),
                comment=_string_or_none(column.get("comment")),
                is_primary_key=column["name"] in pk_columns,
                foreign_key=fk_by_column.get(column["name"]),
            )
            for column in columns
        ]

        table = TableModel(
            name=table_name,
            schema=display_schema,
            logical_name=infer_logical_name(table_comment, table_name),
            comment=table_comment,
            columns=column_models,
        )
        tables.append(table)

        for fk in fks:
            referred_table = fk.get("referred_table")
            if not referred_table or referred_table not in table_set:
                continue
            from_cols = tuple(fk.get("constrained_columns") or [])
            to_cols = tuple(fk.get("referred_columns") or [])
            if not from_cols or not to_cols:
                continue
            relationships.append(
                RelationshipModel(
                    name=fk.get("name") or f"fk_{table_name}_{referred_table}",
                    from_table=_qualified(display_schema, table_name),
                    from_columns=from_cols,
                    to_table=_qualified(display_schema, referred_table),
                    to_columns=to_cols,
                )
            )

    return DatabaseModel(settings.dbms, namespace, tables, relationships)


def _foreign_key_map(foreign_keys: list[dict]) -> dict[str, str]:
    values: dict[str, str] = {}
    for fk in foreign_keys:
        referred_table = fk.get("referred_table")
        referred_columns = fk.get("referred_columns") or []
        for index, column in enumerate(fk.get("constrained_columns") or []):
            target = referred_columns[index] if index < len(referred_columns) else "?"
            values[column] = f"{referred_table}.{target}"
    return values


def _table_comment(inspector, table_name: str, schema: str | None) -> str | None:
    try:
        comment = inspector.get_table_comment(table_name, schema=schema)
    except Exception:
        return None
    text_value = comment.get("text") if isinstance(comment, dict) else None
    return _string_or_none(text_value)


def _qualified(schema: str | None, table_name: str) -> str:
    return f"{schema}.{table_name}" if schema else table_name


def _metadata_schema(settings: ConnectionSettings, namespace: str) -> str | None:
    return None if settings.dbms in {"MySQL", "MSSQL"} else namespace


def _display_schema(settings: ConnectionSettings, namespace: str) -> str | None:
    return namespace if settings.dbms in {"MySQL", "MSSQL"} else _metadata_schema(settings, namespace)


def _string_or_none(value) -> str | None:
    if value is None:
        return None
    text_value = str(value).strip()
    return text_value or None
