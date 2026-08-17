# Migration Rulebook

Status: DRAFT — update only through explicit design/review decisions.

## General

1. Business behavior is authoritative over legacy class/file structure.
2. A migration Feature may span WPF UI, C# services, repositories, stored procedures, tables, files, and platform callbacks.
3. Unknown behavior must remain unknown until evidence resolves it.
4. Do not preserve a legacy pattern solely because it exists.
5. Do not intentionally change confirmed behavior without an explicit decision record.

## Legacy structure rejection

1. `docs/13-legacy-structure-rejection-contract.md` is the canonical operational contract for deciding whether legacy technical structure may appear in the target.
2. Legacy technical similarity is permitted only when an approved behavior rule, verified data-integrity constraint, verified external/platform contract, or verified rollout constraint requires it.
3. Do not map WPF screen/ViewModel/code-behind boundaries 1:1 to React pages/components/state/hooks.
4. Do not map C# class/service/manager/repository/inheritance boundaries 1:1 to FastAPI routers/services/modules/repositories.
5. Do not reproduce WPF event/Dispatcher/callback/lifecycle chains as equivalent frontend/backend handler chains unless observable ordering/lifecycle semantics require them.
6. Do not replicate MSSQL table/column/view/procedure/trigger organization into PostgreSQL by default; preserve required data semantics and integrity, not incidental object layout.
7. Do not derive one HTTP endpoint per legacy method/stored procedure or copy legacy DTO/entity shapes into public API/domain models without a current contract reason.
8. Host/DLL/WPF integration concerns belong behind the platform adapter and must not leak into core business logic.
9. A target design must disposition each applicable carryover candidate as `REJECTED`, `RETAINED-JUSTIFIED`, `NOT-APPLICABLE`, or `BLOCKED`; retention requires durable evidence.

## Evidence

1. Important business rules must have an evidence grade.
2. Source inspection alone does not equal observed runtime behavior.
3. Existing tests are evidence, not complete truth.
4. Characterization tests describe current behavior; they do not automatically endorse it as desired behavior.
5. If parity requires normalization/tolerance, document the rule explicitly.
6. Define comparison semantics per feature; do not default to byte-for-byte equality. Rules 7-10 are examples, not an exhaustive list — a case they do not cover still requires an explicit comparison rule.
7. Compare business identifiers and money values exactly, by numeric value and declared scale, not by serialized string form.
8. Allow floating-point tolerance for analytical results only when the legacy implementation already has numeric tolerance, and only at a tolerance the contract states explicitly and justifies against the legacy value.
9. Normalize timestamps/timezones only when representation differs and semantics are unchanged.
10. Use order-insensitive comparison only when order is not part of the behavior contract.
11. Comparison semantics are specification, not test implementation. Every feature-specific exact/tolerance/normalization/order rule must be declared in that feature's `behavior-contract.md` `## Comparison semantics`; a reusable cross-feature rule may live in this Rulebook only when the feature contract cites the applicable Rulebook rule explicitly. A test/helper may implement a declared rule, but must not invent, relax, or silently override comparison semantics. A missing, placeholder-only, empty, ambiguous, or helper-only comparison rule blocks parity verification rather than defaulting to equality or permissive normalization.
12. Sanitizing or masking a production-derived fixture is fixture preparation, not a hidden comparison normalization. Record the transformation provenance; if it changes a behaviorally relevant property, that fixture cannot support parity for that rule unless the approved behavior contract establishes that the changed representation is irrelevant.

## Platform / DLL

1. Platform integration is an adapter boundary.
2. Core business logic must not depend directly on WPF Dispatcher, host-specific callbacks, or assembly loading details.
3. Whether a compatibility C# DLL remains in the target is unresolved until host capabilities are confirmed.
4. If a compatibility DLL is required, keep it thin and contract-focused.

## Frontend

1. Do not reproduce WPF control hierarchy mechanically in React.
2. Preserve user/business workflow semantics, not pixel/control equivalence, unless a specific UI requirement is confirmed.
3. Put business rules in backend/domain/application layers unless there is a clear UI-only reason.

## Backend

1. FastAPI endpoints are transport boundaries, not the home for all business logic.
2. Define stable request/response/error contracts per feature.
3. Keep host-platform compatibility logic separate from general application services.
4. Every error response uses the single standard envelope (`code`, `message`, optional `detail`) — including request validation errors, framework errors, and uncaught exceptions. Do not invent a second error shape (ADR-0006).
5. Error `code` values are stable, UPPER_SNAKE_CASE contract identifiers; the HTTP status↔code mapping is an explicit table, never derived from `HTTPStatus` phrase text, which is not stable across Python versions (ADR-0006).
6. Business failures raise the transport-agnostic `AppError` from domain/service code; HTTP status is resolved at the API boundary from the code table unless the raise site sets an explicit override. Domain code never shapes HTTP responses.
7. `detail` is a structured object/array or omitted entirely — never a bare scalar; a handler that would send a scalar detail drops it (ADR-0006).
8. Cross-cutting API conventions (pagination, versioning, idempotency, auth/session shape) are decided per feature at first real need and recorded in that feature's design — not silently inherited from a previous feature.

## Database

1. Do not translate MSSQL DDL/SP syntax mechanically without understanding semantics.
2. Inventory stored procedures, triggers, functions, views, jobs, constraints, defaults, collations, and transaction behavior.
3. Business logic embedded in DB objects must be explicitly relocated or intentionally retained/reimplemented.
4. Preserve data integrity semantics before optimizing schema design.
5. Production-derived MSSQL test data is prepared by one-way materialization into an isolated test database; do not introduce continuous/bidirectional sync or an implicit production write path.
6. Production access for materialization requires a DB-server-enforced read-only credential. Connection naming and application guards are additional defenses, not substitutes for server-side permissions.
7. Data copy is fail-closed: schema-only is the default, and every copied table, row-selection rule, selected column, and direct-copy/transformation decision must be explicit. Wildcards, unclassified/new columns, and invented sampling rules block the run.
8. Production DB objects are copied only when explicitly required by the feature/scenario dependency map. Do not materialize server-level objects, credentials/permissions, jobs, linked-server configuration, or unreviewed external/cross-database side effects.
9. A production-derived fixture used as characterization/parity initial state must record source-consistency mode and provenance. A live read whose point-in-time consistency is unproven must not be represented as a reproducible initial-state oracle.
10. DB materialization evidence records metadata, hashes, row counts, integrity results, and transform identifiers only; never commit production rows, connection strings, secrets, or sensitive parameter values as evidence.
11. Live MSSQL inspection must use the bounded read-only evidence path in `docs/issue-18-mssql-readonly-inspection.md`: consume the canonical `mssql-prod-ro` profile, execute only fixed catalog `SELECT` queries, and expose no arbitrary SQL, DDL/DML, `EXEC`, application-row export, or legacy DB-object/job execution path.
12. Metadata absence is evidence only when inspection completeness for the requested scope is established. Hidden rows, unavailable/encrypted definitions, missing `msdb` visibility, query failures, or uninspected categories remain explicit uncertainty and must not be converted into "object/logic does not exist".
13. Raw operational DB definitions and job-step text are sensitive evidence. Do not automatically commit raw inspection captures into Git-tracked feature artifacts; persist reviewed migration-relevant facts, completeness status, hashes/source references, and only policy-approved minimal excerpts.
14. Production databases are read-only evidence sources for repository-owned migration/verification tooling. State-changing DB actions must pass the attested test-write boundary in `docs/12-db-execution-safety-contract.md`; wrapping a production mutation in a transaction/rollback does not make it safe.
15. DB profile labels or SQL keyword matching are not write authorization. The guard consumes Issue #23's canonical profiles and grants write capability only to an attested `test + read-write` target whose actual server/database identity matches approved expected-target metadata.
16. Database/server least privilege and environment network separation are primary controls. Repository code guards are defense in depth and must fail closed on unknown, ambiguous, or mismatched targets and must not expose a routine production-write bypass.
17. Target PostgreSQL schema history is canonical only in Alembic revisions under `target/backend/alembic/versions/`; do not maintain a parallel raw-SQL migration history.
18. Every PostgreSQL schema-changing feature must declare its Alembic revision, clean test-DB bootstrap requirement, canonical connection profile, seed/fixture identity, and DB verification evidence in its target design.
19. PostgreSQL reset/migration DDL must use canonical `postgres-test-rw` resolution plus the attested test-write capability from `docs/12-db-execution-safety-contract.md`. Raw connection inputs, direct-driver bypass, general `DATABASE_URL`, manual DDL, or a bootstrap-specific authorization path are not valid substitutes.
20. Target test seed state must be explicit, deterministic, and version-controlled. Ambient rows in a persistent/shared database are not valid feature or parity evidence.
21. When PostgreSQL state is a required parity source, verification starts from the canonical guarded clean bootstrap at the recorded unique Alembic head; manual DDL or an unidentified/dirty/guard-bypassed target blocks that source.

## Agent workflow

1. Analyzer does not implement.
2. Implementer does not self-approve.
3. Reviewer assumes behavior may have been omitted or invented.
4. Verifier reports uncertainty instead of forcing PASS.
5. Repeated defects trigger Rulebook/Skill/process review.
6. Independent adversarial review depth scales with the slice's recorded lock-in risk: medium or higher requires independent review before commit; low-risk slices may skip it only when the rating and rationale are recorded in the queue artifact.
7. A verifier may not issue a trusted parity verdict until the effective judge configuration passes the mandatory negative-control self-check in `docs/03-evidence-and-verification.md`. A synthetic/framework self-test does not authorize changed adapters, source sets, comparison rules, or environments; failed/unavailable self-checks make verification `BLOCKED`.
