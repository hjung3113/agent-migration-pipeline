---
name: behavior-contract
description: Primary skill when discovered legacy behavior must be synthesized into the feature's observable contract (behavior-contract.md — inputs, rules, outputs, side effects, errors, comparison semantics); do not use as the primary skill for grading one existing claim, registering one new unknown, or a post-implementation parity verdict.
compatibility: OpenCode project skill
---

# Behavior Contract

## Primary artifact boundary

Invoke this as the **primary skill** only when discovered legacy behavior must be synthesized into the feature's observable contract before target design. The primary artifact is `migration/features/{feature-id}/behavior-contract.md`: inputs, business rules, outputs, side effects, errors, comparison semantics, and unresolved items.

Do not use this as the primary skill for:

- assigning a grade to one already-existing claim — `evidence-grading` owns that sub-output;
- registering one new unanswered unknown — `uncertainty-management` owns the open-question entry;
- a post-implementation parity verdict — `parity-verification` owns the verification report.

This skill **composes** the other skills rather than competing with them: while writing the contract, grade each material rule with `evidence-grading`, and register a materially unanswered question with `uncertainty-management`. Supporting skills produce only their narrower sub-output and never take over contract ownership.

## Skill tie-break

When more than one skill appears applicable:

1. identify the artifact the current step is required to produce or update;
2. select the skill that owns that primary artifact;
3. invoke supporting skills only for their narrower sub-output;
4. return all outputs to the primary agent/coordinator; do not let a supporting skill silently change phase or scope.

Worked example: source suggests a rule but runtime evidence is unavailable while the contract is being written — this skill owns the step; `evidence-grading` grades the rule from available evidence; `uncertainty-management` is also used only if an unanswered question materially remains.

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
