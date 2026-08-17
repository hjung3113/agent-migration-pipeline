---
name: feature-migration
description: Use only after a feature has an approved behavior contract and target design to implement the vertical slice while preserving evidence-backed behavior and recording deviations.
compatibility: OpenCode project skill
---

# Feature Migration

Preconditions:

- feature card exists;
- behavior contract exists;
- material rules have evidence grades;
- target feature design exists;
- blocking open questions are resolved or explicitly accepted as provisional;
- if PostgreSQL schema changes, the target design has a complete migration/test-DB plan under `docs/13-postgresql-test-db-and-schema-migration.md`.

Procedure:

1. implement the smallest complete vertical slice;
2. keep platform/DLL code behind adapters;
3. for PostgreSQL schema changes, use the approved Alembic revision path as the only schema history;
4. prepare DB-changing tests through the canonical bootstrap with logical profile `postgres-test-rw` through the shared resolver/DB guard; if a required bootstrap/resolver/guard is absent and not approved for creation in this feature, return `BLOCKED` rather than using manual DDL, raw connection input, or general `DATABASE_URL`;
5. add automated tests at stable observable boundaries;
6. preserve data integrity and error semantics;
7. record Alembic revision/head and seed identity for DB-changing work;
8. record deviations from target design;
9. do not broaden feature scope;
10. hand off to an independent adversarial reviewer.

Done means implementation is ready for review, not that migration parity is proven.
