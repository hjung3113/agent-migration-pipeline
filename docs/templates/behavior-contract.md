# Behavior Contract: <feature>

- Status: draft | ready | blocked
- Legacy source/revision:

> Claim provenance rule
>
> - Record each material legacy claim exactly once.
> - For narrative sections, prefix each claim with `[observed]` or `[inferred]`.
> - `observed` means directly visible/captured in cited evidence; `inferred` means interpretation beyond that evidence.
> - Never combine observation and inference in one bullet or row; split the claims instead.
> - Evidence grade is independent from provenance. A source-visible fact is not automatically grade B.

## Scenario

- [observed]

## Inputs

- [observed]

## Preconditions

- [observed]

## Business rules

| Rule ID | Basis | Rule | Implementation impact | Evidence | Grade |
|---|---|---|---|---|---|
| BR-001 | observed | | yes | | ? |

`Basis` must be `observed` or `inferred`. An inferred rule must cite the supporting evidence/observation. If the inference is materially unsupported, move it to `Unresolved questions` instead of presenting it as a rule.

`Implementation impact` must be literal `yes` or `no`; it controls G2 evidence requirements and must not be inferred from prose during gate evaluation.

## Outputs

- [observed]

## Database side effects

- [observed]

## Files/logs/events/callbacks

- [observed]

## Error/warning behavior

- [observed]

## Ordering/timing requirements

Only include if business-significant. Use `NOT-APPLICABLE — <reason>` when the section does not apply.

- [observed]

## Comparison semantics

Define exact/tolerant/normalized comparisons explicitly. Mark any claim about legacy comparison behavior with its provenance. Use `NOT-APPLICABLE — <reason>` when the section does not apply.

- [observed]

## Known legacy bugs or questionable behavior

- [observed]

## Unresolved questions

| Question / OQ ID | Blocks design? | Status | Evidence / resolution |
|---|---|---|---|
| | yes | OPEN | |

`Blocks design?` must be literal `yes` or `no`. Status should match the linked project OQ when one exists. Unsupported inferred material behavior belongs here rather than being upgraded into a business rule.

## Gate G2 — SPEC_READY

- Result: PENDING | PASS | BLOCKED
- Evaluated at:
- Evaluated by:

| Criterion ID | Result | Evidence reference |
|---|---|---|
| G2.1 | PENDING | |
| G2.2 | PENDING | |
| G2.3 | PENDING | |

The criterion definitions and pass rule are canonical in `docs/02-migration-pipeline.md`. Do not copy or reinterpret them here.
