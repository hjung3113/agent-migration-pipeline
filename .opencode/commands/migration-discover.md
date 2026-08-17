---
description: Discover legacy behavior and dependencies for a scope before migration design.
agent: migration-coordinator
---

Analyze legacy scope: $ARGUMENTS

Read `migration/STATE.md` and Gate G0 in `docs/02-migration-pipeline.md` first.

If the project is still in Phase 0 and G0 is not `PASS`, run only gate-enabling inspection: use `legacy-discovery`, delegate platform-boundary work to `dll-boundary-analyzer`, produce `migration/evidence/dll-boundary-report.md` and `migration/evidence/observable-output-survey.md`, then evaluate G0. If any G0 criterion fails, apply the gate failure protocol and stop; do not begin broad feature discovery.

After G0 is `PASS`, use `legacy-discovery` and delegate source analysis to `legacy-analyzer`; if the scope touches the platform boundary, also delegate to `dll-boundary-analyzer`; if it touches MSSQL, delegate to `db-analyzer`.

Persist feature/dependency artifacts, evidence grades, queue updates, and unresolved questions. Do not implement target code.
