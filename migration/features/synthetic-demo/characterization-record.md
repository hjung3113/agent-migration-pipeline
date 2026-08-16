<!-- This schema is the shared base for evidence storage, judge composition, and reproduction procedures. Renaming any field below forces re-conversion of existing evidence records. -->

# Characterization: synthetic-demo-001

**SYNTHETIC/DUMMY FEATURE.** Fabricated capture, not a real legacy
observation, for the S-011 pipeline dry-run.

- Feature card: `migration/features/synthetic-demo/feature-card.md`
- Behavior contract ref: BR-001
- Harness/boundary: fabricated (no real harness — see DRY-RUN-REPORT.md)
- Capture date: fabricated, 2026-08-17
- Environment: n/a (no legacy build/binary or MSSQL schema exists)
- Harness invocation: n/a
- Artifact root: `migration/features/synthetic-demo/`
- Record grade rollup: ?

Each section below is one capture item defined in docs/03-evidence-and-verification.md; keep the item names unchanged. Each item's `Ref:` narrows the header's `Feature card`/`Behavior contract ref` when set, and defaults to them when blank. Capture raw values first; normalization and comparison rules live in the behavior contract.

For every `Value:` field, use exactly one of: an actual captured value; `none observed` (captured, nothing happened — a real, assertable fact); `not captured (see caveats)` (we didn't look); or `N/A` (item does not apply to this scenario). Do not leave `Value:` blank.

## exact input fixture

- Format: inline input table
- Value: `a="foo"`, `b="bar"`
- Grade: ?
- Ref: BR-001

## initial DB state or relevant records

- Format: N/A
- Value: N/A
- Grade: N/A
- Ref: BR-001

## return/output value

- Format: JSON literal
- Value: `"foobar"`
- Grade: ?
- Ref: BR-001

## resulting DB state

- Format: N/A
- Value: N/A
- Grade: N/A
- Ref: BR-001

## files generated/modified

- Format: N/A
- Value: none observed
- Grade: N/A
- Ref: BR-001

## logs/events

- Format: N/A
- Value: none observed
- Grade: N/A
- Ref: BR-001

## callbacks to platform

- Format: N/A
- Value: none observed
- Grade: N/A
- Ref: BR-001

## exception/error code

- Format: N/A
- Value: none observed
- Grade: N/A
- Ref: BR-001

## timing/order only when business-significant

- Format: N/A
- Value: N/A (not business-significant)
- Grade: N/A
- Ref: BR-001

## Capture caveats

Entirely fabricated for the S-011 pipeline dry-run — not an observation of
any real system. Evidence grade is `?` (unknown/not verifiable) throughout
because there is nothing to verify against.
