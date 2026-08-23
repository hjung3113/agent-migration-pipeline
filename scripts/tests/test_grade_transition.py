"""Revision-aware tests for scripts/validate_grade_transition.py."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.validate_scaffold import ROOT


GIT = shutil.which("git")
CHECKER = ROOT / "scripts/validate_grade_transition.py"
pytestmark = pytest.mark.skipif(GIT is None, reason="git is unavailable")


def run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    assert GIT is not None
    return subprocess.run(
        [GIT, *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def make_repo(tmp_path: Path) -> Path:
    run_git(tmp_path, "init", "-q")
    run_git(tmp_path, "config", "user.email", "issue9@example.test")
    run_git(tmp_path, "config", "user.name", "Issue 9 tests")
    return tmp_path


def record(
    grade: str,
    *history_rows: tuple[str, str, str, str, str],
    include_history: bool = True,
    evidence_body: str = "capture/base-runtime.log",
) -> str:
    text = (
        "# Evidence: ev-001\n\n"
        "- Feature: alpha\n"
        "- Rule/scenario: BR-001\n"
        f"- Grade: {grade}\n"
        "- Captured date: 2026-08-23\n"
        "- Source type: runtime\n\n"
        "## Evidence\n\n"
        f"{evidence_body}\n"
    )
    if include_history:
        text += (
            "\n## Grade history\n\n"
            "| Recorded date | From | To | Reason | Evidence refs |\n"
            "| --- | --- | --- | --- | --- |\n"
        )
        for row in history_rows:
            text += "| " + " | ".join(row) + " |\n"
    return text


def write_record(repo: Path, text: str) -> Path:
    path = repo / "evidence.md"
    path.write_text(text, encoding="utf-8")
    return path


def commit_record(repo: Path, text: str, message: str = "record") -> None:
    write_record(repo, text)
    run_git(repo, "add", "evidence.md")
    run_git(repo, "commit", "-qm", message)


def run_checker(
    repo: Path,
    *files: str,
    base: str = "HEAD",
    head: str | None = None,
) -> subprocess.CompletedProcess[str]:
    args = [sys.executable, str(CHECKER), "--base", base]
    for path in files:
        args.extend(["--file", path])
    if head is not None:
        args.extend(["--head", head])
    return subprocess.run(
        args,
        cwd=repo,
        capture_output=True,
        text=True,
    )


def base_b_record() -> str:
    return record(
        "B",
        ("2026-08-23", "—", "B", "Initial grade", "capture/base-runtime.log"),
    )


def test_missing_base_is_a_hard_cli_error(tmp_path: Path) -> None:
    proc = subprocess.run(
        [sys.executable, str(CHECKER), "--file", "evidence.md"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )

    assert proc.returncode != 0
    assert "--base" in proc.stderr


def test_new_record_can_start_directly_at_its_observed_grade(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    run_git(repo, "commit", "--allow-empty", "-qm", "base")
    write_record(
        repo,
        record(
            "B",
            ("2026-08-23", "—", "B", "Initial runtime observation", "capture/new"),
        ),
    )

    proc = run_checker(repo, "evidence.md")

    assert proc.returncode == 0, proc.stderr


def test_valid_promotion_with_new_evidence_ref_passes(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    commit_record(repo, base_b_record(), "base")
    write_record(
        repo,
        record(
            "A",
            ("2026-08-23", "—", "B", "Initial grade", "capture/base-runtime.log"),
            (
                "2026-08-24",
                "B",
                "A",
                "Independent replay confirms the criterion",
                "capture/independent-replay.log",
            ),
        ),
    )

    proc = run_checker(repo, "evidence.md")

    assert proc.returncode == 0, proc.stderr


def test_promotion_without_a_new_evidence_ref_fails(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    commit_record(repo, base_b_record(), "base")
    write_record(
        repo,
        record(
            "A",
            ("2026-08-23", "—", "B", "Initial grade", "capture/base-runtime.log"),
            (
                "2026-08-24",
                "B",
                "A",
                "Re-read the same evidence",
                "capture/base-runtime.log",
            ),
        ),
    )

    proc = run_checker(repo, "evidence.md")

    assert proc.returncode != 0
    assert "new evidence reference" in proc.stderr


def test_valid_downgrade_with_reason_passes(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    commit_record(repo, base_b_record(), "base")
    write_record(
        repo,
        record(
            "C",
            ("2026-08-23", "—", "B", "Initial grade", "capture/base-runtime.log"),
            (
                "2026-08-24",
                "B",
                "C",
                "Contradictory callback invalidates the direct-observation support",
                "capture/contradiction.json",
            ),
        ),
    )

    proc = run_checker(repo, "evidence.md")

    assert proc.returncode == 0, proc.stderr


def test_unchanged_grade_with_synthetic_history_row_fails(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    commit_record(repo, base_b_record(), "base")
    write_record(
        repo,
        record(
            "B",
            ("2026-08-23", "—", "B", "Initial grade", "capture/base-runtime.log"),
            ("2026-08-24", "B", "B", "No grade change", "capture/new-note"),
        ),
    )

    proc = run_checker(repo, "evidence.md")

    assert proc.returncode != 0
    assert "unchanged grade" in proc.stderr


def test_legacy_record_adopts_a_baseline_before_later_changes(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    legacy = record("B", include_history=False)
    commit_record(repo, legacy, "legacy")
    write_record(
        repo,
        record(
            "B",
            (
                "2026-08-24",
                "—",
                "B",
                "baseline imported at A-7 adoption; prior transition history was not recorded",
                "capture/base-runtime.log",
            ),
        ),
    )

    proc = run_checker(repo, "evidence.md")

    assert proc.returncode == 0, proc.stderr


def test_existing_record_grade_change_requires_an_appended_row(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    commit_record(repo, base_b_record(), "base")
    write_record(repo, base_b_record().replace("- Grade: B", "- Grade: A", 1))

    proc = run_checker(repo, "evidence.md")

    assert proc.returncode != 0
    assert "final history To" in proc.stderr


def test_history_prefix_is_append_only(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    commit_record(repo, base_b_record(), "base")
    write_record(
        repo,
        record(
            "B",
            ("2026-08-23", "—", "B", "Edited old reason", "capture/base-runtime.log"),
        ),
    )

    proc = run_checker(repo, "evidence.md")

    assert proc.returncode != 0
    assert "append-only" in proc.stderr


def test_existing_record_deletion_fails(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    commit_record(repo, base_b_record(), "base")
    (repo / "evidence.md").unlink()

    proc = run_checker(repo, "evidence.md")

    assert proc.returncode != 0
    assert "deleted" in proc.stderr


def test_relabeled_markdown_link_is_not_new_evidence(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    commit_record(
        repo,
        record(
            "C",
            ("2026-08-23", "—", "C", "Initial grade", "[old](capture/same.log)"),
        ),
        "base",
    )
    write_record(
        repo,
        record(
            "B",
            ("2026-08-23", "—", "C", "Initial grade", "[old](capture/same.log)"),
            (
                "2026-08-24",
                "C",
                "B",
                "Relabeled link, same target",
                "[new](capture/same.log)",
            ),
        ),
    )

    proc = run_checker(repo, "evidence.md")

    assert proc.returncode != 0
    assert "missing-evidence" in proc.stderr


def test_relabeled_multiword_markdown_link_label_is_not_new_evidence(
    tmp_path: Path,
) -> None:
    repo = make_repo(tmp_path)
    commit_record(
        repo,
        record(
            "C",
            (
                "2026-08-23",
                "—",
                "C",
                "Initial grade",
                "[old label](capture/same.log)",
            ),
        ),
        "base",
    )
    write_record(
        repo,
        record(
            "B",
            (
                "2026-08-23",
                "—",
                "C",
                "Initial grade",
                "[old label](capture/same.log)",
            ),
            (
                "2026-08-24",
                "C",
                "B",
                "Relabeled link, same target",
                "[new label](capture/same.log)",
            ),
        ),
    )

    proc = run_checker(repo, "evidence.md")

    assert proc.returncode != 0
    assert "missing-evidence" in proc.stderr


def test_same_new_evidence_cannot_be_reused_across_consecutive_promotions(
    tmp_path: Path,
) -> None:
    repo = make_repo(tmp_path)
    commit_record(
        repo,
        record(
            "C",
            ("2026-08-23", "—", "C", "Initial grade", "capture/base.log"),
        ),
        "base",
    )
    write_record(
        repo,
        record(
            "A",
            ("2026-08-23", "—", "C", "Initial grade", "capture/base.log"),
            (
                "2026-08-24",
                "C",
                "B",
                "First promotion",
                "capture/new-runtime.log",
            ),
            (
                "2026-08-25",
                "B",
                "A",
                "Second promotion reuses the same new ref",
                "capture/new-runtime.log",
            ),
        ),
    )

    proc = run_checker(repo, "evidence.md")

    assert proc.returncode != 0
    assert "missing-evidence" in proc.stderr


def test_absolute_file_diagnostic_is_repository_relative(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    commit_record(repo, base_b_record(), "base")
    write_record(
        repo,
        record(
            "B",
            ("2026-08-23", "—", "B", "Initial grade", "capture/base-runtime.log"),
            ("2026-08-24", "B", "B", "No grade change", "capture/new-note"),
        ),
    )

    proc = run_checker(repo, str(repo / "evidence.md"))

    assert proc.returncode != 0
    assert proc.stderr.startswith("evidence.md:")
    assert str(repo) not in proc.stderr
