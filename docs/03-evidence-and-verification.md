# Evidence and Verification Strategy

## Problem

The legacy test suite is incomplete and the application executes inside another platform, so neither test coverage nor direct UI observation can be treated as a complete oracle.

## Verification model

Use a hierarchy of evidence rather than a single source of truth.

| Grade | Meaning | Typical evidence |
|---|---|---|
| A | Strongly confirmed | automated test + observed behavior, or multiple independent strong sources |
| B | Directly observed | captured runtime output / DB change / callback / exception |
| C | Reasonable inference | source + schema/SP/config analysis, not directly observed |
| D | Weak inference | source-only interpretation or ambiguous dead/conditional path |
| ? | Unknown | cannot currently verify |

Grades communicate certainty, not correctness of the legacy behavior.

## Characterization strategy

When possible, create a harness around an observable public boundary and capture:

- exact input fixture
- initial DB state or relevant records
- return/output value
- resulting DB state
- files generated/modified
- logs/events
- callbacks to platform
- exception/error code
- timing/order only when business-significant

A characterization test states **what the legacy system currently does**, not what it ought to do.

## Judge design under incomplete tests

A verification judge may be composite:

```text
existing tests
+ contract tests
+ DB assertions
+ output snapshots
+ callback assertions
+ selected manual evidence
```

Before trusting a parity harness, deliberately introduce a known wrong result and confirm the harness fails. A judge that cannot catch a controlled mismatch is not a useful exit condition.

## Equality rules

Do not default to byte-for-byte equality for every output. Define comparison semantics per feature, for example:

- exact equality for business identifiers and money values
- tolerance for floating-point analytical results if the legacy implementation already has numeric tolerance
- normalized timestamps/timezones when representation changes but semantics do not
- order-insensitive comparison only when order is not part of the contract

All normalization rules belong in the behavior contract or Rulebook, not hidden in test helpers.

## Human verification

Manual confirmation is acceptable evidence when automation is not currently possible, but it must record:

- who/when (if available)
- what scenario was executed
- what was observed
- screenshots/logs/DB rows if permitted
- remaining uncertainty

Do not convert manual observation into an undocumented permanent assumption.
