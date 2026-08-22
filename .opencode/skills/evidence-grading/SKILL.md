---
name: evidence-grading
description: Primary skill when an existing behavior claim already has evidence/inference and must receive or update its A/B/C/D/? confidence grade with a supporting evidence record; do not use as the primary skill for inventing new behavior rules, deciding target behavior, or creating an open question whose answer is not known.
compatibility: OpenCode project skill
---

# Evidence Grading

## Primary artifact boundary

Invoke this as the **primary skill** only when an **existing behavior claim** already has evidence/inference that must receive or update an A/B/C/D/? confidence grade. The primary artifact is the grade plus the supporting evidence record/reference attached to that claim (persisted per the rules below).

Do not use this as the primary skill for:

- inventing a new behavior rule or synthesizing the feature contract — `behavior-contract` owns the contract;
- deciding target behavior — `target-feature-design` work owns that;
- creating an open question whose answer is not known — `uncertainty-management` owns the open-question entry.

This skill **composes** with the others: a behavior-contract step may invoke it to grade each material rule; that makes it a supporting skill for that step, not the owner of the contract.

## Skill tie-break

When more than one skill appears applicable:

1. identify the artifact the current step is required to produce or update;
2. select the skill that owns that primary artifact;
3. invoke supporting skills only for their narrower sub-output;
4. return all outputs to the primary agent/coordinator; do not let a supporting skill silently change phase or scope.

Worked example: a runtime capture already confirms an existing rule — use this skill to attach the grade/evidence record; do not create or reopen a behavior contract merely because the word `behavior` appears.

## Inputs

- An explicit existing claim and its scope.
- [Input] The referenced evidence and any existing record under `migration/features/<feature-id>/evidence/<evidence-id>.md` when the claim is feature-scoped.
- [Input] `migration/features/<feature-id>/feature-card.md` and the relevant contract when feature context is required.
- [Input] `migration/evidence/<evidence-id>.md` for project-wide/reusable evidence when the scope is project-wide.
- [Input] The current grade, provenance, contradiction history, and any applicable grade-transition decision from `docs/09-evidence-grade-transition-control.md`.

## Outputs

- [Output] A feature-scoped evidence record at `migration/features/<feature-id>/evidence/<evidence-id>.md`, or a project-scoped record at `migration/evidence/<evidence-id>.md`.
- [Output] The A/B/C/D/? grade and supporting evidence reference attached to the existing claim.
- For a read-only invoking role, return the complete evidence-record body and canonical destination to `migration-coordinator`; direct persistence is allowed only when the role-boundary contract grants it.
- This skill never updates `migration/STATE.md`, `migration/QUEUE.md`, feature lifecycle metadata, or the behavior contract's ownership decision.

## Procedure

1. [Input] Resolve whether the claim is feature-scoped or project-wide, then read the claim, its cited evidence, `migration/features/<feature-id>/feature-card.md` when applicable, and any existing evidence record.
2. [Input] Separate direct observation from interpretation, identify contradictions, and confirm that the claim already exists rather than inventing a new behavior rule.
3. [Output] Apply the grade meanings and transition controls below without upgrading a grade unless new evidence justifies it.
4. [Output] Record the observation, optional inference, provenance, grade, contradiction status, reproducible evidence reference, and persistence destination in the appropriate evidence record.
5. [Input] Check that production data handling, unresolved questions, and record references do not pretend to answer an unknown.
6. [Output] Return the grade, complete record body or authorized write result, canonical destination, and any `PARTIAL`/`BLOCKED` condition to `migration-coordinator`.

## Branches

- If a required claim, evidence reference, or feature scope is missing, return `BLOCKED`; do not manufacture a grade or evidence record.
- If required runtime evidence is unavailable, return `BLOCKED` when the requested grade transition depends on it; otherwise record the gap and return `PARTIAL` without upgrading the grade.
- If optional evidence is unavailable, continue only with a truthful provisional/`PARTIAL` record.
- If evidence conflicts, preserve both sides and return `PARTIAL` or `BLOCKED` until reconciled or explicitly accepted as a known risk.
- If a material unknown affects the claim's use in a medium/high lock-in decision, route it to `uncertainty-management` and stop the affected decision rather than inferring a grade.
- If the canonical evidence record already exists, update it in place only when authorized; otherwise return the complete update body to `migration-coordinator`.
- `BLOCKED` and `PARTIAL` are result labels for this skill; STOP payloads and lifecycle/state transitions remain owned by the applicable contracts and coordinator.

## Done means

The existing claim has a justified A/B/C/D/? grade, separate provenance, reproducible evidence references, contradiction/unknown handling, and a complete canonical evidence record persisted by an authorized role or handed to `migration-coordinator`. No grade-transition policy, queue/state mutation, or target behavior decision was invented here.

## Grading rules

Grades:

- A: strong confirmation from multiple/independent sources such as automated test plus observed behavior
- B: directly observed runtime behavior
- C: source plus DB/schema/config analysis without direct observation
- D: weak/source-only inference
- ?: unknown or currently unverifiable

Claim provenance is separate from these grades:

- `observed`: the claim is directly visible/captured in its cited evidence without interpretive business meaning;
- `inferred`: the claim requires interpretation beyond the direct evidence.

Rules:

- grade certainty, not whether the behavior is desirable;
- do not upgrade a grade without new evidence;
- never infer grade from provenance: a fact observed in source is not automatically grade B, because B is reserved for directly observed runtime behavior;
- never infer provenance from grade: C/D claims still need explicit `inferred` marking when interpretation is involved;
- split any claim that mixes a direct fact and an interpretation;
- store reproducible evidence using `docs/templates/evidence-record.md` when the claim is important;
- persist feature-specific records as `migration/features/<feature-id>/evidence/<evidence-id>.md` and project-wide/reusable records as `migration/evidence/<evidence-id>.md`;
- treat `evidence-record.md` as a schema template name, not the required persisted instance filename;
- keep direct facts in `Observation` and derived interpretation only in `Inference (optional)`;
- note if production data cannot be committed and point to an approved internal evidence location instead;
- contradictory evidence blocks completion until reconciled or explicitly accepted as a known risk.
