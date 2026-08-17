---
description: Design one approved feature for React, FastAPI, PostgreSQL, and the platform compatibility boundary.
agent: migration-coordinator
---

Design feature: $ARGUMENTS

Require `migration/features/<feature>/behavior-contract.md` Gate G2 result to be `PASS` under the canonical criteria in `docs/02-migration-pipeline.md`. If G2 is not `PASS`, apply the gate failure protocol and stop.

Delegate to `migration-designer` using `target-feature-design`. Do not mechanically preserve WPF/C#/MSSQL structure. Record provisional decisions as open questions rather than silently resolving them.

Write or update `migration/features/<feature>/target-feature-design.md` from `docs/templates/target-feature-design.md`, then have `migration-coordinator` perform the G3.4 pre-implementation design review by checking the behavior-preservation map and rejected-legacy-structure evidence. Persist every G3 criterion result and evidence reference before evaluating the gate.

If G3.5 is not satisfied, leave G3 `BLOCKED` and stop after design. Do not dispatch implementation until a later explicit user instruction is persisted as the implementation authorization and the full G3 gate passes.
