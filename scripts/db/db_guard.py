"""Capability boundary for repository-owned database operations.

Callers select a canonical profile and receive a narrow session capability.
The opaque connection, connector, attestation, classification, and audit
details remain inside this module.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Collection

from scripts.db.connection_profiles import (
    CAPABILITY_READ_WRITE,
    ENGINE_MSSQL,
    ENGINE_POSTGRESQL,
    ENVIRONMENT_TEST,
    PROFILES,
    resolve_connection_profile,
)
from scripts.db.sql_classification import (
    BatchClassification,
    OPERATION_CLASSES as _OPERATION_CLASSES,
    classify_batch,
)
from scripts.db.target_metadata import (
    EXPECTED_TARGETS as _EXPECTED_TARGETS,
    ExpectedTarget,
    get_expected_target,
    validate_target_metadata,
)


_BLOCK_REASONS = frozenset(
    {
        "unknown-profile",
        "resolution-failure",
        "missing-target-metadata",
        "attestation-mismatch",
        "probe-failure",
        "capability-mismatch",
        "privileged-denied",
        "unknown-denied",
        "hazardous-on-readonly",
        "classifier-failure",
        "audit-failure",
    }
)
_EMPTY_STATEMENT_HASH = hashlib.sha256(b"").hexdigest()
_SESSION_TOKEN = object()


class GuardBlockedError(Exception):
    """Raised when a safety condition blocks a DB operation."""

    reason: str

    def __init__(self, reason: str, message: str | None = None) -> None:
        if reason not in _BLOCK_REASONS:
            raise ValueError("unsupported guard block reason")
        self.reason = reason
        super().__init__(message or reason)


@dataclass(frozen=True)
class _AuditContext:
    tool_id: str
    profile: Any = None
    identity: Any = None
    sink: Callable[[str], None] | None = None


def open_readonly(
    profile_name: str,
    *,
    tool_id: str,
    allowed_profiles: Collection[str] | None = None,
    audit_sink: Callable[[str], None] | None = None,
) -> ReadOnlySession:
    """Open an attested read-only capability for a canonical profile."""
    return _open_session(
        profile_name,
        tool_id=tool_id,
        allowed_profiles=allowed_profiles,
        audit_sink=audit_sink,
        writable=False,
    )


def open_test_readwrite(
    profile_name: str,
    *,
    tool_id: str,
    allowed_profiles: Collection[str] | None = None,
    audit_sink: Callable[[str], None] | None = None,
) -> TestWriteSession:
    """Open an attested test read-write capability."""
    return _open_session(
        profile_name,
        tool_id=tool_id,
        allowed_profiles=allowed_profiles,
        audit_sink=audit_sink,
        writable=True,
    )


def _open_session(
    profile_name: str,
    *,
    tool_id: str,
    allowed_profiles: Collection[str] | None,
    audit_sink: Callable[[str], None] | None,
    writable: bool,
) -> ReadOnlySession | TestWriteSession:
    _validate_tool_id(tool_id)
    profile = _known_profile(profile_name)
    context = _AuditContext(tool_id=tool_id, profile=profile, sink=audit_sink)
    connection: Any = None
    connector: Any = None

    try:
        operation = "write" if writable else "read"
        try:
            resolved = resolve_connection_profile(
                profile_name,
                allowed_profiles=allowed_profiles,
                operation=operation,
            )
        except Exception:
            reason = (
                "unknown-profile"
                if _known_profile(profile_name) is None
                else "resolution-failure"
            )
            raise GuardBlockedError(reason, "connection profile resolution failed") from None

        profile = resolved.profile
        context = _AuditContext(tool_id=tool_id, profile=profile, sink=audit_sink)

        if writable and (
            profile.environment != ENVIRONMENT_TEST
            or profile.capability != CAPABILITY_READ_WRITE
        ):
            raise GuardBlockedError(
                "capability-mismatch",
                "write capability requires a canonical test read-write profile",
            )

        try:
            if validate_target_metadata(
                profiles=PROFILES,
                targets=_EXPECTED_TARGETS,
                require_production_resolved=writable,
            ):
                raise GuardBlockedError(
                    "missing-target-metadata",
                    "expected target metadata is invalid",
                )
            expected_target = get_expected_target(
                profile.name,
                targets=_EXPECTED_TARGETS,
            )
        except Exception:
            raise GuardBlockedError(
                "missing-target-metadata",
                "expected target metadata is unavailable",
            ) from None

        connector = _select_connector(profile.engine)
        try:
            connection = connector.connect(resolved.connection_value)
            if connection is None:
                raise _connector_error("connector returned no connection")
            identity = connector.identity_probe(connection)
        except Exception:
            _close_failed_connection(connector, connection)
            raise GuardBlockedError(
                "probe-failure",
                "database connection identity probe failed",
            ) from None

        if not _valid_identity_shape(identity):
            _close_failed_connection(connector, connection)
            raise GuardBlockedError(
                "probe-failure",
                "database connection identity probe returned invalid data",
            )

        context = _AuditContext(
            tool_id=tool_id,
            profile=profile,
            identity=identity,
            sink=audit_sink,
        )
        if not _identity_matches(identity, profile.engine, expected_target):
            _close_failed_connection(connector, connection)
            raise GuardBlockedError(
                "attestation-mismatch",
                "connected database identity does not match expected target",
            )

        if writable:
            return TestWriteSession(
                _SESSION_TOKEN,
                connector,
                connection,
                context,
                expected_target,
            )
        return ReadOnlySession(
            _SESSION_TOKEN,
            connector,
            connection,
            context,
            expected_target,
        )
    except GuardBlockedError as blocked:
        _emit_best_effort(
            context,
            classification=None,
            outcome="blocked",
            reason=blocked.reason,
        )
        raise


def _validate_tool_id(tool_id: str) -> None:
    if not isinstance(tool_id, str) or not tool_id.strip():
        raise GuardBlockedError("resolution-failure", "tool_id is required")


def _known_profile(profile_name: Any) -> Any:
    if not isinstance(profile_name, str):
        return None
    return PROFILES.get(profile_name)


def _select_connector(engine: str) -> Any:
    if engine == ENGINE_MSSQL:
        from scripts.db.connectors.mssql import MssqlConnector

        connector_type = MssqlConnector
    elif engine == ENGINE_POSTGRESQL:
        from scripts.db.connectors.postgresql import PostgresqlConnector

        connector_type = PostgresqlConnector
    else:
        raise GuardBlockedError(
            "capability-mismatch",
            "profile engine has no approved connector",
        )
    try:
        return connector_type()
    except Exception:
        raise GuardBlockedError(
            "capability-mismatch",
            "approved connector could not be constructed",
        ) from None


def _valid_identity_shape(identity: Any) -> bool:
    try:
        values = (
            identity.engine,
            identity.server_identity,
            identity.database_identity,
        )
    except AttributeError:
        return False
    return all(
        isinstance(value, str) and bool(value.strip())
        for value in values
    )


def _identity_matches(
    identity: Any,
    expected_engine: str,
    expected_target: ExpectedTarget,
) -> bool:
    return (
        identity.engine == expected_engine
        and identity.server_identity == expected_target.server_identity
        and identity.database_identity == expected_target.database_identity
    )


def _close_failed_connection(connector: Any, connection: Any) -> None:
    if connector is None or connection is None:
        return
    try:
        connector.close(connection)
    except Exception:
        pass


def _connector_error(message: str) -> Exception:
    from scripts.db.connectors.base import ConnectorError

    return ConnectorError(message)


class _SessionBase:
    __slots__ = (
        "_connector",
        "_connection",
        "_context",
        "_expected_target",
        "_closed",
    )
    # P-2 treats underscore attributes as module-private by convention. The
    # capability API is the supported seam; this is not a runtime attribute
    # firewall for callers that deliberately violate Python privacy.

    def __init__(
        self,
        token: object,
        connector: Any,
        connection: Any,
        context: _AuditContext,
        expected_target: ExpectedTarget,
    ) -> None:
        if token is not _SESSION_TOKEN:
            raise TypeError("sessions must be opened through a guard factory")
        self._connector = connector
        self._connection = connection
        self._context = context
        self._expected_target = expected_target
        self._closed = False

    def fetch_one(self, sql: str, params: Any = None) -> Any:
        classification = self._classify(sql)
        self._require_read(classification)
        self._ensure_open()
        try:
            return self._connector.fetch_one(self._connection, sql, params)
        except Exception:
            raise _connector_error("database fetch_one failed") from None

    def fetch_all(self, sql: str, params: Any = None) -> Any:
        classification = self._classify(sql)
        self._require_read(classification)
        self._ensure_open()
        try:
            return self._connector.fetch_all(self._connection, sql, params)
        except Exception:
            raise _connector_error("database fetch_all failed") from None

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self._connector.close(self._connection)
        except Exception:
            raise _connector_error("database connection close failed") from None

    def __enter__(self) -> _SessionBase:
        self._ensure_open()
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> bool:
        self.close()
        return False

    def _ensure_open(self) -> None:
        if self._closed:
            raise GuardBlockedError("resolution-failure", "database session is closed")

    def _classify(self, sql: str) -> BatchClassification:
        try:
            classification = classify_batch(sql)
            if not isinstance(classification, BatchClassification):
                raise TypeError("classifier returned an invalid result")
            if classification.operation_class not in _OPERATION_CLASSES:
                raise ValueError("classifier returned an unknown operation class")
            if not isinstance(classification.statement_hash, str):
                raise TypeError("classifier returned an invalid statement hash")
            if not isinstance(classification.preview, str):
                raise TypeError("classifier returned an invalid preview")
            if "\n" in classification.preview or "\r" in classification.preview:
                raise ValueError("classifier returned a multiline preview")
            return classification
        except Exception:
            _emit_best_effort(
                self._context,
                classification=None,
                outcome="blocked",
                reason="classifier-failure",
            )
            raise GuardBlockedError(
                "classifier-failure",
                "operation could not be classified",
            ) from None

    def _require_read(self, classification: BatchClassification) -> None:
        if classification.operation_class == "read":
            return
        reason = _reason_for_denied_class(classification.operation_class, readonly=True)
        _emit_best_effort(
            self._context,
            classification=classification,
            outcome="blocked",
            reason=reason,
        )
        raise GuardBlockedError(reason, "operation is not allowed through read capability")


class ReadOnlySession(_SessionBase):
    """Read/query capability with no generic execution method."""

    __slots__ = ()


class TestWriteSession(_SessionBase):
    """Attested test capability with one classified and audited execute path."""

    __slots__ = ()

    def execute(self, sql: str, params: Any = None) -> int:
        classification = self._classify(sql)
        if classification.operation_class in {"privileged", "unknown"}:
            reason = _reason_for_denied_class(
                classification.operation_class,
                readonly=False,
            )
            _emit_best_effort(
                self._context,
                classification=classification,
                outcome="blocked",
                reason=reason,
            )
            raise GuardBlockedError(reason, "operation is denied by the guard")

        self._ensure_open()
        _emit_required(
            self._context,
            classification=classification,
            outcome="allowed",
        )
        try:
            result = self._connector.execute(self._connection, sql, params)
        except Exception:
            _emit_best_effort(
                self._context,
                classification=classification,
                outcome="failed",
                reason="execution-failure",
            )
            raise _connector_error("database execution failed") from None

        _emit_best_effort(
            self._context,
            classification=classification,
            outcome="succeeded",
        )
        return int(result)


def _reason_for_denied_class(operation_class: str, *, readonly: bool) -> str:
    if operation_class == "privileged":
        return "privileged-denied"
    if operation_class == "unknown":
        return "unknown-denied"
    return "hazardous-on-readonly" if readonly else "capability-mismatch"


def _emit_required(
    context: _AuditContext,
    *,
    classification: BatchClassification | None,
    outcome: str,
    reason: str | None = None,
) -> None:
    try:
        _emit(context, classification=classification, outcome=outcome, reason=reason)
    except Exception:
        raise GuardBlockedError(
            "audit-failure",
            "required audit event could not be emitted",
        ) from None


def _emit_best_effort(
    context: _AuditContext,
    *,
    classification: BatchClassification | None,
    outcome: str,
    reason: str | None = None,
) -> None:
    try:
        _emit(context, classification=classification, outcome=outcome, reason=reason)
    except Exception:
        pass


def _emit(
    context: _AuditContext,
    *,
    classification: BatchClassification | None,
    outcome: str,
    reason: str | None = None,
) -> None:
    profile = context.profile
    identity = context.identity
    event: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tool_id": context.tool_id,
        "profile_id": getattr(profile, "name", None),
        "engine": (
            getattr(identity, "engine", None)
            if identity is not None
            else getattr(profile, "engine", None)
        ),
        "environment": getattr(profile, "environment", None),
        "capability": getattr(profile, "capability", None),
        "attested_server_identity": getattr(identity, "server_identity", None),
        "attested_database_identity": getattr(identity, "database_identity", None),
        "operation_class": (
            classification.operation_class if classification is not None else None
        ),
        "sql_preview": classification.preview if classification is not None else "",
        "statement_hash": (
            classification.statement_hash
            if classification is not None
            else _EMPTY_STATEMENT_HASH
        ),
        "outcome": outcome,
    }
    if reason is not None:
        event["reason"] = reason
    line = json.dumps(event, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    sink = context.sink or _write_default_audit
    sink(line)


def _write_default_audit(line: str) -> None:
    sys.stderr.write(line + "\n")


__all__ = [
    "GuardBlockedError",
    "ReadOnlySession",
    "TestWriteSession",
    "open_readonly",
    "open_test_readwrite",
]
