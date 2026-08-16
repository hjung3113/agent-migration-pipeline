# Tooling Decisions

## Adopt now

### OpenCode native Agents / Skills / Commands

Use as the primary harness because the project is explicitly OpenCode-based and these capabilities are first-class, project-local, Git-trackable, and sufficient for the initial workflow.

### AGENTS.md

Use for concise, always-on migration rules and safety constraints.

### Superpowers

Include as a supporting plugin for disciplined planning, implementation, review, and debugging workflows.

Project-specific migration skills remain authoritative where they differ from generic Superpowers guidance.

Pinned to `v6.3.0` (see resolved OQ-024 in `docs/05-open-questions.md`) rather than tracking the default branch, for reproducibility.

## Defer

### UI Inspector

Potentially useful after React screens exist because it can improve the feedback loop between rendered UI and source components. It does not solve the current inability to observe the legacy WPF UI inside the platform, so it is not a Phase 0 dependency.

### Larger OpenCode orchestration layer

Do not add at the start. Native subagents should be exercised first. Revisit when parallel feature queues are large enough that scheduling, retries, and cross-agent coordination become a measured bottleneck.

### External agent memory

Start with Git-backed durable artifacts: Rulebook, queue, evidence, feature specs, ADRs, and open questions. Add a memory service only if this becomes insufficient.

## Borrow ideas without adding a dependency

### Anthropic code migration kit

Adopt the process concepts:

- front-load rules and verification
- keep queues on disk
- use phase gates
- separate implementers and adversarial reviewers
- make work resumable
- repair the generating process when defect patterns repeat

The target project is a redesign migration, so source-file-preserving rules are not copied directly.

### BKIT-style spec/design/gap concepts

The general sequence `spec -> design -> implementation -> gap/review -> quality gate` is useful, but a Claude-Code-specific plugin is unnecessary in an OpenCode-first environment.
