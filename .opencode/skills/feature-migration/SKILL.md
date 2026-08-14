---
name: feature-migration
description: Use only after a feature has an approved behavior contract and target design to implement the vertical slice while preserving evidence-backed behavior and recording deviations.
compatibility: OpenCode project skill
---

# Feature Migration

Preconditions:

- feature card exists;
- behavior contract exists;
- material rules have evidence grades;
- target feature design exists;
- blocking open questions are resolved or explicitly accepted as provisional.

Procedure:

1. implement the smallest complete vertical slice;
2. keep platform/DLL code behind adapters;
3. add automated tests at stable observable boundaries;
4. preserve data integrity and error semantics;
5. record deviations from target design;
6. do not broaden feature scope;
7. hand off to an independent adversarial reviewer.

Done means implementation is ready for review, not that migration parity is proven.
