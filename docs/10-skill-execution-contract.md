# Skill Execution Contract Design

Issue: #6 — OpenCode skills have procedures but do not consistently define artifact paths or decision branches.

This document defines the design only. The `.opencode/skills/*/SKILL.md` files and validation tooling are implementation work and are intentionally not changed in this pass.

## Goal

Make every migration skill executable by a low-reasoning model without requiring it to infer:

- which durable artifacts to read;
- where a result belongs;
- what to do when a prerequisite is missing;
- whether partial evidence permits continuation;
- who persists the result and who advances lifecycle state.

The skill contract must reuse the same artifact vocabulary as the agent and command layers instead of creating a third independent path scheme.

## Current repository constraints

This design is based on the current `main`, including the issue #1 artifact contract and the issue #4 agent-procedure implementation.

- `docs/08-feature-artifact-validation.md` defines canonical feature filenames.
- PR #25 / issue #4 gives agents explicit artifact contracts and establishes an important permission pattern: read-only specialist agents return complete report bodies and `migration-coordinator` persists them.
- `docs/templates/legacy-map.md` and `docs/templates/review.md` now exist after issue #4; issue #15's original missing-template observation is therefore partially stale. Remaining template/canonicalization work stays outside issue #6.
- Issue #5 defines the command-side contract in `docs/10-command-execution-contract.md`; skills define their own artifact destinations and branch semantics without taking ownership of command arguments or state transitions.
- Issue #9 has a dedicated design in `docs/09-evidence-grade-transition-control.md`; issue #6 references that stricter grade-transition contract rather than redefining it.
- Issue #10 added provenance rules to several skills, but those edits still do not provide a uniform `Inputs`/`Outputs`/`Branches` execution contract. Issue #6 preserves the provenance rules while normalizing execution structure.
- Issue #7 defines deterministic agent/skill routing in `docs/09-agent-skill-routing.md`; this document is complementary. Routing decides which role/skill owns the next artifact, while this contract defines how that selected skill reads, writes, branches, and hands off persistence.
- Issue #8 defines the designer/implementer permission boundary in `docs/10-agent-role-boundary.md`; this execution contract must not broaden write authority beyond that role boundary.

## Adversarial findings

The issue identifies a real execution gap, but the literal fix of adding paths plus one `if-then` to each skill is insufficient.

1. A cosmetic branch does not define failure semantics. Skills must distinguish missing prerequisites, unavailable optional evidence, contradictory evidence, and blocking unknowns.
2. Copying the full path contract independently into nine skills would create path drift across agent/command/skill layers. The paths must come from one vocabulary.
3. Templates are schemas, not output locations. Reading `docs/templates/behavior-contract.md` does not imply writing the result back into `docs/templates/`.
4. The issue predates the canonical filenames established by issue #1. Skills must use `feature-card.md`, `legacy-map.md`, `behavior-contract.md`, `target-feature-design.md`, `review.md`, and `verification.md`.
5. Skill output ownership and write permission are different concepts. A skill must declare where its result belongs even when the invoking agent is read-only and must hand the body to the coordinator for persistence.
6. Skills must not independently update `migration/STATE.md`, `migration/QUEUE.md`, or lifecycle `stage`; otherwise commands, agents, and skills can race or disagree about phase transitions.
7. DLL-boundary analysis can be feature-local or project-wide. Forcing every skill into a feature path would be wrong.
8. Implementation-time discovery must not rewrite an approved target design in place. A material deviation reopens the design gate instead of being silently recorded as a post-hoc design change.
9. Issue #5 (command execution), #7 (routing), #8 (write permissions), #9 (evidence-grade history), #10 (observed/inferred provenance), and #11 (verification-judge self-check) are stricter or orthogonal controls. Issue #6 must preserve them rather than flattening them into generic branching prose.

## Canonical path vocabulary

For feature-scoped work:

```text
FEATURE_ID   := validated lowercase kebab-case feature id
FEATURE_ROOT := migration/features/<FEATURE_ID>/
```

Canonical feature artifacts inherited from `docs/08-feature-artifact-validation.md` are:

```text
FEATURE_ROOT/feature-card.md
FEATURE_ROOT/legacy-map.md
FEATURE_ROOT/behavior-contract.md
FEATURE_ROOT/target-feature-design.md
FEATURE_ROOT/review.md
FEATURE_ROOT/verification.md
```

Supporting feature evidence may use:

```text
FEATURE_ROOT/db-dependency-report.md
FEATURE_ROOT/dll-boundary-report.md
FEATURE_ROOT/evidence/<evidence-id>.md
```

Project-wide reusable evidence uses:

```text
migration/evidence/<evidence-id>.md
migration/evidence/dll-boundary-report.md
```

Project-wide unresolved facts use:

```text
docs/05-open-questions.md
```

Feature-local unknowns must be reflected in `FEATURE_ROOT/feature-card.md` so the feature remains resumable. A coordinator may also cross-reference the same Open Question ID in `docs/05-open-questions.md`; duplication must be by ID/reference, not by silently diverging copies of the same question.

Templates under `docs/templates/` define document shape only. Completed work is never written into a template path.

## Invocation contract

Before a skill procedure starts, its caller resolves the scope using `docs/09-agent-skill-routing.md` and the applicable command contract.

### Feature-scoped invocation

The caller supplies a valid `FEATURE_ID`. If it is missing, malformed, or ambiguous, return `BLOCKED` and produce no feature artifact.

### Project-scoped invocation

The caller explicitly supplies project scope or a project-level queue item. A project-scoped skill must not invent a feature ID merely to obtain an output directory.

### Existing canonical output

If the canonical output already exists, update that artifact in place only when the current role has write permission under the role-boundary contract. Do not create names such as `target-design-v2.md`, `verification-final.md`, or dated duplicates.

If the invoking role is read-only, return the complete replacement/update body plus the canonical destination to `migration-coordinator`. Lack of edit permission never changes the destination path.

## Required `SKILL.md` structure

Every implemented skill must contain these sections in this order:

1. `## Inputs` — required artifact paths plus required external/runtime inputs.
2. `## Outputs` — canonical destination(s), scope rules, and whether the skill writes directly or returns a body for persistence.
3. `## Procedure` — numbered steps, normally 5–8, with `[Input]` / `[Output]` path annotations on durable artifact reads/writes.
4. `## Branches` — explicit if-then behavior for missing, partial, contradictory, or blocking information.
5. `## Done means` — the completion condition for the skill itself, not the migration phase.

## Common branch semantics

Every skill implements the following behavior where applicable:

- **If a required durable input is missing:** return `BLOCKED`; do not synthesize the missing artifact and do not advance lifecycle state.
- **If required external/runtime evidence is unavailable:** return `BLOCKED` when the next decision depends on it; otherwise return a truthful `PARTIAL` result with the gap recorded.
- **If optional evidence is unavailable:** continue only when the result can remain valid as `PARTIAL`/provisional.
- **If evidence conflicts:** preserve both sides and return `PARTIAL` or `BLOCKED`; never select the convenient source silently.
- **If a material unknown changes a medium/high lock-in decision:** stop that decision and persist the unknown instead of guessing.
- **If the canonical output already exists:** update it in place only when authorized, otherwise return an update body for the coordinator; never create an alternate canonical file.

Skill success does not itself update `migration/STATE.md`, `migration/QUEUE.md`, or feature lifecycle `stage`/`blocked`. The coordinator performs those transitions after evaluating the returned result and applicable gates.

## Skill routing matrix

| Skill | Required durable inputs | Canonical output/destination | Required branch behavior |
| --- | --- | --- | --- |
| `legacy-discovery` | valid `FEATURE_ID`; `FEATURE_ROOT/feature-card.md` when already created; accessible legacy source/runtime scope | `FEATURE_ROOT/legacy-map.md`; may return feature-card/open-question updates to coordinator | If legacy scope or evidence is unavailable, return `BLOCKED`; do not fabricate a dependency map. Preserve issue #10 provenance rules for all material claims. |
| `behavior-contract` | `FEATURE_ROOT/feature-card.md`; `FEATURE_ROOT/legacy-map.md`; relevant evidence | `FEATURE_ROOT/behavior-contract.md`; supporting feature evidence under `FEATURE_ROOT/evidence/` | If material behavior cannot be established, produce `PARTIAL` rather than inventing a requirement. Preserve issue #10 provenance rules independently from confidence grade. |
| `db-migration-analysis` | `FEATURE_ROOT/legacy-map.md`; accessible MSSQL schema/object/query evidence | `FEATURE_ROOT/db-dependency-report.md` | If referenced DB behavior cannot be inspected, mark it unresolved and block any PostgreSQL semantic choice that depends on it. |
| `dll-boundary-analysis` | DLL/host evidence plus either feature scope or explicit project scope | feature: `FEATURE_ROOT/dll-boundary-report.md`; project: `migration/evidence/dll-boundary-report.md` | If lifecycle/threading/callback/ownership facts needed for architecture are unknown, return `PARTIAL/BLOCKED` and do not choose a compatibility architecture. |
| `evidence-grading` | explicit claim; referenced evidence; existing evidence record when present | feature: `FEATURE_ROOT/evidence/<evidence-id>.md`; project: `migration/evidence/<evidence-id>.md` | Follow `docs/09-evidence-grade-transition-control.md`; provenance from issue #10 remains a separate field/dimension from grade. |
| `target-feature-design` | `FEATURE_ROOT/feature-card.md`; `legacy-map.md`; `behavior-contract.md`; applicable DB/DLL reports; Rulebook/open questions | `FEATURE_ROOT/target-feature-design.md` | If an unresolved fact changes a public contract, data model, platform boundary, or other medium/high lock-in choice, return a provisional/`BLOCKED` design. Direct writes must obey issue #8's designer path restrictions. |
| `feature-migration` | approved `FEATURE_ROOT/behavior-contract.md`; approved `FEATURE_ROOT/target-feature-design.md`; no blocking prerequisite; explicit user implementation gate | code/tests only at target paths declared by the approved design; return changed paths/check results/deviations to coordinator | If a precondition is absent or implementation reveals a material design change, stop that part and return `BLOCKED`; do not rewrite the approved design or broaden scope. |
| `parity-verification` | `FEATURE_ROOT/behavior-contract.md`; implementation under test; `FEATURE_ROOT/review.md`; available judge/evidence inputs | `FEATURE_ROOT/verification.md` | If the available judge cannot support the claimed verdict, return `PARTIAL/BLOCKED`, never PASS. Judge self-check mechanics remain governed by #11. |
| `uncertainty-management` | artifact/evidence that exposed the unknown plus resolved scope | feature-local update request for `FEATURE_ROOT/feature-card.md`; project/cross-feature update for `docs/05-open-questions.md` | If the unknown affects multiple features, DLL/host behavior, deployment, or global policy, route it project-wide; otherwise keep it attached to the feature. |

## Responsibility boundaries

### Skill

Defines the reusable procedure, canonical destination, branch semantics, and returned result shape. It may persist the result only when the invoking role has permission.

### Specialist agent

Provides role-specific reasoning. Read-only agents return the complete artifact body plus canonical destination; editable agents may persist only within their allowed paths. Agent paths must remain consistent with this contract.

### Command

Owns operator arguments, prerequisite checks, invocation scope, failure presentation, and the request to advance state according to `docs/10-command-execution-contract.md`. It must not introduce competing artifact names.

### Migration coordinator

Owns persistence for read-only specialist results and owns `migration/STATE.md`, `migration/QUEUE.md`, feature lifecycle metadata, and durable blocker routing after each result.

The issue #4 agent implementation already establishes most of this persistence model. Issue #6 implementation must align skills to it rather than overwrite it.

## Implementation requirements for issue #6

A later implementation pass should update all nine `.opencode/skills/*/SKILL.md` files to conform to this design.

For each skill:

1. add `Inputs`, `Outputs`, `Procedure`, `Branches`, and `Done means`;
2. use the path vocabulary and scope routing in this document;
3. include `[Input]` / `[Output]` markers on numbered durable-artifact steps;
4. keep procedures compact enough for low-reasoning models;
5. include meaningful stop/partial branches rather than cosmetic conditions;
6. state direct-write versus coordinator-persist behavior explicitly;
7. keep lifecycle/state mutation outside the skill;
8. preserve issue #10 provenance semantics, follow `docs/09-evidence-grade-transition-control.md` for grade transitions, and preserve the stricter requirements of #11 for verification;
9. preserve `docs/09-agent-skill-routing.md` ownership/tie-break rules and `docs/10-command-execution-contract.md` command ownership;
10. preserve `docs/10-agent-role-boundary.md` write permissions; execution rules do not grant new edit authority.

A deterministic scaffold check may verify that every `SKILL.md` has the required structural sections. Semantic correctness of a branch remains review work unless a later machine-readable schema is designed.

## Non-goals

Issue #6 does not:

- replace the routing contract in `docs/09-agent-skill-routing.md`;
- replace the command contract in `docs/10-command-execution-contract.md`;
- broaden the role permission boundary in `docs/10-agent-role-boundary.md`;
- implement the grade-transition design in `docs/09-evidence-grade-transition-control.md`;
- redefine the observed/inferred provenance model from issue #10;
- change negative-control/judge requirements from #11;
- redo the agent procedures already implemented for #4 except where a later consistency pass is required;
- finish remaining template/canonicalization work from #15;
- change lifecycle metadata or canonical required files from `docs/08-feature-artifact-validation.md`;
- modify migration application code.

## Acceptance criteria

The design is ready for implementation when:

- every skill has deterministic input and output destinations;
- feature-local versus project-wide scope is explicit;
- read-only execution still has a deterministic persistence handoff;
- missing prerequisites, partial evidence, conflicts, and blocking unknowns have explicit branch semantics;
- implementation-time design changes reopen the gate instead of rewriting approved design post hoc;
- skill completion cannot independently advance queue/state/lifecycle metadata;
- agent, command, and skill layers can share the same path vocabulary;
- routing ownership from issue #7 and write permissions from issue #8 remain intact;
- issue #9, #10, and #11 semantics remain separate and unweakened.
