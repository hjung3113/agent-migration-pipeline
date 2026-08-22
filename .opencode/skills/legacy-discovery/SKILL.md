---
name: legacy-discovery
description: Use when beginning analysis of a legacy area to map business features, C#/WPF execution paths, dependencies, side effects, tests, and unknowns before any target implementation.
compatibility: OpenCode project skill
---

# Legacy Discovery

## Goal

Turn legacy source into a feature/dependency inventory without treating source structure as the target design.

Use `docs/13-legacy-structure-rejection-contract.md` for stable LSR IDs. Discovery records carryover candidates as structural evidence only; it does not choose target replacements.

## Inputs

- A validated `FEATURE_ID` and an identifiable, accessible legacy source/runtime scope.
- [Input] `migration/features/<feature-id>/feature-card.md` when the feature card already exists.
- [Input] Use `docs/templates/feature-card.md` for feature-card shape when creating or updating that artifact.
- [Input] Legacy C#/WPF source, MSSQL objects, files, platform APIs, configuration, tests, and approved runtime evidence in scope.
- [Input] Existing `docs/05-open-questions.md` entries and relevant Rulebook constraints.

## Outputs

- [Output] The bounded dependency map at `migration/features/<feature-id>/legacy-map.md`.
- [Output] Feature-card update requests for `migration/features/<feature-id>/feature-card.md` and project-wide update requests for `docs/05-open-questions.md` when discovery exposes material unknowns.
- For a read-only invoking role, return complete report/update bodies and canonical destinations to `migration-coordinator`; direct persistence is allowed only when the role has permission.
- This skill never chooses target architecture or updates `migration/STATE.md`, `migration/QUEUE.md`, or feature lifecycle metadata.

## Procedure

1. [Input] Resolve the feature scope and read `migration/features/<feature-id>/feature-card.md`, existing open questions, and the legacy/runtime scope before analysis.
2. [Input] Identify externally reachable entry points and trace calls through WPF, C# services/helpers/repositories, DB objects, files, and platform APIs.
3. [Input] Group paths by business purpose/feature rather than by file, and capture inputs, outputs, persistent side effects, callbacks/events, errors, and configuration dependencies.
4. [Input] Locate tests and state what they actually exercise; record WPF/ViewModel/code-behind, C# class/service, event/lifecycle, MSSQL, operation/DTO, and platform-glue boundaries under applicable LSR IDs when observed.
5. [Output] Produce or update `migration/features/<feature-id>/legacy-map.md` using `docs/templates/legacy-map.md` and return the complete body or authorized write result.
6. [Output] Return feature-card and `docs/05-open-questions.md` update requests for material unresolved facts, with provenance and evidence references.
7. [Input] Re-read the map for unsupported business intent, guessed target replacements, missing dependencies, and unrecorded ambiguity.

Mark ambiguous/dead/conditional behavior as uncertain rather than converting it into an inferred fact.

For every material claim, distinguish a directly visible/captured fact from derived business intent: prefix it `[observed]` or `[inferred]`, never combine both in one bullet, and make inferred claims cite their supporting observation/evidence.

`observed` is claim provenance, not an evidence grade. A source-visible fact does not become grade B unless runtime behavior was directly observed under the project grading rules.

A legacy structure being common, repeated, or named like the business feature does not make it a target requirement.

## Branches

- If the legacy scope, feature ID, or required durable input is unavailable, return `BLOCKED`; do not fabricate `migration/features/<feature-id>/legacy-map.md` or a dependency map.
- If runtime evidence is unavailable but source analysis can still establish a bounded map, record the gap and return `PARTIAL`; if the missing runtime fact is required to identify the scope or a dependency, return `BLOCKED`.
- If optional source/test evidence is unavailable, continue only with the limitation recorded in the map and a truthful `PARTIAL` result.
- If observed facts and inferred intent conflict, preserve both provenance classes and return `PARTIAL` or `BLOCKED`; never promote intent to observed behavior.
- If an unknown affects a medium/high lock-in target decision, persist the unknown request and stop target selection rather than guessing.
- If `migration/features/<feature-id>/legacy-map.md` already exists, update it in place only when authorized; otherwise return the complete update body to `migration-coordinator`.
- `BLOCKED` and `PARTIAL` are skill result labels; common STOP payloads and lifecycle/state transitions remain coordinator-owned.

## Done means

The feature has a bounded `migration/features/<feature-id>/legacy-map.md` with explicit provenance, applicable LSR-tagged structural observations, inputs/outputs/side effects/dependencies, evidence limitations, and material unknown update requests. No target code or target replacement was chosen by this skill.
