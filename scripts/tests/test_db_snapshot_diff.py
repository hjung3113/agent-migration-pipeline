"""Core tests for the Issue #22 snapshot canonicalization and delta tool.

One test per core case in ``migration/ISSUE-22-EXECUTION-PLAN.md`` §4.
No database access: snapshots are built directly through ``build_snapshot``
and exercised end-to-end through the CLI.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date, datetime, time, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from scripts.db import db_snapshot_diff as dsd
from scripts.db.db_snapshot_diff import (
    ArtifactError,
    PairingBlocked,
    PlanError,
    SnapshotBlocked,
    build_snapshot,
    canonical_bytes,
    compute_delta,
    encode_value,
    render_markdown,
    validate_plan,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE = REPO_ROOT / "scripts" / "db" / "db_snapshot_diff.py"
SENTINEL = "SENTINEL-w22-leak-check-ZQ7F42"
COLUMNS = ["business_id", "status", "amount"]


def make_subject(**overrides):
    subject = {
        "subject_id": "db-001",
        "mode": "delta",
        "comparison_rule_ref": "behavior-contract.md :: orders",
        "key_columns": ["business_id"],
        "columns": list(COLUMNS),
        "required_parameters": ["business_id"],
        "max_rows": 10,
        "legacy_query": "SELECT business_id, status, amount FROM dbo.orders WHERE business_id = ?",
        "target_query": "SELECT business_id, status, amount FROM orders WHERE business_id = ?",
    }
    subject.update(overrides)
    return subject


def make_plan(subjects=None):
    return {
        "version": 1,
        "feature_id": "feat-demo",
        "subjects": subjects if subjects is not None else [make_subject()],
    }


def build(plan=None, **overrides):
    options = dict(
        side="legacy",
        moment="before",
        run_id="run-1",
        fixture_ref="fixture-1",
        engine="mssql",
        profile_identity="profile-a",
        schema_revision="rev-1",
        captured_at="2026-10-08T00:00:00+00:00",
        parameters={"business_id": "B-1"},
        result_columns=list(COLUMNS),
        rows=[["B-1", "open", Decimal("10.00")]],
    )
    options.update(overrides)
    return build_snapshot(plan or make_plan(), "db-001", **options)


def write_json(path: Path, obj) -> Path:
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    return path


def cli(*argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(MODULE), *argv],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )


# --- case 1: deterministic canonical bytes and digest, row order independent


def test_case01_identical_payloads_produce_identical_canonical_bytes_and_digest():
    rows = [["B-1", "open", Decimal("10.00")], ["B-2", "sent", Decimal("5.00")]]
    first = build(rows=rows)
    second = build(make_plan(), rows=[rows[1], rows[0]])
    assert canonical_bytes(first["payload"]) == canonical_bytes(second["payload"])
    assert first["content_sha256"] == second["content_sha256"]
    assert first["payload"]["rows"] == second["payload"]["rows"]
    # rows are stored in canonical key order regardless of input order
    assert first["payload"]["rows"][0][0] == {"t": "text", "v": "B-1"}


# --- case 2: digest excludes the envelope field; tampered files are rejected


def test_case02_digest_excludes_content_sha256_and_tampered_load_is_rejected(tmp_path):
    envelope = build()
    assert dsd.payload_digest(envelope["payload"]) == envelope["content_sha256"]

    path = write_json(tmp_path / "snap.json", envelope)
    assert dsd.load_artifact(path) == envelope

    tampered = {
        "content_sha256": envelope["content_sha256"],
        "payload": dict(envelope["payload"], row_count=envelope["payload"]["row_count"] + 1),
    }
    with pytest.raises(ArtifactError):
        dsd.load_artifact(write_json(tmp_path / "tampered.json", tampered))


# --- case 3: NULL versus empty string


def test_case03_null_and_empty_text_are_distinct():
    assert encode_value(None) == {"t": "null", "v": None}
    assert encode_value("") == {"t": "text", "v": ""}
    null_envelope = build(rows=[["B-1", None, Decimal("1.00")]])
    empty_envelope = build(rows=[["B-1", "", Decimal("1.00")]])
    assert null_envelope["content_sha256"] != empty_envelope["content_sha256"]
    assert null_envelope["payload"]["rows"][0][1] == {"t": "null", "v": None}
    assert empty_envelope["payload"]["rows"][0][1] == {"t": "text", "v": ""}


# --- case 4: decimal fidelity without float coercion; non-finite rejected


def test_case04_decimal_is_preserved_without_float_route_and_nan_rejected():
    encoded = encode_value(Decimal("12.30"))
    assert encoded == {"t": "decimal", "v": "12.30"}
    assert encoded["v"] != repr(float(Decimal("12.30")))
    assert encode_value(Decimal("12.3"))["v"] != encoded["v"]

    envelope = build()
    assert envelope["payload"]["rows"][0][2] == {"t": "decimal", "v": "10.00"}

    for bad in (Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")):
        with pytest.raises(SnapshotBlocked) as excinfo:
            encode_value(bad)
        assert excinfo.value.reason_code == "unsupported-type"


# --- case 5: binary/date/time/datetime encoding; unsupported types rejected


@pytest.mark.parametrize(
    "value,expected",
    [
        (b"\x00\x10\xff", {"t": "binary", "v": "0010ff"}),
        (bytearray(b"\x01\x02"), {"t": "binary", "v": "0102"}),
        (date(2026, 10, 8), {"t": "date", "v": "2026-10-08"}),
        (datetime(2026, 10, 8, 1, 2, 3), {"t": "datetime", "v": "2026-10-08T01:02:03"}),
        (
            datetime(2026, 10, 8, 1, 2, 3, tzinfo=timezone.utc),
            {"t": "datetime_tz", "v": "2026-10-08T01:02:03+00:00"},
        ),
        (time(1, 2, 3), {"t": "time", "v": "01:02:03"}),
        (time(1, 2, 3, tzinfo=timezone.utc), {"t": "time_tz", "v": "01:02:03+00:00"}),
    ],
)
def test_case05_binary_and_temporal_encoding(value, expected):
    assert encode_value(value) == expected


@pytest.mark.parametrize("value", [object(), {"unexpected": 1}, [1, 2], 1.5j])
def test_case05b_unsupported_types_are_blocked(value):
    with pytest.raises(SnapshotBlocked) as excinfo:
        encode_value(value)
    assert excinfo.value.reason_code == "unsupported-type"


# --- case 6: duplicate keys are blocked


def test_case06_duplicate_keys_are_blocked():
    with pytest.raises(SnapshotBlocked) as excinfo:
        build(rows=[["B-1", "open", Decimal("1.00")], ["B-1", "sent", Decimal("2.00")]])
    assert excinfo.value.reason_code == "duplicate-key"


# --- case 7: empty key_columns only with max_rows == 1 (P-4)


def test_case07_empty_key_columns_require_single_row_subjects():
    with pytest.raises(PlanError):
        validate_plan(make_plan([make_subject(key_columns=[], max_rows=10)]))

    allowed = validate_plan(make_plan([make_subject(key_columns=[], max_rows=1)]))
    assert allowed["subjects"][0]["key_columns"] == []

    single = build(
        make_plan([make_subject(key_columns=[], max_rows=1)]),
        rows=[["B-1", "open", Decimal("1.00")]],
    )
    assert single["payload"]["row_count"] == 1

    # two rows with the same (empty) key: the max_rows == 1 bound trips first
    with pytest.raises(SnapshotBlocked) as excinfo:
        build(
            make_plan([make_subject(key_columns=[], max_rows=1)]),
            rows=[["B-1", "open", Decimal("1.00")], ["B-2", "sent", Decimal("2.00")]],
        )
    assert excinfo.value.reason_code == "max-rows-exceeded"


# --- case 8: result column mismatch; select-star rejected, COUNT(*) allowed


@pytest.mark.parametrize(
    "result_columns",
    [
        ["business_id", "status"],
        ["business_id", "status", "amount", "extra"],
        ["status", "business_id", "amount"],
    ],
)
def test_case08_result_columns_must_match_declared_columns_in_order(result_columns):
    with pytest.raises(SnapshotBlocked) as excinfo:
        build(result_columns=result_columns)
    assert excinfo.value.reason_code == "column-mismatch"


@pytest.mark.parametrize(
    "query",
    [
        "SELECT * FROM dbo.orders WHERE business_id = ?",
        "SELECT DISTINCT * FROM dbo.orders WHERE business_id = ?",
        "SELECT ALL * FROM dbo.orders WHERE business_id = ?",
        "SELECT business_id, * FROM dbo.orders WHERE business_id = ?",
        "SELECT t.* FROM dbo.orders t WHERE business_id = ?",
        "SELECT TOP 3 * FROM dbo.orders WHERE business_id = ?",
        "SELECT TOP (3) * FROM dbo.orders WHERE business_id = ?",
        "SELECT TOP 3 PERCENT * FROM dbo.orders WHERE business_id = ?",
        "SELECT TOP 3 WITH TIES * FROM dbo.orders WHERE business_id = ?",
    ],
)
def test_case08b_select_star_queries_are_rejected(query):
    with pytest.raises(PlanError):
        validate_plan(make_plan([make_subject(legacy_query=query)]))


@pytest.mark.parametrize(
    "query",
    [
        "SELECT COUNT(*) AS amount FROM dbo.orders WHERE business_id = ?",
        "SELECT business_id, status, amount * 2 FROM dbo.orders WHERE business_id = ?",
    ],
)
def test_case08c_count_star_and_multiplication_are_allowed(query):
    validated = validate_plan(make_plan([make_subject(legacy_query=query)]))
    assert validated["subjects"][0]["legacy_query"] == query


# --- case 9: max_rows overflow is blocked with no artifact


def test_case09_row_limit_overflow_is_blocked_and_produces_nothing():
    plan = make_plan([make_subject(max_rows=1)])
    with pytest.raises(SnapshotBlocked) as excinfo:
        build(plan, rows=[["B-1", "open", Decimal("1.00")], ["B-2", "sent", Decimal("2.00")]])
    assert excinfo.value.reason_code == "max-rows-exceeded"


# --- case 10: structural delta calculation


def test_case10_structural_delta_added_removed_updated_unchanged():
    before = build(
        rows=[
            ["B-1", "open", Decimal("10.00")],
            ["B-2", "open", Decimal("20.00")],
            ["B-3", "open", Decimal("30.00")],
        ]
    )
    after = build(
        moment="after",
        rows=[
            ["B-1", "sent", Decimal("10.00")],
            ["B-3", "open", Decimal("30.00")],
            ["B-4", "open", Decimal("40.00")],
        ],
    )
    delta = compute_delta(before, after)
    payload = delta["payload"]

    assert payload["format"] == "db-delta"
    assert payload["before_sha256"] == dsd.payload_digest(before["payload"])
    assert payload["after_sha256"] == dsd.payload_digest(after["payload"])

    assert [entry["key"][0]["v"] for entry in payload["added"]] == ["B-4"]
    assert payload["added"][0]["row"][1] == {"t": "text", "v": "open"}
    assert [entry["key"][0]["v"] for entry in payload["removed"]] == ["B-2"]

    updated = payload["updated"]
    assert len(updated) == 1
    assert updated[0]["key"][0]["v"] == "B-1"
    assert updated[0]["changed_columns"] == ["status"]
    assert updated[0]["before"] == [
        {"t": "text", "v": "B-1"},
        {"t": "text", "v": "open"},
        {"t": "decimal", "v": "10.00"},
    ]
    assert updated[0]["after"][1] == {"t": "text", "v": "sent"}

    assert payload["unchanged_count"] == 1


# --- case 11: pairing invariant violations are blocked


@pytest.mark.parametrize(
    "field,value",
    [
        ("feature_id", "other-feature"),
        ("subject_id", "db-002"),
        ("side", "target"),
        ("run_id", "run-2"),
        ("fixture_ref", "fixture-2"),
        ("mode", "state"),
        ("comparison_rule_ref", "behavior-contract.md :: other"),
        ("engine", "postgresql"),
        ("plan_version", 2),
        ("query_digest", "0" * 64),
        ("parameter_names", ["other_id"]),
        ("parameter_digest", "1" * 64),
        ("columns", ["business_id", "status"]),
        ("key_columns", []),
        ("max_rows", 11),
    ],
)
def test_case11_pairing_field_mismatches_are_blocked(field, value):
    before = build()
    after = build(moment="after")
    after["payload"] = dict(after["payload"], **{field: value})
    with pytest.raises(PairingBlocked) as excinfo:
        compute_delta(before, after)
    assert excinfo.value.reason_code == f"pairing-mismatch:{field}"


def test_case11b_moment_inversion_and_non_snapshot_inputs_are_blocked():
    before = build()
    after = build(moment="after")

    with pytest.raises(PairingBlocked) as excinfo:
        compute_delta(after, before)
    assert excinfo.value.reason_code == "moment-order"

    delta = compute_delta(before, after)
    with pytest.raises(PairingBlocked) as excinfo:
        compute_delta(delta, delta)
    assert excinfo.value.reason_code == "not-a-snapshot"


# --- case 12: non-read-only and multi-statement plan queries are rejected


@pytest.mark.parametrize(
    "query",
    [
        "INSERT INTO dbo.orders (business_id) VALUES (?)",
        "UPDATE dbo.orders SET status = 'x' WHERE business_id = ?",
        "DELETE FROM dbo.orders WHERE business_id = ?",
        "SELECT business_id INTO #staged FROM dbo.orders WHERE business_id = ?",
        "CREATE TABLE dbo.orders (business_id INT)",
        "EXEC dbo.fetch_orders ?",
        "SELECT business_id FROM dbo.orders WHERE business_id = ?; "
        "SELECT status FROM dbo.orders WHERE business_id = ?",
    ],
)
def test_case12_non_read_only_plan_queries_are_rejected(query):
    with pytest.raises(PlanError):
        validate_plan(make_plan([make_subject(legacy_query=query)]))


# --- case 13: no raw values in render output, stdout, stderr, or errors


def test_case13_sentinel_never_leaks_into_reports_stdout_stderr_or_errors(tmp_path):
    keyed = f"B-{SENTINEL}"
    before = build(
        parameters={"business_id": keyed},
        rows=[[keyed, f"open-{SENTINEL}", Decimal("10.00")]],
    )
    after = build(
        moment="after",
        parameters={"business_id": keyed},
        rows=[[keyed, f"sent-{SENTINEL}", Decimal("10.00")]],
    )
    delta = compute_delta(before, after)

    markdown = render_markdown([before, after, delta])
    assert SENTINEL not in markdown

    before_path = write_json(tmp_path / "before.json", before)
    after_path = write_json(tmp_path / "after.json", after)

    rendered = cli("render", str(before_path), str(after_path))
    assert rendered.returncode == 0
    assert SENTINEL not in rendered.stdout
    assert SENTINEL not in rendered.stderr

    written = cli(
        "delta", "--before", str(before_path), "--after", str(after_path),
        "--output", str(tmp_path / "delta.json"),
    )
    assert written.returncode == 0
    assert SENTINEL not in written.stdout
    assert SENTINEL not in written.stderr

    other = build(moment="after", run_id="run-2")
    mismatched = write_json(tmp_path / "other.json", other)
    blocked = cli(
        "delta", "--before", str(before_path), "--after", str(mismatched),
        "--output", str(tmp_path / "blocked.json"),
    )
    assert blocked.returncode == 2
    assert SENTINEL not in blocked.stderr

    with pytest.raises(SnapshotBlocked) as excinfo:
        build(
            parameters={"business_id": keyed},
            rows=[[keyed, "open", Decimal("1.00")], [keyed, "sent", Decimal("2.00")]],
        )
    assert SENTINEL not in str(excinfo.value)

    with pytest.raises(PairingBlocked) as excinfo:
        compute_delta(before, other)
    assert SENTINEL not in str(excinfo.value)

    tampered = {
        "content_sha256": before["content_sha256"],
        "payload": dict(before["payload"], row_count=99),
    }
    with pytest.raises(ArtifactError) as excinfo:
        dsd.load_artifact(write_json(tmp_path / "tampered.json", tampered))
    assert SENTINEL not in str(excinfo.value)


# --- case 14: CLI exit codes 0/1/2 and no output file on block


def test_case14_cli_exit_codes_and_no_output_file_on_block(tmp_path):
    before_path = write_json(tmp_path / "before.json", build())
    after_path = write_json(tmp_path / "after.json", build(moment="after"))
    out = tmp_path / "delta.json"

    ok = cli("delta", "--before", str(before_path), "--after", str(after_path), "--output", str(out))
    assert ok.returncode == 0
    assert out.exists()
    envelope = json.loads(out.read_text(encoding="utf-8"))
    assert envelope["payload"]["format"] == "db-delta"

    malformed = tmp_path / "malformed.json"
    malformed.write_text("{not json", encoding="utf-8")
    out_one = tmp_path / "delta-one.json"
    bad_input = cli(
        "delta", "--before", str(malformed), "--after", str(after_path), "--output", str(out_one)
    )
    assert bad_input.returncode == 1
    assert not out_one.exists()

    usage = cli("delta", "--before", str(before_path))
    assert usage.returncode == 1

    incomplete = write_json(tmp_path / "incomplete.json", {"payload": build()["payload"]})
    out_two = tmp_path / "delta-two.json"
    missing = cli(
        "delta", "--before", str(incomplete), "--after", str(after_path), "--output", str(out_two)
    )
    assert missing.returncode == 1
    assert not out_two.exists()

    mismatched = write_json(tmp_path / "mismatched.json", build(moment="after", run_id="run-2"))
    out_three = tmp_path / "delta-three.json"
    blocked = cli(
        "delta", "--before", str(before_path), "--after", str(mismatched), "--output", str(out_three)
    )
    assert blocked.returncode == 2
    assert not out_three.exists()

    rendered = cli("render", str(before_path))
    assert rendered.returncode == 0
    assert "| db-snapshot | db-001 | legacy | before |" in rendered.stdout


# --- case 15: default output path is git-ignored


def test_case15_default_output_path_is_git_ignored(tmp_path):
    before_path = write_json(tmp_path / "before.json", build())
    after_path = write_json(tmp_path / "after.json", build(moment="after"))
    written = cli("delta", "--before", str(before_path), "--after", str(after_path))
    assert written.returncode == 0

    default_path = dsd.default_delta_output_path(build(moment="after")["payload"])
    assert default_path.exists()

    check = subprocess.run(
        ["git", "check-ignore", str(default_path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert check.returncode == 0, check.stderr
    assert check.stdout.strip() == str(default_path)
