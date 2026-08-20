---
description: Build or refine an evidence-graded behavior contract for one discovered feature.
agent: migration-coordinator
---

## Arguments

Accepted syntax:

```text
--queue <queue-id> --feature <feature-id>
```

Both flags are required exactly once. `<queue-id>` must name an existing
`Q-###` or `S-###` row, and `<feature-id>` must match
`^[a-z0-9]+(?:-[a-z0-9]+)*$`. Display names are never identifiers. Unknown
flags, duplicates, empty values, unknown queue IDs, or invalid feature IDs are
invocation errors.

## Inputs

Read `AGENTS.md`, `migration/STATE.md`, `migration/QUEUE.md`,
`migration/RULEBOOK.md`, `docs/05-open-questions.md`, the selected queue row,
and the phase-required artifacts. Validate the STATE/QUEUE schema and equal
positive `generation` before durable work begins, using
`docs/11-durable-state-protocol.md`.

The feature directory is `migration/features/<feature-id>/`. Required inputs
are `migration/features/<feature-id>/feature-card.md` and
`migration/features/<feature-id>/legacy-map.md`, plus applicable
`migration/evidence/` DB/DLL reports and referenced evidence records. The
canonical artifact set also includes
`migration/features/<feature-id>/behavior-contract.md`,
`migration/features/<feature-id>/target-feature-design.md`,
`migration/features/<feature-id>/review.md`, and
`migration/features/<feature-id>/verification.md`; do not substitute another
filename.

## Preconditions

The coordinator must verify that:

- the feature exists and its feature card is readable;
- `migration/features/<feature-id>/legacy-map.md` exists;
- DB/DLL follow-up required by discovery is complete or explicitly recorded
  as a blocker or provisional evidence gap;
- the selected queue row is specification work, and its phase/work item and
  completion artifact are compatible with this command's outputs; this run
  may produce a valid partial step toward that artifact.

The full completion artifact and applicable gate condition are checked only
when marking the row `DONE`, not as a precondition to starting this run.

Materially unresolved behavior stops before design. A failed precondition does
not start the selected row unless the STOP/state protocols require recording a
durable blocker on that row.

## Outputs

Write or update `migration/features/<feature-id>/behavior-contract.md` from
`docs/templates/behavior-contract.md`, with evidence grades and references.
Evaluate G2 exactly through the canonical criteria in
`docs/02-migration-pipeline.md` and persist relevant open-question updates.

The feature lifecycle result is `stage: specified` only when design may
validly begin. `blocked` remains an independent feature-local boolean. The
selected queue row is complete only when its own declared completion artifact
and applicable gate condition are fully satisfied.

## State updates

Only the selected `--queue` row may be changed. Apply the common durable-state
rules:

1. Invocation errors and failed preconditions before durable work cause no
   queue/project transaction, except for a protocol-required durable blocker.
2. Immediately before the first durable mutation, transition `TODO ->
   IN_PROGRESS` on the selected row.
3. A durable blocker found after start transitions `IN_PROGRESS -> BLOCKED`
   with the protocol's dependency, `OQ-###`, gate, `EXT:`, or `HUMAN:`
   reference, then derives STATE.
4. A transient post-start failure retains `IN_PROGRESS`; it never fabricates
   `BLOCKED`.
5. Mark `DONE` only when the selected row's full completion condition is
   satisfied; otherwise retain `IN_PROGRESS`.
6. Derive project `status` from queue actionability and persisted specific
   facts; never copy feature, queue, or gate status strings into it.

Persist the behavior contract and OQ/gate evidence first, write
`migration/QUEUE.md` at generation `N+1`, derive the summary, and write
`migration/STATE.md` last at `N+1`. Re-evaluate G2 and store its
`current_gate`, `gate_result`, and `failed_gate_criteria` through that same
transaction. The feature card owns `stage` and feature-local `blocked`.

## Failure behavior

For malformed arguments, print the accepted syntax and the invalid or missing
argument, then make zero durable writes to queue, state, feature artifacts, or
open questions. Such mistakes are not migration blockers.

Use `docs/11-stop-condition-contract.md` for STOP classification and
`docs/11-durable-state-protocol.md` for the resulting mutation:

- pre-start transient failures change nothing;
- post-start transient failures retain `IN_PROGRESS` and preserve only valid
  artifacts;
- missing durable prerequisites block only when the queue/STOP protocol says
  the selected row is durably prevented from proceeding;
- an unresolved material behavior fact is deduplicated/reused as an OQ and
  blocks only its affected scope;
- gate, contradiction, missing-evidence, and defect outcomes stop the affected
  advance without inventing a competing STOP taxonomy;
- an incomplete behavior contract never marks a broad queue row `DONE`.

Update `docs/05-open-questions.md` only for a newly discovered unresolved fact
that affects behavior, integrity, platform/DLL constraints, security,
deployment, or a design/verification decision. Reuse an equivalent OQ. Do not
create one for malformed arguments, transient failures, missing artifacts by
themselves, missing approval by itself, or an already-recorded blocker.
