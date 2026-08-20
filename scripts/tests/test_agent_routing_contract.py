"""Tests for the Issue #7 agent routing-contract checks.

Canonical contract: docs/09-agent-skill-routing.md ("Agent routing
contract", "Escalation contract", "Frontmatter description contract").
Every .opencode/agents/*.md must carry a frontmatter description, the
three deterministic routing sections (positive triggers, negative
triggers, primary output ownership), and a standard `## Escalation`
section with its required fields.

Permission-frontmatter shape is intentionally NOT asserted here
(role-boundary permission work is owned separately, e.g. Issue #8).

Synthetic cases build a fixture `.opencode/agents/` tree under tmp_path;
one test at the bottom runs against the real agent definitions.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.validate_scaffold import (
    ROOT,
    AGENT_ROUTING_SECTIONS,
    ESCALATION_FIELDS,
    validate_agent_routing,
)

AGENTS = ".opencode/agents"

_ESCALATION_VALUES = {
    "Reason": "`out-of-role | missing-evidence | contradiction | "
    "approval-gate | blocking-unknown`",
    "Completed": "work already completed within the role",
    "Evidence": "relevant artifact/evidence references",
    "Unresolved": "the exact remaining question or conflict",
    "Impact": "which artifact, decision, or phase gate is affected",
    "Recommended next route": "agent/skill/human gate requested",
    "Stop current gate": "`yes` or `no`",
}


def escalation_block(skip_field: str | None = None) -> str:
    lines = [
        "## Escalation",
        "",
        "Escalate to the coordinator when out of role or blocked.",
        "",
    ]
    for field in ESCALATION_FIELDS:
        if field == skip_field:
            continue
        lines.append(f"- `{field}`: {_ESCALATION_VALUES[field]};")
    return "\n".join(lines) + "\n"


VALID_AGENT_TEMPLATE = """---
description: Invoke when the trigger fires; owns the primary output; do not use for the nearest exclusion.
mode: subagent
temperature: 0.1
permission:
  edit: deny
  bash: ask
  skill: allow
---

Role summary line.

## Invoke when

- the deterministic positive trigger holds.

## Do not invoke for

- the nearest confusing exclusion.

## Primary output ownership

- the primary artifact this role produces.

{escalation}"""


def make_repo(tmp_path: Path) -> Path:
    (tmp_path / AGENTS).mkdir(parents=True)
    return tmp_path


def add_agent(
    root: Path,
    name: str = "sample-agent",
    *,
    text: str | None = None,
    skip_field: str | None = None,
) -> Path:
    body = text if text is not None else VALID_AGENT_TEMPLATE.format(
        escalation=escalation_block(skip_field=skip_field)
    )
    path = root / AGENTS / f"{name}.md"
    path.write_text(body, encoding="utf-8")
    return path


def test_valid_agent_passes(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    add_agent(root)
    assert validate_agent_routing(root) == []


def test_nested_permission_frontmatter_is_not_required(tmp_path: Path) -> None:
    """Issue #8 owns permission-block shape; this validator must accept an
    agent with no permission block at all (description + sections only)."""
    root = make_repo(tmp_path)
    text = VALID_AGENT_TEMPLATE.format(escalation=escalation_block())
    text = "\n".join(
        line for line in text.splitlines()
        if not line.startswith(("mode:", "temperature:", "permission:"))
        and line.strip() not in ("edit: deny", "bash: ask", "skill: allow")
    ) + "\n"
    add_agent(root, "minimal-agent", text=text)
    assert validate_agent_routing(root) == []


def test_missing_description_fails(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    text = VALID_AGENT_TEMPLATE.format(escalation=escalation_block())
    text = text.replace(
        "description: Invoke when the trigger fires; owns the primary "
        "output; do not use for the nearest exclusion.\n",
        "",
    )
    add_agent(root, text=text)
    errors = validate_agent_routing(root)
    assert errors == [
        f"{AGENTS}/sample-agent.md: missing frontmatter description "
        "(docs/09 frontmatter description contract)",
    ]


@pytest.mark.parametrize("title", AGENT_ROUTING_SECTIONS)
def test_missing_routing_section_fails(tmp_path: Path, title: str) -> None:
    root = make_repo(tmp_path)
    text = VALID_AGENT_TEMPLATE.format(escalation=escalation_block())
    marker = f"## {title}\n"
    start = text.index(marker)
    end = text.index("## ", start + len(marker))
    text = text[:start] + text[end:]
    add_agent(root, text=text)
    errors = validate_agent_routing(root)
    assert errors == [
        f"{AGENTS}/sample-agent.md: missing required routing section "
        f"'## {title}' (docs/09-agent-skill-routing.md)",
    ]


@pytest.mark.parametrize("title", AGENT_ROUTING_SECTIONS)
def test_empty_routing_section_fails(tmp_path: Path, title: str) -> None:
    root = make_repo(tmp_path)
    text = VALID_AGENT_TEMPLATE.format(escalation=escalation_block())
    marker = f"## {title}\n"
    start = text.index(marker) + len(marker)
    end = text.index("\n## ", start)
    text = text[:start] + "\n" + text[end:]
    add_agent(root, text=text)
    errors = validate_agent_routing(root)
    assert errors == [f"{AGENTS}/sample-agent.md: routing section '## {title}' is empty"]


def test_h3_heading_does_not_satisfy_routing_section(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    text = VALID_AGENT_TEMPLATE.format(escalation=escalation_block())
    text = text.replace("## Do not invoke for", "### Do not invoke for")
    add_agent(root, text=text)
    errors = validate_agent_routing(root)
    assert errors == [
        f"{AGENTS}/sample-agent.md: missing required routing section "
        f"'## Do not invoke for' (docs/09-agent-skill-routing.md)",
    ]


def test_missing_escalation_section_fails(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    text = VALID_AGENT_TEMPLATE.format(escalation="")
    text = text.rstrip("\n") + "\n"
    add_agent(root, text=text)
    errors = validate_agent_routing(root)
    assert errors == [
        f"{AGENTS}/sample-agent.md: missing required routing section "
        f"'## Escalation' (docs/09 escalation contract)",
    ]


@pytest.mark.parametrize("field", ESCALATION_FIELDS)
def test_missing_escalation_field_fails(tmp_path: Path, field: str) -> None:
    root = make_repo(tmp_path)
    add_agent(root, skip_field=field)
    errors = validate_agent_routing(root)
    assert errors == [
        f"{AGENTS}/sample-agent.md: '## Escalation' missing required "
        f"field '{field}'",
    ]


def test_failures_aggregate_across_agents(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    add_agent(root, "alpha", text=VALID_AGENT_TEMPLATE.format(escalation=""))
    add_agent(root, "beta")  # valid
    text = VALID_AGENT_TEMPLATE.format(escalation=escalation_block())
    add_agent(
        root,
        "gamma",
        text=text.replace("## Primary output ownership", "## Outputs"),
    )
    errors = validate_agent_routing(root)
    assert len(errors) == 2
    assert (
        f"{AGENTS}/alpha.md: missing required routing section "
        f"'## Escalation' (docs/09 escalation contract)" in errors
    )
    assert (
        f"{AGENTS}/gamma.md: missing required routing section "
        f"'## Primary output ownership' (docs/09-agent-skill-routing.md)"
        in errors
    )


def test_missing_agents_directory_fails(tmp_path: Path) -> None:
    assert validate_agent_routing(tmp_path) == [
        f"{AGENTS}: agent definition directory missing",
    ]


def test_empty_agents_directory_fails(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    assert validate_agent_routing(root) == [
        f"{AGENTS}: no agent definitions found",
    ]


def test_real_agent_definitions_are_compliant() -> None:
    assert validate_agent_routing(ROOT) == []
