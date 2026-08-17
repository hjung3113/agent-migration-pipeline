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

### migration-coordinator

Primary orchestration role. Chooses the next phase, delegates work, enforces gates, and updates durable state. It must not erase uncertainty to keep work moving.

### legacy-analyzer

Reads C#/WPF/configuration code and maps business features, entry points, dependencies, side effects, DB usage, and external calls. Read-only by default.

### dll-boundary-analyzer

Specializes in the host/DLL integration contract: public API, lifecycle, callbacks, threading, configuration, platform dependencies, and testability outside the host.

### db-analyzer

Maps MSSQL schema, procedures, functions, triggers, constraints, query behavior, data semantics, and PostgreSQL migration risks.

### migration-designer

Transforms approved behavior contracts into target feature designs for React/FastAPI/PostgreSQL without mechanically preserving WPF/C# structure.

### implementer

Implements only an approved target design and records deviations instead of silently changing the contract.

### adversarial-reviewer

Reviews diffs/specs independently with the assumption that important behavior may have been lost or accidentally invented.

### verifier

Runs available automated checks and compares evidence. It must distinguish verified, inferred, and unverified outcomes.

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

## Execution-contract ownership

Artifact routing for reusable skills is defined centrally in `docs/09-skill-execution-contract.md`.

Skills own domain artifact reads/writes; agents own role-specific reasoning; commands own invocation arguments and precondition handling; the migration coordinator owns `STATE.md`, `QUEUE.md`, and feature lifecycle transitions. Agent/command/skill files must consume the same routing vocabulary instead of redefining independent output paths.
