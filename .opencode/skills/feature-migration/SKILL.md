---
name: feature-migration
description: Use only after a feature has an approved behavior contract and target design to implement the vertical slice while preserving evidence-backed behavior and recording deviations.
compatibility: OpenCode project skill
---

# Feature Migration

## Inputs

- An explicit user implementation gate under `AGENTS.md` rule 13; design approval alone is not an implementation authorization.
- [Input] `migration/features/<feature-id>/feature-card.md`.
- [Input] Approved `migration/features/<feature-id>/behavior-contract.md`.
- [Input] Approved `migration/features/<feature-id>/target-feature-design.md`.
- [Input] Evidence grades, resolved or explicitly accepted provisional open questions, and the approved code/test paths declared by the target design.
- [Input] If PostgreSQL schema changes, the complete migration/test-DB plan under `docs/13-postgresql-test-db-and-schema-migration.md`.

## Outputs

- [Output] The smallest complete vertical-slice implementation and tests, only at target paths explicitly declared by `migration/features/<feature-id>/target-feature-design.md`.
- [Output] Changed paths, check results, evidence-backed deviations, Alembic revision/head and seed identity for DB-changing work, and any blocker/deviation update request to `migration-coordinator`.
- For a read-only invoking role, return the complete implementation result and check/deviation report; direct edits require the role-boundary and explicit gate authorization.
- This skill does not rewrite the approved design, broaden scope, or update `migration/STATE.md`, `migration/QUEUE.md`, feature lifecycle metadata, review, or verification artifacts.

## Procedure

1. [Input] Verify the feature card, approved behavior contract, approved target design, evidence grades, open-question status, explicit user implementation gate, and declared code/test paths.
2. [Output] Implement the smallest complete vertical slice while keeping platform/DLL code behind adapters.
3. [Output] For PostgreSQL schema changes, use the approved Alembic revision path as the only schema history.
4. [Input] Prepare DB-changing tests through the canonical bootstrap with logical profile `postgres-test-rw` through the shared resolver/DB guard.
5. [Output] Add automated tests at stable observable boundaries, preserve data integrity/error semantics, and record DB revision/head and seed identity for DB-changing work.
6. [Input] Compare implementation behavior with the approved contract/design without silently relaxing either.
7. [Output] Record deviations from target design, changed paths, and verification/check results for the independent reviewer.
8. [Output] Hand off to an independent adversarial reviewer without self-approving review or verification.

## Branches

- If the feature card, approved behavior contract, target design, evidence, explicit `AGENTS.md` rule 13 user gate, or declared implementation path is absent, return `BLOCKED` and do not edit target code.
- If a required blocking open question is unresolved or a provisional design no longer covers the work, return `BLOCKED`; do not guess or broaden scope.
- If the approved DB bootstrap/resolver/guard is absent for required DB tests and the approved design does not declare that bootstrap/resolver/guard path in implementation scope, return `BLOCKED` rather than using manual DDL, raw connection input, or general `DATABASE_URL`; when the approved design does declare the path, implement and use only that approved path within scope.
- If implementation reveals a material design change, stop that part, reopen the design gate, and return `BLOCKED`; do not rewrite `migration/features/<feature-id>/target-feature-design.md` in place as a post-hoc decision.
- If optional evidence or a non-blocking check is unavailable, continue only with a truthful `PARTIAL` result and explicit residual uncertainty.
- If implementation behavior conflicts with the approved contract/design, preserve the deviation and route it for review; do not silently repair the contract or declare parity.
- `BLOCKED` and `PARTIAL` are skill result labels. The common STOP payload, queue/state/lifecycle mutations, review, and verification gates remain coordinator-owned.

## Done means

The approved target paths contain the smallest complete vertical slice and stable-boundary tests, DB-changing work uses the approved migration/test-DB contract, deviations and check results are recorded, and the implementation is handed to an independent reviewer. Done means ready for review, not that migration parity is proven.
