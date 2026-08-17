# Durable State Protocol Design

Issue: #14 — `migration/STATE.md` and `migration/QUEUE.md` do not yet define a deterministic, machine-parseable state contract or field-level update semantics.

This is a design-only artifact. `migration/STATE.md`, `migration/QUEUE.md`, `.opencode/commands/*.md`, the coordinator, validators, and CI are intentionally not changed in this pass because `AGENTS.md` rule 13 requires design approval before implementation.

## Goal

Make migration progress resumable from disk without requiring a model to infer:

- which fields are authoritative;
- which status values are legal;
- which transitions are legal;
- whether a blocker is feature-local, queue-local, or project-level;
- which file wins when durable artifacts disagree;
- how to detect and recover from a partially written multi-file update.

The protocol must remain simple enough for low-reasoning agents and straightforward static validation.

## Adversarial findings

Issue #14 identifies the correct defect, but adding enum legends alone is insufficient.

1. `STATE.md` currently mixes status code and reason in one human sentence (`ACTIVE — blocked ...`), so a parser cannot distinguish state from explanation.
2. `QUEUE.md` currently contains multiple tables with different schemas. A parser can read Markdown tables, but it cannot safely treat two schemas as one queue contract.
3. `TODO` currently means both "not started" and, in practice, "cannot start because legacy access is unavailable". That destroys the distinction between actionable and blocked work.
4. A new `IN_PROGRESS` value is necessary for crash-safe resume. Without it, work that has begun but has not satisfied its completion artifact is indistinguishable from untouched work.
5. Merely saying "update feature, queue, and state" does not prevent partial writes. The protocol needs source-of-truth precedence, a write order, a detectable transaction generation, and a recovery rule.
6. Project-level `BLOCKED` must not be copied from one blocked feature. It must be derived from whether any queue work at the current gate is still actionable.
7. `Last updated` as a date is not enough to detect concurrent or stale writers. Two sessions on the same day can overwrite each other while both appearing current.
8. `DONE` cannot mean "command returned successfully". It means the row's declared completion artifact exists and its applicable gate passed.
9. The command design in `docs/10-command-execution-contract.md` intentionally preserved the then-current queue vocabulary. This protocol is the later authority for durable-state semantics and supersedes that provisional vocabulary once implemented.

## Authority and precedence

Durable state has separate scopes. Do not collapse them.

1. **Feature lifecycle authority** — `migration/features/<feature-id>/feature-card.md` owns feature `stage` and feature-local `blocked` once issue #1 is implemented.
2. **Work-item authority** — `migration/QUEUE.md` owns whether one resumable queue item is `TODO`, `IN_PROGRESS`, `BLOCKED`, or `DONE`.
3. **Project summary authority** — `migration/STATE.md` is a derived summary of the current project phase/gate and queue condition. It must never be used to overwrite a more specific feature or queue fact.
4. **Unresolved-fact authority** — `docs/05-open-questions.md` owns unresolved factual questions; queue/state may reference those IDs but must not duplicate their full content.

When files disagree, repair from the more specific authority outward: feature/open-question evidence -> queue row -> project summary.

## `migration/STATE.md` schema

`STATE.md` should use YAML frontmatter for machine-readable fields and unrestricted Markdown only below the frontmatter for human context.

Canonical frontmatter fields:

```yaml
---
schema_version: 1
generation: 1
phase: "0"
phase_name: "Environment and feasibility"
status: BLOCKED
current_gate: "legacy-source-access"
active_queue_items: []
next_queue_items: []
blocked_queue_items: [Q-001, Q-002, Q-003]
last_updated: "2026-08-18T00:00:00Z"
---
```

Field rules:

| Field | Rule |
| --- | --- |
| `schema_version` | integer; exact supported schema version |
| `generation` | positive integer shared with `QUEUE.md`; changed by every queue/project-state transaction |
| `phase` | string identifier; phase advancement remains governed by the canonical phase-gate design |
| `phase_name` | human-readable label only; must correspond to `phase` |
| `status` | `ACTIVE \| BLOCKED \| PAUSED \| COMPLETE` |
| `current_gate` | stable machine token, not prose |
| `active_queue_items` | queue IDs currently `IN_PROGRESS` |
| `next_queue_items` | actionable queue IDs currently `TODO` |
| `blocked_queue_items` | queue IDs currently `BLOCKED` that are relevant to the current gate |
| `last_updated` | UTC RFC 3339 timestamp, not date-only text |

The Markdown body may explain completed work and the next gate, but no parser or command may infer status from that body.

### Project status derivation

Unless the user explicitly pauses the project:

- `COMPLETE`: all queue work required by the migration plan is `DONE` and the final gate is satisfied.
- `ACTIVE`: at least one current-gate queue item is `IN_PROGRESS` or actionable `TODO`.
- `BLOCKED`: no current-gate item is actionable/in progress and at least one required current-gate item is `BLOCKED`.
- `PAUSED`: explicit human pause; this is the only status not derived from queue actionability.

A single blocked feature or queue row does not make the project `BLOCKED` while another current-gate row remains actionable.

## `migration/QUEUE.md` schema

`QUEUE.md` remains Markdown for human usability, but it must have one machine-readable frontmatter block and exactly one canonical queue table.

Frontmatter:

```yaml
---
schema_version: 1
generation: 1
status_values: [TODO, IN_PROGRESS, BLOCKED, DONE]
---
```

Canonical table columns, in this order:

```text
ID | Status | Phase | Depends on | Blocker | Work item | Completion artifact
```

Rules:

- every queue ID is unique;
- all rows use the same seven columns; separate legacy-independent sections may be represented by `Phase`/work-item text, not a second schema;
- `Depends on` contains `-` or comma-separated queue IDs only;
- `Blocker` contains `-` or durable blocker identifiers such as `OQ-###`, `EXT-*`, or an explicit human-gate token;
- referenced queue dependencies must exist and must not create a dependency cycle;
- `TODO` requires all `Depends on` rows to be `DONE` and `Blocker` to be `-`;
- `IN_PROGRESS` requires all dependencies satisfied and `Blocker` to be `-`;
- `BLOCKED` requires either an unfinished dependency or a non-`-` blocker;
- `DONE` requires the declared completion artifact to exist and the applicable gate to have passed.

### Queue status semantics

| Status | Meaning |
| --- | --- |
| `TODO` | ready to start; no unresolved dependency or blocker |
| `IN_PROGRESS` | execution has begun and the row is resumable, but completion is not yet justified |
| `BLOCKED` | a durable dependency, unresolved fact, external condition, or human gate prevents progress |
| `DONE` | the row's declared completion artifact exists and its gate is satisfied |

Allowed normal transitions:

```text
TODO -> IN_PROGRESS
TODO -> BLOCKED
IN_PROGRESS -> BLOCKED
IN_PROGRESS -> DONE
BLOCKED -> TODO
```

`BLOCKED -> TODO` is used only after all blockers are cleared. A command then moves the selected row `TODO -> IN_PROGRESS` immediately before beginning durable execution.

`DONE` is terminal during normal execution. If later evidence invalidates completion, the coordinator may reopen it only as `DONE -> TODO`, with the reason persisted in the affected review/evidence/open-question artifact and visible in the commit/PR context. Silent reopening is forbidden.

## Transaction generation and concurrency

`STATE.md` and `QUEUE.md` share the same integer `generation`.

Every durable transaction that changes either queue state or project state must:

1. read both files and record starting generation `N`;
2. validate that both files have the same `N`;
3. re-read or otherwise compare before write so a concurrent writer cannot be silently overwritten;
4. write all feature/evidence/open-question artifacts first;
5. write `QUEUE.md` using generation `N+1`;
6. write `STATE.md` last using the same generation `N+1`;
7. prefer committing the complete transaction in one Git commit when the execution environment supports it.

Even a project-only pause/resume transaction increments both files to the same new generation; the queue table may be unchanged.

### Partial-write recovery

A reader must compare generations before starting new work.

- equal generations: normal read;
- `QUEUE.generation > STATE.generation`: treat `STATE.md` as stale, recompute it from queue/feature/open-question authorities, and do not start another queue item until repaired;
- `STATE.generation > QUEUE.generation`: protocol violation; do not infer which write was intended. Stop and reconcile from Git history plus specific durable artifacts.

This makes an interrupted ordered write detectable instead of silently inconsistent.

## Command mutation contract

This protocol supplies the field-level state semantics required by `docs/10-command-execution-contract.md`.

All mutating commands must eventually implement an explicit `State updates` section using the selected `--queue` row.

Common rules:

1. Invalid arguments or failed preconditions before work begins: no durable state transition.
2. When all preconditions pass and execution is about to begin: selected row `TODO -> IN_PROGRESS`; update queue/project generation transaction.
3. Durable blocker discovered after start: `IN_PROGRESS -> BLOCKED`, populate/retain `Blocker` or unresolved dependency, then recompute project state.
4. Transient tool/runtime failure after durable work began: leave the row `IN_PROGRESS`; do not fabricate `BLOCKED`.
5. Successful command execution marks `DONE` only if that run satisfies the selected row's full completion artifact and applicable gate; otherwise keep `IN_PROGRESS`.
6. Any queue mutation recomputes `STATE.md` from queue actionability rather than copying the selected row's status.

Command-specific outcomes:

| Command | Required state behavior |
| --- | --- |
| `migration-discover` | start selected discovery row as `IN_PROGRESS`; unresolved durable legacy access/fact may block only that row/scope; complete only when the row's declared discovery artifact is fully satisfied |
| `migration-spec` | remain `IN_PROGRESS` while the contract is incomplete; material unresolved semantics/human gate -> `BLOCKED`; complete only when specification may validly advance |
| `migration-design` | missing/failed design gate -> no start or `BLOCKED` if a durable gate dependency exists; complete only when the selected design row's artifact/gate is satisfied |
| `migration-implement` | explicit implementation authorization is a precondition; without it, do not start target edits; after start, deviations/failures keep work incomplete until resolved |
| `migration-review` | review findings do not mean `DONE`; a correction-required review keeps the broader row `IN_PROGRESS` unless a durable blocker prevents correction |
| `migration-verify` | PASS may complete the selected row only when its full completion artifact/gate is satisfied; FAIL/PARTIAL keep `IN_PROGRESS`; BLOCKED -> `BLOCKED` |
| `migration-status` | read-only; first validate STATE/QUEUE schema and equal generation; never repair implicitly while reporting |

A broad queue item such as combined review + verification remains `IN_PROGRESS` after a successful review if verification is still outstanding.

## Static validation design

After implementation approval, state validation should be integrated with repository validation rather than left as prose-only guidance.

At minimum validate:

- both frontmatter blocks parse;
- supported `schema_version`;
- equal positive `generation`;
- legal enum values;
- exact queue header and one canonical queue table;
- unique queue IDs;
- dependency references exist and are acyclic;
- status/dependency/blocker invariants;
- `STATE.active_queue_items` exactly matches current relevant `IN_PROGRESS` rows;
- `STATE.next_queue_items` references actionable `TODO` rows;
- `STATE.blocked_queue_items` references relevant `BLOCKED` rows;
- project status is consistent with the current-gate queue condition except explicit `PAUSED`;
- `DONE` rows' declared completion artifacts exist where the artifact path is statically resolvable.

This can extend `scripts/validate_scaffold.py` or call a focused validator from it; the design does not require a specific internal implementation.

## Migration of existing durable files

The implementation pass must migrate current state without pretending work occurred.

- Existing `DONE` rows stay `DONE` only if their completion artifacts still exist.
- Existing `BLOCKED` rows stay `BLOCKED` with dependencies/blockers normalized into the new columns.
- Existing `TODO` rows are reclassified: keep `TODO` only when actually actionable; use `BLOCKED` when legacy access, unfinished queue dependencies, open questions, or gates prevent starting.
- No row becomes `IN_PROGRESS` merely because this schema is introduced.
- Current free-text `STATE.md` information is preserved in the Markdown body where useful, while status reason is separated from enum fields.
- The two current queue tables are merged into the one canonical schema without dropping legacy-independent rows or their completion artifacts.

## Integration with existing designs

- `docs/08-feature-artifact-validation.md` remains authoritative for feature lifecycle metadata.
- `docs/10-command-execution-contract.md` remains authoritative for command argument/input/output selection; this document supersedes its provisional queue/project-state vocabulary and supplies the exact state transition protocol.
- The phase-gate design remains authoritative for when `phase`/`current_gate` may advance.
- Issue #15 remains authoritative for resolving any artifact filename mismatch; this protocol does not choose a new feature artifact name.

If two canonical designs still disagree after those dependencies are merged, implementation stops instead of selecting whichever rule is convenient.

## Implementation requirements after design approval

The implementation pass should update together:

1. `migration/STATE.md` to the frontmatter schema;
2. `migration/QUEUE.md` to frontmatter + one canonical table + normalized dependencies/blockers;
3. `.opencode/agents/migration-coordinator.md` with generation check, source-of-truth precedence, ordered write/recovery behavior;
4. all six mutating command files with exact field-level `State updates` sections;
5. `migration-status.md` with read-only schema/generation consistency checks;
6. repository validation so malformed or inconsistent durable state fails CI.

Do not implement only the enum legends while leaving the commands and recovery rules ambiguous.

## Non-goals

This design does not:

- change migration business behavior;
- define phase-gate checklist contents;
- redefine feature lifecycle stages;
- add target application code;
- solve multi-process locking outside Git/optimistic generation checks;
- introduce cancellation/abandonment semantics; that requires a separate explicit design if needed.

## Acceptance criteria

Issue #14 design is complete when:

1. project and queue status enums are explicit;
2. `STATE.md` has a machine-readable authoritative section independent of prose;
3. `QUEUE.md` has one canonical parseable schema;
4. queue status meanings and allowed transitions are deterministic;
5. blocker/dependency representation is explicit;
6. feature, queue, open-question, and project state authorities cannot silently overwrite one another;
7. concurrent/stale and partial updates are detectable through shared generation;
8. write ordering and recovery are defined;
9. every command has an unambiguous future field-level state update behavior;
10. static validation requirements are sufficient to reject malformed/inconsistent durable state.
