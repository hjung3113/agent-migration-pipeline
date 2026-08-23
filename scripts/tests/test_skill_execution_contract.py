"""Tests for the Issue #6 skill-execution contract checks."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.validate_scaffold import (
    LEGACY_SINGLETON_ALIASES,
    ROOT,
    SKILL_EXECUTION_CONTRACT_SECTIONS,
    SKILL_EXECUTION_CONTRACT_SKILLS,
    validate_skill_execution_contract,
)

SKILLS_DIR = ".opencode/skills"


def valid_skill_text(name: str) -> str:
    return f"""---
name: {name}
description: Primary skill for the execution contract test.
compatibility: OpenCode project skill
---

# {name}

## Inputs

- [Input] `migration/features/<feature-id>/feature-card.md`.

## Outputs

- [Output] `migration/features/<feature-id>/behavior-contract.md`.

## Procedure

1. [Input] Read `migration/features/<feature-id>/feature-card.md`.
2. [Output] Return the result for `migration/features/<feature-id>/behavior-contract.md`.

## Branches

- If a prerequisite is missing, return `BLOCKED` and do not advance lifecycle state.

## Done means

The canonical result is complete and ready for coordinator persistence.
"""


def make_repo(tmp_path: Path) -> Path:
    for name in SKILL_EXECUTION_CONTRACT_SKILLS:
        skill_dir = tmp_path / SKILLS_DIR / name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            valid_skill_text(name),
            encoding="utf-8",
        )
    return tmp_path


def skill_path(root: Path, name: str = SKILL_EXECUTION_CONTRACT_SKILLS[0]) -> Path:
    return root / SKILLS_DIR / name / "SKILL.md"


def remove_section(text: str, title: str) -> str:
    marker = f"## {title}\n"
    start = text.index(marker)
    next_heading = text.find("\n## ", start + len(marker))
    end = len(text) if next_heading == -1 else next_heading + 1
    return text[:start] + text[end:]


def replace_section_body(text: str, title: str, replacement: str) -> str:
    marker = f"## {title}\n"
    start = text.index(marker) + len(marker)
    next_heading = text.find("\n## ", start)
    end = len(text) if next_heading == -1 else next_heading + 1
    return text[:start] + f"\n{replacement}\n" + text[end:]


def test_valid_skill_execution_contract_passes(tmp_path: Path) -> None:
    assert validate_skill_execution_contract(make_repo(tmp_path)) == []


def test_real_skill_definitions_are_compliant() -> None:
    assert validate_skill_execution_contract(ROOT) == []


def test_evidence_grading_contains_the_grade_change_procedure() -> None:
    path = ROOT / SKILLS_DIR / "evidence-grading" / "SKILL.md"
    text = path.read_text(encoding="utf-8")
    start = text.index("## Grade-change procedure")
    end = text.index("\n## Branches", start)
    section = text[start:end]
    numbered_steps = [
        line for line in section.splitlines() if line[:2] in {f"{n}." for n in range(1, 9)}
    ]

    assert len(numbered_steps) == 8
    assert numbered_steps[0].startswith("1. Identify the claim/scenario")
    assert numbered_steps[-1].startswith("8. Never delete or rewrite past grade decisions")


def test_evidence_grading_preserves_transition_safety_sentences() -> None:
    path = ROOT / SKILLS_DIR / "evidence-grading" / "SKILL.md"
    text = path.read_text(encoding="utf-8").lower()

    assert "unresolved contradictory evidence blocks promotion" in text
    assert "promotion requires newly introduced evidence" in text
    assert "never delete or rewrite past grade decisions" in text


def test_missing_skill_file_is_reported(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    missing = SKILL_EXECUTION_CONTRACT_SKILLS[-1]
    skill_path(root, missing).unlink()

    assert validate_skill_execution_contract(root) == [
        f"{SKILLS_DIR}/{missing}/SKILL.md: skill execution contract file missing "
        "(docs/10-skill-execution-contract.md)",
    ]


@pytest.mark.parametrize("title", SKILL_EXECUTION_CONTRACT_SECTIONS)
def test_missing_required_section_fails(tmp_path: Path, title: str) -> None:
    root = make_repo(tmp_path)
    path = skill_path(root)
    path.write_text(
        remove_section(path.read_text(encoding="utf-8"), title),
        encoding="utf-8",
    )

    errors = validate_skill_execution_contract(root)

    assert errors == [
        f"{SKILLS_DIR}/{SKILL_EXECUTION_CONTRACT_SKILLS[0]}/SKILL.md: "
        f"missing required execution section '## {title}' "
        "(docs/10-skill-execution-contract.md)",
    ]


@pytest.mark.parametrize("title", SKILL_EXECUTION_CONTRACT_SECTIONS)
def test_empty_required_section_fails(tmp_path: Path, title: str) -> None:
    root = make_repo(tmp_path)
    path = skill_path(root)
    path.write_text(
        replace_section_body(path.read_text(encoding="utf-8"), title, ""),
        encoding="utf-8",
    )

    errors = validate_skill_execution_contract(root)

    assert errors == [
        f"{SKILLS_DIR}/{SKILL_EXECUTION_CONTRACT_SKILLS[0]}/SKILL.md: "
        f"execution section '## {title}' is empty "
        "(docs/10-skill-execution-contract.md)",
    ]


def test_required_sections_must_appear_in_relative_order(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    path = skill_path(root)
    text = path.read_text(encoding="utf-8")
    inputs_start = text.index("## Inputs")
    outputs_start = text.index("## Outputs")
    inputs_end = text.index("\n## Outputs", inputs_start) + 1
    outputs_end = text.index("\n## Procedure", outputs_start) + 1
    text = (
        text[:inputs_start]
        + text[outputs_start:outputs_end]
        + text[inputs_start:inputs_end]
        + text[outputs_end:]
    )
    path.write_text(text, encoding="utf-8")

    errors = validate_skill_execution_contract(root)

    assert errors == [
        f"{SKILLS_DIR}/{SKILL_EXECUTION_CONTRACT_SKILLS[0]}/SKILL.md: "
        "execution sections must appear in this order: Inputs, Outputs, "
        "Procedure, Branches, Done means "
        "(docs/10-skill-execution-contract.md)",
    ]


@pytest.mark.parametrize("marker", ("[Input]", "[Output]"))
def test_procedure_requires_input_and_output_markers(
    tmp_path: Path,
    marker: str,
) -> None:
    root = make_repo(tmp_path)
    path = skill_path(root)
    text = path.read_text(encoding="utf-8")
    if marker == "[Input]":
        text = text.replace(
            "1. [Input] Read `migration/features/<feature-id>/feature-card.md`.",
            "1. Read the feature card.",
        )
    else:
        text = text.replace(
            "2. [Output] Return the result for `migration/features/<feature-id>/behavior-contract.md`.",
            "2. Return the result.",
        )
    path.write_text(text, encoding="utf-8")

    errors = validate_skill_execution_contract(root)

    assert errors == [
        f"{SKILLS_DIR}/{SKILL_EXECUTION_CONTRACT_SKILLS[0]}/SKILL.md: "
        f"'## Procedure' must contain at least one {marker} marker "
        "(docs/10-skill-execution-contract.md)",
    ]


def test_feature_placeholder_must_be_feature_id(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    path = skill_path(root)
    text = path.read_text(encoding="utf-8").replace(
        "migration/features/<feature-id>/behavior-contract.md",
        "migration/features/<feature>/behavior-contract.md",
        1,
    )
    path.write_text(text, encoding="utf-8")

    errors = validate_skill_execution_contract(root)

    assert len(errors) == 1
    assert "feature artifact path uses '<feature>'; expected '<feature-id>'" in errors[0]


def test_noncanonical_feature_artifact_fails(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    path = skill_path(root)
    text = path.read_text(encoding="utf-8").replace(
        "migration/features/<feature-id>/behavior-contract.md",
        "migration/features/<feature-id>/behaviour-contract.md",
        1,
    )
    path.write_text(text, encoding="utf-8")

    errors = validate_skill_execution_contract(root)

    assert len(errors) == 1
    assert "feature artifact reference 'behaviour-contract.md' is not canonical" in errors[0]


def test_legacy_feature_alias_fails(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    path = skill_path(root)
    alias, canonical = next(iter(LEGACY_SINGLETON_ALIASES.items()))
    text = path.read_text(encoding="utf-8").replace(
        "migration/features/<feature-id>/behavior-contract.md",
        f"migration/features/<feature-id>/{alias}",
    )
    path.write_text(text, encoding="utf-8")

    errors = validate_skill_execution_contract(root)

    assert errors == [
        f"{SKILLS_DIR}/{SKILL_EXECUTION_CONTRACT_SKILLS[0]}/SKILL.md: "
        f"non-canonical feature artifact reference '{alias}'; use '{canonical}' "
        "(docs/08-feature-artifact-validation.md)",
    ]


def test_branches_require_blocked_or_partial(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    path = skill_path(root)
    path.write_text(
        replace_section_body(
            path.read_text(encoding="utf-8"),
            "Branches",
            "- If a prerequisite is missing, stop and report the gap.",
        ),
        encoding="utf-8",
    )

    errors = validate_skill_execution_contract(root)

    assert errors == [
        f"{SKILLS_DIR}/{SKILL_EXECUTION_CONTRACT_SKILLS[0]}/SKILL.md: "
        "'## Branches' must mention BLOCKED or PARTIAL "
        "(docs/10-skill-execution-contract.md)",
    ]
