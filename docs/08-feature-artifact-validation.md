# Feature Artifact Contract and Validation Design

Issues: #1 (feature artifact enforcement), #15 (template/runtime filename drift).

This document is the canonical contract for feature artifact names, locations, lifecycle requirements, and the structural validation design. The naming/location contract is normative now; the remaining A-1 validator implementation described below is separate implementation work.

## Goal

Make feature migration artifacts deterministic enough that agents, templates, documentation, and validators all refer to the same durable files without guessing aliases or output locations.

The first A-1 validation increment checks artifact existence and machine-readable feature metadata only. Heading/content validation belongs to later schema-level validation.

## Adversarial findings

Issue #15 identifies a real drift defect, but its repository snapshot is partly stale after earlier fixes and its recommendations must not be applied mechanically.

1. `feature-card.md`, `legacy-map.md`, `target-feature-design.md`, and `review.md` are already the established durable names after Issues #1/#4. Reverting to `feature.md` or `target-design.md` would reintroduce ambiguity.
2. The remaining singleton mismatch is verification: agents and the feature contract persist `verification.md`, while the source template was named `verification-report.md`. The durable name is already integrated into the lifecycle contract, so the template must follow it rather than renaming the durable artifact.
3. Supporting both old and new singleton aliases is worse than a hard rename. A validator or low-reasoning agent could then accept two files with divergent contents and have no deterministic source of truth.
4. A blanket rule that every file in `docs/templates/` must have the same runtime filename is incorrect. Record templates such as `evidence-record.md` are repeatable schemas; a feature may have many evidence records and therefore needs instance filenames, not one singleton `evidence-record.md`.
5. “Supporting evidence files may be added alongside canonical documents” is too vague. It does not define feature-scoped versus project-wide evidence ownership and encourages root-directory clutter or duplicate records.
6. The filename set must be defined once as a contract and reused by agents/skills/validation. Otherwise documentation can be corrected while operational prompts continue to point at stale names.

## Artifact classes

### Canonical singleton feature artifacts

Each feature has at most one durable artifact of each canonical type. For these six files, the template basename and durable basename must be identical.

| Artifact | Template | Durable feature path |
| --- | --- | --- |
| feature inventory / lifecycle | `docs/templates/feature-card.md` | `migration/features/<feature-id>/feature-card.md` |
| legacy dependency map | `docs/templates/legacy-map.md` | `migration/features/<feature-id>/legacy-map.md` |
| behavior contract | `docs/templates/behavior-contract.md` | `migration/features/<feature-id>/behavior-contract.md` |
| approved target design | `docs/templates/target-feature-design.md` | `migration/features/<feature-id>/target-feature-design.md` |
| independent review | `docs/templates/review.md` | `migration/features/<feature-id>/review.md` |
| verification report | `docs/templates/verification.md` | `migration/features/<feature-id>/verification.md` |

The old singleton names `feature.md`, `target-design.md`, and `verification-report.md` are non-canonical aliases. New operational instructions, templates, or validators must not accept or emit them as substitutes.

### Repeatable supporting records

`docs/templates/evidence-record.md` is a schema template, not a singleton feature filename.

- Feature-scoped evidence: `migration/features/<feature-id>/evidence/<evidence-id>.md`
- Project-wide or intentionally reusable evidence: `migration/evidence/<evidence-id>.md`
- `<evidence-id>` must be lowercase kebab-case and stable enough to be referenced from contracts/reports.
- Do not duplicate the same evidence into both locations. A feature may reference a project-wide record instead.
- Sensitive production data, secrets, or prohibited company information must not be committed; store a sanitized record or an approved external reference instead.

This distinction is deliberate: singleton templates use exact filename identity; repeatable record templates use an explicit instance-location rule.

## Canonical feature directory

Each migration feature uses one lowercase kebab-case directory:

```text
migration/features/<feature-id>/
├── feature-card.md
├── legacy-map.md
├── behavior-contract.md
├── target-feature-design.md
├── review.md
├── verification.md
└── evidence/                  # optional
    └── <evidence-id>.md
```

`<feature-id>` must match `^[a-z0-9]+(?:-[a-z0-9]+)*$`. Files such as `migration/features/README.md` are not features. Extra supporting files are allowed, but they do not replace canonical singleton artifacts.

## Machine-readable feature metadata

`feature-card.md` is the source of truth for lifecycle metadata using constrained frontmatter:

```yaml
---
id: example-feature
stage: discovered
blocked: false
---
```

Allowed `stage` values are `discovered | specified | designed | implementing | reviewing | verifying | done`.

`blocked` is an independent boolean and does not alter the stage. The directory name and `id` must match. Unknown stages, malformed booleans, duplicate keys, missing metadata, or an ID mismatch are validation errors. `stage: done` with `blocked: true` is invalid because completed and currently blocked are mutually exclusive repository states.

The validator must not infer stage from prose such as `Status: done (...)`.

## Artifact requirements by stage

Requirements are cumulative:

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

Evidence records are not stage-mandatory singleton files. Their necessity is driven by material claims and evidence requirements in the relevant behavior/review/verification flow.

## Logical AGENTS.md requirement mapping

| Logical requirement | Canonical location |
| --- | --- |
| feature inventory entry | `feature-card.md` |
| legacy dependency map | `legacy-map.md` |
| behavior contract | `behavior-contract.md` |
| evidence records / confidence grades | claims in canonical artifacts plus referenced evidence records under the evidence rules above |
| unresolved questions | `feature-card.md` and/or `docs/05-open-questions.md` according to scope |
| approved target design | `target-feature-design.md` |
| implementation change | repository/code change; not a required Markdown file |
| independent review report | `review.md` |
| verification report | `verification.md` |
| remaining uncertainty | `verification.md` and referenced open questions/evidence where applicable |

## Validator behavior

The A-1 implementation of `scripts/validate_scaffold.py` should:

1. define one canonical singleton filename set for the six files above;
2. verify that every canonical singleton has a same-basename template under `docs/templates/` so template/runtime drift fails mechanically;
3. enumerate immediate child directories under `migration/features/`;
4. validate each feature directory name;
5. require and parse `feature-card.md` frontmatter;
6. validate `id`, `stage`, and `blocked`, including the `done`/`blocked` invariant;
7. compute the cumulative required file set from `stage`;
8. reject a legacy alias when it is being used in place of a required canonical singleton instead of silently accepting both names;
9. treat `evidence/` and other supporting files as optional extras for structural A-1 validation;
10. report every structural failure for every feature in one run;
11. preserve all existing scaffold checks.

Errors should be aggregated rather than fail-fast so an agent receives a complete repair list.

## Repository normalization

Issue #15 normalization is:

- keep `feature-card.md`, `legacy-map.md`, `behavior-contract.md`, `target-feature-design.md`, and `review.md` as already-established canonical names;
- rename the verification source template from `docs/templates/verification-report.md` to `docs/templates/verification.md`;
- update verifier/verification-skill references to the same canonical template name;
- make feature-scoped versus project-wide evidence placement explicit in both migration README files and evidence-producing guidance;
- do not create alias templates for old singleton names.

Issue #1 still requires separate normalization before its stricter stage validation is enabled, including lifecycle frontmatter/sample artifacts and any missing stage-required files in `synthetic-demo`. Do not create a `synthetic-demo` validator exemption.

## `/migration-status` integration

The A-1 implementation should run the same validator before `/migration-status` produces its summary. Validation failures must be surfaced as process blockers.

No CI workflow change is required if the existing scaffold step continues to invoke `scripts/validate_scaffold.py`.

## Test requirements

A-1 tests should cover: no feature directories; valid metadata; invalid directory name; missing `feature-card.md`; ID mismatch; unknown stage; malformed `blocked`; invalid `done` + `blocked: true`; every stage's cumulative requirements; blocked features retaining stage requirements; optional evidence/supporting files; multiple failures reported together; exact canonical template/runtime basename matching; legacy singleton aliases not satisfying canonical requirements; and normalized `synthetic-demo` passing as `done`.

## Non-goals

This contract does not require heading validation, evidence-grade body validation, proof of design approval, reviewer/verifier independence checks, proof that an implementation diff exists, semantic completeness checks, or automatic validation of every repeatable evidence record. Those belong to later validation layers.

## Acceptance criteria

The artifact contract is internally consistent when all operational guidance refers to the six canonical singleton names, each singleton has a same-basename template, repeatable evidence locations are deterministic, no legacy alias is needed to resolve a feature artifact, and future A-1 validation can derive its required-file checks without choosing between competing names.
