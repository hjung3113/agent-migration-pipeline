"""Content contracts for the mandatory judge self-check operating seam."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILL_PATH = ROOT / ".opencode/skills/parity-verification/SKILL.md"
VERIFIER_PATH = ROOT / ".opencode/agents/verifier.md"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_operating_files_do_not_reintroduce_optional_self_check_hedge() -> None:
    for path in (SKILL_PATH, VERIFIER_PATH):
        assert "where practical" not in _text(path).lower(), path


def test_operating_files_require_the_canonical_negative_control_contract() -> None:
    required_terms = (
        "mandatory",
        "negative-control",
        "judge self-check",
        "safe isolated",
        "decision-relevant detector",
        "known-wrong mutation",
        "declared comparison semantics",
        "self-check `blocked`",
        "self-check `fail`",
        "overall verification `blocked`",
        "nominal parity",
        "effective judge configuration",
        "fingerprint",
        "prior self-check",
        "identical",
        "cited",
        "expected and actual detector results",
        "evidence or reuse reference",
        "there is no waiver",
        "docs/03-evidence-and-verification.md",
        "docs/templates/verification.md",
        "migration/rulebook.md",
    )
    for path in (SKILL_PATH, VERIFIER_PATH):
        content = _text(path).lower()
        missing = [term for term in required_terms if term not in content]
        assert not missing, f"{path}: missing {missing}"


def test_parity_skill_execution_and_routing_structure_remains_intact() -> None:
    content = _text(SKILL_PATH)
    headings = re.findall(r"^## (.+)$", content, flags=re.MULTILINE)
    required_order = ["Inputs", "Outputs", "Procedure", "Branches", "Done means"]
    positions = [headings.index(title) for title in required_order]
    assert positions == sorted(positions)
    assert "## Primary artifact boundary" in content
    assert "## Skill tie-break" in content
    assert "[Input]" in content
    assert "[Output]" in content
    assert "BLOCKED" in content
    assert "PARTIAL" in content
    assert "## Judge inputs and rules" in content
    assert re.search(r"^7\. .*mandatory judge self-check", content, flags=re.MULTILINE)


def test_verifier_routing_stop_and_persistence_delegation_remain_intact() -> None:
    content = _text(VERIFIER_PATH)
    for heading in (
        "## Invoke when",
        "## Do not invoke for",
        "## Primary output ownership",
        "## Artifact contract",
        "## Procedure",
        "## Stop handling",
        "## Stop conditions",
        "## Escalation",
    ):
        assert heading in content
    assert "**[Input]**" in content
    assert "**[Output]**" in content
    assert "migration-coordinator" in content
    assert "common 12-field STOP payload" in content
    assert "shared-state persistence and routing remain" in content
    assert "coordinator-owned" in content
    assert re.search(
        r"^3\. \*\*\[Input\]\*\* .*mandatory .*self-check",
        content,
        flags=re.MULTILINE,
    )
