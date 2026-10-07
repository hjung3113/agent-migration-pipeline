# Implementation worker rules — issue wave (read before your task)

**You are the IMPLEMENTATION WORKER, not the conductor.** Edit files directly in this worktree. Do not dispatch
agents. If something is ambiguous, make the smallest reasonable call and record it in your report — except a
design decision the brief leaves open: stop and report it instead (AGENTS.md rule 13, stop conditions SC-01..SC-07).

1. **Read first:** root `AGENTS.md`, the execution plan named in your task, and every design doc it cites.
2. **Run the narrowest checks yourself before you report:** the pytest files you touched or added
   (`python3 -m pytest <files> -q`), `python3 scripts/validate_scaffold.py`, and — if you touched `target/backend` —
   `cd target/backend && uv run pytest <files> && uv run ruff check . && uv run mypy`. Fix what fails. Put the
   commands and results in your report. **Never** run git (commit, stash, reset, checkout, restore), connect to a
   real database, or push; leave all changes uncommitted — the conductor commits and runs the full gates.
3. **Test first.** Add the failing test, then make the smallest change that passes it. One test per acceptance
   criterion; parameterize variants. Do not change the setup, fixtures, or assertions of existing tests unless the
   task says the behaviour they pin is being removed — then say which test and why in the report.
4. Scope is exactly the task file (YAGNI, surgical changes). No unrelated refactors, no speculative options.
   Never mark a behavior confirmed without evidence, never upgrade an evidence grade, and record unknowns as open
   questions rather than guessing. Update any doc the change makes wrong, in the same diff.
5. **Report:** write `.review/W-<issue>-REPORT.md` — files changed (one line why each), tests added (which
   acceptance criterion each covers), existing tests you changed and why, anything not done, open questions.
   Its **last line** is the sentinel from your task. Write the sentinel only when all edits are finished.
6. **Do not call `orca`.** Terminals, worktrees, and orchestration belong to the conductor. If a needed command is
   blocked, finish with the report and state the command and blocker; do not retry it.
