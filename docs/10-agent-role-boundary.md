# Migration Designer / Implementer Role Boundary Design

Issue: #8 — `migration-designer` and `implementer` currently both have `permission.edit: ask`, so the intended design/implementation separation is not mechanically enforced for direct edits.

This document is **design-only**. Under `AGENTS.md` rule 13, the agent frontmatter, validator, CI, commands, and runtime configuration are not changed in this pass. Implementation requires a later explicit user instruction that the design is done and building may start.

## Goal

Make `migration-designer` able to persist only the canonical target design artifact while making source/test/configuration implementation impossible from that role through OpenCode's built-in mutation paths.

The boundary must be enforced by runtime permissions where OpenCode can express it, not merely by prose instructions that a low-reasoning model may ignore after an approval prompt.

## Current-state verification

The issue is valid against the current repository.

- `.opencode/agents/migration-designer.md` has `edit: ask`, `bash: deny`, and `skill: allow`.
- `.opencode/agents/implementer.md` has `edit: ask`, `bash: ask`, and `skill: allow`.
- `opencode.json` grants global `task: allow`, `edit: ask`, and `bash: ask`; agent-specific rules override/merge with those global defaults.
- Analyzer/reviewer/verifier roles already use `edit: deny`, so the repository already treats permission frontmatter as the intended technical boundary rather than relying only on prose.
- The canonical design artifact is `migration/features/<feature-id>/target-feature-design.md`, not the stale `target-design.md` name mentioned in the issue example.

## External capability verification

OpenCode's current permission documentation supports granular per-resource rules for `edit` and per-agent overrides. The repository's current configuration uses the V1-style `permission` / `bash` / `task` field names, and the documented V1 object syntax supports path-pattern-to-effect mappings such as a broad deny followed by a narrow allow/ask exception.

Relevant documentation:

- https://opencode.ai/docs/permissions/
- https://opencode.ai/docs/agents/

The same documentation states that matching rules are ordered and the last matching rule wins. This makes a deny-all-first, narrow-exception-second policy expressible without an external orchestration layer.

If this repository later upgrades to OpenCode V2 configuration (`permissions`, `shell`, `subagent` naming), that syntax migration is a separate compatibility change and must not be mixed into issue #8.

## Adversarial findings

### 1. The literal issue recommendation is too weak if it only adds prose

Adding "designer edits documentation only" to the prompt improves intent but does not close the defect. With `edit: ask`, the designer can still request approval for a React component, FastAPI module, SQL migration, test, or configuration file. An operator approving the prompt would then bypass the intended phase boundary.

Therefore the primary control must be the permission rule; prose is only a second layer explaining what the role should do when a denied change is needed.

### 2. Path-granular edit restriction is available now

The issue suggested adding an open question if OpenCode could not restrict edits by path. That open question is unnecessary: current OpenCode documentation supports granular edit rules keyed by path patterns.

The design should therefore use the capability rather than leave the role boundary intentionally unenforced.

### 3. The canonical writable path must use the repository's actual artifact name

The designer's durable output is:

```text
migration/features/<feature-id>/target-feature-design.md
```

Allowing `docs/**` would be too broad because it would let the designer change architecture docs, templates, open questions, or other process policy. Allowing all Markdown would be broader still and would make the boundary depend on file extension rather than artifact ownership.

The exception must target only the canonical feature design artifact.

### 4. `bash: deny` is part of the boundary, not an unrelated convenience

A file-edit restriction is ineffective if the same role can use shell commands to rewrite files. The existing `bash: deny` on `migration-designer` is therefore correct and must remain.

Implementation must not relax `bash` to `ask` merely because direct `edit` becomes narrower.

### 5. Global `task: allow` creates a delegation bypass

The direct-edit defect has a second path that the issue text does not mention. `opencode.json` grants `task: allow`, while `migration-designer` does not currently override it.

If the designer may dispatch arbitrary subagents, it can preserve its own read/write restrictions while asking a write-capable `implementer` to perform the implementation. That still violates the design/implementation phase boundary.

For the role boundary to be meaningful, `migration-designer` must explicitly set `task: deny`. The coordinator remains the role that delegates design and implementation phases.

This is not a redesign of all specialist-agent task permissions; it is a necessary anti-bypass rule for the exact designer boundary covered by issue #8.

### 6. Designer must not own lifecycle/state updates

Even though `feature-card.md`, `migration/QUEUE.md`, `migration/STATE.md`, and `docs/05-open-questions.md` are documentation/state files, they are not designer-owned outputs.

Allowing the designer to update them would let it advance its own lifecycle stage, clear blockers, or rewrite unknowns while producing a design. Those responsibilities belong to `migration-coordinator`.

The designer should return requested state/open-question changes to the coordinator rather than writing them directly.

### 7. Implementer should not receive the same static path restriction

`implementer` legitimately needs to modify different frontend, backend, test, migration, and configuration paths depending on the approved feature design. A single static glob comparable to the designer's one-file output would either block valid implementation or become so broad that it adds little value.

For issue #8, `implementer` therefore keeps `edit: ask` and `bash: ask`. Its scope is bounded by the approved `target-feature-design.md`, the explicit user implementation gate, and later independent review/verification.

This asymmetry is intentional: the two agents no longer have equivalent write authority because their responsibilities are not equivalent.

### 8. The simple wildcard is not a feature-directory schema validator

OpenCode's simple `*` wildcard can match path separators. The proposed pattern therefore means "a file named `target-feature-design.md` somewhere under `migration/features/` matching the whole pattern", not a mathematically strict one-segment feature directory check.

That is acceptable for this boundary because the permitted filename remains the canonical design artifact, while the feature-directory shape is governed separately by the feature artifact contract in `docs/08-feature-artifact-validation.md`.

Do not expand the permission rule to broader Markdown paths to compensate for this limitation.

### 9. Future write-capable MCP/plugin tools need their own denial

Issue #8 concerns the repository's current built-in mutation paths. If a future MCP/plugin introduces a write-capable tool that is not governed by `edit`, `bash`, or `task`, the designer policy must explicitly deny that tool as part of the plugin adoption review.

No such additional write tool is configured in the current `opencode.json`, so this is a future compatibility rule rather than current implementation scope.

## Decision

When implementation is explicitly approved, change only `migration-designer`'s role permissions and role text for this issue. Do not add duplicate global agent permission configuration to `opencode.json`.

Target frontmatter design:

```yaml
permission:
  edit:
    "*": deny
    "migration/features/*/target-feature-design.md": ask
  bash: deny
  task: deny
  skill: allow
```

Rules:

1. Put the catch-all edit denial before the narrow design-path exception because the last matching rule wins.
2. Keep the design-path effect as `ask`, not `allow`; writing the design artifact still requires the existing operator approval step.
3. Deny every other direct edit without offering approval.
4. Keep shell execution denied.
5. Deny subagent delegation from `migration-designer` so implementation cannot be proxied through `implementer`.
6. Keep `implementer` permissions unchanged for A-6.
7. Do not add a new OQ for path restrictions because support is confirmed by current OpenCode documentation.

## Artifact ownership after implementation

| Artifact / action | `migration-designer` | `migration-coordinator` | `implementer` |
| --- | --- | --- | --- |
| Read behavior/evidence/design inputs | yes | yes | yes |
| Write `target-feature-design.md` | `ask` | may persist/handoff when needed | no design ownership |
| Write `feature-card.md` stage/blocked state | deny | owner | no |
| Write queue/state/open questions | deny | owner | no direct ownership |
| Edit frontend/backend/DB implementation | deny | orchestration only | `ask`, after gate |
| Edit tests/configuration for implementation | deny | orchestration only | `ask`, after gate |
| Run shell commands | deny | `ask` | `ask` |
| Dispatch subagents | deny | owner | unchanged by A-6 |

## Runtime flow

```text
migration-coordinator
        |
        | delegate design
        v
migration-designer
        |
        | may ask to write only
        v
migration/features/<feature-id>/target-feature-design.md
        |
        | return blockers / requested state changes
        v
migration-coordinator
        |
        | explicit user implementation gate
        v
implementer
        |
        v
approved code / tests / configuration paths
```

The designer cannot transition from the design box to the implementation box by editing source directly, running shell commands, or dispatching the implementer itself.

## Failure behavior

After implementation of this design:

- An attempt by `migration-designer` to edit `migration/features/example/target-feature-design.md` should produce an approval request.
- An attempt to edit `target/frontend/...`, `target/backend/...`, DB migration files, tests, `opencode.json`, templates, queue/state, or another feature artifact should be denied without an approval path.
- An attempt to run a shell command should be denied.
- An attempt to delegate to `implementer` should be denied.
- If a design requires another artifact to change, the designer should return a requested change/blocker to `migration-coordinator` instead of performing it.
- The coordinator may then persist process-state changes or, after the separate explicit user gate, dispatch implementation.

## Implementation plan after explicit approval

1. Update `.opencode/agents/migration-designer.md` frontmatter to the granular `edit` object plus `task: deny`, preserving `bash: deny` and `skill: allow`.
2. Update the designer's artifact contract/procedure text to state that its only direct durable write is `migration/features/{feature-id}/target-feature-design.md` and that all other requested changes are returned to the coordinator.
3. Leave `.opencode/agents/implementer.md` and top-level `opencode.json` unchanged for this issue unless implementation testing proves the documented override semantics do not work in the installed OpenCode version.
4. Run existing repository guards.
5. Exercise the permission boundary in OpenCode with one expected-ask edit, at least one expected-deny source edit, a shell attempt, and a subagent-delegation attempt.
6. If the installed OpenCode version rejects the documented V1 granular syntax, stop implementation and record the exact version/schema mismatch instead of weakening the boundary back to prose.

## Verification requirements

Implementation is not considered complete from configuration inspection alone. Verify behavior at the permission evaluator boundary.

Minimum checks:

| Check | Expected result |
| --- | --- |
| designer edits `migration/features/demo/target-feature-design.md` | `ask` |
| designer edits `target/frontend/src/...` | `deny` |
| designer edits `target/backend/src/...` | `deny` |
| designer edits `migration/features/demo/feature-card.md` | `deny` |
| designer edits `docs/01-architecture.md` | `deny` |
| designer runs shell command | `deny` |
| designer dispatches `implementer` | `deny` |
| implementer edits an approved implementation path | existing `ask` behavior preserved |
| existing scaffold/doc guards | pass |

A successful edit after an operator manually changes the role or uses a different agent does not invalidate this boundary; the acceptance target is the effective policy of `migration-designer` itself.

## Non-goals

- Redesigning every specialist agent's `task` permission.
- Adding path restrictions for all implementer outputs.
- Changing the global `opencode.json` defaults.
- Migrating the repository to OpenCode V2 configuration syntax.
- Adding a new orchestration/security framework.
- Treating the permission system as protection against a human deliberately editing repository files outside OpenCode.

## Open questions

No new project OQ is required for issue #8. The capability needed for the proposed design is documented by OpenCode today.

The installed OpenCode version should still be recorded during implementation verification if its behavior differs from the current documentation; that would be an observed compatibility defect, not a reason to leave the current design unresolved.

## Acceptance criteria for this design

A-6 design is complete when it specifies all of the following without implementing them in the same pass:

1. the designer's single writable artifact;
2. deny-by-default direct edit semantics with a narrow `ask` exception;
3. preservation of `bash: deny`;
4. explicit `task: deny` to prevent implementation delegation bypass;
5. coordinator ownership of lifecycle/state/open-question writes;
6. intentional retention of implementer's broader `edit: ask` / `bash: ask` authority;
7. runtime verification cases for allowed, denied, shell, and delegation behavior;
8. no unnecessary global permission duplication or new OQ;
9. an explicit statement that implementation remains blocked until the user releases the design gate.
