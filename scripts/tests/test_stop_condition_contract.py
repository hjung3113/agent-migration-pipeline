"""Tests for the Issue #13 generated STOP-condition contract."""

from __future__ import annotations

from pathlib import Path

from scripts.sync_agent_stop_conditions import (
    AGENT_STOP_BEGIN_MARKER,
    AGENT_STOP_END_MARKER,
    CANONICAL_STOP_BEGIN_MARKER,
    CANONICAL_STOP_END_MARKER,
    load_canonical_stop_conditions,
    sync_agent_files,
    validate_agent_stop_conditions,
)


CANONICAL_BODY = """Stop and record an open question rather than guessing when a decision depends on:

- SC-01: unknown DLL entry points or lifecycle
- SC-02: unavailable platform behavior
- SC-03: ambiguous business semantics
- SC-04: destructive data migration assumptions
- SC-05: unverified stored procedure / trigger behavior
- SC-06: security/authentication requirements not visible in code
- SC-07: deployment topology not yet known"""

VALID_STOP_HANDLING = """When a STOP applies, return the common STOP payload to migration-coordinator.

```text
Reason: blocking-unknown | missing-evidence | contradiction | approval-gate | out-of-role
Stop condition: SC-01..SC-07 | none
Scope: feature | project
Feature: <feature-id> | none
Queue item: <queue-id> | none
Completed: <safe work completed before STOP>
Evidence: <artifact/source references>
Unresolved: <exact question, missing fact, conflict, or approval>
Impact: <artifact/decision/gate that cannot safely advance>
Recommended next route: <agent/skill/human gate>
Stop current gate: yes | no
Partial artifact: <path/body reference> | none
```"""


def canonical_source(body: str = CANONICAL_BODY) -> str:
    return (
        "# Agent Migration Pipeline\n\n"
        "## Stop conditions\n\n"
        f"{CANONICAL_STOP_BEGIN_MARKER}\n{body}\n"
        f"{CANONICAL_STOP_END_MARKER}\n"
    )


def agent_text(
    body: str = CANONICAL_BODY,
    *,
    include_stop_handling: bool = True,
) -> str:
    handling = (
        f"\n## Stop handling\n\n{VALID_STOP_HANDLING}\n"
        if include_stop_handling
        else ""
    )
    return (
        "# Agent\n\n## Stop conditions\n\n"
        f"{AGENT_STOP_BEGIN_MARKER}\n{body}\n{AGENT_STOP_END_MARKER}\n"
        f"{handling}\n## Escalation\n"
    )


def make_repo(tmp_path: Path, agents: dict[str, str]) -> Path:
    (tmp_path / "AGENTS.md").write_text(canonical_source(), encoding="utf-8")
    agents_dir = tmp_path / ".opencode" / "agents"
    agents_dir.mkdir(parents=True)
    for name, text in agents.items():
        (agents_dir / name).write_text(text, encoding="utf-8")
    return tmp_path


def test_canonical_registry_is_read_from_marked_agents_block(tmp_path: Path) -> None:
    root = make_repo(tmp_path, {"alpha.md": agent_text()})

    body, errors = load_canonical_stop_conditions(root)

    assert errors == []
    assert body == CANONICAL_BODY


def test_missing_agent_block_is_reported(tmp_path: Path) -> None:
    root = make_repo(
        tmp_path,
        {"alpha.md": "# Agent\n\n## Stop handling\n\n" + VALID_STOP_HANDLING},
    )

    errors = validate_agent_stop_conditions(root)

    assert any("alpha.md" in error and "managed" in error for error in errors)


def test_drifted_agent_block_is_reported(tmp_path: Path) -> None:
    drifted = CANONICAL_BODY.replace(
        "SC-07: deployment topology not yet known",
        "SC-07: deployment topology is known",
    )
    root = make_repo(tmp_path, {"alpha.md": agent_text(drifted)})

    errors = validate_agent_stop_conditions(root)

    assert any("alpha.md" in error and "drift" in error for error in errors)


def test_drifted_common_stop_payload_is_reported(tmp_path: Path) -> None:
    drifted = agent_text().replace(
        "Scope: feature | project",
        "Scope: feature | project-only",
    )
    root = make_repo(
        tmp_path,
        {"alpha.md": agent_text(), "beta.md": drifted},
    )

    errors = validate_agent_stop_conditions(root)

    assert any("beta.md" in error and "payload drifts" in error for error in errors)


def test_missing_stop_handling_payload_structure_is_reported(tmp_path: Path) -> None:
    root = make_repo(
        tmp_path,
        {"alpha.md": agent_text(include_stop_handling=False)},
    )

    errors = validate_agent_stop_conditions(root)

    assert any("alpha.md" in error and "Stop handling" in error for error in errors)


def test_checker_enumerates_every_agent_markdown_file(tmp_path: Path) -> None:
    root = make_repo(
        tmp_path,
        {
            "alpha.md": agent_text(),
            "new-specialist.md": agent_text(include_stop_handling=False),
        },
    )

    errors = validate_agent_stop_conditions(root)

    assert any("new-specialist.md" in error for error in errors)


def test_sync_writes_the_same_canonical_block_to_every_agent(tmp_path: Path) -> None:
    root = make_repo(
        tmp_path,
        {
            "alpha.md": "# Agent\n\n## Escalation\n",
            "beta.md": "# Agent\n\n## Stop conditions\n\nold\n\n## Escalation\n",
        },
    )

    changed = sync_agent_files(root)

    assert {path.name for path in changed} == {"alpha.md", "beta.md"}
    for name in ("alpha.md", "beta.md"):
        text = (root / ".opencode" / "agents" / name).read_text(encoding="utf-8")
        assert (
            f"## Stop conditions\n\n{AGENT_STOP_BEGIN_MARKER}\n"
            f"{CANONICAL_BODY}\n{AGENT_STOP_END_MARKER}"
        ) in text


def test_sync_inserts_missing_heading_after_frontmatter(tmp_path: Path) -> None:
    agent = (
        "---\nname: specialist\n---\n\n"
        f"{AGENT_STOP_BEGIN_MARKER}\n{CANONICAL_BODY}\n"
        f"{AGENT_STOP_END_MARKER}\n\n## Escalation\n"
    )
    root = make_repo(tmp_path, {"specialist.md": agent})

    sync_agent_files(root)

    updated = (root / ".opencode" / "agents" / "specialist.md").read_text(
        encoding="utf-8"
    )
    assert updated.startswith("---\nname: specialist\n---\n")
    assert updated.index("## Stop conditions") > updated.index("---\n", 4)


def test_invalid_uniform_stop_payload_enum_fails(tmp_path: Path) -> None:
    invalid_values = {
        (
            "Reason: blocking-unknown | missing-evidence | contradiction | "
            "approval-gate | out-of-role"
        ): "Reason: banana",
        "Stop condition: SC-01..SC-07 | none": "Stop condition: SC-99 | none",
        "Scope: feature | project": "Scope: banana",
        "Stop current gate: yes | no": "Stop current gate: maybe",
    }

    for index, (original, replacement) in enumerate(invalid_values.items()):
        invalid_handling = VALID_STOP_HANDLING.replace(original, replacement)
        invalid_agent = agent_text().replace(VALID_STOP_HANDLING, invalid_handling)
        case_root = tmp_path / f"case-{index}"
        case_root.mkdir()
        root = make_repo(
            case_root,
            {"alpha.md": invalid_agent, "beta.md": invalid_agent},
        )

        errors = validate_agent_stop_conditions(root)

        assert any(
            "invalid value" in error and "common STOP payload field" in error
            for error in errors
        )
