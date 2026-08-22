---
name: dll-boundary-analysis
description: Use when inspecting how the external company platform loads and calls the legacy DLL so the migration can define a compatibility boundary and possible contract harness without guessing host behavior.
compatibility: OpenCode project skill
---

# DLL Boundary Analysis

## Inputs

- An explicit feature scope with a validated `FEATURE_ID`, or an explicit project-scoped queue item; do not invent a feature ID for project work.
- [Input] DLL/host evidence, assembly/runtime metadata, platform SDK information, configuration, logs, and approved runtime observations.
- [Input] `migration/features/<feature-id>/feature-card.md` when feature-scoped, plus `migration/features/<feature-id>/legacy-map.md` when the feature map exists.
- [Input] Existing `docs/05-open-questions.md` entries and any relevant project-wide evidence.

## Outputs

- [Output] For feature scope, the report belongs at `migration/features/<feature-id>/dll-boundary-report.md`.
- [Output] For project scope, the report belongs at `migration/evidence/dll-boundary-report.md`.
- [Output] Confirmed contract facts with evidence, unknowns routed to `docs/05-open-questions.md` or the feature card, candidate compatibility-boundary options, and a recommendation on host-emulator harness feasibility.
- For a read-only invoking role, return the complete report/update bodies and the selected canonical destination to `migration-coordinator`; direct persistence is permission-bound.
- Do not decide that a C# shim is required until host capabilities are known.
- This skill never updates `migration/STATE.md`, `migration/QUEUE.md`, or lifecycle metadata.

## Procedure

1. [Input] Resolve feature versus project scope, then read the applicable feature card, legacy map, open questions, and existing DLL/host evidence.
2. [Input] Inspect assembly/runtime metadata and public interfaces, classes, methods, construction/init/shutdown, sync/async, and thread assumptions.
3. [Input] Inspect WPF Dispatcher/STA dependencies, callbacks/events/delegates, input/output/error contract, configuration/logging/resources, and database connection ownership.
4. [Input] Inspect host-specific SDK dependencies and the ability to invoke the same surface from a minimal test host.
5. [Output] Separate confirmed contract facts from unknowns, map material unknowns to their OQ or feature-card destination, and record evidence.
6. [Output] Write or return `migration/features/<feature-id>/dll-boundary-report.md` for feature scope or `migration/evidence/dll-boundary-report.md` for project scope.
7. [Input] Re-check lifecycle, threading, callback, ownership, and host-capability gaps before recommending a boundary or characterization harness.

## Branches

- If required DLL/host evidence or the selected scope is unavailable, return `BLOCKED` and do not fabricate a boundary report or host contract.
- If lifecycle, threading, callback, ownership, or host-capability facts needed for architecture are unknown, return `PARTIAL`/`BLOCKED` and do not choose a compatibility architecture.
- If optional evidence is unavailable but the confirmed surface remains useful, return `PARTIAL` with the missing evidence recorded.
- If sources conflict, preserve both accounts and return `PARTIAL` or `BLOCKED`; do not resolve the host contract by convenience.
- If the unknown is feature-local, route an update for `migration/features/<feature-id>/feature-card.md`; if it is cross-feature or host-wide, route it to `docs/05-open-questions.md`.
- If the selected canonical report already exists, update it in place only when authorized; otherwise return the complete body to `migration-coordinator` without creating an alternate destination.
- `BLOCKED` and `PARTIAL` are skill result labels. The common STOP payload, durable state, queue, and lifecycle remain coordinator-owned.

## Done means

The selected canonical report distinguishes confirmed DLL/host facts from unknowns with evidence, covers callable and lifecycle boundaries plus threading/callback/ownership concerns, records candidate options and harness feasibility without guessing, and is persisted by an authorized role or handed to `migration-coordinator`.
