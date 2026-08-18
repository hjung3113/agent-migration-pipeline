# Verification Report: synthetic-demo

**SYNTHETIC/DUMMY FEATURE.** This report consolidates the verification
already performed and recorded in `DRY-RUN-REPORT.md` during the S-011
pipeline dry-run (2026-08-17). No new verification was run for this file.

- Date: 2026-08-17 (dry-run; consolidated during Issue #1 normalization)
- Result: PASS (process dry-run scope only — see "Unverified behavior")
- Judge self-check: PASS

> `Result` must be `BLOCKED` unless `Judge self-check` is `PASS`. Judge
> self-check is `PASS`, so this constraint is satisfied.

## Judge self-check

- Effective judge configuration: composite judge
  (`migration/judge/composite.py`) with expected sources narrowed to
  contract-tests and output-snapshots — the feature offers no DB/callback
  evidence (`migration/judge/README.md`)
- Configuration fingerprint: not recorded at dry-run time; see residual
  uncertainty below
- Self-check mode: executed
- Reused self-check evidence ref: N/A
- Safety/isolation note: no real legacy system involved; inputs were
  fabricated fixture values via fake `ContractTestPort`/`OutputSnapshotPort`
- Blocker: None (for the dry-run's purpose; real-feature use remains blocked
  on OQ-010 per `DRY-RUN-REPORT.md`)

| Control ID | Material rule/source | Injection boundary | Baseline | Known-wrong mutation | Expected detector(s) | Actual detector result(s) | Outcome |
|---|---|---|---|---|---|---|---|
| JC-001 | BR-001 `concatenate("foo","bar") == "foobar"` (`behavior-contract.md`, `characterization-record.md` fixture) | fake ContractTestPort/OutputSnapshotPort result injection | correct output `"foobar"` -> `CompositeVerdict.PARTIAL` (correct: `SOURCE_EXISTING_TESTS` honestly INSUFFICIENT) | output `"foobar!"` (one appended character) | contract-tests, output-snapshots | `CompositeVerdict.FAIL`, reason `"mismatch detected by: contract-tests, output-snapshots"` — both declared detectors flipped | PASS |

Both catching ports were confirmed to flip on the mutated input (not just
one silently always-passing), and the reproduced target logic (`a + b`)
matches the captured expectation on the happy path
(`DRY-RUN-REPORT.md` mutation self-test, items 3-4).

## Comparison semantics audit

The behavior contract specifies exact string equality with no tolerance or
normalization (`behavior-contract.md` "Comparison semantics"). The judge's
comparison is plain exact equality; no test/helper-only normalization or
tolerance logic was introduced.

## Evidence used

| Item | Comparison rule ref | Legacy result | New result | Match | Grade |
|---|---|---|---|---|---|
| `concatenate("foo","bar")` | `behavior-contract.md` Comparison semantics (exact string equality) | `"foobar"` (fabricated fixture, `characterization-record.md`) | `"foobar"` (via judge ports, happy-path check) | Yes | ? |

Grade `?` is deliberate: there is no real legacy system, so nothing was
observed; the "legacy" expectation is a fabricated fixture.

## Existing tests

None exist — the fabricated feature has no legacy test suite. The judge
reported `SOURCE_EXISTING_TESTS` = INSUFFICIENT, which correctly held the
baseline verdict to PARTIAL rather than PASS (`DRY-RUN-REPORT.md`).

## Characterization/contract tests

`target/backend/tests/test_synthetic_demo.py` — unit tests against the
characterization-record fixture. `migration/judge/tests/test_mutation_self_test.py`
— composite judge exercised on this scenario including the mandatory
mutation self-test (docs/03).

## DB comparison

N/A — the scenario has no database side effects
(`behavior-contract.md`, `target-feature-design.md`); `db-assertions` is
not decision-relevant and no db-comparison-plan exists.

## Output/file/log/callback comparison

Return value only; compared via the output-snapshots port in the judge
self-test above. No files, logs, or callbacks exist in scope.

## Known mismatches

None. Mutation run failed as designed (that is the self-test passing, not a
defect).

## Unverified behavior

- Everything, in the legacy-parity sense: there is no real legacy system to
  verify against. The PASS above applies to the **process** claim — "the
  pipeline is runnable and the composite judge catches controlled
  mismatches" — not to any migrated business behavior
  (`DRY-RUN-REPORT.md` scope note).
- Real-feature use of the judge remains blocked on OQ-010 (concrete
  adapters), per `migration/judge/README.md` / `DRY-RUN-REPORT.md`.
- The judge configuration fingerprint was not captured at dry-run time, so
  this self-check is not reusable via fingerprint match by a later report.

## Required follow-up

- None for this synthetic feature. For real features: capture the effective
  judge configuration fingerprint at self-check time, and do not skip the
  adversarial review stage.
