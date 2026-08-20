"""Checks for the Issue #8 migration-designer role boundary.

Canonical contract: docs/10-agent-role-boundary.md ("Verification
requirements"). The static tests parse the agent frontmatter directly (no
external YAML dependency — the parser below handles only the flat/one-level
`permission:` shape actually used in this repo's agent files). The runtime
tests shell out to `opencode debug agent <name>`, which resolves the same
ordered, last-match-wins permission list the real OpenCode permission
evaluator uses, and are skipped when the `opencode` CLI is unavailable.
"""

from __future__ import annotations

import fnmatch
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
AGENTS = ROOT / ".opencode" / "agents"

DESIGNER_PATH = "migration/features/*/target-feature-design.md"

OPENCODE = shutil.which("opencode")
skip_if_no_opencode = pytest.mark.skipif(
    OPENCODE is None, reason="opencode CLI not on PATH; cannot exercise the live permission evaluator"
)


def _parse_permission_block(lines: list[str], start: int) -> tuple[dict[str, object], int]:
    """Parse the `permission:` block starting at `lines[start]` (the header line).

    Handles only this repo's actual shape: scalar values (`bash: deny`) and
    one level of nesting for `edit:` as an ordered path->action mapping.
    """
    block: dict[str, object] = {}
    i = start + 1
    while i < len(lines):
        line = lines[i]
        if not line.startswith("  ") or line.strip() == "":
            break
        key, _, value = line.strip().partition(":")
        value = value.strip()
        if value:
            block[key.strip()] = value
            i += 1
            continue
        # Nested mapping (only `edit:` uses this in practice).
        nested: dict[str, str] = {}
        i += 1
        while i < len(lines) and lines[i].startswith("    "):
            nkey, _, nvalue = lines[i].strip().partition(":")
            nested[nkey.strip().strip('"')] = nvalue.strip()
            i += 1
        block[key.strip()] = nested
    return block, i


def frontmatter(name: str) -> dict[str, object]:
    text = (AGENTS / name).read_text(encoding="utf-8")
    assert text.startswith("---\n")
    end = text.index("\n---\n", 4)
    lines = text[4:end].splitlines()
    result: dict[str, object] = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip() == "":
            i += 1
            continue
        key, _, value = line.partition(":")
        value = value.strip()
        if key.strip() == "permission" and not value:
            result["permission"], i = _parse_permission_block(lines, i)
            continue
        result[key.strip()] = value
        i += 1
    return result


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


# --- Runtime verification against the actual OpenCode permission evaluator ---
#
# `opencode debug agent <name>` returns the agent's fully-resolved config,
# including an ordered `permission` rule list (global defaults first, this
# repo's agent-specific overrides last) and a `tools` summary reflecting
# whether each capability is denied outright. Both are produced by the real
# evaluator, not by re-implementing its precedence rules here.


def _resolve_agent(name: str) -> dict:
    proc = subprocess.run(
        [OPENCODE, "debug", "agent", name],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return json.loads(proc.stdout)


def _effective_action(config: dict, permission: str, path: str) -> str | None:
    """Last-match-wins resolution over the resolved ordered rule list."""
    action = None
    for rule in config["permission"]:
        if rule["permission"] != permission:
            continue
        if fnmatch.fnmatch(path, rule["pattern"]):
            action = rule["action"]
    return action


@skip_if_no_opencode
def test_designer_runtime_edit_boundary() -> None:
    config = _resolve_agent("migration-designer")
    assert _effective_action(config, "edit", "migration/features/demo/target-feature-design.md") == "ask"
    assert _effective_action(config, "edit", "migration/features/demo/feature-card.md") == "deny"
    assert _effective_action(config, "edit", "target/frontend/src/App.tsx") == "deny"
    assert _effective_action(config, "edit", "target/backend/src/app/main.py") == "deny"
    assert _effective_action(config, "edit", "docs/01-architecture.md") == "deny"


@skip_if_no_opencode
def test_designer_runtime_bash_task_denied() -> None:
    config = _resolve_agent("migration-designer")
    assert config["tools"]["bash"] is False
    assert config["tools"]["task"] is False
    assert _effective_action(config, "bash", "anything") == "deny"
    assert _effective_action(config, "task", "anything") == "deny"


@skip_if_no_opencode
def test_implementer_runtime_edit_still_asks() -> None:
    config = _resolve_agent("implementer")
    assert config["tools"]["bash"] is True
    assert config["tools"]["edit"] is True
    assert _effective_action(config, "edit", "target/frontend/src/App.tsx") == "ask"
