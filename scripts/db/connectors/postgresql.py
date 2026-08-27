"""Lazy PostgreSQL connector and database/server identity probe."""

from __future__ import annotations

from typing import Any

from scripts.db.connection_profiles import ENGINE_POSTGRESQL
from scripts.db.connectors.base import (
    AttestedIdentity,
    ConnectorError,
    EngineConnector,
)


class PostgresqlConnector:
    engine = ENGINE_POSTGRESQL

    def connect(
        self,
        connection_value: str,
        *,
        driver: Any = None,
        timeout_s: float | None = None,
    ) -> Any:
        if driver is None:
            try:
                import psycopg
            except ImportError as exc:
                raise ConnectorError("postgresql driver 'psycopg' is unavailable") from exc
            driver = psycopg

        try:
            if timeout_s is None:
                return driver.connect(connection_value)
            return driver.connect(connection_value, connect_timeout=timeout_s)
        except Exception as exc:
            raise ConnectorError("postgresql connection failed") from exc

    def identity_probe(self, connection: Any) -> AttestedIdentity:
        database = self._probe_value(
            self.fetch_one(connection, "SELECT current_database()"),
            "database",
        )
        # connection.info.host is the client-supplied route and may be a DNS
        # alias. Use the server-reported address for the attested identity.
        host = self._probe_value(
            self.fetch_one(connection, "SELECT inet_server_addr()"),
            "server",
        )
        port = self._probe_port(
            self.fetch_one(connection, "SELECT inet_server_port()"),
        )
        return AttestedIdentity(
            engine=ENGINE_POSTGRESQL,
            server_identity=f"{host.strip()}:{port}",
            database_identity=database,
        )

    def fetch_one(self, connection: Any, sql: str, params: Any = None) -> Any:
        cursor = self._cursor(connection, "fetch_one")
        try:
            self._execute_cursor(cursor, sql, params)
            return cursor.fetchone()
        except Exception as exc:
            raise ConnectorError("postgresql fetch_one failed") from exc
        finally:
            self._close_cursor(cursor)

    def fetch_all(self, connection: Any, sql: str, params: Any = None) -> Any:
        cursor = self._cursor(connection, "fetch_all")
        try:
            self._execute_cursor(cursor, sql, params)
            return cursor.fetchall()
        except Exception as exc:
            raise ConnectorError("postgresql fetch_all failed") from exc
        finally:
            self._close_cursor(cursor)

    def execute(self, connection: Any, sql: str, params: Any = None) -> int:
        cursor = self._cursor(connection, "execute")
        try:
            self._execute_cursor(cursor, sql, params)
            rowcount = int(cursor.rowcount)
        except Exception as exc:
            self._rollback(connection)
            raise ConnectorError("postgresql execute failed") from exc
        finally:
            self._close_cursor(cursor)
        try:
            connection.commit()
        except Exception as exc:
            raise ConnectorError("postgresql execute commit failed") from exc
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
            raise ConnectorError("postgresql connection close failed") from exc

    @staticmethod
    def _cursor(connection: Any, operation: str) -> Any:
        try:
            return connection.cursor()
        except Exception as exc:
            raise ConnectorError(f"postgresql {operation} cursor failed") from exc

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
            raise ConnectorError(
                f"postgresql {field_name} identity probe returned invalid shape"
            )
        try:
            if len(row) != 1:
                raise ConnectorError(
                    f"postgresql {field_name} identity probe returned invalid shape"
                )
            value = row[0]
        except ConnectorError:
            raise
        except Exception as exc:
            raise ConnectorError(
                f"postgresql {field_name} identity probe returned invalid shape"
            ) from exc
        if not isinstance(value, str) or not value.strip():
            raise ConnectorError(
                f"postgresql {field_name} identity probe returned invalid value"
            )
        return value

    @staticmethod
    def _probe_port(row: Any) -> str:
        if row is None or isinstance(row, (str, bytes)):
            raise ConnectorError(
                "postgresql port identity probe returned invalid shape"
            )
        try:
            if len(row) != 1:
                raise ConnectorError(
                    "postgresql port identity probe returned invalid shape"
                )
            value = row[0]
        except ConnectorError:
            raise
        except Exception as exc:
            raise ConnectorError(
                "postgresql port identity probe returned invalid shape"
            ) from exc

        if isinstance(value, bool):
            raise ConnectorError(
                "postgresql port identity probe returned invalid value"
            )
        if isinstance(value, int):
            port = value
        elif isinstance(value, str) and value and all(
            "0" <= character <= "9" for character in value
        ):
            port = int(value)
        else:
            raise ConnectorError(
                "postgresql port identity probe returned invalid value"
            )
        if not 1 <= port <= 65535:
            raise ConnectorError(
                "postgresql port identity probe returned invalid value"
            )
        return str(port)


PostgreSQLConnector = PostgresqlConnector

__all__ = [
    "AttestedIdentity",
    "ConnectorError",
    "EngineConnector",
    "PostgresqlConnector",
    "PostgreSQLConnector",
]
