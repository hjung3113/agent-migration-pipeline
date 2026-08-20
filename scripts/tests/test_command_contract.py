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

ARGUMENT_GRAMMARS = {
    "migration-discover.md": "--queue <queue-id> --scope <legacy-scope> [--feature <feature-id>]",
    "migration-spec.md": "--queue <queue-id> --feature <feature-id>",
    "migration-design.md": "--queue <queue-id> --feature <feature-id>",
    "migration-implement.md": "--queue <queue-id> --feature <feature-id>",
    "migration-review.md": "--queue <queue-id> --feature <feature-id>",
    "migration-verify.md": "--queue <queue-id> --feature <feature-id>",
    "migration-status.md": "(empty $ARGUMENTS)",
}


def make_repo(tmp_path: Path) -> Path:
    commands = tmp_path / COMMANDS_DIR
    commands.mkdir(parents=True)
    for filename in COMMAND_CONTRACT_FILES:
        section_bodies = {
            title: f"The {title.lower()} contract."
            for title in COMMAND_CONTRACT_SECTIONS
        }
        section_bodies["Arguments"] = (
            "```text\n"
            f"{ARGUMENT_GRAMMARS[filename]}\n"
            "```"
        )
        if filename == "migration-status.md":
            section_bodies["State updates"] = (
                "None. migration-status never mutates migration/STATE.md, "
                "migration/QUEUE.md, feature-card.md, or the OQ registry."
            )
        sections = "\n\n".join(
            f"## {title}\n\n{section_bodies[title]}"
            for title in COMMAND_CONTRACT_SECTIONS
        )
        valid_text = sections + "\n\n" + "\n".join(
            f"`{path}`" for path in CANONICAL_PATHS
        )
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


def test_noncanonical_feature_artifact_name_fails(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    path = root / COMMANDS_DIR / COMMAND_CONTRACT_FILES[0]
    text = path.read_text(encoding="utf-8").replace(
        "migration/features/<feature-id>/behavior-contract.md",
        "migration/features/<feature-id>/behaviour-contract.md",
    )
    path.write_text(text, encoding="utf-8")

    errors = validate_command_contract(root)

    assert errors == [
        f"{COMMANDS_DIR}/{COMMAND_CONTRACT_FILES[0]}: feature artifact "
        "reference 'behaviour-contract.md' is not a canonical singleton name "
        "(docs/08-feature-artifact-validation.md)"
    ]


def test_status_argument_flag_fails(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    path = root / COMMANDS_DIR / "migration-status.md"
    text = path.read_text(encoding="utf-8").replace(
        "(empty $ARGUMENTS)",
        "--feature <feature-id>",
    )
    path.write_text(text, encoding="utf-8")

    errors = validate_command_contract(root)

    assert any(
        "migration-status must accept no arguments" in error for error in errors
    )


def test_status_mutating_state_updates_fail(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    path = root / COMMANDS_DIR / "migration-status.md"
    text = path.read_text(encoding="utf-8").replace(
        "None. migration-status never mutates",
        "The command writes",
    )
    path.write_text(text, encoding="utf-8")

    errors = validate_command_contract(root)

    assert any(
        "State updates" in error and "never mutates" in error for error in errors
    )


def test_queue_argument_is_required_for_queue_commands(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    path = root / COMMANDS_DIR / "migration-spec.md"
    text = path.read_text(encoding="utf-8").replace(
        "--queue <queue-id> --feature <feature-id>",
        "--feature <feature-id>",
    )
    path.write_text(text, encoding="utf-8")

    errors = validate_command_contract(root)

    assert any("must require '--queue <queue-id>'" in error for error in errors)


def test_feature_argument_is_required_and_not_bracketed(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    path = root / COMMANDS_DIR / "migration-review.md"
    text = path.read_text(encoding="utf-8").replace(
        "--queue <queue-id> --feature <feature-id>",
        "--queue <queue-id> [--feature <feature-id>]",
    )
    path.write_text(text, encoding="utf-8")

    errors = validate_command_contract(root)

    assert any("must require '--feature <feature-id>'" in error for error in errors)


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
