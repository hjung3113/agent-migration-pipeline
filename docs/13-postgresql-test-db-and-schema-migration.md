# PostgreSQL Test DB and Schema Migration Design

Status: accepted design for Issue #21; bootstrap implementation is deferred until the first DB-backed target feature requires it.

## Scope

This document defines the target PostgreSQL schema-history and disposable test-database contract used by Target Feature Design, implementation, and parity verification.

It does not implement the bootstrap tool, define production deployment migration policy, define MSSQL-to-PostgreSQL data-copy mechanics, or duplicate the shared DB connection/safety contracts owned by Issues #23 and #20.

## Current-state correction

Issue #21 was written when PostgreSQL migration tooling was assumed to be absent. The current repository already contains:

- `target/backend/alembic.ini`;
- `target/backend/alembic/`;
- `target/backend/alembic/versions/`;
- the `alembic`, `sqlalchemy`, and `psycopg` dependencies in `target/backend/pyproject.toml`;
- a persistent local PostgreSQL `app` database in `docker-compose.yml`.

Therefore Alembic adoption is no longer an open tool-choice question. The missing capability is an operational contract that makes schema application, reset, seed selection, and verification reproducible and safe.

The repository also now has two canonical shared DB contracts that Issue #21 must consume rather than reimplement:

- `docs/12-db-connection-secrets-contract.md` owns the logical `postgres-test-rw` profile and `PG_TEST_RW_CONN` injection path;
- `docs/12-db-execution-safety-contract.md` owns actual-target attestation, `TestWriteSession`, hazardous operation classification, and fail-closed execution safety.

## Adversarial review findings

1. **Re-opening Alembic selection would contradict the repository.** A second migration format or an Adopt/Defer decision would create two possible schema histories.
2. **The existing default database is not a disposable test database.** `docker-compose.yml` creates database `app` on a named volume, and the current Alembic configuration also defaults to `app`. A destructive reset must never infer that target.
3. **A bootstrap-specific connection convention would violate the shared DB contract.** Issue #23 already fixes `postgres-test-rw` and `PG_TEST_RW_CONN`.
4. **A profile label alone is not a safety proof.** A misconfigured secret could make `postgres-test-rw` point at the wrong server/database. Issue #20 now explicitly requires actual engine/server/database attestation before issuing test-write capability.
5. **Reset/migration is hazardous DDL, not a special exemption.** It must flow through the same `ddl` safety class and attested `TestWriteSession` boundary as other state-changing repository DB operations.
6. **Implicit seed data destroys reproducibility.** Tests that depend on ambient rows in a persistent volume can pass locally and fail in CI or parity runs.
7. **DB parity without a clean target baseline is not trustworthy.** Previous feature runs can contaminate before/after evidence unless schema revision and seed identity are recorded.
8. **Automatic downgrade requirements would be speculative.** Reset-from-clean is the required test primitive now; production rollback strategy has not been decided.

## Decisions

### 1. Alembic is the canonical PostgreSQL schema history

`target/backend/alembic/versions/` is the only durable target-schema migration history.

- Do not introduce a parallel raw-SQL migration directory.
- Raw SQL is allowed inside an Alembic revision when PostgreSQL-specific DDL cannot be expressed cleanly through Alembic operations.
- Direct `psql`/SQLAlchemy DDL executed only to make a test pass is not a migration.
- An integration-ready branch must have one Alembic head. Multiple unresolved heads block merge until explicitly reconciled.
- `alembic stamp` is not a normal bootstrap or verification path because it can claim a schema state that was never applied.

### 2. One bootstrap entry point will own disposable target-DB preparation

The canonical entry point is reserved as:

`python scripts/db/pg_test_bootstrap.py <command> --profile postgres-test-rw`

Its implementation is deferred until the first target feature actually changes PostgreSQL schema. That first feature's approved design must include the bootstrap path if the script still does not exist.

The bootstrap is an orchestrator, not a second migration or safety system. It delegates:

- connection resolution to the Issue #23 profile resolver;
- target attestation/capability issuance/operation safety to `docs/12-db-execution-safety-contract.md`;
- schema construction to Alembic.

Minimum commands when implemented:

- `reset`: obtain an attested `TestWriteSession`, reset the disposable application schema through the guarded DDL path, run `alembic upgrade head`, then verify current revision equals head;
- `upgrade`: obtain the same guarded test-write capability, run `alembic upgrade head`, then verify head;
- `status`: report non-secret attested database identity, current revision, expected head, and selected seed profile without destructive changes.

Do not add more commands until a real feature requires them.

### 3. Connection and execution safety are inherited, not reinvented

The bootstrap accepts only the canonical logical profile `postgres-test-rw` from `docs/12-db-connection-secrets-contract.md`. Its opaque connection value comes only from the fixed `PG_TEST_RW_CONN` mapping through the shared resolver.

The bootstrap must not accept raw connection strings, passwords, arbitrary environment-variable names, host/user/password tuples, secret-bearing config paths, or the application's general `DATABASE_URL` as supported migration/reset inputs.

Before any caller DDL executes, the shared safety boundary in `docs/12-db-execution-safety-contract.md` must:

1. resolve the canonical profile;
2. validate non-secret expected-target metadata/tool allowlist;
3. connect through the approved PostgreSQL connector;
4. attest actual engine, server identity, and database identity;
5. prove `environment == test` and `capability == read-write`;
6. issue the guarded test-write capability;
7. classify reset/migration statements as `ddl` and audit/enforce them through that capability.

Any unresolved identity, mismatch, missing safety metadata, unavailable guard, classification failure, or unknown/privileged operation fails closed before hazardous driver execution. There is no bootstrap-local `--force`, `--unsafe`, confirmation override, hostname heuristic, or alternate guard.

### 4. Reset the schema, not the whole PostgreSQL server/database

For the first implementation, `reset` operates only inside the dedicated attested test database:

1. resolve `postgres-test-rw` and obtain the guarded `TestWriteSession`;
2. drop and recreate the application schema (initially `public`) through the guarded DDL path;
3. run Alembic to `head` through the same safety boundary;
4. verify Alembic current revision equals the unique head;
5. apply an explicitly selected test seed, if any, through the same capability rules.

This avoids admin-level `DROP DATABASE` privileges and narrows destructive blast radius. The Issue #20 contract also denies `privileged` operations by default.

If a future feature requires database-level objects that cannot be recreated by schema reset, record a new design decision before widening privileges or destructive scope.

### 5. Seed data is explicit and separate from schema history

Bootstrap is schema-only by default.

- Do not put test-only business rows into Alembic revisions.
- Production reference data belongs in a migration only when it is genuinely part of production schema/state semantics.
- Feature test data must be deterministic, version-controlled, and named by the feature design/test plan.
- A parity run records the selected seed/fixture identity. Ambient rows from a persistent developer volume are never valid seed evidence.
- Do not create a global seed framework until more than one real feature needs shared seed behavior.

### 6. Schema-changing feature workflow

When a target feature changes PostgreSQL schema, `target-feature-design.md` must define:

- the schema delta and integrity semantics;
- intended Alembic revision path/identity;
- whether a clean bootstrap is required;
- canonical connection profile `postgres-test-rw`;
- seed/fixture identity, or `none`;
- DB assertions/parity evidence to collect;
- rollout/backfill behavior that cannot be proven by reset-from-clean, if any.

Implementation then:

1. creates/updates the Alembic revision named by the approved design;
2. creates the bootstrap tool only if this is the first DB-backed feature and the approved design includes it;
3. prepares a dedicated attested test target through the canonical profile + safety + bootstrap path;
4. proves `alembic current` equals the unique `head`;
5. runs feature tests and DB assertions;
6. records revision/head, guarded target identity, and seed identity in the implementation handoff.

If the bootstrap, shared profile resolver, or Issue #20 safety boundary is required but unavailable and its creation is not in approved scope, implementation is `BLOCKED`. Manual DDL, raw connection input, direct driver bypass, or general `DATABASE_URL` is not an acceptable workaround.

### 7. Parity verification requires a reproducible target DB baseline

When PostgreSQL state is a required verification source, the verifier must record:

- logical profile `postgres-test-rw` and non-secret attested target identity;
- successful guarded clean bootstrap/reset evidence;
- Alembic head revision;
- selected seed/fixture identity;
- feature DB before/after evidence under the behavior contract's comparison semantics.

A dirty, shared, unidentified, manually prepared, raw-driver, or guard-bypassed target database makes the PostgreSQL verification source unavailable and therefore blocks any verdict that requires it.

### 8. CI activation is demand-driven

Do not add an always-on PostgreSQL CI service during Phase 0 solely because this design exists.

When the first DB-backed target feature lands, CI must use the same profile/safety/bootstrap path as local development. At that point:

- CI injects `PG_TEST_RW_CONN` for a dedicated disposable test target;
- CI supplies the non-secret expected-target safety metadata required by Issue #20;
- CI invokes the shared resolver/attestation/guard before DB-backed tests or parity adapters;
- local and CI preparation semantics stay identical.

The existing persistent `docker-compose.yml` `app` database is not the disposable test target. A dedicated test service/profile target may be added when the first consumer exists; the public logical profile remains `postgres-test-rw`.

### 9. Downgrade and production rollout are separate decisions

A working `downgrade()` is not required merely to satisfy local reset tests. Require it only when the approved feature rollout/rollback design needs revision-level downgrade.

Production startup migration, zero-downtime DDL, data backfill, deployment ordering, and backup/restore policy remain outside this issue and must not be inferred from the test bootstrap design.

## Rejected alternatives

### Raw SQL files as the primary migration history

Rejected because Alembic is already installed/scaffolded and two histories would create drift.

### A bootstrap-specific connection variable or general `DATABASE_URL`

Rejected because Issue #23 already defines the canonical `postgres-test-rw` profile. A second connection path would allow DB tools to disagree about credentials and capability.

### Treating `postgres-test-rw` as sufficient proof of safety

Rejected because the Issue #20 contract requires actual engine/server/database identity attestation before issuing `TestWriteSession`.

### A bootstrap-local safety check or `--force`

Rejected because it would create a bypassable second authorization model. Reset/migration inherits the repository-wide `ddl` classification and guarded capability path.

### Dropping and recreating the whole database

Rejected for the first implementation because it requires broader privileges and increases blast radius without a current requirement.

### Seeding every test database with a global baseline dataset

Rejected under YAGNI. Feature-owned deterministic fixtures are sufficient until shared reference data is demonstrated.

### Implementing the bootstrap immediately in Phase 0

Rejected because no real target schema revision exists yet. The contract is fixed now so the first DB-backed feature cannot omit it, while implementation waits for a real consumer.

## Implementation acceptance criteria

When the first DB-backed feature implements this design, all of the following must be demonstrated:

1. `postgres-test-rw` resolves only through the Issue #23 shared profile contract;
2. actual engine/server/database identity is attested and `TestWriteSession` is issued under the Issue #20 safety contract before reset/migration DDL;
3. a valid dedicated test target can be reset from arbitrary prior test state to Alembic `head`;
4. running reset again produces the same schema/head and deterministic seed state;
5. unsafe, ambiguous, mismatched, unknown, or privileged targets/operations are rejected before hazardous driver execution;
6. the schema-changing feature has a committed Alembic revision;
7. the feature design and implementation handoff record revision/head plus seed identity;
8. DB-backed verification starts from the canonical guarded bootstrap rather than a persistent developer database;
9. CI, once DB-backed tests exist, invokes the same profile/safety/bootstrap path used locally.

## References

- Issue #21
- `docs/12-db-connection-secrets-contract.md` (Issue #23)
- `docs/12-db-execution-safety-contract.md` (Issue #20)
- `docs/06-tooling-decisions.md`
- `migration/RULEBOOK.md`
- `.opencode/skills/target-feature-design/SKILL.md`
- `.opencode/agents/implementer.md`
- `.opencode/skills/feature-migration/SKILL.md`
- `.opencode/skills/parity-verification/SKILL.md`
