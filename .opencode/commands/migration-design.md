---
description: Design one approved feature for React, FastAPI, PostgreSQL, and the platform compatibility boundary.
agent: migration-coordinator
---

## Arguments

Accepted syntax:

```text
--queue <queue-id> --feature <feature-id>
```

Both flags are required exactly once. `<queue-id>` must name an existing
`Q-###` or `S-###` row, and `<feature-id>` must match
`^[a-z0-9]+(?:-[a-z0-9]+)*$`. Unknown flags, duplicates, empty values,
unknown queue IDs, or invalid feature IDs are invocation errors; display names
are not accepted as identifiers.

## Inputs

Read `AGENTS.md`, `migration/STATE.md`, `migration/QUEUE.md`,
`migration/RULEBOOK.md`, `docs/05-open-questions.md`, the selected queue row,
and the phase-required artifacts. Validate equal positive STATE/QUEUE
`generation` and the schema/transaction protocol before durable work.

All feature-local artifacts are under `migration/features/<feature-id>/`.
Required design inputs are `migration/features/<feature-id>/feature-card.md`,
`migration/features/<feature-id>/legacy-map.md`,
`migration/features/<feature-id>/behavior-contract.md`, and applicable
evidence records or project reports. The related canonical lifecycle artifacts
are `migration/features/<feature-id>/target-feature-design.md`,
`migration/features/<feature-id>/review.md`, and
`migration/features/<feature-id>/verification.md`.

## Preconditions

The coordinator must verify that:

- `migration/features/<feature-id>/behavior-contract.md` exists and is
  readable;
- the applicable issue #3 gate criteria in `docs/02-migration-pipeline.md`
  pass;
- material unknowns affecting the public contract, data model, platform
  boundary, or another medium/high lock-in decision are resolved or explicitly
  allowed as provisional by that gate;
- the selected queue row is design work, its phase/work item and completion
  artifact are compatible, and this run can satisfy the artifact before it is
  completed.

If any precondition fails, stop before `TODO -> IN_PROGRESS` unless the
protocol requires a durable blocker on the selected row. Do not dispatch
implementation from this command.

## Outputs

Delegate design using the approved role contract and write
`migration/features/<feature-id>/target-feature-design.md` from
`docs/templates/target-feature-design.md`. Require the legacy-structure
rejection evidence from `docs/13-legacy-structure-rejection-contract.md`,
including a complete LSR-01..LSR-07 disposition.

The feature lifecycle result is `stage: designed` only after the applicable
design gate passes. `blocked` remains feature-local. A design result does not
authorize target-code edits or complete a broad queue row unless that row's
declared completion condition is satisfied.

## State updates

Only the selected `--queue` row may be mutated:

1. Invocation errors and failed preconditions before durable work cause no
   queue/project transaction, except for a protocol-required durable blocker.
2. Immediately before the first durable mutation, transition `TODO ->
   IN_PROGRESS`.
3. After start, a durable blocker transitions `IN_PROGRESS -> BLOCKED` with
   its canonical dependency/OQ/gate/`EXT:`/`HUMAN:` reference, then derives
   STATE.
4. A transient failure after start retains `IN_PROGRESS`, never `BLOCKED`.
5. Mark `DONE` only when the selected design row's full completion artifact
   and applicable condition are satisfied; otherwise retain `IN_PROGRESS`.
6. Derive project `status` from current-phase queue actionability; it must not
   mirror feature, queue, or `gate_result` values.

Persist design and gate evidence first, write `migration/QUEUE.md` at
generation `N+1`, derive the project summary, and write `migration/STATE.md`
last at `N+1`. Store the G3 `current_gate`, `gate_result`, and
`failed_gate_criteria` through that transaction. Feature `stage`/`blocked`
remains owned by `migration/features/<feature-id>/feature-card.md`.

## Failure behavior

Malformed arguments print the accepted syntax and the invalid or missing
argument, then perform no durable writes. They are invocation failures, not
migration blockers.

STOP and state outcomes follow the canonical contracts:

- a pre-start failure leaves queue, state, features, and OQs unchanged unless
  a durable blocker is explicitly required;
- a post-start transient failure retains `IN_PROGRESS`;
- design-blocking unknowns use OQ deduplication and block only the affected
  feature/queue scope;
- a failed gate, contradiction, or missing evidence stops before implementation
  and persists only the exact applicable gate/STOP outcome;
- no command result can self-approve implementation, review, or verification.

Add an entry to `docs/05-open-questions.md` only for a newly discovered
unresolved fact that affects a design or verification decision, data integrity,
platform/DLL behavior, security, or deployment. Reuse equivalent OQs; do not
create OQs for malformed input, transient failure, missing artifact alone,
missing approval alone, or an already-recorded blocker.
