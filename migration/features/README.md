# Feature Artifacts

Canonical contract: `docs/08-feature-artifact-validation.md`.

Create one lowercase kebab-case directory per migration feature:

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

## Canonical singleton files

The six root Markdown files above are the only canonical singleton feature artifacts. Their source templates use the same basename under `docs/templates/`:

- `feature-card.md`
- `legacy-map.md`
- `behavior-contract.md`
- `target-feature-design.md`
- `review.md`
- `verification.md`

Do not use `feature.md`, `target-design.md`, or `verification-report.md` as aliases for these durable artifacts.

## Evidence records

`docs/templates/evidence-record.md` is a repeatable record schema, not a seventh canonical singleton filename.

- Feature-specific evidence goes under `migration/features/<feature-id>/evidence/<evidence-id>.md`.
- Project-wide or deliberately reusable evidence goes under `migration/evidence/<evidence-id>.md`.
- Reference reusable evidence instead of copying it into the feature directory.
- Use lowercase kebab-case `<evidence-id>` values.

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
- `done`: all six canonical singleton documents

The implementation change itself is not represented by a mandatory Markdown file. Evidence records are supporting artifacts and do not replace a required singleton file.
