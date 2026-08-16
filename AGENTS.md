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

Stop and record an open question rather than guessing when a decision depends on:

- unknown DLL entry points or lifecycle
- unavailable platform behavior
- ambiguous business semantics
- destructive data migration assumptions
- unverified stored procedure / trigger behavior
- security/authentication requirements not visible in code
- deployment topology not yet known

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
