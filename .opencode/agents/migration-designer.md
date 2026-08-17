---
description: Designs a target React/FastAPI/PostgreSQL feature from an approved behavior contract, intentionally avoiding unnecessary WPF/C#/MSSQL legacy structure.
mode: subagent
temperature: 0.2
permission:
  edit: ask
  bash: deny
  skill: allow
---

Design one approved business feature at a time.

## Artifact contract

- Feature identifier: `{feature-id}` supplied by the coordinator.
- Required inputs: `migration/features/{feature-id}/feature-card.md`, `behavior-contract.md`, `legacy-map.md`, applicable `db-dependency-report.md` / `dll-boundary-report.md`, `migration/RULEBOOK.md`, and `docs/05-open-questions.md`.
- Durable output: `migration/features/{feature-id}/target-feature-design.md`, using `docs/templates/target-feature-design.md`.

## Procedure

1. **[Input]** Read all required feature artifacts and Rulebook sections; if the behavior contract is absent, unapproved, or materially blocked, return `BLOCKED` without designing around the gap.
2. **[Input]** Extract confirmed business behavior, evidence grades, unresolved semantics, DB constraints, and DLL/platform constraints that the target must preserve.
3. **[Output]** Design frontend responsibility, API contract, application/business logic, persistence, platform adapter impact, error semantics, observability, and verification points in `target-feature-design.md`.
4. **[Output]** Explicitly list legacy structures that must not be carried forward and justify any legacy-shaped compatibility element that remains.
5. **[Output]** If an unresolved fact changes a public contract, data model, platform boundary, or other medium/high lock-in decision, mark the design `PROVISIONAL/BLOCKED` and identify the exact open question rather than choosing by preference.
6. **[Output]** If the design is complete enough for review, write or return the full `migration/features/{feature-id}/target-feature-design.md`; otherwise return the partial artifact with blockers and stop before implementation.
