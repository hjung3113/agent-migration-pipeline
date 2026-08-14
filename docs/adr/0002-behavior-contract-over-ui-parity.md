# ADR-0002: Behavior contracts over UI parity

- Status: Accepted
- Date: 2026-08-15

## Context

The legacy WPF component runs inside another company platform and its actual UI may be difficult to observe. Existing tests are also incomplete.

## Decision

Use behavior contracts based on inputs, business rules, outputs, DB changes, files, logs, callbacks/events, and error behavior as the primary migration specification.

Visual/UI parity is supplementary evidence when available, not the main oracle.

## Consequences

- migration can progress even with limited legacy UI access;
- characterization must focus on observable side effects;
- uncertain behavior must be explicitly graded and documented.
