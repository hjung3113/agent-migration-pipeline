---
description: Run an independent adversarial review of an implemented migration feature.
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
unknown queue IDs, and invalid feature IDs are invocation errors. Display names
are not identifiers.

## Inputs

Read `AGENTS.md`, `migration/STATE.md`, `migration/QUEUE.md`,
`migration/RULEBOOK.md`, `docs/05-open-questions.md`, the selected queue row,
and the phase-required artifacts. Validate the STATE/QUEUE schema and equal
positive `generation` before durable work.

The review inputs are the feature's
`migration/features/<feature-id>/feature-card.md`,
`migration/features/<feature-id>/legacy-map.md`,
`migration/features/<feature-id>/behavior-contract.md`,
`migration/features/<feature-id>/target-feature-design.md`, exact
implementation diff/changed paths, and the applicable evidence records. The
canonical review and later verification artifacts are
`migration/features/<feature-id>/review.md` and
`migration/features/<feature-id>/verification.md`.

## Preconditions

The coordinator must verify that:

- an implementation diff and changed paths exist;
- the reviewer is independent from the implementer;
- the contract, evidence, target design, and Rulebook inputs needed to judge
  the implementation are readable;
- the selected queue row is review work, and its phase/work item and
  completion artifact are compatible with this command's `review.md` output;
  this run may produce a valid partial step toward that artifact.

For a combined review/verification row, `review.md` is the legitimate first
step and `verification.md` is produced by a later `migration-verify` run. The
full completion artifact and applicable gate condition are checked only when
marking the row `DONE`, not as a precondition to starting this run.

Missing judge inputs produce `BLOCKED`, not a fabricated pass. Do not select a
queue row by fuzzy text, nearest phase, or chat context.

## Outputs

Delegate to `adversarial-reviewer` and persist
`migration/features/<feature-id>/review.md` from
`docs/templates/review.md`. The report must preserve the independent review
result and findings; do not auto-approve.

The feature lifecycle result is `stage: reviewing`. A review PASS permits
verification but does not complete a broad review-plus-verification queue row.
Feature `blocked` remains independent of queue and project status.

## State updates

Only the selected `--queue` row may mutate:

1. Invocation errors and failed preconditions before durable work cause no
   queue/project transaction, except for a protocol-required durable blocker.
2. Immediately before the first durable mutation, transition `TODO ->
   IN_PROGRESS`.
3. A durable prerequisite blocker after start transitions `IN_PROGRESS ->
   BLOCKED` with its canonical dependency/OQ/gate/`EXT:`/`HUMAN:` reference,
   then derives STATE.
4. A transient failure after start retains `IN_PROGRESS`; it never fabricates
   `BLOCKED`.
5. Review findings or correction-required work normally retain `IN_PROGRESS`;
   mark `DONE` only when the selected row's full completion condition is met.
6. Derive project `status` from current queue actionability; never copy a
   review result, queue status, feature stage, or gate result into it.

Persist `migration/features/<feature-id>/review.md` and review evidence first,
write `migration/QUEUE.md` at generation `N+1`, derive the summary, and write
`migration/STATE.md` last at `N+1`. No review PASS is a feature completion or
gate result by itself; any phase-gate evaluation follows
`docs/02-migration-pipeline.md`.

## Failure behavior

Malformed arguments print the accepted syntax and identify the invalid or
missing argument, with no writes to queue, state, feature artifacts, or open
questions. They are not migration blockers.

Use the STOP and durable-state contracts for all other failures:

- pre-start transient failure: no mutation;
- post-start transient failure: retain `IN_PROGRESS` and keep only valid
  review artifacts;
- missing judge input: record the applicable durable prerequisite blocker and
  do not fabricate PASS;
- an actual blocking unknown uses OQ deduplication; review defects route to
  correction while the selected row remains incomplete;
- one feature-local finding must not automatically set project `status:
  BLOCKED` when other actionable queue work remains.

Update `docs/05-open-questions.md` only for a newly discovered unresolved fact
that affects behavior, integrity, platform/DLL constraints, security,
deployment, or a design/verification decision. Reuse equivalent OQs. Do not
create one for malformed input, transient failure, missing artifact alone,
missing approval alone, or an already-recorded blocker.
