# Handoff

Single handoff file for this repo. **Always update this file in place — do
not create dated/numbered handoff files.** See AGENTS.md "Handoff rule."

Last updated: 2026-08-18

## 2026-08-18 — Issue #2 artifact-schema design completed, implementation still gated

Issue #2 (enum/ID/reference validation) was reviewed adversarially as a
design-only task. The literal proposal to parse body `Status:` values conflicts
with Issue #1, where `feature-card.md` frontmatter is the sole machine-readable
lifecycle source, so A-2 is defined as a schema layer on top of A-1 rather than
a second lifecycle parser.

The canonical design is `docs/issue-2-artifact-schema-validation.md`. Key
decisions: enums are schema-specific rather than one global `Grade` enum;
Issue #10 provenance values are exactly `observed | inferred`; `BR-###` IDs are
feature-local while `OQ-###` IDs are repository-global; references are checked
only in declared machine-readable fields rather than arbitrary Markdown;
templates are schema examples, not live artifact instances; and static schema
violations are aggregated with file/line diagnostics. Issue #9 keeps
revision-aware evidence-grade transition logic separate while sharing parsing
infrastructure where useful.

The review also found a concrete current-data inconsistency:
`migration/features/synthetic-demo/characterization-record.md` pairs
`none observed` with `Grade: N/A` in several items. `Grade: N/A` is now
reserved for genuinely inapplicable `Value: N/A` items; observed absence still
requires an evidence grade. This must be normalized during implementation, not
exempted.

No validator/template/sample implementation was changed. Implementation remains
a separate pass after explicit user authorization under AGENTS.md rule 13 and
must first perform the A-1/A-2 repository normalization described in the design.

## 2026-08-18 — Issue #8 designer/implementer role-boundary design completed, implementation still gated

Issue #8 was verified against the current agent definitions and reviewed
adversarially as a design-only task. The direct issue is valid: both
`migration-designer` and `implementer` currently use `edit: ask`, so the
intended design/implementation split is not enforced for direct edits.

The canonical design is now `docs/10-agent-role-boundary.md`. OpenCode's
current permission documentation confirms path-granular per-agent edit rules,
so no new OQ is required. The design uses deny-by-default edits with one
`ask` exception for `migration/features/*/target-feature-design.md`, preserves
`bash: deny`, and adds `task: deny` because the current global `task: allow`
would otherwise let the designer proxy implementation through a write-capable
subagent. Feature metadata, queue/state, open questions, and other process
artifacts remain coordinator-owned; `implementer` intentionally keeps its
broader `edit: ask` / `bash: ask` authority for approved implementation paths.

No `.opencode/agents/*`, `opencode.json`, validator, CI, or command
implementation was changed. The exact implementation steps and runtime
permission checks are documented in `docs/10-agent-role-boundary.md` and
remain blocked until the user explicitly releases the AGENTS.md rule 13 design
gate.

## 2026-08-18 — Issue #5 command contract designed, implementation still gated

Issue #5 (`.opencode/commands/*.md` deterministic execution contract) was
reviewed adversarially as a design-only task. Adding the same generic sections
to all seven commands is insufficient because discovery and status have
different invocation shapes, a feature ID cannot identify a queue row, broad
queue items must not be completed by one feature run, and feature-local
blocking must not automatically become project-level blocking.

The canonical design is `docs/10-command-execution-contract.md`, linked from
`docs/02-migration-pipeline.md`. Mutating commands select an explicit queue
item; lifecycle commands use canonical feature IDs; malformed arguments cause
zero durable writes; feature/queue/project state have separate ownership; and
`migration-status` is explicitly read-only.

Issue #4/PR #25 is now merged and is the agent input/output baseline. Command
implementation is intentionally not included and remains gated on explicit
approval plus reconciliation with issue #1 feature metadata, issue #3 phase
gates, and issue #15's remaining template mismatch. The merged canonical
verification artifact is `verification.md`; `docs/templates/verification-report.md`
remains a separate issue #15 inconsistency and must not silently redefine the
command output path.

## 2026-08-18 — Issue #7 routing design completed, implementation still gated

Issue #7 (ambiguous agent triggers/escalation and overlapping evidence-related
skills) was reviewed adversarially as a design-only task. The issue's proposed
one-line escalation/description changes are directionally correct but
insufficient for a low-reasoning model: they do not define negative triggers,
primary artifact ownership, tie-break behavior, or the difference between a
normal return and a gate-blocking STOP.

The canonical design is now `docs/09-agent-skill-routing.md`, with architecture,
pipeline, and evidence docs linked to it. Routing is based on current phase +
primary artifact. `migration-coordinator` owns cross-role dispatch; specialists
return adjacent-domain work instead of silently expanding scope. The four
overlapping skills are composable: behavior-contract owns the contract,
evidence-grading owns confidence on an existing claim, uncertainty-management
owns a new open question, and parity-verification owns the post-implementation
verification report/verdict. STOP is reserved for conditions that actually
block the current gate.

No `.opencode/agents` or `.opencode/skills` implementation was changed. The
exact implementation steps are documented in the design and should be applied
only after explicit user authorization under AGENTS.md rule 13. The latest main
already includes Issue #4's deterministic agent artifact/procedure contracts;
Issue #7 implementation must extend those definitions rather than overwrite
them.

## 2026-08-18 — Issue #10 observed/inferred provenance design completed

Issue #10 was reviewed adversarially as a design/documentation defect. The
literal fix of adding duplicate Observed/Inferred sections everywhere was
rejected because low-reasoning agents can duplicate the same claim across
both sections and because provenance can be confused with evidence grade.

The design now treats provenance and confidence as separate dimensions:
each material legacy claim is recorded once as `observed` or `inferred`;
mixed claims must be split; inferred claims must cite their supporting
observation/evidence; a source-visible fact is not automatically grade B.
The canonical rule is in `docs/03-evidence-and-verification.md` and is
encoded in `behavior-contract.md`, `evidence-record.md`, and
`feature-card.md`, with matching discovery/spec/grading agent guidance and
adversarial-review checks.

No runtime migration implementation was added. This change only fixes the
analysis/specification contract for issue #10.

## 2026-08-18 — Issue #9 evidence-grade transition design completed, implementation still gated

Issue #9 (silent evidence-grade promotion) was reviewed adversarially as a
design-only task. The issue is valid, but two literal recommendations were
rejected: forcing every new record to begin at `?`/`D` would fabricate grade
transitions, and recording only promotions would hide downgrade/reassessment
history.

The canonical design is now `docs/09-evidence-grade-transition-control.md`.
Key decisions: the top-level grade is a current snapshot backed by an
append-only grade-history chain; initial records may start directly at the
highest grade actually justified by their evidence; every real grade change
is recorded; promotions require newly referenced evidence plus a reason tied
to the target-grade criterion; unresolved contradictions block promotion;
downgrades remain auditable; and the current grade must equal the final
history row. Static enum/schema validation can share parsing with Issue #2,
but detecting a promotion is revision-aware and must receive an explicit base
revision rather than guessing one.

No evidence template, OpenCode skill, validator, CI, or command implementation
was changed. Those remain a separate follow-up after explicit approval under
AGENTS.md rule 13.

## 2026-08-18 — Issue #1 design completed, implementation still gated

Issue #1 (`validate_scaffold.py` feature artifact enforcement) was reviewed
adversarially as a design-only task. The issue's literal filename/status
proposal conflicts with the repository's current templates and
`synthetic-demo`, so implementation must not copy the issue example as-is.

The canonical design is now `docs/08-feature-artifact-validation.md` and
`migration/features/README.md`. Key decisions: canonical filenames use
`feature-card.md` / `target-feature-design.md`; lifecycle `stage` is separate
from boolean `blocked`; `feature-card.md` frontmatter becomes the
machine-readable lifecycle contract; required documents are cumulative by
stage; A-1 checks structure/existence only; `synthetic-demo` must be
normalized rather than exempted; CI already calls the validator, while
`/migration-status` still needs explicit integration.

No validator/template/sample implementation was changed. Implementation
remains a separate follow-up after this design has been accepted under
AGENTS.md rule 13.

## State — process reset, redo pending

S-001 through S-011 (`migration/QUEUE.md`, `migration/SLICES-DRAFT.md`) were
built backwards this session: implementation was dispatched first, and
design decisions got made on the spot by the implementer (embedded in code
+ commit messages, sometimes written up into an ADR after the fact). An
independent audit confirmed a repeated scope-creep pattern on top of that —
several slices built more than their own stated goal asked for (extra
import-linter contracts, a global exception safety net, OpenAPI schema
rewriting, an invented weighted scoring rubric), mostly added during
self-administered review passes.

**AGENTS.md rule 13 (added this session) is now in force: no implementation
starts until the user explicitly says design is done and to start
building, for any slice with lock-in risk medium or higher.** Read it
before doing anything else next session.

**User's explicit instruction: redo S-001..S-011 from the start, but this
time as design-doc elaboration only — no implementation.** The next
session's job is to work through the same slice list and produce/refine
the actual design artifacts (RULEBOOK amendments, ADRs, docs/0X sections,
behavior contracts) for each one, stopping there. Do not write or dispatch
any code for these slices until the user reviews the design output and
explicitly says to start building. This applies to the target skeleton,
the judge framework, the error contract, the platform boundary, the pilot
rubric — everything that has code sitting on top of a design decision
right now should get that decision properly written up and re-examined
before the code is treated as settled.

Note: this design work does **not** need legacy repository access. Only
the legacy-facing slices (Q-001..Q-010) are blocked on that — design
elaboration for the target-side architecture is doable regardless, and
conflating "blocked on legacy access" with "nothing to do" was a mistake
this session made.

## What already exists (do not treat as final; re-examine as part of the redo)

- `migration/SLICES-DRAFT.md` — the slice list itself
- Design docs already touched this session, most likely needing another
  pass: `docs/adr/0004`, `0005`, `0006`; `migration/RULEBOOK.md` Backend
  #4-8 and Agent workflow #6; `docs/02-migration-pipeline.md` pilot
  section; `docs/03-evidence-and-verification.md` characterization-schema
  and judge-verdict sections
- Code that exists ahead of a properly-gated design decision:
  `target/backend/` (FastAPI/React/Postgres skeleton), `migration/judge/`
  (composite judge, already trimmed once — see commit `044375d`),
  `target/backend/src/app/api/errors.py` + `app/domain/errors.py`,
  `target/backend/src/app/platform/` (boundary guard)
- `docs/templates/pilot-selection-rubric.md` — has invented numeric
  weights not grounded in any doc; docs/02 already caveats them as
  unvalidated draft, but the rubric itself should be re-examined in the
  redo, not assumed correct
- All work is committed to `main` in small commits, nothing squashed — read
  `git log` for what happened and why, including the audit findings and
  trims, before repeating any of it

## Legacy-blocked (separate from the redo above)

- Q-001 (DLL boundary inspection), Q-002 (test/CI inventory), Q-003
  (observable-output survey) — `migration/QUEUE.md`
- All of P0 `docs/05-open-questions.md` (OQ-001..OQ-010) — still OPEN
- These need legacy source access regardless of the redo's outcome

## Process notes for next session

- Follow AGENTS.md rule 13 literally: design artifact first, stop, wait for
  explicit "design done, start building" from the user, per slice.
- When dispatching any GLM work, be explicit in the prompt about whether it
  is a design-only task (docs, no code) or an implementation task — do not
  let a single prompt do both, that's exactly the failure mode from this
  session.
- `opencode run -m zai-coding-plan/glm-5.3 --variant low|high --format json
  --auto "<prompt>"` times out around 280s on multi-file tasks; re-run with
  `--continue` to resume the same session rather than starting over.
