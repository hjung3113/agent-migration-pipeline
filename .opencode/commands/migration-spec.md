---
description: Build or refine an evidence-graded behavior contract for one discovered feature.
agent: migration-coordinator
---

Specify feature: $ARGUMENTS

Use `behavior-contract`, `evidence-grading`, and `uncertainty-management`. Build the contract from discovered evidence, not desired target architecture.

Write or update `migration/features/<feature>/behavior-contract.md` from `docs/templates/behavior-contract.md`, then evaluate Gate G2 exactly as defined in `docs/02-migration-pipeline.md`. Persist G2 criterion results and evidence references in the contract.

If any G2 criterion fails, apply the gate failure protocol and stop before target design. Do not convert an unknown semantic into an inferred implementation decision.

## State updates

Mutate only the selected queue row, per `docs/11-durable-state-protocol.md` ("Command field-level mutation contract"):

1. Invocation error or failed precondition before durable work begins: no queue/project transaction, unless the precondition check itself establishes a durable blocker on the selected row (STOP classification per `docs/11-stop-condition-contract.md`).
2. Preconditions satisfied and first durable work is about to begin: selected row `TODO -> IN_PROGRESS` immediately before the first durable mutation.
3. Durable blocker discovered after start: `IN_PROGRESS -> BLOCKED`; persist/map the blocker reference (dependency / `OQ-###` / gate criterion / `EXT:` / `HUMAN:`), then derive STATE.
4. Transient failure after durable work began: retain `IN_PROGRESS`; never fabricate `BLOCKED`.
5. Mark `DONE` only when this run satisfies the row's full completion artifact and applicable completion/gate condition; otherwise retain `IN_PROGRESS`.
6. Every queue/gate mutation recomputes STATE as one generation transaction (read STATE+QUEUE at equal generation N; persist specific artifacts first; QUEUE at N+1; STATE last at N+1). Project `status` is derived from current-gate queue actionability, never copied from the row status or `gate_result`.

This command: stay `IN_PROGRESS` while the contract is incomplete; a durable semantic/gate dependency may make the selected row `BLOCKED`; complete only when the row's completion condition is satisfied.
