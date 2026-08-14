---
name: parity-verification
description: Use after implementation and independent review to compare legacy and target behavior using the strongest available composite judge and produce an evidence-based verification report.
compatibility: OpenCode project skill
---

# Parity Verification

Use `docs/templates/verification-report.md`.

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

1. define comparison semantics before comparing;
2. validate the judge by detecting a controlled mismatch where practical;
3. report mismatches rather than normalizing them away;
4. use PASS, FAIL, PARTIAL, or BLOCKED;
5. list unverified behavior explicitly;
6. if failures repeat across features, recommend a Rulebook/Skill/process change.
