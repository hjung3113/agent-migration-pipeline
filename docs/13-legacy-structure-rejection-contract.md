# Legacy Structure Rejection Contract

- Status: Accepted
- Scope: legacy discovery, target design, implementation, and adversarial review
- Related: `docs/adr/0003-feature-based-migration-unit.md`, `AGENTS.md` rules 1-2, `migration/RULEBOOK.md`

## Problem

"Do not copy the legacy architecture" is too abstract to be an executable migration rule. A low-reasoning agent can preserve WPF/C#/MSSQL structure while changing only syntax or framework names.

This contract makes structural carryover explicit, reviewable, and evidence-based without assuming that every similarity to the legacy system is wrong.

## Decision principle

Legacy technical shape is **not a requirement by default**.

A target structure may resemble the legacy structure only when at least one current, evidenced requirement needs that shape:

- an approved behavior-contract rule;
- a verified data-integrity constraint;
- a verified external/platform/DLL contract;
- a verified rollout/compatibility constraint.

"That is how the legacy code is organized", source-level convenience, name familiarity, or speculative future compatibility are not sufficient justification.

If the requirement for retaining a legacy-shaped element is unknown and the decision has medium/high lock-in risk, the design is `BLOCKED` or `PROVISIONAL`; do not preserve the structure "just in case".

## Canonical anti-pattern categories

These IDs are stable review vocabulary. The examples are deliberately generic and must be refined with real Phase 1 evidence when concrete legacy patterns are discovered.

| ID | Legacy structure that must not be carried forward by default | Typical accidental target copy | Retention requires |
|---|---|---|---|
| LSR-01 | WPF window/page/control tree, ViewModel, code-behind, command layout | one React page/component/store/hook per WPF screen/ViewModel/code-behind unit | behavior or host/UI contract that specifically requires the boundary |
| LSR-02 | C# class/service/manager/repository/inheritance boundaries | one FastAPI router/service/repository/module per legacy class or layer | a target responsibility boundary justified independently of the class layout |
| LSR-03 | WPF event, Dispatcher, callback, lifecycle, or command chain | equivalent React handler/hook chain or backend callback chain with the same incidental sequencing | observable ordering/lifecycle semantics or platform contract |
| LSR-04 | MSSQL table/column/view/procedure/trigger organization | one PostgreSQL object per MSSQL object, same schema decomposition, or syntax-only SP translation | data-integrity, migration/rollout, performance, or external-contract evidence |
| LSR-05 | legacy operation/method/stored-procedure granularity | one HTTP endpoint per method/SP or transport contract derived from implementation calls | an approved public/business interaction contract |
| LSR-06 | legacy DTO/entity/class names and field grouping | public API/domain model copied from C# DTO/entity shapes | externally visible contract, data semantics, or current compatibility requirement |
| LSR-07 | host/DLL/WPF glue mixed into business logic | platform callback/assembly/Dispatcher concerns inside FastAPI/domain/application core | none for core logic; required host compatibility must be isolated behind the platform adapter |

Similarity alone is not a defect. **Unjustified similarity is the defect.**

## Required disposition states

Every target-design carryover candidate uses exactly one of these states:

- `REJECTED` — the legacy shape is intentionally not retained; record the target replacement/boundary.
- `RETAINED-JUSTIFIED` — the legacy-shaped element remains because a current evidenced requirement needs it.
- `NOT-APPLICABLE` — the category does not occur in the feature; cite the inspected artifact/evidence supporting that conclusion.
- `BLOCKED` — whether the structure must remain cannot be decided from current evidence.

Do not use bare `N/A`, `same as legacy`, `for compatibility`, or `for safety` as a disposition/rationale.

## Decision procedure

For every applicable LSR category and every concrete legacy carryover candidate discovered for the feature:

1. **Identify the legacy shape.** Cite its source/evidence in `legacy-map.md` or specialist reports.
2. **Separate behavior from implementation.** State what observable rule, integrity rule, or external contract exists independently of that shape.
3. **Ask whether the shape itself is required.**
   - If no evidenced requirement needs the shape, mark `REJECTED`.
   - If an evidenced requirement needs it, mark `RETAINED-JUSTIFIED`.
   - If the answer depends on an unresolved material fact, mark `BLOCKED`.
4. **Design the target boundary from business responsibility.** Do not substitute a framework-equivalent object merely to preserve familiar decomposition.
5. **Record evidence.** `RETAINED-JUSTIFIED` requires an exact behavior-rule ID, OQ resolution, DB evidence, DLL/platform evidence, or other durable source reference.
6. **Review the implementation.** A target diff that introduces a legacy-shaped boundary not present in the approved disposition is a design deviation, not an implementation convenience.

## Artifact contract

### `legacy-map.md`

Discovery records structural facts without turning them into target requirements.

The `Legacy structure observations — not target requirements` section records:

- LSR category;
- concrete legacy structure;
- source evidence;
- whether any business/external requirement appears tied to it: `yes | no | unknown`;
- follow-up needed.

`yes` does not authorize retention. It only means target design must inspect the cited requirement.

### `target-feature-design.md`

`Legacy structures intentionally not carried forward` is a mandatory disposition table.

Requirements:

- cover every canonical LSR ID with at least one row, using `NOT-APPLICABLE` when appropriate;
- add extra rows for multiple material candidates in the same category;
- every `RETAINED-JUSTIFIED` row has a durable requirement/evidence reference;
- every `BLOCKED` row is linked to an open question when the missing fact is real;
- `REJECTED` rows state the target replacement or boundary, not merely "removed".

### `review.md`

Independent review audits both directions:

1. a `RETAINED-JUSTIFIED` item really has sufficient evidence and remains isolated as designed;
2. no new legacy-shaped structure appeared in implementation outside the approved disposition table.

A review cannot pass structural-carryover checks with a generic statement such as "no WPF/MSSQL carryover found"; it must record result and evidence per LSR category.

## Role responsibilities

### `legacy-analyzer`

- discovers and cites legacy structural facts;
- tags relevant facts with LSR IDs;
- does not propose target replacements;
- must not infer that a structure is a requirement merely because it is repeated or central in the source.

### `migration-designer`

- treats this contract as the canonical rejection checklist;
- creates the disposition table before implementation;
- designs from behavior/responsibility first;
- cannot retain a legacy-shaped element without evidence.

### `implementer`

- implements only the approved target structure;
- treats newly required legacy-shaped structure as a design deviation;
- stops and returns the deviation rather than introducing it silently.

### `adversarial-reviewer`

- audits every LSR category against legacy evidence, approved design, and the implementation diff;
- reports unjustified retention, unjustified target mirroring, and platform-coupling leakage as findings;
- does not assume a renamed/repackaged structure is a redesign.

## Relationship to G3

`docs/02-migration-pipeline.md` remains the canonical gate-definition document.

This contract defines what counts as credible evidence for the existing G3 requirements concerning `Legacy structures intentionally not carried forward` and `Legacy-structure rejection evidence`. It does not create a separate gate.

## Evolution after real legacy discovery

The seven LSR categories are the baseline, not a frozen exhaustive list.

When Phase 1 reveals a repeated project-specific carryover pattern:

1. add a stable LSR category or a project-specific sub-rule here/Rulebook;
2. update the agent watchlists if low-reasoning execution would benefit;
3. keep historical disposition evidence intact;
4. do not weaken an existing rule merely because the first real feature is awkward to redesign.
