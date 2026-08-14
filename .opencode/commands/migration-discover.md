---
description: Discover legacy behavior and dependencies for a scope before migration design.
agent: migration-coordinator
---

Analyze legacy scope: $ARGUMENTS

Use the `legacy-discovery` skill and delegate source analysis to `legacy-analyzer`. If the scope touches the platform boundary, also delegate to `dll-boundary-analyzer`; if it touches MSSQL, delegate to `db-analyzer`.

Persist feature/dependency artifacts, evidence grades, queue updates, and unresolved questions. Do not implement target code.
