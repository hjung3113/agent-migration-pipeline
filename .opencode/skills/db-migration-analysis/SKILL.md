---
name: db-migration-analysis
description: Use when analyzing MSSQL dependencies for a feature to identify data semantics and database-resident business logic before redesigning persistence for PostgreSQL.
compatibility: OpenCode project skill
---

# DB Migration Analysis

## Inputs

- A validated `FEATURE_ID` and a feature scope whose persistence dependencies are being analyzed.
- [Input] `migration/features/<feature-id>/legacy-map.md`.
- [Input] Accessible MSSQL schema, tables/views/stored procedures/functions/triggers/jobs, queries, configuration, and relevant runtime evidence.
- [Input] `migration/features/<feature-id>/feature-card.md` and applicable behavior/open-question context.

## Outputs

- [Output] The feature-scoped DB dependency report at `migration/features/<feature-id>/db-dependency-report.md`.
- [Output] Unresolved data-semantics or migration-risk update requests for `migration/features/<feature-id>/feature-card.md` or `docs/05-open-questions.md` as applicable.
- For a read-only invoking role, return the complete report/update bodies and canonical destinations to `migration-coordinator`; do not write a competing schema artifact.
- This skill proposes semantics only after behavior is understood and never updates `migration/STATE.md`, `migration/QUEUE.md`, or lifecycle metadata.

## Procedure

1. [Input] Read `migration/features/<feature-id>/legacy-map.md`, feature scope, existing evidence, and relevant open questions before inspecting database dependencies.
2. [Input] Inventory tables/views/stored procedures/functions/triggers/jobs touched.
3. [Input] Capture keys, constraints, defaults, precision, nullability, identity behavior, collations, and date/time semantics.
4. [Input] Identify transaction/isolation expectations and map application assumptions around result ordering, row counts, concurrency, and errors.
5. [Input] Classify DB logic as integrity, business rule, query/reporting, or MSSQL-specific artifact, and identify data migration/compatibility risks.
6. [Output] Write or return `migration/features/<feature-id>/db-dependency-report.md` with evidence, unknowns, and behavior-dependent findings.
7. [Output] Propose PostgreSQL semantics only after the behavior is understood, and return any required feature-card/open-question updates to `migration-coordinator`.

Do not mechanically translate T-SQL.

## Branches

- If `migration/features/<feature-id>/legacy-map.md` or the required DB scope is missing, return `BLOCKED`; do not synthesize a dependency report or invent database objects.
- If a referenced DB object or behavior cannot be inspected, record it as unresolved and return `BLOCKED` for any PostgreSQL semantic choice that depends on it.
- If optional schema/runtime evidence is unavailable but the report can remain bounded, continue with a truthful `PARTIAL` result and record the gap.
- If DB evidence conflicts, preserve both sides and return `PARTIAL` or `BLOCKED`; do not select a convenient schema interpretation.
- If an unknown changes transaction, integrity, concurrency, or data-migration lock-in, stop the dependent choice and route an OQ update rather than guessing.
- If `migration/features/<feature-id>/db-dependency-report.md` already exists, update it in place only when authorized; otherwise return the complete update body to `migration-coordinator`.
- `BLOCKED` and `PARTIAL` are skill result labels; database analysis does not own STOP payloads, queue/state changes, or lifecycle transitions.

## Done means

The canonical feature report identifies inspected and uninspected MSSQL dependencies, data semantics, database-resident logic, transaction/concurrency expectations, compatibility risks, evidence, and unresolved choices. Any PostgreSQL proposal is behavior-backed or explicitly blocked/provisional, and the result is persisted by an authorized role or handed to `migration-coordinator`.
