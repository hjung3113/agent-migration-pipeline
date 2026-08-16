# Target Feature Design: synthetic-demo

**SYNTHETIC/DUMMY FEATURE.** Fabricated for the S-011 pipeline dry-run.

## Behavior contract reference

`migration/features/synthetic-demo/behavior-contract.md` (BR-001)

## Scope

A single pure function: concatenate two strings.

## Out of scope

No API endpoint, no persistence, no platform integration — kept to the
minimum needed to exercise app.services and the judge.

## Target flow

```text
app.services.synthetic_demo.concatenate(a, b) -> str
```

No FastAPI route, no repository, no platform adapter involved.

## Frontend responsibilities

None.

## API contract

None — not exposed over HTTP for this dry-run.

## Business/application responsibilities

`app.services.synthetic_demo.concatenate` implements BR-001 exactly:
`return a + b`, no normalization.

## Persistence design

None.

## Platform/DLL compatibility impact

None (RULEBOOK Platform/DLL rules not applicable — no host integration
here).

## Error model

None specified in the behavior contract; no error handling implemented.

## Observability

None.

## Test/verification plan

- `target/backend/tests/test_synthetic_demo.py` — unit tests against the
  characterization-record fixture.
- `migration/judge/tests/test_mutation_self_test.py` — composite judge
  exercised against this scenario, including the mandatory mutation
  self-test (docs/03).

## Legacy structures intentionally not carried forward

N/A — no legacy structure exists.

## Open questions / assumptions

None.
