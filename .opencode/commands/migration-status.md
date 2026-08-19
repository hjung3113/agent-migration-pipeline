---
description: Summarize current migration phase, queue, evidence quality, blockers, and unresolved questions from durable repository state.
agent: migration-coordinator
---

Run `python3 scripts/validate_scaffold.py` first. This is read-only (it does not write anything); do not skip it. If it exits non-zero, treat every reported structural/feature-artifact/durable-state error as a process blocker in this report rather than continuing as if the underlying artifacts are complete.

This command performs the durable-state consistency checks itself and reports them without implicit repair: `migration/STATE.md` and `migration/QUEUE.md` must both parse against the schema in `docs/11-durable-state-protocol.md` and must carry the same positive `generation`. If generations differ, report the partial-write signature and the recovery rule (`QUEUE.generation > STATE.generation` = interrupted ordered write, STATE stale; `STATE.generation > QUEUE.generation` = protocol violation, stop and reconcile from Git history) — but never rewrite either file from this command. It never mutates `migration/STATE.md`, `migration/QUEUE.md`, feature artifacts, or open questions.

Read `migration/STATE.md`, `migration/QUEUE.md`, `migration/RULEBOOK.md`, `docs/05-open-questions.md`, and existing feature artifacts.

Report:

- current phase/gate;
- completed and next actionable queue items;
- P0/P1 blockers, including any `scripts/validate_scaffold.py` failures from the run above;
- evidence quality concerns;
- features by status;
- process/rule issues that should be fixed before more implementation.

Do not infer progress from chat history.
