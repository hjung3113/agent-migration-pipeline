---
name: parity-verification
description: Use after implementation and independent review to compare legacy and target behavior using the strongest available composite judge and produce an evidence-based verification report.
compatibility: OpenCode project skill
---

# Parity Verification

Use `docs/templates/verification.md` and persist the feature result as `migration/features/{feature-id}/verification.md`.

Potential judge inputs:

- legacy existing tests;
- new contract tests;
- characterization fixtures;
- DB before/after comparisons;
- returned/generated outputs;
- files/logs/events/callbacks;
- exception/error behavior;
- approved manual observations.

Rules:

1. before comparing, resolve every material comparison to the feature's `behavior-contract.md` `## Comparison semantics` or to an explicit Rulebook rule referenced by that section;
2. feature-specific exact/tolerance/normalization/order semantics must be declared in the behavior contract; do not introduce them directly in test, fixture, adapter, snapshot, or helper code;
3. if the behavior contract is missing, its comparison section is absent/empty/placeholder-only for material behavior, or a required comparison rule is absent/ambiguous, stop with `BLOCKED` until the contract is updated — never infer a default from test code;
4. a test/helper may implement only the declared comparison rule and must not relax, broaden, or silently override it; record the originating contract comparison row/subject or Rulebook reference in the verification report;
5. validate the judge by detecting a controlled mismatch where practical;
6. report mismatches under the declared semantics rather than normalizing them away;
7. use PASS, FAIL, PARTIAL, or BLOCKED;
8. list unverified behavior and comparison-specification gaps explicitly;
9. if failures repeat across features, recommend a Rulebook/Skill/process change.
