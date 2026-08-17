# Environment Architecture

## Purpose

Provide a small, inspectable OpenCode-native environment for running repeatable migration workflows without introducing unnecessary orchestration infrastructure at the start.

## Layers

```text
OpenCode
  |
  +-- AGENTS.md                 project-wide rules
  +-- .opencode/agents/         role separation
  +-- .opencode/skills/         reusable migration procedures
  +-- .opencode/commands/       operator entry points
  +-- Superpowers               general planning/review workflow support
  |
  +-- docs/                     durable design/context/open questions
  +-- migration/                durable runtime migration state
       +-- RULEBOOK.md
       +-- STATE.md
       +-- QUEUE.md
       +-- features/
       +-- evidence/
```

## Agent responsibilities

Role names alone are not a routing contract. The canonical trigger, exclusion, output-ownership, skill tie-break, and escalation rules are defined in `docs/09-agent-skill-routing.md`.

The architectural invariant is that `migration-coordinator` owns cross-role dispatch and phase/gate transitions. Specialist agents own one bounded artifact/question at a time and return adjacent-domain or blocking work to the coordinator rather than silently expanding scope.

| Agent | Primary responsibility |
| --- | --- |
| `migration-coordinator` | choose/delegate queue work, enforce gates, update durable state |
| `legacy-analyzer` | map legacy application behavior, feature paths, dependencies, and side effects |
| `dll-boundary-analyzer` | analyze external host/DLL contract and platform-dependent behavior |
| `db-analyzer` | analyze MSSQL-resident semantics, integrity rules, and migration risks |
| `migration-designer` | transform an approved behavior contract into target React/FastAPI/PostgreSQL design |
| `implementer` | implement only an approved design after explicit implementation authorization |
| `adversarial-reviewer` | independently identify implementation/spec mismatches without fixing them |
| `verifier` | execute the strongest available parity judge and report evidence-based verdicts |

Unknowns do not automatically mean STOP. They are persisted and escalated; the current gate stops only when proceeding would require invented behavior, violate an approval/design gate, or make verification invalid.

## Skill ownership model

Skills are selected by the artifact they produce, not by overlapping vocabulary:

- `behavior-contract` owns the observable feature contract;
- `evidence-grading` owns confidence grading of an existing claim;
- `uncertainty-management` owns a new unresolved-question record;
- `parity-verification` owns the post-implementation verification report/verdict.

These skills may be composed in that workflow. For example, contract authoring may grade claims and separately register unanswered questions. `docs/09-agent-skill-routing.md` defines the deterministic tie-break algorithm.

## Skill execution contract

Routing decides **which** skill owns the next artifact; execution rules decide **how** that selected skill reads, writes, branches, and hands off persistence. The canonical execution contract is `docs/10-skill-execution-contract.md`.

Skills declare deterministic input/output paths and BLOCKED/PARTIAL branches. Read-only specialist agents return complete artifact bodies to `migration-coordinator`, which persists them at the canonical destination. Skills do not independently advance `migration/STATE.md`, `migration/QUEUE.md`, or feature lifecycle metadata.

## Why OpenCode-native first

OpenCode already provides project-local Agents, Skills, Commands, permissions, and `AGENTS.md`. Starting with these avoids stacking multiple orchestration frameworks that may duplicate context or conflict in agent routing.

Additional tools should be added only after a measured need appears:

- UI Inspector: when the new React UI exists and visual/component feedback becomes valuable
- larger multi-agent orchestrator: when migration queue parallelism becomes a bottleneck
- persistent agent-memory service: when Git-backed documentation is demonstrably insufficient

## State model

Chat history is not a source of truth. Durable state belongs in repository files.

- Policy: `migration/RULEBOOK.md`
- Current phase: `migration/STATE.md`
- Work queue: `migration/QUEUE.md`
- Feature artifacts: `migration/features/<feature>/`
- Evidence: `migration/evidence/` or feature-local evidence
- Project-level unknowns: `docs/05-open-questions.md`
