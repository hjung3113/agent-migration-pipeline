# Verification Report: <feature>

- Date:
- Result: PASS | FAIL | PARTIAL | BLOCKED
- Judge self-check: PASS | FAIL | BLOCKED

> `Result` must be `BLOCKED` unless `Judge self-check` is `PASS`.

## Judge self-check

- Effective judge configuration:
- Configuration fingerprint:
- Self-check mode: executed | reused
- Reused self-check evidence ref: N/A | <artifact/ref>
- Safety/isolation note:
- Blocker: None | <reason>

| Control ID | Material rule/source | Injection boundary | Baseline | Known-wrong mutation | Expected detector(s) | Actual detector result(s) | Outcome |
|---|---|---|---|---|---|---|---|
| JC-001 | | | | | | | PASS / FAIL / BLOCKED |

Record enough detail to prove the mutation was material under the behavior contract, was not a no-op after normalization, and was rejected by every declared detector. Reuse is valid only when the effective-configuration fingerprint is identical to the cited prior self-check.

## Comparison semantics audit

Every material comparison must trace to the feature behavior contract's `## Comparison semantics` row/subject or to an explicit Rulebook rule cited there. Test/helper-only normalization, tolerance, ordering, or equality logic is a specification gap and makes the affected verification `BLOCKED`.

## Evidence used

| Item | Comparison rule ref | Legacy result | New result | Match | Grade |
|---|---|---|---|---|---|
| | | | | | |

## Existing tests

## Characterization/contract tests

## DB comparison

Use `docs/issue-22-db-snapshot-diff-contract.md` when `db-assertions` is decision-relevant. Record one row per logical comparison subject; do not replace required DB evidence with an unscoped whole-database dump or a manual eyeball comparison.

- DB comparison plan: N/A | `migration/features/<feature-id>/db-comparison-plan.json`
- Raw runtime artifact root/reference: N/A | <approved local/secure reference>

| Subject ID | Mode | Comparison rule ref | Legacy capture/delta ref | Target capture/delta ref | Structural change summary | Semantic result | Grade / caveat |
|---|---|---|---|---|---|---|---|
| db-001 | delta / state | | | | | PASS / FAIL / BLOCKED | |

For a side-effect subject, compare legacy and target **deltas** (`before -> after`) by default. Absolute state comparison requires an explicit contract and logically equivalent starting fixtures. If a required subject cannot be captured safely, is truncated/ambiguous, is paired from incompatible runs, or lacks executable declared comparison semantics, record the blocker and keep verification `BLOCKED` rather than omitting the DB source.

Raw production-derived row values, credentials, and connection strings must not be pasted into this Git-tracked report. Persist digests/counts/sanitized summaries or an approved secure-artifact reference; include values only when they are explicitly approved as sanitized/non-sensitive.

## Output/file/log/callback comparison

## Known mismatches

## Unverified behavior

## Required follow-up
