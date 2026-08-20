---
description: Summarize current migration phase, queue, evidence quality, blockers, and unresolved questions from durable repository state.
agent: migration-coordinator
---

## Arguments

This command accepts no arguments:

```text
(empty $ARGUMENTS)
```

Any non-empty `$ARGUMENTS`, including unknown flags, is an invocation error.

## Inputs

Read `AGENTS.md`, `migration/STATE.md`, `migration/QUEUE.md`,
`migration/RULEBOOK.md`, `docs/05-open-questions.md`, and existing feature
artifacts under `migration/features/<feature-id>/`, using the canonical
singleton paths `feature-card.md`, `legacy-map.md`, `behavior-contract.md`,
`target-feature-design.md`, `review.md`, and `verification.md`.

Run `python3 scripts/validate_scaffold.py` first. The command also reads the
same durable state and verifies both files against
`docs/11-durable-state-protocol.md`, including a positive equal
`generation`. It reports a partial-write signature when generations differ:
`QUEUE.generation > STATE.generation` means STATE is stale after an
interrupted ordered write; `STATE.generation > QUEUE.generation` is a protocol
violation requiring reconciliation from Git history and specific artifacts.

## Preconditions

There is no phase prerequisite. The command must be able to read the global
durable inputs and run the scaffold/feature-artifact validator. A validation
or schema error is a process blocker to report, not permission to infer
progress or repair the files.

## Outputs

Produce a read-only report containing:

- current phase and gate;
- completed and next actionable queue items;
- P0/P1 blockers, including validator failures;
- evidence-quality concerns;
- features by lifecycle status;
- process/rule issues that should be fixed before more implementation.

There is no durable output artifact for this command.

## State updates

None. `migration-status` never mutates `migration/STATE.md`,
`migration/QUEUE.md`, feature artifacts, `docs/05-open-questions.md`, gate
fields, feature metadata, queue status, or project status. It does not repair
schema/generation mismatches or infer progress from chat history.

## Failure behavior

For non-empty `$ARGUMENTS`, print the accepted empty syntax, identify that
arguments are unsupported, and make zero durable writes. This is an invocation
error, not a migration blocker.

If the scaffold validator, durable-state parser, or a read fails, report the
exact process blocker and stop the affected summary. Do not rewrite any file,
create an open question, or fabricate a queue/feature/project transition.
Validation failures remain visible to the caller until repaired through the
appropriate owner and normal durable-state protocol.

Open questions are read from `docs/05-open-questions.md`; this read-only
command does not add or deduplicate them. The general OQ rule remains that
only newly discovered unresolved facts affecting behavior, integrity,
platform/DLL constraints, security, deployment, or a design/verification
decision belong in that registry.
