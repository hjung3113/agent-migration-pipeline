---
description: Implement one feature whose behavior contract and target design have passed their gates.
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
are never identifiers.

## Inputs

Read `AGENTS.md`, `migration/STATE.md`, `migration/QUEUE.md`,
`migration/RULEBOOK.md`, `docs/05-open-questions.md`, the selected queue row,
and the phase-required artifacts. Validate the STATE/QUEUE schema and equal
positive `generation` before any durable mutation.

The approved feature inputs are
`migration/features/<feature-id>/feature-card.md`,
`migration/features/<feature-id>/behavior-contract.md`, and
`migration/features/<feature-id>/target-feature-design.md`, plus the evidence
and gate records named by that design. Existing canonical review and
verification artifacts, when present, are
`migration/features/<feature-id>/review.md` and
`migration/features/<feature-id>/verification.md`.

## Preconditions

The coordinator must verify that:

- `migration/features/<feature-id>/behavior-contract.md` exists;
- `migration/features/<feature-id>/target-feature-design.md` exists and is
  approved;
- the applicable G3 gate passes, including its implementation authorization
  criterion;
- AGENTS.md rule 13's explicit user permission to implement this slice is
  present and persisted as the implementation authorization;
- the approved design names the implementation/test paths and no blocker
  invalidates that design;
- the selected queue row is implementation work, its phase/work item and
  completion artifact are compatible, and this run can satisfy that artifact.

If any item fails, do not edit target code and do not start the selected queue
row, except for a protocol-required durable blocker recording.

## Outputs

Delegate only after the preconditions pass. Persist changes only in the code,
configuration, and test paths explicitly named by
`migration/features/<feature-id>/target-feature-design.md`, together with
applicable deviations or blocker evidence in already-authorized durable state.

The feature lifecycle result is `stage: implementing`; it never self-approves
review or verification. The selected queue row remains incomplete unless this
run satisfies its declared completion artifact and applicable condition.

## State updates

Only the selected `--queue` row may be changed:

1. Invocation errors or failed preconditions before durable work cause no
   queue/project transaction, except for a protocol-required durable blocker.
2. Immediately before the first durable mutation, transition `TODO ->
   IN_PROGRESS`.
3. A durable blocker discovered after start transitions `IN_PROGRESS ->
   BLOCKED` with the protocol's dependency/OQ/gate/`EXT:`/`HUMAN:` reference,
   then derives STATE.
4. A transient post-start failure retains `IN_PROGRESS`; never fabricate
   `BLOCKED`.
5. Mark `DONE` only when the selected row's full completion condition is
   satisfied; otherwise retain `IN_PROGRESS`.
6. Derive project `status` from current queue actionability and specific facts;
   do not copy feature, queue, or gate status into project state.

Persist valid implementation/deviation evidence first, write
`migration/QUEUE.md` at generation `N+1`, derive the summary, and write
`migration/STATE.md` last at `N+1`. Re-evaluate gates only through
`docs/02-migration-pipeline.md`; implementation does not invent a new gate
result. Feature `stage`/`blocked` remains owned by
`migration/features/<feature-id>/feature-card.md`.

## Failure behavior

Malformed arguments print the accepted syntax and identify the invalid or
missing argument, with zero durable writes. Missing implementation
authorization or another precondition means target code is not edited.

For execution failures, use the shared contracts:

- pre-start transient failure: no mutation;
- post-start transient/runtime failure: retain selected row `IN_PROGRESS` and
  preserve only validly produced changes;
- durable prerequisite, approval, contradiction, or blocking unknown: apply
  the STOP classification and the narrowest affected queue/feature blocker;
- implementation defects or deviations: persist the applicable evidence and
  keep the row incomplete; do not fabricate review or verification success;
- project `status` is derived from queue actionability and is not made
  `BLOCKED` merely because one feature is blocked.

Update `docs/05-open-questions.md` only for a newly discovered unresolved fact
that affects behavior, integrity, platform/DLL constraints, security,
deployment, or a design/verification decision. Reuse an equivalent OQ. Do not
create one for malformed input, transient failure, missing artifact alone,
missing approval alone, or an already-recorded blocker.
