# Durable State Protocol Design

Issue: #14 — `migration/STATE.md` and `migration/QUEUE.md` do not yet define a deterministic, machine-parseable durable-state contract or field-level update semantics.

This is a design-only artifact. `migration/STATE.md`, `migration/QUEUE.md`, `.opencode/commands/*.md`, the coordinator, validators, and CI are intentionally not changed in this pass because `AGENTS.md` rule 13 requires design approval before implementation.

## Goal

Make migration progress safely resumable from disk without requiring an agent to infer:

- which artifact owns each state dimension;
- which values and transitions are legal;
- whether the project can do work even when its next phase gate cannot pass;
- whether a blocker is feature-local, queue-local, gate-local, or project-wide;
- how a STOP classification maps to durable queue/project state without inventing a second STOP taxonomy;
- which artifact wins when durable state disagrees;
- how to detect stale, concurrent, or partially written multi-file updates.

The protocol must be deterministic for low-reasoning agents and mechanically checkable by repository validation.

## Adversarial findings

Issue #14 identifies a real defect, but enum legends alone would not fix it.

1. `STATE.md` currently embeds an enum and reason in one prose value (`BLOCKED — G0: G0.1, G0.2, G0.3`). A parser cannot treat `Status` as a closed domain without parsing prose.
2. The phase-gate design also uses gate `BLOCKED` language for a failed next-phase gate. That must not be conflated with **operational project status**: useful G0-enabling work can exist while G0 itself is `BLOCKED`.
3. `QUEUE.md` contains two tables with different schemas. Markdown tables are parseable individually, but there is no single queue schema.
4. `TODO` currently means both "ready to start" and "not started because legacy access is unavailable". Actionability cannot be inferred from that value.
5. A durable `IN_PROGRESS` state is required for crash-safe resume. Without it, a started but incomplete row is indistinguishable from untouched work.
6. `DONE` cannot mean "a command returned successfully". It means the row's declared completion artifact exists and its applicable gate/completion condition is satisfied.
7. Saying "update feature, queue, and state" does not make a multi-file update atomic. Source precedence, write order, stale-write detection, and partial-write recovery must be explicit.
8. Date-only `Last updated` cannot detect concurrent writers. Two sessions on the same day can both appear current.
9. Issue #2 explicitly deferred queue `Q-###` dependency validation until the queue has a machine-readable schema. Issue #14 is the design that supplies that schema and ownership boundary.
10. `docs/10-command-execution-contract.md` intentionally kept the then-current queue vocabulary. Its invocation/input/output contract remains valid, but its provisional state vocabulary must defer to this later state protocol.
11. `docs/11-stop-condition-contract.md` now defines why a specialist/coordinator stops and how STOP/OQ routing works. Its prose references to queue/project state must map into this schema rather than become a competing state model.

## State dimensions and authority

Durable state has separate scopes. No artifact may silently absorb another scope.

1. **Feature lifecycle authority** — `migration/features/<feature-id>/feature-card.md` owns feature `stage` and feature-local `blocked` once issue #1 is implemented.
2. **Work-item authority** — `migration/QUEUE.md` owns the lifecycle of each resumable queue row.
3. **Phase-gate authority** — `docs/02-migration-pipeline.md` owns gate criteria; `migration/STATE.md` stores only the current gate ID, its evaluated result, and failed criterion IDs.
4. **STOP classification/routing authority** — `docs/11-stop-condition-contract.md` owns canonical STOP conditions, specialist STOP payloads, OQ deduplication/allocation, and coordinator routing decisions.
5. **Project-operability authority** — `migration/STATE.md` stores a derived project `status` that answers whether useful current-phase work can proceed, not whether the next phase gate already passes.
6. **Unresolved-fact authority** — `docs/05-open-questions.md` owns unresolved factual questions. Queue/state may reference OQ IDs but must not duplicate the question registry.

When artifacts disagree, repair from the more specific authority outward: feature/open-question/gate/STOP evidence -> queue row -> project summary. `STATE.md` never overwrites a more specific fact merely because it is newer prose.

## `migration/STATE.md` schema

Use YAML frontmatter for the machine-readable contract and unrestricted Markdown below it for human context.

Canonical frontmatter:

```yaml
---
schema_version: 1
generation: 1
phase: "0"
phase_name: "Environment and feasibility"
status: ACTIVE
current_gate: G0
gate_result: BLOCKED
failed_gate_criteria: [G0.1, G0.2, G0.3]
active_queue_items: []
next_queue_items: []
blocked_queue_items: [Q-001, Q-002, Q-003]
last_updated: "2026-08-18T00:00:00Z"
---
```

Field contract:

| Field | Contract |
|---|---|
| `schema_version` | positive integer; must equal a supported schema version |
| `generation` | positive integer shared with `QUEUE.md`; incremented by every queue/project-state transaction |
| `phase` | stable phase identifier; advancement is owned by the phase-gate design |
| `phase_name` | human-readable label corresponding to `phase`; not used for routing |
| `status` | `ACTIVE | BLOCKED | PAUSED | COMPLETE` |
| `current_gate` | canonical gate ID from `docs/02-migration-pipeline.md` or `NONE` after final completion |
| `gate_result` | `PENDING | PASS | BLOCKED` for `current_gate`, or `NONE` when no gate applies |
| `failed_gate_criteria` | zero or more canonical criterion IDs belonging to `current_gate`; non-empty exactly when `gate_result: BLOCKED` |
| `active_queue_items` | current-phase/current-gate queue IDs whose status is `IN_PROGRESS` |
| `next_queue_items` | current-phase/current-gate queue IDs whose status is actionable `TODO` |
| `blocked_queue_items` | current-phase/current-gate queue IDs whose status is `BLOCKED` |
| `last_updated` | UTC RFC 3339 timestamp |

The Markdown body may explain completed work, evidence, and next actions. Commands and validators must not infer machine state from body prose.

### Project `status` versus `gate_result`

These values answer different questions and must not mirror each other automatically.

- `gate_result: BLOCKED` means the next phase transition is not currently allowed.
- `status: ACTIVE` means useful work in the current phase/gate is still actionable or already in progress.
- Therefore `status: ACTIVE` with `gate_result: BLOCKED` is valid and expected while gate-enabling work can proceed.

Unless a user explicitly pauses work:

- `COMPLETE`: migration work is complete and no further gate applies;
- `ACTIVE`: at least one relevant queue row is `IN_PROGRESS` or actionable `TODO`;
- `BLOCKED`: no relevant row is actionable/in progress and at least one required relevant row is `BLOCKED`;
- `PAUSED`: explicit human pause only.

A failed phase gate alone does not force project `status: BLOCKED`.

## `migration/QUEUE.md` schema

Keep Markdown for human readability, but define one frontmatter block and exactly one canonical live queue table.

Frontmatter:

```yaml
---
schema_version: 1
generation: 1
status_values: [TODO, IN_PROGRESS, BLOCKED, DONE]
---
```

Canonical live table columns, in this exact order:

```text
ID | Status | Phase | Depends on | Blocker | Work item | Completion artifact
```

### Queue identifiers

- `Q-###` and `S-###` are valid queue-row ID namespaces for the existing repository; each complete ID must be unique in the live queue.
- `Depends on` contains `-` or comma-separated queue IDs only.
- Dependency references must resolve to live queue rows and the dependency graph must be acyclic.
- `Blocker` contains `-` or semicolon-separated durable blocker references using one of these namespaces:
  - `OQ-###` — unresolved fact in `docs/05-open-questions.md`;
  - canonical gate criterion ID such as `G0.1` when that criterion itself blocks the row;
  - `EXT:<lowercase-kebab-token>` for an external prerequisite such as repository/source access;
  - `HUMAN:<lowercase-kebab-token>` for a required durable human approval/gate.
- A STOP payload's `Reason`/`Stop condition` is not copied into the queue as free-form status text. The coordinator maps the persisted cause to the appropriate OQ, gate criterion, dependency, external, or human blocker reference.
- Free-form blocker prose is not a machine field. Explanatory prose belongs in the related artifact, open question, gate/STOP evidence, or Markdown notes outside the live table.

### Status semantics and invariants

| Status | Meaning |
|---|---|
| `TODO` | ready to start now; every queue dependency is `DONE` and `Blocker` is `-` |
| `IN_PROGRESS` | durable execution has begun; dependencies remain satisfied and `Blocker` is `-` |
| `BLOCKED` | an unfinished dependency or durable blocker prevents progress |
| `DONE` | the declared completion artifact exists and the row's applicable completion/gate condition is satisfied |

`TODO` is intentionally **actionable**, not a synonym for "not done yet".

Allowed normal transitions:

```text
TODO -> IN_PROGRESS
TODO -> BLOCKED
IN_PROGRESS -> BLOCKED
IN_PROGRESS -> DONE
BLOCKED -> TODO
```

Rules:

- `BLOCKED -> TODO` occurs only after all blockers and unfinished dependencies are cleared and the affected gate/prerequisite is re-evaluated when required.
- A command moves `TODO -> IN_PROGRESS` immediately before its first durable work mutation, not merely when selected for consideration.
- A transient tool/runtime failure does not create a durable blocker; if durable work already started, retain `IN_PROGRESS`.
- `DONE` is terminal in normal execution. If later evidence invalidates completion, the coordinator may reopen only `DONE -> TODO`, with the reason persisted in an affected evidence/review/open-question artifact and visible in commit/PR history. Silent reopening is forbidden.

## Gate interaction

`docs/02-migration-pipeline.md` remains the only definition of gate criteria. `docs/11-stop-condition-contract.md` determines whether a discovered condition actually stops the current gate and how the coordinator classifies/routes it.

Gate evaluation updates these STATE fields only:

- `current_gate`;
- `gate_result`;
- `failed_gate_criteria`;
- `phase`/`phase_name` only after a valid gate pass permits phase advancement.

Gate evaluation must not directly set project `status`. After queue/gate/STOP facts are persisted, derive `status` from relevant queue actionability unless an explicit pause or final completion applies.

Feature-level gate failure may still set that feature's `blocked: true` according to the feature lifecycle and STOP contracts. Queue rows affected by the failed gate/STOP become `BLOCKED` only when the failed criterion or durable blocker actually prevents those rows; unrelated actionable current-phase work stays actionable.

## STOP-to-state mapping

The STOP contract owns cause semantics; this protocol owns field-level persistence.

| STOP outcome | Durable state mapping |
|---|---|
| canonical blocking unknown with OQ | persist/reuse OQ; affected queue row `BLOCKED` with `Blocker: OQ-###`; feature `blocked: true` only for affected feature scope; derive STATE |
| missing queue prerequisite/artifact | reference the unfinished queue dependency in `Depends on` or an applicable gate criterion in `Blocker`; affected row `BLOCKED`; no OQ unless an unanswered fact exists |
| approval gate | affected row `BLOCKED` with `HUMAN:<token>` or canonical gate criterion; no OQ merely for missing approval |
| external prerequisite | affected row `BLOCKED` with `EXT:<token>`; no OQ unless a separate unknown fact exists |
| contradiction containing an unanswered fact | STOP contract decides OQ reuse/allocation; affected row `BLOCKED` using that OQ or applicable dependency/criterion |
| out-of-role return | no queue status change by itself; coordinator reroutes unless the returned payload also identifies a durable blocker |
| non-blocking unknown | persist/reuse OQ and future dependency reference as required, but do not set current feature/queue/project blocked solely because the unknown exists |

The coordinator, not the specialist, performs these shared-state writes.

## Transaction generation and stale-write protection

`STATE.md` and `QUEUE.md` share the same integer `generation`.

Every durable transaction that changes queue state, project status, gate result, or phase must:

1. read both files and require equal starting generation `N`;
2. retain the observed blob/revision identity or re-read before write so a concurrent writer is not silently overwritten;
3. persist feature/evidence/open-question/gate/STOP evidence artifacts first;
4. write `QUEUE.md` with generation `N+1`;
5. derive the project summary from the newly written specific facts;
6. write `STATE.md` last with the same generation `N+1`;
7. prefer one Git commit for the complete transaction when the execution environment supports it.

A project-only pause/resume or gate re-evaluation still increments both files to the same new generation; the queue table may otherwise be unchanged.

The generation is not a global distributed lock. It is an optimistic stale/partial-write detector backed by Git revision checks.

### Partial-write recovery

Before starting new work, readers compare generations.

- `STATE.generation == QUEUE.generation`: normal read.
- `QUEUE.generation > STATE.generation`: expected signature of an interrupted ordered write. Treat `STATE.md` as stale, recompute it from queue/feature/open-question/gate/STOP authorities, finish the transaction, then continue.
- `STATE.generation > QUEUE.generation`: protocol violation because STATE must be written last from an already-updated queue. Stop and reconcile from Git history plus specific durable artifacts; do not guess the intended queue mutation.

A reader must also stop on malformed schema, unsupported schema version, or concurrent revision change detected after its initial read.

## Command field-level mutation contract

This protocol supplies the exact state semantics required by `docs/10-command-execution-contract.md`. STOP cause classification and routing remain owned by `docs/11-stop-condition-contract.md`.

Common mutating-command rules:

1. Invocation error or failed precondition before durable work begins: no queue/project transaction unless the precondition check itself establishes a durable blocker on the selected row; blocker classification must follow the STOP contract.
2. Preconditions satisfied and first durable work is about to begin: selected row `TODO -> IN_PROGRESS`.
3. Durable blocker discovered after start: `IN_PROGRESS -> BLOCKED`, persist/map the blocker reference, then derive STATE.
4. Transient failure after durable work began: retain `IN_PROGRESS`; do not fabricate `BLOCKED`.
5. Successful command execution marks `DONE` only if that run satisfies the selected row's full completion artifact and applicable completion/gate condition. Otherwise retain `IN_PROGRESS`.
6. Every queue/gate mutation recomputes STATE; never copy the selected row status or gate result into project `status`.

Command-specific outcome rules:

| Command | Required durable-state behavior |
|---|---|
| `migration-discover` | start the selected discovery row as `IN_PROGRESS`; durable legacy-access/fact blockers affect only rows/scopes they actually prevent; complete only when the row's declared artifact is fully satisfied |
| `migration-spec` | stay `IN_PROGRESS` while the contract is incomplete; a durable semantic/gate dependency may make the selected row `BLOCKED`; complete only when its completion condition is satisfied |
| `migration-design` | do not start if prerequisites fail; after start, unresolved design-blocking facts/gates may set the row `BLOCKED`; complete only when the selected design row's completion condition is satisfied |
| `migration-implement` | durable implementation authorization is a precondition; without it, do not transition/start target edits; after start, unresolved deviations remain incomplete |
| `migration-review` | review findings are not queue completion; correction-required work normally remains `IN_PROGRESS` unless a durable prerequisite makes it `BLOCKED` |
| `migration-verify` | PASS may complete only the selected row whose full completion condition is satisfied; FAIL/PARTIAL remain `IN_PROGRESS`; a real verification prerequisite blocker becomes `BLOCKED` |
| `migration-status` | read-only; validate schema + equal generation and report inconsistencies without implicit repair |

A broad queue row such as combined review + verification remains `IN_PROGRESS` after review if verification is still outstanding.

## Static validation ownership

Issue #2 (`docs/issue-2-artifact-schema-validation.md`) owns the general closed-enum/ID/reference validation layer. Issue #14 owns the queue/project-state schema and semantic invariants that Issue #2 explicitly deferred until a machine-readable queue contract existed.

Implementation should share parser/diagnostic infrastructure where useful, but keep ownership clear:

- A-2 can parse/validate closed values and identifier/reference syntax from this schema;
- this protocol owns queue transition, dependency/blocker, generation, gate/state consistency, and derived-summary invariants;
- phase-gate semantic truth remains in `docs/02-migration-pipeline.md`;
- STOP classification truth remains in `docs/11-stop-condition-contract.md`.

At minimum static validation must reject:

- missing/malformed frontmatter;
- unsupported `schema_version`;
- unequal/non-positive generations;
- invalid STATE/QUEUE enums;
- invalid gate/result/criterion relationships;
- more than one live queue table or wrong queue header/order;
- duplicate/invalid queue IDs;
- missing or cyclic dependencies;
- invalid blocker namespace/reference;
- status/dependency/blocker invariant violations;
- STATE queue-ID lists inconsistent with live queue status/actionability;
- project `status` inconsistent with queue actionability except explicit `PAUSED`/`COMPLETE`;
- `DONE` rows whose declared artifact is statically resolvable but missing.

Diagnostics should follow Issue #2's aggregated path/line/category/value/expected-contract format.

## Migration of existing durable files

The implementation pass must normalize current state without inventing progress.

1. Convert current STATE machine fields to frontmatter; keep useful evidence/explanation in the body.
2. Replace combined gate/project prose such as `Status: BLOCKED — G0: ...` with separate `status`, `current_gate`, `gate_result`, and `failed_gate_criteria` fields. The current G0 failure may coexist with `status: ACTIVE` if gate-enabling work is actionable.
3. Merge the current two queue tables into one canonical seven-column live table without dropping Q or S rows.
4. Existing `DONE` rows remain `DONE` only if their completion artifacts still exist and their completion condition remains valid.
5. Existing `BLOCKED` rows remain blocked with dependency/blocker prose normalized into explicit fields.
6. Existing `TODO` rows stay `TODO` only when actually actionable. Rows that cannot start because of legacy access, unresolved facts, unfinished dependencies, or a human gate become `BLOCKED` with explicit references.
7. No row becomes `IN_PROGRESS` merely because the schema is introduced.
8. Do not silently rewrite feature lifecycle state, open-question status, STOP classification, or gate criteria while normalizing queue/project schemas.

## Integration with existing designs

- `docs/08-feature-artifact-validation.md` remains authoritative for feature lifecycle metadata and canonical feature artifact names.
- `docs/issue-2-artifact-schema-validation.md` remains authoritative for the general A-2 validation layer; this document supplies the queue/state schema that A-2 previously deferred.
- `docs/02-migration-pipeline.md` remains authoritative for gate definitions; it records gate result/criteria separately from operational project status.
- `docs/10-command-execution-contract.md` remains authoritative for command invocation/input/output/selected-row scope; this document supplies exact state transitions.
- `docs/11-stop-condition-contract.md` remains authoritative for STOP classification, specialist payloads, OQ reuse/allocation, and routing; this document supersedes only its free-form queue/STATE persistence wording with exact fields and transaction rules.
- Merged issue #15 aligns feature verification on `migration/features/<feature-id>/verification.md` with `docs/templates/verification.md`; this protocol uses that canonical path when evaluating statically resolvable completion artifacts.

If canonical designs still disagree after these integration changes, implementation stops rather than choosing whichever rule is convenient.

## Implementation requirements after design approval

Implement the state contract as one coherent pass:

1. migrate `migration/STATE.md` to the frontmatter schema;
2. migrate `migration/QUEUE.md` to frontmatter + one canonical queue table + normalized dependencies/blockers;
3. update gate persistence to store `gate_result`/`failed_gate_criteria` separately from project `status`;
4. update `.opencode/agents/migration-coordinator.md` with authority precedence, STOP-to-state mapping, generation checks, ordered writes, stale detection, and recovery;
5. update all six mutating command files with exact field-level `State updates` sections;
6. update `migration-status.md` with read-only schema/generation consistency checks;
7. extend the static validation entrypoint so malformed/inconsistent durable state fails CI with aggregated diagnostics;
8. when issue #13 STOP handling is implemented, make its coordinator persistence actions call/use the same queue/state transaction logic instead of a second free-form path.

Do not ship only enum legends while leaving commands, STOP mapping, gate semantics, write ordering, or recovery ambiguous.

## Non-goals

This design does not:

- change migrated business behavior;
- redefine feature lifecycle stages/artifact names;
- redefine phase-gate criterion contents;
- redefine STOP condition IDs, applicability, OQ deduplication, or routing;
- add target application code;
- provide a distributed lock outside Git/optimistic revision checks;
- add cancellation/abandonment semantics; those require an explicit later design if needed.

## Acceptance criteria

Issue #14 design is complete when:

1. project status, gate result, and queue status are separate closed domains;
2. `STATE.md` has a machine-readable authoritative section independent of prose;
3. `QUEUE.md` has one canonical live schema;
4. queue status meanings and allowed transitions are deterministic;
5. dependency/blocker representation is explicit and referentially checkable;
6. feature, queue, gate, STOP, open-question, and project authorities cannot silently overwrite one another;
7. concurrent/stale and partial writes are detectable through generation + revision checks;
8. write ordering and recovery are deterministic;
9. every command and STOP persistence path has an unambiguous future field-level state mutation rule;
10. static validation can reject malformed and cross-artifact inconsistent durable state.
