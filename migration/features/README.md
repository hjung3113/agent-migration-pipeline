# Feature Artifacts

> Design contract for issue #1. The validator, templates, and existing `synthetic-demo` fixture still require a separate implementation pass before this contract is mechanically enforced.

Create one lowercase kebab-case directory per migration feature:

```text
migration/features/<feature-id>/
├── feature-card.md
├── legacy-map.md
├── behavior-contract.md
├── target-feature-design.md
├── review.md
└── verification.md
```

Supporting evidence files may be added alongside these canonical documents.

## Lifecycle metadata

`feature-card.md` is the machine-readable source of truth for lifecycle metadata:

```yaml
---
id: example-feature
stage: discovered
blocked: false
---
```

Allowed stages:

```text
discovered | specified | designed | implementing | reviewing | verifying | done
```

`blocked` is independent from `stage`; do not replace the lifecycle stage with a `blocked` status. `stage: done` with `blocked: true` is invalid.

The feature directory name and metadata `id` must match.

## Required files by stage

Requirements are cumulative:

- `discovered`: `feature-card.md`, `legacy-map.md`
- `specified`: above + `behavior-contract.md`
- `designed`: above + `target-feature-design.md`
- `implementing`: same as `designed`
- `reviewing`: above + `review.md`
- `verifying`: above + `verification.md`
- `done`: all six canonical documents

The implementation change itself is not represented by a mandatory Markdown file.

See `docs/08-feature-artifact-validation.md` for the validation design, rationale, migration requirements, and A-1 scope boundaries.
