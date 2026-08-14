# Migration Pipeline

## Phase 0 — Environment and feasibility

Goal: make the process runnable before migrating production behavior.

Outputs:

- repository rules and agent definitions
- initial Rulebook
- open-question inventory
- ability to inspect legacy source
- decision on what can act as the verification judge

Gate: do not start broad implementation until the host/DLL boundary and minimum observable outputs are understood well enough to evaluate results.

## Phase 1 — Legacy discovery

For each candidate business area:

- identify user/business purpose
- map legacy entry points
- map WPF/UI involvement
- map services/managers/helpers
- map DB tables/views/procedures/triggers
- map filesystem/log/callback/platform side effects
- identify external dependencies
- identify tests
- identify unreachable/unverifiable behavior

Output: feature inventory + dependency map.

## Phase 2 — Behavior specification

Describe each feature as a contract:

```text
Inputs
  -> Preconditions
  -> Business rules / transformations
  -> Outputs
  -> Persistent side effects
  -> Platform callbacks/events
  -> Error/warning behavior
```

Each important rule receives supporting evidence and a confidence grade.

Gate: unresolved semantics that materially affect implementation require human review or remain explicitly provisional.

## Phase 3 — Target design

Redesign the feature for the target web architecture.

Possible outputs:

- React route/component responsibilities
- FastAPI endpoint/application service contract
- domain/business rule placement
- repository/storage responsibilities
- PostgreSQL schema/query changes
- compatibility DLL/adapter behavior if required
- observability and test points

Gate: reviewer checks that the design preserves business intent without carrying unnecessary WPF/MSSQL structure.

## Phase 4 — Implementation

Implement one approved feature slice.

Rules:

- do not silently resolve unknown behavior
- do not broaden scope opportunistically
- document deviations from the design
- add characterization/contract tests when possible

## Phase 5 — Independent review

At minimum, review for:

- missing business rules
- invented behavior
- legacy technical constraints accidentally copied
- DLL/platform coupling leaking into core logic
- data integrity differences
- error/edge-case changes
- untested behavior presented as complete

## Phase 6 — Verification

Use the strongest available evidence, potentially including:

- existing automated tests
- characterization tests
- legacy/new output comparison
- DB before/after comparison
- file/log comparison
- callback/event comparison
- exception/error comparison
- manually captured evidence

A green test suite alone is not sufficient when coverage is incomplete.

## Phase 7 — Gradual replacement

Exact strategy depends on the host platform contract.

Candidate approaches:

1. Thin legacy-compatible C# DLL delegates to the new FastAPI service.
2. Host platform is changed to call HTTP/API directly.
3. Hybrid: selected features use the new service while unsupported features remain in the DLL.

No option is selected yet.

## Failure loop

```text
Verification failure
      |
      v
Classify cause
  |-- implementation defect -> fix implementation
  |-- incomplete spec        -> fix behavior contract
  |-- repeated pattern       -> fix Rulebook/Skill/process
  |-- unknown legacy fact    -> open question / human gate
      |
      v
Re-run review and verification
```
