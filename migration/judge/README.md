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

1. empty result set after merging (nothing submitted and nothing
   expected) → **BLOCKED** (nothing was judged)
2. any source `FAIL` → **FAIL** (a detected mismatch outranks missing sources)
3. any source `NOT_SUBMITTED` / `NOT_IMPLEMENTED` → **BLOCKED**
4. all sources `PASS` → **PASS**
5. otherwise (some `PASS` + some `INSUFFICIENT`, or all `INSUFFICIENT`) →
   **PARTIAL**

## Which sources a judgement requires is explicit, not defaulted

Fixed by `docs/03-evidence-and-verification.md` § "Which sources a
judgement requires is explicit, not defaulted":

- A composite judgement must state which of the six sources it actually
  requires for the scenario at hand — e.g. a feature with no DB side
  effects does not require a DB assertion. Accordingly,
  `CompositeJudge.expected_sources` is a **required constructor argument
  with no default** (`Sequence[str]` in `composite.py`).
- A source listed in `expected_sources` but never submitted is added by
  `_merge_results` as a synthetic `NOT_SUBMITTED` result, which grades the
  scenario **BLOCKED** — never a silent PASS. An under-specified judgement
  is not evidence of a passing feature.
- Per docs/03, this rule applies whether the required set is stated
  per-call or as a framework default; a judge implementation must not let
  an unstated requirement resolve to PASS. `CompositeJudge` takes the
  per-call form: every call site states its required sources explicitly.

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
- **Conflicting/duplicate submissions for the same source are unhandled.**
  If the same source is submitted twice with different verdicts,
  `_merge_results` does not deduplicate; both entries flow into the grading
  scan. Not exercised by any real caller yet — resolve when a runner that
  can actually produce duplicates exists, not speculatively.

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

## Mutation self-test (docs/03 requirement) — done, S-011

`docs/03` requires: *before trusting a parity harness, deliberately
introduce a known wrong result and confirm the harness fails.*

Performed in **S-011** against a synthetic feature
(`migration/features/synthetic-demo/`,
`migration/judge/tests/test_mutation_self_test.py`): fed the judge a
correct result (PARTIAL — honestly reflecting no legacy test suite for a
fabricated feature), then a deliberately mutated wrong result (FAIL,
caught independently by two sources). **Result: PASS** — the judge catches
a controlled mismatch. Still not wired to any real legacy source (blocked
on OQ-010); the framework itself is confirmed trustworthy, concrete
adapters are not built yet.
