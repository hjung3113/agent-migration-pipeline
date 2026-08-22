---
name: target-feature-design
description: Use after a behavior contract is sufficiently approved to redesign one business feature for React, FastAPI, PostgreSQL, and an isolated platform adapter boundary.
compatibility: OpenCode project skill
---

# Target Feature Design

## Inputs

- A validated `FEATURE_ID` and an approved-enough behavior scope.
- [Input] `migration/features/<feature-id>/feature-card.md`.
- [Input] `migration/features/<feature-id>/legacy-map.md`.
- [Input] `migration/features/<feature-id>/behavior-contract.md`.
- [Input] Applicable `migration/features/<feature-id>/db-dependency-report.md`, `migration/features/<feature-id>/dll-boundary-report.md`, evidence records, Rulebook constraints, and open questions.
- [Input] The applicable design-gate result and issue #8 designer write restrictions.

## Outputs

- [Output] The approved or explicitly provisional design at `migration/features/<feature-id>/target-feature-design.md`.
- [Output] A complete LSR-01..LSR-07 legacy-structure disposition, schema/migration/test-DB plan when applicable, and unresolved/provisional decisions.
- For a read-only invoking role, return the complete design body and canonical destination to `migration-coordinator`; direct writes must obey issue #8's designer path restrictions.
- This skill does not update `migration/STATE.md`, `migration/QUEUE.md`, lifecycle metadata, or the approved behavior contract in place.

## Procedure

1. [Input] Read `migration/features/<feature-id>/feature-card.md`, `legacy-map.md`, `behavior-contract.md`, applicable DB/DLL reports, evidence, Rulebook, and open questions.
2. [Input] Design from behavior intent rather than legacy file/class/object structure.
3. [Output] Cover React responsibilities and user workflow; FastAPI transport contract; application/domain responsibilities; PostgreSQL persistence semantics; platform/DLL adapter impact; errors and observability; test/verification hooks; and rollout/compatibility concerns.
4. [Output] Record a complete LSR-01..LSR-07 legacy-structure disposition and justify any `RETAINED-JUSTIFIED` legacy-shaped element with a current durable requirement/evidence reference.
5. [Output] If PostgreSQL schema changes, define the schema delta, Alembic revision path/identity, clean test-DB bootstrap requirement, canonical `postgres-test-rw` profile, explicit seed/fixture identity (or `none`), and DB verification evidence according to `docs/13-postgresql-test-db-and-schema-migration.md`.
6. [Input] Re-check public contract, data model, platform boundary, permissions, unknowns, and gate status before writing or returning `migration/features/<feature-id>/target-feature-design.md`.
7. [Output] Return the design, evidence references, provisional/BLOCKED decisions, and any implementation-path declarations to `migration-coordinator`.

Do not default to one React boundary per WPF/ViewModel unit, one backend boundary per C# class/service, one PostgreSQL object per MSSQL object, or one endpoint per legacy operation. Any `RETAINED-JUSTIFIED` legacy-shaped element needs a current durable requirement/evidence reference.

For any feature that changes PostgreSQL schema, also define the schema delta, Alembic revision path/identity, clean test-DB bootstrap requirement, canonical `postgres-test-rw` profile, explicit seed/fixture identity (or `none`), and DB verification evidence according to `docs/13-postgresql-test-db-and-schema-migration.md`. A schema-changing design without this plan is not ready for implementation.

If the first DB-backed feature requires the deferred bootstrap and `scripts/db/pg_test_bootstrap.py` does not yet exist, the approved design must explicitly include that path in implementation scope. Do not let the implementer invent a manual DDL, raw connection, or general `DATABASE_URL` workaround.

## Branches

- If any required contract, feature artifact, evidence, or design gate is missing, return `BLOCKED`; do not write a target design against an invented prerequisite.
- If an unresolved fact affects a public contract, data model, platform boundary, or other medium/high lock-in choice, mark the relevant design provisional or `BLOCKED`; do not select a convenient assumption or preserve the legacy shape "for safety".
- If required DB bootstrap/schema evidence is unavailable, return `BLOCKED` for the dependent schema design; do not substitute manual DDL, raw connections, or general `DATABASE_URL` input.
- If optional evidence is unavailable but the design remains bounded, continue only with an explicit provisional/`PARTIAL` result and recorded gap.
- If evidence or design inputs conflict, preserve both sides and return `PARTIAL` or `BLOCKED`; do not silently rewrite the behavior contract.
- If implementation-time discovery would require a material design change, reopen the design gate and return `BLOCKED`; do not rewrite `migration/features/<feature-id>/target-feature-design.md` post hoc.
- If the canonical design exists, update it in place only when the role and gate authorize it; otherwise return the complete replacement body to `migration-coordinator`.
- `BLOCKED` and `PARTIAL` are skill result labels. Designer permissions, STOP payloads, durable state, queue, and lifecycle transitions remain governed by their owning contracts.

## Done means

The canonical target design covers the approved behavior, target boundaries, adapter impact, errors, observability, verification hooks, LSR dispositions, and any required PostgreSQL migration/test-DB plan. Every medium/high lock-in unknown is resolved or explicitly provisional/BLOCKED, issue #8 write restrictions are respected, and the design is persisted by an authorized role or handed to `migration-coordinator` without advancing implementation.
