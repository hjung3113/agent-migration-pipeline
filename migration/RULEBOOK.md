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
