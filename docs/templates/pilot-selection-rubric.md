# Pilot Feature Selection Rubric

Template version: 2026-08-16
Status: criteria only — no candidate feature has been scored yet.

## Purpose

Select the first pilot feature for migration. Grounded in:

- docs/07-research-notes.md §Anthropic large-scale migration process — "use a pilot before broad conversion"; the pilot must establish an exit condition/judge before broad conversion.
- ADR-0003 — migration unit is one business feature / vertical slice, so the pilot must exercise a complete slice, not a horizontal layer.
- docs/02-migration-pipeline.md — Phase 1 (discovery) feeds Phase 2 (behavior specification); the pilot should produce artifacts that validate this flow end to end.

A good pilot proves the pipeline (discovery -> contract -> design -> implement -> review -> verify) and surfaces process gaps cheaply. It is not necessarily the most important feature.

## How to use

1. One copy of the scoring sheet per candidate feature.
2. Score each criterion 1–5 using the anchors below. Every score of 1 or 5 requires a one-line evidence note citing the feature card / dependency map.
3. Compute the weighted total.
4. Record the top candidate and runner-up; final selection is a human gate, not an automatic argmax. Scores inform, they do not decide.
5. Re-score if discovery (Phase 1) reveals material new facts. Do not reuse stale scores.

Weights below are defaults for the pilot selection; they may be tuned before first use, but each change must be recorded here with a reason.

## Criteria

### C1. Side-effect observability (can we judge the result?)

The pilot's whole job is to validate the verification judge (Phase 6). Prefer features whose outputs are directly observable and comparable.

- Weight: 0.25
- Scores:
  - 5 — deterministic, exportable outputs (files, DB rows, logs, callback payloads) that can be diffed legacy vs. target
  - 3 — outputs observable but partially manual capture required, or timing/ordering varies
  - 1 — outputs mostly UI-rendered or human-judged, no machine-comparable artifact
- How to estimate: from the feature card §Observable outputs / side effects, count distinct output channels that support before/after comparison (DB, file, log, callback/event, exception).

### C2. DB logic scale (representative but bounded)

MSSQL -> PostgreSQL is a core risk axis. The pilot should contain real DB-resident logic but not the largest schema in the system.

- Weight: 0.20
- Scores:
  - 5 — 3–10 DB objects (tables/views/procedures/triggers) including at least one non-trivial procedure or trigger; schema subset is isolatable
  - 3 — few DB objects, or many objects that are hard to isolate from other features
  - 1 — trivial persistence (single-table CRUD) or entangled with a schema region owned by many features
- How to estimate: count objects in feature card §Database dependencies; check isolation by whether other features reference the same objects.

### C3. DLL/platform boundary representativeness

The host contract is not yet verified (docs/05-open-questions.md). The pilot should exercise the boundary pattern that later features will repeat, without requiring the unknown parts to be solved first.

- Weight: 0.15
- Scores:
  - 5 — touches the DLL entry/callback pattern typical of the system, but can also run/verify standalone if host behavior stays unknown
  - 3 — touches the boundary only in a degenerate way, or hard-depends on unverified host lifecycle
  - 1 — no boundary contact (proves nothing about integration) OR fully gated on unverified host behavior (pilot would stall)
- How to estimate: from feature card §Platform/DLL dependencies, note whether a fallback verification path exists if host contract remains `?`.

### C4. Blast radius on failure

Pilot failures are expected; that is how the Rulebook improves. Keep damage recoverable.

- Weight: 0.15
- Scores:
  - 5 — failure affects only this feature; no destructive writes; rollback is data-preserving
  - 3 — shared tables/services touched, but with reversible operations
  - 1 — destructive data migration, or blocking a shared resource other features need
- How to estimate: list shared DB objects and platform entry points from the dependency map; flag any irreversible operation (delete, in-place transform).

### C5. Existing tests / verifiable baseline

Phase 6 evidence quality depends on what can be compared. Tests are one input; captured behavior is another.

- Weight: 0.10
- Scores:
  - 5 — automated legacy tests exist AND runtime behavior is capturable for characterization
  - 3 — no automated tests, but behavior is directly exercisable and capturable manually
  - 1 — behavior cannot be exercised without the unverified host environment
- How to estimate: feature card §Existing tests plus feasibility of running the legacy feature in isolation.

### C6. Business importance

Deliberately lowest weight: a highly visible feature creates pressure to skip gates, but a completely irrelevant one wastes stakeholder attention.

- Weight: 0.15
- Scores:
  - 5 — real business value, moderate visibility: stakeholders care about the outcome but accept pilot status
  - 3 — peripheral value, or very high visibility with deadline pressure
  - 1 — no genuine user of the result, or visibility so high that gate-skipping pressure is likely
- How to estimate: owner/domain input from the feature card; note stakeholder expectations.

## Scoring sheet (per candidate)

```text
Feature ID:
Feature name:
Scored by:
Date:
Discovery artifacts used: feature card | dependency map | other:

| Criterion | Weight | Score (1–5) | Evidence note |
|-----------|--------|-------------|---------------|
| C1 Side-effect observability | 0.25 |             |               |
| C2 DB logic scale          | 0.20 |             |               |
| C3 DLL boundary represent. | 0.15 |             |               |
| C4 Blast radius            | 0.15 |             |               |
| C5 Existing tests/baseline | 0.10 |             |               |
| C6 Business importance     | 0.15 |             |               |
| Weighted total             | 1.00  |             |               |
```

## Decision record (fill at selection time, not before)

- Candidates scored:
- Selected pilot:
- Runner-up:
- Rationale beyond the score (human gate notes):
- Re-score triggers (facts that would invalidate this selection):
