"""Lazy MSSQL connector and server/database identity probe."""

from __future__ import annotations

from typing import Any

from scripts.db.connection_profiles import ENGINE_MSSQL
from scripts.db.connectors.base import (
    AttestedIdentity,
    ConnectorError,
    EngineConnector,
)


class MssqlConnector:
    engine = ENGINE_MSSQL

    def connect(
        self,
        connection_value: str,
        *,
        driver: Any = None,
        timeout_s: float | None = None,
    ) -> Any:
        if driver is None:
            try:
                import pyodbc
            except ImportError as exc:
                raise ConnectorError("mssql driver 'pyodbc' is unavailable") from exc
            driver = pyodbc

        try:
            if timeout_s is None:
                return driver.connect(connection_value)
            return driver.connect(connection_value, timeout=timeout_s)
        except Exception as exc:
            raise ConnectorError("mssql connection failed") from exc

    def identity_probe(self, connection: Any) -> AttestedIdentity:
        server = self._probe_value(
            self.fetch_one(connection, "SELECT @@SERVERNAME"),
            "server",
        )
        database = self._probe_value(
            self.fetch_one(connection, "SELECT DB_NAME()"),
            "database",
        )
        return AttestedIdentity(
            engine=ENGINE_MSSQL,
            server_identity=server,
            database_identity=database,
        )

    def fetch_one(self, connection: Any, sql: str, params: Any = None) -> Any:
        cursor = self._cursor(connection, "fetch_one")
        try:
            self._execute_cursor(cursor, sql, params)
            return cursor.fetchone()
        except Exception as exc:
            raise ConnectorError("mssql fetch_one failed") from exc
        finally:
            self._close_cursor(cursor)

    def fetch_all(self, connection: Any, sql: str, params: Any = None) -> Any:
        cursor = self._cursor(connection, "fetch_all")
        try:
            self._execute_cursor(cursor, sql, params)
            return cursor.fetchall()
        except Exception as exc:
            raise ConnectorError("mssql fetch_all failed") from exc
        finally:
            self._close_cursor(cursor)

    def execute(self, connection: Any, sql: str, params: Any = None) -> int:
        cursor = self._cursor(connection, "execute")
        try:
            self._execute_cursor(cursor, sql, params)
            rowcount = int(cursor.rowcount)
        except Exception as exc:
            self._rollback(connection)
            raise ConnectorError("mssql execute failed") from exc
        finally:
            self._close_cursor(cursor)
        try:
            connection.commit()
        except Exception as exc:
            raise ConnectorError("mssql execute commit failed") from exc
        return rowcount

    @staticmethod
    def _rollback(connection: Any) -> None:
        try:
            connection.rollback()
        except Exception:
            pass

    def close(self, connection: Any) -> None:
        try:
            connection.close()
        except Exception as exc:
            raise ConnectorError("mssql connection close failed") from exc

    @staticmethod
    def _cursor(connection: Any, operation: str) -> Any:
        try:
            return connection.cursor()
        except Exception as exc:
            raise ConnectorError(f"mssql {operation} cursor failed") from exc

    @staticmethod
    def _execute_cursor(cursor: Any, sql: str, params: Any) -> None:
        if params is None:
            cursor.execute(sql)
        else:
            cursor.execute(sql, params)

    @staticmethod
    def _close_cursor(cursor: Any) -> None:
        try:
            cursor.close()
        except Exception:
            pass

    @staticmethod
    def _probe_value(row: Any, field_name: str) -> str:
        if row is None or isinstance(row, (str, bytes)):
            raise ConnectorError(f"mssql {field_name} identity probe returned invalid shape")
        try:
            if len(row) != 1:
                raise ConnectorError(
                    f"mssql {field_name} identity probe returned invalid shape"
                )
            value = row[0]
        except ConnectorError:
            raise
        except Exception as exc:
            raise ConnectorError(
                f"mssql {field_name} identity probe returned invalid shape"
            ) from exc
        if not isinstance(value, str) or not value.strip():
            raise ConnectorError(
                f"mssql {field_name} identity probe returned invalid value"
            )
        return value


MSSQLConnector = MssqlConnector

__all__ = [
    "AttestedIdentity",
    "ConnectorError",
    "EngineConnector",
    "MssqlConnector",
    "MSSQLConnector",
]
