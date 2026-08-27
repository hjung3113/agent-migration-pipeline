"""Public-seam tests for the Issue #20 DB execution guard."""

from __future__ import annotations

import inspect
import json
import os
from dataclasses import dataclass, field
from unittest.mock import patch

import pytest

import scripts.db.db_guard as db_guard
from scripts.db.connection_profiles import ENGINE_MSSQL, ENGINE_POSTGRESQL
from scripts.db.sql_classification import BatchClassification
from scripts.db.target_metadata import ExpectedTarget


SENTINEL_CONNECTION = "mssql://user:SECRET-VALUE@db.example/app"
SENTINEL_PARAMETER = "PARAM-SECRET-VALUE"
SENTINEL_ROW = "ROW-SECRET-VALUE"
TARGETS = {
    "mssql-prod-ro": ExpectedTarget("prod-server", "app"),
    "mssql-test-rw": ExpectedTarget("test-server", "app_test"),
    "postgres-test-rw": ExpectedTarget("pg-server:5432", "pg_app_test"),
}
ENVIRON = {
    "MSSQL_PROD_RO_CONN": SENTINEL_CONNECTION,
    "MSSQL_TEST_RW_CONN": SENTINEL_CONNECTION,
    "PG_TEST_RW_CONN": SENTINEL_CONNECTION,
}


@dataclass
class FakeIdentity:
    engine: str
    server_identity: str
    database_identity: str


@dataclass
class FakeConnector:
    engine: str = ENGINE_MSSQL
    identity: FakeIdentity = field(
        default_factory=lambda: FakeIdentity(
            ENGINE_MSSQL, "prod-server", "app"
        )
    )
    probe_error: Exception | None = None
    connect_error: Exception | None = None
    execute_error: Exception | None = None
    fetch_error: Exception | None = None
    row: object = (1,)
    rows: list[object] = field(default_factory=lambda: [(1,)])
    connect_calls: list[str] = field(default_factory=list)
    probe_calls: list[object] = field(default_factory=list)
    fetch_one_calls: list[tuple[object, str, object]] = field(default_factory=list)
    fetch_all_calls: list[tuple[object, str, object]] = field(default_factory=list)
    execute_calls: list[tuple[object, str, object]] = field(default_factory=list)
    close_calls: list[object] = field(default_factory=list)

    def connect(self, connection_value: str, **_kwargs: object) -> object:
        self.connect_calls.append(connection_value)
        if self.connect_error is not None:
            raise self.connect_error
        return object()

    def identity_probe(self, connection: object) -> FakeIdentity:
        self.probe_calls.append(connection)
        if self.probe_error is not None:
            raise self.probe_error
        return self.identity

    def fetch_one(self, connection: object, sql: str, params=None):
        self.fetch_one_calls.append((connection, sql, params))
        if self.fetch_error is not None:
            raise self.fetch_error
        return self.row

    def fetch_all(self, connection: object, sql: str, params=None):
        self.fetch_all_calls.append((connection, sql, params))
        if self.fetch_error is not None:
            raise self.fetch_error
        return self.rows

    def execute(self, connection: object, sql: str, params=None) -> int:
        self.execute_calls.append((connection, sql, params))
        if self.execute_error is not None:
            raise self.execute_error
        return 1

    def close(self, connection: object) -> None:
        self.close_calls.append(connection)


def _events() -> list[str]:
    return []


def _open_readonly(
    connector: FakeConnector,
    events: list[str] | None = None,
    *,
    metadata: object = TARGETS,
    environ: dict[str, str] | None = None,
):
    with patch.object(db_guard, "_EXPECTED_TARGETS", metadata):
        with patch.dict(os.environ, ENVIRON if environ is None else environ, clear=True):
            return db_guard.open_readonly(
                "mssql-prod-ro",
                tool_id="test-tool",
                connector_overrides={ENGINE_MSSQL: connector},
                audit_sink=(events if events is not None else _events()).append,
            )


def _open_test(
    connector: FakeConnector,
    events: list[str] | None = None,
    *,
    metadata: object = TARGETS,
    environ: dict[str, str] | None = None,
    profile_name: str = "mssql-test-rw",
):
    with patch.object(db_guard, "_EXPECTED_TARGETS", metadata):
        with patch.dict(os.environ, ENVIRON if environ is None else environ, clear=True):
            return db_guard.open_test_readwrite(
                profile_name,
                tool_id="test-tool",
                connector_overrides={ENGINE_MSSQL: connector},
                audit_sink=(events if events is not None else _events()).append,
            )


def _event_lines(events: list[str]) -> list[dict[str, object]]:
    return [json.loads(line) for line in events]


def test_public_factory_signatures_have_no_raw_connection_or_bypass_argument() -> None:
    expected = [
        "profile_name",
        "tool_id",
        "allowed_profiles",
        "connector_overrides",
        "audit_sink",
    ]
    for factory in (db_guard.open_readonly, db_guard.open_test_readwrite):
        parameters = list(inspect.signature(factory).parameters.values())
        assert [parameter.name for parameter in parameters] == expected
        assert "metadata" not in inspect.signature(factory).parameters
        assert "environ" not in inspect.signature(factory).parameters
        assert parameters[0].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        assert all(
            parameter.kind is inspect.Parameter.KEYWORD_ONLY
            for parameter in parameters[1:]
        )


def test_guard_block_reasons_are_fixed_and_exposed_on_the_exception() -> None:
    allowed = {
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
    for reason in allowed:
        error = db_guard.GuardBlockedError(reason)
        assert error.reason == reason


def test_readonly_session_requires_matching_identity_before_fetch() -> None:
    connector = FakeConnector()
    session = _open_readonly(connector)
    assert session.fetch_one("SELECT id FROM accounts") == (1,)
    assert len(connector.probe_calls) == 1
    assert connector.fetch_one_calls[0][1] == "SELECT id FROM accounts"


def test_production_read_session_is_attested_and_closes_through_connector() -> None:
    connector = FakeConnector()
    with _open_readonly(connector) as session:
        assert session.fetch_all("SELECT id FROM accounts") == [(1,)]
    assert len(connector.close_calls) == 1


def test_readonly_session_has_no_generic_execute_or_raw_public_attributes() -> None:
    session = _open_readonly(FakeConnector())
    assert not hasattr(session, "execute")
    for name in ("connection", "cursor", "driver", "connector"):
        assert not hasattr(session, name)


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO accounts (name) VALUES ('Ada')",
        "CREATE TABLE archive (id INT)",
        "EXEC dbo.refresh_accounts @scope = 1",
        "BEGIN TRAN; INSERT INTO accounts (name) VALUES ('Ada'); ROLLBACK",
    ],
)
def test_production_readonly_hazardous_operations_are_blocked_before_driver(
    sql: str,
) -> None:
    connector = FakeConnector()
    events = _events()
    session = _open_readonly(connector, events)
    with pytest.raises(db_guard.GuardBlockedError) as raised:
        session.fetch_one(sql)
    assert raised.value.reason in {"hazardous-on-readonly", "privileged-denied", "unknown-denied"}
    assert connector.fetch_one_calls == []
    event = _event_lines(events)[-1]
    assert event["outcome"] == "blocked"


def test_test_write_session_requires_test_readwrite_and_matching_identity() -> None:
    connector = FakeConnector(
        identity=FakeIdentity(ENGINE_MSSQL, "test-server", "app_test")
    )
    session = _open_test(connector)
    assert session.execute("INSERT INTO accounts (name) VALUES (?)", ("Ada",)) == 1
    assert len(connector.execute_calls) == 1


def test_test_write_session_can_fetch_only_through_read_path() -> None:
    connector = FakeConnector(
        identity=FakeIdentity(ENGINE_MSSQL, "test-server", "app_test")
    )
    session = _open_test(connector)
    assert session.fetch_one("SELECT id FROM accounts") == (1,)
    with pytest.raises(db_guard.GuardBlockedError):
        session.fetch_one("DELETE FROM accounts")
    assert len(connector.fetch_one_calls) == 1


def test_write_factory_rejects_production_readonly_profile_before_connector() -> None:
    connector = FakeConnector()
    events = _events()
    with pytest.raises(db_guard.GuardBlockedError) as raised:
        _open_test(connector, events, profile_name="mssql-prod-ro")
    assert raised.value.reason == "resolution-failure"
    assert connector.connect_calls == []
    event = _event_lines(events)[-1]
    assert event["operation_class"] is None
    assert event["outcome"] == "blocked"


@pytest.mark.parametrize(
    ("identity", "reason"),
    [
        (FakeIdentity(ENGINE_MSSQL, "wrong-server", "app"), "attestation-mismatch"),
        (FakeIdentity(ENGINE_MSSQL, "prod-server", "wrong-db"), "attestation-mismatch"),
        (FakeIdentity(ENGINE_POSTGRESQL, "prod-server", "app"), "attestation-mismatch"),
    ],
)
def test_attestation_mismatch_blocks_before_caller_sql(
    identity: FakeIdentity, reason: str
) -> None:
    connector = FakeConnector(identity=identity)
    with pytest.raises(db_guard.GuardBlockedError) as raised:
        _open_readonly(connector)
    assert raised.value.reason == reason
    assert connector.connect_calls == [SENTINEL_CONNECTION]
    assert connector.fetch_one_calls == []


@pytest.mark.parametrize(
    "identity",
    [
        object(),
        FakeIdentity(ENGINE_MSSQL, "", "app"),
        FakeIdentity(ENGINE_MSSQL, "prod-server", ""),
        FakeIdentity(ENGINE_MSSQL, "   ", "app"),
    ],
)
def test_malformed_attestation_is_probe_failure(identity: object) -> None:
    connector = FakeConnector(identity=identity)  # type: ignore[arg-type]
    with pytest.raises(db_guard.GuardBlockedError) as raised:
        _open_readonly(connector)
    assert raised.value.reason == "probe-failure"
    assert connector.fetch_one_calls == []


def test_probe_failure_blocks_and_does_not_run_caller_sql() -> None:
    connector = FakeConnector(probe_error=TimeoutError("SECRET-VALUE"))
    with pytest.raises(db_guard.GuardBlockedError) as raised:
        _open_readonly(connector)
    assert raised.value.reason == "probe-failure"
    assert connector.fetch_one_calls == []
    assert "SECRET-VALUE" not in str(raised.value)


def test_missing_expected_target_blocks_before_connect() -> None:
    metadata = dict(TARGETS)
    metadata["mssql-prod-ro"] = ExpectedTarget("", "app")
    connector = FakeConnector()
    with pytest.raises(db_guard.GuardBlockedError) as raised:
        _open_readonly(connector, metadata=metadata)
    assert raised.value.reason == "missing-target-metadata"
    assert connector.connect_calls == []


def test_full_registry_preflight_blocks_both_misconfigured_test_registry_and_env() -> None:
    metadata = dict(TARGETS)
    metadata["mssql-test-rw"] = metadata["mssql-prod-ro"]
    connector = FakeConnector(
        identity=FakeIdentity(ENGINE_MSSQL, "prod-server", "app")
    )
    with pytest.raises(db_guard.GuardBlockedError) as raised:
        _open_test(connector, metadata=metadata)
    assert raised.value.reason == "missing-target-metadata"
    assert connector.connect_calls == []


def test_target_registry_key_drift_is_preflight_failure() -> None:
    metadata = dict(TARGETS)
    del metadata["postgres-test-rw"]
    connector = FakeConnector()
    with pytest.raises(db_guard.GuardBlockedError) as raised:
        _open_readonly(connector, metadata=metadata)
    assert raised.value.reason == "missing-target-metadata"
    assert connector.connect_calls == []


@pytest.mark.parametrize(
    ("sql", "reason"),
    [
        ("GRANT SELECT ON accounts TO analyst", "privileged-denied"),
        ("SET NOCOUNT ON", "unknown-denied"),
        ("SELECT 1; SET NOCOUNT ON", "unknown-denied"),
        ("INSERT INTO accounts (name) VALUES ('Ada'); SET NOCOUNT ON", "unknown-denied"),
    ],
)
def test_privileged_and_unknown_operations_are_denied_even_on_attested_test_session(
    sql: str, reason: str
) -> None:
    connector = FakeConnector(
        identity=FakeIdentity(ENGINE_MSSQL, "test-server", "app_test")
    )
    events = _events()
    session = _open_test(connector, events)
    with pytest.raises(db_guard.GuardBlockedError) as raised:
        session.execute(sql)
    assert raised.value.reason == reason
    assert connector.execute_calls == []
    event = _event_lines(events)[-1]
    assert event["outcome"] == "blocked"


def test_classifier_failure_is_a_block_and_driver_never_sees_sql(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connector = FakeConnector(
        identity=FakeIdentity(ENGINE_MSSQL, "test-server", "app_test")
    )
    events = _events()

    def fail_classifier(_sql: str):
        raise RuntimeError(SENTINEL_PARAMETER)

    monkeypatch.setattr(db_guard, "classify_batch", fail_classifier)
    session = _open_test(connector, events)
    with pytest.raises(db_guard.GuardBlockedError) as raised:
        session.execute("INSERT INTO accounts VALUES (?)", (SENTINEL_PARAMETER,))
    assert raised.value.reason == "classifier-failure"
    assert connector.execute_calls == []
    assert SENTINEL_PARAMETER not in "\n".join(events)


def test_invalid_classifier_result_is_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connector = FakeConnector(
        identity=FakeIdentity(ENGINE_MSSQL, "test-server", "app_test")
    )
    events = _events()
    monkeypatch.setattr(
        db_guard,
        "classify_batch",
        lambda _sql: BatchClassification("not-a-class", "hash", "preview"),
    )
    session = _open_test(connector, events)
    with pytest.raises(db_guard.GuardBlockedError) as raised:
        session.execute("INSERT INTO accounts VALUES (1)")
    assert raised.value.reason == "classifier-failure"
    assert connector.execute_calls == []


def test_pre_audit_sink_failure_cancels_hazardous_execution() -> None:
    connector = FakeConnector(
        identity=FakeIdentity(ENGINE_MSSQL, "test-server", "app_test")
    )

    def fail_sink(_line: str) -> None:
        raise OSError("sink unavailable")

    with patch.object(db_guard, "_EXPECTED_TARGETS", TARGETS):
        with patch.dict(os.environ, ENVIRON, clear=True):
            session = db_guard.open_test_readwrite(
                "mssql-test-rw",
                tool_id="test-tool",
                connector_overrides={ENGINE_MSSQL: connector},
                audit_sink=fail_sink,
            )
    with pytest.raises(db_guard.GuardBlockedError) as raised:
        session.execute("INSERT INTO accounts VALUES (1)")
    assert raised.value.reason == "audit-failure"
    assert connector.execute_calls == []


def test_allowed_and_succeeded_audit_events_are_redacted_and_single_line() -> None:
    connector = FakeConnector(
        identity=FakeIdentity(ENGINE_MSSQL, "test-server", "app_test")
    )
    events = _events()
    session = _open_test(connector, events)
    session.execute(
        "INSERT INTO accounts (name) VALUES (?)",
        (SENTINEL_PARAMETER,),
    )
    assert len(events) == 2
    assert all("\n" not in line for line in events)
    parsed = _event_lines(events)
    assert [event["outcome"] for event in parsed] == ["allowed", "succeeded"]
    assert parsed[0]["operation_class"] == "mutation"
    assert parsed[0]["profile_id"] == "mssql-test-rw"
    assert parsed[0]["engine"] == ENGINE_MSSQL
    assert parsed[0]["environment"] == "test"
    assert parsed[0]["capability"] == "read-write"
    assert parsed[0]["attested_server_identity"] == "test-server"
    assert parsed[0]["attested_database_identity"] == "app_test"
    assert parsed[0]["sql_preview"] == "INSERT INTO accounts (name) VALUES (?)"
    assert isinstance(parsed[0]["statement_hash"], str)
    assert SENTINEL_CONNECTION not in "\n".join(events)
    assert SENTINEL_PARAMETER not in "\n".join(events)
    assert SENTINEL_ROW not in "\n".join(events)


def test_failed_execution_emits_failed_audit_without_sensitive_exception_text() -> None:
    connector = FakeConnector(
        identity=FakeIdentity(ENGINE_MSSQL, "test-server", "app_test"),
        execute_error=RuntimeError(SENTINEL_ROW),
    )
    events = _events()
    session = _open_test(connector, events)
    with pytest.raises(Exception):
        session.execute("INSERT INTO accounts VALUES (?)", (SENTINEL_PARAMETER,))
    assert [event["outcome"] for event in _event_lines(events)] == [
        "allowed",
        "failed",
    ]
    assert SENTINEL_ROW not in "\n".join(events)
    assert SENTINEL_PARAMETER not in "\n".join(events)


def test_open_test_failure_emits_an_audit_event_with_null_operation_class() -> None:
    connector = FakeConnector(
        identity=FakeIdentity(ENGINE_MSSQL, "wrong-server", "app_test")
    )
    events = _events()
    with pytest.raises(db_guard.GuardBlockedError):
        _open_test(connector, events)
    event = _event_lines(events)[-1]
    assert event["operation_class"] is None
    assert event["outcome"] == "blocked"
    assert event["reason"] == "attestation-mismatch"


def test_open_resolution_failure_is_audited_without_echoing_connection_value() -> None:
    connector = FakeConnector()
    events = _events()
    with pytest.raises(db_guard.GuardBlockedError) as raised:
        _open_test(connector, events, environ={})
    assert raised.value.reason == "resolution-failure"
    event = _event_lines(events)[-1]
    assert event["operation_class"] is None
    rendered = "\n".join(events) + str(raised.value)
    assert SENTINEL_CONNECTION not in rendered
    assert "SECRET-VALUE" not in rendered


def test_audit_events_use_default_stderr_sink_when_no_sink_is_given(
    capsys: pytest.CaptureFixture[str],
) -> None:
    connector = FakeConnector(
        identity=FakeIdentity(ENGINE_MSSQL, "test-server", "app_test")
    )
    with patch.object(db_guard, "_EXPECTED_TARGETS", TARGETS):
        with patch.dict(os.environ, ENVIRON, clear=True):
            session = db_guard.open_test_readwrite(
                "mssql-test-rw",
                tool_id="test-tool",
                connector_overrides={ENGINE_MSSQL: connector},
            )
    session.execute("INSERT INTO accounts VALUES (1)")
    assert len(capsys.readouterr().err.splitlines()) == 2


def test_guard_module_has_no_cli_env_bypass_or_public_connector_reexport() -> None:
    source = inspect.getsource(db_guard)
    assert "argparse" not in source
    assert "sys.argv" not in source
    assert "input(" not in source
    assert "os.environ" not in source
    assert "os.getenv" not in source
    assert not hasattr(db_guard, "MssqlConnector")
    assert not hasattr(db_guard, "PostgresqlConnector")
    assert not hasattr(db_guard, "ConnectorError")


def test_guard_does_not_accept_a_caller_raw_connection_string() -> None:
    with pytest.raises(TypeError):
        db_guard.open_test_readwrite(
            "mssql-test-rw",
            tool_id="test-tool",
            connection_value=SENTINEL_CONNECTION,
        )


def test_connector_receives_only_resolver_value_after_all_checks() -> None:
    connector = FakeConnector(
        identity=FakeIdentity(ENGINE_MSSQL, "test-server", "app_test")
    )
    _open_test(connector)
    assert connector.connect_calls == [SENTINEL_CONNECTION]


def test_public_factory_rejects_combined_metadata_and_environment_overrides() -> None:
    decoy_metadata = {
        "mssql-prod-ro": ExpectedTarget("approved-prod-server", "approved-prod-db"),
        "mssql-test-rw": ExpectedTarget("prod-server", "app"),
        "postgres-test-rw": ExpectedTarget("pg-server", "pg_app_test"),
    }
    connector = FakeConnector(
        identity=FakeIdentity(ENGINE_MSSQL, "prod-server", "app")
    )

    with pytest.raises(TypeError):
        db_guard.open_test_readwrite(
            "mssql-test-rw",
            tool_id="test-tool",
            environ={"MSSQL_TEST_RW_CONN": SENTINEL_CONNECTION},
            connector_overrides={ENGINE_MSSQL: connector},
            metadata=decoy_metadata,
        )
