# Evidence Store

Canonical evidence-location rules are defined in `docs/08-feature-artifact-validation.md`.

Use this directory only for project-wide evidence or evidence intentionally reused by multiple features:

```text
migration/evidence/<evidence-id>.md
```

Create records from `docs/templates/evidence-record.md`. The template filename names the schema; persisted records use a lowercase kebab-case `<evidence-id>` so multiple records can coexist.

Feature-specific evidence belongs with its feature instead:

```text
migration/features/<feature-id>/evidence/<evidence-id>.md
```

Do not duplicate the same evidence in both locations. Feature artifacts may reference a reusable project-wide record.

Do not commit sensitive production data, secrets, or prohibited company information. Prefer sanitized fixtures and references to approved internal evidence locations when necessary.
