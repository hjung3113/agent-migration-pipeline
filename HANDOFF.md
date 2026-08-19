# Handoff

Single handoff file for this repo. **Always update this file in place — do
not create dated/numbered handoff files.** See AGENTS.md "Handoff rule."

Last updated: 2026-08-20

## Next session: Issue #14 implemented, continue Track P at (#7, #8)

Issue #14 (durable-state protocol) is implemented in worktree
`wt-issue14-durable-state` (this branch) against the merged canonical design
`docs/11-durable-state-protocol.md`, per the owner's explicit rule-13
authorization for #14 only. All 8 implementation requirements done as one
pass:

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
- New `scripts/tests/test_durable_state.py` (64 tests, positive +
  negative for every check above).

Owner adversarial review (before merge, matching #1/#2's diligence) found
and fixed one real bug: the project-`status` actionability invariant only
fired when current-phase rows made ACTIVE or BLOCKED the required value,
so a queue with no actionable/blocked current-phase row (e.g. all DONE)
left `status` completely unconstrained — a stale `ACTIVE`/`BLOCKED` would
validate clean. Fixed with the missing branch (neither is justified;
expected `PAUSED`/`COMPLETE`), plus a regression test. Also deduplicated
`_visible_numbered`/`_visible_lines` (two near-identical fence/HTML-comment
skippers); `_visible_lines` now delegates to `_visible_numbered`.

Final state: `python3 scripts/validate_scaffold.py` exits 0;
`python3 -m pytest scripts/tests/ -q` — 252 passed (188 pre-existing green);
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
