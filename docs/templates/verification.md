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

## Output/file/log/callback comparison

## Known mismatches

## Unverified behavior

## Required follow-up
