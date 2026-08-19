---
description: Run an independent adversarial review of an implemented migration feature.
agent: migration-coordinator
---

Review feature: $ARGUMENTS

Delegate to `adversarial-reviewer`. Compare behavior contract, evidence, target design, implementation, and Rulebook. Focus on omitted/invented behavior, data integrity, platform coupling, error semantics, and unsupported assumptions. Persist findings; do not auto-approve.

## State updates

Mutate only the selected queue row, per `docs/11-durable-state-protocol.md` ("Command field-level mutation contract"):

1. Invocation error or failed precondition before durable work begins: no queue/project transaction, unless the precondition check itself establishes a durable blocker on the selected row (STOP classification per `docs/11-stop-condition-contract.md`).
2. Preconditions satisfied and first durable work is about to begin: selected row `TODO -> IN_PROGRESS` immediately before the first durable mutation.
3. Durable blocker discovered after start: `IN_PROGRESS -> BLOCKED`; persist/map the blocker reference (dependency / `OQ-###` / gate criterion / `EXT:` / `HUMAN:`), then derive STATE.
4. Transient failure after durable work began: retain `IN_PROGRESS`; never fabricate `BLOCKED`.
5. Mark `DONE` only when this run satisfies the row's full completion artifact and applicable completion/gate condition; otherwise retain `IN_PROGRESS`.
6. Every queue/gate mutation recomputes STATE as one generation transaction (read STATE+QUEUE at equal generation N; persist specific artifacts first; QUEUE at N+1; STATE last at N+1). Project `status` is derived from current-gate queue actionability, never copied from the row status or `gate_result`.

This command: review findings are not queue completion; correction-required work normally remains `IN_PROGRESS` unless a durable prerequisite makes the selected row `BLOCKED`.
