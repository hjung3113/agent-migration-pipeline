# Pipeline Dry-Run Report: synthetic-demo (S-011)

Date: 2026-08-17
Purpose: confirm the pipeline is runnable and the composite judge (S-001) is
a trustworthy exit condition, before any real feature migration begins
(docs/02 Phase 0). Uses a fabricated feature — no real legacy source
involved.

## Pipeline stages exercised

| Stage | Artifact | Ran? |
|---|---|---|
| Discover | `feature-card.md` | Yes (fabricated facts, explicitly labeled) |
| Specify | `behavior-contract.md` (BR-001) | Yes |
| Grade evidence | `characterization-record.md` | Yes (grade `?` throughout — honest, nothing to verify against) |
| Design | `target-feature-design.md` | Yes |
| Implement | `target/backend/src/app/services/synthetic_demo.py` + `target/backend/tests/test_synthetic_demo.py` | Yes |
| Adversarial review | N/A for this dry-run (lock-in risk rated low in `migration/SLICES-DRAFT.md`; per the review policy this session followed, Opus review is reserved for regression-risk/hard-to-reverse decisions) | Skipped, by policy |
| Verify | `migration/judge/tests/test_mutation_self_test.py` | Yes — see below |

All template fields were filled in (not skipped) to confirm the templates
from S-002/S-004/S-005/S-006/S-009 are actually fillable end-to-end, not
just structurally valid.

## Mutation self-test (the required exit condition, docs/03)

> "Before trusting a parity harness, deliberately introduce a known wrong
> result and confirm the harness fails. A judge that cannot catch a
> controlled mismatch is not a useful exit condition."

Scenario: `concatenate("foo", "bar")`, legacy-expected output `"foobar"`
(fabricated, `characterization-record.md`).

1. **Baseline** — fed the judge the correct output (`"foobar"`) via fake
   `ContractTestPort`/`OutputSnapshotPort` results, `ExistingTestsPort`
   honestly reported `INSUFFICIENT` (no legacy test suite exists for a
   fabricated feature). Result: `CompositeVerdict.PARTIAL` — not `PASS`,
   because one expected source is not confirming. This is the correct,
   non-misleading grade for this scenario, not a defect.
2. **Mutation** — injected a known-wrong output (`"foobar!"`, appended one
   character) into the same two ports. Result: `CompositeVerdict.FAIL`,
   with reason `"mismatch detected by: contract-tests, output-snapshots"`.
3. **Confirmed both catching ports actually flip** on the mutated input
   (not just one, with the other silently always-passing) — a check against
   a self-test that only *looks* like it's testing the judge.
4. **Confirmed the reproduced target logic** (`a + b`) itself matches the
   captured legacy expectation on the happy path, closing the loop between
   "what the characterization record says" and "what the target code does."

**Result: PASS.** The composite judge catches a controlled mismatch. It is
usable as an exit condition for real feature verification once concrete
adapters exist (blocked on OQ-010, per `migration/judge/README.md`).

Verification commands and results:

```text
$ python3 -m pytest migration/judge/tests/ -q
....                                                                     [100%]
4 passed in 0.01s

$ (cd target/backend && uv run pytest -q)
.............                                                            [100%]
13 passed

$ (cd target/backend && uv run ruff check . && uv run mypy && uv run lint-imports)
All checks passed! / Success: no issues found in 15 source files / Contracts: 4 kept, 0 broken.
```

## Process defects found and fixed

1. **`migration/judge` had no way to run its own tests without manually
   setting `PYTHONPATH`.** It has no `pyproject.toml`/pytest config of its
   own (it's pipeline tooling, not part of `target/backend`'s Python
   project). Fixed minimally: added `migration/judge/tests/conftest.py`
   that inserts the repo root onto `sys.path`. No structural change to
   `composite.py`/`ports.py` (README principle 7: fix the process, not the
   rules).
2. **No other defects found.** The templates (feature-card, behavior-
   contract, characterization-record, target-feature-design) were fillable
   without ambiguity for this scenario. The judge's `expected_sources`
   narrowing (documented in `migration/judge/README.md`) worked as intended
   for a feature with no DB/callback evidence to offer.

No new open questions were generated — the fabricated scenario intentionally
has no real unknowns, so it did not exercise `docs/05-open-questions.md`'s
resolution machinery. That remains untested until a real feature reaches
this stage.

## Scope note

This is a **process** dry-run, not a claim that any real feature has been
migrated. `app.services.synthetic_demo` and its tests are explicitly labeled
SYNTHETIC/DUMMY in code and commit message and carry no business meaning.
