"""Shared connector types for the DB execution safety guard.

This module deliberately imports no database driver.  Concrete engine
connectors own their optional lazy imports.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class AttestedIdentity:
    engine: str
    server_identity: str
    database_identity: str


class ConnectorError(Exception):
    """Raised for connection, probe, or low-level connector failures."""


class EngineConnector(Protocol):
    engine: str

    def connect(
        self,
        connection_value: str,
        *,
        driver: Any = None,
        timeout_s: float | None = None,
    ) -> Any:
        ...

    def identity_probe(self, connection: Any) -> AttestedIdentity:
        ...

    def fetch_one(self, connection: Any, sql: str, params: Any = None) -> Any:
        ...

    def fetch_all(self, connection: Any, sql: str, params: Any = None) -> Any:
        ...

    def execute(self, connection: Any, sql: str, params: Any = None) -> int:
        ...

    def close(self, connection: Any) -> None:
        ...
