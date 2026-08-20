# Agent Migration Pipeline Rules

## Mission

Build and operate a repeatable migration pipeline for converting a legacy C# WPF + MSSQL application into a web system using TypeScript/React/Tailwind, Python/FastAPI, and PostgreSQL while preserving business behavior and data integrity.

The legacy component is currently invoked by an external company platform as a DLL. The exact DLL contract and host lifecycle are not yet known.

## Non-negotiable rules

1. Do not treat legacy source structure as target architecture.
2. Migrate by business feature / vertical slice, not file-by-file translation.
3. Do not claim behavior is confirmed without evidence.
4. Record unknowns in `docs/05-open-questions.md` or the relevant feature artifact.
5. Separate observed behavior from inferred intent.
6. Attach an evidence grade to important business rules.
7. Keep platform/DLL-specific concerns behind an explicit adapter boundary.
8. Do not assume a C# compatibility DLL is required or unnecessary until the host contract is verified.
9. Do not mark a feature complete only because it compiles or tests pass.
10. Reviewer and verifier agents must be independent from the implementer role.
11. When the same defect pattern repeats, update the rule/process before applying repetitive local fixes.
12. Persist queue, decisions, evidence, and unresolved items on disk so another session can resume without relying on chat history.
13. **Design gate: no implementation until the user explicitly says design is done and to start building.** For any slice with lock-in risk medium or higher, produce the design artifact first (ADR / RULEBOOK amendment / behavior contract) and stop — do not dispatch implementation in the same pass, and do not let an implementer resolve an undecided design point on the spot. Wait for an explicit go-ahead from the user before writing code against it.

## Engineering execution principles

Apply these together with the migration rules above. The Karpathy-inspired principles are adapted from `duolahypercho/andrej-karpathy-skills` and are intentionally phrased for this repository.

### YAGNI (You Aren't Gonna Need It)

Implement only what is required by the current verified migration scope.

- Do not add speculative features, extension points, configuration, compatibility layers, or abstractions for hypothetical future needs.
- Do not preserve a legacy structure merely because it might become useful later.
- Add complexity only when a current behavior contract, integration constraint, or verified requirement justifies it.
- Prefer deleting an unnecessary design idea over carrying it forward as dormant flexibility.

### 1. Think before coding

Make the task and its evidence explicit before changing code.

- Surface assumptions that could change behavior or architecture.
- Identify meaningful tradeoffs when more than one approach is valid.
- Do not silently resolve ambiguous business semantics, DLL behavior, data behavior, or security requirements.
- When ambiguity is material, record it as an open question and follow the repository stop conditions and design gate.

### 2. Simplicity first

Choose the smallest design and implementation that satisfies the verified requirement.

- Prefer direct code over architecture introduced for a single use case.
- Do not add dependencies when the repository can express the required behavior simply without them.
- Do not introduce configurability or generalization without an active requirement.
- If a solution is becoming framework-like, check whether a narrower solution meets the same contract.

### 3. Surgical changes

Keep every change tied to the requested migration scope.

- Touch only files needed for the task.
- Do not mix unrelated refactors, formatting sweeps, renames, or cleanup into the change.
- Preserve local conventions unless the task explicitly changes them.
- Remove imports, variables, helpers, or artifacts made obsolete by the change itself.
- Report unrelated defects separately instead of expanding the patch opportunistically.

### 4. Goal-driven verification

Define the observable success condition before declaring work complete.

- Bug fix: identify the failing case and expected corrected behavior.
- Feature migration: identify the legacy behavior or approved target behavior that must be observable.
- Refactor: identify the behavior and data guarantees that must remain unchanged.
- Review: identify concrete risks, regressions, missing evidence, and missing tests.
- Use the narrowest meaningful verification that proves the goal; if verification cannot be run, state the gap explicitly and do not imply success.

## Required artifacts per feature

Before implementation:

- feature inventory entry
- legacy dependency map
- behavior contract
- evidence records / confidence grades
- unresolved questions
- approved target design

Before completion:

- implementation change
- independent review report
- verification report
- remaining uncertainty explicitly documented

## Evidence grades

- **A**: automated test and observed legacy behavior agree, or equivalent strong independent evidence
- **B**: observed runtime behavior captured directly
- **C**: inferred from source + DB/schema/configuration analysis, not directly observed
- **D**: weak inference from source only
- **?**: unknown / not currently verifiable

Never silently upgrade an evidence grade.

## Target architecture defaults

These are defaults, not immutable rules:

- React/TypeScript/Tailwind for web UI
- FastAPI/Python for backend APIs and business orchestration
- PostgreSQL for persistence
- explicit application/service/repository boundaries where useful
- platform integration isolated from business logic
- compatibility adapters allowed when required for gradual replacement

## Working flow

```text
Discover -> Specify -> Grade Evidence -> Human Gate if needed
         -> Design -> Implement -> Adversarial Review -> Verify
         -> PASS or Process/Rule Fix -> Repeat
```

## Handoff rule

`HANDOFF.md` at the repo root is the single handoff file. Always update it
in place at the end of a session; never create a second handoff file
(dated, numbered, or otherwise). It is committed to Git, not gitignored.

## Stop conditions

<!-- BEGIN MANAGED STOP CONDITIONS -->
Stop and record an open question rather than guessing when a decision depends on:

- SC-01: unknown DLL entry points or lifecycle
- SC-02: unavailable platform behavior
- SC-03: ambiguous business semantics
- SC-04: destructive data migration assumptions
- SC-05: unverified stored procedure / trigger behavior
- SC-06: security/authentication requirements not visible in code
- SC-07: deployment topology not yet known
<!-- END MANAGED STOP CONDITIONS -->

## Important files

- `docs/00-project-context.md` — project background and session-derived decisions
- `docs/01-architecture.md` — pipeline/environment architecture
- `docs/02-migration-pipeline.md` — phase flow and gates
- `docs/03-evidence-and-verification.md` — incomplete-test strategy
- `docs/04-dll-integration-boundary.md` — current DLL constraint and candidate target boundaries
- `docs/05-open-questions.md` — unresolved facts
- `migration/RULEBOOK.md` — migration policy decisions
- `migration/STATE.md` — current phase/state
- `migration/QUEUE.md` — resumable work queue
