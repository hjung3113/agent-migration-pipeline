---
name: target-feature-design
description: Use after a behavior contract is sufficiently approved to redesign one business feature for React, FastAPI, PostgreSQL, and an isolated platform adapter boundary.
compatibility: OpenCode project skill
---

# Target Feature Design

Use `docs/templates/target-feature-design.md` and the canonical structural rejection rules in `docs/13-legacy-structure-rejection-contract.md`.

Design from behavior intent, not legacy file/class/object structure.

Cover:

- React responsibilities and user workflow;
- FastAPI transport contract;
- application/domain responsibilities;
- PostgreSQL persistence semantics;
- platform/DLL adapter impact;
- errors and observability;
- test/verification hooks;
- rollout/compatibility concerns;
- a complete LSR-01..LSR-07 legacy-structure disposition.

Do not default to one React boundary per WPF/ViewModel unit, one backend boundary per C# class/service, one PostgreSQL object per MSSQL object, or one endpoint per legacy operation. Any `RETAINED-JUSTIFIED` legacy-shaped element needs a current durable requirement/evidence reference.

For any feature that changes PostgreSQL schema, also define the schema delta, Alembic revision path/identity, clean test-DB bootstrap requirement, canonical `postgres-test-rw` profile, explicit seed/fixture identity (or `none`), and DB verification evidence according to `docs/13-postgresql-test-db-and-schema-migration.md`. A schema-changing design without this plan is not ready for implementation.

If the first DB-backed feature requires the deferred bootstrap and `scripts/db/pg_test_bootstrap.py` does not yet exist, the approved design must explicitly include that path in implementation scope. Do not let the implementer invent a manual DDL, raw connection, or general-`DATABASE_URL` workaround.

If a material unknown affects the design or a medium/high lock-in carryover disposition, mark the relevant part provisional or blocked instead of selecting a convenient assumption or preserving the legacy shape "for safety".
