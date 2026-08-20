"""Tests for the Issue #7 agent routing-contract checks.

Canonical contract: docs/09-agent-skill-routing.md ("Agent routing
contract", "Escalation contract", "Frontmatter description contract").
Every .opencode/agents/*.md must carry a frontmatter description, the
three deterministic routing sections (positive triggers, negative
triggers, primary output ownership), and a standard `## Escalation`
section that delegates its payload to the common STOP contract.

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
    ESCALATION_STOP_PAYLOAD_MARKER,
    ROUTING_CONTRACT_SKILLS,
    SKILL_ROUTING_SECTIONS,
    validate_agent_routing,
    validate_skill_routing_contract,
)

AGENTS = ".opencode/agents"

def escalation_block() -> str:
    return (
        "## Escalation\n\n"
        "Escalate to the coordinator when out of role or blocked.\n\n"
        f"Escalation returns use the {ESCALATION_STOP_PAYLOAD_MARKER} "
        "defined in `## Stop handling` above.\n"
    )


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
) -> Path:
    body = text if text is not None else VALID_AGENT_TEMPLATE.format(
        escalation=escalation_block()
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


def test_escalation_without_common_stop_payload_fails(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    text = VALID_AGENT_TEMPLATE.format(escalation=escalation_block()).replace(
        ESCALATION_STOP_PAYLOAD_MARKER,
        "a separate payload",
    )
    add_agent(root, text=text)
    errors = validate_agent_routing(root)
    assert errors == [
        f"{AGENTS}/sample-agent.md: '## Escalation' must delegate to the "
        "common STOP payload (docs/11-stop-condition-contract.md)",
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


@pytest.mark.parametrize(
    "description,missing",
    [
        (
            "migration helper",
            "positive trigger ('Invoke when ...'), primary output ownership "
            "('owns ...'), nearest exclusion ('do not use for ...')",
        ),
        (
            "owns the primary output; do not use for the nearest exclusion.",
            "positive trigger ('Invoke when ...')",
        ),
        (
            "Invoke when the trigger fires; do not use for the nearest exclusion.",
            "primary output ownership ('owns ...')",
        ),
        (
            "Invoke when the trigger fires; owns the primary output.",
            "nearest exclusion ('do not use for ...')",
        ),
    ],
)
def test_weak_description_fails(tmp_path: Path, description: str, missing: str) -> None:
    """A description that regresses to something non-deterministic (e.g. a
    one-line summary with no trigger/ownership/exclusion) must fail — this
    is the exact ambiguity docs/09's frontmatter description contract
    exists to prevent from silently reappearing."""
    root = make_repo(tmp_path)
    text = VALID_AGENT_TEMPLATE.format(escalation=escalation_block())
    text = text.replace(
        "description: Invoke when the trigger fires; owns the primary "
        "output; do not use for the nearest exclusion.",
        f"description: {description}",
    )
    add_agent(root, text=text)
    errors = validate_agent_routing(root)
    assert errors == [
        f"{AGENTS}/sample-agent.md: frontmatter description missing "
        f"{missing} (docs/09 frontmatter description contract)",
    ]


def test_real_agent_definitions_are_compliant() -> None:
    assert validate_agent_routing(ROOT) == []


# --- Issue #7 skill routing-contract checks (docs/09 "Skill routing
# contract"): the four overlapping skills must each carry a "Primary
# artifact boundary" and "Skill tie-break" section. ---

SKILLS_DIR = ".opencode/skills"

VALID_SKILL_TEMPLATE = """---
name: {name}
description: Primary skill when the trigger fires; do not use as the primary skill for the nearest exclusion.
compatibility: OpenCode project skill
---

# Sample Skill

## Primary artifact boundary

Invoke this as the primary skill only when the trigger fires.

## Skill tie-break

1. identify the artifact the current step must produce.
"""


def make_skill_repo(tmp_path: Path, name: str = "behavior-contract", *, text: str | None = None) -> Path:
    skill_dir = tmp_path / SKILLS_DIR / name
    skill_dir.mkdir(parents=True)
    body = text if text is not None else VALID_SKILL_TEMPLATE.format(name=name)
    (skill_dir / "SKILL.md").write_text(body, encoding="utf-8")
    return tmp_path


def test_valid_skill_passes(tmp_path: Path) -> None:
    root = make_skill_repo(tmp_path)
    assert validate_skill_routing_contract(root) == [
        f"{SKILLS_DIR}/{name}/SKILL.md: canonical routing-contract skill file missing"
        for name in ROUTING_CONTRACT_SKILLS
        if name != "behavior-contract"
    ]


def test_missing_skill_file_fails(tmp_path: Path) -> None:
    root = tmp_path
    errors = validate_skill_routing_contract(root)
    assert errors == [
        f"{SKILLS_DIR}/{name}/SKILL.md: canonical routing-contract skill file missing"
        for name in ROUTING_CONTRACT_SKILLS
    ]


@pytest.mark.parametrize("title", SKILL_ROUTING_SECTIONS)
def test_missing_skill_routing_section_fails(tmp_path: Path, title: str) -> None:
    text = VALID_SKILL_TEMPLATE.format(name="behavior-contract")
    marker = f"## {title}\n"
    start = text.index(marker)
    tail_marker = "\n## "
    end = text.find(tail_marker, start + len(marker))
    text = text[:start] + (text[end + 1 :] if end != -1 else "")
    root = make_skill_repo(tmp_path, text=text)
    errors = validate_skill_routing_contract(root)
    expected_missing = f"{SKILLS_DIR}/behavior-contract/SKILL.md: missing required section '## {title}' (docs/09-agent-skill-routing.md skill routing contract)"
    assert expected_missing in errors


def test_other_skills_are_not_checked(tmp_path: Path) -> None:
    """A skill outside the four canonical overlapping skills is out of
    scope for this check even with no routing sections at all."""
    root = tmp_path
    (root / SKILLS_DIR / "unrelated-skill").mkdir(parents=True)
    (root / SKILLS_DIR / "unrelated-skill" / "SKILL.md").write_text(
        "---\nname: unrelated-skill\ndescription: does something else\n---\n",
        encoding="utf-8",
    )
    errors = validate_skill_routing_contract(root)
    assert not any("unrelated-skill" in error for error in errors)


def test_real_skill_definitions_are_compliant() -> None:
    assert validate_skill_routing_contract(ROOT) == []
