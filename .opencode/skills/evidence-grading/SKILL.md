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

Rules:

- grade certainty, not whether the behavior is desirable;
- do not upgrade a grade without new evidence;
- store reproducible evidence using `docs/templates/evidence-record.md` when the claim is important;
- note if production data cannot be committed and point to an approved internal evidence location instead;
- contradictory evidence blocks completion until reconciled or explicitly accepted as a known risk.
