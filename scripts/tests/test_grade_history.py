"""Tests for the Issue #9 evidence-record grade-history invariants."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.validate_scaffold import validate_evidence_record


HISTORY_HEADER = "| Recorded date | From | To | Reason | Evidence refs |\n"
HISTORY_SEPARATOR = "| --- | --- | --- | --- | --- |\n"


def record_text(
    *,
    grade: str = "B",
    history: str | None = None,
    header_grade: str | None = None,
) -> str:
    current_grade = grade if header_grade is None else header_grade
    body = (
        "# Evidence: ev-001\n\n"
        "- Feature: alpha\n"
        "- Rule/scenario: BR-001\n"
        f"- Grade: {current_grade}\n"
        "- Captured date: 2026-08-23\n"
        "- Source type: runtime\n"
    )
    if history is not None:
        body += "\n## Grade history\n\n" + history
    return body


def history_row(
    recorded_date: str = "2026-08-23",
    from_grade: str = "—",
    to_grade: str = "B",
    reason: str = "Initial grade from direct runtime observation",
    refs: str = "capture/runtime-001",
) -> str:
    return f"| {recorded_date} | {from_grade} | {to_grade} | {reason} | {refs} |\n"


def history_table(*rows: str, header: str = HISTORY_HEADER) -> str:
    return header + HISTORY_SEPARATOR + "".join(rows)


def validate_record(tmp_path: Path, text: str) -> list[str]:
    path = tmp_path / "record.md"
    path.write_text(text, encoding="utf-8")
    errors: list[str] = []
    validate_evidence_record(path, "record.md", "ev-001", 1, {}, errors)
    return errors


@pytest.mark.parametrize("grade", ["?", "D", "C", "B", "A"])
def test_each_valid_grade_can_be_initialised_directly(
    tmp_path: Path, grade: str
) -> None:
    refs = "" if grade == "?" else "capture/runtime-001"
    errors = validate_record(
        tmp_path,
        record_text(
            grade=grade,
            history=history_table(history_row(to_grade=grade, refs=refs)),
        ),
    )

    assert errors == []


def test_history_is_required(tmp_path: Path) -> None:
    errors = validate_record(tmp_path, record_text(history=None))

    assert any("[missing-history]" in error for error in errors)


def test_history_header_must_use_fixed_columns(tmp_path: Path) -> None:
    history = history_table(
        history_row(),
        header="| Date | From | To | Reason | Evidence refs |\n",
    )

    errors = validate_record(tmp_path, record_text(history=history))

    assert any("[invalid-schema]" in error for error in errors)


def test_initial_row_must_use_em_dash_from(tmp_path: Path) -> None:
    history = history_table(history_row(from_grade="?"))

    errors = validate_record(tmp_path, record_text(history=history))

    assert any("initial row From must be `—`" in error for error in errors)


def test_history_grade_values_must_use_the_grade_enum(tmp_path: Path) -> None:
    history = history_table(history_row(to_grade="B+"))

    errors = validate_record(tmp_path, record_text(history=history))

    assert any("[invalid-enum]" in error for error in errors)


def test_history_rows_must_form_a_continuous_chain(tmp_path: Path) -> None:
    history = history_table(
        history_row(to_grade="C", refs="capture/source-001"),
        history_row(from_grade="B", to_grade="B", refs="capture/source-002"),
    )

    errors = validate_record(tmp_path, record_text(grade="B", history=history))

    assert any("history chain is broken" in error for error in errors)


def test_current_grade_must_match_last_history_to(tmp_path: Path) -> None:
    history = history_table(history_row(to_grade="C", refs="capture/source-001"))

    errors = validate_record(tmp_path, record_text(grade="B", history=history))

    assert any("Grade" in error and "final history To" in error for error in errors)


def test_grade_is_required_when_history_exists(tmp_path: Path) -> None:
    history = history_table(history_row(to_grade="B"))

    errors = validate_record(
        tmp_path,
        record_text(grade="B", header_grade="", history=history),
    )

    assert any("Grade is required when grade history exists" in error for error in errors)


def test_every_history_row_requires_a_reason(tmp_path: Path) -> None:
    history = history_table(history_row(reason=""))

    errors = validate_record(tmp_path, record_text(history=history))

    assert any("Reason must not be empty" in error for error in errors)


def test_initial_unknown_grade_may_omit_evidence_refs(tmp_path: Path) -> None:
    history = history_table(history_row(to_grade="?", refs=""))

    assert validate_record(tmp_path, record_text(grade="?", history=history)) == []


def test_non_unknown_initial_and_later_rows_require_evidence_refs(
    tmp_path: Path,
) -> None:
    initial = history_row(to_grade="B", refs="")
    later = history_row(
        from_grade="B", to_grade="A", refs="", reason="Stronger independent evidence"
    )

    errors = validate_record(
        tmp_path,
        record_text(
            grade="A",
            history=history_table(initial, later),
        ),
    )

    assert sum("Evidence refs must not be empty" in error for error in errors) == 2


def test_recorded_date_uses_iso_calendar_date_shape(tmp_path: Path) -> None:
    history = history_table(history_row(recorded_date="23-08-2026"))

    errors = validate_record(tmp_path, record_text(history=history))

    assert any("Recorded date must use YYYY-MM-DD" in error for error in errors)
