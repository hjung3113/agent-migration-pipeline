---
name: evidence-grading
description: Use whenever a legacy behavior claim is captured or reviewed to assign an explicit A/B/C/D/? confidence grade and document the supporting observation or inference.
compatibility: OpenCode project skill
---

# Evidence Grading

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
