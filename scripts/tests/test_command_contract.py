"""Tests for the Issue #5 command-execution contract check."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.validate_scaffold import (
    COMMAND_CONTRACT_FILES,
    COMMAND_CONTRACT_SECTIONS,
    ROOT,
    collect_validation_errors,
    validate_command_contract,
)

COMMANDS_DIR = ".opencode/commands"

CANONICAL_PATHS = (
    "migration/features/<feature-id>/feature-card.md",
    "migration/features/<feature-id>/legacy-map.md",
    "migration/features/<feature-id>/behavior-contract.md",
    "migration/features/<feature-id>/target-feature-design.md",
    "migration/features/<feature-id>/review.md",
    "migration/features/<feature-id>/verification.md",
)


def make_repo(tmp_path: Path) -> Path:
    commands = tmp_path / COMMANDS_DIR
    commands.mkdir(parents=True)
    sections = "\n\n".join(
        f"## {title}\n\nThe {title.lower()} contract."
        for title in COMMAND_CONTRACT_SECTIONS
    )
    valid_text = sections + "\n\n" + "\n".join(
        f"`{path}`" for path in CANONICAL_PATHS
    )
    for filename in COMMAND_CONTRACT_FILES:
        (commands / filename).write_text(valid_text, encoding="utf-8")
    return tmp_path


def test_valid_command_contract_passes(tmp_path: Path) -> None:
    root = make_repo(tmp_path)

    assert validate_command_contract(root) == []


@pytest.mark.parametrize("title", COMMAND_CONTRACT_SECTIONS)
def test_missing_contract_section_fails(tmp_path: Path, title: str) -> None:
    root = make_repo(tmp_path)
    path = root / COMMANDS_DIR / COMMAND_CONTRACT_FILES[0]
    text = path.read_text(encoding="utf-8")
    marker = f"## {title}\n"
    start = text.index(marker)
    next_heading = text.find("\n## ", start + len(marker))
    end = len(text) if next_heading == -1 else next_heading + 1
    path.write_text(text[:start] + text[end:], encoding="utf-8")

    errors = validate_command_contract(root)

    assert errors == [
        f"{COMMANDS_DIR}/{COMMAND_CONTRACT_FILES[0]}: missing required "
        f"command contract section '## {title}' "
        "(docs/10-command-execution-contract.md)"
    ]


def test_missing_command_file_is_reported(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    missing = COMMAND_CONTRACT_FILES[-1]
    (root / COMMANDS_DIR / missing).unlink()

    assert validate_command_contract(root) == [
        f"{COMMANDS_DIR}/{missing}: command contract file missing",
    ]


def test_legacy_artifact_reference_fails(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    path = root / COMMANDS_DIR / COMMAND_CONTRACT_FILES[0]
    text = path.read_text(encoding="utf-8").replace(
        "migration/features/<feature-id>/verification.md",
        "migration/features/<feature-id>/verification-report.md",
    )
    path.write_text(text, encoding="utf-8")

    errors = validate_command_contract(root)

    assert len(errors) == 1
    assert "non-canonical feature artifact reference 'verification-report.md'" in errors[0]


def test_noncanonical_feature_placeholder_fails(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    path = root / COMMANDS_DIR / COMMAND_CONTRACT_FILES[0]
    text = path.read_text(encoding="utf-8").replace(
        "migration/features/<feature-id>/feature-card.md",
        "migration/features/<feature>/feature-card.md",
    )
    path.write_text(text, encoding="utf-8")

    errors = validate_command_contract(root)

    assert len(errors) == 1
    assert "feature artifact path uses '<feature>'; expected '<feature-id>'" in errors[0]


def test_real_command_contract_is_compliant() -> None:
    assert validate_command_contract(ROOT) == []


def test_collect_validation_errors_includes_command_contract_check(
    tmp_path: Path,
) -> None:
    root = make_repo(tmp_path)
    path = root / COMMANDS_DIR / COMMAND_CONTRACT_FILES[0]
    text = path.read_text(encoding="utf-8").replace("## Arguments\n", "")
    path.write_text(text, encoding="utf-8")

    errors = collect_validation_errors(root)

    assert any(
        f"{COMMANDS_DIR}/{COMMAND_CONTRACT_FILES[0]}: missing required "
        "command contract section '## Arguments'" in error
        for error in errors
    )
