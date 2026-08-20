---
description: Discover legacy behavior and dependencies for a scope before migration design.
agent: migration-coordinator
---

## Arguments

Accepted syntax:

```text
--queue <queue-id> --scope <legacy-scope> [--feature <feature-id>]
```

`--queue` and `--scope` are required exactly once. `<queue-id>` must identify
an existing `Q-###` or `S-###` queue row; `<legacy-scope>` is the non-empty
legacy source area to inspect. `--feature` is optional only for a broad
inventory/discovery queue item and, when present, must match
`^[a-z0-9]+(?:-[a-z0-9]+)*$`. Display names are never identifiers.

Unknown flags, duplicate flags, empty values, an unknown queue ID, or an
invalid feature ID are invocation errors.

## Inputs

Before mutating work advances, read `AGENTS.md`, `migration/STATE.md`,
`migration/QUEUE.md`, `migration/RULEBOOK.md`, `docs/05-open-questions.md`,
the selected queue row, and the phase-required artifacts. Validate the
STATE/QUEUE schema and their equal positive `generation` using
`docs/11-durable-state-protocol.md` before any durable mutation.

For a feature-scoped run, the feature directory is
`migration/features/<feature-id>/` and its existing
`migration/features/<feature-id>/feature-card.md` is an input. A broad run
may create feature cards. Use the canonical artifact names
`migration/features/<feature-id>/legacy-map.md`,
`migration/features/<feature-id>/behavior-contract.md`,
`migration/features/<feature-id>/target-feature-design.md`,
`migration/features/<feature-id>/review.md`, and
`migration/features/<feature-id>/verification.md` when existing artifacts are
read.

If the scope touches the platform boundary or MSSQL, read the applicable
project evidence under `migration/evidence/` and the matching templates under
`docs/templates/`. Do not infer a DLL contract from unavailable access.

## Preconditions

The coordinator must verify that:

- the selected queue item is discovery/inventory work;
- `<legacy-scope>` is identifiable and inspectable, subject to the applicable
  G0 checklist in `docs/02-migration-pipeline.md`;
- output feature IDs do not collide with unrelated existing features;
- the selected row's phase/work item and completion artifact are compatible
  with this command's discovery outputs; this run may produce a valid partial
  step toward that artifact.

The full completion artifact and applicable gate condition are checked only
when marking the row `DONE`, not as a precondition to starting this run.

If a precondition cannot be safely satisfied, STOP before durable work unless
the STOP/state protocols require recording a durable blocker on the selected
row. Do not begin broad feature discovery while the applicable G0 gate forbids
it; perform only gate-enabling inspection allowed by the canonical checklist.

## Outputs

Persist the applicable canonical feature artifacts:

- `migration/features/<feature-id>/feature-card.md`;
- `migration/features/<feature-id>/legacy-map.md`;
- conditional project evidence such as `migration/evidence/dll-boundary-report.md`,
  `migration/evidence/observable-output-survey.md`, or
  `migration/evidence/db-dependency-report.md` when the inspected scope
  requires it.

The feature lifecycle result is `stage: discovered`; `blocked` is an
independent feature-local boolean reflecting material unresolved discovery
facts. Do not implement target code. A broad queue row remains incomplete
unless this run satisfies its own declared completion artifact.

## State updates

The selected `--queue` row is the only queue row this command may mutate.
Apply the common rules from `docs/11-durable-state-protocol.md`:

1. Invocation errors and failed preconditions before durable work cause no
   queue/project transaction, unless the precondition check itself establishes
   a durable blocker under the STOP contract.
2. Immediately before the first durable mutation, transition the selected row
   `TODO -> IN_PROGRESS`.
3. After work starts, a durable blocker transitions
   `IN_PROGRESS -> BLOCKED` with its `OQ-###`, dependency, gate criterion,
   `EXT:`, or `HUMAN:` reference; then derive `STATE.md`.
4. A transient failure after durable work starts retains `IN_PROGRESS` and
   never fabricates `BLOCKED`.
5. Transition to `DONE` only when this run satisfies the selected row's full
   completion artifact and applicable gate/completion condition; otherwise
   retain `IN_PROGRESS`.
6. Recompute project state from the newly persisted feature/queue/gate/STOP
   facts. Never copy feature, queue, or gate strings into project `status`.

Persist feature artifacts first, write `migration/QUEUE.md` at generation
`N+1`, derive the project summary, and write `migration/STATE.md` last at the
same generation. Re-evaluate the applicable G0 checklist through
`docs/02-migration-pipeline.md` when this run produces gate evidence; store
`current_gate`, `gate_result`, and `failed_gate_criteria` through that same
transaction. Feature `stage`/`blocked` remains owned by
`migration/features/<feature-id>/feature-card.md`.

## Failure behavior

Malformed arguments fail immediately: print the accepted syntax, identify the
invalid or missing argument, and leave `migration/QUEUE.md`,
`migration/STATE.md`, feature artifacts, and open questions unchanged. User
input mistakes are not migration blockers.

Classify all later failures through `docs/11-stop-condition-contract.md` and
persist state through `docs/11-durable-state-protocol.md`:

- a transient failure before durable start changes nothing;
- a transient failure after durable start retains the selected row
  `IN_PROGRESS` and keeps only validly produced artifacts;
- a missing durable prerequisite blocks the selected row only when the
  protocol's blocker rule applies;
- a newly discovered material fact uses OQ deduplication and blocks only the
  affected scope; it must not blanket-block unrelated project work;
- a gate, contradiction, or missing-evidence STOP records the exact gate/STOP
  outcome without inventing a second taxonomy;
- valid artifacts may remain persisted after an incomplete run, but the queue
  row cannot be marked `DONE` merely because the command returned.

Update `docs/05-open-questions.md` only for a newly discovered unresolved fact
that affects behavior, data integrity, DLL/platform constraints, security,
deployment, or another design/verification decision. Reuse an equivalent
existing OQ. Do not create an OQ for malformed arguments, transient failures,
missing artifacts alone, missing approval alone, or an already-recorded
blocker.
