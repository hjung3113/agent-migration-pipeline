---
description: Discover legacy behavior and dependencies for a scope before migration design.
agent: migration-coordinator
---

Analyze legacy scope: $ARGUMENTS

Read `migration/STATE.md` and Gate G0 in `docs/02-migration-pipeline.md` first.

If the project is still in Phase 0 and G0 is not `PASS`, run only gate-enabling inspection: use `legacy-discovery`, delegate platform-boundary work to `dll-boundary-analyzer`, produce `migration/evidence/dll-boundary-report.md` and `migration/evidence/observable-output-survey.md`, then evaluate G0. If any G0 criterion fails, apply the gate failure protocol and stop; do not begin broad feature discovery.

After G0 is `PASS`, use `legacy-discovery` and delegate source analysis to `legacy-analyzer`; if the scope touches the platform boundary, also delegate to `dll-boundary-analyzer`; if it touches MSSQL, delegate to `db-analyzer`.

Persist feature/dependency artifacts, evidence grades, queue updates, and unresolved questions. Do not implement target code.

## State updates

Mutate only the selected queue row, per `docs/11-durable-state-protocol.md` ("Command field-level mutation contract"):

1. Invocation error or failed precondition before durable work begins: no queue/project transaction, unless the precondition check itself establishes a durable blocker on the selected row (STOP classification per `docs/11-stop-condition-contract.md`).
2. Preconditions satisfied and first durable work is about to begin: selected row `TODO -> IN_PROGRESS` immediately before the first durable mutation.
3. Durable blocker discovered after start: `IN_PROGRESS -> BLOCKED`; persist/map the blocker reference (dependency / `OQ-###` / gate criterion / `EXT:` / `HUMAN:`), then derive STATE.
4. Transient failure after durable work began: retain `IN_PROGRESS`; never fabricate `BLOCKED`.
5. Mark `DONE` only when this run satisfies the row's full completion artifact and applicable completion/gate condition; otherwise retain `IN_PROGRESS`.
6. Every queue/gate mutation recomputes STATE as one generation transaction (read STATE+QUEUE at equal generation N; persist specific artifacts first; QUEUE at N+1; STATE last at N+1). Project `status` is derived from current-gate queue actionability, never copied from the row status or `gate_result`.

This command: start the selected discovery row as `IN_PROGRESS`; durable legacy-access/fact blockers affect only the rows/scopes they actually prevent; complete the row only when its declared artifact is fully satisfied.
