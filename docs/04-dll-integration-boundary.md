# DLL Integration Boundary

## Confirmed fact

The current legacy functionality is loaded/called by a separate company platform in **DLL/library form**.

## Why this matters

The target backend is Python/FastAPI and the target UI is web-based, so the host contract may not map directly to the target runtime. The integration boundary must be understood before deciding deployment and gradual replacement architecture.

## Design rule

Platform-specific integration must remain outside core business logic.

```text
Company Platform
      |
      v
Platform Adapter / Compatibility Boundary
      |
      +---- business/application APIs ----> FastAPI/Core
      |
      +---- UI navigation/session bridge -> React/Web UI
```

## Candidate architectures

### Option A — Thin compatibility DLL

Keep a minimal C# DLL that satisfies the existing platform contract and delegates to the new web backend.

Potential benefits:

- gradual replacement without requiring host changes first
- clear strangler boundary
- legacy platform contract can be contract-tested separately

Risks/questions:

- process/service availability
- authentication between DLL and FastAPI
- latency and failure semantics
- synchronous host methods mapped to network calls
- host startup/shutdown lifecycle
- deployment/version compatibility

### Option B — Direct web/API integration

Modify the host platform to call the FastAPI service and launch/embed the React UI directly.

Potential benefit: removes the compatibility DLL sooner.

Blocking fact: it is not yet known whether the platform can be changed this way.

### Option C — Hybrid

Use a compatibility DLL for selected integration points while progressively moving functionality behind web APIs.

This may be the safest migration path if host changes are possible but slow.

## What the DLL analyzer must discover

- assembly target framework/runtime
- public types/methods/interfaces
- how the host discovers the DLL
- constructor/init/shutdown sequence
- sync vs async assumptions
- STA/MTA/thread affinity
- WPF Dispatcher dependencies
- callbacks/events/delegates
- return values and error propagation
- file/config/environment dependencies
- DB connection ownership
- logging integration
- whether multiple instances are loaded
- whether the DLL is isolated in-process or out-of-process
- whether a test host/sample launcher exists

## Testability goal

If practical, build a minimal **host emulator / contract harness** that calls the same public DLL surface outside the full platform. This would provide a much better migration judge than UI inspection alone.

This is a goal, not yet a confirmed possibility.
