---
name: parity-verification
description: Primary skill when implementation and independent review are complete and legacy/contract expectations must be compared with target observations; the primary artifact is the verification report and PASS/FAIL/PARTIAL/BLOCKED verdict under predeclared comparison semantics; do not use for discovering/specifying legacy behavior or changing the contract/normalization rules after results are known.
compatibility: OpenCode project skill
---

# Parity Verification

## Primary artifact boundary

Invoke this as the **primary skill** only when implementation and independent review are complete and legacy/contract expectations must be compared with target observations. The primary artifact is the verification report and parity verdict using the **predefined** judge/comparison semantics (`migration/features/{feature-id}/verification.md`).

Do not use this as the primary skill for:

- discovering or specifying legacy behavior — `behavior-contract` (synthesis) and the analysis roles own that; evidence records are **inputs** here, not the primary output;
- changing the behavior contract or normalization rules after results are known — a comparison-semantics gap is `BLOCKED`, never a post-hoc redefinition.

This skill **composes** with the others: it consumes graded evidence records produced by `evidence-grading` and treats unresolved comparison semantics as open questions for `uncertainty-management`, without owning either artifact.

## Skill tie-break

When more than one skill appears applicable:

1. identify the artifact the current step is required to produce or update;
2. select the skill that owns that primary artifact;
3. invoke supporting skills only for their narrower sub-output;
4. return all outputs to the primary agent/coordinator; do not let a supporting skill silently change phase or scope.

Worked example: the target implementation has run and its callback order must be compared with the approved contract — use this skill; evidence records are inputs, not the primary output.

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
4. when target PostgreSQL state is a required source, require a guarded dedicated test target prepared by the canonical bootstrap defined in `docs/13-postgresql-test-db-and-schema-migration.md`; record logical profile `postgres-test-rw`, non-secret guarded target identity, reset evidence, Alembic head, and seed/fixture identity in the verification environment;
5. a dirty, shared, unidentified, manually prepared, guard-bypassed, raw-connection, or general-`DATABASE_URL` target makes the PostgreSQL source unavailable; if that source is required, verification is `BLOCKED`;
6. a test/helper may implement only the declared comparison rule and must not relax, broaden, or silently override it; record the originating contract comparison row/subject or Rulebook reference in the verification report;
7. validate the judge by detecting a controlled mismatch where practical;
8. report mismatches under the declared semantics rather than normalizing them away;
9. use PASS, FAIL, PARTIAL, or BLOCKED;
10. list unverified behavior and comparison-specification gaps explicitly;
11. if failures repeat across features, recommend a Rulebook/Skill/process change.
