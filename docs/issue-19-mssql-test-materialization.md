# MSSQL Test Materialization Design

Issue: #19 — production-derived MSSQL schema/minimal data cannot currently be prepared safely and reproducibly for characterization/parity work.

This document defines the design only. DB connection code, extraction/materialization scripts, manifests, fixtures, and runtime tests remain implementation work behind `AGENTS.md` rule 13.

## Goal

Provide a one-way, auditable way to materialize an approved subset of a production-like MSSQL state into a dedicated test MSSQL database without giving the migration pipeline a write path to production or silently copying unreviewed sensitive data.

The output is a **versioned test-state materialization**, not a continuously synchronized replica.

## Adversarial findings

The issue identifies a real verification gap, but the proposed solution is unsafe or over-broad if applied literally.

1. Calling the operation `sync` implies in-place/continuous or potentially bidirectional reconciliation. The required behavior is narrower: one-way materialization from a read-only source into an isolated test target.
2. "Masking list is non-empty" is not a safe default. It still permits an omitted sensitive column to be copied unchanged. Data copy must fail closed unless every copied source column is explicitly classified.
3. Arbitrary sampling (`TOP`, random rows, percentage samples) is not a valid fixture strategy. It is nondeterministic and can break parent/child integrity or omit the business case under test.
4. Copying every database object mechanically is unsafe. Jobs, users/permissions, linked-server dependencies, cross-database references, mail/CLR/external side effects, or environment-specific definitions must not be reproduced merely because they exist in production.
5. A tool cannot make OQ-014 true. OQ-014 asks whether approved sanitized datasets/fixtures are actually available; designing or even implementing a materializer does not prove that a usable fixture exists.
6. Sanitization is not parity normalization. A transformed fixture can alter validation, uniqueness, formatting, joins, or other business behavior. Those effects must be visible in fixture provenance and must not be hidden inside comparison helpers.
7. A live production read is not automatically a consistent point-in-time snapshot. If the source consistency mechanism cannot be demonstrated, the resulting state may be useful for exploration but cannot be represented as a reproducible initial-state oracle.
8. "Log what was copied" must not mean logging copied values, credentials, or raw SQL parameters containing sensitive data. Evidence must contain metadata/fingerprints, not production records.

## Chosen model

The implementation target is a future `scripts/db/mssql_materialize_test.py`-style command with two phases:

1. **plan/preflight** — validate connection roles, target isolation, manifest completeness, object safety, and source-read consistency requirements without writing anything;
2. **materialize** — apply only the approved schema/data plan to the test database and emit non-sensitive provenance evidence.

There is no reverse path and no production mutation path.

### Scope ownership

- Issue #23 owns credential injection and connection-profile naming/storage.
- Issue #20 owns the mandatory runtime guard that prevents dangerous SQL from reaching a production connection. A server-enforced read-only production credential remains the primary defense; the code guard is defense in depth.
- Issue #18 may provide schema/object inspection output, but this design does not require #19 to become another general MSSQL inspection framework.
- Issue #22 consumes prepared DB states for snapshot/diff verification; #19 does not implement the parity diff engine.

Implementation of #19 is blocked until #20 and #23 establish their contracts. The materializer must consume those contracts rather than inventing its own competing connection model.

## Materialization manifest

Every run is driven by an explicit, reviewable manifest. The exact serialization format is an implementation decision, but the semantic fields are fixed.

### Required run identity

- source connection role/profile reference;
- target connection role/profile reference;
- feature/scenario reference or other reason for the fixture;
- approved schema object set;
- per-table data mode and row-selection rule;
- per-column copy/transform classification for every copied column;
- required post-load integrity checks;
- source-consistency requirement;
- manifest revision/hash.

No wildcard means "all production data". Absence of an entry means **do not copy it**.

### Schema object policy

Schema materialization is allowlist-based and feature/scenario scoped.

Allowed only when explicitly selected and required by the dependency map:

- tables and columns;
- primary/foreign/unique/check/default constraints;
- required indexes;
- required views/functions/stored procedures/triggers after their definitions are reviewed for test safety.

Never copied by the v1 materializer:

- logins/users/permissions/credentials;
- SQL Agent jobs/schedules;
- linked-server configuration;
- server/database operational settings unrelated to feature behavior;
- backup/restore configuration;
- any server-level object.

An allowed DB-scoped object that references another database/server or can produce external side effects is rejected until that dependency is explicitly reviewed and represented as a safe test dependency. Creating an object in a test DB does not make its external references safe.

### Data policy

Each table is either `schema-only` or explicitly data-enabled.

For a data-enabled table:

1. row selection is explicit and scenario-oriented; the tool does not invent random/generic sampling;
2. the selected column set is explicit; `SELECT *` semantics are forbidden;
3. every selected source column is classified as either approved direct copy or an approved transformation;
4. unclassified/new columns cause preflight failure instead of default copying;
5. required parent/reference rows are explicitly included by the manifest; v1 does not infer an automatic FK-closure algorithm;
6. post-load constraints/integrity checks must pass or the materialization fails.

This intentionally favors a small manifest over a generic data-cloning framework.

## Sanitization contract

Transformations are chosen per column from reviewed project policy; this design does not speculate a library of masking algorithms before real schemas are known.

A transformation must record the invariants it is required to preserve when they matter to the scenario, for example nullability, equality relationships, uniqueness, format/length class, numeric range, or foreign-key compatibility.

Deterministic transformation is required when equality or cross-row/cross-table identity must be preserved. Determinism alone does not make a transformation behaviorally valid.

If sanitization changes a property that the feature behavior depends on, that fixture cannot be used to claim parity for that rule unless the approved behavior contract explicitly establishes that the changed representation is irrelevant to the comparison. The masking operation itself is never hidden as a normalization/tolerance rule.

Raw production values are never written to repository evidence. Sanitized row data also stays out of Git by default unless company policy explicitly approves a persisted fixture artifact.

## Safety invariants

Preflight/materialization must fail closed when any invariant cannot be proven.

1. The production source uses a DB-server-enforced read-only credential; a conventionally named profile is not sufficient proof.
2. Issue #20's runtime guard must identify source and target roles and reject write-capable execution against the source.
3. Source and target must resolve to distinct DB identities. An ambiguous or identical host/database identity is fatal.
4. V1 targets a fresh/empty dedicated test database. It does not reconcile or clean an arbitrary existing DB. In-place reset/merge behavior requires a separate explicit design decision.
5. Source connections execute metadata/data reads only. DDL/DML and stored-procedure execution needed for materialization occur only against the test target.
6. Production-derived DB object definitions are treated as data to review/apply to the test target, never as permission to execute their bodies against production.
7. Any unexpected schema column/object discovered relative to the reviewed manifest blocks the run instead of being silently copied.
8. Secrets, connection strings, raw rows, and sensitive parameter values are excluded from logs/evidence.

## Source consistency and reproducibility

A materialization run must declare how source consistency was obtained.

Preferred input is an approved read-only replica/snapshot or another mechanism that provides a safe consistent view. If live production reads are used, the implementation must confirm a consistency mode that does not introduce unacceptable production locking/impact.

When a consistent point-in-time view cannot be demonstrated, the run is marked `non-reproducible-live-read`. It may support discovery, but characterization/parity artifacts must not cite it as proof that multiple executions started from the same DB state.

Every successful run emits enough metadata to identify the state without storing its sensitive contents:

- run ID and timestamps;
- logical source/target identity (no secrets);
- tool revision;
- manifest hash;
- source consistency mode;
- selected schema-object names and definition hashes;
- start/end source schema fingerprint or equivalent drift check;
- per-table copied row counts;
- transformation rule identifiers/versions, not transformed values;
- post-load integrity-check results;
- final target schema/materialization fingerprint;
- success/failure and reason.

Feature-specific evidence belongs with that feature; reusable project-wide run evidence may live under `migration/evidence/`. In either location, the evidence record references the approved internal fixture/run location rather than embedding sensitive rows.

## Characterization/parity use

A production-derived materialization is valid as a characterization/parity initial state only when:

- the materialization succeeded under all safety checks;
- its provenance record is available;
- the fixture is stable/reusable for the compared executions, or both sides demonstrably consume the same frozen state;
- sanitization preserves the behaviorally relevant properties for the scenario;
- any comparison semantics affected by representation changes are explicitly declared in the feature behavior contract;
- the verifier records the fixture/schema version in the effective judge configuration, so changing the fixture invalidates self-check reuse.

A materializer run is preparation evidence, not proof that the legacy and target behaviors are equal.

## OQ-014 handling

OQ-014 remains `OPEN` after this design.

It may become `CONFIRMED` only when there is evidence that an approved production-like sanitized dataset/fixture is actually available for use. A future successful implementation/materialization can be part of that evidence, but the status change must refer to the real fixture/workflow and its approval/provenance — not merely to the existence of code.

## Failure behavior

The future command exits without performing data materialization when any of these is true:

- connection-role contract is missing or source read-only status is unproven;
- source/target identity collision or ambiguity exists;
- target is not a fresh/empty approved test DB;
- manifest contains wildcard/unclassified data scope;
- current schema contains a selected/unexpected column that is not classified;
- an approved schema object has unresolved external/cross-database side effects;
- required source consistency cannot be established for a run that requests reproducible characterization use;
- a write-to-source attempt is detected;
- post-load integrity checks fail.

A partial load is a failed run and must not be cited as a valid fixture.

## Implementation verification requirements

When implementation is explicitly authorized, tests must at minimum prove:

- source and target identity collision is rejected;
- production write/DDL/DML/EXEC paths are rejected even when configuration is misleading;
- non-empty test targets are rejected in v1;
- schema-only materialization works without data-copy permission;
- `SELECT *`/wildcard scope and unclassified/new columns are rejected;
- explicit copied columns and transformations produce expected row counts while preserving declared integrity constraints;
- unresolved cross-database/external-side-effect DB objects are rejected;
- manifest/schema changes alter the run fingerprint;
- logs/evidence contain no connection secrets or row values;
- failed/partial loads cannot produce a success evidence record;
- a non-reproducible live read cannot be represented as a reproducible characterization initial state.

Actual production connectivity is not required for unit tests; integration validation against approved MSSQL test infrastructure occurs only after the safety/credential prerequisites are implemented.

## Non-goals

Do not add continuous replication, CDC, bidirectional sync, automatic PII discovery, a generic anonymization framework, automatic FK graph crawling, arbitrary existing-target reconciliation, PostgreSQL bootstrap/migration, DB snapshot diffing, production backup/restore automation, or DB credential management to #19.

Those features either belong to other issues or require evidence of a real need before adding complexity.

## Acceptance criteria

The #19 design is complete when the repository defines one-way fail-closed materialization, explicit schema/data allowlists, per-column classification, sanitization provenance, source-consistency semantics, non-sensitive evidence, test-target isolation, dependencies on #20/#23, and the rule that OQ-014 remains factual rather than being resolved by tool existence.
