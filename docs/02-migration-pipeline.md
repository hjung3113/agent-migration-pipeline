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

## Feature artifact gate contract

Each migration feature must persist its lifecycle metadata and canonical artifacts under `migration/features/<feature-id>/` according to `docs/08-feature-artifact-validation.md`.

The lifecycle `stage` and `blocked` state are separate. Required artifacts are cumulative by stage, so a blocked feature retains the obligations of the stage it reached.

`validate_scaffold.py` is the structural guard for this contract. A-1 validates deterministic metadata and artifact existence only; body/heading semantics remain a later validation layer.

## Command entrypoint contract

The seven `.opencode/commands/migration-*.md` files are phase entrypoints, not informal prompts. Their argument grammar, durable inputs/outputs, queue selection, state ownership, preconditions, and failure behavior are defined by `docs/10-command-execution-contract.md`.

Command implementations must not infer a queue row or feature from chat context, must not advance a phase when a required artifact/gate is missing, and must keep feature-local blocking separate from project-level blocking. Canonical artifact paths come from the feature-artifact contract and the merged issue #4 agent contracts rather than being chosen independently inside each command.

Issue #5 command implementation remains gated on design approval and must be reconciled with issue #1 feature metadata, issue #3 phase-gate checklists, issue #14 durable-state semantics, and issue #15's remaining artifact/template filename mismatch.

## Durable state contract

`migration/STATE.md` and `migration/QUEUE.md` are the cross-session durable state interface. Their machine-readable schemas, status enums, legal transitions, source-of-truth precedence, shared transaction generation, ordered multi-file writes, partial-write recovery, and field-level command update semantics are defined by `docs/11-durable-state-protocol.md`.

For durable-state semantics, `docs/11-durable-state-protocol.md` is later and more specific than the provisional queue/project vocabulary retained by the issue #5 command design. Command arguments/inputs/outputs remain owned by `docs/10-command-execution-contract.md`; state transition semantics must be reconciled to the durable-state protocol before command implementation.

Project `BLOCKED` is derived from current-gate queue actionability, not copied from one blocked feature or one selected queue row. A durable-state transaction is not considered consistent unless `STATE.md` and `QUEUE.md` carry the same generation.

## Agent/skill routing contract

The coordinator selects roles by **current phase + required primary artifact**, using `docs/09-agent-skill-routing.md` as the canonical routing design.

| Pipeline work | Primary agent | Primary skill(s) |
| --- | --- | --- |
| legacy application discovery | `legacy-analyzer` | evidence grading / uncertainty only as supporting work |
| MSSQL-resident discovery | `db-analyzer` | evidence grading / uncertainty only as supporting work |
| host/DLL boundary discovery | `dll-boundary-analyzer` | evidence grading / uncertainty only as supporting work |
| behavior specification | coordinator delegates contract work | `behavior-contract` owns the contract; `evidence-grading` and `uncertainty-management` may support it |
| target design | `migration-designer` | target design procedure; unresolved semantics return to coordinator rather than being designed away |
| implementation | `implementer` | implementation procedure only after approved design and explicit user build authorization |
| independent review | `adversarial-reviewer` | review procedure; no self-fix |
| parity verification | `verifier` | `parity-verification` owns the verification report/verdict |

Specialists do not directly absorb adjacent-domain work. They return a routing/escalation packet to `migration-coordinator`. STOP applies only when the current gate cannot safely advance; non-blocking unknowns are persisted while unaffected work may continue.

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

DB-resident semantics and host/DLL contract questions discovered here are routed by the coordinator to `db-analyzer` and `dll-boundary-analyzer`; `legacy-analyzer` records the references but does not silently take over those specialist domains.

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

`behavior-contract` owns this artifact. For each already-defined material claim, `evidence-grading` assigns confidence from actual evidence. When the unanswered question itself must be tracked, `uncertainty-management` records it separately. These supporting skills are composable; they are not alternative names for the same output.

Gate: unresolved semantics that materially affect implementation require human review or remain explicitly provisional.

### Pilot selection

The first migration pilot (QUEUE Q-006) is selected using the weighted rubric in `docs/templates/pilot-selection-rubric.md` (S-006): side-effect observability, DB logic scale, DLL/platform-boundary representativeness, blast radius, existing-test baseline, and business importance. Scores inform the choice; the final selection is a human gate, not an automatic argmax. Material new facts from discovery trigger a re-score — stale scores are not reused.

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

`migration-designer` must return to the coordinator when a material design decision depends on missing behavior evidence or unresolved semantics; architecture preference is not allowed to close the question.

## Phase 4 — Implementation

Implement one approved feature slice only after the user explicitly authorizes implementation under `AGENTS.md` rule 13.

Rules:

- do not silently resolve unknown behavior
- do not broaden scope opportunistically
- document deviations from the design
- add characterization/contract tests when possible
- return to the coordinator when implementation exposes a new design decision instead of resolving it in-place

## Phase 5 — Independent review

At minimum, review for:

- missing business rules
- invented behavior
- legacy technical constraints accidentally copied
- DLL/platform coupling leaking into core logic
- data integrity differences
- error/edge-case changes
- untested behavior presented as complete

The adversarial reviewer reports findings; it does not modify the implementation while acting in the review role.

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

`parity-verification` is used only here, after implementation and independent review. It consumes predefined contract/evidence/comparison semantics and must not redefine them after seeing target results.

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
  |-- implementation defect -> coordinator routes implementer fix
  |-- incomplete spec        -> coordinator routes behavior-contract correction
  |-- repeated pattern       -> fix Rulebook/Skill/process
  |-- unknown legacy fact    -> uncertainty-management / human gate
      |
      v
Re-run independent review and verification
```
