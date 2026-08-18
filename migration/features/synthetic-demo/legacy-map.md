# Legacy Map — synthetic-demo

**SYNTHETIC/DUMMY FEATURE.** No legacy system exists. This map records the
fabricated scenario used for the S-011 pipeline dry-run; every "observed"
fact below is invented, not observed, and is graded `?` accordingly
(`feature-card.md`, `DRY-RUN-REPORT.md`).

## Scope

- Feature: synthetic-demo (fabricated string concatenation utility)
- Legacy entry points: none exist. Assumed shape only: a synchronous
  function call combining two text values; no UI, no DB, no callbacks
  (`feature-card.md` "Legacy entry points").
- Source roots inspected: none — there is no legacy source to inspect.

## Observed behavior

| Behavior / rule | Evidence location | Grade | Fact or inference |
|---|---|---|---|
| BR-001: return `a` immediately followed by `b`, no separator, normalization, or trimming | `behavior-contract.md` | ? | Fabricated for the dry-run — not observed from any legacy system |

## Execution paths and dependencies

- WPF/UI: NOT-OBSERVED — no UI in the fabricated scenario.
- Services/managers/helpers: assumed shape is a single synchronous function
  call; no real service exists (fabricated).
- Database calls: NOT-OBSERVED — none by design of the synthetic scenario
  (`feature-card.md`).
- Filesystem/logging: NOT-OBSERVED — return value only.
- Platform/DLL callbacks: NOT-OBSERVED — none by design of the synthetic
  scenario (`feature-card.md`).
- External dependencies: NOT-OBSERVED.

## Legacy structure observations — not target requirements

No legacy codebase exists, so no LSR category was observed. NOT-OBSERVED for
all of LSR-01..LSR-07, with the inspected scope being "nothing — fabricated
feature, no legacy source".

| LSR ID | Concrete legacy structure observed | Evidence location | Requirement appears tied to this shape? | Follow-up |
|---|---|---|---|---|
| LSR-01..LSR-07 | NOT-OBSERVED (no legacy exists) | `feature-card.md` "Legacy code/components" | no | None |

## Existing tests and observability

- Tests: none — the fabricated feature has no legacy test suite. This
  absence was intentional: the dry-run exercised the judge's handling of
  `SOURCE_EXISTING_TESTS` = INSUFFICIENT (`feature-card.md`, `DRY-RUN-REPORT.md`).
- Observable outputs: return value only.
- Unreachable/unexercised paths: n/a — no legacy runtime exists.

## Specialist follow-up

- DB analysis: not required (no database dependencies exist).
- DLL analysis: not required (no platform/DLL dependencies exist).

## Open questions

- None — synthetic feature; no legacy unknowns apply (`feature-card.md`).
