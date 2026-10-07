---
name: issue-wave-conductor
description: Conduct GitHub issues of this migration-pipeline repo to open PRs against main, one issue = one branch = one PR, with omp/codex workers implementing, one final independent review per issue using the shared routing table, and the conductor verifying on the host. Covers the rule-13 design gate, brief writing, launch, watching, host verification, review, ship, and cleanup. Use when the user says "wave 진행", "이슈들 진행해", "다음 이슈", or asks to work through Track D/P issues with workers. Adapted from FeedbackOps' issue-wave-conductor (2026-10-07).
---

# Issue wave conductor (agent-migration-pipeline)

The conductor never writes product code beyond mechanical fixes; workers implement, reviewers judge, the conductor
verifies, commits, and opens the PR. **Merging is the user's call**: open the PR, post the review, and wait for an
explicit "merge it". There is no auto-merge grant in this repo.

## Roles and routing

Read `~/.claude/skills/orca-dispatch-recipes/routing.tsv` for the current roles, runtimes, models and efforts.
The user's session overrides win; pass them with `worker-launch.sh --model/--effort` instead of duplicating
model defaults here. Shared scripts live in `~/.claude/skills/orca-dispatch-recipes/scripts/`:
`worker-launch.sh`, `worker-wait.sh`, and `ship-pr.sh`.

Use the local `scripts/launch-worker.sh` to prepare an issue worktree and launch implementation; use shared
`worker-launch.sh` directly for `fix`, `review-final`, and `review-check`. A report sentinel alone is not
completion: `worker-wait.sh` also checks freshness, the last non-empty line, and worker exit or terminal
idleness. Close a completed worker's terminal immediately; keep its state JSON for the report and cleanup.

## State

- `WAVE_STATE` — a scratch dir (the session scratchpad): worker state JSON (`W-<n>.json`, `W-<n>-FIX<k>.json`,
  `W-<n>-FINAL.json`, `W-<n>-CHECK<k>.json`). Pass `--state-dir "$WAVE_STATE"` on every launch and wait; use
  distinct names, reports, and sentinels for every round.
- `WAVE_BRIEFS` — brief dir, `.review/wave/` in the main checkout (gitignored). `AMP_MAIN` — the main checkout.
- Durable state stays on disk per AGENTS.md rule 12: the execution plan (`migration/ISSUE-<n>-EXECUTION-PLAN.md`),
  `HANDOFF.md`, and PR/issue comments. `.review/` is scratch and is not a substitute.

## Loop per issue

0. **Design gate (AGENTS.md rule 13).** For lock-in risk medium or higher, the first pass produces the design or
   execution-plan artifact only — re-run the 7-item "구현 시작 전 체크" from `migration/ISSUES-PLAN-DRAFT.md`
   against current `origin/main`, record judgment calls with design-doc citations and open questions, commit the
   plan on the issue branch, then **stop and report**. Do not launch implementation until the user explicitly says
   to start building. An implementer may never settle an undecided design point; it goes back to the user.
1. **Brief** (`$WAVE_BRIEFS/<n>-task.md`): re-verify every fact on current `origin/main` (paths, line numbers,
   existing helpers, the owning contract) — issue text goes stale. Sections: *Facts (verified on main)* / *Do* /
   *Acceptance (tests)* / sentinel line. Name the approved surfaces to reuse (e.g. `scripts.db.db_guard`), the
   evidence-grade and open-question rules that apply, what is out of scope, and conductor decisions as
   "final — do not re-litigate". End with `Sentinel (last line of .review/W-<n>-REPORT.md): <!-- W-<n>-DONE -->`.
2. **Launch**: `scripts/launch-worker.sh <n> <slug>`. It delegates to shared `worker-launch.sh` with role `impl`;
   set `WORKER_ROLE=impl-fallback` when Orca hangs, and optionally `WORKER_MODEL` / `WORKER_EFFORT`.
   Parallelise only issues that touch disjoint files; 2–3 in flight is the ceiling while the conductor also verifies.
3. **Wait**: shared `worker-wait.sh --state "$WAVE_STATE/W-<n>.json" --timeout 3600 --poll 30` (run it in the
   background). Act on the exit code: `0` done → verify on the host and close the terminal; `10` failed →
   inspect the report/log and write a repair brief; `11` quota → stop the stalled worker and relaunch in the same
   worktree with shared `worker-launch.sh --role impl-luna` (not `launch-worker.sh`, which creates a new worktree)
   and a task that says the worktree holds partial edits; `12` timeout → read the screen
   (`orca terminal read --screen`), do not treat it as completion or launch a duplicate; `2` usage → fix the args.
4. **Verify on the host**: `scripts/verify.sh <worktree>` — scaffold validation, OQ update rule, doc links,
   `scripts/tests/` pytest, plus `target/backend` / `target/frontend` gates when the diff touches them.
   Mutation-check new tests once (break the fix, see the named test fail, restore). Confirm the diff stays inside
   the brief's file set (`git -C <worktree> diff --stat origin/main`). Then commit the worker's changes yourself.
5. **Fix it yourself only if mechanical** (import order, a typo in a path, a test expectation that pinned removed
   behaviour). Record each in `.review/W-<n>-VERIFY.md`. Anything with judgment → a fix brief
   (`.review/W-<n>-FIX<k>-TASK.md`) quoting the host output, launched with shared `worker-launch.sh --role fix
   --cwd <worktree> --task <abs> --report <abs> --sentinel '<sentinel>' --name W-<n>-FIX<k> --state-dir "$WAVE_STATE"`.
6. **One final review per issue** (reviewer rules: `templates/review-rules.md`, copied to
   `.review/00-REVIEW-RULES.md`). Run host verification **first**, then one independent final review (AGENTS.md
   rule 10: a different model from the implementer, no implementation-session context) with a
   `W-<n>-FINAL-TASK.md` (scope, prior rounds, risks to trace, exact report path and sentinel) and
   `W-<n>-VERIFY.md` (numbers and your own observations to confirm or reject). Launch with shared
   `worker-launch.sh --role review-final ... --name W-<n>-FINAL`. Give every finding a YAGNI pass against the
   threat model (an AI agent's honest mistake, not an attacker): fix the reachable ones, record the rest as
   documented limitations. Batch all fixes into one fix round; the conductor verifies it and ships — no second
   final review. Use `review-check` only for an intermediate check the conductor needs. No review after
   copy-only or mechanical changes.
7. **Ship**: rerun `scripts/verify.sh` after rebasing. Use shared `ship-pr.sh --branch <branch> --base main
   --title '<title>' --body-file <body-file>` **without `--merge`** (body: change, review verdict with applied and
   deferred findings, verification numbers, remaining uncertainty). Post the final review as a PR comment. Wait
   for CI and the user's merge instruction. Pass only finished resources via `--terminal <handle>`; keep the
   worktree until the PR merges.
8. **After merge**: confirm `main` with `scripts/verify.sh "$AMP_MAIN"`, comment and close the issue, remove the
   worktree, and update `HANDOFF.md` in place (committed to Git per AGENTS.md "Handoff rule"). File follow-ups
   (deferred findings, owner decisions) as issues or open questions in `docs/05-open-questions.md`.

## Traps (measured)

- A worktree's `.review/` is gitignored — `launch-worker.sh` copies the brief and rules in.
- `orca worktree create` may fail to return a terminal handle; retry `terminal create`.
- omp workers stall silently on their 5-hour quota; read the worker terminal with `orca terminal read --screen`
  (the stream read shows only the splash) and trust `Provider requested Nms wait`, not the printed reset time.
- If Orca hangs at `runtimeState: starting`, launch with `WORKER_ROLE=impl-fallback` (background `codex exec`).
- An implementer's own self-check is not the independent review (#23 precedent).
- Freshly written validators in this repo repeatedly check the shape, not the substance (PR #66/#67/#68): the
  final-review task must ask the reviewer to try inputs that satisfy the structure but violate the rule.
- Batch rewrites of skill/agent files silently drop conditional clauses and doc references (#61/#62/#64): diff
  those lines against the pre-rewrite version during host verification.
- zsh: never name a variable `path` (tied to `PATH`) or `status` (read-only).
