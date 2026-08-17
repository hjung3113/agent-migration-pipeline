# Tooling Decisions

## Purpose

This document defines which agent/tooling dependencies are allowed in the migration pipeline and how they are controlled.

The goal is not to maximize tooling. The goal is a reproducible, inspectable workflow with the smallest dependency surface that materially improves migration quality.

## Decision rules

1. Prefer OpenCode-native, project-local, Git-tracked mechanisms before adding external orchestration or memory systems.
2. Add a dependency only when it solves a measured workflow gap; do not add speculative infrastructure.
3. Project-specific migration rules, behavior contracts, Rulebook entries, and verification gates are authoritative over generic tool guidance.
4. Executable external Git dependencies must not follow a branch, `HEAD`, or another floating reference.
5. Upgrades are explicit repository changes with review and validation; tools never self-upgrade as an implicit part of normal work.
6. Medium-or-higher lock-in changes remain behind the `AGENTS.md` design gate: approve the design first, then implement in a separate pass after explicit user authorization.

## Adopt now

### OpenCode native Agents / Skills / Commands

Use as the primary harness. These capabilities are project-local, Git-trackable, and sufficient for the initial migration workflow.

Responsibilities:

- Agents: role boundaries and independent review/verification responsibilities.
- Skills: reusable migration procedures.
- Commands: repeatable entry points into those procedures.
- `AGENTS.md`: concise always-on rules and safety constraints.

### Superpowers

Use only as a supporting workflow plugin for planning, implementation discipline, review, and debugging.

It is not an authority for migration semantics. If Superpowers guidance conflicts with this repository's Rulebook, feature contract, verification design, or project-specific skills, the repository rules win.

#### Current implementation state

`opencode.json` currently uses release tag `v6.3.0`. This is better than the original floating branch reference, but it is not the final reproducibility boundary because a Git tag can be moved or recreated.

Upstream verification for the currently selected release:

- release label: `v6.3.0`
- annotated tag object: `86babb696875227929e85420f287d6309374b93f`
- resolved commit: `b36e0829c6d0140e93cfef2ca599b1b07d4a7797`

#### Approved target design

The executable plugin reference should use the immutable commit SHA:

`superpowers@git+https://github.com/obra/superpowers.git#b36e0829c6d0140e93cfef2ca599b1b07d4a7797`

The release tag remains human-readable metadata. The commit SHA is the executable identity.

This document approves that design only. Changing `opencode.json` or validation code is implementation and must occur in a separate pass after explicit user authorization under the repository design gate.

#### Upgrade contract

A Superpowers upgrade is an intentional dependency change, not routine startup behavior.

An implementation pass for an upgrade must:

1. choose the target upstream release deliberately;
2. resolve the release tag to its exact commit SHA;
3. review upstream changes for effects on planning/review/debugging behavior and conflicts with project-specific rules;
4. update `opencode.json` to the reviewed SHA;
5. update this document and OQ-024 with the release-to-commit mapping;
6. run the scaffold validation before merge.

Rollback is the inverse operation: restore the previously reviewed commit SHA and rerun validation. No separate downgrade mechanism is required.

#### Regression guard design

The validation layer should reject a Superpowers Git reference that is missing a full 40-character commit SHA. This makes the no-floating-reference rule executable instead of relying only on reviewer memory.

The validator should check reference immutability only. It should not decide whether a newer release is desirable; version selection remains an explicit review decision.

### DB connection and secret injection contract

Migration DB tooling uses logical connection profiles backed only by fixed process-environment variables. DB scripts accept profile names, never raw connection strings, passwords, arbitrary environment-variable names, or secret-bearing config-file paths.

The initial profiles are deliberately limited to:

- `mssql-prod-ro` -> `MSSQL_PROD_RO_CONN`
- `mssql-test-rw` -> `MSSQL_TEST_RW_CONN`
- `postgres-test-rw` -> `PG_TEST_RW_CONN`

There is no production read-write profile. Missing/unknown configuration fails closed with no fallback. Connection values must not appear in logs, errors, evidence, or committed files.

The full design and Issue #18-#22 integration boundary are defined in `docs/12-db-connection-secrets-contract.md`. OQ-021 remains a separate open question about the legacy DLL's current configuration mechanism.

## Defer

### UI Inspector

Potentially useful after React screens exist because it may improve the rendered-UI-to-source feedback loop. It does not solve the current inability to observe the legacy WPF UI inside the host platform, so it is not a Phase 0 dependency.

### Larger OpenCode orchestration layer

Do not add at the start. Exercise native subagents first. Revisit only when parallel feature queues create a measured scheduling, retry, or coordination bottleneck.

### External agent memory

Start with Git-backed durable artifacts: Rulebook, queue, evidence, feature specs, ADRs, and open questions. Add a memory service only if those artifacts prove insufficient.

## Borrow ideas without adding a dependency

### Anthropic code migration concepts

Adopt process ideas where useful:

- front-load rules and verification;
- keep queues and evidence on disk;
- use phase gates;
- separate implementers and adversarial reviewers;
- keep work resumable;
- repair the generating process when defect patterns repeat.

Do not copy source-preserving migration constraints that conflict with this project's business-intent redesign goal.

### BKIT-style spec/design/gap concepts

The sequence `spec -> design -> implementation -> gap/review -> quality gate` is useful, but a Claude-Code-specific plugin is unnecessary in an OpenCode-first environment.

## Failure modes this policy prevents

- two clones executing different plugin behavior because a branch advanced;
- a nominally pinned release changing because a tag was moved;
- an unreviewed upstream change altering agent behavior between sessions;
- documentation claiming reproducibility without an executable invariant;
- implementation being mixed into the same pass as a medium-risk design decision;
- adding orchestration or memory infrastructure before a concrete need exists.
