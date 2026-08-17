# Agent and Skill Routing Design

Issue: #7 — agent trigger conditions, role boundaries, and evidence-related skill selection are ambiguous.

This document defines the design only. Changes to `.opencode/agents/*.md` and `.opencode/skills/*/SKILL.md` are implementation work and remain gated by `AGENTS.md` rule 13 until the user explicitly authorizes implementation.

## Goal

Make routing deterministic enough for a low-reasoning model to choose the correct role and skill without guessing from overlapping keywords.

The routing rule is based on **current pipeline phase + primary artifact/output ownership**, not on loose words such as `evidence`, `unknown`, or `behavior`.

## Adversarial findings

Issue #7 identifies the correct failure mode, but the suggested one-line fixes are not sufficient by themselves.

1. Adding only `## Escalation` does not tell the model when an agent should be invoked, when it should not be invoked, or what artifact it owns.
2. Making the four evidence-related skills mutually exclusive would be incorrect. A single behavior-contract step can legitimately grade an existing claim and register a separate unresolved question.
3. `return to migration-coordinator and STOP` is too broad as a universal rule. A specialist should return normally after completing its role; STOP is required only when a material unknown blocks the current gate.
4. Routing by file type is unsafe. Legacy source analysis can encounter DB objects and DLL boundaries, but those discoveries are references for specialist routing, not permission for one agent to absorb every domain.
5. Reviewer and verifier boundaries need explicit protection: review finds defects against the approved artifacts; verification executes the judge and produces a parity verdict. Neither role may silently repair the implementation or redefine the contract.
6. Frontmatter descriptions are important because they are visible during initial tool/agent selection, but body-level positive triggers, negative triggers, output ownership, and escalation rules are also required for deterministic behavior after selection.
7. Cross-role handoff must stay coordinator-owned. Direct peer-to-peer re-routing by subagents would make queue/state/gate decisions invisible and inconsistent.

## Routing invariants

1. `migration-coordinator` is the only role that owns cross-agent dispatch and phase/gate transitions.
2. Every delegated work item has exactly one **primary agent**, selected by the artifact or decision it must produce.
3. A primary agent may use supporting skills, but supporting skills do not change ownership of the work item.
4. A specialist does not absorb adjacent specialist work. It records the boundary reference and returns it to the coordinator for routing.
5. Unknowns are persisted when material. Work stops only when the unknown blocks the current gate or would force invention of behavior/design.
6. Reviewer and verifier remain independent of the implementer and do not edit the implementation while acting in those roles.
7. A role returning completed work is normal completion, not escalation. Escalation is reserved for out-of-role work, unresolved material facts, contradictions, or approval gates.

## Agent routing contract

| Agent | Invoke when | Primary output ownership | Do not invoke for | Escalate/return when |
| --- | --- | --- | --- | --- |
| `migration-coordinator` | a queue item must be selected, delegated, gated, resumed, or moved between phases | queue/state updates, delegation decision, gate result | deep domain analysis or implementation that belongs to a specialist | human approval is required, policies conflict, or no specialist can resolve a blocking dependency |
| `legacy-analyzer` | legacy C#/WPF/application source must be mapped into business features, call paths, side effects, dependencies, and candidate behavior claims | feature inventory and legacy dependency map inputs | deep MSSQL-resident semantics; host/DLL lifecycle; target architecture design | DB-resident behavior is material -> coordinator routes `db-analyzer`; host/DLL contract is material -> `dll-boundary-analyzer`; semantics remain unknown -> persist uncertainty |
| `db-analyzer` | business behavior or integrity depends on MSSQL schema, queries, procedures, triggers, functions, jobs, transactions, precision, collation, or DB side effects | DB portion of legacy dependency/evidence map and PostgreSQL migration risks | target PostgreSQL design; general application behavior unrelated to DB semantics | required DB evidence is unavailable, behavior crosses into application/host ownership, or a material DB fact is unknown |
| `dll-boundary-analyzer` | a decision depends on the external host/DLL public surface, loading, lifecycle, callbacks, threading, errors, configuration, resource ownership, or host testability | host/DLL boundary facts, dependency map, blocking boundary questions | general business-feature discovery; target web architecture; unrelated DB internals | host behavior cannot be observed, public contract is ambiguous, or the question belongs to general legacy/DB analysis |
| `migration-designer` | an approved behavior contract exists and the feature is ready for target architecture design | `target-feature-design` and explicit legacy structures intentionally not carried forward | discovering legacy behavior; deciding unresolved business semantics; implementation | contract/evidence is insufficient, a material unknown affects design, or approval is missing |
| `implementer` | the target design is approved **and the user has explicitly authorized implementation** | implementation change, tests, recorded deviations | resolving design decisions, changing behavior contracts, approving its own work | implementation requires a new design decision, conflicts with the approved contract/design, or exposes a material unknown |
| `adversarial-reviewer` | implementation is complete enough for independent review before verification | independent review findings/report | implementing fixes; changing approved behavior to match the code; executing the parity judge as the final verdict | a finding requires design/spec correction, missing evidence prevents judging severity, or implementation must return to coordinator/implementer |
| `verifier` | implementation and independent review are complete and the feature is ready for evidence-based parity judgment | verification report and PASS/FAIL/PARTIAL/BLOCKED verdict | code review, implementation fixes, discovering new requirements, redefining comparison semantics after seeing results | judge inputs are missing, comparison semantics are undefined, a mismatch requires implementation/spec correction, or evidence is insufficient |

### Adjacent-domain rule

Specialists may **identify** adjacent-domain facts but must not silently take ownership of them.

Examples:

- `legacy-analyzer` may record that a stored procedure is called, but `db-analyzer` owns the procedure's DB-resident semantics.
- `legacy-analyzer` may record that a public DLL callback is invoked, but `dll-boundary-analyzer` owns host lifecycle/threading/callback-contract analysis.
- `db-analyzer` may identify a PostgreSQL migration risk, but `migration-designer` owns the target schema/application placement decision after the behavior contract is approved.

The coordinator routes these references as separate work only when they are material to the current feature/gate.

## Skill routing contract

The four overlapping skills are separated by their **primary artifact**. They are composable in a fixed workflow; they are not competing synonyms.

| Skill | Invoke when | Primary artifact/output | Do not use as the primary skill for |
| --- | --- | --- | --- |
| `behavior-contract` | discovered legacy behavior must be synthesized into the feature's observable contract before target design | `behavior-contract.md`: inputs, rules, outputs, side effects, errors, comparison semantics, unresolved items | assigning a grade to one already-existing claim; registering one new unknown; post-implementation parity verdict |
| `evidence-grading` | an **existing behavior claim** already has evidence/inference that must receive or update an A/B/C/D/? confidence grade | evidence grade plus supporting evidence record/reference attached to that claim | inventing a new behavior rule; deciding target behavior; creating an open question whose answer is not known |
| `uncertainty-management` | work encounters an **unanswered material question** whose resolution affects a decision, gate, or confidence | open-question entry: exact question, impact, evidence, resolution path, blocking/provisional state | grading a resolved/existing claim as the main task; hiding an unknown behind `?` without tracking the question |
| `parity-verification` | implementation and independent review are complete and legacy/contract expectations must be compared with target observations | verification report and parity verdict using the predefined judge/comparison semantics | discovering/specifying legacy behavior; changing the behavior contract or normalization rules after results are known |

## Skill tie-break algorithm

When more than one skill appears applicable:

1. Identify the artifact the current step is required to produce or update.
2. Select the skill that owns that primary artifact.
3. Invoke supporting skills only for their narrower sub-output.
4. Return all outputs to the primary agent/coordinator; do not let a supporting skill silently change phase or scope.

Examples:

- Source suggests a rule but runtime evidence is unavailable while writing the feature contract: `behavior-contract` owns the step; `evidence-grading` grades the rule as supported by the available evidence, and `uncertainty-management` is also used only if an unanswered question materially remains.
- A runtime capture already confirms an existing rule: use `evidence-grading`; do not create a new behavior contract merely because the word `behavior` appears.
- The question is “does the host invoke this callback on the UI thread?” and no evidence exists: use `uncertainty-management`; the output is an open question, not an evidence record pretending to answer it.
- The target implementation has run and its callback order must be compared with the approved contract: use `parity-verification`; evidence records are inputs, not the primary output.

## Escalation contract

Every specialist agent implementation must have a standard `## Escalation` section. An escalation return must contain:

- `Reason`: `out-of-role | missing-evidence | contradiction | approval-gate | blocking-unknown`;
- `Completed`: work already completed within the role;
- `Evidence`: relevant artifact/evidence references;
- `Unresolved`: the exact remaining question or conflict;
- `Impact`: which artifact, decision, or phase gate is affected;
- `Recommended next route`: agent/skill/human gate requested;
- `Stop current gate`: `yes` or `no`.

`Stop current gate: yes` is required only when proceeding would invent behavior, violate an approval/design gate, or make verification meaningless. Non-blocking unknowns are recorded and returned with `no` so unaffected work can continue.

## Frontmatter description contract

Implementation must make each agent/skill discoverable from its frontmatter description without requiring the model to read every body first.

Descriptions should state, in compact form:

1. the positive trigger (`Invoke when ...`);
2. the primary output/ownership;
3. the nearest confusing exclusion (`Do not use for ...`) where overlap is likely.

The body remains authoritative for the full routing and escalation rules.

## Coordinator dispatch algorithm

For every queue item:

1. determine the current feature phase/gate;
2. state the required primary artifact or decision;
3. choose exactly one primary agent from the agent routing table;
4. pass only the evidence/artifacts needed for that role;
5. let the agent use supporting skills under the skill tie-break algorithm;
6. on normal completion, update durable state and select the next gate;
7. on escalation, inspect `Stop current gate`; route the recommended specialist or human gate without allowing the current specialist to self-expand scope.

## Implementation plan (deferred)

After explicit user authorization to implement this design:

1. update all eight `.opencode/agents/*.md` definitions so frontmatter and body contain deterministic trigger, exclusion, output ownership, and escalation semantics;
2. update the four overlapping skill descriptions and bodies to use the primary-artifact boundaries above;
3. make `migration-coordinator.md` explicitly enforce the coordinator dispatch algorithm and prevent direct specialist scope expansion;
4. preserve reviewer/verifier independence and the existing implementation design gate;
5. add a lightweight static validation/test so future agent definitions cannot silently omit required routing sections.

No `.opencode` implementation changes belong in this design-only PR.

## Acceptance criteria for later implementation

Issue #7 implementation is complete when:

- every agent has an explicit positive trigger, nearest negative boundary, primary output, and escalation contract;
- the four overlapping skills can be selected deterministically by primary artifact;
- behavior-contract work may compose evidence grading and uncertainty tracking without making them mutually exclusive;
- coordinator-owned routing prevents specialists from silently absorbing adjacent roles;
- STOP is used only for a gate-blocking condition, not ordinary handoff;
- reviewer and verifier cannot self-fix or redefine the artifacts they judge;
- static validation detects missing routing sections/descriptions.

## Non-goals

This design does not change the migration phase model, evidence grade meanings, feature artifact filenames, judge verdict semantics, or target architecture. It only defines deterministic routing and escalation boundaries for the existing pipeline.
