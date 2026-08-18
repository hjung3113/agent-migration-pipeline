---
id: synthetic-demo
stage: done
blocked: false
---

# Feature: synthetic-demo

**SYNTHETIC/DUMMY FEATURE.** Not a real legacy feature. Fabricated for
migration slice S-011 to exercise the full discover -> spec -> design ->
implement -> review -> verify pipeline and the migration/judge composite
judge before any real feature migration begins. All "legacy" facts below
are invented, not observed.

- ID: synthetic-demo
- Owner/domain: pipeline tooling (no real business owner)
- Status: done (dry-run only, not a real migration)
- Priority: n/a

## Business purpose

None — fabricated. Stand-in business purpose: "combine two text values
into one," modeled as if it were a trivial legacy string-concatenation
utility.

## Legacy entry points

None — fabricated. Assumed shape: a synchronous function call, no UI, no
DB, no callbacks.

## Legacy code/components

None exist. Not evidence-graded because there is no legacy source.

## Database dependencies

None (by design of the synthetic scenario).

## Platform/DLL dependencies

None (by design of the synthetic scenario).

## Observable outputs / side effects

Return value only.

## Existing tests

None (fabricated feature has no legacy test suite) — this absence is itself
part of the dry-run: it exercises the judge's handling of
`SOURCE_EXISTING_TESTS` = INSUFFICIENT rather than a fabricated PASS.

## Behavior contract

Link: `migration/features/synthetic-demo/behavior-contract.md`

## Target design

Link: `migration/features/synthetic-demo/target-feature-design.md`

## Open questions

None — synthetic feature, no legacy unknowns apply.

## Verification status

See `migration/features/synthetic-demo/DRY-RUN-REPORT.md`.
