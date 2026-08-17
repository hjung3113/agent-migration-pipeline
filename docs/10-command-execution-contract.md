# Command Execution Contract Design

Issue: #5 — `.opencode/commands/*.md` do not define deterministic arguments, preconditions, outputs, state updates, or failure behavior.

This is a design-only artifact. The seven command files are intentionally not changed in this pass because AGENTS.md rule 13 requires design approval before implementation.

## Goal

Make every migration command executable without inferring:

- what `$ARGUMENTS` means;
- which durable inputs must exist;
- where outputs are persisted;
- which queue/state records may change;
- when execution must stop rather than advance the pipeline.

Commands are phase entrypoints. Specialist agents perform delegated work, but the command contract owns invocation validation, prerequisite validation, expected durable outputs, and allowed state transitions.

## Adversarial findings

The issue is valid, but adding the same four headings mechanically to all seven commands would still leave important ambiguity.

1. `migration-status` is global and read-only. It should not require a feature ID or invent a status artifact merely for uniformity.
2. `migration-discover` can run before stable feature IDs exist, so a feature-only grammar would deadlock broad inventory discovery.
3. A feature ID cannot identify the queue row to update. Current queue items such as Q-004/Q-010 are broader than one feature.
4. A successful feature command must not mark a broad queue row `DONE` unless that row's own completion artifact is fully satisfied.
5. `migration/STATE.md` is project-level summary state. One blocked feature must not automatically block the whole project when other queue items remain actionable.
6. Issue #4 is now implemented by merged PR #25, so command input/output paths must align with the merged agent contracts rather than the pre-#4 prose.
7. Canonical feature paths still have one unresolved mismatch under issue #15: merged feature design uses `verification.md`, while the existing template is `verification-report.md`.
8. Phase-gate criteria remain a separate concern under issue #3. Commands should reference one authoritative gate checklist instead of copying subjective variants into each command.

## Argument contract

### `migration-discover`

```text
--queue <queue-id> --scope <legacy-scope> [--feature <feature-id>]
```

- `--queue` is required and must name an existing queue row.
- `--scope` is required and identifies the legacy source area to inspect.
- `--feature` is optional only for broad inventory/discovery queue items.
- when present, `<feature-id>` must match `^[a-z0-9]+(?:-[a-z0-9]+)*$`.
- display names are never accepted as identifiers.

### `migration-spec`, `migration-design`, `migration-implement`, `migration-review`, `migration-verify`

```text
--queue <queue-id> --feature <feature-id>
```

Both values are required exactly once. Unknown flags, duplicates, empty values, unknown queue IDs, and invalid feature IDs are invocation errors.

### `migration-status`

Accepts no arguments. Any non-empty `$ARGUMENTS` is an invocation error.

## Invocation failure rule

Malformed arguments fail before any durable write.

The command must:

1. stop immediately;
2. print the accepted syntax;
3. identify the invalid or missing argument;
4. leave `migration/QUEUE.md`, `migration/STATE.md`, feature artifacts, and open questions unchanged.

User input mistakes are not migration blockers.

## Common durable inputs

Before a mutating command advances work, the coordinator reads:

- `AGENTS.md`;
- `migration/STATE.md`;
- `migration/QUEUE.md`;
- `migration/RULEBOOK.md`;
- `docs/05-open-questions.md`;
- the queue row selected by `--queue`;
- feature artifacts required by that phase.

`migration-status` reads the same global state plus existing feature artifacts. Once issue #1 is implemented, it also runs the same structural feature-artifact validator and surfaces failures as process blockers.

## Queue selection and completion

`--queue` selects the only queue row a command may mutate.

Before changing it, the command verifies:

1. the row exists;
2. its phase/work item is compatible with the command;
3. its stated completion artifact is compatible with the command output;
4. this command run is sufficient to satisfy that completion artifact.

If condition 4 is false, valid feature artifacts may still be persisted, but the broad queue row remains incomplete.

Queue rows must never be selected by fuzzy text matching, nearest phase, or chat context.

## State ownership

### Feature state

After issue #1 is implemented, `migration/features/<feature-id>/feature-card.md` is the authoritative feature lifecycle state:

- `stage`: `discovered | specified | designed | implementing | reviewing | verifying | done`;
- `blocked`: independent boolean.

Until that metadata implementation exists, commands must not invent a parallel feature lifecycle field elsewhere.

### Queue state

`migration/QUEUE.md` tracks resumable work items. A command may update only the row selected by `--queue`.

Use the current repository vocabulary unless separately redesigned:

- `TODO`: actionable or incomplete;
- `BLOCKED`: a durable prerequisite/unknown prevents the selected work item;
- `DONE`: the row's stated completion artifact exists and its applicable gate passed.

Argument errors and transient tool failures do not change durable queue status unless they reveal a real prerequisite blocker.

### Project state

`migration/STATE.md` summarizes the overall phase/gate. Feature-local work updates project state only when it changes the project-level phase/gate or when no actionable work remains at the current gate.

## Open-question rule

Update `docs/05-open-questions.md` only for newly discovered unresolved facts that affect behavior, data integrity, DLL/platform constraints, security, deployment, or another design/verification decision.

Do not create an open question for malformed arguments, transient tool failures, or already-recorded blockers.

## Per-command contract

| Command | Required feature inputs | Durable outputs | Successful lifecycle result |
| --- | --- | --- | --- |
| `migration-discover` | existing feature card when feature-scoped; otherwise queue/scope | `feature-card.md`, `legacy-map.md`; conditional DB/DLL evidence reports | `discovered`; `blocked` reflects material unresolved discovery facts |
| `migration-spec` | `feature-card.md`, `legacy-map.md`, applicable DB/DLL evidence | `behavior-contract.md`; relevant open-question updates | `specified` only when design may validly begin |
| `migration-design` | feature card, legacy map, behavior contract, applicable evidence, gate decision | `target-feature-design.md` | `designed` only after the applicable design gate passes |
| `migration-implement` | approved behavior contract/design plus explicit user implementation gate | only code/config/test paths explicitly named by the approved target design; blocker/deviation updates in existing durable state | `implementing`; never self-approves review/verification |
| `migration-review` | contract, evidence, target design, exact implementation diff/changed paths | `review.md` | `reviewing`; PASS permits verification but not completion |
| `migration-verify` | contract, target design, review, implementation, available judges/evidence | canonical verification artifact from `migration/features/README.md` | enter `verifying`; only complete PASS may advance to `done` |
| `migration-status` | global state/queue/Rulebook/open questions/features | no durable output | no mutation |

All feature-local paths are under `migration/features/<feature-id>/`.

## Canonical path authority

Command files must not choose filenames independently.

Path authority is:

1. merged `migration/features/README.md` and `docs/08-feature-artifact-validation.md`;
2. merged issue #4 agent contracts for role ownership and conditional reports;
3. matching templates where names agree.

At the time of this design, the canonical verification artifact is `migration/features/<feature-id>/verification.md`. The still-existing `docs/templates/verification-report.md` mismatch is issue #15 work and must not cause command implementation to switch to `verification-report.md` locally.

## Preconditions and stop behavior

Gate checklist details belong to issue #3. Commands reference those authoritative checks rather than restating subjective phrases.

### `migration-discover`

Required:

- selected queue item is discovery/inventory work;
- legacy scope is identifiable and inspectable;
- output feature IDs do not collide with unrelated existing features.

Missing durable legacy access may block the selected queue item. A simple malformed scope argument does not.

### `migration-spec`

Required:

- feature exists;
- `legacy-map.md` exists;
- DB/DLL follow-up required by discovery is complete or explicitly recorded as a blocker/provisional evidence gap.

Materially unresolved behavior stops before design.

### `migration-design`

Required:

- behavior contract exists;
- applicable issue #3 gate passes;
- material unknowns affecting public contract, data model, platform boundary, or other medium/high lock-in decisions are resolved or explicitly allowed as provisional by the gate.

Failure stops before implementation.

### `migration-implement`

Required:

- behavior contract exists;
- target design exists and is approved;
- AGENTS.md rule 13 explicit user permission to implement the slice exists;
- implementation/test paths are named by the approved design;
- no blocker invalidates the approved design.

If any item fails, target code is not edited.

### `migration-review`

Required:

- implementation diff/changed paths exist;
- reviewer is independent from implementer;
- contract/evidence/design inputs needed to judge the implementation are readable.

Missing judge inputs produce `BLOCKED`, not a fabricated pass.

### `migration-verify`

Required:

- independent review exists;
- no unresolved blocking review finding remains;
- valid judges can exercise material behavior, or unexercised behavior is explicitly classified as residual uncertainty.

`FAIL`, `PARTIAL`, and `BLOCKED` never advance the feature to `done`.

### `migration-status`

No phase prerequisite. It reports durable repository state only and never infers progress from chat history.

## Failure classification

| Failure class | Durable mutation |
| --- | --- |
| invocation/argument error | none |
| transient tool/runtime failure | none unless a durable blocker is discovered |
| missing durable prerequisite | selected queue item may become `BLOCKED`; feature `blocked: true` once metadata exists |
| newly discovered unknown fact | update open questions; block only affected scope when material |
| implementation/review/verification defect | persist applicable report/evidence and route through failure loop; do not mark completion |
| successful execution | persist canonical output; update lifecycle/queue only as justified by the selected row and gate |

## Dependency ordering

Issue #5 implementation must be consistent with:

- issue #1: feature lifecycle metadata and structural artifact validation;
- issue #3: deterministic phase-gate checklists;
- issue #4: merged specialist agent input/output and write-ownership contracts;
- issue #15: remaining artifact/template filename alignment.

If two source-of-truth contracts disagree, implementation stops until the contradiction is resolved.

## Implementation requirements after design approval

All seven `.opencode/commands/*.md` files should be updated together so the repository never runs under a mixed command contract.

Each must contain explicit sections equivalent to:

- `Arguments`;
- `Inputs`;
- `Preconditions`;
- `Outputs`;
- `State updates`;
- `Failure behavior`.

The implementation should also add a structural check that all seven command files contain the required contract sections and that referenced canonical artifact paths agree with the feature-artifact design. That check validates structure/path consistency, not semantic correctness.

## Non-goals

This design does not:

- modify command implementation files;
- redefine the merged issue #4 agent procedures;
- define issue #3 gate checklist contents;
- resolve issue #15's remaining template filename conflict;
- implement issue #1 lifecycle metadata;
- invent new queue status values;
- define feature-specific business behavior.

## Acceptance criteria

Issue #5 design is complete when:

1. argument grammar is deterministic for discovery, feature lifecycle, and status commands;
2. malformed arguments cause zero durable writes;
3. every mutating command selects an explicit queue row;
4. per-command required inputs and durable outputs are exact;
5. feature, queue, and project state ownership are separated;
6. broad queue rows cannot be falsely completed by one feature run;
7. precondition failures have explicit stop behavior;
8. status is explicitly read-only;
9. canonical path conflicts are treated as dependency work rather than silently resolved;
10. later command implementation must align with the final gate/artifact contracts before completion.
