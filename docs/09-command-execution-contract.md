# Command Execution Contract Design

Issue: #5 — migration commands do not define deterministic arguments, preconditions, outputs, state updates, or failure behavior.

This document defines the design only. `.opencode/commands/*.md` are implementation artifacts and are intentionally not changed in this pass because AGENTS.md rule 13 requires design approval before implementation.

## Goal

Make every migration command executable by a low-reasoning coordinator without inferring:

- what `$ARGUMENTS` means;
- which durable inputs must exist;
- where outputs must be persisted;
- which queue/state records may change;
- when the command must stop instead of advancing the pipeline.

The command layer is an entrypoint contract. Specialist agents may do the work, but the command remains responsible for validating invocation and phase preconditions and for defining the durable result expected from the coordinator.

## Adversarial findings

The issue identifies the correct failure mode, but applying the suggested sections mechanically is insufficient.

1. `migration-status` is read-only and global. Requiring a feature ID or a durable output file for all seven commands would invent work and make the contract less accurate.
2. `migration-discover` can operate on a broad legacy scope before a stable feature ID exists. A feature-only argument grammar would deadlock initial inventory work.
3. A feature ID alone cannot deterministically identify the `migration/QUEUE.md` row to update. The current queue contains broad items such as Q-004 and Q-010, so commands must receive or resolve an explicit queue item rather than guessing by phase.
4. A queue row must not be marked `DONE` merely because one feature command succeeded. The row's own completion artifact must be satisfied; broad queue rows may require multiple command runs or later decomposition.
5. `STATE.md` is project-level summary state, not feature state. A feature-local blocker must not automatically mark the whole migration project blocked when other queue items remain actionable.
6. Canonical artifact naming is currently inconsistent across merged design and existing templates. `migration/features/README.md` and `docs/08-feature-artifact-validation.md` define `verification.md`, while `docs/templates/verification-report.md` and open PR #25 use `verification-report.md`. Commands must not choose a filename by local preference.
7. Phase-gate wording is still qualitative under issue #3. Command files should reference one authoritative gate definition rather than duplicate slightly different heuristics in seven places.
8. Open PR #25 for issue #4 changes agent input/output contracts. Command implementation must be aligned with the final merged agent contract, not with the current short agent prose or a stale PR snapshot.

## Command classes

There are three command classes.

### 1. Discovery command

`migration-discover` may operate on either a broad inventory scope or one known feature.

Canonical argument envelope:

```text
--queue <queue-id> --scope <legacy-scope> [--feature <feature-id>]
```

Rules:

- `--queue` is required and must match an existing queue row.
- `--scope` is required and must identify the legacy source area to inspect.
- `--feature` is optional only when the queue item is explicitly an inventory/discovery item whose completion artifact allows multiple feature cards.
- when `--feature` is supplied, it must match `^[a-z0-9]+(?:-[a-z0-9]+)*$`.
- display names are never accepted as identifiers.

### 2. Feature lifecycle commands

`migration-spec`, `migration-design`, `migration-implement`, `migration-review`, and `migration-verify` operate on one feature.

Canonical argument envelope:

```text
--queue <queue-id> --feature <feature-id>
```

Rules:

- both arguments are required exactly once;
- unknown flags, duplicate flags, empty values, unknown queue IDs, and invalid feature IDs are invocation errors;
- `<feature-id>` is the directory/metadata ID, never a human-readable feature name.

### 3. Status command

`migration-status` accepts no arguments.

Any non-empty `$ARGUMENTS` is an invocation error. It is read-only and produces terminal/chat output only; it does not create a status artifact merely to satisfy a generic output rule.

## Common invocation failure rule

Malformed or incomplete arguments fail before any repository write.

On invocation error the command must:

1. stop immediately;
2. print the exact accepted syntax for that command;
3. name the invalid/missing argument;
4. make no change to `migration/QUEUE.md`, `migration/STATE.md`, feature artifacts, or open questions.

User input mistakes are not durable migration blockers.

## Common durable inputs

Before a mutating command advances work, the coordinator reads:

- `AGENTS.md`;
- `migration/STATE.md`;
- `migration/QUEUE.md`;
- `migration/RULEBOOK.md`;
- `docs/05-open-questions.md`;
- the selected queue row;
- the feature artifacts required by that command, when feature-scoped.

`migration-status` reads the same global files plus existing feature artifacts and the structural validator result once issue #1 is implemented.

## Queue-item contract

The `--queue` value selects the only queue row the command may mutate.

A command must verify all of the following before changing that row:

1. the row exists;
2. its phase/work item is compatible with the command;
3. its completion artifact is compatible with the command output;
4. completing one command run is sufficient to satisfy the row, or the row explicitly represents a broader work item that must remain incomplete.

If condition 4 is false, the command may persist valid feature artifacts but must not mark the broad queue row `DONE`.

Command implementation must never select a queue row by fuzzy text matching, nearest phase, or chat context.

## State ownership

Durable state has three different scopes.

### Feature state

Once issue #1's metadata design is implemented, `migration/features/<feature-id>/feature-card.md` is the authoritative feature lifecycle state:

- `stage`: `discovered | specified | designed | implementing | reviewing | verifying | done`;
- `blocked`: independent boolean.

Until that metadata implementation lands, commands must not simulate the same state by inventing alternate fields elsewhere.

### Queue state

`migration/QUEUE.md` records resumable work-item state. A command may update only the row selected by `--queue`.

Use the repository's existing status vocabulary unless a separate design changes it. In this design that means:

- `TODO`: work remains actionable or incomplete;
- `BLOCKED`: a durable prerequisite/unknown prevents the selected work item from proceeding;
- `DONE`: the row's stated completion artifact exists and its applicable gate has passed.

A command failure does not imply `BLOCKED`. Argument errors, tool failures, or partial execution that can simply be retried leave the durable work state unchanged unless they reveal a real prerequisite blocker.

### Project state

`migration/STATE.md` summarizes the overall migration phase/gate.

Feature-local work must update project state only when it changes the project-level phase/gate or when the current gate has no actionable work remaining. A single blocked feature does not make the entire project blocked if other valid queue items remain.

## Open-question rule

A command creates or updates `docs/05-open-questions.md` only when execution discovers an unresolved fact that affects behavior, data integrity, platform/DLL constraints, security, deployment, or another design/verification decision.

Do not create an open question for malformed arguments, missing optional files, transient tool failures, or already-known blockers.

## Per-command contract

| Command | Required feature inputs | Durable outputs | Successful lifecycle result |
| --- | --- | --- | --- |
| `migration-discover` | existing feature card when feature-scoped; otherwise selected queue/scope | `migration/features/<feature-id>/feature-card.md`, `legacy-map.md`; conditional DB/DLL evidence reports where applicable | `stage: discovered`; `blocked` reflects unresolved material discovery facts |
| `migration-spec` | `feature-card.md`, `legacy-map.md`, applicable DB/DLL evidence | `migration/features/<feature-id>/behavior-contract.md`; open-question updates when needed | `stage: specified` only when the behavior contract is sufficient to enter the design gate |
| `migration-design` | `feature-card.md`, `legacy-map.md`, `behavior-contract.md`, applicable evidence, gate decision | `migration/features/<feature-id>/target-feature-design.md` | `stage: designed` only after the applicable design gate passes; provisional/blocking designs do not open implementation |
| `migration-implement` | approved `behavior-contract.md`, approved `target-feature-design.md`, explicit user implementation gate | only code/config/test paths explicitly named by the approved target design; durable blocker/deviation updates in existing state/open-question artifacts | `stage: implementing`; implementation success never self-approves review or verification |
| `migration-review` | behavior contract, evidence, target design, exact implementation diff/changed paths | `migration/features/<feature-id>/review.md` | `stage: reviewing`; `PASS` permits verification but does not mark the feature done |
| `migration-verify` | behavior contract, target design, review, implementation, available judges/evidence | canonical verification artifact from `migration/features/README.md` | enter `stage: verifying`; only a complete `PASS` may advance to `stage: done` |
| `migration-status` | global state + queue + Rulebook + open questions + feature artifacts | no durable output | no state mutation |

## Canonical path authority

Command files must not embed a filename that conflicts with the repository's canonical feature-artifact design.

Until issue #15 is resolved, path authority is:

1. merged `migration/features/README.md` and `docs/08-feature-artifact-validation.md` for canonical feature filenames;
2. matching templates where names agree;
3. unresolved template/name mismatches are blockers for command implementation, not permission to choose a competing filename.

At the time of this design, the canonical merged verification filename is `migration/features/<feature-id>/verification.md`. The existing `docs/templates/verification-report.md` and open PR #25's `verification-report.md` contract must be reconciled before command implementation is treated as complete.

## Preconditions and stop behavior by phase

Each command must implement explicit yes/no preconditions. Gate details belong to the authoritative phase-gate design from issue #3; command files reference those gate IDs/checklists rather than restating subjective phrases.

Minimum command-local preconditions are:

### `migration-discover`

- selected queue item is a discovery/inventory item;
- legacy scope is identifiable and inspectable;
- output feature IDs do not collide with unrelated existing feature directories.

If legacy source/evidence is unavailable, mark the selected queue item `BLOCKED` only when the absence is a real durable prerequisite; record the corresponding open question when it is an unknown fact rather than simple missing access.

### `migration-spec`

- feature exists;
- `legacy-map.md` exists;
- required DB/DLL follow-up identified by discovery is complete or explicitly recorded as a blocker/provisional evidence gap.

If material behavior cannot be specified, persist the partial contract if useful, set feature `blocked: true` after issue #1 metadata is implemented, keep/mark the queue item `BLOCKED`, and stop before design.

### `migration-design`

- behavior contract exists;
- applicable issue #3 design-gate checklist passes;
- material unknowns that affect public contract, data model, platform boundary, or other medium/high lock-in decisions are resolved or explicitly permitted as provisional by the gate.

Failure stops before target implementation work.

### `migration-implement`

- behavior contract exists;
- target design exists and is approved;
- AGENTS.md rule 13 explicit user implementation permission is present for the slice;
- implementation/test paths are named by the approved design;
- no blocking review/design/open-question state invalidates the design.

If any item fails, do not edit target code.

### `migration-review`

- implementation diff/changed paths exist;
- reviewer is independent from the implementer;
- contract, evidence, and target design required to judge the implementation are readable.

Missing judge inputs produce `BLOCKED`, not a fabricated review pass.

### `migration-verify`

- independent review exists;
- no unresolved blocking review finding remains;
- at least one valid judge can exercise each material behavior or the unexercised behavior is explicitly classified as residual uncertainty.

`FAIL`, `PARTIAL`, or `BLOCKED` never advance the feature to `done`.

### `migration-status`

- no phase precondition;
- report durable repository state only;
- once issue #1 implementation exists, run the same structural validator first and surface validation failures as process blockers.

## Failure classification

Command implementations classify failures before updating durable state.

| Failure class | Durable mutation |
| --- | --- |
| invocation/argument error | none |
| transient tool/runtime failure | none unless it reveals a durable blocker |
| missing durable prerequisite | selected queue item may become `BLOCKED`; feature `blocked: true` when metadata exists |
| newly discovered unknown fact | update open questions; block only the affected scope when material |
| implementation/review/verification defect | persist the produced report/evidence and route through the failure loop; do not mark completion |
| successful command execution | persist canonical output; update lifecycle/queue only to the extent justified by the selected row and gate |

## Dependency ordering

Command implementation for issue #5 is not standalone. It must be reconciled with:

- issue #1: feature lifecycle metadata and structural artifact validation;
- issue #3: deterministic phase-gate checklists;
- issue #4 / PR #25: specialist agent input/output contracts and write ownership;
- issue #15: canonical template/feature filename alignment.

The command layer should reference these source-of-truth contracts rather than duplicate them. If two dependencies disagree, implementation stops until the contradiction is resolved.

## Implementation requirements after design approval

The later implementation pass should update all seven `.opencode/commands/*.md` together so no command runs under a mixed contract.

Each command file must have explicit sections equivalent to:

- `Arguments`;
- `Inputs`;
- `Preconditions`;
- `Outputs`;
- `State updates`;
- `Failure behavior`.

The implementation should also add a structural check that all seven command files contain the required contract sections and that referenced canonical artifact paths agree with the feature-artifact design. The validator should check structure/path references, not attempt to prove semantic correctness.

## Non-goals

This design does not:

- modify command or agent implementation files;
- resolve issue #3's gate checklist contents;
- resolve issue #15's filename conflict;
- implement issue #1 lifecycle metadata;
- invent new queue status values;
- define business-feature-specific behavior.

## Acceptance criteria

The issue #5 design is complete when:

1. argument grammar is deterministic for discovery, feature lifecycle, and status commands;
2. malformed arguments cause zero durable writes;
3. every mutating command selects an explicit queue row rather than guessing;
4. per-command required inputs and durable outputs are exact;
5. feature, queue, and project state ownership are separated;
6. broad queue rows cannot be falsely completed by one feature run;
7. phase/precondition failures have explicit stop behavior;
8. status is explicitly read-only;
9. canonical path conflicts are treated as dependency blockers rather than silently resolved;
10. later command implementation is required to align with the final agent/gate/artifact contracts before it can be considered complete.
