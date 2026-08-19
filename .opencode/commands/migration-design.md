---
description: Design one approved feature for React, FastAPI, PostgreSQL, and the platform compatibility boundary.
agent: migration-coordinator
---

Design feature: $ARGUMENTS

Require `migration/features/<feature>/behavior-contract.md` Gate G2 result to be `PASS` under the canonical criteria in `docs/02-migration-pipeline.md`. If G2 is not `PASS`, apply the gate failure protocol and stop.

Delegate to `migration-designer` using `target-feature-design`. Require `docs/13-legacy-structure-rejection-contract.md` and the feature's LSR-tagged legacy evidence as design inputs. Do not mechanically preserve WPF/C#/MSSQL structure or choose `RETAINED-JUSTIFIED` without durable requirement evidence. Record material unresolved carryover decisions as open questions rather than preserving the legacy shape by default.

Write or update `migration/features/<feature>/target-feature-design.md` from `docs/templates/target-feature-design.md`, including a complete LSR-01..LSR-07 disposition, then have `migration-coordinator` perform the G3.4 pre-implementation design review by checking the behavior-preservation map and legacy-structure disposition/rejection evidence. Persist every G3 criterion result and evidence reference before evaluating the gate.

If G3.5 is not satisfied, leave G3 `BLOCKED` and stop after design. Do not dispatch implementation until a later explicit user instruction is persisted as the implementation authorization and the full G3 gate passes.

## State updates

Mutate only the selected queue row, per `docs/11-durable-state-protocol.md` ("Command field-level mutation contract"):

1. Invocation error or failed precondition before durable work begins: no queue/project transaction, unless the precondition check itself establishes a durable blocker on the selected row (STOP classification per `docs/11-stop-condition-contract.md`).
2. Preconditions satisfied and first durable work is about to begin: selected row `TODO -> IN_PROGRESS` immediately before the first durable mutation.
3. Durable blocker discovered after start: `IN_PROGRESS -> BLOCKED`; persist/map the blocker reference (dependency / `OQ-###` / gate criterion / `EXT:` / `HUMAN:`), then derive STATE.
4. Transient failure after durable work began: retain `IN_PROGRESS`; never fabricate `BLOCKED`.
5. Mark `DONE` only when this run satisfies the row's full completion artifact and applicable completion/gate condition; otherwise retain `IN_PROGRESS`.
6. Every queue/gate mutation recomputes STATE as one generation transaction (read STATE+QUEUE at equal generation N; persist specific artifacts first; QUEUE at N+1; STATE last at N+1). Project `status` is derived from current-gate queue actionability, never copied from the row status or `gate_result`.

This command: do not start if prerequisites fail (no `TODO -> IN_PROGRESS` transition); after start, unresolved design-blocking facts/gates may set the selected row `BLOCKED`; complete only when the selected design row's completion condition is satisfied.
