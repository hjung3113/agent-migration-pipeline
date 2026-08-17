# Evidence Grade Transition Control Design

Issue: #9 — evidence grades can currently be overwritten without a durable reason or supporting-evidence trail.

This document defines the design only. Changes to `docs/templates/evidence-record.md`, `.opencode/skills/evidence-grading/SKILL.md`, validators, CI, and commands are implementation work and are intentionally not made in this pass under AGENTS.md rule 13.

## Goal

Make evidence-grade decisions auditable and mechanically checkable so an agent cannot silently raise confidence by replacing a single `Grade:` field.

The control must preserve the meaning of the existing A/B/C/D/? model rather than manufacturing artificial low grades merely to create a transition history.

## Current failure mode

The repository already defines the grade meanings and says never to silently upgrade a grade, but the persisted record is only a mutable snapshot:

- `docs/templates/evidence-record.md` has one current `Grade:` field and no grade-decision history;
- `.opencode/skills/evidence-grading/SKILL.md` says not to upgrade without new evidence but gives no ordered procedure for finding and comparing an existing record;
- git history can show that a line changed, but not the business reason for the grade decision or which evidence justified it.

Therefore a low-reasoning agent can replace `C` with `B` after seeing a new artifact without proving that the artifact satisfies the B-grade criterion or recording why the previous decision changed.

## Adversarial findings

The issue identifies the correct defect, but its suggested fix needs tighter semantics.

1. **Do not force every new record to start at `?` or `D`.** `D` already means weak/source-only inference and therefore requires evidence; it is not a safe default. If a record is created from a directly observed runtime capture, assigning `B` initially is correct. Creating a synthetic `? -> B` transition would record an event that never happened.
2. **History must cover every grade change, not only promotions.** A later contradiction may require `B -> C` or `C -> ?`. Omitting downgrades makes the audit trail asymmetric and hides invalidated confidence.
3. **A history table by itself is not enough.** The current `Grade:` field and the last history row can drift unless their equality is an invariant. History rows must also form a continuous chain (`previous To == next From`).
4. **A generic PR/commit link is not sufficient new evidence.** Git is the change audit. The transition must reference the actual evidence artifact, capture, test, log, DB observation, callback, source location, or approved internal evidence location that changes the confidence judgement.
5. **Grade A cannot be obtained by duplicating one source through multiple summaries.** The existing definition requires strong independent evidence. Two generated documents derived from the same runtime capture are one evidentiary source for independence purposes.
6. **Unresolved contradictory evidence must block promotion.** Adding one stronger-looking source cannot silently outrank a contradiction that has not been reconciled.
7. **Transition validation is revision-aware, unlike enum validation.** Issue #2 can validate the current file shape and allowed values, but detecting a promotion requires an explicit base revision. A validator must not guess which historical revision is the comparison baseline.
8. **Record replacement must not bypass history.** If an existing claim is rewritten into a new evidence record instead of updating the existing record, the previous grade disappears. Implementations must preserve stable evidence-record identity for the same claim/scenario.

## Grade ordering for transition detection

For the narrow purpose of deciding whether a grade change is an upgrade or downgrade, use:

```text
? < D < C < B < A
```

This ordering represents confidence strength only. It does not mean higher-grade legacy behavior is more correct, desirable, or suitable for the target system.

A **promotion** moves right in this ordering. A **downgrade** moves left. Reassessing evidence while keeping the same grade is not a grade transition and does not require a new history row.

The grade meanings remain owned by `docs/03-evidence-and-verification.md` and AGENTS.md; this design governs grade lifecycle, not a new grading scale.

## Evidence record contract

An evidence record has two related views of grade state:

1. `Grade:` is the current snapshot used by readers and tooling.
2. `## Grade history` is the append-only decision trail explaining how that snapshot was reached.

The implementation template should use the following logical schema:

```markdown
## Grade history

| Recorded date | From | To | Reason | Evidence refs |
| --- | --- | --- | --- | --- |
| YYYY-MM-DD | — | B | Initial grade from direct runtime observation | path/or/stable-ref |
```

`Recorded date` is kept for self-contained human scanning; git remains the authoritative author/commit history, so the table does not duplicate author or commit fields.

### Required invariants

- The history is append-only for semantic decisions. Do not delete, reorder, or rewrite past grade decisions to make the current state look cleaner.
- The first row uses `From = —` and records the initial grade decision.
- Every later row's `From` equals the preceding row's `To`.
- The top-level `Grade:` equals the final row's `To`.
- `From` and `To` use only `A | B | C | D | ?`, except the first row's `From = —`.
- Every changed grade has a non-empty reason.
- Every promotion has at least one evidence reference that was not part of the prior grade decision and that is sufficient to explain why the higher grade is now justified.
- A downgrade records the contradiction, invalidation, or reassessment that removed support for the previous grade.
- Historical typo/format cleanup may not change the semantic meaning of a past decision. Semantic corrections are recorded explicitly rather than rewriting history.

## Initial grading

A new record is graded from the evidence that actually exists at creation time.

- No usable evidence yet -> initial `?`.
- Weak/source-only inference -> initial `D`.
- Source plus DB/schema/config inference -> initial `C`.
- Direct runtime observation -> initial `B`.
- Strong independent evidence satisfying the existing A criterion -> initial `A`.

The initial history row is `— -> <initial grade>`. There is no requirement to manufacture intermediate grades.

This is materially different from "all records start at `?` or `D`": the latter would turn record-creation mechanics into false evidence history.

## Grade-change procedure

The evidence-grading skill implementation should make the following order explicit.

1. Identify the claim/scenario and locate its existing evidence record before assigning a grade. If the same claim already has a record, update that record rather than creating a replacement that loses history.
2. Read the current `Grade:`, the complete grade history, current evidence references, and `Limitations / uncertainty` including contradictions.
3. Add or reference the new evidence, contradiction, or invalidation first. Do not choose the desired target grade before evaluating the evidence.
4. Re-evaluate the highest grade actually justified by the canonical grade definitions. Unresolved contradictory evidence blocks promotion.
5. If the justified grade is unchanged, keep `Grade:` unchanged and do not append a synthetic transition row. Update evidence/limitations as needed.
6. If the grade changes, append one history row. A promotion must cite at least one newly introduced supporting evidence reference; a downgrade must cite the reason support was weakened or invalidated.
7. Update the top-level `Grade:` in the same repository change and verify it equals the last history row's `To`.
8. Never delete prior grade decisions to simplify the record. If later evidence reverses a decision, record the reversal as another transition.

## Promotion requirements

A promotion is valid only when all of the following are true:

- new evidence exists relative to the prior grade decision;
- the evidence is referenced from the transition row using a stable locator;
- the reason explains which target-grade criterion is newly satisfied;
- unresolved contradictory evidence does not make the higher grade unjustified;
- for `-> A`, the referenced evidence demonstrates the required independence rather than multiple representations of one source.

Lifecycle progress, implementation completion, reviewer preference, or a desire to unblock a gate are never evidence and cannot justify a promotion.

## Downgrade and contradiction handling

Downgrades are first-class transitions, not failures to be hidden.

When contradictory evidence appears:

1. record the contradiction in the evidence/limitations sections;
2. do not promote while it is unresolved;
3. if the contradiction invalidates the current grade, downgrade to the highest still-defensible grade, including `?` when nothing reliable remains;
4. append the downgrade reason and contradiction/invalidation reference to grade history;
5. if the contradiction is later reconciled, a later promotion follows the normal new-evidence rule.

## Evidence reference requirements

A transition reference should resolve to the evidence itself or to an approved locator for it. Examples include:

- repository-relative artifact path plus section/test/capture identifier;
- characterization or evidence record ID;
- test name and persisted output artifact;
- captured DB/log/callback/runtime artifact;
- source location when inference is the evidence class;
- approved internal evidence URI when production-sensitive material cannot be committed.

A PR URL, commit SHA, issue URL, or prose statement alone is change metadata, not evidence, unless it resolves to a concrete evidence artifact that can be reproduced or inspected.

## Mechanical enforcement design

Implementation should be layered because current-state validation and transition validation are different problems.

### Layer 1 — record schema

Extend `docs/templates/evidence-record.md` with `## Grade history` and the fixed columns above.

Schema validation can check without git history:

- grade enum values;
- history presence;
- initial `From = —`;
- row-to-row continuity;
- current `Grade:` equals the final `To`;
- required reason/reference fields.

This can share parsing conventions with Issue #2's enum/schema validation work.

### Layer 2 — agent procedure

Rewrite `.opencode/skills/evidence-grading/SKILL.md` from a prose reminder into the numbered compare-before-change procedure above. The procedure is the primary control for low-reasoning agents; validation is a backstop, not a substitute for the workflow.

### Layer 3 — revision-aware transition check

Promotion detection requires comparing a base revision to a candidate revision. The implementation should use a dedicated transition check or an explicitly revision-aware mode; it must receive a base ref/SHA rather than infer one silently.

For an existing record, a detected promotion should fail or warn when the candidate revision does not also:

- append a matching history transition;
- keep the current grade aligned with the final row;
- provide at least one new evidence reference for the promotion.

For a newly created record, only the initial-row invariants apply; the validator must not invent a pre-existing `?` grade.

Issue #2's enum validator may share the Markdown parser, but the two concerns should not be conflated: static schema validation needs one file state, while anti-silent-upgrade validation needs two revisions.

## Existing-record adoption

If an evidence record predates this control and therefore has a current grade but no history, do not fabricate its unknown past transitions.

On adoption, add one explicit baseline row:

```text
— -> <current grade>
Reason: baseline imported at A-7 adoption; prior transition history was not recorded
Evidence refs: current supporting evidence refs
```

Subsequent changes follow the normal transition rules. The baseline states the limitation instead of pretending the historical sequence is known.

At the time of this design, the repository has the evidence-record template but no instantiated `migration/evidence/*` record requiring backfill, so no current data migration is needed for A-7 design acceptance.

## Implementation boundaries

This design pass does **not** change:

- `docs/templates/evidence-record.md`;
- `.opencode/skills/evidence-grading/SKILL.md`;
- `scripts/validate_scaffold.py` or a new transition checker;
- CI or OpenCode commands;
- existing grade values or definitions.

Those changes are the implementation phase and remain gated by explicit user approval under AGENTS.md rule 13.

## Test requirements for implementation

Implementation tests should cover at least:

- new record initialized directly at each valid grade without synthetic transitions;
- malformed grade/history enums;
- missing history;
- first row with invalid `From`;
- broken row-to-row chain;
- top-level `Grade:` differing from the final history row;
- valid promotion with new evidence ref;
- promotion without a new evidence ref;
- valid downgrade with contradiction/invalidation reason;
- unchanged grade with added evidence and no synthetic history row;
- unresolved contradiction blocking promotion at the skill/process level;
- `-> A` requiring independent evidence semantics in review;
- legacy baseline adoption without fabricated historical transitions;
- revision-aware comparison receiving an explicit base revision.

## Acceptance criteria

A-7 design is complete when:

- every initial grade and later grade change has a durable decision trail;
- initial records are graded from actual evidence rather than forced through `?`/`D`;
- all promotions require newly referenced evidence and a reason tied to the higher-grade criterion;
- downgrades and contradiction-driven reassessments remain visible;
- current grade and history consistency are deterministic invariants;
- static schema validation and revision-aware transition validation are separated cleanly;
- git is used for who/when/change auditing while the record stores why and what evidence justified the decision;
- no implementation is performed before the design gate is explicitly released.
