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
- persist feature-specific records as `migration/features/{feature-id}/evidence/{evidence-id}.md` and project-wide/reusable records as `migration/evidence/{evidence-id}.md`;
- treat `evidence-record.md` as a schema template name, not the required persisted instance filename;
- keep direct facts in `Observation` and derived interpretation only in `Inference (optional)`;
- note if production data cannot be committed and point to an approved internal evidence location instead;
- contradictory evidence blocks completion until reconciled or explicitly accepted as a known risk.
