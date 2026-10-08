# Handoff

Single handoff file for this repo, updated in place (AGENTS.md "Handoff rule"). It holds **current state
only**. Past session logs live in Git: the last long-form version is `git show bef5b43:HANDOFF.md`, and
`git log -p -- HANDOFF.md` has the full history.

Last updated: 2026-10-08

## Now

- **Workflow:** issues run through the `issue-wave-conductor` skill (`.claude/skills/issue-wave-conductor/`,
  merged in PR #70): rule-13 design gate, brief, omp worker, host `verify.sh`, **one** final independent review
  (codex gpt-6.1-sol), one fix round, PR to `main`, user merge.
- **Issue #18 merged** (PR #71, `aa311aa`, issue closed, worktree removed). `main` re-verified: `verify.sh` ALL
  PASS, 680 tests. Live MSSQL validation of the inspector is still pending (needs expected-target values + DBA env).
- **#22 core PR open, waiting on the user's merge**: `scripts/db/db_snapshot_diff.py` (plan
  `migration/ISSUE-22-EXECUTION-PLAN.md`, branch `hjung3113/issue22-core`, worktree
  `~/orca/workspaces/agent-migration-pipeline/issue22-core`). Final review CHANGES-REQUIRED → all 6 findings fixed in
  one round; `verify.sh` ALL PASS, 782 tests. Issue #22 stays open for the live adapter phase (capture via
  `db_guard`, `DbAssertionPort` adapter, negative control moved there by the user, parity-skill wiring).
- **Track D order** (`migration/ISSUES-PLAN-DRAFT.md`): `#23 ✓ -> #20 ✓ -> (#18 ✓, #22 core) -> #22 live adapter ->
  #21 (deferred)`. DB consumers use `from scripts.db.db_guard import open_readonly, open_test_readwrite`.
- **Track P** (#1, #2, #5, #6, #7, #8, #9, #11, #13, #14): merged. Several of these issues are still OPEN on GitHub.
  Check each against its merged PR and close it or record what remains.

## Waiting on the user

1. Real `server_identity` / `database_identity` for each canonical profile (`scripts/db/target_metadata.py` ships
   unresolved by design). The MSSQL `server_identity` must distinguish environments, not be a bare default
   instance name (#20 NF-4).
2. Confirmation that the production credential is read-only at the server/account level (#20 AC2).
3. Approved test infrastructure for live MSSQL/PostgreSQL integration (deferred non-goal of #20 and #18).
4. Whether CI should run `python3 -m pytest scripts/tests/` (631 tests; today only `verify.sh` runs them).

## Known gaps carried forward (non-blocking, deliberately unfixed)

- #9: `validate_grade_transition.py::_parse_history()` duplicates `validate_scaffold.py::_validate_grade_history()`;
  the append-only history check is byte-exact (stricter than the design's typo allowance).
- #20: NF-2 (`SELECT <side-effecting fn>()` classifies `read`; the read-only credential is the control), NF-3
  (the driver-boundary scan covers `scripts/**` only), NF-5 (raw driver exception reachable via `__context__`).
- #6 F10: the skill validator uses a hard-coded skill-name tuple and `_h2_sections()` is not fence-aware.

## Separate gates (not authorized)

- **Track 0** (S-001..S-011 design-only redo): rule 13 is not released. The pilot rubric's invented weights and
  code that predates gated design (`target/backend/`, `migration/judge/`) need re-examination before it closes.
- **Legacy-blocked:** Q-001..Q-003 (`migration/QUEUE.md`) and OQ-001..OQ-010 need legacy source access.
