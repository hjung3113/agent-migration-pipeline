# Target Feature Design: <feature>

- Status: draft | ready | blocked

## Behavior contract reference

- Path:
- G2 result:

## Scope

## Out of scope

## Target flow

```text
React -> FastAPI -> Application/Domain -> Repository -> PostgreSQL
             \
              -> Platform adapter if required
```

## Behavior preservation map

| Behavior rule ID | Target responsibility | Preservation note |
|---|---|---|
| BR-001 | | |

Every behavior-contract rule with `Implementation impact = yes` must appear exactly once.

## Frontend responsibilities

## API contract

## Business/application responsibilities

## Persistence design

## Platform/DLL compatibility impact

## Error model

## Observability

## Test/verification plan

## Legacy structures intentionally not carried forward

## Open questions / assumptions

| Question / OQ ID | Blocks implementation? | Status | Evidence / resolution |
|---|---|---|---|
| | yes | OPEN | |

`Blocks implementation?` must be literal `yes` or `no`.

## Design review

- Reviewer role: migration-coordinator
- Result: PENDING | PASS | FAIL
- Behavior-map evidence:
- Legacy-structure rejection evidence:
- Notes:

This is the coordinator-owned pre-implementation consistency review required by G3.4. It does not replace the post-implementation independent `adversarial-reviewer` report.

## Implementation authorization

- Status: PENDING | APPROVED
- Source reference:
- Recorded at:

`APPROVED` requires an explicit user instruction to start implementation. Persist the durable source reference before gate evaluation.

## Gate G3 — DESIGN_READY

- Result: PENDING | PASS | BLOCKED
- Evaluated at:
- Evaluated by:

| Criterion ID | Result | Evidence reference |
|---|---|---|
| G3.1 | PENDING | |
| G3.2 | PENDING | |
| G3.3 | PENDING | |
| G3.4 | PENDING | |
| G3.5 | PENDING | |

The criterion definitions and pass rule are canonical in `docs/02-migration-pipeline.md`. Do not copy or reinterpret them here.
