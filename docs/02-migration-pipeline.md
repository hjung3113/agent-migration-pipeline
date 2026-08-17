# Migration Pipeline

This document is the canonical definition of migration phases and phase-gate criteria. Commands and agents must reference gate IDs from this file instead of inventing or copying alternative criteria.

## Gate evaluation protocol

A phase gate has one of three results: `PENDING`, `PASS`, or `BLOCKED`.

A criterion is `PASS` only when all of the following are true:

1. the referenced artifact exists;
2. the referenced field/section is populated with a non-placeholder value;
3. the criterion's required evidence/source reference is present;
4. any required status value is one of the explicitly allowed values below.

`unknown`, `not checked`, a blank field, a placeholder, or missing evidence is a failed criterion. There is no partial gate pass and an agent must not waive a failed criterion.

Gate criteria live only in this document. Feature artifacts store criterion IDs, results, and evidence references; they do not redefine the criteria.

When any criterion fails, first classify the cause and then apply the STOP/persistence contract in `docs/11-stop-condition-contract.md`:

1. record the gate as `BLOCKED` and stop the phase-advancing command; do not delegate work from the next phase;
2. if the failure is an actual unresolved fact, reuse an existing matching item in `docs/05-open-questions.md` or add a new one only when the unknown is not already tracked;
3. if the failure is a missing artifact/prerequisite, reference the missing dependency/queue work instead of inventing an open question unless an unanswered fact actually exists;
4. if the failure is an approval gate such as G3.5, persist the approval state/source in the referenced artifact and do not create an open question merely because authorization has not yet been given;
5. for feature-level G2/G3 failures, set that feature's `feature-card.md` `blocked: true` without changing its lifecycle `stage`, and set the affected feature/queue work item to `BLOCKED` with the failed criterion/dependency reference;
6. update `migration/STATE.md` to project-level `BLOCKED` only when the failed gate blocks the project-level phase/next gate or no actionable work remains at the current gate; a single feature-local failure must not automatically mark the whole project blocked.

Human input resolves source facts or supplies approvals; it does not bypass a false criterion. If approval arrives in chat, persist that approval in the referenced artifact before re-evaluating the gate.

## Phase 0 — Environment and feasibility

Goal: make the process runnable and establish the minimum legacy boundary needed for evidence-based discovery.

Outputs:

- repository rules and agent definitions;
- initial Rulebook and open-question inventory;
- access to the legacy source needed for boundary inspection;
- `migration/evidence/dll-boundary-report.md`, created from `docs/templates/dll-boundary-report.md`;
- `migration/evidence/observable-output-survey.md`, created from `docs/templates/observable-output-survey.md`;
- a decision on the minimum observable evidence that can feed the verification judge.

Before G0 passes, only gate-enabling inspection is allowed. Do not start broad feature discovery.

### Gate G0 — FOUNDATION_READY (Phase 0 -> Phase 1)

| ID | Boolean criterion |
|---|---|
| G0.1 | `migration/evidence/dll-boundary-report.md` has `Status: analyzed` or `verified`, and section `2. Public types / methods / interfaces` contains at least one host-callable entry point with a non-empty evidence/source link. |
| G0.2 | `migration/evidence/observable-output-survey.md` contains at least one output row with `Observable without full UI? = yes` and `Usable for parity? = yes`, a non-`?` evidence grade, a non-empty evidence/source reference, and that output ID is listed under `Minimum viable judge`. |
| G0.3 | In `docs/05-open-questions.md`, both `OQ-001` and `OQ-010` are `CONFIRMED` or `NOT-APPLICABLE`; neither may remain `OPEN` or `DEFERRED`. |

Pass rule: `G0.1 && G0.2 && G0.3`.

## Feature artifact gate contract

Each feature uses the canonical directory and lifecycle metadata defined in `docs/08-feature-artifact-validation.md` and `migration/features/README.md`.

Phase-gate status and feature lifecycle status are complementary:

- `feature-card.md` `stage` records the furthest lifecycle stage reached;
- `feature-card.md` `blocked` records whether the feature is currently stopped;
- a failed G2 or G3 gate sets `blocked: true` without replacing or rolling back `stage`;
- passing a gate does not by itself advance `stage`; the command advances stage only after the next phase artifact has been persisted.

The structural validator from issue #1 checks metadata and required-file existence. It does not prove the semantic G2/G3 criteria in this document.

## Command entrypoint contract

The seven `.opencode/commands/migration-*.md` files are phase entrypoints, not informal prompts. Their argument grammar, durable inputs/outputs, queue selection, state ownership, preconditions, and failure behavior are defined by `docs/10-command-execution-contract.md`.

Command implementations must not infer a queue row or feature from chat context, must not advance a phase when a required artifact/gate is missing, and must keep feature-local blocking separate from project-level blocking. Canonical artifact paths come from the feature-artifact contract and the merged issue #4 agent contracts rather than being chosen independently inside each command.

Issue #5 command implementation remains gated on design approval and must be reconciled with issue #1 feature metadata, issue #3 phase-gate checklists, and issue #15's remaining artifact/template filename mismatch.

## Agent/skill routing contract

The coordinator selects roles by **current phase + required primary artifact**, using `docs/09-agent-skill-routing.md` as the canonical routing design.

| Pipeline work | Primary agent | Primary skill(s) |
|---|---|---|
| legacy application discovery | `legacy-analyzer` | evidence grading / uncertainty only as supporting work |
| MSSQL-resident discovery | `db-analyzer` | evidence grading / uncertainty only as supporting work |
| host/DLL boundary discovery | `dll-boundary-analyzer` | evidence grading / uncertainty only as supporting work |
| behavior specification | coordinator delegates contract work | `behavior-contract` owns the contract; `evidence-grading` and `uncertainty-management` may support it |
| target design | `migration-designer` | target design procedure; unresolved semantics return to coordinator rather than being designed away |
| implementation | `implementer` | implementation procedure only after approved design and explicit user build authorization |
| independent review | `adversarial-reviewer` | review procedure; no self-fix |
| parity verification | `verifier` | `parity-verification` owns the verification report/verdict |

Specialists do not directly absorb adjacent-domain work. They return a routing/escalation packet to `migration-coordinator`. STOP applies only when the current gate cannot safely advance; non-blocking unknowns are persisted while unaffected work may continue.

The seven canonical unknown classes remain policy in `AGENTS.md`. `docs/11-stop-condition-contract.md` defines their local publication into agent context, the common specialist STOP payload, and the coordinator-owned file-level persistence actions. Gate criterion definitions remain authoritative in this document; STOP handling must not copy or redefine them.

## Phase 1 — Legacy discovery

For each candidate business area:

- identify user/business purpose;
- map legacy entry points;
- map WPF/UI involvement;
- map services/managers/helpers;
- map DB tables/views/procedures/triggers;
- map filesystem/log/callback/platform side effects;
- identify external dependencies and tests;
- identify unreachable or unverifiable behavior.

Outputs per feature:

- `migration/features/<feature>/feature-card.md`;
- `migration/features/<feature>/legacy-map.md`;
- evidence records and linked open questions.

DB-resident semantics and host/DLL contract questions discovered here are routed by the coordinator to `db-analyzer` and `dll-boundary-analyzer`; `legacy-analyzer` records the references but does not silently take over those specialist domains.

There is no separate human gate here. `migration-spec` may start only from persisted Phase 1 artifacts; missing discovery evidence is a precondition failure, not an inferred fact.

## Phase 2 — Behavior specification

Describe each feature as a behavior contract in `migration/features/<feature>/behavior-contract.md`, using `docs/templates/behavior-contract.md`.

`behavior-contract` owns this artifact. For each already-defined material claim, `evidence-grading` assigns confidence from actual evidence. When the unanswered question itself must be tracked, `uncertainty-management` records it separately. These supporting skills are composable; they are not alternative names for the same output.

The contract separates observed legacy behavior from target design and records evidence grades for business rules.

### Gate G2 — SPEC_READY (Phase 2 -> Phase 3)

| ID | Boolean criterion |
|---|---|
| G2.1 | `behavior-contract.md` has non-placeholder content in `Inputs`, `Preconditions`, `Business rules`, `Outputs`, and `Error/warning behavior`; sections that do not apply explicitly contain `NOT-APPLICABLE` with a reason. |
| G2.2 | Every business-rule row with `Implementation impact = yes` has a non-empty evidence reference and an evidence grade of `A`, `B`, or `C`; grades `D` and `?` fail the criterion. |
| G2.3 | `behavior-contract.md` `Unresolved questions` contains no row with `Blocks design? = yes` and `Status = OPEN`; project-wide OQ IDs referenced by such rows must also not be `OPEN` in `docs/05-open-questions.md`. |

Pass rule: `G2.1 && G2.2 && G2.3`.

If a business semantic is unknown and affects implementation, represent that mechanically as `Implementation impact = yes`, grade `?`, or `Blocks design? = yes`; do not use prose such as "material enough" as a gate decision.

Evidence grades are current evidence state, not workflow progress. A gate must never promote a grade merely to unblock itself; grade changes remain subject to the evidence-grade lifecycle defined by `docs/09-evidence-grade-transition-control.md` once that design is implemented.

### Pilot selection

The first migration pilot (QUEUE Q-006) is selected using `docs/templates/pilot-selection-rubric.md` (S-006). Scores inform the choice; the final selection remains a human decision. Any new discovery fact that changes one or more rubric inputs requires a re-score before the decision is recorded.

## Phase 3 — Target design

Redesign the feature for React, FastAPI, PostgreSQL, and the platform boundary in `migration/features/<feature>/target-feature-design.md`, using `docs/templates/target-feature-design.md`.

The target design may change legacy technical structure, but must preserve the approved behavior contract.

`migration-designer` must return to the coordinator when a material design decision depends on missing behavior evidence or unresolved semantics; architecture preference is not allowed to close the question.

### Gate G3 — DESIGN_READY (Phase 3 -> Phase 4)

| ID | Boolean criterion |
|---|---|
| G3.1 | `target-feature-design.md` references a `behavior-contract.md` whose `Gate G2 — SPEC_READY` result is `PASS`. |
| G3.2 | `Frontend responsibilities`, `API contract`, `Business/application responsibilities`, `Persistence design`, `Platform/DLL compatibility impact`, `Error model`, `Observability`, `Test/verification plan`, and `Legacy structures intentionally not carried forward` are populated; non-applicable sections explicitly say `NOT-APPLICABLE` with a reason. |
| G3.3 | `target-feature-design.md` `Open questions / assumptions` contains no row with `Blocks implementation? = yes` and `Status = OPEN`. |
| G3.4 | `target-feature-design.md` `Behavior preservation map` contains one row for every behavior-contract rule with `Implementation impact = yes`, and `Design review` has `Reviewer role: migration-coordinator`, `Result: PASS`, and non-empty evidence references for the behavior map and rejected legacy structures. |
| G3.5 | `target-feature-design.md` `Implementation authorization` has `Status: APPROVED` and a durable source reference to the user's explicit instruction to start implementation. |

Pass rule: `G3.1 && G3.2 && G3.3 && G3.4 && G3.5`.

`migration-design` must finish the design and stop if G3.5 is not yet satisfied. `migration-implement` may persist a newly received user authorization, re-evaluate G3, and proceed only after the complete gate is `PASS`.

The coordinator-owned G3.4 review is a pre-implementation design consistency check. It does not replace the independent post-implementation `adversarial-reviewer` required in Phase 5.

## Phase 4 — Implementation

Implement one approved feature slice only after the user explicitly authorizes implementation under `AGENTS.md` rule 13.

Rules:

- do not silently resolve unknown behavior;
- do not broaden scope opportunistically;
- document deviations from the design;
- add characterization/contract tests when possible;
- return to the coordinator when implementation exposes a new design decision instead of resolving it in-place;
- do not let the implementer also act as the independent reviewer or verifier.

## Phase 5 — Independent review

At minimum, review for:

- missing business rules;
- invented behavior;
- legacy technical constraints accidentally copied;
- DLL/platform coupling leaking into core logic;
- data-integrity differences;
- error/edge-case changes;
- untested behavior presented as complete.

The adversarial reviewer reports findings; it does not modify the implementation while acting in the review role.

## Phase 6 — Verification

Use the strongest available evidence, potentially including:

- existing automated tests;
- characterization tests;
- legacy/new output comparison;
- DB before/after comparison;
- file/log comparison;
- callback/event comparison;
- exception/error comparison;
- manually captured evidence.

`parity-verification` is used only here, after implementation and independent review. It consumes predefined contract/evidence/comparison semantics and must not redefine them after seeing target results.

A green test suite alone is not sufficient when coverage is incomplete.

## Phase 7 — Gradual replacement

Exact strategy depends on the confirmed host-platform contract.

Candidate approaches:

1. a thin legacy-compatible C# DLL delegates to the new FastAPI service;
2. the host platform calls HTTP/API directly;
3. selected features use the new service while unsupported features remain in the DLL.

No option is selected until its required host facts are confirmed.

## Failure loop

```text
Verification or gate failure
      |
      v
Classify cause
  |-- implementation defect -> coordinator routes implementer fix
  |-- incomplete spec        -> coordinator routes behavior-contract correction
  |-- design defect          -> coordinator routes target-design correction
  |-- repeated pattern       -> fix Rulebook/Skill/process
  |-- unknown legacy fact    -> uncertainty-management / human gate + BLOCKED gate
      |
      v
Re-run the applicable gate, independent review, and verification
```
