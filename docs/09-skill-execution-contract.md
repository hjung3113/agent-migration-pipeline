# Skill Execution Contract Design

Issue: #6 — OpenCode skills have procedures but do not consistently define artifact paths or decision branches.

This document defines the design only. The `.opencode/skills/*/SKILL.md` files, agents, commands, templates, and validators are implementation work and are intentionally not changed in this pass.

## Goal

Make every migration skill executable by a low-reasoning model without requiring it to infer:

- which durable artifacts to read;
- where a result must be persisted;
- what to do when a prerequisite is missing;
- whether it may continue with partial evidence;
- who owns lifecycle/state transitions.

The contract must remain consistent across skill, agent, and command layers instead of duplicating competing path conventions.

## Adversarial findings

The issue identifies a real execution gap, but its literal recommendation is insufficient on its own.

1. Adding one arbitrary `if-then` to each skill does not define failure semantics. Branches must distinguish missing prerequisites, unavailable evidence, contradictory evidence, and blocking unknowns.
2. Repeating full path rules independently in every skill would create nine copies of the same contract and make issues #4 and #5 easier to implement inconsistently.
3. Templates are schemas, not output locations. `docs/templates/behavior-contract.md` does not tell an agent where the feature-specific contract belongs.
4. The current repository already has a canonical feature artifact contract from `docs/08-feature-artifact-validation.md`: `feature-card.md`, `legacy-map.md`, `behavior-contract.md`, `target-feature-design.md`, `review.md`, and `verification.md`. Issue #6 must consume that contract rather than invent another naming scheme.
5. Issue #15 is partially stale after the issue #1 design: canonical feature filenames are now defined, but some supporting templates are still absent. Skill routing must not depend on those templates already existing.
6. A skill should not independently mutate `migration/STATE.md`, `migration/QUEUE.md`, or lifecycle `stage`. Otherwise commands, coordinator agents, and skills can race or disagree about phase transitions. The caller owns orchestration state; the skill owns its domain artifact.
7. Some skills are feature-scoped while DLL-boundary analysis is primarily project-scoped. A single hard-coded feature path for all skills would be incorrect.
8. Issue #9 (evidence grade history) and issue #11 (verification judge self-check) are higher-severity semantic controls. This design must not silently absorb or weaken those separate requirements.

## Canonical path vocabulary

For a feature-scoped invocation:

```text
FEATURE_ID := validated lowercase kebab-case feature id
FEATURE_ROOT := migration/features/<FEATURE_ID>/
```

Canonical feature artifacts are inherited from `docs/08-feature-artifact-validation.md`:

```text
FEATURE_ROOT/feature-card.md
FEATURE_ROOT/legacy-map.md
FEATURE_ROOT/behavior-contract.md
FEATURE_ROOT/target-feature-design.md
FEATURE_ROOT/review.md
FEATURE_ROOT/verification.md
```

Supporting feature evidence may be stored under:

```text
FEATURE_ROOT/evidence/<evidence-id>.md
FEATURE_ROOT/db-dependency-report.md
```

Project-wide reusable evidence belongs under:

```text
migration/evidence/
```

Project-wide unresolved facts belong in:

```text
docs/05-open-questions.md
```

Feature-local unresolved facts belong in `FEATURE_ROOT/feature-card.md`, consistent with the logical-artifact mapping in `docs/08-feature-artifact-validation.md`.

Templates under `docs/templates/` define document shape only. A skill must never write completed work back into a template file.

## Invocation contract

Before any skill procedure starts, its caller must resolve the invocation scope.

### Feature-scoped skills

The caller must provide a valid `FEATURE_ID`. If the feature ID is missing, malformed, or ambiguous, the skill returns `BLOCKED` to the caller and writes no feature artifact.

### Project-scoped skills

The caller must explicitly identify project scope. Project-scoped skills do not invent a feature ID merely to obtain an output directory.

### Existing outputs

If the canonical output already exists, the skill updates it in place. It must not create alternate names such as `target-design-v2.md`, `verification-final.md`, or dated duplicates unless a separate evidence record is intentionally required.

## Common execution rules

Every implemented `SKILL.md` must contain these sections in this order:

1. `## Inputs` — required artifact paths and external/runtime inputs.
2. `## Outputs` — canonical primary output path plus permitted secondary writes.
3. `## Procedure` — numbered execution steps, normally 5–8 steps.
4. `## Branches` — explicit if-then behavior for missing, partial, contradictory, or blocking information.
5. `## Done means` — observable completion condition for the skill only.

The common branch policy is:

- **If a required durable input is missing:** return `BLOCKED`; do not synthesize the missing artifact and do not advance lifecycle state.
- **If optional evidence is unavailable:** continue only when the output can truthfully be `PARTIAL` or provisional; record the gap in the owning feature artifact or project open-question file.
- **If evidence conflicts:** preserve the conflict and return `PARTIAL` or `BLOCKED` as appropriate; never choose the convenient source silently.
- **If a material unknown changes the correctness of the next irreversible decision:** stop that decision and persist the unknown rather than guessing.
- **If an output already exists:** update it in place and preserve still-valid evidence/unknowns.

Skills do not update `migration/STATE.md`, `migration/QUEUE.md`, or `feature-card.md` lifecycle `stage` solely because their procedure finished. The command/coordinator layer performs those transitions after checking the skill result.

## Skill routing matrix

| Skill | Required durable inputs | Primary output | Permitted secondary writes | Required branch behavior |
| --- | --- | --- | --- | --- |
| `legacy-discovery` | valid `FEATURE_ID`; accessible legacy source/runtime inputs | `FEATURE_ROOT/legacy-map.md` and create/update `FEATURE_ROOT/feature-card.md` | feature-local unknowns in `feature-card.md`; cross-feature/platform unknowns in `docs/05-open-questions.md` | If legacy source/runtime evidence is unavailable, return `BLOCKED`; do not fabricate a map. |
| `behavior-contract` | `FEATURE_ROOT/feature-card.md`; `FEATURE_ROOT/legacy-map.md` | `FEATURE_ROOT/behavior-contract.md` | evidence records; feature-local/project unknowns | If a material behavior cannot be established, write a PARTIAL contract and keep the rule unresolved instead of inventing a requirement. |
| `db-migration-analysis` | `FEATURE_ROOT/legacy-map.md`; accessible MSSQL schema/object/query evidence | `FEATURE_ROOT/db-dependency-report.md` | evidence records; feature-local/project unknowns | If DB behavior is referenced but the DB object or runtime semantics cannot be inspected, mark that dependency unresolved and block any PostgreSQL semantic decision that depends on it. |
| `dll-boundary-analysis` | project scope; accessible DLL/host metadata or runtime evidence | `migration/evidence/dll-boundary-report.md` | `docs/05-open-questions.md` | If host entry points/lifecycle cannot be observed, record the unknown and do not select a compatibility architecture. |
| `evidence-grading` | explicit claim plus its referenced evidence; existing record when one exists | feature scope: `FEATURE_ROOT/evidence/<evidence-id>.md`; project scope: `migration/evidence/<evidence-id>.md` | update the owning contract/report with the evidence-record reference when appropriate | If evidence does not support a higher certainty, keep or lower the grade; grade-history mechanics remain governed by #9. |
| `target-feature-design` | `FEATURE_ROOT/behavior-contract.md`; relevant `legacy-map.md` and supporting DB/DLL evidence | `FEATURE_ROOT/target-feature-design.md` | feature-local/project unknowns | If a P0/material unknown changes the design choice, mark that part provisional or `BLOCKED`; do not choose a convenient assumption. |
| `feature-migration` | approved `FEATURE_ROOT/behavior-contract.md`; approved `FEATURE_ROOT/target-feature-design.md`; no unresolved blocking precondition | repository implementation/tests for the bounded feature slice | record design deviations in the existing target-design artifact and new evidence/unknown records | If any required precondition is absent or blocking, return `BLOCKED` before modifying implementation files. |
| `parity-verification` | `FEATURE_ROOT/behavior-contract.md`; implementation under test; `FEATURE_ROOT/review.md`; available judge/evidence inputs | `FEATURE_ROOT/verification.md` | evidence records; unresolved verification gaps | If the available judge cannot support the claimed verdict, return `PARTIAL`/`BLOCKED`, never PASS. Judge self-check requirements remain governed by #11. |
| `uncertainty-management` | the artifact/evidence that exposed the unknown plus invocation scope | feature-local: update `FEATURE_ROOT/feature-card.md`; project/cross-feature: update `docs/05-open-questions.md` | add references from affected contract/design/report | If the unknown affects multiple features, the DLL boundary, deployment, or a global policy, route it to `docs/05-open-questions.md`; otherwise keep the canonical question in the feature card. |

## Responsibility boundaries

### Skill

Owns reusable domain procedure and its canonical artifact writes.

### Agent

Owns role-specific reasoning and delegation. Agents must consume this routing contract rather than redefine different output paths.

### Command

Owns operator arguments, precondition checks, invocation scope, lifecycle transition requests, and user-facing failure handling.

### Coordinator

Owns `migration/STATE.md`, `migration/QUEUE.md`, and feature lifecycle transition decisions after successful skill completion.

This separation is the dependency contract for issues #4 and #5: their implementations must reference the same paths rather than establish new ones.

## Implementation requirements for issue #6

A later implementation pass should update all nine `.opencode/skills/*/SKILL.md` files to conform to this design.

For each skill implementation:

1. add explicit `Inputs`, `Outputs`, `Procedure`, `Branches`, and `Done means` sections;
2. use the canonical paths in this document;
3. keep procedures compact enough for low-reasoning models;
4. include at least one meaningful failure/uncertainty branch, not a cosmetic if-then statement;
5. never make a skill responsible for queue/state transitions;
6. preserve the stricter semantics of issues #9 and #11 for their dedicated implementation passes.

Implementation should also add a deterministic scaffold check that every `SKILL.md` contains the required structural sections. Semantic validation of whether a branch is correct remains review work unless a later schema is defined.

## Non-goals

This issue does not:

- implement evidence grade history or anti-upgrade mechanics from #9;
- change verification negative-control/judge rules from #11;
- fully implement agent procedures from #4;
- fully implement command arguments/state-update rules from #5;
- create missing supporting templates from #15;
- change feature lifecycle metadata or required canonical files from `docs/08-feature-artifact-validation.md`;
- implement or modify migration application code.

## Acceptance criteria

The design is ready for implementation when:

- every skill has one unambiguous primary output location;
- feature-local versus project-wide scope has deterministic routing;
- missing prerequisites have explicit stop behavior;
- partial/unknown/contradictory evidence cannot be silently converted into certainty;
- skill completion cannot independently advance queue/state/lifecycle metadata;
- issues #4 and #5 can reuse the same path vocabulary without defining competing filenames;
- issue #9 and #11 semantics remain explicitly separate and unweakened.
