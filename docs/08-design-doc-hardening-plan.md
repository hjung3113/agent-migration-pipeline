# Design Document Hardening Plan

Tracks the plan for making the pipeline's own design documents (agent/command/skill
docs, templates, gate criteria, state files) concrete and internally consistent,
and for making each document's role unambiguous. Source issues: GitHub #1-#17
(repo `hjung3113/agent-migration-pipeline`). DB tooling (#18-23) is a separate
track and out of scope here; #17 (plugin version pinning) is a config concern,
not a design-doc concern, and is also excluded.

Work is split into slices. Each slice is a self-contained unit of doc edits;
slices are ordered by dependency, not by issue number.

## Slice 0 — Document role skeleton (no dependencies, parallelizable)

Establishes which document owns which decision before any other slice edits
content that assumes an answer.

- **#15** — Reconcile `docs/templates/*` filenames with the example names used in
  `migration/features/README.md`. Canonical naming that every later slice's
  path references depend on.
- **#13** — Define how the single source of truth (AGENTS.md stop conditions)
  relates to per-agent docs: republish vs. reference, and what a STOP does to
  `docs/05-open-questions.md` / `feature.md` / `migration/STATE.md`.
- **#7** — Define non-overlapping trigger conditions for the four skills that
  currently share territory: `behavior-contract`, `evidence-grading`,
  `parity-verification`, `uncertainty-management`.

## Slice 1 — Gate/criteria concreteness (parallel with Slice 0, prerequisite for Slice 2)

Turns qualitative gate language into checkable criteria that Slice 2's command
docs will reference.

- **#3** — Rewrite Phase gates ("understood well enough", "materially affect")
  as boolean checklists (3-6 items each, pointing at specific files/fields).
- **#14** — Define the allowed `Status` enum values for `migration/STATE.md`
  and `migration/QUEUE.md`.

## Slice 2 — Procedure documents (depends on Slice 0 + Slice 1)

Needs the canonical names (Slice 0) and the concrete criteria (Slice 1) before
procedures can cite exact paths and exact gate/state conditions. Internal
order: agents, then commands, then skills.

- **#4** — Add numbered steps + input/output paths + if-then branches to the
  8 agent docs (`.opencode/agents/*.md`).
- **#8** — While editing `migration-designer.md` / `implementer.md` for #4,
  also differentiate their `edit` permission scope (designer: docs only,
  implementer: code only). Piggybacks on the same file edits.
- **#5** — Add `## Output`, `## Preconditions`, `## State updates` sections to
  the 7 command docs (`.opencode/commands/*.md`), referencing #3's checklists
  and #14's enum.
- **#6** — Add input/output paths + if-then branches to the 9 skill docs
  (`.opencode/skills/*/SKILL.md`), following the path conventions fixed by #4/#5.

## Slice 3 — Evidence/verification principle consistency (parallel with Slice 0; overlaps Slice 2's files)

Fixes places where a principle document (`docs/03-evidence-and-verification.md`)
and an execution document (a SKILL.md, a template) disagree or fail to connect.
`parity-verification/SKILL.md` and `verifier.md` are touched by both this slice
and Slice 2 (#6) — do them in the same pass to avoid rework.

- **#11** — `docs/03` requires judge self-validation (negative control);
  `parity-verification/SKILL.md` and `verifier.md` weaken it to "where
  practical". Remove the escape clause or replace it with an explicit,
  narrow whitelist of exceptions.
- **#12** — `behavior-contract.md` already has a `## Comparison semantics`
  section; `parity-verification/SKILL.md` doesn't point to it. Make it the
  required location instead of letting comparison rules live in test code.
- **#9** — Add a `## Grade history` section to `evidence-record.md` template so
  the "never silently upgrade a grade" rule is enforceable, not just stated.
- **#10** — Add explicit Observed/Inferred structure to `behavior-contract.md`,
  `feature-card.md`, `evidence-record.md`.

## Slice 4 — Supplementary concreteness (independent, any time)

- **#16** — Add 3-5 concrete legacy-structure anti-pattern examples to
  `migration-designer.md` (and mirror the same list in `adversarial-reviewer.md`).

## Slice 5 — Automated enforcement (depends on Slices 0, 1, 2, 3)

Closes the loop: once the conventions above exist, encode them as checks.

- **#1** — Extend `validate_scaffold.py` to check per-feature artifacts exist,
  using the filenames fixed in Slice 0.
- **#2** — Extend `validate_scaffold.py` to validate enum/ID formats
  (Grade, Status, Result, `OQ-\d{3}`, `BR-\d{3}`) defined in Slice 1.

## Dependency graph

```
Slice 0 (#15, #13, #7)  ─┬─→ Slice 2 (#4, #8, #5, #6) ─┐
Slice 1 (#3, #14)        ┘                              ├─→ Slice 5 (#1, #2)
Slice 0 ──────────────────→ Slice 3 (#11, #12, #9, #10) ┘
Slice 4 (#16): independent
```

## Execution / review policy (open item)

Intent: dispatch each slice's edit work to a model sized to the slice's
difficulty (low effort for mechanical renames/additions, high effort for
slices requiring judgment calls, e.g. Slice 2/3), then review.

Review split:
- Slices whose mistakes are hard to reverse or carry regression risk once
  other slices build on them (Slice 0, Slice 1, Slice 5) — Opus review,
  scoped to the diff only, not a full read of the surrounding docs.
- Everything else (Slice 2, Slice 3, Slice 4) — Sonnet, high reasoning
  effort, as reviewer.

Execution tooling (an `orca`/`opencode` CLI driving a GLM 5.3 model at
variable effort) was requested but is not available in the current session
environment — not installed, no reachable sibling session/environment
configured with it. Unresolved as of this handoff; whoever picks this up
should either confirm where that tooling lives and point this session at it,
or fall back to the Agent tool's native Sonnet/Opus models for the work pass
too, not just review.

## Status

Not started. This document is the handoff; no slice work has been applied yet.
