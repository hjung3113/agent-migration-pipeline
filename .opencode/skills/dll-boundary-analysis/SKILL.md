---
name: dll-boundary-analysis
description: Use when inspecting how the external company platform loads and calls the legacy DLL so the migration can define a compatibility boundary and possible contract harness without guessing host behavior.
compatibility: OpenCode project skill
---

# DLL Boundary Analysis

Inspect:

- assembly/runtime metadata;
- public interfaces/classes/methods;
- construction/init/shutdown;
- sync/async and thread assumptions;
- WPF Dispatcher/STA dependencies;
- callbacks/events/delegates;
- input/output/error contract;
- configuration/logging/resources;
- database connection ownership;
- host-specific SDK dependencies;
- ability to invoke the same surface from a minimal test host.

Output:

1. confirmed contract facts with evidence;
2. unknowns mapped to `docs/05-open-questions.md`;
3. candidate compatibility-boundary options;
4. recommendation on whether a host-emulator characterization harness is feasible.

Do not decide that a C# shim is required until host capabilities are known.
