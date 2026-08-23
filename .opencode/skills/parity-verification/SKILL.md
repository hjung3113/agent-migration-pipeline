---
name: parity-verification
description: Primary skill when implementation and independent review are complete and legacy/contract expectations must be compared with target observations; the primary artifact is the verification report and PASS/FAIL/PARTIAL/BLOCKED verdict under predeclared comparison semantics; do not use for discovering/specifying legacy behavior or changing the contract/normalization rules after results are known.
compatibility: OpenCode project skill
---

# Parity Verification

## Primary artifact boundary

Invoke this as the **primary skill** only when implementation and independent review are complete and legacy/contract expectations must be compared with target observations. The primary artifact is the verification report and parity verdict using the **predefined** judge/comparison semantics (`migration/features/<feature-id>/verification.md`).

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

## Inputs

- A validated `FEATURE_ID` and an implementation that is ready for independent verification.
- [Input] Use `docs/templates/verification.md` as the report shape.
- [Input] `migration/features/<feature-id>/behavior-contract.md` with all material comparison semantics declared.
- [Input] `migration/features/<feature-id>/review.md` from an independent reviewer.
- [Input] The implementation under test and approved `migration/features/<feature-id>/target-feature-design.md`.
- [Input] Available judge inputs: existing/new tests, characterization fixtures, guarded DB comparisons, outputs, files, logs, events, errors, and approved observations.
- [Input] Applicable evidence records under `migration/features/<feature-id>/evidence/<evidence-id>.md` and any project-wide evidence.

## Outputs

- [Output] The canonical verdict and verification report at `migration/features/<feature-id>/verification.md`.
- [Output] Explicit PASS, FAIL, PARTIAL, or BLOCKED result, declared comparison references, mismatches, unverified behavior, and residual uncertainty.
- For a read-only invoking role, return the complete report body and canonical destination to `migration-coordinator`; direct persistence is allowed only under the role-boundary contract.
- This skill does not edit implementation, behavior contract, review, `migration/STATE.md`, `migration/QUEUE.md`, or lifecycle metadata.

## Procedure

1. [Input] Read `migration/features/<feature-id>/behavior-contract.md`, `migration/features/<feature-id>/target-feature-design.md`, `migration/features/<feature-id>/review.md`, implementation paths, and evidence records.
2. [Input] Resolve every material comparison against the contract's `## Comparison semantics` or an explicitly cited Rulebook rule before running the judge.
3. [Input] Prepare any required PostgreSQL comparison target only through the guarded canonical bootstrap and logical `postgres-test-rw` profile.
4. [Input] Run the judge against the declared legacy/contract and target observations; validate the judge with a controlled mismatch under the mandatory negative-control self-check gate in `docs/03-evidence-and-verification.md`, and record its status and evidence in `docs/templates/verification.md`.
5. [Output] Report comparisons, mismatches, unverified behavior, judge environment, evidence references, and a PASS/FAIL/PARTIAL/BLOCKED verdict in `migration/features/<feature-id>/verification.md`.
6. [Input] Check that no test/helper normalized away a mismatch or changed a declared comparison rule.
7. [Output] Return the complete report body, canonical destination, and any blocking result to `migration-coordinator`.

## Branches

- If a required contract, independent review, implementation, or evidence input is missing, return `BLOCKED`; never fabricate a verdict or report.
- If a required judge input or runtime source is unavailable, return `BLOCKED` when it prevents a meaningful verdict; otherwise return `PARTIAL` with the unverified behavior recorded.
- If optional evidence is unavailable, continue only when the verdict remains truthful as `PARTIAL`.
- If comparisons conflict, preserve the mismatch and return `FAIL`, `PARTIAL`, or `BLOCKED` under the declared semantics; never select the convenient observation.
- If a comparison rule is missing or a material unknown changes the result, stop with `BLOCKED` and route the contract/open-question decision instead of redefining semantics after results are known.
- If the canonical report already exists, update it in place only when authorized; otherwise return the complete replacement body to `migration-coordinator`.
- `BLOCKED`/`PARTIAL` verdicts and the skill result are not the agent common STOP payload; queue/state/lifecycle transitions remain coordinator-owned.

## Done means

The canonical verification report records the predeclared comparison semantics, evidence and environment, controlled judge check, mismatches, unverified behavior, and an honest PASS/FAIL/PARTIAL/BLOCKED verdict. The report is persisted by an authorized role or handed to `migration-coordinator`; no implementation or contract was silently repaired.

## Judge inputs and rules

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
7. Before trusting the parity verdict, execute the mandatory judge self-check as a material negative control: use a safe isolated injection boundary, declare every decision-relevant detector, record the baseline and known-wrong mutation under the declared comparison semantics, prove that every declared detector rejects the mutation without silently normalizing it away, and cover every source or procedure capable of contributing a passing comparison. If a required source or procedure cannot be safely negative-controlled after checking isolated fixture, comparator, or manual-artifact boundaries, mark the self-check `BLOCKED`; there is no waiver. A self-check `FAIL` or `BLOCKED` makes the overall verification `BLOCKED`, regardless of the nominal parity results. Record the self-check status, effective judge configuration and fingerprint, control injection, expected and actual detector results, evidence or reuse reference, and blocker in `docs/templates/verification.md` under the mandatory gate in `docs/03-evidence-and-verification.md`. Reuse a prior self-check only when the effective-configuration fingerprint is identical and the prior self-check evidence is cited. The S-011 synthetic/framework self-test does not authorize changed adapters, source sets, comparison rules, or environments; follow `migration/RULEBOOK.md` Agent workflow #7.
8. report mismatches under the declared semantics rather than normalizing them away;
9. use PASS, FAIL, PARTIAL, or BLOCKED;
10. list unverified behavior and comparison-specification gaps explicitly;
11. if failures repeat across features, recommend a Rulebook/Skill/process change.
