# Composite Judge Framework (skeleton)

Migration slice **S-001**. Implements the judge structure fixed by
`docs/03-evidence-and-verification.md` § "Judge design under incomplete
tests": six evidence sources combined into one overall grade.

## Purpose

The legacy test suite is incomplete and the application runs inside another
platform, so no single source can be the oracle. This package is the
**framework skeleton** for a composite judge that merges:

```
existing tests + contract tests + DB assertions
+ output snapshots + callback assertions + selected manual evidence
-> PASS | FAIL | PARTIAL | BLOCKED
```

Scope boundaries:

- **Ports only, no adapters.** `ports.py` defines one abstract port per
  evidence source; `composite.py` defines `CompositeJudge` and the grade
  combination rules. There is no code that touches the legacy system,
  MSSQL, files, or the host platform.
- **Real legacy judge integration is deferred until OQ-010 is confirmed**
  (which outputs are observable without the full UI — see
  `docs/05-open-questions.md`). Until then this skeleton only fixes the
  interfaces and combination semantics, because every later feature
  verification depends on them (high replacement cost).
- This is **pipeline tooling under `migration/`**, not part of the target
  FastAPI app (which will be scaffolded separately in S-007).
- Standard library only; Python type hints throughout.

## Layout

| File | Contents |
|---|---|
| `ports.py` | `EvidenceResult`, `SourceVerdict`, and six abstract ports: `ExistingTestsPort`, `ContractTestPort`, `DbAssertionPort`, `OutputSnapshotPort`, `CallbackAssertionPort`, `ManualEvidencePort` |
| `composite.py` | `CompositeJudge`, `CompositeVerdict`, `CompositeReport` |

Both modules' docstrings document how the eight characterization capture
items in `docs/templates/characterization-record.md` map onto the ports.

## Grade combination rules

Evaluated in order by `CompositeJudge.judge()`:

0. the same source reports two **different** verdicts (conflicting
   duplicate submission) → **BLOCKED** — we cannot tell which is
   authoritative, even if one of them was FAIL. Identical duplicates (e.g.
   a retry) collapse silently and do not trigger this.
1. any source `FAIL` → **FAIL** (a detected mismatch outranks missing sources)
2. any source `NOT_SUBMITTED` / `NOT_IMPLEMENTED` → **BLOCKED**
3. no source `PASS` (empty, or every source `INSUFFICIENT`) → **BLOCKED** —
   zero confirming evidence is the same epistemic state as no evidence at
   all, so it is not reported as PARTIAL.
4. all sources `PASS` → **PASS**
5. otherwise (some `PASS` + some `INSUFFICIENT`) → **PARTIAL**

`expected_sources` **defaults to all six canonical sources**, not to an
empty tuple — an under-configured judge must not be able to silently PASS
on a single submitted result. Narrow it explicitly per scenario (e.g. drop
`SOURCE_MANUAL_EVIDENCE` when no manual evidence is expected). Declared but
missing sources are added as synthetic `NOT_SUBMITTED` results.

`CompositeReport.coverage_complete` is `False` whenever any source was
blocking or conflicting — read it alongside `verdict`, since a FAIL with
`coverage_complete=False` is still a genuine FAIL but was reached without
every expected source weighing in.

## Known limitations (tracked, not yet fixed)

- **No uniform port method.** Each of the six ports uses a distinct
  abstract method name (`run_contract_tests`, `assert_db_state`, ...), so a
  future runner cannot iterate ports polymorphically without hardcoding all
  six call sites. Consider a shared `collect() -> EvidenceResult` entry
  point (e.g. via a `Protocol`) when the first concrete adapter is written.
- **`EvidenceResult.source` is adapter-supplied, not validated against the
  port that produced it.** A buggy adapter could stamp the wrong
  `SOURCE_*` name and silently satisfy `expected_sources` for a source that
  never actually ran. A future runner should stamp `source` from the
  port's own `source_name`, not trust the adapter's payload.

## Extending with new ports / adapters

Adding a concrete adapter (after OQ-010 confirms the source is observable):

1. Subclass the relevant port from `ports.py` and implement its one
   abstract method, returning a single `EvidenceResult`.
2. The adapter only **collects evidence and compares** — comparison
   semantics (exact / tolerance / normalized, per `docs/03` "Equality
   rules") belong to the behavior contract, never to the adapter or the
   composite judge.
3. Give the result a `SOURCE_*` name, a `SourceVerdict`, a `detail` trace,
   and optionally an evidence grade (`A|B|C|D|?`) plus
   `linked_capture_items` referencing the characterization record.
4. Feed results into `CompositeJudge(expected_sources=[...]).judge(results)`
   and persist the returned `CompositeReport` (Rulebook rule 12).

Adding a **new evidence source kind** (rare): define a new `SOURCE_*`
constant and an `EvidencePort` subclass in `ports.py` with one abstract
method, then rely on `CompositeJudge` unchanged — combination rules are
source-agnostic.

## Mutation self-test (docs/03 requirement) — planned for S-011

`docs/03` requires: *before trusting a parity harness, deliberately
introduce a known wrong result and confirm the harness fails.*

How this skeleton will be self-tested in **S-011** (pipeline dry-run with a
synthetic feature — not yet performed):

1. Build a fake adapter per port that returns canned `EvidenceResult`s for
   a toy scenario.
2. **Mutation pass:** flip at least one result to a known-wrong value
   (e.g. a DB assertion comparing against a mutated `resulting DB state`
   capture, a callback assertion with a swapped call order) and confirm
   `CompositeJudge` grades the scenario **FAIL** for every port, and that
   missing expected sources grade **BLOCKED** rather than silently
   passing.
3. A judge that cannot catch the controlled mismatch is not a useful exit
   condition; any such finding becomes a Rulebook/skill fix
   (README principle 7: fix the process).

Until the S-011 mutation self-test passes, treat this judge as **unproven
scaffolding** — no feature may claim verification credit from it.
