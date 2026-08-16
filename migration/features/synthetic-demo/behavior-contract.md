# Behavior Contract: synthetic-demo

**SYNTHETIC/DUMMY FEATURE.** All values below are fabricated for the S-011
pipeline dry-run, not observed from any real legacy system.

## Scenario

Combine two text values into one, in the order given.

## Inputs

Two strings, `a` and `b`.

## Preconditions

None.

## Business rules

| Rule ID | Rule | Evidence | Grade |
|---|---|---|---|
| BR-001 | Return `a` immediately followed by `b`, with no separator, normalization, or trimming. | Fabricated for this dry-run — not observed. | ? |

## Outputs

A single string equal to `a + b`.

## Database side effects

None.

## Files/logs/events/callbacks

None.

## Error/warning behavior

None specified — inputs are assumed always valid strings.

## Ordering/timing requirements

Not business-significant.

## Comparison semantics

Exact string equality (RULEBOOK Evidence rule 7 applies to money/identifiers,
not applicable here; this is plain exact comparison, no tolerance/normalization).

## Known legacy bugs or questionable behavior

None — no legacy exists.

## Unresolved questions

None.
