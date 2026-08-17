# ADR-0003: Business feature is the migration unit

- Status: Accepted
- Date: 2026-08-15
- Updated: 2026-08-18

## Context

The target changes UI framework, backend language/framework, database, and potentially platform integration. File-to-file or class-to-class conversion would preserve accidental WPF/C#/MSSQL decomposition and make framework replacement look like architectural redesign.

The original decision said to migrate by business feature, but that is insufficient unless the process also defines how to distinguish required legacy semantics from incidental legacy structure.

## Decision

Plan, design, implement, review, and verify migration by business feature / vertical slice.

A feature may cross WPF UI, C# classes/services/helpers, MSSQL objects, files, tests, callbacks, and the host/DLL boundary. Those legacy elements are evidence inputs to the feature; they are not target-module boundaries.

Legacy technical shape is not a target requirement by default. Any legacy-shaped element retained in the target requires a current evidenced reason such as an approved behavior rule, data-integrity constraint, external/platform contract, or rollout compatibility requirement.

The canonical executable rejection/disposition rules and anti-pattern IDs are defined in `docs/13-legacy-structure-rejection-contract.md`.

## Required consequences

- discovery records structural facts separately from business requirements;
- target design explicitly disposes of legacy carryover candidates rather than using free-form "avoid legacy" prose;
- WPF screen/ViewModel/code-behind, C# class/service boundaries, event/lifecycle chains, MSSQL object layout, operation granularity, DTO/entity shape, and host/DLL glue are all presumptively non-authoritative target structure;
- justified compatibility carryover is allowed, but its evidence and isolation boundary must be recorded;
- unresolved medium/high lock-in carryover questions block/provisionalize design instead of defaulting to preservation;
- adversarial review checks for renamed or framework-equivalent copies, not only literal WPF/MSSQL dependencies.

## Consequences

- target design can match business intent instead of legacy class/file boundaries;
- dependency discovery becomes a required early phase;
- feature scopes may cross many legacy files and DB objects;
- some target structures may still resemble legacy structures when evidence genuinely requires them;
- structural-rejection evidence becomes part of the pre-implementation design review and post-implementation independent review.
