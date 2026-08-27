"""Public-seam tests for the Issue #20 engine connectors."""

from __future__ import annotations

import builtins
import sys
from dataclasses import dataclass, field

import pytest

from scripts.db.sql_classification import classify_batch


@dataclass
class FakeCursor:
    connection: "FakeConnection"
    executed: list[tuple[str, tuple[object, ...]]] = field(default_factory=list)
    closed: bool = False

    def execute(self, sql: str, *params: object) -> None:
        self.executed.append((sql, params))
        if self.connection.execute_error is not None:
            raise self.connection.execute_error

    def fetchone(self):
        sql = self.executed[-1][0]
        values = self.connection.rows.get(sql, [])
        return values[0] if values else None

    def fetchall(self):
        sql = self.executed[-1][0]
        return list(self.connection.rows.get(sql, []))

    @property
    def rowcount(self) -> int:
        return self.connection.rowcount

    def close(self) -> None:
        self.closed = True


@dataclass
class FakeConnection:
    rows: dict[str, list[object]] = field(default_factory=dict)
    host: str = "db.example"
    port: int = 5432
    rowcount: int = 3
    execute_error: Exception | None = None
    cursors: list[FakeCursor] = field(default_factory=list)
    closed: bool = False

    def cursor(self) -> FakeCursor:
        cursor = FakeCursor(self)
        self.cursors.append(cursor)
        return cursor

    def close(self) -> None:
        self.closed = True


@dataclass
class FakeDriver:
    connection: FakeConnection
    calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = field(
        default_factory=list
    )
    connect_error: Exception | None = None

    def connect(self, value: str, *args: object, **kwargs: object) -> FakeConnection:
        self.calls.append((value, args, kwargs))
        if self.connect_error is not None:
            raise self.connect_error
        return self.connection


def test_connector_modules_import_without_loading_optional_drivers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delitem(sys.modules, "pyodbc", raising=False)
    monkeypatch.delitem(sys.modules, "psycopg", raising=False)

    import scripts.db.connectors.mssql  # noqa: F401
    import scripts.db.connectors.postgresql  # noqa: F401

    assert "pyodbc" not in sys.modules
    assert "psycopg" not in sys.modules


@pytest.mark.parametrize(
    ("module_name", "connector_name"),
    [
        ("pyodbc", "MssqlConnector"),
        ("psycopg", "PostgresqlConnector"),
    ],
)
def test_missing_driver_is_wrapped_without_connection_value(
    monkeypatch: pytest.MonkeyPatch, module_name: str, connector_name: str
) -> None:
    module = (
        __import__("scripts.db.connectors.mssql", fromlist=[connector_name])
        if module_name == "pyodbc"
        else __import__("scripts.db.connectors.postgresql", fromlist=[connector_name])
    )
    connector = getattr(module, connector_name)()
    sentinel = "mssql://user:SECRET-VALUE@db.example/app"
    real_import = builtins.__import__

    def deny_driver(name, globals=None, locals=None, fromlist=(), level=0):
        if name == module_name:
            raise ImportError(module_name)
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", deny_driver)
    with pytest.raises(module.ConnectorError) as raised:
        connector.connect(sentinel)
    assert module_name in str(raised.value)
    assert sentinel not in str(raised.value)
    assert "SECRET-VALUE" not in str(raised.value)


def test_mssql_connect_uses_injected_driver() -> None:
    from scripts.db.connectors.mssql import MssqlConnector

    connection = FakeConnection()
    driver = FakeDriver(connection)
    result = MssqlConnector().connect("mssql-opaque-value", driver=driver, timeout_s=4.5)
    assert result is connection
    assert driver.calls == [("mssql-opaque-value", (), {"timeout": 4.5})]


def test_mssql_probe_uses_server_and_database_identity_queries() -> None:
    from scripts.db.connectors.mssql import MssqlConnector

    connection = FakeConnection(
        rows={
            "SELECT @@SERVERNAME": [("mssql-server",)],
            "SELECT DB_NAME()": [("application",)],
        }
    )
    identity = MssqlConnector().identity_probe(connection)
    assert (identity.engine, identity.server_identity, identity.database_identity) == (
        "mssql",
        "mssql-server",
        "application",
    )
    assert [call[0] for cursor in connection.cursors for call in cursor.executed] == [
        "SELECT @@SERVERNAME",
        "SELECT DB_NAME()",
    ]


def test_postgresql_connect_and_probe_use_database_query_and_server_address() -> None:
    from scripts.db.connectors.postgresql import PostgresqlConnector

    connection = FakeConnection(
        rows={
            "SELECT current_database()": [("application_test",)],
            "SELECT inet_server_addr()": [("10.20.30.40",)],
        },
        host="postgres.example",
        port=5433,
    )
    driver = FakeDriver(connection)
    connector = PostgresqlConnector()
    assert connector.connect("postgres-opaque-value", driver=driver) is connection
    identity = connector.identity_probe(connection)
    assert (identity.engine, identity.server_identity, identity.database_identity) == (
        "postgresql",
        "10.20.30.40:5433",
        "application_test",
    )
    assert [call[0] for cursor in connection.cursors for call in cursor.executed] == [
        "SELECT current_database()",
        "SELECT inet_server_addr()",
    ]


def test_every_identity_probe_query_is_classified_as_read() -> None:
    assert classify_batch("SELECT @@SERVERNAME").operation_class == "read"
    assert classify_batch("SELECT DB_NAME()").operation_class == "read"
    assert classify_batch("SELECT current_database()").operation_class == "read"
    assert classify_batch("SELECT inet_server_addr()").operation_class == "read"


def test_execute_passes_parameters_without_interpolation_and_returns_rowcount() -> None:
    from scripts.db.connectors.mssql import MssqlConnector

    connection = FakeConnection(rowcount=7)
    sentinel = "SECRET-VALUE"
    count = MssqlConnector().execute(
        connection,
        "UPDATE accounts SET name = ? WHERE id = ?",
        (sentinel, 4),
    )
    assert count == 7
    assert connection.cursors[0].executed == [
        ("UPDATE accounts SET name = ? WHERE id = ?", ((sentinel, 4),))
    ]


def test_fetch_methods_and_close_delegate_to_connection() -> None:
    from scripts.db.connectors.postgresql import PostgresqlConnector

    connection = FakeConnection(rows={"SELECT id FROM accounts": [(1,), (2,)]})
    connector = PostgresqlConnector()
    assert connector.fetch_one(connection, "SELECT id FROM accounts") == (1,)
    assert connector.fetch_all(connection, "SELECT id FROM accounts") == [(1,), (2,)]
    connector.close(connection)
    assert connection.closed


@pytest.mark.parametrize(
    "rows",
    [
        [],
        [(None,)],
        [(" ",)],
        [("server", "database")],
    ],
)
def test_mssql_probe_rejects_missing_null_empty_or_wrong_shape(rows: list[object]) -> None:
    from scripts.db.connectors.mssql import ConnectorError, MssqlConnector

    connection = FakeConnection(
        rows={
            "SELECT @@SERVERNAME": rows,
            "SELECT DB_NAME()": [("application",)],
        }
    )
    with pytest.raises(ConnectorError):
        MssqlConnector().identity_probe(connection)


def test_probe_exceptions_are_connector_errors_and_do_not_echo_values() -> None:
    from scripts.db.connectors.mssql import ConnectorError, MssqlConnector

    sentinel = "mssql://user:SECRET-VALUE@db.example/app"
    connection = FakeConnection(execute_error=TimeoutError(sentinel))
    with pytest.raises(ConnectorError) as raised:
        MssqlConnector().identity_probe(connection)
    assert sentinel not in str(raised.value)
    assert "SECRET-VALUE" not in str(raised.value)


def test_normal_probe_values_are_returned_even_when_they_do_not_match_a_target() -> None:
    from scripts.db.connectors.mssql import MssqlConnector

    connection = FakeConnection(
        rows={
            "SELECT @@SERVERNAME": [("unexpected-server",)],
            "SELECT DB_NAME()": [("unexpected-database",)],
        }
    )
    identity = MssqlConnector().identity_probe(connection)
    assert identity.server_identity == "unexpected-server"
    assert identity.database_identity == "unexpected-database"
