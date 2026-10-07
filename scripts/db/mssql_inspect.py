"""Issue #18 MSSQL read-only operational-database inspector.

Executes one closed registry of literal read-only catalog ``SELECT``
queries through ``scripts.db.db_guard.open_readonly`` and serializes a
single normalized snapshot: JSON is canonical, Markdown is rendered from
the same object.

Design: docs/issue-18-mssql-readonly-inspection.md.
Contracts consumed (not duplicated):
- docs/12-db-connection-secrets-contract.md (Issue #23 profile ``mssql-prod-ro``)
- docs/12-db-execution-safety-contract.md (Issue #20 guard/classifier)

Boundary rules enforced by construction:
- The guard is the only database path. This module imports no resolver,
  connector, or driver and never assembles SQL fragments from input.
- No ``--sql``, no ``EXEC``/``sp_helptext``; module text comes from
  ``sys.sql_modules``. Filters are ``?`` parameters only.
- Connection values never enter the snapshot, Markdown, warnings,
  stdout, or error text. Raw definitions and job-step commands exist
  only inside the local capture directory (not printed to stdout).
- Completeness is evidence: zero rows never imply absence. Final rule
  (user decision 2026-10-07, extended by review round W-18-FIX1):
  in-scope data partly retrieved = PARTIAL; the source wholly
  inaccessible = BLOCKED; flag absent = NOT_REQUESTED; COMPLETE only
  when every required query succeeded, nothing in scope is
  unavailable, and the category's visibility precondition is proven
  (capture.visibility). Unproven visibility keeps a successfully
  queried category PARTIAL.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

try:
    from scripts.db import db_guard
except ModuleNotFoundError:  # direct execution: python3 scripts/db/mssql_inspect.py
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.db import db_guard  # type: ignore[no-redef]


TOOL_ID = "mssql-inspect"
PROFILE_NAME = "mssql-prod-ro"
SCHEMA_VERSION = 1
DEFAULT_OUTPUT_ROOT = Path(".local") / "mssql-inspection"
SNAPSHOT_JSON_NAME = "snapshot.json"
SNAPSHOT_MARKDOWN_NAME = "snapshot.md"

CAPTURE_CATEGORY = "capture"

# Completeness/capability statuses (design output model).
CAPABILITY_DATABASE_CATALOG = "database_catalog"
CAPABILITY_MODULE_DEFINITIONS = "module_definitions"
CAPABILITY_AGENT_JOBS = "agent_jobs"
CAPABILITY_AGENT_JOB_STEP_TEXT = "agent_job_step_text"
CAPABILITY_ORDER = (
    CAPABILITY_DATABASE_CATALOG,
    CAPABILITY_MODULE_DEFINITIONS,
    CAPABILITY_AGENT_JOBS,
    CAPABILITY_AGENT_JOB_STEP_TEXT,
)

STATUS_COMPLETE = "COMPLETE"
STATUS_PARTIAL = "PARTIAL"
STATUS_BLOCKED = "BLOCKED"
STATUS_NOT_REQUESTED = "NOT_REQUESTED"

# Definition availability statuses. OMITTED_BY_POLICY and ERROR are
# reserved enum members of the design output model; nothing in V1
# produces them.
DEFINITION_AVAILABLE = "AVAILABLE"
DEFINITION_UNAVAILABLE = "UNAVAILABLE"
DEFINITION_OMITTED_BY_POLICY = "OMITTED_BY_POLICY"
DEFINITION_ERROR = "ERROR"

FLAG_INCLUDE_JOBS = "include_jobs"
FLAG_INCLUDE_JOB_STEP_TEXT = "include_job_step_text"

# Recorded visibility preconditions (design L224-228): fixed registry
# probes whose non-secret boolean/NULL results gate COMPLETE. The
# limitation string is a constant capture note, deliberately not a
# warning: object-level DENY is not resolvable by these probes.
VISIBILITY_DATABASE = "database_view_definition"
VISIBILITY_JOBS = "agent_jobs"
VISIBILITY_LIMITATION = (
    "Object-level DENY cannot be ruled out by the recorded visibility"
    " probes."
)
VISIBILITY_WARNINGS = {
    VISIBILITY_DATABASE: (
        "database visibility precondition unproven: VIEW DEFINITION on"
        " the current database was not proven for the capture principal"
    ),
    VISIBILITY_JOBS: (
        "agent job visibility precondition unproven: sysadmin or msdb"
        " SQLAgentReaderRole/SQLAgentOperatorRole membership was not"
        " proven for the capture principal"
    ),
}
CAPABILITY_VISIBILITY = {
    CAPABILITY_DATABASE_CATALOG: VISIBILITY_DATABASE,
    CAPABILITY_MODULE_DEFINITIONS: VISIBILITY_DATABASE,
    CAPABILITY_AGENT_JOBS: VISIBILITY_JOBS,
    CAPABILITY_AGENT_JOB_STEP_TEXT: VISIBILITY_JOBS,
}


@dataclass(frozen=True)
class QuerySpec:
    """One closed-registry query. ``sql`` is a literal; filters are ``?``
    parameters whose count must equal ``len(param_roles)``."""

    name: str
    category: str
    sql: str
    param_roles: tuple[str, ...] = ()
    mode: str = "all"  # "all" -> fetch_all, "one" -> fetch_one
    requires: str | None = None  # capability flag that must be requested


QUERY_REGISTRY: tuple[QuerySpec, ...] = (
    # --- capture context (design L139-147) ---
    QuerySpec(
        name="db_name",
        category=CAPTURE_CATEGORY,
        mode="one",
        sql="SELECT DB_NAME() AS [database_name] ORDER BY 1;",
    ),
    QuerySpec(
        name="server_properties",
        category=CAPTURE_CATEGORY,
        mode="one",
        sql=(
            "SELECT SERVERPROPERTY('ProductVersion') AS [product_version], "
            "SERVERPROPERTY('ProductLevel') AS [product_level], "
            "SERVERPROPERTY('Edition') AS [edition], "
            "SERVERPROPERTY('EngineEdition') AS [engine_edition] "
            "ORDER BY 1;"
        ),
    ),
    QuerySpec(
        name="database_properties",
        category=CAPTURE_CATEGORY,
        mode="one",
        sql=(
            "SELECT d.name AS [database_name], d.compatibility_level, "
            "d.collation_name "
            "FROM sys.databases AS d "
            "WHERE d.database_id = DB_ID() "
            "ORDER BY d.name;"
        ),
    ),
    QuerySpec(
        name="principal",
        category=CAPTURE_CATEGORY,
        mode="one",
        sql="SELECT SUSER_SNAME() AS [principal_name] ORDER BY 1;",
    ),
    # Visibility preconditions (design L224-228). A successful empty
    # inventory is not an absence claim unless these are proven. The
    # job probe needs affirmative evidence only: sysadmin membership,
    # or the current login's msdb user being in a role that sees all
    # jobs. A failed probe leaves visibility NULL (unproven).
    QuerySpec(
        name="database_visibility",
        category=CAPTURE_CATEGORY,
        mode="one",
        sql=(
            "SELECT HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE',"
            " 'VIEW DEFINITION') AS [view_definition] ORDER BY 1;"
        ),
    ),
    QuerySpec(
        name="agent_visibility",
        category=CAPTURE_CATEGORY,
        mode="one",
        sql=(
            "SELECT CASE WHEN IS_SRVROLEMEMBER('sysadmin') = 1 THEN 1 "
            "WHEN EXISTS ("
            "SELECT 1 "
            "FROM msdb.sys.database_principals AS mp "
            "JOIN msdb.sys.database_role_members AS drm "
            "ON drm.member_principal_id = mp.principal_id "
            "JOIN msdb.sys.database_principals AS rp "
            "ON rp.principal_id = drm.role_principal_id "
            "WHERE mp.sid = SUSER_SID() "
            "AND rp.name IN ('SQLAgentReaderRole', 'SQLAgentOperatorRole')"
            ") THEN 1 ELSE 0 END AS [sees_all_jobs] "
            "ORDER BY 1;"
        ),
    ),
    # --- schemas/tables/columns ---
    QuerySpec(
        name="schemas",
        category="tables",
        sql=(
            "SELECT s.schema_id, s.name AS [schema_name] "
            "FROM sys.schemas AS s "
            "WHERE (? IS NULL OR s.name = ?) "
            "ORDER BY s.name;"
        ),
        param_roles=("schema", "schema"),
    ),
    QuerySpec(
        name="tables",
        category="tables",
        sql=(
            "SELECT t.object_id, s.name AS [schema_name], "
            "t.name AS [table_name], t.[type], t.type_desc, t.is_ms_shipped "
            "FROM sys.tables AS t "
            "JOIN sys.schemas AS s ON s.schema_id = t.schema_id "
            "WHERE (? IS NULL OR s.name = ?) "
            "AND (? IS NULL OR t.object_id = OBJECT_ID(?)) "
            "ORDER BY s.name, t.name;"
        ),
        param_roles=("schema", "schema", "object", "object"),
    ),
    QuerySpec(
        name="columns",
        category="tables",
        sql=(
            "SELECT c.object_id, c.column_id, c.name AS [column_name], "
            "st.name AS [type_name], c.max_length, c.precision, c.scale, "
            "c.is_nullable, c.is_identity, c.is_computed, "
            "cc.definition AS [computed_definition], cc.is_persisted, "
            "c.collation_name, ic.seed_value, ic.increment_value "
            "FROM sys.columns AS c "
            "JOIN sys.types AS st ON st.user_type_id = c.user_type_id "
            "JOIN sys.tables AS t ON t.object_id = c.object_id "
            "JOIN sys.schemas AS s ON s.schema_id = t.schema_id "
            "LEFT JOIN sys.computed_columns AS cc "
            "ON cc.object_id = c.object_id AND cc.column_id = c.column_id "
            "LEFT JOIN sys.identity_columns AS ic "
            "ON ic.object_id = c.object_id AND ic.column_id = c.column_id "
            "WHERE (? IS NULL OR s.name = ?) "
            "AND (? IS NULL OR c.object_id = OBJECT_ID(?)) "
            "ORDER BY c.object_id, c.column_id;"
        ),
        param_roles=("schema", "schema", "object", "object"),
    ),
    # --- integrity and access structures ---
    QuerySpec(
        name="key_constraints",
        category="integrity",
        sql=(
            "SELECT kc.object_id, kc.name AS [constraint_name], "
            "kc.type_desc, kc.is_system_named, "
            "s.name AS [schema_name], t.name AS [table_name], "
            "i.index_id, ic.key_ordinal, c.name AS [column_name] "
            "FROM sys.key_constraints AS kc "
            "JOIN sys.tables AS t ON t.object_id = kc.parent_object_id "
            "JOIN sys.schemas AS s ON s.schema_id = t.schema_id "
            "JOIN sys.indexes AS i "
            "ON i.object_id = kc.parent_object_id "
            "AND i.index_id = kc.unique_index_id "
            "JOIN sys.index_columns AS ic "
            "ON ic.object_id = kc.parent_object_id "
            "AND ic.index_id = i.index_id "
            "JOIN sys.columns AS c "
            "ON c.object_id = ic.object_id AND c.column_id = ic.column_id "
            "WHERE (? IS NULL OR s.name = ?) "
            "AND (? IS NULL OR kc.parent_object_id = OBJECT_ID(?)) "
            "ORDER BY kc.object_id, ic.key_ordinal, c.name;"
        ),
        param_roles=("schema", "schema", "object", "object"),
    ),
    QuerySpec(
        name="foreign_keys",
        category="integrity",
        sql=(
            "SELECT fk.object_id, fk.name AS [constraint_name], "
            "fk.is_disabled, fk.is_not_trusted, "
            "fk.update_referential_action_desc, "
            "fk.delete_referential_action_desc, "
            "ps.name AS [parent_schema], pt.name AS [parent_table], "
            "pc.name AS [parent_column], fkc.constraint_column_id, "
            "rs.name AS [referenced_schema], rt.name AS [referenced_table], "
            "rc.name AS [referenced_column] "
            "FROM sys.foreign_keys AS fk "
            "JOIN sys.foreign_key_columns AS fkc "
            "ON fkc.constraint_object_id = fk.object_id "
            "JOIN sys.tables AS pt ON pt.object_id = fk.parent_object_id "
            "JOIN sys.schemas AS ps ON ps.schema_id = pt.schema_id "
            "JOIN sys.columns AS pc "
            "ON pc.object_id = fkc.parent_object_id "
            "AND pc.column_id = fkc.parent_column_id "
            "JOIN sys.tables AS rt ON rt.object_id = fk.referenced_object_id "
            "JOIN sys.schemas AS rs ON rs.schema_id = rt.schema_id "
            "JOIN sys.columns AS rc "
            "ON rc.object_id = fkc.referenced_object_id "
            "AND rc.column_id = fkc.referenced_column_id "
            "WHERE (? IS NULL OR ps.name = ?) "
            "AND (? IS NULL OR fk.parent_object_id = OBJECT_ID(?)) "
            "ORDER BY fk.object_id, fkc.constraint_column_id;"
        ),
        param_roles=("schema", "schema", "object", "object"),
    ),
    QuerySpec(
        name="check_constraints",
        category="integrity",
        sql=(
            "SELECT cc.object_id, cc.name AS [constraint_name], "
            "cc.is_disabled, cc.is_not_trusted, cc.definition, "
            "s.name AS [schema_name], t.name AS [table_name], "
            "c.name AS [column_name] "
            "FROM sys.check_constraints AS cc "
            "JOIN sys.tables AS t ON t.object_id = cc.parent_object_id "
            "JOIN sys.schemas AS s ON s.schema_id = t.schema_id "
            "LEFT JOIN sys.columns AS c "
            "ON c.object_id = cc.parent_object_id "
            "AND c.column_id = cc.parent_column_id "
            "WHERE (? IS NULL OR s.name = ?) "
            "AND (? IS NULL OR cc.parent_object_id = OBJECT_ID(?)) "
            "ORDER BY cc.object_id, cc.name;"
        ),
        param_roles=("schema", "schema", "object", "object"),
    ),
    QuerySpec(
        name="default_constraints",
        category="integrity",
        sql=(
            "SELECT dc.object_id, dc.name AS [constraint_name], "
            "dc.is_system_named, dc.definition, "
            "s.name AS [schema_name], t.name AS [table_name], "
            "c.name AS [column_name] "
            "FROM sys.default_constraints AS dc "
            "JOIN sys.tables AS t ON t.object_id = dc.parent_object_id "
            "JOIN sys.schemas AS s ON s.schema_id = t.schema_id "
            "JOIN sys.columns AS c "
            "ON c.object_id = dc.parent_object_id "
            "AND c.column_id = dc.parent_column_id "
            "WHERE (? IS NULL OR s.name = ?) "
            "AND (? IS NULL OR dc.parent_object_id = OBJECT_ID(?)) "
            "ORDER BY dc.object_id, dc.name;"
        ),
        param_roles=("schema", "schema", "object", "object"),
    ),
    QuerySpec(
        name="indexes",
        category="indexes",
        sql=(
            "SELECT i.object_id, i.index_id, i.name AS [index_name], "
            "i.type_desc, i.is_unique, i.is_primary_key, "
            "i.is_unique_constraint, i.has_filter, i.filter_definition, "
            "s.name AS [schema_name], t.name AS [table_name], "
            "ic.key_ordinal, c.name AS [column_name], ic.is_included_column "
            "FROM sys.indexes AS i "
            "JOIN sys.tables AS t ON t.object_id = i.object_id "
            "JOIN sys.schemas AS s ON s.schema_id = t.schema_id "
            "LEFT JOIN sys.index_columns AS ic "
            "ON ic.object_id = i.object_id AND ic.index_id = i.index_id "
            "LEFT JOIN sys.columns AS c "
            "ON c.object_id = ic.object_id AND c.column_id = ic.column_id "
            "WHERE (? IS NULL OR s.name = ?) "
            "AND (? IS NULL OR i.object_id = OBJECT_ID(?)) "
            "ORDER BY i.object_id, i.index_id, ic.key_ordinal, c.name;"
        ),
        param_roles=("schema", "schema", "object", "object"),
    ),
    # --- programmable objects (definitions via sys.sql_modules) ---
    QuerySpec(
        name="modules",
        category="module_definitions",
        sql=(
            "SELECT o.object_id, s.name AS [schema_name], "
            "o.name AS [object_name], o.[type], o.type_desc, "
            "o.create_date, o.modify_date, "
            "OBJECTPROPERTY(o.object_id, 'IsEncrypted') AS [is_encrypted], "
            "m.is_recompiled, m.execute_as_principal_id, "
            "m.definition "
            "FROM sys.objects AS o "
            "JOIN sys.schemas AS s ON s.schema_id = o.schema_id "
            "LEFT JOIN sys.sql_modules AS m ON m.object_id = o.object_id "
            "WHERE o.is_ms_shipped = 0 "
            "AND o.[type] IN ('P', 'FN', 'IF', 'TF', 'V') "
            "AND (? IS NULL OR s.name = ?) "
            "AND (? IS NULL OR o.object_id = OBJECT_ID(?)) "
            "ORDER BY s.name, o.name;"
        ),
        param_roles=("schema", "schema", "object", "object"),
    ),
    # DML triggers live in sys.objects (same schema as their table);
    # database DDL triggers exist only in sys.triggers and carry no
    # schema, so they are covered under database-wide scope only.
    # OBJECTPROPERTY('IsEncrypted') does not apply to database DDL
    # triggers, so their encryption evidence is projected NULL and the
    # availability reason stays UNKNOWN.
    QuerySpec(
        name="triggers",
        category="module_definitions",
        sql=(
            "SELECT t.object_id, s.name AS [schema_name], "
            "t.name AS [object_name], t.type_desc, "
            "t.is_disabled, t.is_instead_of_trigger, "
            "t.is_not_for_replication, te.type_desc AS [event_type], "
            "CASE WHEN o.object_id IS NULL THEN NULL "
            "ELSE OBJECTPROPERTY(t.object_id, 'IsEncrypted') "
            "END AS [is_encrypted], "
            "m.definition "
            "FROM sys.triggers AS t "
            "LEFT JOIN sys.objects AS o ON o.object_id = t.object_id "
            "LEFT JOIN sys.schemas AS s ON s.schema_id = o.schema_id "
            "LEFT JOIN sys.trigger_events AS te ON te.object_id = t.object_id "
            "LEFT JOIN sys.sql_modules AS m ON m.object_id = t.object_id "
            "WHERE (? IS NULL OR s.name = ?) "
            "AND (? IS NULL OR t.object_id = OBJECT_ID(?)) "
            "ORDER BY t.object_id, te.type_desc;"
        ),
        param_roles=("schema", "schema", "object", "object"),
    ),
    # --- SQL Server Agent (msdb, three-part names; separate visibility
    # boundary). Command text is a distinct opt-in query so the default
    # job query never touches sysjobsteps.command. ---
    QuerySpec(
        name="jobs",
        category="agent_jobs",
        requires=FLAG_INCLUDE_JOBS,
        sql=(
            "SELECT j.job_id, j.name AS [job_name], j.enabled, "
            "js.step_id, js.step_name, js.subsystem, js.database_name, "
            "js.on_success_action, js.on_failure_action, "
            "sch.enabled AS [schedule_enabled], "
            "sch.freq_type, sch.freq_interval, sch.active_start_time, "
            "sjs.next_run_date, sjs.next_run_time, "
            "sjs.schedule_id, sch.name AS [schedule_name] "
            "FROM msdb.dbo.sysjobs AS j "
            "LEFT JOIN msdb.dbo.sysjobsteps AS js ON js.job_id = j.job_id "
            "LEFT JOIN msdb.dbo.sysjobschedules AS sjs "
            "ON sjs.job_id = j.job_id "
            "LEFT JOIN msdb.dbo.sysschedules AS sch "
            "ON sch.schedule_id = sjs.schedule_id "
            "ORDER BY j.name, js.step_id, sch.name, sjs.schedule_id;"
        ),
    ),
    QuerySpec(
        name="job_step_commands",
        category="agent_job_step_text",
        requires=FLAG_INCLUDE_JOB_STEP_TEXT,
        sql=(
            "SELECT j.name AS [job_name], js.step_id, "
            "js.step_name, js.command "
            "FROM msdb.dbo.sysjobs AS j "
            "JOIN msdb.dbo.sysjobsteps AS js ON js.job_id = j.job_id "
            "ORDER BY j.name, js.step_id;"
        ),
    ),
)

QUERY_BY_NAME: dict[str, QuerySpec] = {spec.name: spec for spec in QUERY_REGISTRY}
REGISTRY_SQL_TEXTS: frozenset[str] = frozenset(spec.sql for spec in QUERY_REGISTRY)

CAPABILITY_BY_CATEGORY = {
    "tables": CAPABILITY_DATABASE_CATALOG,
    "integrity": CAPABILITY_DATABASE_CATALOG,
    "indexes": CAPABILITY_DATABASE_CATALOG,
    "module_definitions": CAPABILITY_MODULE_DEFINITIONS,
    "agent_jobs": CAPABILITY_AGENT_JOBS,
    "agent_job_step_text": CAPABILITY_AGENT_JOB_STEP_TEXT,
}


# ---------------------------------------------------------------------------
# Scope
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScopeItem:
    """One concrete scope execution: database-wide, one schema, or one
    ``schema.object`` two-part name."""

    kind: str  # "all" | "schema" | "object"
    value: str | None = None

    @property
    def schema(self) -> str | None:
        if self.kind == "schema":
            return self.value
        if self.kind == "object":
            return (self.value or "").split(".", 1)[0]
        return None

    @property
    def two_part(self) -> str | None:
        return self.value if self.kind == "object" else None

    def as_dict(self) -> dict[str, str]:
        if self.kind == "all":
            return {"kind": self.kind}
        return {"kind": self.kind, "value": self.value or ""}


@dataclass(frozen=True)
class _RequestedScope:
    schemas: tuple[str, ...]
    objects: tuple[str, ...]
    include_jobs: bool
    include_job_step_text: bool

    def items(self) -> tuple[ScopeItem, ...]:
        if not self.schemas and not self.objects:
            return (ScopeItem("all"),)
        items: list[ScopeItem] = []
        for name in sorted(set(self.schemas)):
            items.append(ScopeItem("schema", name))
        for name in sorted(set(self.objects)):
            items.append(ScopeItem("object", name))
        return tuple(items)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schemas": list(self.schemas),
            "objects": list(self.objects),
            FLAG_INCLUDE_JOBS: self.include_jobs,
            FLAG_INCLUDE_JOB_STEP_TEXT: self.include_job_step_text,
        }


# ---------------------------------------------------------------------------
# Row normalization
# ---------------------------------------------------------------------------


def _text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return value.hex()
    iso = getattr(value, "isoformat", None)
    if callable(iso):
        return iso()
    return str(value)


def _flag(value: Any) -> bool:
    return bool(value)


def _definition_fields(raw: Any, encrypted: Any) -> dict[str, Any]:
    """Definition-availability fields for one definition-bearing record
    (module, trigger, computed column, check/default constraint, or
    filtered-index predicate).

    A NULL (or empty) definition is UNAVAILABLE; the reason is specific
    only when the catalog itself gives evidence (IsEncrypted), never
    invented. The raw text and its UTF-8 sha256 are recorded only when
    AVAILABLE.
    """
    text = _text(raw)
    if text is None or text == "":
        return {
            "definition_status": DEFINITION_UNAVAILABLE,
            "definition_reason": "ENCRYPTED" if _flag(encrypted) else "UNKNOWN",
        }
    return {
        "definition_status": DEFINITION_AVAILABLE,
        "definition_reason": None,
        "definition_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "definition": text,
    }


def _convert_schemas(rows: Iterable[tuple]) -> list[dict[str, Any]]:
    records = [{"schema_id": r[0], "name": _text(r[1])} for r in rows]
    records.sort(key=lambda rec: (rec["name"] or "", rec["schema_id"] or 0))
    return records


def _convert_tables(rows: Iterable[tuple]) -> list[dict[str, Any]]:
    records = [
        {
            "object_id": r[0],
            "schema_name": _text(r[1]),
            "table_name": _text(r[2]),
            "type": _text(r[3]),
            "type_desc": _text(r[4]),
            "is_ms_shipped": _flag(r[5]),
        }
        for r in rows
    ]
    records.sort(key=lambda rec: (rec["schema_name"] or "", rec["table_name"] or ""))
    return records


def _convert_columns(rows: Iterable[tuple]) -> list[dict[str, Any]]:
    records = [
        {
            "object_id": r[0],
            "column_id": r[1],
            "name": _text(r[2]),
            "type_name": _text(r[3]),
            "max_length": r[4],
            "precision": r[5],
            "scale": r[6],
            "is_nullable": _flag(r[7]),
            "is_identity": _flag(r[8]),
            "is_computed": _flag(r[9]),
            "computed_is_persisted": _flag(r[11]),
            "collation_name": _text(r[12]),
            "identity_seed": _text(r[13]),
            "identity_increment": _text(r[14]),
        }
        for r in rows
    ]
    for record, r in zip(records, rows):
        # Only computed columns carry an expression; a non-computed
        # column is not "unavailable", it has no expression fields.
        if record["is_computed"]:
            record.update(_definition_fields(r[10], None))
    records.sort(key=lambda rec: (rec["object_id"] or 0, rec["column_id"] or 0))
    return records


def _convert_key_constraints(rows: Iterable[tuple]) -> list[dict[str, Any]]:
    grouped: dict[Any, dict[str, Any]] = {}
    for r in rows:
        record = grouped.get(r[0])
        if record is None:
            record = {
                "object_id": r[0],
                "constraint_name": _text(r[1]),
                "constraint_kind": _text(r[2]),
                "is_system_named": _flag(r[3]),
                "schema_name": _text(r[4]),
                "table_name": _text(r[5]),
                "index_id": r[6],
                "columns": [],
            }
            grouped[r[0]] = record
        record["columns"].append({"name": _text(r[8]), "ordinal": r[7]})
    records = list(grouped.values())
    for record in records:
        record["columns"].sort(
            key=lambda column: (column["ordinal"] if column["ordinal"] is not None else 0)
        )
    records.sort(key=lambda rec: (rec["schema_name"] or "", rec["table_name"] or "", rec["constraint_name"] or ""))
    return records


def _convert_foreign_keys(rows: Iterable[tuple]) -> list[dict[str, Any]]:
    grouped: dict[Any, dict[str, Any]] = {}
    for r in rows:
        record = grouped.get(r[0])
        if record is None:
            record = {
                "object_id": r[0],
                "constraint_name": _text(r[1]),
                "is_disabled": _flag(r[2]),
                "is_not_trusted": _flag(r[3]),
                "update_action": _text(r[4]),
                "delete_action": _text(r[5]),
                "parent_schema": _text(r[6]),
                "parent_table": _text(r[7]),
                "referenced_schema": _text(r[10]),
                "referenced_table": _text(r[11]),
                "column_pairs": [],
            }
            grouped[r[0]] = record
        record["column_pairs"].append(
            {
                "parent_column": _text(r[8]),
                "referenced_column": _text(r[12]),
                "ordinal": r[9],
            }
        )
    records = list(grouped.values())
    for record in records:
        record["column_pairs"].sort(
            key=lambda pair: (pair["ordinal"] if pair["ordinal"] is not None else 0)
        )
    records.sort(
        key=lambda rec: (
            rec["parent_schema"] or "",
            rec["parent_table"] or "",
            rec["constraint_name"] or "",
        )
    )
    return records


def _convert_check_constraints(rows: Iterable[tuple]) -> list[dict[str, Any]]:
    records = [
        {
            "object_id": r[0],
            "constraint_name": _text(r[1]),
            "is_disabled": _flag(r[2]),
            "is_not_trusted": _flag(r[3]),
            "schema_name": _text(r[5]),
            "table_name": _text(r[6]),
            "column_name": _text(r[7]),
        }
        for r in rows
    ]
    for record, r in zip(records, rows):
        record.update(_definition_fields(r[4], None))
    records.sort(
        key=lambda rec: (
            rec["schema_name"] or "",
            rec["table_name"] or "",
            rec["constraint_name"] or "",
        )
    )
    return records


def _convert_default_constraints(rows: Iterable[tuple]) -> list[dict[str, Any]]:
    records = [
        {
            "object_id": r[0],
            "constraint_name": _text(r[1]),
            "is_system_named": _flag(r[2]),
            "schema_name": _text(r[4]),
            "table_name": _text(r[5]),
            "column_name": _text(r[6]),
        }
        for r in rows
    ]
    for record, r in zip(records, rows):
        record.update(_definition_fields(r[3], None))
    records.sort(
        key=lambda rec: (
            rec["schema_name"] or "",
            rec["table_name"] or "",
            rec["constraint_name"] or "",
        )
    )
    return records


def _convert_indexes(rows: Iterable[tuple]) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, Any], dict[str, Any]] = {}
    for r in rows:
        key = (r[0], r[1])
        record = grouped.get(key)
        if record is None:
            record = {
                "object_id": r[0],
                "index_id": r[1],
                "index_name": _text(r[2]),
                "type_desc": _text(r[3]),
                "is_unique": _flag(r[4]),
                "is_primary_key": _flag(r[5]),
                "is_unique_constraint": _flag(r[6]),
                "has_filter": _flag(r[7]),
                "schema_name": _text(r[9]),
                "table_name": _text(r[10]),
                "columns": [],
            }
            grouped[key] = record
            # A non-filtered index is not "unavailable": it has no
            # predicate, so only filtered indexes carry availability
            # fields for filter_definition.
            if record["has_filter"]:
                record.update(_definition_fields(r[8], None))
        record["columns"].append(
            {
                "name": _text(r[12]),
                "ordinal": r[11],
                "is_included": _flag(r[13]),
            }
        )
    records = list(grouped.values())
    for record in records:
        record["columns"].sort(
            key=lambda column: (column["ordinal"] if column["ordinal"] is not None else 0)
        )
    records.sort(
        key=lambda rec: (
            rec["schema_name"] or "",
            rec["table_name"] or "",
            rec["index_id"] if rec["index_id"] is not None else 0,
        )
    )
    return records


def _convert_modules(rows: Iterable[tuple]) -> list[dict[str, Any]]:
    records = []
    for r in rows:
        record = {
            "object_id": r[0],
            "schema_name": _text(r[1]),
            "object_name": _text(r[2]),
            "object_type": _text(r[3]),
            "object_type_desc": _text(r[4]),
            "created": _text(r[5]),
            "modified": _text(r[6]),
            # OBJECTPROPERTY(..., 'IsEncrypted') is tri-state: NULL when
            # the server cannot provide the property.
            "is_encrypted": None if r[7] is None else _flag(r[7]),
            "is_recompiled": _flag(r[8]),
            "execute_as_principal_id": r[9],
        }
        record.update(_definition_fields(r[10], r[7]))
        records.append(record)
    records.sort(
        key=lambda rec: (rec["schema_name"] or "", rec["object_name"] or "")
    )
    return records


def _convert_triggers(rows: Iterable[tuple]) -> list[dict[str, Any]]:
    grouped: dict[Any, dict[str, Any]] = {}
    for r in rows:
        record = grouped.get(r[0])
        if record is None:
            record = {
                "object_id": r[0],
                "schema_name": _text(r[1]),
                "object_name": _text(r[2]),
                "object_type_desc": _text(r[3]),
                "is_disabled": _flag(r[4]),
                "is_instead_of_trigger": _flag(r[5]),
                "is_not_for_replication": _flag(r[6]),
                "events": [],
                # NULL for database DDL triggers: OBJECTPROPERTY does
                # not apply, so encryption evidence is unknown.
                "is_encrypted": None if r[8] is None else _flag(r[8]),
            }
            record.update(_definition_fields(r[9], r[8]))
            grouped[r[0]] = record
        event = _text(r[7])
        if event is not None and event not in record["events"]:
            record["events"].append(event)
    records = list(grouped.values())
    for record in records:
        record["events"].sort()
    records.sort(
        key=lambda rec: (rec["schema_name"] or "", rec["object_name"] or "")
    )
    return records


def _convert_jobs(rows: Iterable[tuple]) -> list[dict[str, Any]]:
    seen: set[tuple] = set()
    records = []
    for r in rows:
        key = tuple(row_value if not isinstance(row_value, bytearray) else bytes(row_value) for row_value in r)
        if key in seen:
            continue
        seen.add(key)
        records.append(
            {
                "job_id": _text(r[0]),
                "job_name": _text(r[1]),
                "enabled": _flag(r[2]),
                "step_id": r[3],
                "step_name": _text(r[4]),
                "subsystem": _text(r[5]),
                "database_name": _text(r[6]),
                "on_success_action": r[7],
                "on_failure_action": r[8],
                "schedule_enabled": _flag(r[9]),
                "schedule_freq_type": r[10],
                "schedule_freq_interval": r[11],
                "schedule_active_start_time": r[12],
                "next_run_date": r[13],
                "next_run_time": r[14],
                "schedule_id": r[15],
                "schedule_name": _text(r[16]),
            }
        )
    records.sort(
        key=lambda rec: (
            rec["job_name"] or "",
            rec["step_id"] if rec["step_id"] is not None else 0,
            rec["step_name"] or "",
            rec["schedule_id"] if rec["schedule_id"] is not None else 0,
            rec["schedule_name"] or "",
        )
    )
    return records


def _merge_job_commands(jobs: list[dict[str, Any]], rows: Iterable[tuple]) -> list[dict[str, Any]]:
    commands = {
        (_text(r[0]), r[1]): {"step_name": _text(r[2]), "command": _text(r[3])}
        for r in rows
    }
    for record in jobs:
        match = commands.get((record["job_name"], record["step_id"]))
        if match is not None:
            record["command"] = match["command"]
    return jobs


_ROW_CONVERTERS: dict[str, Callable[[Iterable[tuple]], list[dict[str, Any]]]] = {
    "schemas": _convert_schemas,
    "tables": _convert_tables,
    "columns": _convert_columns,
    "key_constraints": _convert_key_constraints,
    "foreign_keys": _convert_foreign_keys,
    "check_constraints": _convert_check_constraints,
    "default_constraints": _convert_default_constraints,
    "indexes": _convert_indexes,
    "modules": _convert_modules,
    "triggers": _convert_triggers,
    "jobs": _convert_jobs,
}


# ---------------------------------------------------------------------------
# Completeness
# ---------------------------------------------------------------------------


@dataclass
class _CategoryTally:
    requested: bool = False
    ok: int = 0
    failed: int = 0
    records: int = 0
    unavailable: int = 0
    visibility_ok: bool | None = None
    parent_failed: bool = False

    def status(self) -> str:
        """Final completeness rule (user decision 2026-10-07, extended
        by review round W-18-FIX1): in-scope data partly retrieved =
        PARTIAL; the source wholly inaccessible = BLOCKED; flag absent
        = NOT_REQUESTED. COMPLETE only when every required query
        succeeded, nothing in scope is unavailable, and the category's
        visibility precondition is proven (True). An unproven
        precondition (False/NULL) keeps a successfully queried category
        PARTIAL; agent_job_step_text without its successful parent jobs
        query can never be COMPLETE."""
        if not self.requested:
            return STATUS_NOT_REQUESTED
        if self.failed and self.records == 0:
            return STATUS_BLOCKED
        if self.parent_failed or self.visibility_ok is not True:
            return STATUS_PARTIAL
        if self.failed or self.unavailable:
            return STATUS_PARTIAL
        return STATUS_COMPLETE


# ---------------------------------------------------------------------------
# Capture run
# ---------------------------------------------------------------------------


@dataclass
class _CaptureRun:
    scope: _RequestedScope
    warnings: list[str] = field(default_factory=list)
    rows: dict[str, list[tuple]] = field(default_factory=dict)
    tallies: dict[str, _CategoryTally] = field(
        default_factory=lambda: {
            capability: _CategoryTally() for capability in CAPABILITY_ORDER
        }
    )

    def add_rows(self, name: str, new_rows: Sequence[tuple]) -> None:
        bucket = self.rows.setdefault(name, [])
        seen = {(self._hashable(r)) for r in bucket}
        for row in new_rows:
            key = self._hashable(row)
            if key not in seen:
                seen.add(key)
                bucket.append(row)

    @staticmethod
    def _hashable(row: tuple) -> tuple:
        return tuple(
            bytes(value) if isinstance(value, bytearray) else value for value in row
        )


def _params_for(spec: QuerySpec, item: ScopeItem) -> tuple:
    values = {"schema": item.schema, "object": item.two_part}
    return tuple(values.get(role) for role in spec.param_roles)


def _run_capture_query(session: Any, run: _CaptureRun, spec: QuerySpec) -> tuple | None:
    """Run one capture-context query; failures become warnings and null
    capture fields (they never abort a valid inventory)."""
    try:
        row = session.fetch_one(spec.sql, None)
    except db_guard.GuardBlockedError:
        raise
    except Exception:
        run.warnings.append(f"capture query '{spec.name}' failed")
        return None
    if row is None:
        run.warnings.append(f"capture query '{spec.name}' returned no row")
        return None
    return tuple(row)


def _new_capture_context() -> dict[str, Any]:
    return {
        "database_name": None,
        "server": {
            "product_version": None,
            "product_level": None,
            "edition": None,
            "engine_edition": None,
        },
        "compatibility_level": None,
        "collation": None,
        "principal_name": None,
        "visibility": {
            VISIBILITY_DATABASE: None,
            VISIBILITY_JOBS: None,
            "limitation": VISIBILITY_LIMITATION,
        },
    }


def _visibility_value(value: Any) -> bool | None:
    return None if value is None else bool(value)


def _apply_capture_row(context: dict[str, Any], name: str, row: tuple) -> None:
    if name == "db_name":
        context["database_name"] = _text(row[0])
    elif name == "server_properties":
        context["server"] = {
            "product_version": _text(row[0]),
            "product_level": _text(row[1]),
            "edition": _text(row[2]),
            "engine_edition": row[3],
        }
    elif name == "database_properties":
        context["compatibility_level"] = row[1]
        context["collation"] = _text(row[2])
    elif name == "principal":
        context["principal_name"] = _text(row[0])
    elif name == "database_visibility":
        context["visibility"][VISIBILITY_DATABASE] = _visibility_value(row[0])
    elif name == "agent_visibility":
        context["visibility"][VISIBILITY_JOBS] = _visibility_value(row[0])


def _execute_inventory(
    session: Any, run: _CaptureRun
) -> None:
    scope_items = run.scope.items()
    for spec in QUERY_REGISTRY:
        if spec.category == CAPTURE_CATEGORY:
            continue
        capability = CAPABILITY_BY_CATEGORY[spec.category]
        if spec.requires is not None:
            if not getattr(run.scope, spec.requires):
                continue
        tally = run.tallies[capability]
        tally.requested = True
        executions = scope_items if spec.param_roles else (ScopeItem("all"),)
        for item in executions:
            params = _params_for(spec, item) if spec.param_roles else None
            try:
                if spec.mode == "one":
                    row = session.fetch_one(spec.sql, params)
                    fetched: list[tuple] = [row] if row is not None else []
                else:
                    fetched = list(session.fetch_all(spec.sql, params) or [])
            except db_guard.GuardBlockedError:
                raise
            except Exception:
                tally.failed += 1
                run.warnings.append(
                    f"inventory query '{spec.name}' failed"
                    f" ({spec.category}, scope {item.as_dict()})"
                )
                continue
            tally.ok += 1
            if fetched:
                run.add_rows(spec.name, fetched)


def _finalize_inventory(
    run: _CaptureRun, context: dict[str, Any]
) -> dict[str, Any]:
    converted: dict[str, list[dict[str, Any]]] = {}
    for name, spec in QUERY_BY_NAME.items():
        if name in _ROW_CONVERTERS:
            converted[name] = _ROW_CONVERTERS[name](run.rows.get(name, []))

    jobs = converted.get("jobs", [])
    command_rows = run.rows.get("job_step_commands", [])
    if command_rows:
        jobs = _merge_job_commands(jobs, command_rows)

    modules = converted.get("modules", [])
    triggers = converted.get("triggers", [])
    unavailable = sum(
        1
        for record in (*modules, *triggers)
        if record.get("definition_status") == DEFINITION_UNAVAILABLE
    )

    catalog_records = (
        len(converted.get("schemas", []))
        + len(converted.get("tables", []))
        + len(converted.get("columns", []))
        + len(converted.get("key_constraints", []))
        + len(converted.get("foreign_keys", []))
        + len(converted.get("check_constraints", []))
        + len(converted.get("default_constraints", []))
        + len(converted.get("indexes", []))
    )
    catalog_unavailable = sum(
        1
        for record in (
            *converted.get("columns", []),
            *converted.get("check_constraints", []),
            *converted.get("default_constraints", []),
            *converted.get("indexes", []),
        )
        if record.get("definition_status") == DEFINITION_UNAVAILABLE
    )
    if catalog_unavailable:
        run.warnings.append(
            f"{catalog_unavailable} in-scope catalog expression(s)"
            " unavailable (computed column, check/default constraint,"
            " or filtered index)"
        )
    module_records = len(modules) + len(triggers)
    run.tallies[CAPABILITY_DATABASE_CATALOG].records = catalog_records
    run.tallies[CAPABILITY_DATABASE_CATALOG].unavailable = catalog_unavailable
    run.tallies[CAPABILITY_MODULE_DEFINITIONS].records = module_records
    run.tallies[CAPABILITY_MODULE_DEFINITIONS].unavailable = unavailable
    run.tallies[CAPABILITY_AGENT_JOBS].records = len(jobs)
    # Only command evidence actually merged into the job inventory
    # counts; when the parent jobs query failed there are no job
    # records to attach, so retained evidence is zero.
    run.tallies[CAPABILITY_AGENT_JOB_STEP_TEXT].records = sum(
        1 for record in jobs if "command" in record
    )

    # F6: step text without its successful parent jobs query cannot be
    # COMPLETE and must not masquerade as complete evidence.
    jobs_tally = run.tallies[CAPABILITY_AGENT_JOBS]
    step_tally = run.tallies[CAPABILITY_AGENT_JOB_STEP_TEXT]
    step_tally.parent_failed = (
        step_tally.requested and jobs_tally.requested and jobs_tally.failed > 0
    )
    if step_tally.parent_failed and not (
        step_tally.failed and step_tally.records == 0
    ):
        run.warnings.append(
            "agent job-step text is not linked to a job inventory:"
            " the jobs query did not succeed"
        )

    # F1: requested COMPLETE requires the category's visibility
    # precondition to be proven; an unproven precondition on a
    # successfully queried category degrades to PARTIAL with a warning
    # naming the missing precondition.
    for capability, visibility_key in CAPABILITY_VISIBILITY.items():
        tally = run.tallies[capability]
        if not tally.requested:
            continue
        proven = context["visibility"].get(visibility_key)
        tally.visibility_ok = proven is True
        if proven is not True and not (tally.failed and tally.records == 0):
            run.warnings.append(VISIBILITY_WARNINGS[visibility_key])

    return {
        "schemas": converted.get("schemas", []),
        "tables": converted.get("tables", []),
        "columns": converted.get("columns", []),
        "integrity": {
            "key_constraints": converted.get("key_constraints", []),
            "foreign_keys": converted.get("foreign_keys", []),
            "check_constraints": converted.get("check_constraints", []),
            "default_constraints": converted.get("default_constraints", []),
            "indexes": converted.get("indexes", []),
        },
        "modules": modules,
        "triggers": triggers,
        "agent_jobs": jobs,
    }


def _capabilities(run: _CaptureRun) -> dict[str, str]:
    return {
        capability: run.tallies[capability].status()
        for capability in CAPABILITY_ORDER
    }


# ---------------------------------------------------------------------------
# Rendering (pure functions of the normalized snapshot)
# ---------------------------------------------------------------------------


def dump_json(snapshot: dict[str, Any]) -> str:
    """Canonical JSON serialization: sorted keys, stable indentation."""
    return json.dumps(snapshot, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def render_markdown(snapshot: dict[str, Any]) -> str:
    """Human-readable view derived from the same normalized snapshot.
    Never emits raw definitions, job-step commands, or expressions —
    only object identifiers, statuses, and hashes."""
    capture = snapshot["capture"]
    capabilities = snapshot["capabilities"]
    inventory = snapshot["inventory"]
    server = capture["server"]
    scope = snapshot["scope"]
    lines: list[str] = []
    lines.append("# MSSQL inspection snapshot")
    lines.append("")
    lines.append(f"- capture_id: `{capture['capture_id']}`")
    lines.append(f"- captured_at_utc: {capture['captured_at_utc']}")
    lines.append(f"- tool: {capture['tool_id']} (schema_version {capture['schema_version']})")
    lines.append(f"- profile: {capture['profile']}")
    if capture["expect_database"]:
        lines.append(f"- expect_database: {capture['expect_database']}")
    lines.append(
        f"- database: {capture['database_name']}"
        f" (compatibility_level {capture['compatibility_level']},"
        f" collation {capture['collation']})"
    )
    lines.append(
        f"- server: {server['product_version']} {server['product_level']}"
        f" {server['edition']} engine_edition={server['engine_edition']}"
    )
    lines.append(f"- principal: {capture['principal_name']}")
    lines.append(
        f"- visibility limitation: {capture['visibility']['limitation']}"
    )
    lines.append(
        "- scope: "
        + ", ".join(
            f"{item['kind']}{':' + item['value'] if 'value' in item else ''}"
            for item in capture["effective_scope"]
        )
    )
    lines.append("")
    lines.append("## Capabilities")
    lines.append("")
    lines.append("| capability | status |")
    lines.append("| --- | --- |")
    for capability in CAPABILITY_ORDER:
        lines.append(f"| {capability} | {capabilities[capability]} |")
    lines.append("")
    if snapshot["warnings"]:
        lines.append("## Warnings")
        lines.append("")
        for warning in snapshot["warnings"]:
            lines.append(f"- {warning}")
        lines.append("")
    lines.append("## Inventory")
    lines.append("")
    scope_values = set(scope["schemas"]) | set(scope["objects"])
    lines.append(
        f"- schemas: {len(inventory['schemas'])}"
        + (f" (scope: {', '.join(sorted(scope_values))})" if scope_values else "")
    )
    lines.append(f"- tables: {len(inventory['tables'])}")
    lines.append(f"- columns: {len(inventory['columns'])}")
    integrity = inventory["integrity"]
    lines.append(f"- key_constraints: {len(integrity['key_constraints'])}")
    lines.append(f"- foreign_keys: {len(integrity['foreign_keys'])}")
    lines.append(f"- check_constraints: {len(integrity['check_constraints'])}")
    lines.append(f"- default_constraints: {len(integrity['default_constraints'])}")
    lines.append(f"- indexes: {len(integrity['indexes'])}")
    lines.append("")
    lines.append("### Modules")
    lines.append("")
    for record in inventory["modules"]:
        lines.append(
            f"- {record['schema_name']}.{record['object_name']}"
            f" ({record['object_type_desc']}, {record['object_id']})"
            f" definition={record['definition_status']}"
            + (
                f" sha256={record['definition_sha256']}"
                if record["definition_status"] == DEFINITION_AVAILABLE
                else f" reason={record['definition_reason']}"
            )
        )
    lines.append("")
    lines.append("### Triggers")
    lines.append("")
    for record in inventory["triggers"]:
        owner = record["schema_name"] or "(database)"
        lines.append(
            f"- {owner}.{record['object_name']}"
            f" ({record['object_type_desc']}, {record['object_id']})"
            f" definition={record['definition_status']}"
            + (
                f" sha256={record['definition_sha256']}"
                if record["definition_status"] == DEFINITION_AVAILABLE
                else f" reason={record['definition_reason']}"
            )
        )
    lines.append("")
    lines.append("### Agent jobs")
    lines.append("")
    for record in inventory["agent_jobs"]:
        lines.append(
            f"- {record['job_name']} (job_id {record['job_id']})"
            f" step {record['step_id']} {record['step_name']}"
            f" subsystem={record['subsystem']} database={record['database_name']}"
        )
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class _UsageParser(argparse.ArgumentParser):
    """Usage errors exit 1 (design exit-code contract), not argparse's 2,
    which is reserved for blocked/mismatch outcomes. The diagnostic is
    generic on purpose: rejected argument values are never echoed,
    because a mistaken value can contain a connection secret."""

    def error(self, message: str) -> None:  # noqa: D401 - argparse contract
        self.print_usage(sys.stderr)
        self.exit(
            1,
            f"{self.prog}: error: invalid usage; a required option is"
            " missing, malformed, or not accepted. Rejected argument"
            " values are not echoed.\n",
        )


def _build_parser() -> _UsageParser:
    parser = _UsageParser(prog="mssql_inspect", description=__doc__.splitlines()[0])
    subparsers = parser.add_subparsers(dest="command", required=True)
    snapshot = subparsers.add_parser(
        "snapshot", help="capture one read-only catalog snapshot"
    )
    snapshot.add_argument(
        "--profile",
        choices=(PROFILE_NAME,),
        default=PROFILE_NAME,
        help="logical DB profile (only %(choices)s is accepted)",
    )
    snapshot.add_argument(
        "--expect-database",
        default=None,
        metavar="NAME",
        help="abort before inventory when DB_NAME() differs",
    )
    snapshot.add_argument(
        "--schema",
        action="append",
        default=[],
        metavar="SCHEMA",
        help="scope to one schema (repeatable)",
    )
    snapshot.add_argument(
        "--object",
        action="append",
        default=[],
        metavar="SCHEMA.NAME",
        help="scope to one object (repeatable)",
    )
    snapshot.add_argument(
        "--include-jobs",
        action="store_true",
        help="request SQL Server Agent inventory (msdb)",
    )
    snapshot.add_argument(
        "--include-job-step-text",
        action="store_true",
        help="include job-step command text; requires --include-jobs",
    )
    snapshot.add_argument(
        "--format",
        choices=("json", "markdown", "both"),
        default="json",
        help=(
            "capture output; the JSON snapshot is always written as the"
            " canonical evidence, markdown/both additionally render"
            " snapshot.md from the same object"
        ),
    )
    snapshot.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_ROOT),
        metavar="PATH",
        help=(
            "capture root (default: %(default)s); the capture-id"
            " subdirectory is always appended"
        ),
    )
    return parser


def _validate_snapshot_args(parser: _UsageParser, args: argparse.Namespace) -> None:
    if args.include_job_step_text and not args.include_jobs:
        parser.error("--include-job-step-text requires --include-jobs")
    for schema in args.schema:
        if not schema.strip():
            parser.error("--schema values must be non-empty")
    for obj in args.object:
        parts = obj.split(".")
        if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
            parser.error(f"--object must be '<schema>.<name>': {obj!r}")


def _new_capture_id() -> str:
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{now}-{uuid.uuid4().hex[:8]}"


def _print_summary(
    capture_id: str,
    capture_dir: Path,
    scope: _RequestedScope,
    capabilities: dict[str, str],
    warnings: list[str],
) -> None:
    scope_text = (
        "database-wide"
        if not scope.schemas and not scope.objects
        else ", ".join(
            [*(f"schema:{s}" for s in sorted(set(scope.schemas))),
             *(f"object:{o}" for o in sorted(set(scope.objects)))]
        )
    )
    print(f"capture_id: {capture_id}")
    print(f"output: {capture_dir}")
    print(f"scope: {scope_text}")
    statuses = " ".join(
        f"{capability}={capabilities[capability]}" for capability in CAPABILITY_ORDER
    )
    print(f"capabilities: {statuses}")
    print(f"warnings: {len(warnings)}")
    for warning in warnings:
        print(f"warning: {warning}")


def run_snapshot(args: argparse.Namespace) -> int:
    scope = _RequestedScope(
        schemas=tuple(args.schema),
        objects=tuple(args.object),
        include_jobs=args.include_jobs,
        include_job_step_text=args.include_job_step_text,
    )
    run = _CaptureRun(scope=scope)

    session = db_guard.open_readonly(
        PROFILE_NAME,
        tool_id=TOOL_ID,
        allowed_profiles=(PROFILE_NAME,),
    )
    with session:
        context = _new_capture_context()
        db_name_spec = QUERY_BY_NAME["db_name"]
        db_name_row = _run_capture_query(session, run, db_name_spec)
        if db_name_row is not None:
            _apply_capture_row(context, "db_name", db_name_row)

        # Wrong-target guard: compare DB_NAME() before any other query
        # runs; on mismatch abort and write no capture. The guard's own
        # registry attestation always runs first and cannot be relaxed
        # by this flag. The comparison is exact: database-name equality
        # depends on instance collation, and Python case folding must
        # not invent identifier equivalence.
        if args.expect_database is not None:
            actual = context["database_name"]
            if actual is None:
                print(
                    "blocked: cannot verify expected database"
                    " (DB_NAME() capture query failed)",
                    file=sys.stderr,
                )
                return 2
            if actual != args.expect_database:
                print(
                    "blocked: expected database"
                    f" {args.expect_database!r} but connected to {actual!r}",
                    file=sys.stderr,
                )
                return 2

        for name in (
            "server_properties",
            "database_properties",
            "principal",
            "database_visibility",
            "agent_visibility",
        ):
            # msdb is touched only when jobs were requested (opt-in boundary).
            if name == "agent_visibility" and not scope.include_jobs:
                continue
            row = _run_capture_query(session, run, QUERY_BY_NAME[name])
            if row is not None:
                _apply_capture_row(context, name, row)

        _execute_inventory(session, run)

    inventory = _finalize_inventory(run, context)
    capabilities = _capabilities(run)

    capture_id = _new_capture_id()
    captured_at_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "capture": {
            "capture_id": capture_id,
            "captured_at_utc": captured_at_utc,
            "tool_id": TOOL_ID,
            "schema_version": SCHEMA_VERSION,
            "profile": PROFILE_NAME,
            "expect_database": args.expect_database,
            "database_name": context["database_name"],
            "server": context["server"],
            "compatibility_level": context["compatibility_level"],
            "collation": context["collation"],
            "principal_name": context["principal_name"],
            "visibility": context["visibility"],
            "requested_scope": scope.as_dict(),
            "effective_scope": [item.as_dict() for item in scope.items()],
        },
        "scope": scope.as_dict(),
        "capabilities": capabilities,
        "warnings": list(run.warnings),
        "inventory": inventory,
    }

    capture_dir = Path(args.output_dir) / capture_id
    capture_dir.mkdir(parents=True, exist_ok=False)
    (capture_dir / SNAPSHOT_JSON_NAME).write_text(dump_json(snapshot), encoding="utf-8")
    if args.format in ("markdown", "both"):
        (capture_dir / SNAPSHOT_MARKDOWN_NAME).write_text(
            render_markdown(snapshot), encoding="utf-8"
        )

    _print_summary(capture_id, capture_dir, scope, capabilities, run.warnings)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    _validate_snapshot_args(parser, args)
    try:
        return run_snapshot(args)
    except db_guard.GuardBlockedError as blocked:
        print(f"blocked: {blocked.reason}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
