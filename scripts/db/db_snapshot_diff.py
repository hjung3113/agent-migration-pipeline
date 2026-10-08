"""DB snapshot canonicalization and before/after delta (Issue #22 core).

DB-independent core per ``docs/issue-22-db-snapshot-diff-contract.md`` and
``migration/ISSUE-22-EXECUTION-PLAN.md``: capture-plan validation, canonical
typed value encoding, self-hashing JSON envelopes, a pure snapshot builder,
before/after pairing with raw structural delta calculation, a sanitized
Markdown renderer, and a small CLI (``delta``/``render``).

There is no database access, no ``capture`` subcommand, and no adapter here.
Raw structural deltas only: this tool never normalizes values and never
applies business comparison semantics; those belong to the behavior contract
via the future ``DbAssertionPort`` adapter.

Error policy: reason codes only. No snapshot/delta payload value, key value,
or parameter value is ever printed in reports, stdout, stderr, or exception
messages.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import tempfile
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable, Sequence

try:
    from scripts.db.sql_classification import (
        _split_batch_tokens,
        _tokenize,
        classify_batch,
    )
except ModuleNotFoundError:  # direct execution: python3 scripts/db/db_snapshot_diff.py
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.db.sql_classification import (  # type: ignore[no-redef]
        _split_batch_tokens,
        _tokenize,
        classify_batch,
    )


REPO_ROOT = Path(__file__).resolve().parents[2]

SNAPSHOT_FORMAT = "db-snapshot"
DELTA_FORMAT = "db-delta"
FORMAT_VERSION = 1

ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

MODES = ("delta", "state")
SIDES = ("legacy", "target")
MOMENTS = ("before", "after")

_PLAN_TOP_KEYS = frozenset({"version", "feature_id", "subjects"})
_PLAN_SUBJECT_KEYS = frozenset(
    {
        "subject_id",
        "mode",
        "comparison_rule_ref",
        "key_columns",
        "columns",
        "required_parameters",
        "max_rows",
        "legacy_query",
        "target_query",
    }
)
_PAIRING_FIELDS = (
    "feature_id",
    "subject_id",
    "side",
    "run_id",
    "fixture_ref",
    "mode",
    "comparison_rule_ref",
    "engine",
    "plan_version",
    "query_digest",
    "parameter_names",
    "parameter_digest",
    "columns",
    "key_columns",
    "max_rows",
)


class PlanError(Exception):
    """A db-comparison-plan file failed static validation."""


class SnapshotBlocked(Exception):
    """Snapshot production is blocked; no artifact is produced."""

    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


class PairingBlocked(Exception):
    """The before/after pair is invalid; no delta artifact is produced."""

    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


class ArtifactError(Exception):
    """An artifact file is unreadable, malformed, or fails digest verification."""


# ---------------------------------------------------------------------------
# Capture plan validation (P-2..P-4)
# ---------------------------------------------------------------------------


def load_plan(path: str | Path) -> dict:
    """Load and validate one ``db-comparison-plan.json`` file."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise PlanError(f"unreadable plan file: {exc}") from exc
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        raise PlanError(f"plan is not valid JSON: {exc}") from exc
    return validate_plan(obj)


def validate_plan(obj: Any) -> dict:
    """Validate the v1 plan schema strictly; unknown keys are rejected."""
    if not isinstance(obj, dict):
        raise PlanError("plan must be a JSON object")
    _require_exact_keys(obj, _PLAN_TOP_KEYS, "plan")
    version = obj["version"]
    if isinstance(version, bool) or not isinstance(version, int) or version != 1:
        raise PlanError("plan version must be the integer 1")
    _require_id(obj["feature_id"], "plan feature_id")
    subjects = obj["subjects"]
    if not isinstance(subjects, list) or not subjects:
        raise PlanError("plan subjects must be a non-empty list")
    seen: set[str] = set()
    for index, subject in enumerate(subjects):
        _validate_subject(subject, seen, index)
    return obj


def _require_exact_keys(obj: Any, expected: frozenset[str], label: str) -> None:
    if not isinstance(obj, dict):
        raise PlanError(f"{label} must be a JSON object")
    keys = set(obj)
    unknown = sorted(keys - expected)
    missing = sorted(expected - keys)
    if unknown or missing:
        raise PlanError(
            f"{label} keys invalid (unknown={unknown}, missing={missing})"
        )


def _require_id(value: Any, label: str) -> None:
    if not isinstance(value, str) or not ID_PATTERN.fullmatch(value):
        raise PlanError(f"{label} must match ^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _require_name_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list):
        raise PlanError(f"{label} must be a list")
    for entry in value:
        if not isinstance(entry, str) or not entry:
            raise PlanError(f"{label} entries must be non-empty strings")
    if len(set(value)) != len(value):
        raise PlanError(f"{label} entries must be unique")
    return value


def _validate_subject(subject: Any, seen: set[str], index: int) -> None:
    label = f"subject[{index}]"
    _require_exact_keys(subject, _PLAN_SUBJECT_KEYS, label)
    subject_id = subject["subject_id"]
    _require_id(subject_id, f"{label} subject_id")
    if subject_id in seen:
        raise PlanError(f"duplicate subject_id: {subject_id}")
    seen.add(subject_id)
    if subject["mode"] not in MODES:
        raise PlanError(f"{subject_id}: mode must be 'delta' or 'state'")
    rule_ref = subject["comparison_rule_ref"]
    if not isinstance(rule_ref, str) or not rule_ref:
        raise PlanError(
            f"{subject_id}: comparison_rule_ref must be a non-empty string"
        )
    columns = _require_name_list(subject["columns"], f"{subject_id}: columns")
    if not columns:
        raise PlanError(f"{subject_id}: columns must be non-empty")
    key_columns = _require_name_list(
        subject["key_columns"], f"{subject_id}: key_columns"
    )
    if any(name not in columns for name in key_columns):
        raise PlanError(f"{subject_id}: key_columns must be a subset of columns")
    parameters = _require_name_list(
        subject["required_parameters"], f"{subject_id}: required_parameters"
    )
    max_rows = subject["max_rows"]
    if isinstance(max_rows, bool) or not isinstance(max_rows, int) or max_rows < 1:
        raise PlanError(f"{subject_id}: max_rows must be a positive integer")
    if not key_columns and max_rows != 1:
        raise PlanError(
            f"{subject_id}: empty key_columns is only valid with max_rows == 1"
        )
    _validate_query(subject["legacy_query"], parameters, f"{subject_id}: legacy_query")
    _validate_query(subject["target_query"], parameters, f"{subject_id}: target_query")


def _validate_query(query: Any, required_parameters: Sequence[str], label: str) -> None:
    if not isinstance(query, str) or not query.strip():
        raise PlanError(f"{label} must be a non-empty string")
    if classify_batch(query).operation_class != "read":
        raise PlanError(f"{label} is not classified as read-only")
    tokens, malformed = _tokenize(query)
    statements, split_malformed = _split_batch_tokens(tokens)
    if malformed or split_malformed:
        raise PlanError(f"{label} is malformed SQL")
    if len(statements) != 1:
        raise PlanError(f"{label} must contain exactly one statement")
    if _count_top_level_selects(statements[0]) > 1:
        raise PlanError(f"{label} must contain exactly one statement")
    if _has_select_star(statements[0]):
        raise PlanError(f"{label} must not use select-star")
    placeholders = sum(
        1
        for token in statements[0]
        if token.kind == "symbol" and token.value == "?"
    )
    if placeholders != len(required_parameters):
        raise PlanError(
            f"{label} has {placeholders} '?' placeholder(s) for "
            f"{len(required_parameters)} required_parameters"
        )


def _is_word(token: Any, wanted: str) -> bool:
    return token.kind == "word" and token.value.upper() == wanted


def _has_select_star(tokens: Sequence[Any]) -> bool:
    """Reject ``*`` used as a select item; allow ``COUNT(*)`` and multiplication."""
    for index, token in enumerate(tokens):
        if token.kind != "symbol" or token.value != "*":
            continue
        previous = tokens[index - 1] if index else None
        if previous is None:
            continue
        if _is_word(previous, "SELECT") or _is_word(previous, "DISTINCT") or _is_word(previous, "ALL"):
            return True
        if previous.kind == "symbol" and previous.value in {",", "."}:
            return True
        if _ends_top_clause(tokens, index - 1):
            return True
    return False


def _ends_top_clause(tokens: Sequence[Any], last_index: int) -> bool:
    """True when ``tokens[last_index]`` ends a ``TOP`` clause of any accepted form.

    Covers ``TOP <literal|@param|?>``, ``TOP ( ... )`` with any balanced
    content, and either form followed by ``PERCENT`` or ``WITH TIES``.
    """
    if last_index < 0 or last_index >= len(tokens):
        return False
    token = tokens[last_index]
    if token.kind == "literal":
        return last_index >= 1 and _is_word(tokens[last_index - 1], "TOP")
    if token.kind == "word" and token.value.startswith("@"):
        return last_index >= 1 and _is_word(tokens[last_index - 1], "TOP")
    if token.kind == "symbol" and token.value == ")":
        open_index = _matching_open(tokens, last_index)
        if open_index is None or open_index == 0:
            return False
        if not _is_word(tokens[open_index - 1], "TOP"):
            return False
        return _parens_balanced(tokens[open_index + 1 : last_index])
    if _is_word(token, "PERCENT"):
        return last_index >= 1 and _ends_top_clause(tokens, last_index - 1)
    if _is_word(token, "TIES"):
        return (
            last_index >= 2
            and _is_word(tokens[last_index - 1], "WITH")
            and _ends_top_clause(tokens, last_index - 2)
        )
    return False


def _parens_balanced(tokens: Sequence[Any]) -> bool:
    """True when parentheses inside ``tokens`` balance out and never dip negative."""
    depth = 0
    for token in tokens:
        if token.kind != "symbol":
            continue
        if token.value == "(":
            depth += 1
        elif token.value == ")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def _matching_open(tokens: Sequence[Any], close_index: int) -> int | None:
    depth = 0
    for index in range(close_index, -1, -1):
        token = tokens[index]
        if token.kind != "symbol":
            continue
        if token.value == ")":
            depth += 1
        elif token.value == "(":
            depth -= 1
            if depth == 0:
                return index
    return None


_SET_OPERATORS = frozenset({"UNION", "INTERSECT", "EXCEPT"})


def _count_top_level_selects(tokens: Sequence[Any]) -> int:
    """Count depth-0 ``SELECT`` words that start a statement, not a set operand.

    A depth-0 ``SELECT`` directly after ``UNION``/``INTERSECT``/``EXCEPT``
    (optionally with ``ALL``/``DISTINCT`` in between) belongs to the same
    compound statement; any other depth-0 ``SELECT`` starts a new one.
    """
    count = 0
    depth = 0
    for index, token in enumerate(tokens):
        if token.kind == "symbol":
            if token.value == "(":
                depth += 1
                continue
            if token.value == ")":
                depth -= 1
                continue
        if depth != 0 or token.kind != "word" or token.value.upper() != "SELECT":
            continue
        previous = tokens[index - 1] if index else None
        if previous is not None and previous.kind == "word":
            previous_word = previous.value.upper()
            if previous_word in _SET_OPERATORS:
                continue
            if previous_word in {"ALL", "DISTINCT"} and index >= 2:
                before = tokens[index - 2]
                if before.kind == "word" and before.value.upper() in _SET_OPERATORS:
                    continue
        count += 1
    return count


def get_subject(plan: dict, subject_id: str) -> dict:
    """Return the validated plan subject with ``subject_id``."""
    subjects = plan.get("subjects") if isinstance(plan, dict) else None
    for subject in subjects or []:
        if isinstance(subject, dict) and subject.get("subject_id") == subject_id:
            return subject
    raise PlanError(f"unknown subject_id: {subject_id}")


# ---------------------------------------------------------------------------
# Canonical value encoding (P-6)
# ---------------------------------------------------------------------------


def encode_value(value: Any) -> dict:
    """Encode one DB scalar as a tagged canonical value ``{"t": ..., "v": ...}``.

    Exact type checks: scalar subclasses (for example ``numpy.float64`` or a
    ``float`` subclass with an overridden repr) have no approved canonical
    representation and are blocked instead of silently coerced.
    """
    if value is None:
        return {"t": "null", "v": None}
    kind = type(value)
    if kind is bool:
        return {"t": "bool", "v": value}
    if kind is int:
        return {"t": "int", "v": str(value)}
    if kind is Decimal:
        if not value.is_finite():
            raise SnapshotBlocked("unsupported-type")
        return {"t": "decimal", "v": str(value)}
    if kind is float:
        if not math.isfinite(value):
            raise SnapshotBlocked("unsupported-type")
        return {"t": "float", "v": repr(value)}
    if kind is str:
        return {"t": "text", "v": value}
    if kind is datetime:
        if value.tzinfo is not None and value.utcoffset() is not None:
            return {"t": "datetime_tz", "v": value.isoformat()}
        return {"t": "datetime", "v": value.isoformat()}
    if kind is date:
        return {"t": "date", "v": value.isoformat()}
    if kind is time:
        if value.tzinfo is not None and value.utcoffset() is not None:
            return {"t": "time_tz", "v": value.isoformat()}
        return {"t": "time", "v": value.isoformat()}
    if kind in (bytes, bytearray, memoryview):
        return {"t": "binary", "v": bytes(value).hex()}
    raise SnapshotBlocked("unsupported-type")


# ---------------------------------------------------------------------------
# Canonical bytes, digests, and envelopes (P-7)
# ---------------------------------------------------------------------------


def canonical_bytes(payload: Any) -> bytes:
    """Canonical JSON bytes: sorted keys, compact separators, UTF-8, no escapes."""
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def payload_digest(payload: Any) -> str:
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def make_envelope(payload: dict) -> dict:
    """Wrap a payload in the self-hashing envelope; digest excludes the envelope."""
    return {"content_sha256": payload_digest(payload), "payload": payload}


def load_artifact(path: str | Path) -> dict:
    """Load one snapshot/delta artifact, verifying digest, format, and version."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        raise ArtifactError(f"unreadable artifact: {path}") from None
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        raise ArtifactError("artifact is not valid JSON") from None
    if not isinstance(obj, dict) or set(obj) != {"content_sha256", "payload"}:
        raise ArtifactError(
            "artifact envelope must contain exactly content_sha256 and payload"
        )
    payload = obj["payload"]
    if not isinstance(payload, dict):
        raise ArtifactError("artifact payload must be a JSON object")
    if payload_digest(payload) != obj["content_sha256"]:
        raise ArtifactError("artifact digest mismatch")
    version = payload.get("format_version")
    if (
        payload.get("format") not in {SNAPSHOT_FORMAT, DELTA_FORMAT}
        or isinstance(version, bool)
        or version != FORMAT_VERSION
    ):
        raise ArtifactError("unknown artifact format or format_version")
    if payload["format"] == SNAPSHOT_FORMAT:
        _validate_snapshot_payload(payload)
    else:
        _validate_delta_payload(payload)
    return obj


# ---------------------------------------------------------------------------
# Artifact payload validation (capture invariants)
# ---------------------------------------------------------------------------

_ENCODER_TAGS = frozenset(
    {
        "null",
        "bool",
        "int",
        "decimal",
        "float",
        "text",
        "datetime",
        "datetime_tz",
        "date",
        "time",
        "time_tz",
        "binary",
    }
)

_SNAPSHOT_KEYS = frozenset(
    {
        "format",
        "format_version",
        "feature_id",
        "run_id",
        "fixture_ref",
        "subject_id",
        "mode",
        "comparison_rule_ref",
        "side",
        "moment",
        "engine",
        "profile_identity",
        "schema_revision",
        "plan_version",
        "query_digest",
        "parameter_names",
        "parameter_digest",
        "columns",
        "key_columns",
        "max_rows",
        "row_count",
        "rows",
        "captured_at",
    }
)

_DELTA_KEYS = frozenset(
    {
        "format",
        "format_version",
        "feature_id",
        "run_id",
        "fixture_ref",
        "subject_id",
        "mode",
        "comparison_rule_ref",
        "side",
        "engine",
        "columns",
        "key_columns",
        "query_digest",
        "parameter_digest",
        "before_sha256",
        "after_sha256",
        "added",
        "removed",
        "updated",
        "unchanged_count",
    }
)


def _is_valid_tagged(value: Any) -> bool:
    """True for a canonical tagged value ``{"t": tag, "v": value}``.

    ``v`` is ``None`` only for the ``null`` tag, ``bool`` only for ``bool``,
    and a ``str`` for every other encoder tag; this keeps Python's coercive
    equality (``True == 1``) unreachable between differently tagged cells.
    """
    if not isinstance(value, dict) or set(value) != {"t", "v"}:
        return False
    tag = value["t"]
    if tag == "null":
        return value["v"] is None
    if tag == "bool":
        return isinstance(value["v"], bool)
    return tag in _ENCODER_TAGS and isinstance(value["v"], str)


def _require_exact_artifact_keys(payload: dict, expected: frozenset, label: str) -> None:
    keys = set(payload)
    unknown = sorted(keys - expected)
    missing = sorted(expected - keys)
    if unknown or missing:
        raise ArtifactError(
            f"{label} keys invalid (unknown={unknown}, missing={missing})"
        )


def _require_payload_id(payload: dict, field: str, label: str) -> None:
    value = payload[field]
    if not isinstance(value, str) or not ID_PATTERN.fullmatch(value):
        raise ArtifactError(f"{label} {field} must match ^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _require_non_empty_str(payload: dict, field: str, label: str) -> None:
    value = payload[field]
    if not isinstance(value, str) or not value:
        raise ArtifactError(f"{label} {field} must be a non-empty string")


def _require_positive_int(payload: dict, field: str, label: str) -> int:
    value = payload[field]
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ArtifactError(f"{label} {field} must be a positive integer")
    return value


def _require_int(payload: dict, field: str, label: str) -> int:
    value = payload[field]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ArtifactError(f"{label} {field} must be an integer")
    return value


def _require_columns(payload: dict, label: str) -> list:
    columns = payload["columns"]
    if (
        not isinstance(columns, list)
        or not columns
        or any(not isinstance(name, str) or not name for name in columns)
    ):
        raise ArtifactError(
            f"{label} columns must be a non-empty list of non-empty strings"
        )
    if len(set(columns)) != len(columns):
        raise ArtifactError(f"{label} columns must be unique")
    return columns


def _require_key_columns(payload: dict, columns: list, label: str) -> list:
    key_columns = payload["key_columns"]
    if not isinstance(key_columns, list) or any(
        not isinstance(name, str) or not name for name in key_columns
    ):
        raise ArtifactError(f"{label} key_columns must be a list of non-empty strings")
    if len(set(key_columns)) != len(key_columns):
        raise ArtifactError(f"{label} key_columns must be unique")
    if any(name not in columns for name in key_columns):
        raise ArtifactError(f"{label} key_columns must be a subset of columns")
    return key_columns


def _require_tagged_row(row: Any, width: int, label: str) -> None:
    if not isinstance(row, list) or len(row) != width:
        raise ArtifactError(f"{label} must have one cell per column")
    if any(not _is_valid_tagged(cell) for cell in row):
        raise ArtifactError(f"{label} contains an invalid tagged value")


def _require_key_cells(key: Any, label: str) -> None:
    if not isinstance(key, list):
        raise ArtifactError(f"{label} must be a list of tagged values")
    for cell in key:
        if not _is_valid_tagged(cell):
            raise ArtifactError(f"{label} contains an invalid tagged value")
        if cell["t"] == "null":
            raise ArtifactError(f"{label} contains a null key cell")


def _validate_snapshot_payload(payload: Any) -> None:
    """Reject snapshot payloads that violate the builder's capture invariants.

    Raises ``ArtifactError`` with a reason only; payload values are never
    echoed in the message.
    """
    label = "snapshot payload"
    if not isinstance(payload, dict):
        raise ArtifactError(f"{label} must be a JSON object")
    _require_exact_artifact_keys(payload, _SNAPSHOT_KEYS, label)
    if payload["format"] != SNAPSHOT_FORMAT:
        raise ArtifactError(f"{label} format must be '{SNAPSHOT_FORMAT}'")
    version = payload["format_version"]
    if (
        isinstance(version, bool)
        or not isinstance(version, int)
        or version != FORMAT_VERSION
    ):
        raise ArtifactError(f"{label} format_version must be {FORMAT_VERSION}")
    for field in ("feature_id", "run_id", "subject_id"):
        _require_payload_id(payload, field, label)
    if payload["side"] not in SIDES:
        raise ArtifactError(f"{label} side must be one of {SIDES}")
    if payload["moment"] not in MOMENTS:
        raise ArtifactError(f"{label} moment must be one of {MOMENTS}")
    if payload["mode"] not in MODES:
        raise ArtifactError(f"{label} mode must be one of {MODES}")
    for field in (
        "fixture_ref",
        "comparison_rule_ref",
        "engine",
        "profile_identity",
        "schema_revision",
        "captured_at",
        "query_digest",
        "parameter_digest",
    ):
        _require_non_empty_str(payload, field, label)
    parameter_names = payload["parameter_names"]
    if not isinstance(parameter_names, list) or any(
        not isinstance(name, str) or not name for name in parameter_names
    ):
        raise ArtifactError(
            f"{label} parameter_names must be a list of non-empty strings"
        )
    if len(set(parameter_names)) != len(parameter_names):
        raise ArtifactError(f"{label} parameter_names must be unique")
    plan_version = payload["plan_version"]
    if (
        isinstance(plan_version, bool)
        or not isinstance(plan_version, int)
        or plan_version != 1
    ):
        raise ArtifactError(f"{label} plan_version must be the integer 1")
    max_rows = _require_positive_int(payload, "max_rows", label)
    columns = _require_columns(payload, label)
    key_columns = _require_key_columns(payload, columns, label)
    if not key_columns and max_rows != 1:
        raise ArtifactError(
            f"{label} empty key_columns is only valid with max_rows == 1"
        )
    rows = payload["rows"]
    if not isinstance(rows, list):
        raise ArtifactError(f"{label} rows must be a list")
    row_count = _require_int(payload, "row_count", label)
    if row_count != len(rows):
        raise ArtifactError(f"{label} row_count does not match the number of rows")
    if len(rows) > max_rows:
        raise ArtifactError(f"{label} rows exceed max_rows")
    width = len(columns)
    key_indexes = [columns.index(name) for name in key_columns]
    seen_keys: set = set()
    for row in rows:
        _require_tagged_row(row, width, f"{label} row")
        key = [row[index] for index in key_indexes]
        _require_key_cells(key, f"{label} key")
        key_id = canonical_bytes(key).decode("utf-8")
        if key_id in seen_keys:
            raise ArtifactError(f"{label} contains duplicate keys")
        seen_keys.add(key_id)


def _validate_delta_payload(payload: Any) -> None:
    """Reject delta payloads that ``compute_delta`` could not have produced.

    Raises ``ArtifactError`` with a reason only; payload values are never
    echoed in the message.
    """
    label = "delta payload"
    if not isinstance(payload, dict):
        raise ArtifactError(f"{label} must be a JSON object")
    _require_exact_artifact_keys(payload, _DELTA_KEYS, label)
    if payload["format"] != DELTA_FORMAT:
        raise ArtifactError(f"{label} format must be '{DELTA_FORMAT}'")
    version = payload["format_version"]
    if (
        isinstance(version, bool)
        or not isinstance(version, int)
        or version != FORMAT_VERSION
    ):
        raise ArtifactError(f"{label} format_version must be {FORMAT_VERSION}")
    for field in ("feature_id", "run_id", "subject_id"):
        _require_payload_id(payload, field, label)
    if payload["side"] not in SIDES:
        raise ArtifactError(f"{label} side must be one of {SIDES}")
    if payload["mode"] not in MODES:
        raise ArtifactError(f"{label} mode must be one of {MODES}")
    for field in (
        "fixture_ref",
        "comparison_rule_ref",
        "engine",
        "query_digest",
        "parameter_digest",
        "before_sha256",
        "after_sha256",
    ):
        _require_non_empty_str(payload, field, label)
    columns = _require_columns(payload, label)
    _require_key_columns(payload, columns, label)
    unchanged = payload["unchanged_count"]
    if isinstance(unchanged, bool) or not isinstance(unchanged, int) or unchanged < 0:
        raise ArtifactError(f"{label} unchanged_count must be a non-negative integer")
    width = len(columns)
    for field in ("added", "removed"):
        entries = payload[field]
        if not isinstance(entries, list):
            raise ArtifactError(f"{label} {field} must be a list")
        for entry in entries:
            if not isinstance(entry, dict) or set(entry) != {"key", "row"}:
                raise ArtifactError(
                    f"{label} {field} entry must contain exactly key and row"
                )
            _require_key_cells(entry["key"], f"{label} {field} key")
            _require_tagged_row(entry["row"], width, f"{label} {field} row")
    updated = payload["updated"]
    if not isinstance(updated, list):
        raise ArtifactError(f"{label} updated must be a list")
    for entry in updated:
        if not isinstance(entry, dict) or set(entry) != {
            "key",
            "changed_columns",
            "before",
            "after",
        }:
            raise ArtifactError(f"{label} updated entry keys invalid")
        _require_key_cells(entry["key"], f"{label} updated key")
        changed = entry["changed_columns"]
        if not isinstance(changed, list) or any(
            not isinstance(name, str) or not name or name not in columns
            for name in changed
        ):
            raise ArtifactError(f"{label} changed_columns must reference columns")
        _require_tagged_row(entry["before"], width, f"{label} updated before row")
        _require_tagged_row(entry["after"], width, f"{label} updated after row")


# ---------------------------------------------------------------------------
# Snapshot builder (P-5, P-8)
# ---------------------------------------------------------------------------


def build_snapshot(
    plan: dict,
    subject_id: str,
    *,
    side: str,
    moment: str,
    run_id: str,
    fixture_ref: str,
    engine: str,
    profile_identity: str,
    schema_revision: str,
    captured_at: str,
    parameters: dict,
    result_columns: Sequence[str],
    rows: Sequence[Sequence[Any]],
) -> dict:
    """Build one canonical snapshot envelope. Pure; writes nothing.

    ``plan`` must come from ``validate_plan``/``load_plan``. ``side`` selects
    the plan query used for the digest. All block conditions raise
    ``SnapshotBlocked`` and produce no artifact.
    """
    if side not in SIDES:
        raise ValueError(f"side must be one of {SIDES}")
    if moment not in MOMENTS:
        raise ValueError(f"moment must be one of {MOMENTS}")
    if not isinstance(run_id, str) or not ID_PATTERN.fullmatch(run_id):
        raise ValueError("run_id must match ^[A-Za-z0-9][A-Za-z0-9._-]*$")
    metadata = {
        "fixture_ref": fixture_ref,
        "engine": engine,
        "profile_identity": profile_identity,
        "schema_revision": schema_revision,
        "captured_at": captured_at,
    }
    for name, value in metadata.items():
        if not isinstance(value, str) or not value:
            raise ValueError(f"{name} must be a non-empty string")

    subject = get_subject(plan, subject_id)
    columns: list[str] = list(subject["columns"])
    key_columns: list[str] = list(subject["key_columns"])
    max_rows: int = subject["max_rows"]
    query: str = subject[f"{side}_query"]
    required_parameters: list[str] = list(subject["required_parameters"])

    if list(result_columns) != columns:
        raise SnapshotBlocked("column-mismatch")
    if len(rows) > max_rows:
        raise SnapshotBlocked("max-rows-exceeded")
    if not isinstance(parameters, dict) or set(parameters) != set(required_parameters):
        raise SnapshotBlocked("parameter-mismatch")

    parameter_names = list(required_parameters)
    parameter_digest = payload_digest(
        [[name, encode_value(parameters[name])] for name in parameter_names]
    )

    key_indexes = [columns.index(name) for name in key_columns]
    encoded: list[tuple[bytes, list, list]] = []
    seen_keys: set[bytes] = set()
    for row in rows:
        if len(row) != len(columns):
            raise SnapshotBlocked("row-width")
        if any(row[index] is None for index in key_indexes):
            raise SnapshotBlocked("null-key")
        key = [encode_value(row[index]) for index in key_indexes]
        key_bytes = canonical_bytes(key)
        if key_bytes in seen_keys:
            raise SnapshotBlocked("duplicate-key")
        seen_keys.add(key_bytes)
        encoded.append((key_bytes, key, [encode_value(value) for value in row]))
    encoded.sort(key=lambda item: item[0])

    payload = {
        "format": SNAPSHOT_FORMAT,
        "format_version": FORMAT_VERSION,
        "feature_id": plan["feature_id"],
        "run_id": run_id,
        "fixture_ref": fixture_ref,
        "subject_id": subject_id,
        "mode": subject["mode"],
        "comparison_rule_ref": subject["comparison_rule_ref"],
        "side": side,
        "moment": moment,
        "engine": engine,
        "profile_identity": profile_identity,
        "schema_revision": schema_revision,
        "plan_version": plan["version"],
        "query_digest": hashlib.sha256(query.encode("utf-8")).hexdigest(),
        "parameter_names": parameter_names,
        "parameter_digest": parameter_digest,
        "columns": columns,
        "key_columns": key_columns,
        "max_rows": max_rows,
        "row_count": len(encoded),
        "rows": [row for _, _, row in encoded],
        "captured_at": captured_at,
    }
    return make_envelope(payload)


# ---------------------------------------------------------------------------
# Pairing and structural delta (P-9)
# ---------------------------------------------------------------------------


def compute_delta(before_env: dict, after_env: dict) -> dict:
    """Compute the raw structural delta of a compatible before/after pair.

    Tagged values compare by exact equality; no normalization, tolerance, or
    ordering rule is applied. All lists are in canonical key order.
    """
    before = _payload_of(before_env)
    after = _payload_of(after_env)
    if before.get("format") != SNAPSHOT_FORMAT or after.get("format") != SNAPSHOT_FORMAT:
        raise PairingBlocked("not-a-snapshot")
    if before.get("moment") != "before" or after.get("moment") != "after":
        raise PairingBlocked("moment-order")
    for field in _PAIRING_FIELDS:
        if before.get(field) != after.get(field):
            raise PairingBlocked(f"pairing-mismatch:{field}")

    # Pairing checks keep their PairingBlocked contract for builder-shaped
    # envelopes; structural validation runs before any indexing so malformed
    # caller-built payloads fail as ArtifactError instead.
    _validate_snapshot_payload(before)
    _validate_snapshot_payload(after)

    columns, before_rows = _snapshot_rows(before)
    _, after_rows = _snapshot_rows(after)
    before_keys = set(before_rows)
    after_keys = set(after_rows)

    added = [
        {"key": after_rows[key_id][0], "row": after_rows[key_id][1]}
        for key_id in sorted(after_keys - before_keys)
    ]
    removed = [
        {"key": before_rows[key_id][0], "row": before_rows[key_id][1]}
        for key_id in sorted(before_keys - after_keys)
    ]
    updated = []
    unchanged_count = 0
    for key_id in sorted(before_keys & after_keys):
        before_row = before_rows[key_id][1]
        after_row = after_rows[key_id][1]
        if before_row == after_row:
            unchanged_count += 1
            continue
        changed_columns = [
            name for index, name in enumerate(columns) if before_row[index] != after_row[index]
        ]
        updated.append(
            {
                "key": before_rows[key_id][0],
                "changed_columns": changed_columns,
                "before": before_row,
                "after": after_row,
            }
        )

    payload = {
        "format": DELTA_FORMAT,
        "format_version": FORMAT_VERSION,
        "feature_id": before["feature_id"],
        "run_id": before["run_id"],
        "fixture_ref": before["fixture_ref"],
        "subject_id": before["subject_id"],
        "mode": before["mode"],
        "comparison_rule_ref": before["comparison_rule_ref"],
        "side": before["side"],
        "engine": before["engine"],
        "columns": columns,
        "key_columns": before["key_columns"],
        "query_digest": before["query_digest"],
        "parameter_digest": before["parameter_digest"],
        "before_sha256": payload_digest(before),
        "after_sha256": payload_digest(after),
        "added": added,
        "removed": removed,
        "updated": updated,
        "unchanged_count": unchanged_count,
    }
    return make_envelope(payload)


def _payload_of(envelope: Any) -> dict:
    if not isinstance(envelope, dict) or not isinstance(envelope.get("payload"), dict):
        raise ArtifactError("artifact envelope must contain a payload object")
    return envelope["payload"]


def _snapshot_rows(payload: dict) -> tuple[list[str], dict[str, tuple[list, list]]]:
    columns = payload.get("columns")
    key_columns = payload.get("key_columns")
    rows = payload.get("rows")
    if (
        not isinstance(columns, list)
        or not isinstance(key_columns, list)
        or not isinstance(rows, list)
    ):
        raise ArtifactError("artifact payload is missing columns/key_columns/rows")
    if any(name not in columns for name in key_columns):
        raise ArtifactError("artifact payload key_columns are not a subset of columns")
    key_indexes = [columns.index(name) for name in key_columns]
    keyed: dict[str, tuple[list, list]] = {}
    for row in rows:
        if not isinstance(row, list) or len(row) != len(columns):
            raise ArtifactError("artifact payload row width does not match columns")
        key = [row[index] for index in key_indexes]
        key_id = canonical_bytes(key).decode("utf-8")
        if key_id in keyed:
            # Defensive: payload validation already rejects duplicate keys;
            # never let dict assignment silently overwrite one.
            raise ArtifactError("artifact payload contains duplicate keys")
        keyed[key_id] = (key, row)
    return columns, keyed


# ---------------------------------------------------------------------------
# Markdown rendering (P-10)
# ---------------------------------------------------------------------------


def render_markdown(envelopes: Iterable[dict]) -> str:
    """Render one sanitized Markdown table row per artifact. Never prints values."""
    headers = ("kind", "subject", "side", "moment", "sha256", "rows/changes", "changed columns")
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for envelope in envelopes:
        payload = _payload_of(envelope)
        digest = envelope.get("content_sha256")
        digest = digest if isinstance(digest, str) else payload_digest(payload)
        kind = payload.get("format")
        if kind == SNAPSHOT_FORMAT:
            _validate_snapshot_payload(payload)
            moment = payload.get("moment")
            counts = f"rows={payload['row_count']}"
            changed = "—"
        elif kind == DELTA_FORMAT:
            _validate_delta_payload(payload)
            moment = "—"
            counts = (
                f"added={len(payload['added'])}"
                f" removed={len(payload['removed'])}"
                f" updated={len(payload['updated'])}"
                f" unchanged={payload['unchanged_count']}"
            )
            changed = ", ".join(_changed_column_union(payload)) or "—"
        else:
            raise ArtifactError("unknown artifact format")
        side = payload.get("side")
        cells = [
            _cell(kind),
            _cell(payload.get("subject_id")),
            _cell(side),
            _cell(moment),
            _cell(digest),
            _cell(counts),
            _cell(changed),
        ]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def _cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _changed_column_union(payload: dict) -> list[str]:
    union: list[str] = []
    for entry in payload.get("updated") or []:
        for name in (entry or {}).get("changed_columns") or []:
            if name not in union:
                union.append(name)
    return union


# ---------------------------------------------------------------------------
# CLI (P-11)
# ---------------------------------------------------------------------------


def default_delta_output_path(payload: dict) -> Path:
    """Default delta destination under ``.artifacts/db``; never sanitizes input.

    Unsafe ID/side values are rejected instead of being coerced into path
    components, and the resolved destination must stay inside the artifact
    root.
    """
    for field in ("feature_id", "run_id", "subject_id"):
        value = payload.get(field)
        if not isinstance(value, str) or not ID_PATTERN.fullmatch(value):
            raise ArtifactError(
                f"delta payload {field} is not a safe path component"
            )
    if payload.get("side") not in SIDES:
        raise ArtifactError("delta payload side is not a safe path component")
    root = (REPO_ROOT / ".artifacts" / "db").resolve()
    path = (
        root
        / payload["feature_id"]
        / payload["run_id"]
        / f"{payload['subject_id']}.{payload['side']}.delta.json"
    ).resolve()
    if not path.is_relative_to(root):
        raise ArtifactError("default output path escapes the artifact root")
    return path


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str):  # usage errors exit 1; argparse's default is 2
        self.print_usage(sys.stderr)
        self.exit(1, f"{self.prog}: error: {message}\n")


def _build_parser() -> _ArgumentParser:
    parser = _ArgumentParser(
        prog="db_snapshot_diff.py",
        description="DB snapshot canonicalization and before/after delta (no DB access).",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    delta = subcommands.add_parser(
        "delta", help="compute a delta from one before/after snapshot pair"
    )
    delta.add_argument("--before", required=True, help="before snapshot artifact path")
    delta.add_argument("--after", required=True, help="after snapshot artifact path")
    delta.add_argument(
        "--output",
        help="output path (default .artifacts/db/<feature_id>/<run_id>/<subject_id>.<side>.delta.json)",
    )
    render = subcommands.add_parser(
        "render", help="render snapshot/delta artifacts as a sanitized Markdown table"
    )
    render.add_argument("artifacts", nargs="+", help="artifact paths")
    render.add_argument("--output", help="output path (default stdout)")
    return parser


def _write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle_fd, temp_name = tempfile.mkstemp(dir=str(path.parent), prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(handle_fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def _artifact_json(envelope: dict) -> str:
    return json.dumps(envelope, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _run_delta(args: argparse.Namespace) -> int:
    before = load_artifact(args.before)
    after = load_artifact(args.after)
    delta = compute_delta(before, after)
    payload = delta["payload"]
    output = Path(args.output) if args.output else default_delta_output_path(payload)
    _write_text_atomic(output, _artifact_json(delta))
    print(
        f"delta {delta['content_sha256']}"
        f" added={len(payload['added'])}"
        f" removed={len(payload['removed'])}"
        f" updated={len(payload['updated'])}"
        f" unchanged={payload['unchanged_count']}"
        f" -> {output}"
    )
    return 0


def _run_render(args: argparse.Namespace) -> int:
    envelopes = [load_artifact(path) for path in args.artifacts]
    markdown = render_markdown(envelopes)
    if args.output:
        _write_text_atomic(Path(args.output), markdown)
    else:
        sys.stdout.write(markdown)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "delta":
            return _run_delta(args)
        return _run_render(args)
    except ArtifactError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except PairingBlocked as exc:
        print(f"blocked: {exc.reason_code}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
