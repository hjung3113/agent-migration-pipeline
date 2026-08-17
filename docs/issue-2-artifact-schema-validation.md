# Artifact Schema and Reference Validation Design

Issue: #2 — closed enum values and ID/reference formats are not mechanically enforced.

This document defines the design only. Validator code, templates, sample artifacts, and command wiring are implementation work and remain gated by AGENTS.md rule 13.

## Goal

Reject machine-contract values that are "almost right" while avoiding brittle regex scans over arbitrary Markdown prose.

A-2 validates **closed value domains, identifier formats, identifier uniqueness in the correct scope, and explicitly structured references**. It does not decide whether an artifact is semantically complete.

## Adversarial findings

The issue identifies a real gap, but its proposed implementation cannot be applied literally to the current repository.

1. Issue #1 already makes `feature-card.md` frontmatter (`id`, `stage`, `blocked`) the lifecycle source of truth. Parsing body text such as `- Status:` would create a second, conflicting lifecycle contract.
2. `Grade` is not one global enum. Evidence/business-rule grades use `A | B | C | D | ?`, while characterization capture items need `N/A` when the item is genuinely inapplicable.
3. `docs/templates/` contains instructional alternatives such as `A | B | C | D | ?`; templates are schema examples, not artifact instances.
4. `BR-001` is feature-local. Global BR uniqueness would reject valid independent behavior contracts.
5. `OQ-###` is repository-global, but `migration/QUEUE.md` uses `Q-###` and free-form blocker prose. Queue dependency integrity is not an A-2 reference rule until it has its own machine-readable schema.
6. Repository-wide regex scanning for `OQ-###`/`BR-###` would misclassify examples, fenced code, historical notes, and templates as live references.
7. `scripts/check_oq_updates.py` is a diff-aware evidence-policy guard. It does not statically validate the full current OQ registry and therefore does not replace A-2.
8. Issue #9 owns evidence-grade history and revision-aware promotion/downgrade control in `docs/09-evidence-grade-transition-control.md`. A-2 owns current-state schema validation only.
9. Issue #10 added the closed provenance domain `observed | inferred` to behavior-rule `Basis` and claim prefixes; this is now part of the schema surface.
10. `validate_scaffold.py` currently fails fast. Schema validation should aggregate violations so agents receive one repair list.

## Validation layers

1. **A-1 structure** — feature metadata and required artifact existence (`docs/08-feature-artifact-validation.md`).
2. **A-2 schema** — closed values, ID formats/scopes, and explicit reference integrity (this document).
3. **Evidence-grade lifecycle** — history and revision-aware transition checks (`docs/09-evidence-grade-transition-control.md`).
4. **Semantic completeness** — required content, evidence sufficiency, approvals, reviewer/verifier identity, and whether a completed artifact is substantively complete.

A-2 must not duplicate A-1 lifecycle parsing, infer semantic completeness, or guess historical revisions.

## Instance discovery

Validation must identify artifact instances deterministically without treating templates as live data.

- canonical feature documents are identified by fixed filenames under `migration/features/<feature-id>/`;
- optional evidence records inside a feature directory are identified by first non-comment H1 `# Evidence: <ID>`;
- characterization records inside a feature directory are identified by first non-comment H1 `# Characterization: <ID>`;
- `docs/templates/` is always schema/example input, never an artifact-instance validation target.

This avoids inventing filename patterns while still supporting multiple evidence/characterization records per feature.

## Canonical schema rules

### Feature lifecycle metadata

A-2 consumes the A-1 frontmatter contract and does not parse a body `Status:` field.

- `id`: lowercase kebab-case and equal to the feature directory name;
- `stage`: `discovered | specified | designed | implementing | reviewing | verifying | done`;
- `blocked`: strict boolean;
- `stage: done` with `blocked: true`: invalid.

These checks are owned by A-1 even if implementation shares parsing helpers.

### Claim provenance

Issue #10 makes provenance a closed current-state domain.

- behavior-contract `Basis` must be exactly `observed | inferred` when non-empty;
- narrative claim markers in schema-governed sections may be only `[observed]` or `[inferred]`;
- near-miss variants such as `Observed`, `[inference]`, or `mixed` are invalid;
- provenance validity is independent from evidence grade validity.

A-2 checks the marker/domain. Whether a claim is substantively classified correctly remains semantic review.

### Behavior contract

In `migration/features/<feature-id>/behavior-contract.md`, the `Business rules` table is the structured BR definition location.

- non-empty Rule IDs must match `^BR-\d{3}$`;
- Rule IDs must be unique **within that behavior contract**;
- non-empty `Basis` cells must be exactly `observed | inferred`;
- non-empty Grade cells must be exactly `A | B | C | D | ?`;
- another feature may legally reuse the same BR numeric suffix.

A-2 validates values that are present. Whether every important rule exists is a later completeness check.

### Evidence records

For an evidence-record instance:

- the H1 record ID must be non-empty and stable for the same claim/scenario;
- non-empty current `Grade` must be exactly `A | B | C | D | ?`;
- non-empty `Source type` must be exactly `automated-test | runtime | db | log | callback | source | manual | other`;
- a dedicated BR reference, when present, must match `^BR-\d{3}$` and resolve in the same feature's behavior contract.

The current free-form `Rule/scenario` text is not treated as a reference. Referential integrity requires a declared structured field.

Grade-history continuity, current-grade/history equality, promotion evidence, downgrade history, and base-revision comparison remain owned by Issue #9.

### Characterization records

Characterization records use fixed `- Key: value` fields and capture-item sections as the machine-readable boundary.

- non-empty `Record grade rollup` must be `A | B | C | D | ?`;
- capture-item `Grade` may be `A | B | C | D | ? | N/A`;
- `Grade: N/A` is valid only for an actually inapplicable item whose `Value:` is `N/A` or the documented `N/A (...)` form;
- `none observed` is an observation, not N/A, and therefore still requires an evidence grade;
- non-empty `Behavior contract ref` and item `Ref` values must match `^BR-\d{3}$` and resolve in the same feature's behavior contract.

The current `synthetic-demo` contains `none observed` paired with `Grade: N/A`; this is a repository inconsistency to normalize before enforcement, not a reason to add an exemption.

### Verification report

For canonical feature `verification.md` instances:

- non-empty `Result` must be exactly `PASS | FAIL | PARTIAL | BLOCKED`;
- non-empty Grade cells in its evidence table must be `A | B | C | D | ?`.

Blank work-in-progress values are not silently converted into valid final values. Stage-dependent requiredness is a completeness rule, not A-2 enum validation.

### Open questions

`docs/05-open-questions.md` is the global OQ registry.

For every registry row:

- ID must match `^OQ-\d{3}$`;
- ID must be globally unique;
- Status must be exactly `OPEN | CONFIRMED | NOT-APPLICABLE | DEFERRED`.

Structured resolved headings such as `### OQ-024` must point to an existing registry ID.

Feature OQ references become mechanically checkable only through an explicit structured list. The implementation pass should standardize the feature `## Open questions` section so each reference has a leading OQ ID that must resolve in the global registry. OQ-like prose elsewhere is ignored.

## Parsing contract

Do not implement one repository-wide Markdown regex.

Use schema-specific parsers with explicit scope:

- frontmatter parser for A-1 lifecycle metadata;
- Markdown table parser scoped to Business Rules and the OQ registry;
- exact `- Key: value` parser for evidence/characterization/verification fields;
- structured bullet parsing only where provenance/reference lists are explicitly declared.

Fenced code, examples, ordinary prose, historical notes, and templates are not instance data. Duplicate machine keys in the same schema scope are validation errors; never silently take the first or last value.

## Error reporting

A-1/A-2 violations should be collected before exit and include enough location information for direct repair:

```text
migration/features/example/behavior-contract.md:17 [invalid-enum] Grade `B+`; expected A|B|C|D|?
docs/05-open-questions.md:9 [invalid-id] `OQ-12`; expected OQ-###
migration/features/example/feature-card.md:31 [missing-ref] OQ-099 is not defined in docs/05-open-questions.md
```

Each diagnostic must include repository-relative path, line number, category, offending value/reference, and expected contract.

## Integration with existing guards

`scripts/validate_scaffold.py` remains the single static repository-validation entry point used by CI. Implementation may extract helpers, but `python3 scripts/validate_scaffold.py` must run A-1 and A-2 together.

`scripts/check_oq_updates.py` remains separate: A-2 validates the current OQ registry, while `check_oq_updates.py` validates the evidence/process requirement when OQ status changes.

Issue #9 transition validation remains separate whenever two revisions are required. Parser/constants should be shared where useful, but static and revision-aware checks must not be conflated.

No CI workflow change is required for A-2 because CI already executes the static validator. `/migration-status` should surface the same static validation failures after the A-1 command integration is implemented.

## Repository normalization required before enforcement

The implementation pass must first:

- complete A-1 template/sample normalization from `docs/08-feature-artifact-validation.md`;
- remove reliance on body lifecycle `Status:` so frontmatter stays the only machine lifecycle source;
- preserve Issue #10's `observed | inferred` provenance contract;
- make live evidence/characterization/verification instance fields contain one actual value rather than template alternatives;
- standardize feature Open Question references into the structured grammar above;
- fix `synthetic-demo` so `none observed` is not paired with `Grade: N/A`;
- add/normalize canonical `verification.md` for `synthetic-demo` as required by A-1;
- keep `docs/templates/` excluded from artifact-instance validation;
- coordinate evidence-record parsing/schema with Issue #9 so one parser can support both static A-2 rules and grade-history rules.

Do not add exemptions for `synthetic-demo`, templates, or known bad lines. Normalize the data contract instead.

## Test requirements

Implementation tests should cover:

- every accepted/rejected enum spelling and casing per field;
- `observed | inferred` provenance and near-miss rejection;
- `BR-001` accepted; `BR-1`, `BR-0001`, `br-001`, `BR-01A` rejected;
- duplicate BR IDs rejected within one feature but legal across different features;
- `OQ-001` accepted; wrong-width/case variants and duplicate OQ IDs rejected;
- OQ status validation independent of diff history;
- existing/missing structured OQ references;
- existing/missing same-feature BR references;
- evidence/characterization H1 instance discovery with templates ignored;
- prose/code occurrences ignored;
- blank WIP values not mistaken for valid final values;
- characterization `N/A` invariant and `none observed` distinction;
- duplicate machine keys rejected;
- multiple errors aggregated with correct file/line diagnostics;
- normalized `synthetic-demo` and the current OQ registry passing.

## Non-goals for A-2

Do not include arbitrary prose reference scanning, global BR uniqueness, queue `Q-###`/slice `S-###` dependency validation, semantic evidence/provenance sufficiency, design approval proof, reviewer/verifier independence, implementation-diff proof, automatic lifecycle completion, or revision-aware grade-transition detection.

If queue dependency integrity is required later, first replace prose such as `blocked by Q-004/Q-006` with an explicit machine-readable dependency field and validate that schema separately.

## Acceptance criteria

A-2 implementation is complete when closed values reject near-miss spellings, provenance/BR/OQ identifiers obey their defined domains and scopes, declared references resolve without scanning prose, templates are not mistaken for instances, current repository inconsistencies are normalized instead of exempted, all violations include file/line diagnostics, and CI plus `/migration-status` consume the same static validation result.
