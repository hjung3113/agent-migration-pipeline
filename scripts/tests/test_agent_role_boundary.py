"""Static checks for the Issue #8 migration-designer role boundary.

Canonical contract: docs/10-agent-role-boundary.md ("Verification
requirements"). Runtime permission evaluation (expected-ask edit,
expected-deny edits, shell, delegation) can only be exercised inside a
live OpenCode session; these tests statically verify the effective
frontmatter policy and the implementer asymmetry (A-6 rule 6).
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
AGENTS = ROOT / ".opencode" / "agents"

DESIGNER_PATH = "migration/features/*/target-feature-design.md"


def frontmatter(name: str) -> dict:
    text = (AGENTS / name).read_text(encoding="utf-8")
    assert text.startswith("---\n")
    end = text.index("\n---\n", 4)
    return yaml.safe_load(text[4:end])


def test_designer_edit_rules_match_design() -> None:
    fm = frontmatter("migration-designer.md")
    edit = fm["permission"]["edit"]
    assert isinstance(edit, dict)
    # Ordered, last-match-wins: catch-all deny first, narrow ask exception second.
    assert list(edit) == ["*", DESIGNER_PATH]
    assert edit["*"] == "deny"
    assert edit[DESIGNER_PATH] == "ask"


def test_designer_bash_task_skill() -> None:
    fm = frontmatter("migration-designer.md")
    assert fm["permission"]["bash"] == "deny"
    assert fm["permission"]["task"] == "deny"
    assert fm["permission"]["skill"] == "allow"


def test_designer_body_states_write_boundary() -> None:
    text = (AGENTS / "migration-designer.md").read_text(encoding="utf-8")
    assert "only" in text and "direct durable write" in text
    assert "migration-coordinator" in text


def test_implementer_permissions_unchanged() -> None:
    fm = frontmatter("implementer.md")
    assert fm["permission"]["edit"] == "ask"
    assert fm["permission"]["bash"] == "ask"
