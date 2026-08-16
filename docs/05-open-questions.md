# Open Questions

Unknowns are first-class migration artifacts. Do not resolve these by assumption.

Status values: `OPEN`, `CONFIRMED`, `NOT-APPLICABLE`, `DEFERRED`.

## P0 — Blocks architecture / verification

| ID | Status | Question | Why it matters |
|---|---|---|---|
| OQ-001 | OPEN | What exact public interface/entry points does the company platform call in the DLL? | Defines compatibility boundary and contract harness. |
| OQ-002 | OPEN | What .NET target/runtime and host process loads the DLL? | Determines compatibility shim/runtime constraints. |
| OQ-003 | OPEN | What is the DLL lifecycle: load, initialize, repeated calls, shutdown, multiple instances? | Affects state, connection, cache, and web-service bridging design. |
| OQ-004 | OPEN | What are the input/output types and ownership rules? | Required for behavior contracts and adapter design. |
| OQ-005 | OPEN | Are callbacks/events/delegates used to communicate back to the platform? | Required for parity and asynchronous behavior. |
| OQ-006 | OPEN | How are errors propagated: exceptions, return codes, result objects, logs, callbacks? | Required for compatibility. |
| OQ-007 | OPEN | Can the DLL be invoked outside the full platform using a test host or small launcher? | Determines whether characterization tests can be automated. |
| OQ-008 | OPEN | Is there a platform SDK/mock/sandbox/test harness? | Could provide the strongest integration oracle. |
| OQ-009 | OPEN | Can the host platform be modified to call HTTP APIs or open/embed a web UI? | Decides whether a compatibility DLL is temporary, permanent, or unnecessary. |
| OQ-010 | OPEN | Which outputs are observable without the full UI: DB, files, logs, callbacks, return values? | Defines the practical verification judge. |

## P1 — Business behavior / data

| ID | Status | Question | Why it matters |
|---|---|---|---|
| OQ-011 | OPEN | What automated tests exist and what business areas do they cover? | Determines baseline evidence strength. |
| OQ-012 | OPEN | Is there CI for the legacy code and can agents run it? | Needed for repeatable parity loops. |
| OQ-013 | OPEN | Which MSSQL stored procedures, triggers, functions, jobs, or views contain business logic? | Prevents business rules being lost during PostgreSQL migration. |
| OQ-014 | OPEN | Are there production-like sanitized datasets or fixtures available? | Needed for characterization and DB parity. |
| OQ-015 | OPEN | Which numerical/analytical outputs require exact equality vs tolerance? | Defines valid comparison semantics. |
| OQ-016 | OPEN | Which workflows are business-critical and should be migrated first? | Needed to prioritize feature queue. |
| OQ-017 | OPEN | Are there known legacy bugs that must not be preserved? | Separates parity from desired behavior. |

## P2 — Deployment / security / operations

| ID | Status | Question | Why it matters |
|---|---|---|---|
| OQ-018 | OPEN | Where can FastAPI/PostgreSQL/React be deployed relative to the company platform? | Defines topology and latency/security constraints. |
| OQ-019 | OPEN | How are users/session/authentication represented by the host platform? | Required for web identity propagation. |
| OQ-020 | OPEN | What network/security restrictions apply to an in-process DLL calling a service? | May rule out a simple HTTP shim. |
| OQ-021 | OPEN | What configuration/secrets mechanism does the current DLL use? | Needed for deployment migration. |
| OQ-022 | OPEN | Are offline/disconnected scenarios required? | A service-based target may behave differently. |
| OQ-023 | OPEN | What rollback/side-by-side deployment mechanism is available? | Required for gradual replacement. |

## P3 — Tooling decisions to validate

| ID | Status | Question | Why it matters |
|---|---|---|---|
| OQ-024 | CONFIRMED | Should Superpowers be pinned to a fixed tag after initial evaluation? | Reproducibility vs rapid updates. |
| OQ-025 | DEFERRED | Does the React phase need UI Inspector MCP? | Add only when visual/component inspection provides real value. |
| OQ-026 | DEFERRED | Is native OpenCode subagent orchestration insufficient at scale? | Only then evaluate a larger orchestration layer. |
| OQ-027 | DEFERRED | Is Git-backed documentation insufficient for long-term agent memory? | Only then add an external memory system. |

## Resolved

### OQ-024 — Superpowers pinning

**Status:** CONFIRMED (2026-08-16)

Pin `superpowers` to a fixed tag (`v6.3.0`, latest at time of decision) in `opencode.json` instead of tracking the plugin's default branch.

**Evidence:** `git ls-remote --tags https://github.com/obra/superpowers.git` — reproducibility outweighs picking up unreviewed upstream changes automatically for a project-local, disk-backed pipeline. Bump the tag explicitly and re-run `scripts/validate_scaffold.py` when upgrading.

## Update rule

When an item is confirmed:

1. change status;
2. record the answer directly under the table or in the relevant design doc;
3. include evidence/source;
4. update any affected Rulebook/design decisions.
