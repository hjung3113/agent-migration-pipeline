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

## Claim provenance: observed vs inferred

Evidence grade and claim provenance are separate dimensions. Every material legacy claim must be recorded exactly once and classified as either `observed` or `inferred`.

- **observed**: a fact directly visible or captured in the cited evidence without adding business meaning. Examples include a source call to a named stored procedure, a schema column, a captured return value, or an observed callback.
- **inferred**: a statement that requires interpretation beyond the direct evidence, including business purpose, intent, causal meaning, or an unobserved behavioral rule derived from source/schema/configuration.

Rules:

1. Do not put an observation and an inference in the same claim. Split them into separate bullets or rows.
2. Record the observation first. Add an inference only when interpretation is required.
3. An inferred claim must cite the observation/evidence it is derived from; unsupported inference becomes an unresolved question, not a fact.
4. Do not duplicate the same statement in both forms. Provenance classifies one claim; it does not create two copies of it.
5. `observed` does **not** mean evidence grade B. Grade B specifically means directly observed runtime behavior under the grading model above. A fact visible in source is observed provenance, but a business-behavior claim derived from source may still be grade C or D.
6. Evidence grade must never be used as a substitute for provenance, and provenance must never be used as a shortcut for evidence grade.

Artifact encoding is fixed as follows:

- `docs/templates/behavior-contract.md`: every material rule carries a `Basis` value of `observed` or `inferred`; narrative claims use `[observed]` / `[inferred]` prefixes.
- `docs/templates/evidence-record.md`: direct facts belong in `Observation`; derived interpretation belongs only in `Inference (optional)`.
- `docs/templates/feature-card.md`: legacy-discovery claims use `[observed]` / `[inferred]` prefixes instead of duplicating sections.

A reviewer must treat an unmarked material claim, a mixed observation/inference claim, or an inference presented as observation as a specification defect.

## Operational skill boundary

Evidence-related skills are intentionally composable but have different primary outputs. The canonical routing rules are in `docs/09-agent-skill-routing.md`.

- `behavior-contract` creates/updates the observable feature contract.
- `evidence-grading` assigns confidence to an existing behavior claim from available evidence.
- `uncertainty-management` creates/updates an unresolved-question record when the answer itself is not known.
- `parity-verification` runs after implementation and independent review to produce the target-vs-contract/legacy verification report and verdict.

When one workflow needs more than one of these outputs, choose the skill that owns the primary artifact and invoke the others only as supporting steps. Do not choose between them from overlapping words such as `behavior`, `evidence`, or `unknown`.

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

### Record schema rules (fixed in `docs/templates/characterization-record.md`, S-002)

Captures are stored against the standard record schema in `docs/templates/characterization-record.md`. Its non-obvious rules are project decisions, not formatting preferences:

- Every `Value:` field holds exactly one of: an actual captured value; `none observed` (captured, nothing happened — a real, assertable fact, used e.g. for happy-path "no error" captures); `not captured (see caveats)` (we didn't look); or `N/A` (item does not apply to this scenario). Blank values are forbidden — "absent" and "not looked at" must not be conflatable.
- The record's `Environment` header must name the legacy build/binary version and the MSSQL schema version, not just an environment label like "dev"/"staging" — otherwise the capture is not reproducible.
- An `Artifact root` header is required so every relative artifact path in the record resolves unambiguously.
- Each capture item carries its own evidence grade (A–D/?) in addition to the record-level rollup, and a `Ref:` that narrows the header's feature-card/behavior-contract reference per item.
- Capture raw values first; normalization and comparison rules live in the behavior contract, never in the record.
- The capture-item names are frozen: renaming an item forces re-conversion of every existing evidence record, because the schema is the shared base for evidence storage, judge composition (`migration/judge/ports.py` consumes these items), and reproduction procedures.

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

### Judge self-check gate — mandatory negative control

A feature verdict and trust in the judge are separate questions. No parity result is valid until the **effective judge configuration used for that verification** has a passing negative control.

The effective configuration includes, at minimum:

- the required evidence-source set for the scenario;
- the concrete adapters or manual procedures that produce those source results;
- the behavior-contract comparison and normalization rules used by those adapters/procedures;
- the fixture/schema/environment versions that affect comparison behavior; and
- the judge/harness implementation revision.

Before trusting that configuration, deliberately inject one or more known-wrong results and prove that the configuration rejects them. The control must be material under the behavior contract; a cosmetic mutation that no business rule should detect is not a valid self-check.

Negative-control rules:

1. **Use a safe isolated injection boundary.** Prefer a fixture, adapter input, comparator input, synthetic response, or staged manual artifact. Do not mutate shared production data or a shared legacy/target environment merely to test the judge.
2. **Declare expected detectors before execution.** For each controlled mismatch, list every decision-relevant source/procedure that is expected to detect it.
3. **Prove the detectors actually reject the mismatch.** Every declared detector must return FAIL or explicitly reject the staged mismatch. A detector that still reports PASS, silently normalizes the mismatch away, or was not actually exercised makes the self-check FAIL.
4. **Guard against a no-op mutation.** Record the baseline and mutated value/state and prove they differ under the contract's comparison semantics.
5. **Cover the decision-relevant judge, not just one convenient port.** One control may cover multiple sources; multiple controls are required when necessary so that every required source/procedure capable of contributing a passing comparison is negatively controlled.
6. **There is no `where practical` waiver.** If a required source/procedure cannot be safely negative-controlled after checking isolated fixture/comparator/manual-artifact boundaries, the self-check is BLOCKED. This is an explicit inability to validate the exit condition, not permission to skip it.

Self-check status is exactly one of:

- **PASS** — the required controls were executed successfully, or a previously executed self-check was validly reused under the reuse rule below;
- **FAIL** — a control ran but the judge accepted a known-wrong result, an expected detector did not reject it, or the mutation was not actually material;
- **BLOCKED** — no safe isolated control can be executed for part of the effective configuration, or required self-check evidence/configuration identity is missing.

If judge self-check status is **FAIL** or **BLOCKED**, the feature's overall verification result is **BLOCKED**, regardless of the nominal parity results. The report may still list observed mismatches or candidate feature failures, but it may not claim PASS, FAIL, or PARTIAL as a trusted parity verdict because the exit condition itself is unvalidated.

A previous self-check may be reused only when the report records an identical effective-configuration fingerprint and cites the prior self-check evidence. Any change to required sources, concrete adapters/manual procedure, comparison/normalization rules, relevant fixture/schema/environment version, or judge implementation invalidates reuse and requires a new control.

The S-011 synthetic self-test (`migration/features/synthetic-demo/`, `migration/judge/tests/test_mutation_self_test.py`) proves only that the current composite-judge skeleton can reject its synthetic controlled mismatch. It does **not** validate future real adapters, feature-specific comparison rules, or different required-source combinations; those configurations still require their own self-check or valid fingerprint-based reuse.

Every verification artifact must use `docs/templates/verification.md` to record self-check status, effective configuration/fingerprint, control injection, expected detectors, actual detector results, evidence/reuse reference, and any blocker. A self-check that cannot be audited from the report is not a passing self-check.

### Verdict combination semantics (fixed in `migration/judge`, S-001)

`CompositeJudge` merges per-source results into one overall grade under fixed precedence (implementation: `migration/judge/composite.py`):

1. empty result set after merging (nothing submitted, nothing expected) → **BLOCKED** — nothing was judged;
2. any source FAIL → **FAIL** — a detected mismatch is decisive negative evidence and outranks sources that could not run;
3. any source NOT_SUBMITTED / NOT_IMPLEMENTED → **BLOCKED**;
4. all sources PASS → **PASS**;
5. otherwise (≥1 PASS + ≥1 INSUFFICIENT, or all INSUFFICIENT) → **PARTIAL** — judging proceeded but evidence is incomplete.

A source declared in `expected_sources` but never submitted is merged as a synthetic NOT_SUBMITTED result (→ BLOCKED), per the section above. The framework lives under `migration/judge/` as pipeline tooling: standard library only, ports without concrete adapters — adapter wiring waits on OQ-010. The mapping from characterization capture items to evidence-source ports is fixed in `migration/judge/ports.py`.

Accepted limitations, deliberately deferred until the first concrete adapter exists (tracked in `migration/judge/README.md` "Known limitations"): no uniform port method across the six ports, `EvidenceResult.source` is adapter-supplied rather than stamped from the producing port, and conflicting duplicate submissions for the same source are unhandled. Resolving these speculatively, before any adapter could be shaped by them, was rejected as inference without evidence.

### Which sources a judgement requires is explicit, not defaulted

A composite judgement must state which of the sources above it actually requires for the scenario at hand (e.g. a feature with no DB side effects does not require a DB assertion). A source that was required and never submitted grades the scenario **BLOCKED**, never a silent PASS — an under-specified judgement is not evidence of a passing feature. This applies whether "which sources are required" is stated per-call or as a framework default; a judge implementation must not let an unstated requirement resolve to PASS. (`migration/judge/CompositeJudge`, S-001.)

## Equality rules

Do not default to byte-for-byte equality for every output. Define comparison semantics per feature, for example:

- exact equality for business identifiers and money values
- tolerance for floating-point analytical results if the legacy implementation already has numeric tolerance
- normalized timestamps/timezones when representation changes but semantics are unchanged
- order-insensitive comparison only when order is not part of the contract

All normalization rules belong in the behavior contract or Rulebook, not hidden in test helpers.

## Human verification

Manual confirmation is acceptable evidence when automation is not currently possible, but it must record:

- who/when (if available)
- what scenario was executed
- what was observed
- screenshots/logs/DB rows if permitted
- remaining uncertainty

Manual evidence is not exempt from the judge self-check gate. Its negative control may use a deliberately mismatched staged artifact or comparison pair; if the manual procedure cannot be safely challenged with a known mismatch, verification remains BLOCKED rather than treating "manual" as a waiver.

Do not convert manual observation into an undocumented permanent assumption.
