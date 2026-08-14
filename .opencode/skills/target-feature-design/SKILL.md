---
name: target-feature-design
description: Use after a behavior contract is sufficiently approved to redesign one business feature for React, FastAPI, PostgreSQL, and an isolated platform adapter boundary.
compatibility: OpenCode project skill
---

# Target Feature Design

Use `docs/templates/target-feature-design.md`.

Design from behavior intent, not legacy file structure.

Cover:

- React responsibilities and user workflow;
- FastAPI transport contract;
- application/domain responsibilities;
- PostgreSQL persistence semantics;
- platform/DLL adapter impact;
- errors and observability;
- test/verification hooks;
- rollout/compatibility concerns;
- legacy patterns intentionally removed.

If a P0 unknown affects the design, mark the relevant part provisional or blocked instead of selecting a convenient assumption.
