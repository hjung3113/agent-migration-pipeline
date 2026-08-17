---
description: Implement one feature whose behavior contract and target design have passed their gates.
agent: migration-coordinator
---

Implement feature: $ARGUMENTS

Read Gate G3 in `docs/02-migration-pipeline.md` and the feature's `target-feature-design.md`.

If this request contains the user's explicit instruction to start implementation, persist that instruction under `Implementation authorization` before evaluating G3. Evaluate all G3 criteria; do not treat "check preconditions" as sufficient.

If any G3 criterion fails, apply the gate failure protocol and stop. Only after G3 is `PASS` delegate implementation to `implementer` using `feature-migration`.

Persist deviations and new unknowns. Do not run the reviewer as the implementer.
