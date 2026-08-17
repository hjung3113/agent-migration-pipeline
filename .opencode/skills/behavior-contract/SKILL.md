---
name: behavior-contract
description: Use after legacy discovery to specify a feature as observable inputs, business rules, outputs, side effects, errors, and comparison semantics independent of WPF/source-file structure.
compatibility: OpenCode project skill
---

# Behavior Contract

Use `docs/templates/behavior-contract.md`.

For each scenario:

1. define inputs and preconditions;
2. enumerate business rules with stable IDs;
3. define outputs and DB changes;
4. define files/logs/events/callbacks where relevant;
5. define errors/warnings;
6. identify order/timing requirements only when business-significant;
7. define every material exact/tolerant/normalized/order-sensitive comparison in the feature's `## Comparison semantics`; feature-specific rules belong in the contract, while a reusable Rulebook rule must be cited explicitly rather than copied or implied;
8. classify every material legacy claim as `observed` or `inferred`; never mix both in one bullet/row, and make every inferred claim cite the observation/evidence it derives from;
9. attach evidence and confidence grade to each material rule independently from provenance — `observed` is not a synonym for grade B;
10. separate current legacy behavior from desired future corrections;
11. list materially unsupported inferences or unknown comparison semantics as unresolved questions instead of inventing defaults.

Comparison semantics are part of the behavior specification. Never defer a tolerance, normalization, ordering rule, or other comparison assumption to test/helper code. A contract may be PARTIAL, but a material comparison whose semantics are missing or still represented only by template placeholders remains unresolved and will block parity verification until the contract is updated.

Never fill missing behavior with guessed requirements, and never duplicate the same claim under both provenance classes.
