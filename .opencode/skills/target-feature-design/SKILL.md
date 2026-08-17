---
name: target-feature-design
description: Use after a behavior contract is sufficiently approved to redesign one business feature for React, FastAPI, PostgreSQL, and an isolated platform adapter boundary.
compatibility: OpenCode project skill
---

# Target Feature Design

Use `docs/templates/target-feature-design.md` and the canonical structural rejection rules in `docs/13-legacy-structure-rejection-contract.md`.

Design from behavior intent, not legacy file/class/object structure.

Cover:

- React responsibilities and user workflow;
- FastAPI transport contract;
- application/domain responsibilities;
- PostgreSQL persistence semantics;
- platform/DLL adapter impact;
- errors and observability;
- test/verification hooks;
- rollout/compatibility concerns;
- a complete LSR-01..LSR-07 legacy-structure disposition.

Do not default to one React boundary per WPF/ViewModel unit, one backend boundary per C# class/service, one PostgreSQL object per MSSQL object, or one endpoint per legacy operation. Any `RETAINED-JUSTIFIED` legacy-shaped element needs a current durable requirement/evidence reference.

If a material unknown affects the design or a medium/high lock-in carryover disposition, mark the relevant part provisional or blocked instead of selecting a convenient assumption or preserving the legacy shape "for safety".
