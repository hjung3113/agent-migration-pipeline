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

## PostgreSQL schema migration / test DB plan

- PostgreSQL schema change: yes | no
- Schema delta / integrity semantics:
- Alembic revision path / identity:
- Clean test DB bootstrap required: yes | no
- Bootstrap implementation path in this feature: N/A | `scripts/db/pg_test_bootstrap.py`
- Connection profile: N/A | `postgres-test-rw`
- Seed / fixture identity: none | <name/path>
- Expected Alembic head:
- Clean-state DB assertions / parity evidence:

If `PostgreSQL schema change` is `yes`, every field above must be concrete according to `docs/13-postgresql-test-db-and-schema-migration.md`. If the bootstrap is required but does not yet exist, this design must explicitly include its implementation path or remain blocked. The connection path is the canonical `postgres-test-rw` profile plus shared DB guard; never authorize manual DDL, raw connection strings, or a general `DATABASE_URL` as reset substitutes.

If `PostgreSQL schema change` is `no`, use `N/A` for migration-only fields rather than inventing a migration.

## Platform/DLL compatibility impact

## Error model

## Observability

## Test/verification plan

## Legacy structures intentionally not carried forward

Use `docs/13-legacy-structure-rejection-contract.md`. Every canonical LSR ID must be dispositioned; add more rows when the feature contains multiple material candidates in one category.

| LSR ID | Legacy structure / carryover candidate | Disposition | Target replacement / isolation | Requirement / evidence reference | Rationale |
|---|---|---|---|---|---|
| LSR-01 | | REJECTED / RETAINED-JUSTIFIED / NOT-APPLICABLE / BLOCKED | | | |
| LSR-02 | | REJECTED / RETAINED-JUSTIFIED / NOT-APPLICABLE / BLOCKED | | | |
| LSR-03 | | REJECTED / RETAINED-JUSTIFIED / NOT-APPLICABLE / BLOCKED | | | |
| LSR-04 | | REJECTED / RETAINED-JUSTIFIED / NOT-APPLICABLE / BLOCKED | | | |
| LSR-05 | | REJECTED / RETAINED-JUSTIFIED / NOT-APPLICABLE / BLOCKED | | | |
| LSR-06 | | REJECTED / RETAINED-JUSTIFIED / NOT-APPLICABLE / BLOCKED | | | |
| LSR-07 | | REJECTED / RETAINED-JUSTIFIED / NOT-APPLICABLE / BLOCKED | | | |

Rules:

- `RETAINED-JUSTIFIED` requires a durable behavior/data/platform/rollout evidence reference.
- `REJECTED` names the target replacement or isolation boundary.
- `NOT-APPLICABLE` must still cite evidence that the category does not occur in the inspected feature.
- `BLOCKED` must link to a real unresolved fact/open question when applicable.
- Bare `N/A`, `same as legacy`, `for compatibility`, and `for safety` are not valid rationales.

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

This is the coordinator-owned pre-implementation consistency review required by G3.4. `Legacy-structure rejection evidence` must point to the completed LSR disposition table and supporting evidence, not a generic statement. It does not replace the post-implementation independent `adversarial-reviewer` report.

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
