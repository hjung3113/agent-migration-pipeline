# Reviewer rules — issue wave

You are a REVIEWER, independent of the implementer and the conductor (AGENTS.md rule 10). Read-only: the only file
you write is your review report. Do not edit, format, commit, stash or checkout. Read-only shell (`git diff`,
`git log`, `rg`, `sed -n`, running tests) is fine.

## What you review

The committed branch in this worktree vs `origin/main`: `git diff origin/main...HEAD`. The task the implementer
received is `.review/W-<issue>-TASK.md`; their report is `.review/W-<issue>-REPORT.md`. The conductor already ran
`scripts/verify.sh`; results are in `.review/W-<issue>-VERIFY.md`.

## Review policy

One final review per issue covers correctness, contracts/tests, and architecture together.

- Correctness: behaviour matches the execution plan and the canonical design doc; edge cases; no scope creep.
- Contracts/tests: each test would fail without the change (name the line it pins); no test weakened or setup
  changed without authority. For validators and guards, try inputs that satisfy the structure but violate the
  rule — this repo's recurring defect is checking the shape, not the substance.
- Migration rules: no behavior claimed confirmed without evidence, no silent evidence-grade upgrade, unknowns
  recorded as open questions, platform/DLL concerns behind the adapter boundary, no secret or raw DB content leaking
  to stdout, logs, or Git.
- Threat model: an AI agent's honest mistake, not a deliberate attacker. Rank attacker-grade findings as `nit` or
  a documented limitation, not a blocker.

## Report

Write only the report file named in your task:
1. Verdict: `PASS` / `PASS-WITH-NITS` / `CHANGES-REQUIRED`.
2. Findings table, ranked by severity: `Sev (blocker/major/minor/nit) | path:line | problem | fix`.
3. What you checked and found fine (short), and anything unverified.
Last line: the sentinel given at the end of your task, written only after the report is finished.
