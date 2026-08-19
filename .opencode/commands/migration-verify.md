---
description: Verify one migrated feature against available legacy evidence and observable behavior.
agent: migration-coordinator
---

Verify feature: $ARGUMENTS

Delegate to `verifier` using `parity-verification`. Use the strongest available composite judge and produce PASS/FAIL/PARTIAL/BLOCKED with explicit unverified behavior.

## State updates

Mutate only the selected queue row, per `docs/11-durable-state-protocol.md` ("Command field-level mutation contract"):

1. Invocation error or failed precondition before durable work begins: no queue/project transaction, unless the precondition check itself establishes a durable blocker on the selected row (STOP classification per `docs/11-stop-condition-contract.md`).
2. Preconditions satisfied and first durable work is about to begin: selected row `TODO -> IN_PROGRESS` immediately before the first durable mutation.
3. Durable blocker discovered after start: `IN_PROGRESS -> BLOCKED`; persist/map the blocker reference (dependency / `OQ-###` / gate criterion / `EXT:` / `HUMAN:`), then derive STATE.
4. Transient failure after durable work began: retain `IN_PROGRESS`; never fabricate `BLOCKED`.
5. Mark `DONE` only when this run satisfies the row's full completion artifact and applicable completion/gate condition; otherwise retain `IN_PROGRESS`.
6. Every queue/gate mutation recomputes STATE as one generation transaction (read STATE+QUEUE at equal generation N; persist specific artifacts first; QUEUE at N+1; STATE last at N+1). Project `status` is derived from current-gate queue actionability, never copied from the row status or `gate_result`.

This command: PASS may complete only the selected row whose full completion condition is satisfied; FAIL/PARTIAL remain `IN_PROGRESS`; a real verification prerequisite blocker becomes `BLOCKED`.
