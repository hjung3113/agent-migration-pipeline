---
description: Verify one migrated feature against available legacy evidence and observable behavior.
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
unknown queue IDs, or invalid feature IDs are invocation errors. Display names
are never identifiers.

## Inputs

Read `AGENTS.md`, `migration/STATE.md`, `migration/QUEUE.md`,
`migration/RULEBOOK.md`, `docs/05-open-questions.md`, the selected queue row,
and the phase-required artifacts. Validate the STATE/QUEUE schema and equal
positive `generation` before durable work.

The verification inputs are
`migration/features/<feature-id>/feature-card.md`,
`migration/features/<feature-id>/legacy-map.md`,
`migration/features/<feature-id>/behavior-contract.md`,
`migration/features/<feature-id>/target-feature-design.md`,
`migration/features/<feature-id>/review.md`, the implementation, and available
judges/evidence. The durable verification artifact is
`migration/features/<feature-id>/verification.md`.

## Preconditions

The coordinator must verify that:

- an independent `migration/features/<feature-id>/review.md` exists;
- no unresolved blocking review finding remains;
- valid judges can exercise material behavior, or unexercised behavior is
  explicitly classified as residual uncertainty;
- the selected queue row is verification work, its phase/work item and
  completion artifact are compatible, and this run can satisfy that artifact.

`FAIL`, `PARTIAL`, and `BLOCKED` are valid verification results but never
advance the feature to `done` or complete an insufficient queue row.

## Outputs

Delegate to `verifier` using the `parity-verification` contract and persist
`migration/features/<feature-id>/verification.md` from
`docs/templates/verification.md`. Use the strongest available composite judge
and record PASS/FAIL/PARTIAL/BLOCKED with explicitly unverified behavior.

Enter feature `stage: verifying`; only a complete PASS with the applicable
completion condition may advance the feature to `stage: done`. Feature-local
`blocked` is independent of queue and project state.

## State updates

Only the selected `--queue` row may mutate:

1. Invocation errors and failed preconditions before durable work cause no
   queue/project transaction, except for a protocol-required durable blocker.
2. Immediately before the first durable mutation, transition `TODO ->
   IN_PROGRESS`.
3. A real durable verification prerequisite blocker after start transitions
   `IN_PROGRESS -> BLOCKED` with its dependency/OQ/gate/`EXT:`/`HUMAN:`
   reference, then derives STATE.
4. A transient failure after start retains `IN_PROGRESS`; never fabricate
   `BLOCKED`.
5. PASS may transition the selected row to `DONE` only when its full declared
   completion artifact and applicable gate condition are satisfied. FAIL,
   PARTIAL, and incomplete PASS retain `IN_PROGRESS`.
6. Derive project `status` from queue actionability and specific facts; never
   copy verification, feature, queue, or gate status strings into it.

Persist `migration/features/<feature-id>/verification.md` and evidence first,
write `migration/QUEUE.md` at generation `N+1`, derive the project summary,
and write `migration/STATE.md` last at `N+1`. Any phase/gate re-evaluation
uses `docs/02-migration-pipeline.md`; it is not inferred from the verdict.

## Failure behavior

Malformed arguments print the accepted syntax and identify the invalid or
missing argument, with zero durable writes. User input mistakes are not
blockers.

Apply the canonical STOP classification and durable-state protocol:

- pre-start transient failure: no mutation;
- post-start transient/runtime failure: retain `IN_PROGRESS` and preserve only
  validly produced evidence;
- a missing judge or prerequisite is `BLOCKED` only when it is a durable
  blocker, not because a tool happened to fail transiently;
- FAIL/PARTIAL or a verification defect persists the report and routes the
  failure loop without marking `DONE`;
- a newly discovered material unknown uses OQ deduplication and blocks only
  its affected feature/queue scope;
- project status remains a derived summary and is not blanket-blocked by one
  feature-local verification result.

Update `docs/05-open-questions.md` only for a newly discovered unresolved fact
that affects behavior, integrity, platform/DLL constraints, security,
deployment, or a design/verification decision. Reuse an equivalent OQ. Do not
create one for malformed input, transient failure, missing artifact alone,
missing approval alone, or an already-recorded blocker.
