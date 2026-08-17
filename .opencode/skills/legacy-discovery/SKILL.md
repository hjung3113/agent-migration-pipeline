---
name: legacy-discovery
description: Use when beginning analysis of a legacy area to map business features, C#/WPF execution paths, dependencies, side effects, tests, and unknowns before any target implementation.
compatibility: OpenCode project skill
---

# Legacy Discovery

## Goal

Turn legacy source into a feature/dependency inventory without treating source structure as the target design.

Use `docs/13-legacy-structure-rejection-contract.md` for stable LSR IDs. Discovery records carryover candidates as structural evidence only; it does not choose target replacements.

## Procedure

1. Identify externally reachable entry points in scope.
2. Trace calls through WPF, C# services/helpers/repositories, DB objects, files, and platform APIs.
3. Group paths by business purpose/feature rather than by file.
4. Record inputs, outputs, persistent side effects, callbacks/events, errors, and configuration dependencies.
5. Locate existing tests and note what they actually exercise.
6. Record WPF/ViewModel/code-behind boundaries, C# class/service boundaries, event/lifecycle chains, MSSQL object layout, operation/DTO shapes, and platform glue under the applicable LSR IDs when observed.
7. For every material claim, distinguish a directly visible/captured fact from derived business intent: prefix it `[observed]` or `[inferred]`, never combine both in one bullet, and make inferred claims cite their supporting observation/evidence.
8. Mark ambiguous/dead/conditional behavior as uncertain rather than converting it into an inferred fact.
9. Produce or update feature cards using `docs/templates/feature-card.md`.
10. Add material unknowns to `docs/05-open-questions.md`.

`observed` is claim provenance, not an evidence grade. A source-visible fact does not become grade B unless runtime behavior was directly observed under the project grading rules.

A legacy structure being common, repeated, or named like the business feature does not make it a target requirement.

## Done means

A feature has a bounded legacy map, explicit provenance for material claims, LSR-tagged structural observations where applicable, and enough evidence to begin a behavior contract. No target code is written by this skill.
