# ADR-0005: Platform adapter boundary guard (`app.platform`)

- Status: Accepted
- Date: 2026-08-16

## Context

`docs/04-dll-integration-boundary.md` states the design rule "Platform-specific integration must remain outside core business logic", and RULEBOOK Platform/DLL #1–#2 make platform integration an adapter boundary that core business logic must not depend on directly. Until now nothing enforced this: the S-007 import-linter layer contract (`app.api -> app.services -> app.repositories -> app.domain`, run via `uv run lint-imports`) constrains only relationships *among* core layers, and ADR-0004 explicitly deferred the platform boundary to this slice (S-008).

The actual host contract is unknown: OQ-001–OQ-009 (entry points, host runtime, lifecycle, data types, callbacks, error propagation, test host, SDK, host modifiability) are all OPEN, and RULEBOOK Platform/DLL #3 records that whether a compatibility C# DLL is adopted at all is unresolved. S-008 therefore covers the convention and the guard only — not DLL adoption, not adapter implementation.

## Decision

### 1. Namespace: `app.platform`

Create `target/backend/src/app/platform/` as the sole namespace for company-platform/DLL compatibility code. In this slice it contains no implementation — only a package docstring stating its purpose and an empty marker ABC `PlatformPort` marking the future adapter extension point. `PlatformPort` declares no methods because the required surface is unknown (OQ-001); inventing one would be inference, not evidence. Its method surface will be derived from confirmed host-contract entry points.

### 2. Guard: forbidden import contract

Add an import-linter `forbidden` contract next to the S-007 layer contract in `pyproject.toml`:

- `app.api`, `app.services`, `app.repositories`, `app.domain` must not import `app.platform` (or its submodules).
- The reverse direction stays allowed: `app.platform` may import core layers.

If this contract fails, platform/host dependency has leaked into core — that intent is stated in the contract name and the comment above it in `pyproject.toml`.

### 3. `app.api` is also forbidden to import `app.platform`

Judgment call, resolved as **forbidden**, on these grounds:

- The docs/04 dependency diagram points from the Platform Adapter *into* business/application APIs (`Platform Adapter -> business/application APIs -> FastAPI/Core`). The adapter is a **client** of the API, not a dependency of it; the API layer must remain unaware of how requests arrive (DLL shim, sidecar, or direct host calls — OQ-009 undecided).
- RULEBOOK Backend #1/#3: FastAPI endpoints are transport boundaries, and host-platform compatibility logic must stay separate from general application services. If a route imported `app.platform`, any future host-contract change would ripple into the transport layer.
- Host session/identity bridging (OQ-019) would arrive as request data handled by endpoints, not as an import of the adapter.

The one legitimate future wiring point is the composition root (`app.main` or a dedicated bootstrap module), which is deliberately outside both import-linter contracts: something must instantiate an adapter when one exists. If the confirmed host contract ever requires an api/core layer to import `app.platform`, that is an explicit ADR amendment, never a silent contract loosening.

### 4. No platform code before contract confirmation

Until OQ-001–OQ-009 are resolved, no code is placed in `app.platform/` beyond the marker port: no host communication, no process management, no DLL/assembly loading, no host-specific callbacks (RULEBOOK Platform/DLL #2–#3).

## Consequences

- the boundary is enforced (`uv run lint-imports` fails the build), not a convention nobody checks; a platform import from any core layer becomes a CI failure;
- the contract flags direct imports from the four named layers; `app.platform` remains free to depend on core, and the composition root remains free to wire an adapter when one exists;
- extending `PlatformPort` or adding adapter code requires confirmed host-contract evidence plus a decision record; expected follow-ups when OQ-001–OQ-009 resolve: port methods from confirmed entry points, adapter implementation(s), and a contract harness per docs/04 "Testability goal";
- direction asymmetry is intentional and mirrors docs/04: platform depends on core; core never depends on platform.

## Amendments (post-review, 2026-08-16)

Opus-reviewed same day as the initial decision; two changes made before any feature code could depend on the boundary as originally shaped:

- **"Sole namespace" scoped to behavior, not every host-shaped data type.** The original wording would have forced host session/identity bridging (a FastAPI `Depends(...)` parsing a host-issued token) to either live outside `app.platform` or be imported by a route — both violate the letter of the original rule. Resolved: `app.platform`'s sole-namespace claim covers host *behavior* (communication, process management, assembly loading, host callbacks — the same list already in the package docstring), not host-agnostic data contracts. The concrete mechanism that keeps `app.api` unaware of the platform implementation is named explicitly: routes declare a host-agnostic, protocol-typed dependency; `app.main` binds the concrete platform implementation via FastAPI's `app.dependency_overrides`. Without naming that mechanism, "the composition root wires it" was an assertion, not a design.
- **Reverse direction constrained.** `app.platform` was originally free to import any core layer, which would have made it a second, undisciplined entry point into core (bypassing the transport/service discipline `app.api` is held to). `app.platform` is now placed above `app.api` in the S-007 `[tool.importlinter]` layers contract (so no core layer may import it, including indirectly), and a dedicated `forbidden` contract additionally stops `app.platform` from importing `app.repositories` directly — the adapter must route through `app.services` like any other caller. `app.domain` (shared value types, non-behavioral) stays importable from `app.platform`.
- **Composition-root exemption guarded.** `app.main` is still deliberately outside the layer/isolation contracts (something must wire the adapter), but a new `forbidden` contract stops any other module from importing `app.main`, so the exemption cannot quietly turn it into a shared utility hub.
- The S-007 layers-contract name was also corrected: it previously implied strict adjacency ("only depend on the one to its right"), which `type = "layers"` does not enforce — skipping layers is permitted, only upward dependencies are forbidden. Renamed for accuracy, no behavior change.

All four `[tool.importlinter]` contracts (`lint-imports`) plus `pytest`/`ruff`/`mypy --strict` verified green after the amendment.
