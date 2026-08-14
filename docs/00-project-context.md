# Project Context

## Goal

Migrate an existing internal application from:

- C# WPF
- MSSQL
- Windows/platform-dependent execution

into a web-oriented architecture:

- TypeScript + React + Tailwind CSS
- Python + FastAPI
- PostgreSQL

The objective is not a mechanical rewrite. The migration should preserve business behavior and data integrity while removing unnecessary legacy architecture and technical constraints.

## Known environment constraints

### 1. The legacy component is invoked as a DLL

The surrounding company platform loads/calls the application functionality in library form. This was confirmed during the initial design discussion.

What is **not yet confirmed**:

- exported interface / public methods
- host process and .NET runtime
- load/unload lifecycle
- threading requirements
- input/output contract
- callbacks/events
- error propagation
- whether the DLL can be executed or hosted independently

These are tracked in `docs/05-open-questions.md`.

### 2. The actual legacy UI is difficult to observe

Because the component runs inside another platform, direct visual inspection of the WPF UI may be limited or inconvenient. UI pixel parity therefore cannot be the primary migration oracle.

### 3. Existing tests are incomplete

The legacy test suite cannot be assumed to define full correct behavior. Migration verification must combine multiple evidence types instead of relying on test coverage alone.

## Decisions made so far

1. Use **behavior contracts** rather than UI/source parity as the main migration specification.
2. Capture observable effects such as return values, DB before/after, files, logs, callbacks, exceptions, and generated data.
3. Introduce **characterization/golden-master style tests** where practical to capture current behavior before replacing it.
4. Grade evidence so inferred behavior is not presented as confirmed behavior.
5. Use **business Feature / Vertical Slice** as the migration unit.
6. Separate analysis, design, implementation, review, and verification agent roles.
7. Keep platform-specific DLL concerns behind an adapter boundary.
8. Keep unresolved facts explicitly documented.
9. Build the environment around **OpenCode native Agents, Skills, and Commands**, with Superpowers as a supporting workflow plugin.
10. Defer additional orchestration/memory/UI tools until a concrete need exists.

## Candidate high-level target

```text
Company Platform
      |
      | current contract: DLL
      v
[Platform Compatibility Boundary]   <- shape TBD
      |
      +------> Web UI / React
      |
      +------> FastAPI
                  |
            Business Logic
                  |
              PostgreSQL
```

The compatibility boundary is intentionally unresolved. If the host platform can only call a DLL, a thin C# shim may be required during migration. If the host platform supports HTTP/browser integration, the shim may be unnecessary.

## Why this differs from a normal language port

The Bun Zig-to-Rust case that inspired the workflow largely preserved external behavior while changing implementation language. This project also changes UI technology, backend architecture, database, and potentially deployment/integration boundaries. Therefore:

- migration rules are architecture/business rules, not just language mappings;
- files are not the unit of work;
- verification should focus on business behavior and side effects;
- human sign-off is required where legacy behavior cannot be observed reliably.
