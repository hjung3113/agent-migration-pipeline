---
description: Build or refine an evidence-graded behavior contract for one discovered feature.
agent: migration-coordinator
---

Specify feature: $ARGUMENTS

Use `behavior-contract`, `evidence-grading`, and `uncertainty-management`. Build the contract from discovered evidence, not desired target architecture.

Write or update `migration/features/<feature>/behavior-contract.md` from `docs/templates/behavior-contract.md`, then evaluate Gate G2 exactly as defined in `docs/02-migration-pipeline.md`. Persist G2 criterion results and evidence references in the contract.

If any G2 criterion fails, apply the gate failure protocol and stop before target design. Do not convert an unknown semantic into an inferred implementation decision.
