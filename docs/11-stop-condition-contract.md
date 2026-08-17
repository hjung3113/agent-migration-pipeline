# Agent Stop Condition Contract

Issue: #13 — the seven project stop conditions exist only in `AGENTS.md`, while individual agent definitions neither republish them nor define deterministic file-level behavior when a gate must stop.

This document defines the design only. Changes to `AGENTS.md`, `.opencode/agents/*.md`, synchronization scripts, and validators are implementation work and remain gated by `AGENTS.md` rule 13 until the user explicitly authorizes implementation.

## Goal

Make STOP behavior deterministic for low-reasoning agents without creating eight hand-maintained copies of policy or violating the current agent permission/ownership model.

A STOP must answer four questions unambiguously:

1. which canonical condition was encountered;
2. whether the **current gate** is actually blocked;
3. what the specialist returns to `migration-coordinator`;
4. which durable files the coordinator updates before any further routing.

## Adversarial findings

Issue #13 identifies a real failure mode, but the literal recommendation is incompatible with the repository as it exists now.

1. Copying the seven bullets manually into eight agent files solves discoverability once but creates nine policy copies that can drift.
2. The presence of an unknown is not itself a STOP. `AGENTS.md` says to stop when **a decision depends on** the unknown; `docs/09-agent-skill-routing.md` likewise permits non-blocking unknowns to be persisted while unaffected work continues.
3. Five specialist roles are read-only (`edit: deny`) and the other specialists still do not own shared queue/state lifecycle updates. Requiring every agent to edit `docs/05-open-questions.md`, feature metadata, and project state would violate the coordinator-owned persistence model from issue #4/#7.
4. `blocked` is not a lifecycle stage. Issue #1's canonical feature contract keeps `stage` unchanged and uses a separate boolean `blocked`; writing `Status: blocked` or replacing `stage` with `blocked` would destroy lifecycle information.
5. Feature-local blocking and project-level blocking are different. Updating `migration/STATE.md` as globally blocked for every feature-local STOP would misrepresent unrelated runnable work.
6. A STOP should reuse an already-open equivalent question when one exists. Blindly adding a new `OQ-###` on every encounter would create duplicates and inconsistent references.
7. Approval gates, missing artifacts, contradictions, and out-of-role work may also stop a gate, but they are not automatically new unknown facts and therefore must not automatically create open questions.
8. A specialist may have produced safe partial work before discovering a blocker. Discarding that work makes resumability worse; persisting it while preventing gate advancement is safer.

## Canonical stop-condition registry

`AGENTS.md` remains the policy source of truth. The implementation should give the existing seven conditions stable IDs without changing their meaning:

| ID | Canonical condition |
| --- | --- |
| `SC-01` | unknown DLL entry points or lifecycle |
| `SC-02` | unavailable platform behavior |
| `SC-03` | ambiguous business semantics |
| `SC-04` | destructive data migration assumptions |
| `SC-05` | unverified stored procedure / trigger behavior |
| `SC-06` | security/authentication requirements not visible in code |
| `SC-07` | deployment topology not yet known |

The canonical text is owned by `AGENTS.md`; this table defines the stable identifiers used by the stop protocol. Agent-local copies must be generated from the canonical block rather than maintained independently.

## STOP applicability rule

An agent stops the current gate only when all of the following are true:

1. a current decision, artifact, verification result, or phase transition depends on the fact;
2. the fact falls under one of the canonical stop conditions or another explicit policy gate;
3. continuing would require guessing, silently choosing a contract, or presenting unverifiable work as complete.

If the unknown is material but affects only a later gate, the agent records/returns it with `Stop current gate: no`; unaffected work may continue. The later affected gate must not advance until the question is resolved or explicitly accepted as provisional by the applicable policy/human gate.

STOP means **do not advance the affected gate**. It does not mean terminate the whole migration process or discard safe work already completed.

## Specialist stop return contract

All non-coordinator agents return the same structured escalation payload. This specializes the escalation contract in `docs/09-agent-skill-routing.md` rather than replacing it.

```text
Reason: blocking-unknown | missing-evidence | contradiction | approval-gate | out-of-role
Stop condition: SC-01..SC-07 | none
Scope: feature | project
Feature: <feature-id> | none
Queue item: <queue-id> | none
Completed: <safe work completed before STOP>
Evidence: <artifact/source references>
Unresolved: <exact question, missing fact, conflict, or approval>
Impact: <artifact/decision/gate that cannot safely advance>
Recommended next route: <agent/skill/human gate>
Stop current gate: yes | no
Partial artifact: <path/body reference> | none
```

Rules:

- `Stop condition` is required for the seven canonical unknown classes; other escalation reasons use `none` unless a canonical unknown is also involved.
- Specialists never allocate `OQ-###` IDs. The coordinator owns deduplication and ID assignment at persistence time.
- Specialists never change feature lifecycle metadata, queue status, or project state as part of STOP handling.
- Read-only specialists return complete/partial artifact bodies to the coordinator as already required by their artifact contracts.
- `migration-designer` and `implementer` may edit their owned outputs when permitted, but shared blocker/state persistence remains coordinator-owned.

## Coordinator file-action contract

`migration-coordinator` derives durable actions from the stop payload. It must persist the blocker before routing new work or allowing the affected gate to advance.

### Blocking canonical unknown — feature scope

1. Persist any safe partial specialist artifact, clearly retaining its partial/blocking status.
2. Search `docs/05-open-questions.md` for an equivalent unresolved question. Reuse that ID when equivalent; otherwise allocate the next `OQ-###` and add it as `OPEN`.
3. Keep the feature's current `stage` unchanged and set `migration/features/<feature-id>/feature-card.md` `blocked: true`.
4. Set the active feature queue item in `migration/QUEUE.md` to `BLOCKED` and reference the blocking OQ/dependency in its work-item/status text.
5. Update `migration/STATE.md` only when the blocker changes the project-level current phase/status/`Next gate`; a feature-local blocker alone must not falsely block the whole project.
6. Return control to the coordinator routing loop. Independent queue work may continue only if it does not cross the blocked gate.

### Blocking canonical unknown — project scope

1. Persist safe partial project evidence/report output if one exists.
2. Reuse or create the corresponding `OPEN` entry in `docs/05-open-questions.md`.
3. Do not mutate a feature card when no feature owns the blocker.
4. Set the affected project-level queue item to `BLOCKED` with the OQ/dependency reference.
5. Update `migration/STATE.md` `Status`/`Next gate` so a later session can see exactly why the project gate cannot advance.
6. Route only work that is independent of the blocked project gate.

### Non-blocking unknown

1. Reuse or create the open question when it is material and not already tracked.
2. Do not set feature `blocked: true` or the queue item to `BLOCKED` solely because the unknown exists.
3. Record which future artifact/gate depends on the question.
4. Allow the current bounded task to finish, but prevent the affected later gate from advancing without resolution/provisional approval.

### Other STOP reasons

`approval-gate`, `missing-evidence`, `contradiction`, and `out-of-role` use the same coordinator-owned routing/state model, but **do not create a new open question by default**. An OQ is created only when an actual unanswered fact is present. Missing prerequisite artifacts should reference their queue/dependency instead of being disguised as business uncertainty.

## Persistence invariants

The coordinator must preserve these invariants after a STOP:

1. no feature lifecycle `stage` advances because of partial work;
2. feature `blocked` is separate from `stage` and is used only when that feature's current gate is blocked;
3. queue `BLOCKED` reflects the specific affected work item, not the entire repository by implication;
4. project `STATE` is changed only when project-level resumability would otherwise be misleading;
5. every blocking unknown has exactly one referenced open-question identity after deduplication;
6. resolving an OQ does not automatically unblock a feature/queue item until the coordinator re-evaluates the affected gate;
7. no specialist self-routes around a STOP or edits shared state to make progress appear unblocked.

The coordinator should treat the related file writes as one logical persistence batch. If the batch cannot be completed, it must leave the gate conservative (not advanced) and report a state-persistence failure rather than continuing from partially updated lifecycle state.

## Agent-local publication and drift prevention

Low-reasoning agents need the stop conditions in their own prompt context, so local publication is required. Manual duplication is not acceptable as the maintenance mechanism.

Implementation should use a generated managed block:

```text
AGENTS.md canonical Stop conditions
        |
        v
scripts/sync_agent_stop_conditions.py
        |
        +-- --write -> refresh managed `## Stop conditions` block in all 8 agent files
        +-- --check -> fail if any agent block is missing or differs
```

Design requirements:

- `AGENTS.md` receives machine-stable begin/end markers around the canonical stop-condition block and stable `SC-01..SC-07` IDs.
- every `.opencode/agents/*.md` contains a generated `## Stop conditions` block with the same canonical conditions;
- generated text is not customized per agent;
- role-specific behavior belongs in a separate `## Stop handling` section so the canonical policy remains byte/normalized-text comparable;
- all eight current agent files are enumerated by the sync/check logic rather than relying on a hard-coded subset that can silently omit a new role;
- `scripts/validate_scaffold.py` (or a helper it calls) fails when an agent lacks the managed block, the block drifts from `AGENTS.md`, or required stop-handling structure is absent;
- the existing CI scaffold validation then becomes the enforcement point; no runtime include feature is assumed.

A canonical policy edit therefore fails validation until all local agent blocks are regenerated in the same change.

## Role-specific implementation behavior

After explicit implementation authorization:

- **all eight agents**: add generated `## Stop conditions` plus a `## Stop handling` section that references the common stop payload;
- **read-only specialists** (`legacy-analyzer`, `db-analyzer`, `dll-boundary-analyzer`, `adversarial-reviewer`, `verifier`): return blocker payload + safe artifact body only; never attempt shared-state edits;
- **migration-designer / implementer**: stop owned work at the affected boundary and return the same blocker payload; do not rewrite approved contracts or shared state to bypass it;
- **migration-coordinator**: implement deduplication, OQ allocation, feature/queue/project scope classification, conservative lifecycle updates, and re-evaluation before unblocking;
- **validator/sync tooling**: enforce local publication and canonical-text synchronization.

## Interaction with existing designs

- `docs/08-feature-artifact-validation.md` remains authoritative for `stage` + `blocked` feature metadata.
- `docs/09-agent-skill-routing.md` remains authoritative for routing and escalation ownership; this document defines the STOP-specific trigger and durable persistence semantics.
- `docs/10-command-execution-contract.md` remains authoritative for command-level state mutation; commands must not invent a competing STOP state model.
- `docs/05-open-questions.md` remains the canonical project-level unknown registry.
- `migration/QUEUE.md` and `migration/STATE.md` remain the resumable work/project state sources of truth.

## Acceptance criteria for later implementation

Issue #13 implementation is complete when:

- all eight agent definitions receive the canonical seven stop conditions in their local context;
- those copies are generated/checked from `AGENTS.md` rather than hand-maintained;
- every specialist emits the same deterministic STOP/escalation payload;
- read-only agents never need edit permission to satisfy STOP behavior;
- coordinator handling deterministically updates/reuses open questions, feature `blocked`, queue status, and project state according to scope;
- lifecycle `stage` is never replaced by a synthetic `blocked` stage;
- feature-local blockers do not automatically mark the whole project blocked;
- duplicate OQs are not created for the same unresolved fact;
- non-blocking unknowns may be tracked without stopping unrelated work;
- CI detects missing/drifted agent stop-condition blocks.

## Non-goals

This design does not implement the sync script, change agent Markdown, modify `AGENTS.md`, or extend the validator. It also does not redefine evidence grades, queue status vocabulary, feature lifecycle stages, command argument grammar, or the routing ownership model.