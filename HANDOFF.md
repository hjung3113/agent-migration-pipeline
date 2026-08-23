# Handoff

Single handoff file for this repo. **Always update this file in place — do
not create dated/numbered handoff files.** See AGENTS.md "Handoff rule."

Last updated: 2026-08-23

## Next session: Issue #9 + followup done, merged; continue Track P at #11

Issue #9 (evidence-grade transition control) is implemented, reviewed, and merged to `main`
(PR #65, squash-merged as `d6ad610`), against the merged canonical design
`docs/09-evidence-grade-transition-control.md`. Built with the same three-stage pipeline as
Issue #6:

1. **Gate check + execution plan** — opencode (`zai-coding-plan/glm-5.3`, `--variant high`,
   `--auto`) re-ran the ISSUES-PLAN-DRAFT "구현 시작 전 체크" 7-item gate for #9 against
   current `main` (all 7 passed, no blockers) and wrote `migration/ISSUE-9-EXECUTION-PLAN.md`
   — a DAG (T-L1/T-L2/T-L3 file-disjoint layers, then T-I1 integration, T-R1 review, T-H1
   handoff) plus 8 derived judgment calls (P-1..P-8, e.g. Layer 1 extends
   `validate_evidence_record()` in place rather than adding a sibling function; Layer 3 is a
   standalone script requiring an explicit `--base <ref>` with no default, never wired into
   `collect_validation_errors()`/CI). Committed as `fae875d` on branch
   `hjung3113/issue9-plan`.
2. **Implementation** — codex (`gpt-5.6-luna`, `model_reasoning_effort=max`, repo default)
   executed that plan verbatim in the same worktree/branch:
   - **Layer 1 (schema)**: `docs/templates/evidence-record.md` gained a `## Grade history`
     section (fixed columns `Recorded date | From | To | Reason | Evidence refs`);
     `validate_evidence_record()` in `scripts/validate_scaffold.py` gained a
     `_validate_grade_history()` helper enforcing history presence, initial `From = —`
     (em-dash sentinel, distinct from grade `?`), row-to-row continuity, `Grade:` == final
     row `To`, enum values, non-empty reasons, evidence-refs presence rules.
   - **Layer 2 (agent procedure)**: `.opencode/skills/evidence-grading/SKILL.md` gained a new
     `## Grade-change procedure` H2 with the design's 8-step compare-before-change procedure;
     the existing 5-section (#6) and routing (#7) structure was preserved untouched — purely
     additive diff, confirmed line-by-line against `main`.
   - **Layer 3 (revision-aware transition check)**: new standalone
     `scripts/validate_grade_transition.py`, deliberately not wired into
     `collect_validation_errors()`/`main()`/CI. Requires explicit `--base <ref>` (no default,
     hard CLI error if omitted), repeatable `--file <path>`, optional `--head <ref>`. Detects
     promotion/downgrade via `? < D < C < B < A`, requires a promotion's evidence ref be a
     token absent from the base revision's file text, enforces append-only history prefix,
     flags same-path record deletion between revisions, and handles the legacy-adoption
     baseline row when the base revision predates this control.
   - New tests: `scripts/tests/test_grade_history.py`, `scripts/tests/test_grade_transition.py`,
     plus additions to `test_validate_schema.py` and `test_skill_execution_contract.py` (29
     new tests total). Opened PR #65.
3. **Independent adversarial review (T-R1)** — same two-phase pattern as #6 (fresh subagent,
   phase 1 sees only PR title/body and forms 20 falsifiable hypotheses from the design doc +
   this repo's F1/F2 failure-pattern history; phase 2 gets the diff/repo and verifies each
   against real code/tests). **Verdict: APPROVE — all 20 hypotheses refuted**, no defects of
   the class Issue #6 found (silent conditional/reference drops during a batch rewrite).
   Confirmed live (not from PR-body claims): `validate_scaffold.py` exit 0, `pytest
   scripts/tests/ -q` 370 passed (341 main + 29 new, arithmetic verified), `check_doc_links.py`
   / `check_oq_updates.py` green.
   - Two non-blocking findings recorded on the PR as known limitations rather than fixed:
     **(1)** `validate_grade_transition.py`'s `_parse_history()` (~200 lines) duplicates
     `validate_scaffold.py`'s `_validate_grade_history()` (~187 lines) instead of importing it
     — both correct today, but nothing enforces the two stay in sync if one is edited later;
     a real follow-up candidate is having Layer 3 import Layer 1's helper directly.
     **(2)** the append-only history check compares historical rows byte-for-byte, so even a
     harmless typo fix to a past row's `Reason` fails `[append-only]` — stricter than the
     design's literal text ("historical typo/format cleanup may not change the semantic
     meaning of a past decision", implying pure typo fixes should be allowed). Safety-first
     simplification, not treated as blocking.
4. **Merge** — squash-merged as `d6ad610` after the review comment was posted to PR #65.

**Post-merge followup (PR #66, squash-merged as `4771dbc`)**: per updated process, the
independent review's two non-blocking findings were *not* auto-merged this time — the user
explicitly changed the workflow (see below) and separately posted their own post-merge review
on PR #65 finding two real **blocking** P1 defects in `scripts/validate_grade_transition.py`'s
promotion new-evidence check (not the two non-blocking findings from the T-R1 review; those
two are still open/unfixed, tracked below):

- **P1 — Markdown link label change bypassed new-evidence detection.**
  `_evidence_ref_tokens()` didn't canonicalize a Markdown link's target locator, so relabeling
  `[old](capture/x.log)` -> `[new](capture/x.log)` looked like new evidence despite citing the
  identical target — directly undermines the anti-silent-upgrade purpose of Layer 3. Fixed by
  extracting Markdown links from the raw `Evidence refs` cell via a non-anchored regex *before*
  delimiter-splitting (a first-pass fix that only anchored the regex to a single already-split
  token still missed multi-word link labels — e.g. `[old label](capture/x.log)` — because the
  label's internal space fragmented the token before the link pattern could match; both GitHub
  owner review and Codex's automated inline review caught this on the first followup commit,
  fixed in a second commit same PR).
- **P1 — same new evidence reusable across consecutive promotions in one candidate diff.**
  Promotion refs were checked only against the base revision's original file text, not against
  evidence already introduced by an earlier appended row in the same diff, so `C -> B -> A`
  could cite the identical brand-new ref in both promotion rows and both would pass. Fixed:
  `_check_existing_transition()` now accumulates each appended row's evidence-refs text into a
  running `known_evidence_text` blob (seeded from `base_text`) that later rows are checked
  against.
- 3 new regression tests added (`test_relabeled_markdown_link_is_not_new_evidence`,
  `test_relabeled_multiword_markdown_link_label_is_not_new_evidence`,
  `test_same_new_evidence_cannot_be_reused_across_consecutive_promotions`). Final state:
  `validate_scaffold.py` exit 0, `pytest scripts/tests/ -q` 373 passed (370 post-#65 + 3),
  doc-links/OQ green.

**Workflow change for this repo, effective this session**: do not auto-merge a Track P/D PR
after a clean independent review. Open the PR, post the review as a PR comment, then wait —
merge only on the user's explicit instruction. (Saved as a standing memory:
`feedback_no_auto_merge`.) This does not roll back the standing Track P/D rule-13
*implementation* authorization from AGENTS.md — it only changes who pulls the merge trigger.

The T-R1 review's two non-blocking findings from the original PR #65 review are still **not**
fixed (deliberately, per that review's own recommendation to treat them as follow-up, not
blockers) — leaving them here as a known-gap pointer for whoever picks up Track P/D work with
spare scope: (1) `validate_grade_transition.py`'s `_parse_history()` duplicates
`validate_scaffold.py`'s `_validate_grade_history()` instead of importing it; (2) the
append-only history check is byte-for-byte, stricter than the design's stated allowance for
historical typo/format cleanup.

Track P merge order per plan: `#9 -> #11`. #11 shares `parity-verification`/verifier files
with #6 (not with #9's files), so it is unaffected by this session's file set. Before starting
#11, redo the 7-item gate against current `main`, and re-read `.opencode/skills/
parity-verification/SKILL.md`, the verifier agent, and `docs/03-evidence-and-verification.md`
/`migration/RULEBOOK.md:96`/`docs/templates/verification.md` as they now stand (all already
canonical per the design; #11's remaining scope is narrowly the leftover `"where practical"`
string in `parity-verification/SKILL.md:30` plus verifier-agent/regression-test work — see
`ISSUES-PLAN-DRAFT.md`'s P-R lane note). Rule-13 Track P/D authorization remains in effect and
has not been revoked. After #11, Track P is complete per the current plan; Track D (`#23 ->
#20 -> ...`) remains separately gated and untouched this session.

## Historical: Issue #6 done, merged; continue Track P at #9 -> #11

Issue #6 (skill execution contract) is implemented, reviewed, and merged to
`main` (PR #64, squash-merged as `5ef270d`), against the merged canonical
design `docs/10-skill-execution-contract.md`. Built via a three-stage
pipeline instead of the earlier "opencode/codex per branch" pattern:

1. **Gate check + execution plan** — opencode (glm-5.3, `--variant high`,
   `--auto`) re-ran the ISSUES-PLAN-DRAFT "구현 시작 전 체크" 7-item gate for
   #6 against current `main` (all 7 passed, no blockers) and wrote
   `migration/ISSUE-6-EXECUTION-PLAN.md` — a DAG task breakdown (T-V1
   validator task + S-1..S-9 one per skill file, all mutually
   file-disjoint so fully parallel in principle, executed as one physical
   PR per the repo's "no mixed-contract state" precedent) plus 4 derived
   judgment calls (P-1..P-4, e.g. normalizing `{feature-id}` ->
   `<feature-id>` to match the command layer) and explicit design-gate
   reopen triggers. Committed as `e16ccda` on branch `hjung3113/issue6-plan`.
2. **Implementation** — codex (`gpt-5.6-luna`, `model_reasoning_effort=max`)
   executed that plan verbatim in the same worktree/branch: added
   `validate_skill_execution_contract()` to `scripts/validate_scaffold.py`
   (6 structural checks: existence, 5-section presence/order,
   `[Input]`/`[Output]` markers in Procedure, canonical `<feature-id>` +
   singleton path via the existing `_FEATURE_PATH_RE`, legacy-alias
   rejection, `BLOCKED`/`PARTIAL` mention in Branches) plus
   `scripts/tests/test_skill_execution_contract.py` (20 tests), and
   rewrote all 9 `.opencode/skills/*/SKILL.md` into the ordered
   `Inputs`/`Outputs`/`Procedure`/`Branches`/`Done means` contract. Opened
   PR #64.
3. **Independent adversarial review (T-R1)** — a fresh Opus subagent was
   deliberately run in two phases to avoid anchoring: phase 1 saw only the
   PR title/body (no diff) and wrote a review checklist/hypotheses from
   that alone; phase 2 was given the actual diff and repo access and told
   to verify or refute its own phase-1 hypotheses against real code
   (including running the validator/pytest itself). Verdict: **REQUEST
   CHANGES**, 10 findings. Two were HIGH and would not have been caught by
   the green validator/pytest suite:
   - **F1** — `feature-migration/SKILL.md`'s DB-bootstrap Branches rule
     lost its "unless the approved design declares that path in scope"
     escape hatch during the 5-section rewrite, becoming an unconditional
     `BLOCKED`. Combined with `target-feature-design/SKILL.md` requiring
     the design to declare that same bootstrap path when missing, this
     was a precondition deadlock on the first DB-backed feature — the
     same defect *class* PR #61/#62's post-merge review found (a
     structural rewrite silently dropping a conditional clause).
   - **F2** — `target-feature-design/SKILL.md` lost its lead-in reference
     to `docs/templates/target-feature-design.md` and
     `docs/13-legacy-structure-rejection-contract.md` (the doc that
     defines the LSR-01..LSR-07 IDs the file requires elsewhere), and
     `check_doc_links.py` can't catch a *deleted* link.
   - F3-F6 (MEDIUM): three more skills silently dropped their
     `docs/templates/*.md` reference; a legacy-discovery guardrail
     ("don't promote ambiguous/dead behavior to an inferred fact") was
     dropped; `"where practical"` (an #11-owned hedge phrase, and the
     evidence doc says explicitly "there is no `where practical` waiver")
     leaked into two new locations in parity-verification beyond its one
     canonical, preserved occurrence; and in 3 files the preserved rule
     sub-blocks (`### Contract authoring rules` etc.) ended up nested
     inside `## Procedure`, inflating its numbered-step count to 18 against
     the design's "normally 5-8" guidance.
   - F7-F9 (LOW): four #7-owned tie-break sections had an unreported
     wording tweak (`"that primary artifact"` -> `"the primary artifact"`)
     that loosens routing semantics; one skill's rule was silently
     broadened; and the PR body's Non-goals claimed the execution plan
     doc wasn't touched by the PR when it was (included from the T-0
     commit).
   - F10 (validator leniency: hardcoded skill-name tuple won't auto-cover
     a future 10th skill; alias check scans whole file not just feature
     paths; `_h2_sections()` has no fenced-code awareness) was
     **deliberately left unfixed** — recorded as a future validator
     hardening item, not blocking this issue.
   - What the review confirmed as true and did *not* need changing: test
     counts (341 total / 20 new) were honest, not padded; all 9 skills got
     a real 5-section transform with zero leftover `{feature-id}` braces;
     the new validator genuinely implements all 6 planned checks (not a
     weaker stand-in); `#11` rule 7, `#10` provenance markers, and `#13`
     STOP-payload deference were preserved byte-for-byte where it
     mattered; nothing outside declared scope (`HANDOFF.md`, `docs/08`,
     `.opencode/agents`, `.opencode/commands`, migration app code) was
     touched.
4. **Fix + re-verify** — codex (`gpt-5.6-luna`, max) fixed F1-F8 in
   commit `eb3e92c` (F1/F2 by restoring the dropped conditional/reference
   text verbatim rather than reinventing it; F6 by relocating the
   preserved rule sub-blocks out of `## Procedure` without editing their
   text) and updated the PR body for F9. Final re-verification: `python3
   scripts/validate_scaffold.py` exit 0, `python3 -m pytest scripts/tests/
   -q` — 341 passed, `check_doc_links.py`/`check_oq_updates.py` green.
   Squash-merged as `5ef270d`.

This F1/F2 pattern (a batch structural rewrite silently dropping a
conditional clause or a doc reference, invisible to both the validator and
`check_doc_links.py`) is now the second time this exact failure shape has
shown up (first in #61/#62's post-merge findings). Future skill/agent-file
batch rewrites should specifically diff conditional/exception clauses and
doc-reference lines against the pre-rewrite version, not just check
structural presence.

Next Track P order per plan: `#9 -> #11`. Before starting #9, redo the
"구현 시작 전 체크" 7-item gate in `ISSUES-PLAN-DRAFT.md` against current
`main` — #9 (evidence-grade transition control) shares
`evidence-grading/SKILL.md` and `scripts/validate_scaffold.py` with this
session's work, so re-read both as they now stand rather than assuming the
pre-#6 shape. As with #6, budget time after merge for an independent
adversarial review pass (the phase-separated PR-body-only-then-diff
review pattern used this session is worth reusing — it forced the
reviewer to form falsifiable hypotheses before seeing the code, rather
than pattern-matching against a diff it already trusted). Rule-13 Track
P/D authorization remains in effect and has not been revoked.

## Historical: Issues #5/#13 done + PR #61/#62 review followup merged; continue Track P at #6

Issues #5 (command execution contract) and #13 (agent STOP condition
contract) are implemented, reviewed, and merged to `main` against their
merged canonical designs `docs/10-command-execution-contract.md` and
`docs/11-stop-condition-contract.md`. Built in parallel by codex
(`gpt-5.6-luna`, `model_reasoning_effort=max`, per the repo's current
model-routing policy) in separate Orca worktrees off the same base, per the
plan's note that #5/#13 are logically parallel. **After merge, the owner left
post-merge review comments on both PRs (bot review + own review) identifying
7 real gaps; a third followup PR fixed all of them (PR #63, squash-merged as
`076d2a0`)** — see below.

- **#13** (PR #61, squash-merged as `9ffdacf`): canonical `SC-01..SC-07`
  registry now lives in a `<!-- BEGIN/END MANAGED STOP CONDITIONS -->` marker
  block in `AGENTS.md`; new `scripts/sync_agent_stop_conditions.py` generates
  and checks the identical `## Stop conditions` block across every
  `.opencode/agents/*.md`; all eight agents also carry a role-appropriate
  `## Stop handling` section stating the common STOP payload; and
  `migration-coordinator.md` gets deduplication, OQ allocation,
  feature/project scope classification, conservative lifecycle persistence,
  and gate re-evaluation — explicitly reusing Issue #14's already-merged
  durable-state transaction/validator path (`validate_durable_state()`,
  generation transaction, blob re-hash) rather than a second persistence
  mechanism.
- **#5** (PR #62, squash-merged as `ca3c564`): all seven
  `.opencode/commands/*.md` files now share one consistent contract
  (`Arguments` / `Inputs` / `Preconditions` / `Outputs` / `State updates` /
  `Failure behavior`); `migration-status.md` stays explicitly read-only,
  consistent with Issue #1's existing validator wiring; new
  `validate_command_contract()` checks all seven files carry the required
  sections and that referenced feature-artifact paths use the canonical
  `<feature-id>` placeholder and canonical singleton names (docs/08),
  rejecting legacy aliases.
- **PR #61/#62 followup** (PR #63, squash-merged as `076d2a0`, built the same
  way in a third isolated codex worktree): fixed all 7 owner-identified
  post-merge gaps, none requiring a new design decision —
  - `scripts/sync_agent_stop_conditions.py`: `--write`'s heading-restore path
    no longer prepends `## Stop conditions` before the YAML frontmatter (it
    was inserting at document offset 0 instead of at the marker block's own
    offset); `validate_agent_stop_conditions()` now validates each common
    STOP payload enum field (`Reason`, `Stop condition`, `Scope`, `Stop
    current gate`) against its actual permitted values from docs/11, instead
    of only checking cross-agent string equality (which let identical drift
    to an invalid value like `Scope: banana` pass undetected).
  - All 8 `.opencode/agents/*.md` `## Escalation` sections (Issue #7) now
    delegate to the common 12-field STOP payload (Issue #13) instead of
    separately restating their own older 7-field list, which was missing the
    newer `Scope`/`Feature`/`Queue item`/`Partial artifact` fields;
    `validate_agent_routing()` updated to match (checks for the delegation
    marker, not the old field list).
  - All 6 mutating `.opencode/commands/*.md` files had a precondition
    deadlock: "this run can satisfy the completion artifact" required the
    run to already fully satisfy its own output (e.g. `migration-design`
    required a G3-complete, gate-passed `target-feature-design.md` before it
    could run — the artifact it exists to produce; `migration-review` on a
    combined review/verification row required `verification.md`, produced by
    a later `migration-verify` run). Fixed: precondition now requires only
    phase/artifact-type compatibility; full artifact satisfaction is the bar
    for marking the row `DONE`, not for starting the run.
  - `validate_command_contract()` gained a canonical feature-artifact-name
    check (a typo like `behaviour-contract.md` previously passed silently)
    and `_validate_command_argument_grammar()`: `migration-status.md` must
    accept no arguments and its `State updates` must affirmatively state no
    mutation (negation-aware, so "never mutates" doesn't false-positive); the
    other six commands must require `--queue <queue-id>`, and the five
    feature-scoped ones must also require `--feature <feature-id>`
    (unbracketed) — previously the validator only checked that six H2
    headings existed and were non-empty, so e.g. giving `migration-status` a
    `--feature` flag would still pass CI.

Issues #5 (command execution contract) and #13 (agent STOP condition
contract) are implemented, reviewed, and merged to `main` against their
merged canonical designs `docs/10-command-execution-contract.md` and
`docs/11-stop-condition-contract.md`. Built in parallel by codex
(`gpt-5.6-luna`, `model_reasoning_effort=max`, per the repo's current
model-routing policy) in separate Orca worktrees off the same base, per the
plan's note that #5/#13 are logically parallel.

- **#13** (PR #61, squash-merged as `9ffdacf`): canonical `SC-01..SC-07`
  registry now lives in a `<!-- BEGIN/END MANAGED STOP CONDITIONS -->` marker
  block in `AGENTS.md`; new `scripts/sync_agent_stop_conditions.py` generates
  and checks the identical `## Stop conditions` block across every
  `.opencode/agents/*.md`; all eight agents also carry a role-appropriate
  `## Stop handling` section stating the common STOP payload; and
  `migration-coordinator.md` gets deduplication, OQ allocation,
  feature/project scope classification, conservative lifecycle persistence,
  and gate re-evaluation — explicitly reusing Issue #14's already-merged
  durable-state transaction/validator path (`validate_durable_state()`,
  generation transaction, blob re-hash) rather than a second persistence
  mechanism.
- **#5** (PR #62, squash-merged as `ca3c564`): all seven
  `.opencode/commands/*.md` files now share one consistent contract
  (`Arguments` / `Inputs` / `Preconditions` / `Outputs` / `State updates` /
  `Failure behavior`); `migration-status.md` stays explicitly read-only,
  consistent with Issue #1's existing validator wiring; new
  `validate_command_contract()` checks all seven files carry the required
  sections and that referenced feature-artifact paths use the canonical
  `<feature-id>` placeholder and canonical singleton names (docs/08),
  rejecting legacy aliases.

**File-ownership boundary honored across the two branches**: #13 owns
`.opencode/agents/*.md` + `AGENTS.md`; #5 owns `.opencode/commands/*.md`;
neither touched the other's files (verified by diff before merge). Both
additively touched `scripts/validate_scaffold.py` (each adding one isolated
`validate_*_contract()` function plus a new `collect_validation_errors()`
term) — #13 merged first, #5's branch was rebased onto the updated `main`
and the resulting conflict was a trivial concatenation (same pattern as the
#7/#8 session), not a semantic collision.

One #5 worker run stalled for ~3 minutes mid-exploration (spinner counter
advancing with no new tool-call output); interrupted (Escape) and redirected
with "stop exploring, start editing" per the same recovery pattern the
#7-session handoff documented for opencode headless hangs — this time on
codex, confirming the recovery pattern generalizes across CLI backends. The
sibling #13 terminal was also interrupted in the same pass as a false
positive (it was mid-progress, not stalled) and simply resumed with no lost
work.

The #13 worker's branch included an extra unreviewed `docs: update handoff
for issue 13` commit that landed between this session's status check and
push (a real timing race — the worker kept committing after the review
snapshot was taken); it was squash-merged along with the reviewed commits.
Its stale HANDOFF.md content (said "committed but not pushed") is superseded
by this entry. No functional code was in that commit beyond the handoff
text, so no re-review was needed, but future sessions should re-check
`git log <base>..HEAD` immediately before pushing, not only right after
`NEW_COMMITS_DETECTED` fires, in case the worker is still active.

Final state on `main`: `python3 scripts/validate_scaffold.py` exits 0;
`python3 -m pytest scripts/tests/ -q` — 321 passed (301 baseline before
#5/#13 + 7 (#13) + 12 (#5) + net +1 from PR #63's followup, which added
several new regression tests but also consolidated a parametrized
7-field-check test down to 1 when the old Escalation field list was
replaced).

Next Track P order per plan: `#6 -> #9 -> #11`. Before starting, redo the
"구현 시작 전 체크" 7-item gate in `ISSUES-PLAN-DRAFT.md` against current
`main`. #6 now has all three of its prerequisites merged (#5, #7, #8 —
command ownership, routing, permission boundary) so it can start
immediately; consume them rather than re-deciding skill I/O ownership. As
with #5/#13, budget time after merge to re-check for owner review comments
on the resulting PR(s) before considering the issue closed — this session's
#61/#62 followup shows real regression-worthy gaps can survive the initial
adversarial pass. Rule-13 Track P/D authorization remains in effect and has
not been revoked.

## Historical: Issues #7/#8 done, merged; continue Track P at #5 -> #13

Issues #7 (agent/skill routing determinism) and #8 (migration-designer
permission boundary) are implemented, reviewed, and merged to `main`
against their merged canonical designs `docs/09-agent-skill-routing.md`
and `docs/10-agent-role-boundary.md`. Built in parallel by opencode
(glm-5.3, `--variant low` for #8, `--variant high` for #7) in separate
Orca worktrees off the same base, per the plan's P-R lane note that #7/#8
are independent scopes.

- **#8** (PR #58, squash-merged as `d1483a5`): `migration-designer`
  frontmatter now has deny-by-default granular `edit` (catch-all `deny`
  before a narrow `ask` exception for `migration/features/*/
  target-feature-design.md`, last-match-wins), `bash: deny`, and new
  `task: deny` (closes the implementer-delegation bypass the design
  called out). Body states the designer's only direct durable write and
  that all other changes return to `migration-coordinator`.
- **#7** (PR #59, squash-merged as `1019e19`): all 8 `.opencode/agents/
  *.md` got a 3-part frontmatter `description` (`Invoke when ... ; owns
  ... ; do not use for ...`), `## Invoke when` / `## Do not invoke for` /
  `## Primary output ownership` body sections, and a standard 7-field
  `## Escalation` section; `migration-coordinator.md` states the 7-step
  dispatch algorithm and forbids peer-to-peer specialist re-routing; the
  4 overlapping skills (`behavior-contract`/`evidence-grading`/
  `uncertainty-management`/`parity-verification`) each got a `## Primary
  artifact boundary` + `## Skill tie-break` section.

**File-ownership boundary honored across the two branches**: both touch
`.opencode/agents/migration-designer.md` (#8 owns the `permission:`
frontmatter block, #7 owns `description:` + body routing/escalation
sections) — each branch was explicitly instructed not to touch the
other's region, verified by diff before merge, and the one resulting
merge conflict (both branches appended content after the same procedure
step 6) was a trivial concatenation, not a semantic collision.

One #7 implementation run stalled for ~1 hour on a self-dispatched nested
"adversarial review" subagent task inside `opencode run --auto` (headless
mode) with zero progress/CPU; killed and resumed with an explicit
instruction to self-review inline instead of dispatching another agent,
which completed in ~2 minutes. If a future headless opencode run needs a
review step, prefer inline self-review over `task`-tool subagent dispatch
inside `opencode run --auto` unless/until that hang is understood.

Owner adversarial review (via PR comments, both PRs, matching #1/#2/#14's
diligence) found 4 real gaps, all fixed in follow-up commits before final
merge (no over-hardening added beyond what each finding actually required):

- PR #58 P1: only static frontmatter checks existed; the design's
  "Verify behavior at the permission evaluator boundary" requirement was
  unmet. Fixed by discovering `opencode debug agent <name>` returns the
  actual resolved, ordered, last-match-wins permission list and `tools`
  summary the real evaluator produces — used that directly instead of
  building interactive-session automation. Guarded with
  `shutil.which("opencode")` skip so environments without the CLI don't
  break. Landed separately as PR #60 (squash-merged as `b8456aa`) since
  #58 was already merged when the review comment landed.
- PR #58 P2: the new test imported `yaml` (PyYAML), but the repo has no
  dependency manifest anywhere and CI's `repo-guards` job never runs
  `pytest` — a clean checkout would fail. Replaced with a small parser
  scoped to the repo's actual flat/one-level `permission:` shape, no
  external dependency (same commit as the P1 fix, PR #60).
- PR #59 P2 (#1 of 2): `validate_agent_routing()`'s description check
  only required non-empty, so a description could regress to something
  ambiguous (e.g. "migration helper") and still pass — silently
  reopening the exact initial-selection ambiguity #7 was meant to close.
  Fixed: now requires the 3 markers every current description actually
  uses (`Invoke when` / `owns` / `do not use for`).
- PR #59 P2 (#2 of 2): the 4 overlapping skills had no regression check
  for their `## Primary artifact boundary` / `## Skill tie-break`
  sections — `validate_skills()` only checks name/non-empty description,
  so both new sections could be deleted from any of the 4 with
  validation staying green. Fixed with new
  `validate_skill_routing_contract()`, scoped to only those 4 canonical
  skill files.

Final state on `main`: `python3 scripts/validate_scaffold.py` exits 0;
`python3 -m pytest scripts/tests/ -q` — 301 passed (262 baseline before
#7/#8 + 4 (#8) + 3 (#60 runtime checks) + 22 (#7) + 10 (#59 followup) =
301); `check_doc_links.py` / `check_oq_updates.py` pass.

Next Track P order per plan: `#5 -> #13 -> #6 -> #9 -> #11`. Before
starting each, redo the "구현 시작 전 체크" 7-item gate in
`ISSUES-PLAN-DRAFT.md` against current `main`. Per the plan: `#6` now has
all three of its prerequisites merged (`#5` still pending, `#7`/`#8`
done) so it cannot start until `#5` lands; `#5` and `#13` are logically
parallel but the plan says merge sequentially if they touch shared
coordinator/validator files — check the actual diffs before assuming
parallel-safe, the way #7/#8 turned out to need careful scoping despite
looking independent on paper. Rule-13 Track P/D authorization remains in
effect and has not been revoked.

## Next session (superseded): Issue #14 done, merged; continue Track P at (#7, #8)

Issue #14 (durable-state protocol) is implemented, reviewed, and merged to
`main` (PR #57, squash-merged as `bc3b946`), against the merged canonical
design `docs/11-durable-state-protocol.md`, per the owner's explicit rule-13
authorization for #14 only. Built by opencode (glm-5.3, `--variant high`) in
a separate worktree, same process as #1/#2. All 8 implementation
requirements done as one pass:

- `migration/STATE.md` migrated to the frontmatter schema. Honest
  normalization: `gate_result: BLOCKED` with `failed_gate_criteria:
  [G0.1, G0.2, G0.3]` (no `migration/evidence/*` artifacts exist, OQ-001/
  OQ-010 still OPEN); project `status: BLOCKED` **derived** per docs/11
  (every current-gate Phase 0 row is BLOCKED, none actionable — not a copy
  of the gate result; `ACTIVE` + `gate_result: BLOCKED` remains valid when
  gate-enabling work is actionable).
- `migration/QUEUE.md` migrated to frontmatter + exactly one canonical
  7-column live table (both old tables merged, no rows dropped;
  difficulty/lock-in/review detail preserved in notes below the table).
  Honest normalization per docs/11 migration item 6: Q-001..Q-003
  `TODO -> BLOCKED` with `EXT:legacy-source-access`; Q-004..Q-006
  `TODO -> BLOCKED` with `G0.1; G0.2; G0.3` (docs/02 forbids broad
  discovery before G0 passes — this fixes finding #4's "TODO means two
  things" defect; blockers clear when G0 is re-evaluated PASS); Q-007..Q-010
  keep BLOCKED with prose deps moved into `Depends on`.
- `migration-coordinator.md`: authority precedence, STOP-to-state
  persistence table, generation transaction (equal-generation read,
  artifacts -> QUEUE N+1 -> STATE last N+1), stale/partial-write recovery.
- All six mutating command files got exact `## State updates` sections
  (docs/11's six common rules + per-command row). Note: the task text said
  "5 common rules" but docs/11 lists 6; all 6 were included per doc
  precedence. `migration-status.md` states its read-only schema +
  equal-generation consistency duty explicitly.
- `scripts/validate_scaffold.py` extended (new section only; A-1/A-2
  untouched) with `validate_durable_state()` wired into
  `collect_validation_errors()`: frontmatter/enums/schema-version/
  generation, gate/result/criterion relationships (embedded G0/G2/G3
  criterion registry from docs/02), single canonical live table,
  `Q-###`/`S-###` IDs, dependency resolution + cycles, blocker grammar
  (`OQ-###` / gate criterion / `EXT:` / `HUMAN:` kebab), status invariants,
  STATE list consistency vs current-phase rows, project status vs
  actionability (PAUSED/COMPLETE exempt), DONE artifact existence
  (best-effort, single-path cells only). Issue #13 note left in the section
  comment: its coordinator persistence must reuse this logic, not add a
  second free-form path.
- New `scripts/tests/test_durable_state.py` (74 tests, positive +
  negative for every check above).

Owner adversarial review (before merge, matching #1/#2's diligence), two
rounds, both pushed to PR #57 before any merge:

Round 1 found and fixed one real bug: the project-`status` actionability
invariant only fired when current-phase rows made ACTIVE or BLOCKED the
required value, so a queue with no actionable/blocked current-phase row
(e.g. all DONE) left `status` completely unconstrained — a stale
`ACTIVE`/`BLOCKED` would validate clean. Fixed with the missing branch
(neither is justified; expected `PAUSED`/`COMPLETE`), plus a regression
test. Also deduplicated `_visible_numbered`/`_visible_lines` (two
near-identical fence/HTML-comment skippers); `_visible_lines` now delegates
to `_visible_numbered`.

Round 2 was a formal PR review (5 findings) judged individually against
docs/11 rather than applied wholesale; 4 were real, 1 was already handled:

- **[Fixed]** `Blocker: OQ-###` syntax was checked but never resolved
  against `docs/05-open-questions.md`, so `OQ-999` validated the same as a
  real OQ. `validate_durable_state()` now takes an `oq_ids` param (the same
  set `validate_oq_registry()`/`collect_validation_errors()` already
  compute) and flags unresolved OQ blockers as `missing-ref`; skipped (not
  auto-failed) when the caller doesn't supply a registry.
- **[Fixed]** `DONE` rows weren't checked against the dependency/blocker
  invariants that already applied to `TODO`/`IN_PROGRESS`/`BLOCKED`, so a
  `DONE` row could still declare an unmet dependency or an active blocker.
  Added the same `invalid-invariant` check DONE was missing.
- **[Fixed]** `status: COMPLETE` was fully exempt from the actionability
  check with no invariant of its own, so it could coexist with an open gate
  or unfinished queue rows. Added: COMPLETE requires `current_gate: NONE`,
  `gate_result: NONE`, empty `failed_gate_criteria`, and every queue row
  (not just current-phase) `DONE`.
- **[Fixed]** The `relevant` current-phase row computation used exact
  string match on `Phase`, so a combined-phase row like Q-010's `5-6` would
  silently drop out of `active_queue_items`/`next_queue_items`/
  `blocked_queue_items`/actionability once `STATE.phase` became `5` or `6`
  (this is inert today — current phase is `0` — but was a real latent bug).
  Added `_phase_matches()`: exact match, or state phase inside a
  `low-high` numeric range.
- **[Already covered, not reopened]** The reviewer's concurrent
  stale-write finding (revision identity beyond generation-equality) named
  a real docs/11 requirement, but the coordinator's "Generation transaction"
  section already had a "stop on... revision change detected after initial
  read" line; that line was vague prose with no deterministic mechanism.
  Made it concrete instead of writing new logic: `git hash-object` of
  `STATE.md`/`QUEUE.md` captured at transaction start, re-checked
  immediately before each write (before `QUEUE.md` at old step 3, before
  `STATE.md` at old step 5), abort+restart the transaction on mismatch.

quiet_state()'s default status moved from `COMPLETE` (chosen in round 1,
now itself invariant-bearing) to `PAUSED` (the only status with zero
invariants beyond list-consistency) to keep unrelated fixtures quiet; round
1's `COMPLETE`-specific regression test was updated accordingly, and
dedicated COMPLETE/DONE/OQ/phase-range tests were added instead of
overloading the shared fixture.

Final state on `main`: `python3 scripts/validate_scaffold.py` exits 0;
`python3 -m pytest scripts/tests/ -q` — 262 passed (188 pre-existing green);
`check_doc_links.py` / `check_oq_updates.py` pass. No design gap found that
required stopping; the Q-004..Q-006 blocker choice (failed G0 criteria per
the STOP contract's "applicable gate criterion in Blocker" rule) was the
one judgment call, made within docs/11's already-decided blocker grammar.

Next Track P order per plan: `(#7, #8) -> #5 -> #13 -> #6 -> #9 -> #11`.
Before starting each, redo the "구현 시작 전 체크" 7-item gate in
`ISSUES-PLAN-DRAFT.md` against current `main`. #13 implementation must
reuse this validator/transaction logic. Rule-13 Track P/D authorization
remains in effect and has not been revoked.

## Next session (superseded): Issue #2 done, continue Track P at Issue #14

Issue #2 (A-2 artifact schema/reference validation) is implemented,
reviewed, and merged to `main` (PR #56, squash-merged as `6d60cce`).
Built by opencode (glm-5.3, `--variant low`) in a separate Orca worktree,
same process as Issue #1. It extends `scripts/validate_scaffold.py` per
the merged canonical design `docs/issue-2-artifact-schema-validation.md`:
closed enums (grades, provenance, source types, verification results, OQ
statuses), `BR-###`/`OQ-###` ID formats with per-file BR uniqueness and
global OQ uniqueness, structured reference resolution (BR refs resolve in
the same feature's behavior contract; feature-card `## Open questions`
bullet OQ refs and `### OQ-###` resolved headings resolve in the global
registry), H1-based evidence/characterization instance discovery with
templates/fenced-code/prose never treated as instances, duplicate machine
keys rejected, and all diagnostics aggregated as `path:line [category]`.
A-1 lifecycle parsing untouched; Issue #9 revision-aware checks and
queue/Q-### validation intentionally not implemented (Non-goals).

Repository normalization done (no exemptions added): four `Grade: N/A` →
`Grade: ?` for the `none observed` capture items in
`migration/features/synthetic-demo/characterization-record.md`, and
`verification.md` `Result:` reduced to exact `PASS` with the scope note
moved to a continuation line. `docs/05-open-questions.md` passed as-is.

Adversarial review (owner review before merge, matching PR #55's
diligence) found and fixed one real bug: `CLAIM_MARKER_RE` matched any
bracketed list bullet, so a standard Markdown task-list checkbox
(`- [ ]`, `- [x]`) was misclassified as an invalid `[observed]`/
`[inferred]` provenance marker. Fixed by excluding checkbox states from
the claim-marker check; regression test added
(`test_task_list_checkbox_is_not_a_claim_marker`).

Final state on `main`: `python3 scripts/validate_scaffold.py` exits 0
(A-1 + A-2 clean); `python3 -m pytest scripts/tests/ -q` — 188 passed.
No new lock-in design decisions were made; the checkbox fix was within
the merged A-2 design's already-decided scope (claim-marker check exists
only to validate provenance markers), so no design gate was reopened.

Next Track P order per plan: `#14 -> (#7, #8) -> #5 -> #13 -> #6 -> #9 ->
#11`. Track P/D implementation authorization from AGENTS.md rule 13 is
still in effect and has not been revoked. Before starting #14, redo the
"구현 시작 전 체크" 7-item gate in `ISSUES-PLAN-DRAFT.md` against current
`main` — do not assume the plan's file-line references are still exact.

## Next session (superseded): Issue #1 done, continue Track P at Issue #2

Implementation authorization from AGENTS.md rule 13 for Track P / Track D
(`migration/ISSUES-PLAN-DRAFT.md`) is still in effect — this is not a
one-time release, but it has not been revoked. **Issue #1 is now fully
implemented, reviewed, and merged to `main`** (PRs #54, #55). Track P order
per the plan is `#1 -> #2 -> #14 -> (#7, #8) -> #5 -> #13 -> #6 -> #9 -> #11`;
Track D order is `#23 -> #20 -> (#18, #22 core) -> #22 live adapter -> #21
(deferred)`. Both tracks otherwise remain design-only pending implementation.

Do this first, in order:

1. Re-open Issue #2's "구현 시작 전 체크" in `ISSUES-PLAN-DRAFT.md` (all 7
   items blocking) — confirm `docs/issue-2-artifact-schema-validation.md`
   still matches current `main` and that Issue #1's A-1 parser/structure
   (now in `scripts/validate_scaffold.py`) is the actual foundation to build
   the enum/ID/reference schema layer on top of, per the plan's `P-A` lane
   (`#1 -> #2 -> #9`). Do not add a second lifecycle parser — `feature-card.md`
   frontmatter stays the sole machine-readable lifecycle source.
2. Follow AGENTS.md rule 13 per item: a new lock-in decision the merged
   design doesn't cover reopens that item's design gate, it doesn't get
   decided on the spot.
3. Independent review scales with lock-in risk (RULEBOOK Agent workflow
   #6) — Track D's #20 (guard) and #22 (snapshot/diff) are still the
   highest-risk items in this batch and should get adversarial review
   before merge, whenever Track D implementation starts.

Track 0 (S-001..S-011 legacy-independent redo) is untouched by this
authorization — it remains its own design-only gate per the "What already
exists" section below, unless the user separately authorizes it.

## 2026-08-19 — Issue #1 A-1 feature-artifact validator: implemented, reviewed, merged (PRs #54, #55)

Implemented and merged the A-1 increment of
`docs/08-feature-artifact-validation.md` against its merged canonical
design. Two branches, built in parallel by opencode (glm-5.3, `--variant
low`/`--variant high`) in separate Orca worktrees off the same base:

- `hjung3113/issue1-normalize-low` (PR #54, merged): added canonical
  `id/stage/blocked` frontmatter to `migration/features/synthetic-demo/
  feature-card.md` and created the three missing stage-`done` singleton
  artifacts (`legacy-map.md`, `review.md`, `verification.md`), all sourced
  honestly from the feature's existing artifacts — no fabricated legacy
  facts, no fabricated review PASS.
- `hjung3113/issue1-validator-high` (PR #55, merged): extended
  `scripts/validate_scaffold.py` with all 11 "Validator behavior"
  requirements — canonical singleton set + same-basename template drift
  check, feature directory enumeration/name validation, feature-card.md
  frontmatter parsing with duplicate-key detection, id/stage/blocked
  validation incl. done+blocked invariant, cumulative stage file
  requirements, legacy-alias rejection, evidence/supporting files ignored,
  all failures aggregated across all features. Existing scaffold checks
  untouched. New test suite `scripts/tests/test_validate_scaffold.py`.

PR #55 got a real adversarial review round (owner review, not rubber-stamp)
before merge; 3 findings, all confirmed valid and fixed in `5f252ef`:

1. **Blocker** — `/migration-status` integration was deferred as an
   optional follow-up, but it is explicit confirmed scope (Issue #1
   implementation-comment item 8, and `docs/08`'s "`/migration-status`
   integration" section). Fixed: `.opencode/commands/migration-status.md`
   now runs the validator first and surfaces failures as process blockers.
2. **Validation hole** — `parse_feature_card()` silently skipped any
   indented line as if it were blank/comment, so nested/malformed YAML
   under a flat scalar key (e.g. a stray indented `bogus: true`) passed
   undetected. Fixed: indented non-empty, non-comment lines now fail as
   unparseable.
3. **Determinism gap** — a present canonical file short-circuited the
   check for a coexisting legacy alias (`feature.md` / `target-design.md`
   / `verification-report.md`), so canonical and alias could exist
   side by side with divergent content and no detected drift. Fixed:
   alias presence is now checked unconditionally, independent of whether
   the canonical file is also present.

Final state on `main`: `python3 scripts/validate_scaffold.py` passes,
`python3 -m pytest scripts/tests/ -q` — 59 passed. No new lock-in design
decisions were made; all three fixes were within `docs/08`'s already-merged
contract, so no design gate was reopened.

Remaining open item, not a blocker for #1 itself: verification.md (the
formal verifier pass) for this increment has not been run as a separate
step — the adversarial review above stood in for it this round. Next
session doing Track P should decide whether Issue #1 needs a standalone
`verifier` pass before being considered fully closed, or whether the
review + CI green + 59 passing tests is treated as sufficient given its
risk level (validator/tooling change, not DB/production-safety).

## 2026-08-18 — Issue #20 DB execution safety design merged; implementation still gated

Issue #20 was checked against the actual DB analyzer/skill, current DB tooling
plans, and the already merged Issue #18/#19/#22/#23 contracts, then reviewed
adversarially as a design-only task. The production-write blast-radius risk is
real, but the issue's literal keyword/profile-name guard is not a sufficient
authorization boundary.

The canonical design is `docs/12-db-execution-safety-contract.md`, merged
through PR #49 as `2e6f32c805881d6c1549bedabfafa80e193ef1ca`. It consumes
Issue #23's canonical `mssql-prod-ro`, `mssql-test-rw`, and
`postgres-test-rw` profiles rather than inventing another connection contract.
Production is a read-only evidence source; write capability requires canonical
`test + read-write` metadata plus runtime attestation that the actual
engine/server/database exactly matches the approved test target. Mutation, DDL,
stored-procedure execution, unknown/mixed batches, and rollback-wrapped
production mutations fail closed before driver execution.

`docs/01-architecture.md` and `migration/RULEBOOK.md` were aligned with that
boundary. Server-enforced production read-only permissions and network
separation remain the primary controls; code guarding is defense in depth.
Normal migration tooling must not expose raw writable connections, hazardous
audit records must redact secrets/parameters/rows, and later CI/static checks
must detect direct driver/connection bypasses outside the approved migration DB
boundary.

No `scripts/db/db_guard.py`, DB connector, credentials, profile implementation,
or runtime DB code was added because AGENTS.md rule 13 still gates
implementation. The concrete follow-up requirements were recorded on Issue #20,
which remains open until implementation is explicitly authorized and completed.

## 2026-08-18 — Issue #18 MSSQL read-only inspection design merged; implementation still gated

Issue #18 was verified against the current DB analyzer/skill, DB dependency
report template, Rulebook, scripts, and the newly merged DB connection contract,
then reviewed adversarially as a design-only task. The core inspection-tool gap
is real, although the issue's exact `scripts/` inventory is stale.

The canonical design is `docs/issue-18-mssql-readonly-inspection.md`, merged
through PR #51 as `21efc641958e01797932a7e4de5c1fa090699ae3`. The design
consumes Issue #23's shared `mssql-prod-ro` profile, exposes only a fixed catalog
`SELECT` set, and forbids arbitrary SQL, DDL/DML, `EXEC`, DB-object/job execution,
and application-row export. Catalog, module-definition, SQL Agent job, and
job-step-text completeness are independent so hidden/unavailable metadata cannot
be mistaken for absence.

`docs/01-architecture.md`, `migration/RULEBOOK.md`, and
`docs/templates/db-dependency-report.md` were aligned with the same boundary.
Raw operational definitions/job commands stay in an approved local/secure
capture rather than being automatically committed; Git keeps reviewed facts,
completeness, hashes/references, and only policy-approved minimal excerpts.
OQ-013 remains OPEN until Phase 1 obtains and analyzes real MSSQL evidence.

No `scripts/db/mssql_inspect.py`, DB driver/helper, `.opencode` agent/skill, or
live DB implementation was added because AGENTS.md rule 13 still gates
implementation. The exact later implementation and validation scope is recorded
on Issue #18.

## 2026-08-18 — Issue #22 DB snapshot/diff contract designed and merged; implementation still gated

Issue #22 was verified against the actual verifier diagram, evidence strategy,
`DbAssertionPort`, parity-verification skill, and verification template, then
reviewed adversarially as a design-only task. The missing DB before/after
capture/diff path is real, but a literal whole-database JSON/CSV diff would be
an unreliable parity oracle across MSSQL and PostgreSQL and would create new
safety/data-leak risks.

The canonical design is `docs/issue-22-db-snapshot-diff-contract.md`, merged
through PR #48 as `f73fe42dfe981ebc80ccdc98b1c804c43a07bbc0`.
`docs/03-evidence-and-verification.md` and `docs/templates/verification.md`
were aligned with it. The default parity object is now a feature-scoped logical
subject's legacy `before -> after` delta versus the target `before -> after`
delta, with explicit projections, stable keys, parameterized queries, hard row
bounds, canonical typed JSON, and comparison semantics owned only by the
behavior contract/Rulebook.

The design also requires fail-closed read-only capture, keeps raw DB row
snapshots outside Git and out of v1 Markdown rendering, defines unambiguous
snapshot hashing/pairing, and makes the DB judge negative control a staged
snapshot/delta mutation rather than a DB mutation. Provisioning/write-safety
work remains separated under Issues #18-#21. No DB script, driver, judge adapter,
or `.opencode` implementation was added because AGENTS.md rule 13 still gates
implementation. The exact follow-up implementation scope is recorded on Issue
#22, which remains open.

## 2026-08-18 — Issue #17 Superpowers pinning design merged; implementation still gated

Issue #17 was re-checked against current `main`. The original floating-branch
defect had already been partially addressed by pinning release tag `v6.3.0`,
so the stale issue text was not applied literally. Adversarial review found two
remaining gaps: Git tags are movable, and `scripts/validate_scaffold.py` does
not enforce the pinning invariant it is cited to validate.

PR #47 rewrites the Superpowers policy in `docs/06-tooling-decisions.md` and
OQ-024 in `docs/05-open-questions.md`. The approved reproducibility boundary is
the immutable commit `b36e0829c6d0140e93cfef2ca599b1b07d4a7797`, resolved
from annotated tag `v6.3.0`; the tag remains human-readable release metadata.
The design also defines explicit upgrade/rollback behavior and a future
fail-closed validator rule requiring a full 40-character commit SHA.

No `opencode.json` or validator implementation was merged because Issue #17 is
Medium and AGENTS.md rule 13 keeps implementation behind explicit user
authorization. The exact implementation steps and positive/negative validation
cases are recorded on Issue #17. PR #47 merged as
`a995f16c8f70d6b8bc06057eed0b329d1d761a21`.

## 2026-08-18 — Issue #11 judge self-check design merged; implementation still gated

Issue #11 was verified against the current parity-verification skill and
verifier agent and reviewed adversarially as a design-only task. The reported
failure mode is real: both operational instructions still weaken judge
self-validation with `where practical`.

The literal fix of deleting those words was rejected as insufficient. The
existing S-011 synthetic mutation test validates only the composite-judge
skeleton; it does not validate future feature-specific adapters/manual
procedures, required-source sets, comparison/normalization rules,
fixture/schema/environment versions, or judge revisions.

PR #43 therefore makes negative control mandatory for the effective judge
configuration in `docs/03-evidence-and-verification.md`, adds auditable
self-check fields to the canonical `docs/templates/verification.md`, and adds
the verifier invariant to `migration/RULEBOOK.md`. A safe isolated known-wrong
mutation must be material under declared comparison semantics and must be
rejected by every declared detector. A missing safe control is `BLOCKED`, not a
waiver. Prior self-check evidence is reusable only for an identical recorded
configuration fingerprint.

No `.opencode` skill/agent implementation was changed because AGENTS.md rule 13
still gates implementation. The exact follow-up changes and regression tests
are recorded on Issue #11. PR #43 merged as
`85dbdac024043be7106cfd9983fb63d16651e865`.

## 2026-08-18 — Issue #14 durable-state protocol designed and merged; implementation still gated

Issue #14 was re-checked against the actual `migration/STATE.md` and
`migration/QUEUE.md`, the latest phase-gate, command, STOP, artifact-schema,
and artifact-naming designs, then reviewed adversarially as a design-only task.
The literal enum-only fix was rejected because it would still leave two queue
schemas, ambiguous actionable-vs-blocked work, no crash-resumable
`IN_PROGRESS`, gate/project `BLOCKED` conflation, and no way to detect a stale
or partially written cross-file state update.

The canonical design is `docs/11-durable-state-protocol.md`, merged through PR
#41. It defines machine-readable STATE/QUEUE schemas, one canonical queue table,
`TODO | IN_PROGRESS | BLOCKED | DONE`, explicit blocker/dependency references,
legal transitions, source-of-truth precedence, shared transaction `generation`,
ordered writes, and deterministic partial-write recovery. A key correction is
that phase `gate_result` and operational project `status` are separate: a gate
may be `BLOCKED` while the project remains `ACTIVE` because gate-enabling work
is still actionable. `docs/02-migration-pipeline.md` and
`docs/10-command-execution-contract.md` were reconciled to that rule.

Issue #13 remains authoritative for STOP cause/payload/OQ deduplication/routing;
Issue #14 owns the exact QUEUE/STATE fields, transitions, and transaction used
to persist those results. No `migration/STATE.md`, `migration/QUEUE.md`,
`.opencode` command/coordinator, validator, or CI implementation was changed.
The concrete future implementation steps are recorded on Issue #14 and remain
gated by AGENTS.md rule 13.

## 2026-08-18 — Issue #13 STOP contract designed and merged; implementation still gated

Issue #13 was checked against the actual eight agent definitions, the current
permission model, feature lifecycle contract, routing/skill execution
contracts, and phase-gate failure rules. The reported failure mode is real,
but the literal recommendation would violate current ownership: read-only
specialists cannot edit shared state, `blocked` is separate from lifecycle
`stage`, and a feature-local blocker must not automatically make project state
BLOCKED.

The canonical design is `docs/11-stop-condition-contract.md`, merged through PR
#40 and linked from `docs/01-architecture.md`; `docs/02-migration-pipeline.md`
was reconciled with the same persistence semantics. `AGENTS.md` remains the
source of truth for the seven STOP conditions. The later implementation should
assign stable `SC-01..SC-07` IDs, generate a managed local `## Stop conditions`
block into all eight agent files, and make CI reject missing/drifted copies.
Specialists return one common STOP payload; `migration-coordinator` owns OQ
dedup/allocation, safe partial-artifact persistence, feature `blocked`, affected
queue status, and project-state updates according to blocker scope. Missing
artifacts or pending approval do not manufacture open questions.

No `.opencode/agents`, `AGENTS.md`, sync script, or validator implementation was
included in PR #40 because AGENTS.md rule 13 still gates that implementation.
The concrete later implementation steps are documented in the design and in
Issue #13's implementation comment.

## 2026-08-18 — Issue #15 artifact naming/location contract aligned

Issue #15 was re-checked against current `main`, not implemented from its stale
snapshot literally. Earlier Issue #1/#4 work had already established
`feature-card.md`, `legacy-map.md`, `target-feature-design.md`, `review.md`, and
`verification.md` as durable feature names; the remaining singleton mismatch
was the verification template still being named `verification-report.md`.

The canonical contract in `docs/08-feature-artifact-validation.md` was rewritten
adversarially to distinguish singleton feature artifacts from repeatable record
templates. Singleton template basenames must exactly match durable feature
basenames, so the verification template is now `docs/templates/verification.md`
and verifier/parity-verification guidance points to it. Old singleton aliases
(`feature.md`, `target-design.md`, `verification-report.md`) are explicitly
non-canonical and should not be accepted as substitutes.

`evidence-record.md` is intentionally not treated as a singleton. Feature-scoped
records persist under `migration/features/<feature-id>/evidence/<evidence-id>.md`;
project-wide/reusable records persist under `migration/evidence/<evidence-id>.md`.
Both migration README files, the evidence template, and evidence-grading skill
now state this rule so low-reasoning agents do not have to infer placement.

Issue #1's stricter validator/sample normalization remains separate work; this
change only makes its future required-file/template checks deterministic.

## 2026-08-18 — Issue #6 skill execution-contract design completed, implementation still gated

Issue #6 was verified against the current skills and reviewed adversarially as
a design-only task. The literal recommendation to add paths plus a generic
if-then to each skill is insufficient because routing, write permission,
persistence ownership, and lifecycle mutation are separate concerns.

The canonical design is now `docs/10-skill-execution-contract.md`, linked from
`docs/01-architecture.md`. `docs/09-agent-skill-routing.md` remains authoritative
for which role/skill owns the next artifact; the Issue #6 contract defines the
selected skill's exact durable inputs/outputs, feature-vs-project scope,
BLOCKED/PARTIAL/conflict branches, and read-only persistence handoff.

Skills do not independently advance `migration/STATE.md`, `migration/QUEUE.md`,
or feature lifecycle metadata. Read-only specialists return complete artifact
bodies to `migration-coordinator` for canonical persistence. Material
implementation-time design deviations reopen the design gate instead of
silently rewriting approved design. The later implementation must preserve
Issue #5 command ownership, Issue #7 routing, Issue #8 write permissions,
Issue #9 grade transitions, Issue #10 provenance, and Issue #11 judge
self-check semantics.

No `.opencode/skills/*/SKILL.md` or migration application code was changed in
this design pass. The design itself was merged through PR #36; this handoff
entry was applied afterward on `main` because concurrent sessions were editing
this single shared file and caused PR conflicts.

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

## Track 0 — S-001..S-011 redo (still design-only, separate gate)

Originally: an independent audit found S-001..S-011 were built backwards
(implementation dispatched first, design decisions made on the spot,
scope creep during self-review). AGENTS.md rule 13 was added in response,
and the user ordered a redo of S-001..S-011 as design-doc elaboration only.

Status check needed: the extensive per-issue design work logged above this
section already touched much of the same surface this redo targeted
(RULEBOOK Backend/Agent-workflow sections, ADR-0004/0005/0006-adjacent
docs, characterization/judge-verdict sections). Whether that fully
satisfies the original redo instruction, item by item, has not been
independently re-audited — do not assume it's done without checking
current `migration/RULEBOOK.md`, the ADRs, and
`docs/templates/pilot-selection-rubric.md` (last known issue: invented
numeric weights not grounded in any doc) against the original redo scope
below before treating Track 0 as closed.

This redo remains gated separately from the Track P/D implementation
authorized above — the user has not released rule 13 for Track 0.

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
