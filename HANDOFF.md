# Handoff

Single handoff file for this repo. **Always update this file in place — do
not create dated/numbered handoff files.** See AGENTS.md "Handoff rule."

Last updated: 2026-08-18

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
