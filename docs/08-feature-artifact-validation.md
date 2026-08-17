# Feature Artifact Validation Design

Issue: #1 — feature-level required artifacts are not enforced by `scripts/validate_scaffold.py`.

This document defines the design only. The validator, templates, sample artifacts, and command integration are implementation work and are intentionally not changed here.

## Goal

Make feature migration gates mechanically checkable without requiring the LLM to remember which artifacts should exist at each lifecycle stage.

The first implementation increment validates **artifact existence and machine-readable feature metadata only**. Heading/content validation belongs to a later increment (A-2).

## Adversarial findings

The issue describes the correct failure mode, but its suggested implementation cannot be applied literally to the current repository.

1. `migration/features/README.md` documents `feature.md` and `target-design.md`, while templates and `synthetic-demo` use `feature-card.md` and `target-feature-design.md`.
2. `blocked` cannot be a lifecycle stage because a feature may become blocked at any stage; replacing the stage with `blocked` destroys the information required to compute mandatory artifacts.
3. Free-form Markdown status is not a safe machine contract. `synthetic-demo` currently uses `Status: done (dry-run only, not a real migration)`.
4. The ten AGENTS.md requirements are logical artifacts, not ten files. `implementation change` is a repository change, while evidence, unresolved questions, and remaining uncertainty belong inside canonical documents.
5. `synthetic-demo` is marked done but has no `legacy-map.md`, `review.md`, or `verification.md`; enabling the proposed rule without normalization would break CI immediately.
6. CI already executes `python3 scripts/validate_scaffold.py`, so extending the script automatically extends CI coverage. `/migration-status` still needs explicit integration.

## Canonical feature directory

Each migration feature uses one lowercase kebab-case directory:

```text
migration/features/<feature-id>/
```

`<feature-id>` must match `^[a-z0-9]+(?:-[a-z0-9]+)*$`. Files such as `migration/features/README.md` are not features. Extra supporting files are allowed.

## Canonical required documents

```text
feature-card.md
legacy-map.md
behavior-contract.md
target-feature-design.md
review.md
verification.md
```

Logical AGENTS.md requirements map as follows:

| Logical requirement | Canonical location |
| --- | --- |
| feature inventory entry | `feature-card.md` |
| legacy dependency map | `legacy-map.md` |
| behavior contract | `behavior-contract.md` |
| evidence records / confidence grades | `behavior-contract.md` plus optional supporting evidence files |
| unresolved questions | `feature-card.md` |
| approved target design | `target-feature-design.md` |
| implementation change | repository/code change; not a required Markdown file |
| independent review report | `review.md` |
| verification report | `verification.md` |
| remaining uncertainty | `verification.md` |

A-1 validates existence only. Required headings, evidence grade values, approval markers, reviewer identity, and uncertainty content are later schema-level checks.

## Machine-readable feature metadata

`feature-card.md` becomes the source of truth for lifecycle metadata using constrained frontmatter:

```yaml
---
id: example-feature
stage: discovered
blocked: false
---
```

Allowed `stage` values are `discovered | specified | designed | implementing | reviewing | verifying | done`.

`blocked` is an independent boolean and does not alter the stage. The directory name and `id` must match. Unknown stages, malformed booleans, duplicate keys, missing metadata, or an ID mismatch are validation errors. `stage: done` with `blocked: true` is also invalid because completed and currently blocked are mutually exclusive repository states.

The validator must not infer stage from prose such as `Status: done (...)`.

## Artifact requirements by stage

The required set is cumulative:

| Stage | Required documents |
| --- | --- |
| `discovered` | `feature-card.md`, `legacy-map.md` |
| `specified` | above + `behavior-contract.md` |
| `designed` | above + `target-feature-design.md` |
| `implementing` | same as `designed` |
| `reviewing` | above + `review.md` |
| `verifying` | above + `verification.md` |
| `done` | all six canonical documents |

`implementing` adds no Markdown artifact because implementation is the code/data/configuration change itself. `review.md` and `verification.md` may be work-in-progress when their stages begin; A-1 checks only existence.

## Validator behavior

`validate_scaffold.py` should:

1. enumerate immediate child directories under `migration/features/`;
2. validate each feature directory name;
3. require and parse `feature-card.md` frontmatter;
4. validate `id`, `stage`, and `blocked` including the `done`/`blocked` invariant;
5. compute the cumulative required file set from `stage`;
6. report every missing file for every feature in one run;
7. preserve all existing scaffold checks.

Errors should be aggregated rather than fail-fast so an agent receives a complete repair list.

## Existing repository migration required before enforcement

The implementation PR must normalize the repository before the new rule is allowed to pass CI:

- update `docs/templates/feature-card.md` with the metadata frontmatter contract;
- add canonical templates for `legacy-map.md` and `review.md` if absent;
- align the verification template to canonical `verification.md` usage;
- migrate `migration/features/synthetic-demo/feature-card.md` to frontmatter metadata;
- add canonical `legacy-map.md`, `review.md`, and `verification.md` for `synthetic-demo` while preserving `DRY-RUN-REPORT.md` and other supporting evidence;
- do not add a special validator exemption for `synthetic-demo`.

## `/migration-status` integration

The implementation should run the same validator before `/migration-status` produces its summary. Validation failures must be surfaced as process blockers.

No CI workflow change is required because the existing scaffold step already invokes `scripts/validate_scaffold.py`.

## Test requirements

Implementation tests should cover: no feature directories; valid metadata; invalid directory name; missing `feature-card.md`; ID mismatch; unknown stage; malformed `blocked`; invalid `done` + `blocked: true`; every stage's cumulative requirements; blocked features retaining stage requirements; optional extra files; multiple failures reported together; and normalized `synthetic-demo` passing as `done`.

## Non-goals for A-1

Do not include required heading validation, evidence-grade body validation, proof of design approval, reviewer/verifier independence checks, proof that an implementation diff exists, or semantic completeness checks. Those belong in later validation layers.

## Acceptance criteria

A-1 implementation is complete when lifecycle metadata is deterministic, required files are stage-derived, all structural failures are reported together, existing fixtures are normalized rather than exempted, CI fails on violations, `/migration-status` surfaces the same violations, and body semantics remain outside A-1.
