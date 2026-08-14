---
name: legacy-discovery
description: Use when beginning analysis of a legacy area to map business features, C#/WPF execution paths, dependencies, side effects, tests, and unknowns before any target implementation.
compatibility: OpenCode project skill
---

# Legacy Discovery

## Goal

Turn legacy source into a feature/dependency inventory without treating source structure as the target design.

## Procedure

1. Identify externally reachable entry points in scope.
2. Trace calls through WPF, C# services/helpers/repositories, DB objects, files, and platform APIs.
3. Group paths by business purpose/feature rather than by file.
4. Record inputs, outputs, persistent side effects, callbacks/events, errors, and configuration dependencies.
5. Locate existing tests and note what they actually exercise.
6. Mark ambiguous/dead/conditional behavior as uncertain.
7. Produce or update feature cards using `docs/templates/feature-card.md`.
8. Add material unknowns to `docs/05-open-questions.md`.

## Done means

A feature has a bounded legacy map and enough evidence to begin a behavior contract. No target code is written by this skill.
