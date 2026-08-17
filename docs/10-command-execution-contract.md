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

Commands are phase entrypoints. Specialist agents perform delegated work, but the command contract owns invocation validation, prerequisite validation, expected durable outputs, and selected-row mutation scope. Exact queue/project state values, transitions, and transaction behavior are owned by `docs/11-durable-state-protocol.md`.

## Adversarial findings

The issue is valid, but adding the same four headings mechanically to all seven commands would still leave important ambiguity.

1. `migration-status` is global and read-only. It should not require a feature ID or invent a status artifact merely for uniformity.
2. `migration-discover` can run before stable feature IDs exist, so a feature-only grammar would deadlock broad inventory discovery.
3. A feature ID cannot identify the queue row to update. Current queue items such as Q-004/Q-010 are broader than one feature.
4. A successful feature command must not mark a broad queue row `DONE` unless that row's own completion artifact is fully satisfied.
5. `migration/STATE.md` is project-level summary state. One blocked feature must not automatically block the whole project when other queue items remain actionable.
6. Issue #4 is implemented by merged PR #25, so command input/output paths must align with the merged agent contracts rather than pre-#4 prose.
7. Issue #15 has since aligned the canonical verification artifact/template on `verification.md`; commands must use that merged path rather than preserve the historical mismatch.
8. Phase-gate criteria remain a separate concern under issue #3. Commands should reference one authoritative gate checklist instead of copying subjective variants into each command.
9. Issue #13 now owns STOP classification, specialist STOP payloads, OQ deduplication, and coordinator routing; command failure behavior must reuse that model rather than invent a second STOP taxonomy.
10. Issue #14 later separates project operability, gate result, and queue lifecycle. Command implementation must not retain this document's earlier provisional state vocabulary as a competing contract.

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

It must also validate the STATE/QUEUE schema and matching transaction generation defined by `docs/11-durable-state-protocol.md` before starting a durable mutation.

`migration-status` reads the same global state plus existing feature artifacts. Once issue #1 is implemented, it also runs the same structural feature-artifact validator and surfaces failures as process blockers. It reports state-schema/generation inconsistency but does not repair it implicitly.

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

The canonical queue statuses and legal transitions are defined by `docs/11-durable-state-protocol.md`:

- `TODO`: actionable and ready to start;
- `IN_PROGRESS`: durable execution has begun but completion is not yet justified;
- `BLOCKED`: an explicit durable dependency/blocker prevents progress;
- `DONE`: the row's stated completion artifact and applicable completion/gate condition are satisfied.

Argument errors do not change queue status. A transient tool/runtime failure does not fabricate `BLOCKED`; if durable work already started, the selected row remains `IN_PROGRESS`.

### Project and gate state

`migration/STATE.md` is the derived project summary. It stores project operational `status` separately from the current phase `gate_result`.

- gate evaluation/phase advancement follows `docs/02-migration-pipeline.md`;
- STOP cause classification and coordinator routing follow `docs/11-stop-condition-contract.md`;
- project status, queue-derived lists, shared generation, write ordering, and recovery follow `docs/11-durable-state-protocol.md`;
- a failed gate does not automatically make the project operationally blocked while gate-enabling work is actionable.

Feature-local work updates project state only through the durable-state derivation rules; commands must not copy feature/queue/gate status strings directly into project `status`.

## Open-question rule

Update `docs/05-open-questions.md` only for newly discovered unresolved facts that affect behavior, data integrity, DLL/platform constraints, security, deployment, or another design/verification decision.

Do not create an open question for malformed arguments, transient tool failures, missing artifacts by themselves, approval absence by itself, or already-recorded blockers. STOP/OQ classification follows `docs/11-stop-condition-contract.md`.

## Per-command contract

| Command | Required feature inputs | Durable outputs | Successful lifecycle result |
| --- | --- | --- | --- |
| `migration-discover` | existing feature card when feature-scoped; otherwise queue/scope | `feature-card.md`, `legacy-map.md`; conditional DB/DLL evidence reports | `discovered`; `blocked` reflects material unresolved discovery facts |
| `migration-spec` | `feature-card.md`, `legacy-map.md`, applicable DB/DLL evidence | `behavior-contract.md`; relevant open-question updates | `specified` only when design may validly begin |
| `migration-design` | feature card, legacy map, behavior contract, applicable evidence, gate decision | `target-feature-design.md` | `designed` only after the applicable design gate passes |
| `migration-implement` | approved behavior contract/design plus explicit user implementation gate | only code/config/test paths explicitly named by the approved target design; blocker/deviation updates in existing durable state | `implementing`; never self-approves review/verification |
| `migration-review` | contract, evidence, target design, exact implementation diff/changed paths | `review.md` | `reviewing`; PASS permits verification but not completion |
| `migration-verify` | contract, target design, review, implementation, available judges/evidence | `verification.md` | enter `verifying`; only complete PASS may advance to `done` |
| `migration-status` | global state/queue/Rulebook/open questions/features | no durable output | no mutation |

All feature-local paths are under `migration/features/<feature-id>/`.

The table describes feature-lifecycle outcomes, not queue status transitions. Every mutating command's queue/project mutation must separately follow `docs/11-durable-state-protocol.md`.

## Canonical path authority

Command files must not choose filenames independently.

Path authority is:

1. merged `migration/features/README.md` and `docs/08-feature-artifact-validation.md`;
2. merged issue #4 agent contracts for role ownership and conditional reports;
3. matching templates where names agree.

The canonical verification artifact is `migration/features/<feature-id>/verification.md`, and the template is now `docs/templates/verification.md`. Issue #15 resolved the former `verification-report.md` mismatch; commands must not reintroduce the obsolete filename.

## Preconditions and stop behavior

Gate checklist details belong to issue #3. Commands reference those authoritative checks rather than restating subjective phrases. When execution cannot safely continue, STOP classification/payload/routing follows `docs/11-stop-condition-contract.md`, while exact queue/STATE mutations follow `docs/11-durable-state-protocol.md`.

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
| transient tool/runtime failure before durable start | none |
| transient tool/runtime failure after durable start | retain selected row `IN_PROGRESS`; persist only artifacts already validly produced |
| missing durable prerequisite | before start: no transition or selected row `BLOCKED` only when the blocker is a durable row condition; after start: `IN_PROGRESS -> BLOCKED` when the protocol's blocker rule is satisfied |
| newly discovered unknown fact | apply STOP/OQ deduplication rules; block only affected scope when material |
| approval gate / contradiction / missing evidence | apply the STOP contract without fabricating an OQ; persist exact queue/state outcome through the durable-state protocol |
| implementation/review/verification defect | persist applicable report/evidence and route through failure loop; keep queue incomplete unless a durable prerequisite blocker exists |
| successful execution | persist canonical output; mark selected row `DONE` only when its full completion condition is satisfied |

Exact transitions, generation increments, write ordering, and project derivation are in `docs/11-durable-state-protocol.md`.

## Dependency ordering

Issue #5 implementation must be consistent with:

- issue #1: feature lifecycle metadata and structural artifact validation;
- issue #2: closed enum/ID/reference validation infrastructure;
- issue #3: deterministic phase-gate checklists;
- issue #4: merged specialist agent input/output and write-ownership contracts;
- issue #13: STOP classification, specialist payload, OQ deduplication, and coordinator routing;
- issue #14: canonical queue/project durable-state schema, transitions, generation, and recovery;
- merged issue #15 artifact filename alignment (`verification.md`).

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

`State updates` must name the selected queue transition, feature metadata mutation if any, gate re-evaluation if any, and project-state derivation using the fields/transaction protocol in `docs/11-durable-state-protocol.md` rather than generic prose such as "update queue/state".

The implementation should also add a structural check that all seven command files contain the required contract sections and that referenced canonical artifact paths agree with the feature-artifact design. State-schema validation belongs to the shared repository validator described by issues #2/#14.

## Non-goals

This design does not:

- modify command implementation files;
- redefine the merged issue #4 agent procedures;
- define issue #3 gate checklist contents;
- redefine issue #13 STOP cause/routing semantics;
- redefine issue #14 queue/project state semantics;
- implement issue #1 lifecycle metadata;
- define feature-specific business behavior.

## Acceptance criteria

Issue #5 design is complete when:

1. argument grammar is deterministic for discovery, feature lifecycle, and status commands;
2. malformed arguments cause zero durable writes;
3. every mutating command selects an explicit queue row;
4. per-command required inputs and durable outputs are exact;
5. feature, queue, gate, STOP-routing, and project state ownership are separated;
6. broad queue rows cannot be falsely completed by one feature run;
7. precondition failures have explicit stop behavior;
8. status is explicitly read-only;
9. canonical artifact paths are sourced from the merged feature contract rather than local command choices;
10. later command implementation must align with the final feature, gate, STOP, artifact, and durable-state contracts before completion.
