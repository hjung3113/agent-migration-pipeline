# Handoff

Single handoff file for this repo, updated in place (AGENTS.md "Handoff rule"). It holds **current state
only**. Past session logs live in Git: the last long-form version is `git show bef5b43:HANDOFF.md`, and
`git log -p -- HANDOFF.md` has the full history.

Last updated: 2026-10-07

## Now

- **Workflow:** from 2026-10-07, issues run through the `issue-wave-conductor` skill
  (`.claude/skills/issue-wave-conductor/`, adapted from FeedbackOps). It covers the rule-13 design gate, brief,
  omp/codex worker, host `verify.sh`, **one** final independent review, one fix round, a PR to `main`, and the
  user merge. Introduced in **PR #70** (`chore/issue-wave-conductor`), which is open and awaiting "merge it".
- **Issue #18** (MSSQL read-only inspector, `scripts/db/mssql_inspect.py`): **design gate, waiting for the
  user's "구현 시작".** Execution plan `migration/ISSUE-18-EXECUTION-PLAN.md` (108 lines) is committed as `a6821ec`
  on local branch `hjung3113/issue18-plan` (worktree `~/orca/workspaces/agent-migration-pipeline/issue18-plan`,
  not pushed; worker terminals closed). The conductor spot-checked its citations against the code and they hold.
  DAG: T-1 inspector + tests ∥ T-2 `.opencode` db-analyzer/skill ∥ T-3 `.gitignore` → verify → one final review →
  one fix round → PR. Open for the user (plan §6): (1) the PARTIAL vs BLOCKED rule (proposed: some data
  retrieved = PARTIAL, source wholly unavailable = BLOCKED); (2) when the `mssql-prod-ro` expected-target values
  arrive — until then every `open_readonly` fails closed, so tests use fakes/patch seams; (3) the live-validation
  environment (out of scope).
- **Track D order** (`migration/ISSUES-PLAN-DRAFT.md`): `#23 ✓ -> #20 ✓ -> (#18, #22 core) -> #22 live adapter ->
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
