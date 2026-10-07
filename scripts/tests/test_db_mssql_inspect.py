"""Public-seam tests for the Issue #18 MSSQL read-only inspector.

The real guard and the real SQL classifier run on every registry query;
only the guard's connector and expected-target registry are replaced
(same seam as test_db_guard.py). No real database is contacted.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
from contextlib import ExitStack
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import patch

import pytest

import scripts.db.db_guard as db_guard
import scripts.db.mssql_inspect as mi
from scripts.db.connection_profiles import ENGINE_MSSQL
from scripts.db.sql_classification import (
    _DANGEROUS_VERBS,
    _UNKNOWN_STARTS,
    _tokenize,
    classify_batch,
)
from scripts.db.target_metadata import ExpectedTarget
from scripts.validate_scaffold import BANNED_DRIVER_ROOTS, ROOT


SENTINEL_CONNECTION = "mssql://svc:SECRET-VALUE@db.example/app"
SENTINEL_OUTPUT_SECRET = "PW-SENTINEL-9"

TARGETS = {
    "mssql-prod-ro": ExpectedTarget("prod-server", "app"),
    "mssql-test-rw": ExpectedTarget("test-server", "app_test"),
    "postgres-test-rw": ExpectedTarget("pg-server:5432", "pg_app_test"),
}
ENVIRON = {"MSSQL_PROD_RO_CONN": SENTINEL_CONNECTION}

DEFINITION_TEXT = "CREATE PROCEDURE dbo.usp_get_customer AS SELECT 1;"
TRIGGER_TEXT = (
    "CREATE TRIGGER dbo.TR_customer_audit ON dbo.customer AFTER UPDATE"
    " AS SELECT 1;"
)
JOB_COMMAND = "EXEC dbo.load_nightly"

SQL_TO_NAME = {spec.sql: spec.name for spec in mi.QUERY_REGISTRY}


def full_rows() -> dict[str, list[tuple]]:
    """Rows shaped exactly like the registry SELECT column order."""
    return {
        "schemas": [(1, "dbo"), (2, "sales")],
        "tables": [(101, "dbo", "customer", "U", "USER_TABLE", 0)],
        "columns": [
            (
                101, 1, "customer_id", "int", 4, 10, 0,
                0, 1, 0, None, None, None, "1000", "1",
            )
        ],
        "key_constraints": [
            (201, "PK_customer", "PRIMARY KEY", 0, "dbo", "customer", 1, 1, "customer_id")
        ],
        "foreign_keys": [
            (
                301, "FK_order_customer", 0, 0, "NO_ACTION", "NO_ACTION",
                "dbo", "sales_order", "customer_id", 1,
                "dbo", "customer", "customer_id",
            )
        ],
        "check_constraints": [
            (401, "CK_order_qty", 0, 0, "([qty]>(0))", "dbo", "sales_order", "qty")
        ],
        "default_constraints": [
            (501, "DF_order_qty", 0, "((0))", "dbo", "sales_order", "qty")
        ],
        "indexes": [
            (
                101, 2, "IX_customer_name", "NONCLUSTERED", 0, 0, 0, 0, None,
                "dbo", "customer", 1, "customer_name", 0,
            )
        ],
        "modules": [
            (
                601, "dbo", "usp_get_customer", "P", "SQL_STORED_PROCEDURE",
                "2020-01-01T00:00:00", "2021-06-01T00:00:00",
                0, 0, 1, DEFINITION_TEXT,
            )
        ],
        "triggers": [
            (701, "dbo", "TR_customer_audit", "SQL_TRIGGER", 0, 0, 0, "UPDATE", 0, TRIGGER_TEXT)
        ],
        "jobs": [
            (
                "8F3A-UUID", "Nightly load", 1, 1, "load", "TSQL", "app",
                1, 2, 1, 1, 1, "000000", 20260107, 30000, 7, "Weekly",
            )
        ],
        "job_step_commands": [("Nightly load", 1, "load", JOB_COMMAND)],
    }


ONE_ROWS: dict[str, tuple] = {
    "db_name": ("app",),
    "server_properties": ("15.0.2000.5", "RTM", "Developer Edition (64-bit)", 3),
    "database_properties": ("app", 150, "SQL_Latin1_General_CP1_CI_AS"),
    "principal": ("DOMAIN\\ro_inspector",),
    "database_visibility": (1,),
    "agent_visibility": (1,),
}


@dataclass
class ScriptedConnector:
    """Fake connector keyed by closed-registry query name. Any SQL text
    outside the registry fails the test immediately."""

    engine: str = ENGINE_MSSQL
    identity: object = field(
        default_factory=lambda: _Identity(ENGINE_MSSQL, "prod-server", "app")
    )
    rows_by_query: dict[str, list[tuple]] = field(default_factory=full_rows)
    one_rows_by_query: dict[str, tuple] = field(
        default_factory=lambda: dict(ONE_ROWS)
    )
    failing_queries: frozenset[str] = frozenset()
    fetch_one_calls: list[tuple[str, str, object]] = field(default_factory=list)
    fetch_all_calls: list[tuple[str, str, object]] = field(default_factory=list)
    connect_calls: list[str] = field(default_factory=list)
    probe_calls: list[object] = field(default_factory=list)
    close_calls: list[object] = field(default_factory=list)

    def connect(self, connection_value: str, **_kwargs: object) -> object:
        self.connect_calls.append(connection_value)
        return object()

    def identity_probe(self, connection: object) -> "_Identity":
        self.probe_calls.append(connection)
        return self.identity

    def fetch_one(self, connection: object, sql: str, params: object = None):
        name = self._name(sql)
        self.fetch_one_calls.append((name, sql, params))
        if name in self.failing_queries:
            raise RuntimeError("scripted failure")
        row = self.one_rows_by_query.get(name)
        if row is None:
            raise AssertionError(f"no scripted fetch_one row for '{name}'")
        return row

    def fetch_all(self, connection: object, sql: str, params: object = None):
        name = self._name(sql)
        self.fetch_all_calls.append((name, sql, params))
        if name in self.failing_queries:
            raise RuntimeError("scripted failure")
        return list(self.rows_by_query.get(name, []))

    def close(self, connection: object) -> None:
        self.close_calls.append(connection)

    @staticmethod
    def _name(sql: str) -> str:
        name = SQL_TO_NAME.get(sql)
        assert name is not None, "query text is outside the closed registry"
        return name


@dataclass(frozen=True)
class _Identity:
    engine: str
    server_identity: str
    database_identity: str


def run_tool(
    argv: list[str],
    connector: ScriptedConnector | None = None,
    *,
    targets: object = TARGETS,
    environ: dict[str, str] | None = None,
) -> tuple[int, ScriptedConnector]:
    connector = connector if connector is not None else ScriptedConnector()
    with ExitStack() as stack:
        if targets is not None:
            stack.enter_context(
                patch.object(db_guard, "_EXPECTED_TARGETS", targets)
            )
        stack.enter_context(
            patch.object(db_guard, "_select_connector", return_value=connector)
        )
        stack.enter_context(
            patch.dict(
                os.environ,
                ENVIRON if environ is None else environ,
                clear=True,
            )
        )
        code = mi.main(list(argv))
    return code, connector


def base_argv(tmp_path: Path, *extra: str) -> list[str]:
    return ["snapshot", "--output-dir", str(tmp_path / "captures"), *extra]


def only_capture_dir(tmp_path: Path) -> Path:
    root = tmp_path / "captures"
    assert root.is_dir()
    dirs = [entry for entry in root.iterdir() if entry.is_dir()]
    assert len(dirs) == 1
    return dirs[0]


def load_snapshot(tmp_path: Path) -> tuple[dict, Path]:
    capture_dir = only_capture_dir(tmp_path)
    snapshot = json.loads(
        (capture_dir / "snapshot.json").read_text(encoding="utf-8")
    )
    return snapshot, capture_dir


def executed_names(connector: ScriptedConnector) -> set[str]:
    return {
        name
        for name, _sql, _params in (*connector.fetch_one_calls, *connector.fetch_all_calls)
    }


# ---------------------------------------------------------------------------
# 1. Golden snapshot: JSON+Markdown bytes are deterministic
# ---------------------------------------------------------------------------


def test_full_snapshot_matches_golden_and_is_deterministic(tmp_path: Path) -> None:
    code, _connector = run_tool(
        base_argv(
            tmp_path,
            "--include-jobs",
            "--include-job-step-text",
            "--format",
            "both",
        )
    )
    assert code == 0
    snapshot, capture_dir = load_snapshot(tmp_path)

    definition_sha = hashlib.sha256(DEFINITION_TEXT.encode("utf-8")).hexdigest()
    trigger_sha = hashlib.sha256(TRIGGER_TEXT.encode("utf-8")).hexdigest()
    assert snapshot["capabilities"] == {
        "database_catalog": "COMPLETE",
        "module_definitions": "COMPLETE",
        "agent_jobs": "COMPLETE",
        "agent_job_step_text": "COMPLETE",
    }
    assert snapshot["warnings"] == []
    assert snapshot["scope"] == {
        "schemas": [],
        "objects": [],
        "include_jobs": True,
        "include_job_step_text": True,
    }
    assert snapshot["inventory"] == {
        "schemas": [
            {"schema_id": 1, "name": "dbo"},
            {"schema_id": 2, "name": "sales"},
        ],
        "tables": [
            {
                "object_id": 101,
                "schema_name": "dbo",
                "table_name": "customer",
                "type": "U",
                "type_desc": "USER_TABLE",
                "is_ms_shipped": False,
            }
        ],
        "columns": [
            {
                "object_id": 101,
                "column_id": 1,
                "name": "customer_id",
                "type_name": "int",
                "max_length": 4,
                "precision": 10,
                "scale": 0,
                "is_nullable": False,
                "is_identity": True,
                "is_computed": False,
                "computed_is_persisted": False,
                "collation_name": None,
                "identity_seed": "1000",
                "identity_increment": "1",
            }
        ],
        "integrity": {
            "key_constraints": [
                {
                    "object_id": 201,
                    "constraint_name": "PK_customer",
                    "constraint_kind": "PRIMARY KEY",
                    "is_system_named": False,
                    "schema_name": "dbo",
                    "table_name": "customer",
                    "index_id": 1,
                    "columns": [{"name": "customer_id", "ordinal": 1}],
                }
            ],
            "foreign_keys": [
                {
                    "object_id": 301,
                    "constraint_name": "FK_order_customer",
                    "is_disabled": False,
                    "is_not_trusted": False,
                    "update_action": "NO_ACTION",
                    "delete_action": "NO_ACTION",
                    "parent_schema": "dbo",
                    "parent_table": "sales_order",
                    "referenced_schema": "dbo",
                    "referenced_table": "customer",
                    "column_pairs": [
                        {
                            "parent_column": "customer_id",
                            "referenced_column": "customer_id",
                            "ordinal": 1,
                        }
                    ],
                }
            ],
            "check_constraints": [
                {
                    "object_id": 401,
                    "constraint_name": "CK_order_qty",
                    "is_disabled": False,
                    "is_not_trusted": False,
                    "definition_status": "AVAILABLE",
                    "definition_reason": None,
                    "definition_sha256": hashlib.sha256(
                        "([qty]>(0))".encode("utf-8")
                    ).hexdigest(),
                    "definition": "([qty]>(0))",
                    "schema_name": "dbo",
                    "table_name": "sales_order",
                    "column_name": "qty",
                }
            ],
            "default_constraints": [
                {
                    "object_id": 501,
                    "constraint_name": "DF_order_qty",
                    "is_system_named": False,
                    "definition_status": "AVAILABLE",
                    "definition_reason": None,
                    "definition_sha256": hashlib.sha256(
                        "((0))".encode("utf-8")
                    ).hexdigest(),
                    "definition": "((0))",
                    "schema_name": "dbo",
                    "table_name": "sales_order",
                    "column_name": "qty",
                }
            ],
            "indexes": [
                {
                    "object_id": 101,
                    "index_id": 2,
                    "index_name": "IX_customer_name",
                    "type_desc": "NONCLUSTERED",
                    "is_unique": False,
                    "is_primary_key": False,
                    "is_unique_constraint": False,
                    "has_filter": False,
                    "schema_name": "dbo",
                    "table_name": "customer",
                    "columns": [
                        {"name": "customer_name", "ordinal": 1, "is_included": False}
                    ],
                }
            ],
        },
        "modules": [
            {
                "object_id": 601,
                "schema_name": "dbo",
                "object_name": "usp_get_customer",
                "object_type": "P",
                "object_type_desc": "SQL_STORED_PROCEDURE",
                "created": "2020-01-01T00:00:00",
                "modified": "2021-06-01T00:00:00",
                "is_encrypted": False,
                "is_recompiled": False,
                "execute_as_principal_id": 1,
                "definition_status": "AVAILABLE",
                "definition_reason": None,
                "definition_sha256": definition_sha,
                "definition": DEFINITION_TEXT,
            }
        ],
        "triggers": [
            {
                "object_id": 701,
                "schema_name": "dbo",
                "object_name": "TR_customer_audit",
                "object_type_desc": "SQL_TRIGGER",
                "is_disabled": False,
                "is_instead_of_trigger": False,
                "is_not_for_replication": False,
                "events": ["UPDATE"],
                "is_encrypted": False,
                "definition_status": "AVAILABLE",
                "definition_reason": None,
                "definition_sha256": trigger_sha,
                "definition": TRIGGER_TEXT,
            }
        ],
        "agent_jobs": [
            {
                "job_id": "8F3A-UUID",
                "job_name": "Nightly load",
                "enabled": True,
                "step_id": 1,
                "step_name": "load",
                "subsystem": "TSQL",
                "database_name": "app",
                "on_success_action": 1,
                "on_failure_action": 2,
                "schedule_enabled": True,
                "schedule_freq_type": 1,
                "schedule_freq_interval": 1,
                "schedule_active_start_time": "000000",
                "next_run_date": 20260107,
                "next_run_time": 30000,
                "schedule_id": 7,
                "schedule_name": "Weekly",
                "command": JOB_COMMAND,
            }
        ],
    }

    # Deterministic serialization: re-rendering is byte-identical.
    json_bytes = (capture_dir / "snapshot.json").read_text(encoding="utf-8")
    markdown_bytes = (capture_dir / "snapshot.md").read_text(encoding="utf-8")
    assert mi.dump_json(snapshot) == json_bytes
    assert mi.render_markdown(snapshot) == markdown_bytes
    assert mi.dump_json(snapshot) == mi.dump_json(snapshot)
    assert mi.render_markdown(snapshot) == mi.render_markdown(snapshot)
    assert f"capture_id: `{snapshot['capture']['capture_id']}`" in markdown_bytes
    assert "| database_catalog | COMPLETE |" in markdown_bytes


# ---------------------------------------------------------------------------
# 2. Registry allowlist: every query is classified read
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("spec", mi.QUERY_REGISTRY, ids=lambda spec: spec.name)
def test_registry_query_is_read_closed_and_ordered(spec: object) -> None:
    sql = spec.sql  # type: ignore[attr-defined]
    assert sql.count("?") == len(spec.param_roles)  # type: ignore[attr-defined]
    assert "ORDER BY" in sql  # type: ignore[attr-defined]
    tokens, _malformed = _tokenize(sql)
    words = {token.value.upper() for token in tokens if token.kind == "word"}
    assert "INTO" not in words
    assert not words & _DANGEROUS_VERBS
    assert not words & _UNKNOWN_STARTS
    assert classify_batch(sql).operation_class == "read"


# ---------------------------------------------------------------------------
# 3. Closed set in practice: log subset, no --sql, no driver symbols
# ---------------------------------------------------------------------------


def test_query_log_stays_inside_registry_and_no_sql_flag(tmp_path: Path) -> None:
    connector = ScriptedConnector()
    code, connector = run_tool(
        base_argv(tmp_path, "--include-jobs", "--include-job-step-text"),
        connector,
    )
    assert code == 0
    executed_sql = [sql for _name, sql, _params in connector.fetch_all_calls]
    executed_sql += [sql for _name, sql, _params in connector.fetch_one_calls]
    assert executed_sql, "expected at least one registry query"
    assert set(executed_sql) <= set(mi.REGISTRY_SQL_TEXTS)

    tree = ast.parse(Path(mi.__file__).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert not any(
        name.startswith("scripts.db.connectors") or name.startswith("db.connectors")
        for name in imported
    )
    assert imported & set(BANNED_DRIVER_ROOTS) == set()

    connector = ScriptedConnector()
    with pytest.raises(SystemExit) as excinfo:
        mi.main(["snapshot", "--sql", "SELECT 1", "--output-dir", str(tmp_path)])
    assert excinfo.value.code == 1
    assert connector.connect_calls == []


# ---------------------------------------------------------------------------
# 4. Profile contract
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("profile", ["mssql-test-rw", "postgres-test-rw", "no-such"])
def test_only_mssql_prod_ro_profile_accepted(
    tmp_path: Path, profile: str
) -> None:
    connector = ScriptedConnector()
    with pytest.raises(SystemExit) as excinfo:
        run_tool(base_argv(tmp_path, "--profile", profile), connector)
    assert excinfo.value.code == 1
    assert connector.connect_calls == []


# ---------------------------------------------------------------------------
# 5. Wrong-database guard
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("expect_database", "failing", "expected_code"),
    [
        ("otherdb", frozenset(), 2),
        ("APP", frozenset(), 2),
        ("app", frozenset({"db_name"}), 2),
    ],
)
def test_expect_database_mismatch_aborts_before_inventory(
    tmp_path: Path,
    expect_database: str,
    failing: frozenset[str],
    expected_code: int,
) -> None:
    connector = ScriptedConnector(failing_queries=failing)
    code, connector = run_tool(
        base_argv(tmp_path, "--expect-database", expect_database),
        connector,
    )
    assert code == expected_code
    if expected_code == 2:
        assert (tmp_path / "captures").exists() is False
        one_names = {name for name, _sql, _params in connector.fetch_one_calls}
        assert one_names <= {"db_name"}
        assert connector.fetch_all_calls == []
    else:
        _snapshot, _capture_dir = load_snapshot(tmp_path)


# ---------------------------------------------------------------------------
# 6. Unavailable definitions are explicit, never absence
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("encrypted", "expected_reason"),
    [(0, "UNKNOWN"), (1, "ENCRYPTED")],
)
def test_null_definition_is_unavailable_and_partial(
    tmp_path: Path, encrypted: int, expected_reason: str
) -> None:
    rows = full_rows()
    rows["modules"] = [
        (
            601, "dbo", "usp_get_customer", "P", "SQL_STORED_PROCEDURE",
            "2020-01-01T00:00:00", "2021-06-01T00:00:00",
            encrypted, 0, None, None,
        )
    ]
    code, _connector = run_tool(base_argv(tmp_path), ScriptedConnector(rows_by_query=rows))
    assert code == 0
    snapshot, _capture_dir = load_snapshot(tmp_path)
    record = snapshot["inventory"]["modules"][0]
    assert record["definition_status"] == "UNAVAILABLE"
    assert record["definition_reason"] == expected_reason
    assert "definition_sha256" not in record
    assert "definition" not in record
    assert snapshot["capabilities"]["module_definitions"] == "PARTIAL"
    assert snapshot["capabilities"]["database_catalog"] == "COMPLETE"
    json_text = json.dumps(snapshot)
    assert "ABSENT" not in json_text
    assert "OMITTED_BY_POLICY" not in json_text


# ---------------------------------------------------------------------------
# 7. msdb failure blocks jobs without invalidating database objects
# ---------------------------------------------------------------------------


def test_msdb_failure_blocks_jobs_only(tmp_path: Path) -> None:
    connector = ScriptedConnector(failing_queries=frozenset({"jobs"}))
    code, _connector = run_tool(base_argv(tmp_path, "--include-jobs"), connector)
    assert code == 0
    snapshot, _capture_dir = load_snapshot(tmp_path)
    capabilities = snapshot["capabilities"]
    assert capabilities["agent_jobs"] == "BLOCKED"
    assert capabilities["agent_job_step_text"] == "NOT_REQUESTED"
    assert capabilities["database_catalog"] == "COMPLETE"
    assert capabilities["module_definitions"] == "COMPLETE"
    assert snapshot["inventory"]["agent_jobs"] == []
    assert any(
        warning.startswith("inventory query 'jobs' failed")
        for warning in snapshot["warnings"]
    )


# ---------------------------------------------------------------------------
# 8. Job-step text is opt-in
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("flags", "expected_jobs", "expected_step_text", "expect_command"),
    [
        ([], "NOT_REQUESTED", "NOT_REQUESTED", None),
        (["--include-jobs"], "COMPLETE", "NOT_REQUESTED", False),
        (
            ["--include-jobs", "--include-job-step-text"],
            "COMPLETE",
            "COMPLETE",
            True,
        ),
    ],
)
def test_job_step_text_is_opt_in(
    tmp_path: Path,
    flags: list[str],
    expected_jobs: str,
    expected_step_text: str,
    expect_command: bool | None,
) -> None:
    code, connector = run_tool(base_argv(tmp_path, *flags))
    assert code == 0
    snapshot, _capture_dir = load_snapshot(tmp_path)
    capabilities = snapshot["capabilities"]
    assert capabilities["agent_jobs"] == expected_jobs
    assert capabilities["agent_job_step_text"] == expected_step_text
    executed = executed_names(connector)
    jobs_records = snapshot["inventory"]["agent_jobs"]
    if expected_jobs == "NOT_REQUESTED":
        assert "jobs" not in executed
        assert "agent_visibility" not in executed
        assert all(
            "msdb" not in sql.lower()
            for _name, sql, _params in (*connector.fetch_one_calls, *connector.fetch_all_calls)
        )
        assert jobs_records == []
    else:
        assert "jobs" in executed
    if expected_step_text == "NOT_REQUESTED":
        assert "job_step_commands" not in executed
        for record in jobs_records:
            assert "command" not in record
    else:
        assert "job_step_commands" in executed
        assert jobs_records[0]["command"] == JOB_COMMAND


def test_job_step_text_without_jobs_is_a_usage_error(tmp_path: Path) -> None:
    connector = ScriptedConnector()
    with pytest.raises(SystemExit) as excinfo:
        run_tool(base_argv(tmp_path, "--include-job-step-text"), connector)
    assert excinfo.value.code == 1
    assert connector.connect_calls == []


# ---------------------------------------------------------------------------
# 14. Visibility preconditions gate COMPLETE (review F1)
# ---------------------------------------------------------------------------


def test_visibility_preconditions_gate_complete(tmp_path: Path) -> None:
    one_rows = dict(ONE_ROWS)
    one_rows["database_visibility"] = (0,)
    code, _connector = run_tool(
        base_argv(tmp_path, "--include-jobs", "--include-job-step-text"),
        ScriptedConnector(one_rows_by_query=one_rows),
    )
    assert code == 0
    snapshot, _capture_dir = load_snapshot(tmp_path)
    capabilities = snapshot["capabilities"]
    assert capabilities["database_catalog"] == "PARTIAL"
    assert capabilities["module_definitions"] == "PARTIAL"
    assert capabilities["agent_jobs"] == "COMPLETE"
    assert capabilities["agent_job_step_text"] == "COMPLETE"
    assert snapshot["capture"]["visibility"]["database_view_definition"] is False
    assert any(
        warning.startswith("database visibility precondition unproven")
        for warning in snapshot["warnings"]
    )


def test_failed_visibility_probe_is_unproven_and_partial(tmp_path: Path) -> None:
    connector = ScriptedConnector(failing_queries=frozenset({"agent_visibility"}))
    code, _connector = run_tool(
        base_argv(tmp_path, "--include-jobs"), connector
    )
    assert code == 0
    snapshot, _capture_dir = load_snapshot(tmp_path)
    assert snapshot["capture"]["visibility"]["agent_jobs"] is None
    assert snapshot["capabilities"]["agent_jobs"] == "PARTIAL"
    assert snapshot["capabilities"]["database_catalog"] == "COMPLETE"
    assert any(
        "agent job visibility precondition unproven" in warning
        for warning in snapshot["warnings"]
    )
    assert any(
        "capture query 'agent_visibility' failed" in warning
        for warning in snapshot["warnings"]
    )


def test_blocked_jobs_do_not_add_visibility_warning(tmp_path: Path) -> None:
    one_rows = dict(ONE_ROWS)
    one_rows["agent_visibility"] = (0,)
    connector = ScriptedConnector(
        failing_queries=frozenset({"jobs"}),
        one_rows_by_query=one_rows,
    )
    code, _connector = run_tool(base_argv(tmp_path, "--include-jobs"), connector)
    assert code == 0
    snapshot, _capture_dir = load_snapshot(tmp_path)
    assert snapshot["capabilities"]["agent_jobs"] == "BLOCKED"
    assert not any(
        "visibility precondition unproven" in warning
        for warning in snapshot["warnings"]
    )


# ---------------------------------------------------------------------------
# 15. Documented catalog columns only (review F2)
# ---------------------------------------------------------------------------


def test_module_queries_use_documented_catalog_columns() -> None:
    modules_sql = mi.QUERY_BY_NAME["modules"].sql
    triggers_sql = mi.QUERY_BY_NAME["triggers"].sql
    assert "m.is_encrypted" not in modules_sql
    assert "execute_as_desc" not in modules_sql
    assert "m.execute_as_principal_id" in modules_sql
    assert "OBJECTPROPERTY(" in modules_sql
    assert "m.is_encrypted" not in triggers_sql
    assert "OBJECTPROPERTY(" in triggers_sql


def test_ddl_trigger_encryption_evidence_is_null_and_unknown(tmp_path: Path) -> None:
    rows = full_rows()
    rows["triggers"] = rows["triggers"] + [
        (
            702, None, "TR_ddl_audit", "SQL_TRIGGER", 0, 0, 0,
            "CREATE_TABLE", None, None,
        ),
    ]
    code, _connector = run_tool(base_argv(tmp_path), ScriptedConnector(rows_by_query=rows))
    assert code == 0
    snapshot, _capture_dir = load_snapshot(tmp_path)
    record = next(
        r for r in snapshot["inventory"]["triggers"] if r["object_id"] == 702
    )
    assert record["schema_name"] is None
    assert record["is_encrypted"] is None
    assert record["definition_status"] == "UNAVAILABLE"
    assert record["definition_reason"] == "UNKNOWN"
    dml = next(
        r for r in snapshot["inventory"]["triggers"] if r["object_id"] == 701
    )
    assert dml["is_encrypted"] is False


# ---------------------------------------------------------------------------
# 16. Hidden catalog expressions are unavailable evidence (review F3)
# ---------------------------------------------------------------------------


def test_hidden_catalog_expressions_are_unavailable_and_partial(tmp_path: Path) -> None:
    rows = full_rows()
    rows["columns"] = rows["columns"] + [
        (
            101, 2, "total_qty", "int", 4, 10, 0, 1, 0, 1,
            "([qty]*[unit_price])", 1, None, None, None,
        ),
        (
            101, 3, "hidden_total", "int", 4, 10, 0, 1, 0, 1,
            None, None, None, None, None,
        ),
    ]
    rows["indexes"] = rows["indexes"] + [
        (
            101, 3, "IX_filtered", "NONCLUSTERED", 0, 0, 0, 1, None,
            "dbo", "customer", 1, "customer_name", 0,
        )
    ]
    rows["check_constraints"] = [
        (401, "CK_hidden", 0, 0, None, "dbo", "sales_order", "qty")
    ]
    rows["default_constraints"] = [
        (501, "DF_hidden", 0, None, "dbo", "sales_order", "qty")
    ]
    code, _connector = run_tool(base_argv(tmp_path), ScriptedConnector(rows_by_query=rows))
    assert code == 0
    snapshot, _capture_dir = load_snapshot(tmp_path)
    columns = {record["name"]: record for record in snapshot["inventory"]["columns"]}
    visible = columns["total_qty"]
    assert visible["definition_status"] == "AVAILABLE"
    assert visible["definition"] == "([qty]*[unit_price])"
    assert visible["definition_sha256"] == hashlib.sha256(
        "([qty]*[unit_price])".encode("utf-8")
    ).hexdigest()
    hidden = columns["hidden_total"]
    assert hidden["definition_status"] == "UNAVAILABLE"
    assert hidden["definition_reason"] == "UNKNOWN"
    assert "definition" not in hidden
    assert "definition_sha256" not in hidden
    assert "definition_status" not in columns["customer_id"]
    indexes = snapshot["inventory"]["integrity"]["indexes"]
    assert indexes[0]["index_name"] == "IX_customer_name"
    assert "definition_status" not in indexes[0]
    assert indexes[1]["index_name"] == "IX_filtered"
    assert indexes[1]["has_filter"] is True
    assert indexes[1]["definition_status"] == "UNAVAILABLE"
    check = snapshot["inventory"]["integrity"]["check_constraints"][0]
    assert check["definition_status"] == "UNAVAILABLE"
    assert "definition" not in check
    default = snapshot["inventory"]["integrity"]["default_constraints"][0]
    assert default["definition_status"] == "UNAVAILABLE"
    assert snapshot["capabilities"]["database_catalog"] == "PARTIAL"
    assert snapshot["capabilities"]["module_definitions"] == "COMPLETE"
    assert any(
        "catalog expression(s) unavailable" in warning
        for warning in snapshot["warnings"]
    )


# ---------------------------------------------------------------------------
# 17. Usage errors never echo rejected values (review F4)
# ---------------------------------------------------------------------------


def test_usage_error_does_not_echo_rejected_value(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    connector = ScriptedConnector()
    secret_value = f"Server=prod;Uid=svc;PWD={SENTINEL_OUTPUT_SECRET}"
    for extra in (
        ["--profile", secret_value],
        ["--no-such-flag", secret_value],
    ):
        with pytest.raises(SystemExit) as excinfo:
            run_tool(base_argv(tmp_path, *extra), connector)
        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert SENTINEL_OUTPUT_SECRET not in captured.err
        assert SENTINEL_OUTPUT_SECRET not in captured.out
        assert captured.err.startswith("usage:")
    assert connector.connect_calls == []
    assert not (tmp_path / "captures").exists()


# ---------------------------------------------------------------------------
# 18. Job/schedule linkage is projected and distinguished (review F5)
# ---------------------------------------------------------------------------


def test_job_schedule_linkage_survives_dedupe(tmp_path: Path) -> None:
    rows = full_rows()
    step = (
        "8F3A-UUID", "Nightly load", 1, 1, "load", "TSQL", "app",
        1, 2, 1, 1, 1, "000000", 20260107, 30000,
    )
    rows["jobs"] = [step + (7, "Weekly"), step + (9, "Weekly")]
    code, _connector = run_tool(
        base_argv(tmp_path, "--include-jobs"),
        ScriptedConnector(rows_by_query=rows),
    )
    assert code == 0
    snapshot, _capture_dir = load_snapshot(tmp_path)
    job_records = snapshot["inventory"]["agent_jobs"]
    assert len(job_records) == 2
    assert [record["schedule_id"] for record in job_records] == [7, 9]
    assert all(record["schedule_name"] == "Weekly" for record in job_records)


# ---------------------------------------------------------------------------
# 19. Step text without its job is never COMPLETE (review F6)
# ---------------------------------------------------------------------------


def test_step_text_without_jobs_is_partial_without_orphans(tmp_path: Path) -> None:
    connector = ScriptedConnector(failing_queries=frozenset({"jobs"}))
    code, _connector = run_tool(
        base_argv(tmp_path, "--include-jobs", "--include-job-step-text"),
        connector,
    )
    assert code == 0
    snapshot, _capture_dir = load_snapshot(tmp_path)
    capabilities = snapshot["capabilities"]
    assert capabilities["agent_jobs"] == "BLOCKED"
    assert capabilities["agent_job_step_text"] == "PARTIAL"
    assert snapshot["inventory"]["agent_jobs"] == []
    assert JOB_COMMAND not in json.dumps(snapshot)
    assert any(
        "not linked to a job inventory" in warning
        for warning in snapshot["warnings"]
    )


def test_step_text_own_failure_stays_blocked(tmp_path: Path) -> None:
    connector = ScriptedConnector(
        failing_queries=frozenset({"jobs", "job_step_commands"})
    )
    code, _connector = run_tool(
        base_argv(tmp_path, "--include-jobs", "--include-job-step-text"),
        connector,
    )
    assert code == 0
    snapshot, _capture_dir = load_snapshot(tmp_path)
    assert snapshot["capabilities"]["agent_job_step_text"] == "BLOCKED"
    assert not any(
        "not linked to a job inventory" in warning
        for warning in snapshot["warnings"]
    )


# ---------------------------------------------------------------------------
# 9. One snapshot model feeds both renderings
# ---------------------------------------------------------------------------


def test_renderers_derive_from_one_snapshot_model(tmp_path: Path) -> None:
    code, _connector = run_tool(
        base_argv(tmp_path, "--include-jobs", "--include-job-step-text", "--format", "both")
    )
    assert code == 0
    snapshot, capture_dir = load_snapshot(tmp_path)
    json_text = (capture_dir / "snapshot.json").read_text(encoding="utf-8")
    markdown_text = (capture_dir / "snapshot.md").read_text(encoding="utf-8")
    assert json_text == mi.dump_json(snapshot)
    assert markdown_text == mi.render_markdown(snapshot)
    # Raw module text lives only in the canonical JSON capture.
    assert DEFINITION_TEXT in json_text
    assert DEFINITION_TEXT not in markdown_text
    assert snapshot["capture"]["capture_id"] in markdown_text
    assert "visibility limitation:" in markdown_text


# ---------------------------------------------------------------------------
# 10. Default output is Git-ignored; raw text stays in the capture
# ---------------------------------------------------------------------------


def test_default_output_is_gitignored_and_raw_stays_in_capture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    code, _connector = run_tool(["snapshot", "--format", "both"])
    assert code == 0
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".local/mssql-inspection/" in gitignore
    default_root = tmp_path / ".local" / "mssql-inspection"
    assert default_root.is_dir()
    dirs = [entry for entry in default_root.iterdir() if entry.is_dir()]
    assert len(dirs) == 1
    capture_dir = dirs[0]
    relative = capture_dir.relative_to(tmp_path)
    assert relative.parts[:2] == (".local", "mssql-inspection")
    json_text = (capture_dir / "snapshot.json").read_text(encoding="utf-8")
    markdown_text = (capture_dir / "snapshot.md").read_text(encoding="utf-8")
    assert DEFINITION_TEXT in json_text
    assert DEFINITION_TEXT not in markdown_text
    assert DEFINITION_TEXT not in capsys.readouterr().out


# ---------------------------------------------------------------------------
# 11. Secrets never reach outputs
# ---------------------------------------------------------------------------


def test_connection_secret_absent_from_all_outputs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    environ = {
        "MSSQL_PROD_RO_CONN": f"mssql://svc:{SENTINEL_OUTPUT_SECRET}@db.example/app"
    }
    connector = ScriptedConnector(failing_queries=frozenset({"jobs"}))
    code, connector = run_tool(
        base_argv(tmp_path, "--include-jobs", "--format", "both"),
        connector,
        environ=environ,
    )
    assert code == 0
    snapshot, capture_dir = load_snapshot(tmp_path)
    json_text = (capture_dir / "snapshot.json").read_text(encoding="utf-8")
    markdown_text = (capture_dir / "snapshot.md").read_text(encoding="utf-8")
    captured = capsys.readouterr()
    for surface in (captured.out, captured.err, json_text, markdown_text):
        assert SENTINEL_OUTPUT_SECRET not in surface
        assert "SECRET-VALUE" not in surface
    # Control: the sentinel really was the connection value in play.
    assert SENTINEL_OUTPUT_SECRET in connector.connect_calls[0]
    assert SENTINEL_OUTPUT_SECRET not in json.dumps(snapshot)


# ---------------------------------------------------------------------------
# 12. Capture context completeness (design L139-147)
# ---------------------------------------------------------------------------


def test_capture_context_is_complete(tmp_path: Path) -> None:
    code, _connector = run_tool(
        base_argv(tmp_path, "--include-jobs", "--expect-database", "app")
    )
    assert code == 0
    snapshot, _capture_dir = load_snapshot(tmp_path)
    capture = snapshot["capture"]
    assert set(capture) == {
        "capture_id",
        "captured_at_utc",
        "tool_id",
        "schema_version",
        "profile",
        "expect_database",
        "database_name",
        "server",
        "compatibility_level",
        "collation",
        "principal_name",
        "visibility",
        "requested_scope",
        "effective_scope",
    }
    assert capture["tool_id"] == "mssql-inspect"
    assert capture["schema_version"] == 1
    assert capture["profile"] == "mssql-prod-ro"
    assert capture["expect_database"] == "app"
    assert capture["database_name"] == "app"
    assert capture["compatibility_level"] == 150
    assert capture["collation"] == "SQL_Latin1_General_CP1_CI_AS"
    assert capture["server"] == {
        "product_version": "15.0.2000.5",
        "product_level": "RTM",
        "edition": "Developer Edition (64-bit)",
        "engine_edition": 3,
    }
    assert capture["principal_name"] == "DOMAIN\\ro_inspector"
    assert capture["visibility"] == {
        "database_view_definition": True,
        "agent_jobs": True,
        "limitation": (
            "Object-level DENY cannot be ruled out by the recorded"
            " visibility probes."
        ),
    }
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", capture["captured_at_utc"])
    assert re.fullmatch(r"\d{8}T\d{6}Z-[0-9a-f]{8}", capture["capture_id"])
    assert capture["requested_scope"] == {
        "schemas": [],
        "objects": [],
        "include_jobs": True,
        "include_job_step_text": False,
    }
    assert capture["effective_scope"] == [{"kind": "all"}]


# ---------------------------------------------------------------------------
# 13. Guard blocks fail closed with exit code 2 and no capture
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("targets", "expected_reason"),
    [
        (None, "missing-target-metadata"),
        (
            {**TARGETS, "mssql-prod-ro": ExpectedTarget("other-server", "app")},
            "attestation-mismatch",
        ),
    ],
)
def test_guard_blocks_exit_2_without_capture(
    tmp_path: Path,
    targets: object,
    expected_reason: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    code, _connector = run_tool(base_argv(tmp_path), targets=targets)
    assert code == 2
    assert expected_reason in capsys.readouterr().err
    assert not (tmp_path / "captures").exists()
