# ADR-0003: Business feature is the migration unit

- Status: Accepted
- Date: 2026-08-15

## Context

The target changes UI framework, backend language/framework, database, and potentially platform integration. File-to-file conversion would preserve too much legacy structure.

## Decision

Plan and verify migration by business feature / vertical slice, mapping all relevant WPF, C#, MSSQL, platform, and output dependencies into one feature artifact.

## Consequences

- target design can match business intent instead of legacy class/file boundaries;
- dependency discovery becomes a required early phase;
- feature scopes may cross many legacy files and DB objects.
