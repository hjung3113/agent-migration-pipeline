"""Tests for the Issue #14 durable-state checks in scripts/validate_scaffold.py.

Canonical contract: docs/11-durable-state-protocol.md ("Static validation
ownership", "Migration of existing durable files"). Validates the
migration/STATE.md frontmatter, the migration/QUEUE.md frontmatter plus its
single canonical live table, generation equality, dependency/blocker grammar
and invariants, derived STATE summary lists, project status versus queue
actionability, and DONE completion-artifact existence.

Synthetic cases build a minimal fixture repository under tmp_path; the test
at the bottom runs the real (migrated) repository tree end to end.

Fixture layout (deterministic line numbers for exact diagnostics):

    migration/QUEUE.md      migration/STATE.md
    1  ---                  1  ---
    2  schema_version       2  schema_version
    3  generation           3  generation
    4  status_values        4  phase
    5  ---                  5  phase_name
    6                       6  status
    7  # Migration Queue    7  current_gate
    8  header               8  gate_result
    9  separator            9  failed_gate_criteria
    10 first row            10 active_queue_items
                            11 next_queue_items
                            12 blocked_queue_items
                            13 last_updated
                            14 ---
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.validate_scaffold import ROOT, validate_durable_state

QUEUE_HEADER = (
    "| ID | Status | Phase | Depends on | Blocker | Work item | "
    "Completion artifact |"
)


def state_text(drop: tuple[str, ...] = (), **overrides: str) -> str:
    fields = {
        "schema_version": "1",
        "generation": "3",
        "phase": '"0"',
        "phase_name": '"Environment and feasibility"',
        "status": "ACTIVE",
        "current_gate": "G0",
        "gate_result": "BLOCKED",
        "failed_gate_criteria": "[G0.1, G0.2]",
        "active_queue_items": "[]",
        "next_queue_items": "[Q-003]",
        "blocked_queue_items": "[Q-001, Q-002]",
        "last_updated": '"2026-08-19T15:20:46Z"',
    }
    fields.update(overrides)
    lines = ["---"]
    for key, value in fields.items():
        if key in drop:
            continue
        lines.append(f"{key}: {value}")
    lines.append("---")
    lines.extend(["", "# Migration State", "", "Human context prose only.", ""])
    return "\n".join(lines)


def quiet_state(**overrides: str) -> str:
    """STATE whose queue-ID lists start empty (for fixtures whose queue does
    not contain the default Q-001/Q-002/Q-003 rows)."""
    base = {"next_queue_items": "[]", "blocked_queue_items": "[]"}
    base.update(overrides)
    return state_text(**base)


def row(
    row_id="Q-003",
    status="TODO",
    phase="0",
    deps="-",
    blocker="-",
    work="work item",
    artifact="prose artifact",
) -> str:
    return (
        f"| {row_id} | {status} | {phase} | {deps} | {blocker} | {work} "
        f"| {artifact} |"
    )


DEFAULT_ROWS = [
    row("Q-001", "BLOCKED", blocker="EXT:legacy-source-access"),
    row("Q-002", "BLOCKED", blocker="OQ-001"),
    row("Q-003", "TODO", deps="Q-004"),
    row("Q-004", "DONE", artifact="docs/marker.txt"),
    row("S-001", "DONE", artifact="this table"),
]


def queue_text(
    rows: list[str] | None = None,
    generation: str = "3",
    schema_version: str = "1",
    status_values: str = "[TODO, IN_PROGRESS, BLOCKED, DONE]",
    header: str = QUEUE_HEADER,
    between: str = "",
) -> str:
    if rows is None:
        rows = DEFAULT_ROWS
    lines = [
        "---",
        f"schema_version: {schema_version}",
        f"generation: {generation}",
        f"status_values: {status_values}",
        "---",
        "",
        "# Migration Queue",
    ]
    if between:
        lines.append(between)
    lines.append(header)
    lines.append("|---|---|---|---|---|---|---|")
    lines.extend(rows)
    lines.append("")
    return "\n".join(lines)


def make_repo(
    tmp_path: Path, state: str | None = None, queue: str | None = None
) -> Path:
    """Default-valid fixture repo: phase 0, G0 BLOCKED, Q-003 actionable."""
    migration = tmp_path / "migration"
    migration.mkdir(exist_ok=True)
    docs = tmp_path / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "marker.txt").write_text("exists\n", encoding="utf-8")
    (migration / "STATE.md").write_text(state or state_text(), encoding="utf-8")
    (migration / "QUEUE.md").write_text(queue or queue_text(), encoding="utf-8")
    return tmp_path


def run(
    tmp_path: Path, state: str | None = None, queue: str | None = None
) -> list[str]:
    return validate_durable_state(make_repo(tmp_path, state, queue))


# --- positive cases ----------------------------------------------------------


def test_valid_state_and_queue_pass(tmp_path: Path) -> None:
    assert run(tmp_path) == []


def test_in_progress_row_passes(tmp_path: Path) -> None:
    state = state_text(active_queue_items="[Q-003]", next_queue_items="[]")
    queue = queue_text(rows=[
        row("Q-001", "BLOCKED", blocker="EXT:legacy-source-access"),
        row("Q-002", "BLOCKED", blocker="OQ-001"),
        row("Q-003", "IN_PROGRESS", deps="Q-004"),
        row("Q-004", "DONE", artifact="docs/marker.txt"),
    ])
    assert run(tmp_path, state, queue) == []


def test_blocked_by_unmet_dependency_only_passes(tmp_path: Path) -> None:
    """BLOCKED via an unfinished dependency with `Blocker: -` is valid."""
    state = state_text(
        next_queue_items="[Q-004]",
        blocked_queue_items="[Q-001, Q-002, Q-003]",
    )
    queue = queue_text(rows=[
        row("Q-001", "BLOCKED", blocker="EXT:legacy-source-access"),
        row("Q-002", "BLOCKED", blocker="OQ-001"),
        row("Q-003", "BLOCKED", deps="Q-004"),
        row("Q-004", "TODO"),
    ])
    assert run(tmp_path, state, queue) == []


def test_blocked_via_gate_criterion_and_human_blockers_pass(tmp_path: Path) -> None:
    state = state_text(
        next_queue_items="[]",
        blocked_queue_items="[Q-001, Q-002, Q-003]",
        status="BLOCKED",
    )
    queue = queue_text(rows=[
        row("Q-001", "BLOCKED", blocker="EXT:legacy-source-access"),
        row("Q-002", "BLOCKED", blocker="OQ-001; G0.3"),
        row("Q-003", "BLOCKED", blocker="HUMAN:pilot-approval"),
    ])
    assert run(tmp_path, state, queue) == []


def test_paused_and_complete_exempt_from_actionability(tmp_path: Path) -> None:
    assert run(tmp_path, state_text(status="PAUSED")) == []

    state = quiet_state(
        status="COMPLETE",
        current_gate="NONE",
        gate_result="NONE",
        failed_gate_criteria="[]",
    )
    queue = queue_text(rows=[row("Q-004", "DONE", artifact="docs/marker.txt")])
    assert run(tmp_path, state, queue) == []


def test_pending_gate_with_empty_criteria_passes(tmp_path: Path) -> None:
    assert run(tmp_path, state_text(gate_result="PENDING",
                                    failed_gate_criteria="[]")) == []


def test_fenced_example_table_is_not_a_live_table(tmp_path: Path) -> None:
    between = (
        "```text\n" + QUEUE_HEADER + "\n|---|---|---|---|---|---|---|\n"
        "| Q-009 | TODO | 0 | - | - | fenced example | none |\n```\n"
    )
    assert run(tmp_path, queue=queue_text(between=between)) == []


def test_done_row_with_unresolvable_artifact_prose_is_skipped(tmp_path: Path) -> None:
    queue = queue_text(rows=[
        row("Q-001", "DONE", artifact="DLL boundary report + OQ updates"),
        row("Q-002", "DONE", artifact="migration/{a,b}/x.md"),
        row("Q-003", "DONE", artifact="this table"),
        row("Q-004", "DONE", artifact="docs/marker.txt"),
    ])
    assert run(tmp_path, state=quiet_state(), queue=queue) == []


# --- frontmatter schema ------------------------------------------------------


def test_missing_state_frontmatter_rejected(tmp_path: Path) -> None:
    errors = run(tmp_path, state="# Migration State\n\nno frontmatter\n")
    assert errors == [
        "migration/STATE.md:1 [missing-frontmatter] file must start with "
        "YAML frontmatter delimited by ---"
    ]


def test_missing_queue_frontmatter_rejected(tmp_path: Path) -> None:
    errors = run(tmp_path, queue="# Migration Queue\n\nno frontmatter\n")
    assert errors == [
        "migration/QUEUE.md:1 [missing-frontmatter] file must start with "
        "YAML frontmatter delimited by ---"
    ]


def test_unterminated_state_frontmatter_rejected(tmp_path: Path) -> None:
    errors = run(tmp_path, state="---\nstatus: ACTIVE\n")
    assert errors == [
        "migration/STATE.md:2 [missing-frontmatter] unterminated YAML "
        "frontmatter (missing closing ---)"
    ]


def test_state_file_missing_rejected(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    (root / "migration" / "STATE.md").unlink()
    assert validate_durable_state(root) == [
        "migration/STATE.md: durable-state file missing"
    ]


def test_queue_file_missing_rejected(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    (root / "migration" / "QUEUE.md").unlink()
    assert validate_durable_state(root) == [
        "migration/QUEUE.md: durable-state file missing"
    ]


def test_unsupported_schema_version_rejected(tmp_path: Path) -> None:
    errors = run(tmp_path, state_text(schema_version="2"))
    assert errors == [
        "migration/STATE.md:2 [unsupported-schema-version] schema_version 2 "
        "is not supported (expected 1)"
    ]


@pytest.mark.parametrize("generation", ["0", "-1", "two"])
def test_non_positive_or_non_integer_generation_rejected(
    tmp_path: Path, generation: str
) -> None:
    errors = run(tmp_path, state_text(generation=generation))
    assert len(errors) == 1
    assert "generation must be a positive integer" in errors[0]


def test_unequal_generations_rejected(tmp_path: Path) -> None:
    errors = run(tmp_path, queue=queue_text(generation="4"))
    assert errors == [
        "migration/QUEUE.md:3 [invalid-generation] QUEUE generation 4 != "
        "STATE generation 3; every durable transaction must update both "
        "files to the same new generation"
    ]


def test_missing_required_state_key_rejected(tmp_path: Path) -> None:
    errors = run(tmp_path, state_text(drop=("status",)))
    assert errors == [
        "migration/STATE.md:1 [missing-key] missing required frontmatter "
        "key: status"
    ]


def test_duplicate_frontmatter_key_rejected(tmp_path: Path) -> None:
    state = state_text().replace(
        "status: ACTIVE\n", "status: ACTIVE\nstatus: BLOCKED\n", 1
    )
    errors = run(tmp_path, state)
    assert errors == [
        "migration/STATE.md:7 [duplicate-key] duplicate frontmatter key: status"
    ]


def test_indented_frontmatter_line_rejected(tmp_path: Path) -> None:
    state = state_text().replace(
        "status: ACTIVE\n", "status: ACTIVE\n  nested: true\n", 1
    )
    errors = run(tmp_path, state)
    assert len(errors) == 1
    assert "[invalid-frontmatter] indented line" in errors[0]
    assert "nested: true" in errors[0]


def test_non_bracket_list_field_rejected(tmp_path: Path) -> None:
    errors = run(tmp_path, state_text(failed_gate_criteria="G0.1"))
    assert errors == [
        "migration/STATE.md:9 [invalid-type] failed_gate_criteria must be a "
        "bracket list like [A, B] or [], got 'G0.1'"
    ]


def test_invalid_timestamp_rejected(tmp_path: Path) -> None:
    errors = run(tmp_path, state_text(last_updated='"2026-08-19"'))
    assert len(errors) == 1
    assert "[invalid-timestamp]" in errors[0]


# --- STATE enums and gate relationships --------------------------------------


def test_invalid_project_status_rejected(tmp_path: Path) -> None:
    errors = run(tmp_path, state_text(status="RUNNING"))
    assert errors == [
        "migration/STATE.md:6 [invalid-enum] status `RUNNING`; expected "
        "ACTIVE|BLOCKED|PAUSED|COMPLETE"
    ]


def test_invalid_gate_result_rejected(tmp_path: Path) -> None:
    errors = run(tmp_path, state_text(gate_result="FAILED"))
    assert errors == [
        "migration/STATE.md:8 [invalid-enum] gate_result `FAILED`; expected "
        "PENDING|PASS|BLOCKED|NONE"
    ]


def test_unknown_current_gate_rejected(tmp_path: Path) -> None:
    errors = run(tmp_path, state_text(current_gate="G9"))
    assert errors == [
        "migration/STATE.md:7 [invalid-enum] current_gate `G9`; expected "
        "G0|G2|G3|NONE (canonical gates from docs/02-migration-pipeline.md)"
    ]


def test_blocked_gate_requires_criteria(tmp_path: Path) -> None:
    errors = run(tmp_path, state_text(failed_gate_criteria="[]"))
    assert errors == [
        "migration/STATE.md:8 [invalid-relationship] gate_result BLOCKED "
        "requires a non-empty failed_gate_criteria list"
    ]


def test_pass_gate_requires_empty_criteria(tmp_path: Path) -> None:
    errors = run(tmp_path, state_text(gate_result="PASS"))
    assert errors == [
        "migration/STATE.md:9 [invalid-relationship] gate_result PASS "
        "requires failed_gate_criteria to be empty, got ['G0.1', 'G0.2']"
    ]


def test_criterion_from_wrong_gate_rejected(tmp_path: Path) -> None:
    errors = run(tmp_path, state_text(failed_gate_criteria="[G2.1]"))
    assert errors == [
        "migration/STATE.md:9 [invalid-ref] criterion `G2.1` does not belong "
        "to gate G0 (criteria: G0.1, G0.2, G0.3)"
    ]


def test_current_gate_none_xor_gate_result_none(tmp_path: Path) -> None:
    errors = run(
        tmp_path,
        state_text(gate_result="NONE", failed_gate_criteria="[]"),
    )
    assert errors == [
        "migration/STATE.md:7 [invalid-relationship] current_gate: NONE "
        "exactly when gate_result: NONE (no gate applies)"
    ]


def test_status_values_mismatch_rejected(tmp_path: Path) -> None:
    errors = run(tmp_path, queue=queue_text(status_values="[TODO, DONE]"))
    assert errors == [
        "migration/QUEUE.md:4 [invalid-enum] status_values must be exactly "
        "[TODO, IN_PROGRESS, BLOCKED, DONE], got [TODO, DONE]"
    ]


# --- queue table shape -------------------------------------------------------


def test_second_live_table_rejected(tmp_path: Path) -> None:
    queue = (
        queue_text() + "\n" + QUEUE_HEADER + "\n|---|---|---|---|---|---|---|\n"
        + row("Q-005", "TODO") + "\n"
    )
    errors = run(tmp_path, queue=queue)
    assert errors == [
        "migration/QUEUE.md:16 [duplicate-table] more than one live queue "
        "table; QUEUE.md must contain exactly one"
    ]


def test_old_five_column_header_rejected(tmp_path: Path) -> None:
    old_header = "| ID | Status | Phase | Work item | Completion artifact |"
    queue = queue_text(
        header=old_header,
        rows=["| Q-001 | TODO | 0 | old shape | artifact |"],
    )
    errors = run(tmp_path, state=quiet_state(), queue=queue)
    assert errors == [
        "migration/QUEUE.md:8 [invalid-header] live queue table columns must "
        "be exactly ID | Status | Phase | Depends on | Blocker | Work item | "
        "Completion artifact, got ID | Status | Phase | Work item | "
        "Completion artifact"
    ]


def test_reordered_header_rejected(tmp_path: Path) -> None:
    reordered = (
        "| ID | Status | Phase | Blocker | Depends on | Work item | "
        "Completion artifact |"
    )
    errors = run(
        tmp_path,
        queue=queue_text(header=reordered, rows=[row("Q-001", "TODO")]),
    )
    assert any("[invalid-header]" in error for error in errors)


def test_missing_live_table_rejected(tmp_path: Path) -> None:
    queue = queue_text().split("| ID", 1)[0]
    errors = run(tmp_path, state=quiet_state(), queue=queue)
    assert any("[missing-table] no canonical live queue table" in error
               for error in errors)


def test_row_with_wrong_column_count_rejected(tmp_path: Path) -> None:
    queue = queue_text(rows=["| Q-001 | DONE | 0 | - | - | six cells |"])
    errors = run(tmp_path, state=quiet_state(), queue=queue)
    assert errors == [
        "migration/QUEUE.md:10 [invalid-row] expected 7 columns, got 6"
    ]


# --- queue IDs, dependencies, blockers ---------------------------------------


def test_malformed_queue_id_rejected(tmp_path: Path) -> None:
    errors = run(tmp_path, state=quiet_state(),
                 queue=queue_text(rows=[row("Q-1", "DONE")]))
    assert errors == [
        "migration/QUEUE.md:10 [invalid-id] `Q-1`; expected Q-### or S-###"
    ]


def test_duplicate_queue_id_rejected(tmp_path: Path) -> None:
    queue = queue_text(rows=[row("Q-001", "DONE"), row("Q-001", "DONE")])
    errors = run(tmp_path, state=quiet_state(), queue=queue)
    assert errors == [
        "migration/QUEUE.md:11 [duplicate-id] duplicate queue ID `Q-001` "
        "(first defined at line 10)"
    ]


def test_missing_dependency_reference_rejected(tmp_path: Path) -> None:
    errors = run(
        tmp_path,
        state=quiet_state(blocked_queue_items="[Q-003]", status="BLOCKED"),
        queue=queue_text(rows=[row("Q-003", "BLOCKED", deps="Q-999")]),
    )
    assert errors == [
        "migration/QUEUE.md:10 [missing-ref] `Q-003` depends on `Q-999` "
        "which is not a live queue row"
    ]


def test_malformed_dependency_token_rejected(tmp_path: Path) -> None:
    errors = run(
        tmp_path,
        state=quiet_state(
            blocked_queue_items="[Q-003]", status="BLOCKED"
        ),
        queue=queue_text(rows=[
            row("Q-003", "BLOCKED", deps="Q4", blocker="OQ-001"),
        ]),
    )
    assert errors == [
        "migration/QUEUE.md:10 [invalid-id] Depends on token `Q4`; expected "
        "Q-### or S-###"
    ]


def test_cyclic_dependencies_rejected(tmp_path: Path) -> None:
    state = state_text(
        next_queue_items="[]",
        blocked_queue_items="[Q-001, Q-003, Q-004]",
        status="BLOCKED",
    )
    queue = queue_text(rows=[
        row("Q-001", "BLOCKED", blocker="EXT:legacy-source-access"),
        row("Q-003", "BLOCKED", deps="Q-004"),
        row("Q-004", "BLOCKED", deps="Q-003"),
    ])
    errors = run(tmp_path, state, queue)
    assert errors == [
        "migration/QUEUE.md:11 [cyclic-dependency] `Q-003` depends "
        "(transitively) on itself",
        "migration/QUEUE.md:12 [cyclic-dependency] `Q-004` depends "
        "(transitively) on itself",
    ]


@pytest.mark.parametrize(
    "blocker,offender",
    [
        ("EXT:Legacy_Access", "EXT:Legacy_Access"),
        ("EXT:", "EXT:"),
        ("HUMAN:Approval", "HUMAN:Approval"),
        ("human:approval", "human:approval"),
        ("OQ-1", "OQ-1"),
        ("OQ-001; legacy access", "legacy access"),
        ("G0", "G0"),
        ("G9.9", "G9.9"),
        ("blocked by owner approval", "blocked by owner approval"),
    ],
)
def test_invalid_blocker_syntax_rejected(
    tmp_path: Path, blocker: str, offender: str
) -> None:
    errors = run(
        tmp_path,
        state=quiet_state(),
        queue=queue_text(rows=[row("Q-001", "DONE", blocker=blocker)]),
    )
    assert errors == [
        "migration/QUEUE.md:10 [invalid-ref] Blocker `" + offender
        + "`; expected OQ-###, canonical gate criterion (e.g. G0.1), "
        "EXT:<kebab-token>, or HUMAN:<kebab-token>"
    ]


def test_invalid_row_status_rejected(tmp_path: Path) -> None:
    errors = run(tmp_path, state=quiet_state(),
                 queue=queue_text(rows=[row("Q-001", "DOING")]))
    assert errors == [
        "migration/QUEUE.md:10 [invalid-enum] Status `DOING`; expected "
        "TODO|IN_PROGRESS|BLOCKED|DONE"
    ]


# --- status/dependency/blocker invariants ------------------------------------


def test_todo_with_unmet_dependency_rejected(tmp_path: Path) -> None:
    queue = queue_text(rows=[
        row("Q-003", "TODO", deps="Q-004"),
        row("Q-004", "BLOCKED", blocker="EXT:legacy-source-access"),
    ])
    state = state_text(
        next_queue_items="[Q-003]", blocked_queue_items="[Q-004]"
    )
    errors = run(tmp_path, state, queue)
    assert errors == [
        "migration/QUEUE.md:10 [invalid-invariant] `Q-003` is TODO but not "
        "actionable; TODO requires every dependency DONE and Blocker `-`"
    ]


def test_todo_with_blocker_rejected(tmp_path: Path) -> None:
    queue = queue_text(rows=[row("Q-003", "TODO", blocker="OQ-001")])
    errors = run(tmp_path, state=quiet_state(next_queue_items="[Q-003]"),
                 queue=queue)
    assert errors == [
        "migration/QUEUE.md:10 [invalid-invariant] `Q-003` is TODO but not "
        "actionable; TODO requires every dependency DONE and Blocker `-`"
    ]


def test_in_progress_with_blocker_rejected(tmp_path: Path) -> None:
    state = quiet_state(active_queue_items="[Q-003]")
    queue = queue_text(rows=[row("Q-003", "IN_PROGRESS", blocker="HUMAN:approval")])
    errors = run(tmp_path, state, queue)
    assert errors == [
        "migration/QUEUE.md:10 [invalid-invariant] `Q-003` is IN_PROGRESS "
        "with violated preconditions; IN_PROGRESS requires dependencies DONE "
        "and Blocker `-`"
    ]


def test_blocked_without_cause_rejected(tmp_path: Path) -> None:
    state = state_text(
        next_queue_items="[]",
        blocked_queue_items="[Q-001, Q-002, Q-003]",
        status="BLOCKED",
    )
    queue = queue_text(rows=[
        row("Q-001", "BLOCKED", blocker="EXT:legacy-source-access"),
        row("Q-002", "BLOCKED", blocker="OQ-001"),
        row("Q-003", "BLOCKED", deps="Q-004"),
        row("Q-004", "DONE", artifact="docs/marker.txt"),
    ])
    errors = run(tmp_path, state, queue)
    assert errors == [
        "migration/QUEUE.md:12 [invalid-invariant] `Q-003` is BLOCKED "
        "without an unfinished dependency or blocker reference"
    ]


def test_done_row_with_missing_artifact_path_rejected(tmp_path: Path) -> None:
    queue = queue_text(rows=[
        row("Q-003", "DONE", artifact="docs/does-not-exist.md"),
        row("Q-004", "DONE", artifact="docs/marker.txt"),
    ])
    errors = run(tmp_path, state=quiet_state(), queue=queue)
    assert errors == [
        "migration/QUEUE.md:10 [missing-artifact] DONE row `Q-003` declares "
        "completion artifact `docs/does-not-exist.md` which does not exist "
        "in the repository"
    ]


# --- STATE summary lists versus the live queue -------------------------------


def test_state_blocked_list_inconsistent_rejected(tmp_path: Path) -> None:
    errors = run(tmp_path, state_text(blocked_queue_items="[Q-001]"))
    assert errors == [
        "migration/STATE.md:12 [invalid-invariant] blocked_queue_items "
        "['Q-001'] does not match the current-phase (phase 0) rows with "
        "that status: ['Q-001', 'Q-002']"
    ]


def test_state_next_list_inconsistent_rejected(tmp_path: Path) -> None:
    errors = run(tmp_path, state_text(next_queue_items="[]"))
    assert errors == [
        "migration/STATE.md:11 [invalid-invariant] next_queue_items [] does "
        "not match the current-phase (phase 0) rows with that status: "
        "['Q-003']"
    ]


def test_state_list_unknown_queue_id_rejected(tmp_path: Path) -> None:
    errors = run(tmp_path, state_text(blocked_queue_items="[Q-001, Q-009]"))
    assert len(errors) == 2
    assert (
        "migration/STATE.md:12 [missing-ref] `Q-009` in blocked_queue_items "
        "is not a live queue row" in errors
    )
    assert "[invalid-invariant] blocked_queue_items" in errors[1]


def test_state_lists_only_cover_current_phase_rows(tmp_path: Path) -> None:
    """Later-phase BLOCKED rows must not leak into the current-gate lists."""
    queue = queue_text(rows=DEFAULT_ROWS + [
        row("Q-010", "BLOCKED", phase="5-6", deps="Q-003"),
    ])
    assert run(tmp_path, queue=queue) == []


def test_project_status_inconsistent_with_actionability_rejected(
    tmp_path: Path,
) -> None:
    # All current-phase rows BLOCKED/DONE but STATE claims ACTIVE.
    state = state_text(next_queue_items="[]")
    queue = queue_text(rows=[
        row("Q-001", "BLOCKED", blocker="EXT:legacy-source-access"),
        row("Q-002", "BLOCKED", blocker="OQ-001"),
        row("Q-004", "DONE", artifact="docs/marker.txt"),
    ])
    errors = run(tmp_path, state, queue)
    assert errors == [
        "migration/STATE.md:6 [invalid-invariant] status ACTIVE but no "
        "current-phase queue row is actionable and at least one is BLOCKED "
        "(expected BLOCKED)"
    ]


def test_project_status_blocked_with_actionable_todo_rejected(
    tmp_path: Path,
) -> None:
    errors = run(tmp_path, state_text(status="BLOCKED"))
    assert errors == [
        "migration/STATE.md:6 [invalid-invariant] status BLOCKED but "
        "current-phase queue rows include actionable TODO/IN_PROGRESS work "
        "(expected ACTIVE)"
    ]


# --- real tree ---------------------------------------------------------------


def test_real_repo_durable_state_is_consistent() -> None:
    """The migrated migration/STATE.md + migration/QUEUE.md must validate."""
    assert validate_durable_state(ROOT) == []
