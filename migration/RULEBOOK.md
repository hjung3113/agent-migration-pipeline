# Migration Rulebook

Status: DRAFT — update only through explicit design/review decisions.

## General

1. Business behavior is authoritative over legacy class/file structure.
2. A migration Feature may span WPF UI, C# services, repositories, stored procedures, tables, files, and platform callbacks.
3. Unknown behavior must remain unknown until evidence resolves it.
4. Do not preserve a legacy pattern solely because it exists.
5. Do not intentionally change confirmed behavior without an explicit decision record.

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

## Agent workflow

1. Analyzer does not implement.
2. Implementer does not self-approve.
3. Reviewer assumes behavior may have been omitted or invented.
4. Verifier reports uncertainty instead of forcing PASS.
5. Repeated defects trigger Rulebook/Skill/process review.
6. Independent adversarial review depth scales with the slice's recorded lock-in risk: medium or higher requires independent review before commit; low-risk slices may skip it only when the rating and rationale are recorded in the queue artifact.
7. A verifier may not issue a trusted parity verdict until the effective judge configuration passes the mandatory negative-control self-check in `docs/03-evidence-and-verification.md`. A synthetic/framework self-test does not authorize changed adapters, source sets, comparison rules, or environments; failed/unavailable self-checks make verification `BLOCKED`.
