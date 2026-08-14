# ADR-0001: OpenCode-native orchestration first

- Status: Accepted
- Date: 2026-08-15

## Context

The migration environment needs specialized agents, reusable procedures, repeatable commands, and durable rules. Multiple third-party orchestration frameworks could provide overlapping functionality.

## Decision

Start with OpenCode-native `AGENTS.md`, `.opencode/agents`, `.opencode/skills`, and `.opencode/commands`. Add Superpowers as a supporting workflow plugin.

Do not add a second orchestration framework until native orchestration has a measured limitation.

## Consequences

- fewer overlapping prompts and routing rules;
- lower setup complexity;
- project behavior remains visible in Git;
- scaling features may require additional tooling later.
