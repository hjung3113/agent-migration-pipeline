#!/usr/bin/env python3
"""Check evidence-grade transitions between an explicit base and candidate.

The scaffold validator checks one record state.  This entry point deliberately
requires ``--base`` so promotion checks never infer a comparison revision.
Without ``--head`` the candidate is read from the working tree.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    from scripts.validate_scaffold import (
        EVIDENCE_H1_RE,
        GRADE_HISTORY_COLUMNS,
        GRADES,
        ISO_DATE_RE,
        _err,
        _parse_kv,
        _parse_tables,
        _split_sections,
        _unique_fields,
        _visible_lines,
    )
except ModuleNotFoundError:  # direct ``python3 scripts/validate_grade_transition.py``
    from validate_scaffold import (
        EVIDENCE_H1_RE,
        GRADE_HISTORY_COLUMNS,
        GRADES,
        ISO_DATE_RE,
        _err,
        _parse_kv,
        _parse_tables,
        _split_sections,
        _unique_fields,
        _visible_lines,
    )


GRADE_ORDER = {grade: index for index, grade in enumerate(("?", "D", "C", "B", "A"))}
REF_TOKEN_SPLIT_RE = re.compile(r"[\s,;]+")


@dataclass(frozen=True)
class GradeRow:
    lineno: int
    recorded_date: str
    from_grade: str
    to_grade: str
    reason: str
    evidence_refs: str


@dataclass(frozen=True)
class EvidenceRecord:
    record_id: str
    grade: str | None
    grade_lineno: int
    history: tuple[GradeRow, ...] | None
    errors: tuple[str, ...]


def _record_error(path: str, lineno: int, category: str, message: str) -> str:
    return _err(path, lineno, category, message)


def _parse_history(
    path: str,
    sections: list[tuple[str, list[tuple[int, str]]]],
    grade: str | None,
    grade_lineno: int,
    *,
    require_history: bool,
) -> tuple[tuple[GradeRow, ...] | None, list[str]]:
    errors: list[str] = []
    history_sections = [
        section_lines
        for title, section_lines in sections
        if title == "grade history"
    ]
    if not history_sections:
        if require_history:
            errors.append(
                _record_error(
                    path,
                    grade_lineno,
                    "missing-history",
                    "evidence record must contain a `## Grade history` section",
                )
            )
        return None, errors
    if len(history_sections) > 1:
        errors.append(
            _record_error(
                path,
                history_sections[1][0][0] if history_sections[1] else grade_lineno,
                "invalid-schema",
                "evidence record must contain only one `## Grade history` section",
            )
        )

    history_lines = history_sections[0]
    tables = list(_parse_tables(history_lines))
    if not tables:
        errors.append(
            _record_error(
                path,
                history_lines[0][0] if history_lines else grade_lineno,
                "invalid-schema",
                "`## Grade history` must contain a Markdown table",
            )
        )
        return None, errors

    header_lineno, headers, rows = tables[0]
    if len(tables) > 1:
        errors.append(
            _record_error(
                path,
                tables[1][0],
                "invalid-schema",
                "`## Grade history` must contain exactly one Markdown table",
            )
        )
    expected_headers = list(GRADE_HISTORY_COLUMNS)
    if headers != expected_headers:
        errors.append(
            _record_error(
                path,
                header_lineno,
                "invalid-schema",
                "grade history columns must be exactly "
                + " | ".join(expected_headers),
            )
        )
    if not rows:
        errors.append(
            _record_error(
                path,
                header_lineno,
                "missing-history",
                "grade history must contain at least one decision row",
            )
        )
        return None, errors

    parsed_rows: list[GradeRow] = []
    previous_to: str | None = None
    final_to: str | None = None
    for index, (row_lineno, original_cells) in enumerate(rows):
        cells = list(original_cells)
        if len(cells) != len(GRADE_HISTORY_COLUMNS):
            errors.append(
                _record_error(
                    path,
                    row_lineno,
                    "invalid-schema",
                    "grade history rows must contain exactly five cells",
                )
            )
            cells.extend([""] * (len(GRADE_HISTORY_COLUMNS) - len(cells)))
            cells = cells[: len(GRADE_HISTORY_COLUMNS)]

        recorded_date, from_grade, to_grade, reason, evidence_refs = cells
        parsed_rows.append(
            GradeRow(
                row_lineno,
                recorded_date,
                from_grade,
                to_grade,
                reason,
                evidence_refs,
            )
        )

        if not ISO_DATE_RE.fullmatch(recorded_date):
            errors.append(
                _record_error(
                    path,
                    row_lineno,
                    "invalid-format",
                    "Recorded date must use YYYY-MM-DD",
                )
            )

        if index == 0:
            if from_grade != "—":
                errors.append(
                    _record_error(
                        path,
                        row_lineno,
                        "invalid-invariant",
                        "initial row From must be `—`",
                    )
                )
        elif from_grade not in GRADES:
            errors.append(
                _record_error(
                    path,
                    row_lineno,
                    "invalid-enum",
                    f"history From `{from_grade}`; expected A|B|C|D|?",
                )
            )
        elif previous_to is not None and from_grade != previous_to:
            errors.append(
                _record_error(
                    path,
                    row_lineno,
                    "invalid-invariant",
                    "history chain is broken: From must equal the preceding row's To",
                )
            )

        if to_grade not in GRADES:
            errors.append(
                _record_error(
                    path,
                    row_lineno,
                    "invalid-enum",
                    f"history To `{to_grade}`; expected A|B|C|D|?",
                )
            )
        else:
            final_to = to_grade
            previous_to = to_grade

        if not reason:
            errors.append(
                _record_error(
                    path,
                    row_lineno,
                    "invalid-invariant",
                    "Reason must not be empty in grade history",
                )
            )
        if not evidence_refs and not (index == 0 and to_grade == "?"):
            errors.append(
                _record_error(
                    path,
                    row_lineno,
                    "invalid-invariant",
                    "Evidence refs must not be empty for this grade decision",
                )
            )

    if grade is None or not grade:
        errors.append(
            _record_error(
                path,
                grade_lineno,
                "missing-field",
                "Grade is required when grade history exists",
            )
        )
    elif final_to is not None and grade in GRADES and grade != final_to:
        errors.append(
            _record_error(
                path,
                grade_lineno,
                "invalid-invariant",
                f"Grade `{grade}` must equal the final history To `{final_to}`",
            )
        )

    return tuple(parsed_rows), errors


def _parse_record(path: str, text: str, *, require_history: bool) -> EvidenceRecord:
    lines = list(_visible_lines(text))
    errors: list[str] = []
    first_h1 = next(((lineno, line[2:].strip()) for lineno, line in lines if line.startswith("# ")), None)
    if first_h1 is None:
        errors.append(
            _record_error(path, 1, "invalid-record", "expected `# Evidence: <ID>` H1")
        )
        return EvidenceRecord("", None, 1, None, tuple(errors))

    id_lineno, title = first_h1
    evidence_match = EVIDENCE_H1_RE.fullmatch(title)
    if evidence_match is None:
        errors.append(
            _record_error(path, id_lineno, "invalid-record", "expected `# Evidence: <ID>` H1")
        )
        record_id = ""
    else:
        record_id = evidence_match.group(1).strip()
        if not record_id:
            errors.append(
                _record_error(
                    path,
                    id_lineno,
                    "invalid-id",
                    "empty record ID; expected `# Evidence: <ID>`",
                )
            )

    header, sections = _split_sections(lines)
    seen, duplicates = _unique_fields(_parse_kv(header))
    for lineno, key in duplicates:
        errors.append(
            _record_error(path, lineno, "duplicate-key", f"duplicate field `{key}` in record header")
        )
    grade_field = seen.get("Grade")
    grade = grade_field[1] if grade_field else None
    grade_lineno = grade_field[0] if grade_field else id_lineno
    if grade and grade not in GRADES:
        errors.append(
            _record_error(
                path,
                grade_lineno,
                "invalid-enum",
                f"Grade `{grade}`; expected A|B|C|D|?",
            )
        )
    if not require_history and (grade is None or not grade):
        errors.append(
            _record_error(
                path,
                grade_lineno,
                "missing-field",
                "base evidence record must have a Grade for transition comparison",
            )
        )

    history, history_errors = _parse_history(
        path,
        sections,
        grade,
        grade_lineno,
        require_history=require_history,
    )
    errors.extend(history_errors)
    return EvidenceRecord(record_id, grade, grade_lineno, history, tuple(errors))


def _evidence_ref_tokens(value: str) -> list[str]:
    return [token.strip("`<>[]()") for token in REF_TOKEN_SPLIT_RE.split(value) if token]


def _row_values(row: GradeRow) -> tuple[str, str, str, str, str]:
    return (
        row.recorded_date,
        row.from_grade,
        row.to_grade,
        row.reason,
        row.evidence_refs,
    )


def _check_existing_transition(
    path: str,
    base_text: str,
    base_record: EvidenceRecord,
    candidate_record: EvidenceRecord,
) -> list[str]:
    errors: list[str] = []
    if base_record.record_id != candidate_record.record_id:
        errors.append(
            _record_error(
                path,
                candidate_record.grade_lineno,
                "record-identity",
                "evidence record ID must remain stable across revisions",
            )
        )
    if base_record.grade not in GRADES or candidate_record.grade not in GRADES:
        return errors

    candidate_history = candidate_record.history
    if candidate_history is None:
        return errors

    if base_record.history is None:
        first = candidate_history[0]
        if first.from_grade != "—" or first.to_grade != base_record.grade:
            errors.append(
                _record_error(
                    path,
                    first.lineno,
                    "adoption-baseline",
                    "legacy record adoption must begin with `— -> <base Grade>`",
                )
            )
        base_history_length = 1
    else:
        base_history = base_record.history
        prefix_matches = len(candidate_history) >= len(base_history) and all(
            _row_values(candidate_row) == _row_values(base_row)
            for candidate_row, base_row in zip(
                candidate_history[: len(base_history)], base_history
            )
        )
        if not prefix_matches:
            errors.append(
                _record_error(
                    path,
                    candidate_history[0].lineno,
                    "append-only",
                    "candidate grade history must preserve the base history as an append-only prefix",
                )
            )
        base_history_length = len(base_history)

    appended = candidate_history[base_history_length:]
    if candidate_record.grade != base_record.grade and not appended:
        errors.append(
            _record_error(
                path,
                candidate_record.grade_lineno,
                "missing-transition",
                "grade change requires an appended history transition",
            )
        )
        return errors

    if not appended:
        return errors

    previous_grade = base_record.grade
    for row in appended:
        if row.from_grade != previous_grade:
            errors.append(
                _record_error(
                    path,
                    row.lineno,
                    "missing-transition",
                    "appended history transition must start at the prior grade",
                )
            )
        if row.from_grade == row.to_grade:
            errors.append(
                _record_error(
                    path,
                    row.lineno,
                    "synthetic-transition",
                    "an unchanged grade must not append a synthetic history row",
                )
            )
        elif row.from_grade in GRADE_ORDER and row.to_grade in GRADE_ORDER:
            if GRADE_ORDER[row.to_grade] > GRADE_ORDER[row.from_grade]:
                new_refs = [
                    token
                    for token in _evidence_ref_tokens(row.evidence_refs)
                    if token and token not in base_text
                ]
                if not new_refs:
                    errors.append(
                        _record_error(
                            path,
                            row.lineno,
                            "missing-evidence",
                            "promotion requires at least one new evidence reference "
                            "not present in the base revision",
                        )
                    )
        if row.to_grade in GRADES:
            previous_grade = row.to_grade

    return errors


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
    )


def _repo_root() -> tuple[Path | None, str | None]:
    proc = _git(Path.cwd(), "rev-parse", "--show-toplevel")
    if proc.returncode != 0:
        return None, proc.stderr.strip() or "not inside a Git repository"
    return Path(proc.stdout.strip()), None


def _git_path(path_arg: str, repo: Path) -> tuple[str | None, str | None]:
    supplied = Path(path_arg)
    absolute = supplied if supplied.is_absolute() else Path.cwd() / supplied
    try:
        relative = absolute.resolve().relative_to(repo.resolve())
    except ValueError:
        return None, "file path must be inside the Git repository"
    return relative.as_posix(), None


def _revision_file(repo: Path, ref: str, path: str) -> tuple[str | None, bool, str | None]:
    exists = _git(repo, "cat-file", "-e", f"{ref}:{path}")
    if exists.returncode != 0:
        return None, False, None
    shown = _git(repo, "show", f"{ref}:{path}")
    if shown.returncode != 0:
        return None, True, shown.stderr.strip() or "unable to read Git revision"
    return shown.stdout, True, None


def _validate_ref(repo: Path, ref: str) -> str | None:
    proc = _git(repo, "rev-parse", "--verify", f"{ref}^{{commit}}")
    return None if proc.returncode == 0 else (proc.stderr.strip() or f"unknown revision `{ref}`")


def _check_file(repo: Path, base_ref: str, head_ref: str | None, path_arg: str) -> list[str]:
    display_path = Path(path_arg).as_posix()
    git_path, path_error = _git_path(path_arg, repo)
    if path_error or git_path is None:
        return [_record_error(display_path, 1, "invalid-path", path_error or "invalid file path")]

    base_text, base_exists, base_error = _revision_file(repo, base_ref, git_path)
    if base_error:
        return [_record_error(display_path, 1, "git", base_error)]

    if head_ref is None:
        candidate_path = Path(path_arg)
        if not candidate_path.is_absolute():
            candidate_path = Path.cwd() / candidate_path
        if candidate_path.is_file():
            candidate_text = candidate_path.read_text(encoding="utf-8")
        else:
            candidate_text = None
    else:
        candidate_text, candidate_exists, candidate_error = _revision_file(
            repo, head_ref, git_path
        )
        if candidate_error:
            return [_record_error(display_path, 1, "git", candidate_error)]
        if not candidate_exists:
            candidate_text = None

    if base_exists and candidate_text is None:
        return [
            _record_error(
                display_path,
                1,
                "deleted-record",
                "existing evidence record was deleted between revisions",
            )
        ]
    if candidate_text is None:
        return [
            _record_error(
                display_path,
                1,
                "missing-record",
                "candidate evidence record does not exist",
            )
        ]

    candidate_record = _parse_record(display_path, candidate_text, require_history=True)
    errors = list(candidate_record.errors)
    if not base_exists:
        return errors

    assert base_text is not None
    base_record = _parse_record(display_path, base_text, require_history=False)
    errors.extend(base_record.errors)
    if base_record.errors or candidate_record.errors:
        return errors
    errors.extend(
        _check_existing_transition(
            display_path, base_text, base_record, candidate_record
        )
    )
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate evidence-grade history transitions against an explicit Git base."
    )
    parser.add_argument(
        "--base",
        required=True,
        help="Git revision containing the prior evidence record",
    )
    parser.add_argument(
        "--file",
        action="append",
        required=True,
        dest="files",
        help="Evidence-record path to validate; repeat for multiple files",
    )
    parser.add_argument(
        "--head",
        help="Git revision for the candidate (defaults to the working tree)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo, repo_error = _repo_root()
    if repo is None:
        print(_record_error(".", 1, "git", repo_error or "not inside a Git repository"), file=sys.stderr)
        return 1

    base_error = _validate_ref(repo, args.base)
    if base_error:
        for path in args.files:
            print(_record_error(Path(path).as_posix(), 1, "git", base_error), file=sys.stderr)
        return 1
    if args.head:
        head_error = _validate_ref(repo, args.head)
        if head_error:
            for path in args.files:
                print(_record_error(Path(path).as_posix(), 1, "git", head_error), file=sys.stderr)
            return 1

    errors: list[str] = []
    for path in args.files:
        errors.extend(_check_file(repo, args.base, args.head, path))
    for error in errors:
        print(error, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
