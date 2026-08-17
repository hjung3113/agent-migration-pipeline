# MSSQL Read-only Inspection Tool Design

Issue: #18 — MSSQL operational database inspection tooling is missing even though the migration workflow requires schema and database-resident business-logic evidence.

This document defines the design only. `AGENTS.md` rule 13 keeps the script, DB driver/helper, agent, skill, validator, and live-connection implementation behind a later explicit implementation gate.

## Goal

Define the smallest deterministic evidence-collection boundary that lets `db-analyzer` inspect production MSSQL during Phase 1 without giving an agent a general SQL console or silently persisting sensitive database source into Git.

The tool exists to make questions such as OQ-013 answerable from evidence rather than source-code guesses while preserving uncertainty whenever catalog visibility is incomplete.

## Current repository facts

The issue's exact snapshot is stale: `scripts/` now contains multiple repository guard scripts, not only `validate_scaffold.py`. The material defect remains: there is still no MSSQL catalog/definition inspector.

The current workflow already requires tables, keys, constraints, defaults, indexes, collations, identity behavior, precision/nullability, procedures, functions, views, triggers, jobs, and transaction semantics. A prose instruction to inspect those objects is not an executable evidence path.

Issue #23 now owns DB credential injection and logical profile naming. Issue #18 therefore consumes that contract instead of inventing a new connection-string environment variable.

## Adversarial findings

The issue direction is valid, but its literal proposal is insufficient.

1. **A read-only label is not a permission boundary.** The production profile must resolve to a DBA-provisioned server-enforced read-only account, while the inspector itself remains incapable of arbitrary SQL execution. Profile naming/client guards are defense in depth, not substitutes for DB permissions.
2. **An empty catalog result does not prove absence.** SQL Server metadata visibility can hide rows. The tool must distinguish `not found in a complete inspected scope` from `not visible / unavailable / not inspected`.
3. **Unavailable module text must not mean no logic.** Encrypted/hidden/unavailable definitions remain unresolved evidence and prevent a completeness claim for that object.
4. **SQL Server Agent is a separate visibility boundary.** Jobs live under `msdb`; inability to inspect them must become explicit partial coverage, not a false zero-job result.
5. **Raw definitions are sensitive evidence.** Procedure/view/function/trigger bodies and job-step commands can contain proprietary code, endpoints, literals, or credentials. Raw captures must not be automatically copied into Git-tracked feature artifacts.
6. **`INFORMATION_SCHEMA` alone is insufficient.** SQL Server-specific semantics such as identity/computed columns, indexes, filtered predicates, exact constraint metadata, and module properties require `sys.*` catalog views.
7. **A generic `--sql` path defeats the safety model.** V1 uses only a closed set of embedded catalog `SELECT` queries. No user SQL, DDL, DML, `EXEC`, procedure/job execution, or application-row export belongs in this tool.
8. **Full-database extraction can be excessive.** The interface needs schema/object scoping while still supporting an explicitly intended full visible inventory for discovery.
9. **Raw Markdown paste is not the durable evidence model.** The canonical machine snapshot and the reviewed `db-dependency-report.md` have different sensitivity/completeness responsibilities.

## Ownership and dependencies

### Issue #18 owns

- MSSQL catalog/definition inspection scope;
- the fixed read-only query set;
- inspection completeness semantics;
- normalized snapshot schema and Markdown rendering;
- raw-capture versus durable-report boundary;
- future integration into `db-analyzer` and `db-migration-analysis`.

### Issue #23 owns

- logical DB profile names;
- environment-variable mapping and secret injection;
- fail-closed profile resolution;
- secret redaction rules.

Issue #18 accepts only profile `mssql-prod-ro`; it does not read arbitrary connection strings or define another secret-loading convention.

### Other issues

Issue #19 may consume #18 schema/object evidence when preparing a test materialization but remains a separate one-way materialization design. Issue #20's later DB guard may add shared target-identity defenses; #18 does not need a write-capable path in order to operate.

## Tool boundary

Canonical future path:

```text
scripts/db/mssql_inspect.py
```

The tool has one responsibility: execute a fixed set of read-only catalog queries and serialize the resulting metadata/definitions.

It must not:

- run arbitrary SQL;
- execute legacy procedures/functions/jobs/triggers;
- read application table rows;
- translate/rewrite T-SQL;
- decide target business-rule ownership;
- mutate migration queue/state artifacts.

## Connection and safety contract

### Profile input

The CLI accepts only:

```text
--profile mssql-prod-ro
```

The profile is resolved through `docs/12-db-connection-secrets-contract.md`. Raw connection strings, passwords, host/user/password triples, arbitrary environment-variable names, and secret-bearing config paths are not supported CLI inputs.

The logical profile name may be logged; the resolved connection value may not.

### Server-side principal

Phase 1 requires the `mssql-prod-ro` connection to use a DBA-approved, server-enforced read-only principal with the metadata/object-definition visibility needed for the approved scope. SQL Agent visibility is an additional capability, not a reason to grant broad administration rights.

The inspector records capability/visibility observations but cannot certify that an account is globally read-only. Account provisioning remains an operational security responsibility.

### Fixed-query allowlist

The implementation contains a closed query set. Every DB operation is a literal/parameterized `SELECT` against approved catalog views/functions. Schema/object filters use parameters or safe identifier handling; they never become arbitrary SQL fragments.

There is no `--sql`, generic query file, or `EXEC` path in V1.

### Database identity guard

The CLI accepts `--expect-database <name>`. If supplied and connected `DB_NAME()` differs, inspection aborts before the inventory queries run. This is an inspection-specific wrong-target guard, not a replacement for the broader Issue #20 design.

## CLI contract

```text
python scripts/db/mssql_inspect.py snapshot \
  --profile mssql-prod-ro \
  [--expect-database <name>] \
  [--schema <schema>]... \
  [--object <schema.name>]... \
  [--include-jobs] \
  [--include-job-step-text] \
  [--format json|markdown|both] \
  [--output-dir <path>]
```

Rules:

- `snapshot` is the only V1 subcommand.
- `mssql-prod-ro` is the only accepted profile.
- With no `--schema`/`--object`, database scope is all visible user objects in the connected database.
- `--include-jobs` requests SQL Server Agent inventory separately.
- `--include-job-step-text` requires `--include-jobs` and is opt-in because job commands are especially likely to contain sensitive literals.
- JSON is canonical. Markdown is rendered from the same normalized snapshot; it is not queried/generated independently.
- Default raw output is a local non-Git area such as `.local/mssql-inspection/<capture-id>/`. The later implementation must add the chosen local capture path to `.gitignore` before live use.
- Stdout contains only a short non-secret capture summary/status. Raw definitions are not printed by default.

## Inspection coverage

V1 covers only evidence already required by current migration contracts.

### Capture context

- SQL Server/product version needed to interpret catalog behavior;
- database name, compatibility level, and database collation;
- capture UTC timestamp;
- snapshot schema/tool revision;
- requested/effective scope;
- selected logical profile name;
- non-secret current-principal/visibility capability observations.

### Tables and columns

- schemas/tables;
- columns and SQL Server types;
- length/precision/scale;
- nullability;
- identity behavior;
- computed-column expression/status where visible;
- column collation where applicable.

### Integrity and access structures

- primary keys;
- foreign keys/referenced columns;
- unique constraints;
- check/default expressions where visible;
- indexes, uniqueness, key/include columns, and filtered-index predicate where visible.

### Programmable objects

For procedures, scalar/table-valued functions, views, and database/table triggers:

- schema/name/type/object id;
- relevant module flags;
- raw definition when visible;
- definition hash for stable evidence reference/change detection;
- explicit definition availability status.

V1 does not add dependency-graph reconstruction, T-SQL parsing, dynamic-SQL resolution, or server-level trigger analysis. Add those only if real feature analysis demonstrates the need.

### SQL Server Agent jobs

When requested and visible:

- job identity/name/enabled state;
- step id/name/subsystem/database context;
- schedule linkage/basic schedule metadata;
- job-step command text only when explicitly opted in.

Failure to inspect `msdb` does not invalidate the database-object portion, but DB analysis cannot claim job-inventory completeness.

## Output model

The versioned JSON top level is:

```text
schema_version
capture
scope
capabilities
warnings
inventory
```

`capabilities` records independent statuses:

```text
database_catalog: COMPLETE | PARTIAL | BLOCKED
module_definitions: COMPLETE | PARTIAL | BLOCKED
agent_jobs: NOT_REQUESTED | COMPLETE | PARTIAL | BLOCKED
agent_job_step_text: NOT_REQUESTED | COMPLETE | PARTIAL | BLOCKED
```

Each definition-bearing record includes:

```text
definition_status: AVAILABLE | UNAVAILABLE | OMITTED_BY_POLICY | ERROR
definition_reason: <specific evidence when known, otherwise UNKNOWN>
definition_sha256: <hash when AVAILABLE>
definition: <raw text only in the local capture when AVAILABLE and policy permits>
```

The inspector must not invent a precise reason when available SQL Server evidence cannot distinguish encryption, metadata visibility, or another cause.

## Completeness semantics

Completeness is evidence, not display metadata.

- A category is `COMPLETE` only when every required fixed query for the requested scope succeeded and recorded visibility preconditions support an absence claim for that scope.
- A successful query returning zero rows is not sufficient by itself.
- Hidden/unavailable definitions make `module_definitions` at least `PARTIAL` when those objects are in scope.
- Missing `msdb` visibility makes requested `agent_jobs` `PARTIAL` or `BLOCKED`.
- Analysis relying on a `PARTIAL`/`BLOCKED` category must preserve uncertainty and must not close an open question merely because no row/text was returned.

## Raw capture versus Git-tracked artifacts

### Raw capture

Contains exact catalog output and definitions. It remains in the approved local/secure evidence location and is not automatically committed.

### `db-dependency-report.md`

Contains reviewed facts required for migration decisions:

- capture id/schema version/time/scope;
- completeness/capability status;
- object identifiers;
- hashes/evidence references;
- minimum necessary excerpts only when repository/company policy allows them;
- classification and remaining uncertainty.

An agent must not paste the entire snapshot into `legacy-map.md` or `db-dependency-report.md` merely because Markdown rendering exists.

If an approved secure durable evidence store is added later, the report may reference it. Until then, Git retains decision/evidence summaries rather than raw operational DB dumps.

## Migration workflow integration

### `db-analyzer`

After the implementation gate, the procedure must:

1. resolve feature DB scope from `feature-card.md`/`legacy-map.md`;
2. run the inspector with `mssql-prod-ro` when live MSSQL evidence is available;
3. inspect completeness before interpreting absence;
4. classify captured behavior into `db-dependency-report.md`;
5. return `PARTIAL`/`BLOCKED` when required objects/definitions/jobs remain invisible;
6. never copy credentials, raw dumps, or unrestricted sensitive definitions into the coordinator handoff.

### `db-migration-analysis`

The skill must name this inspector as the canonical live-MSSQL evidence path and preserve the same completeness/sensitivity rules. Source-code SQL strings may supplement the capture but do not silently replace an unavailable required DB definition.

### OQ-013

This design does not resolve OQ-013. It defines the evidence path needed to answer it. OQ-013 remains open until Phase 1 obtains and analyzes real DB evidence.

## Phase 0 / Phase 1 boundary

Phase 0 is complete when the interface, safety model, output/completeness semantics, and workflow integration are approved. No live credential/database is required for this design pass.

Phase 1 implementation/live validation must prove at least:

1. `mssql-prod-ro` is the only accepted profile and uses the shared Issue #23 resolver;
2. no arbitrary SQL execution path exists and only the approved catalog query set is used;
3. connection values never appear in stdout, snapshots, errors, or tests;
4. wrong-database guard aborts before capture;
5. known fixture objects produce correct column/constraint/index/module metadata;
6. unavailable definitions become explicit `PARTIAL`/unavailable evidence rather than `ABSENT`;
7. missing job visibility is reported independently and does not masquerade as zero jobs;
8. job-step text remains opt-in;
9. JSON and Markdown come from one normalized snapshot model;
10. raw output defaults to an ignored/non-Git location;
11. `db-analyzer`/`db-migration-analysis` propagate capture provenance and completeness into `db-dependency-report.md`.

Live validation uses a DBA-approved non-destructive environment or approved production read-only inspection account. Unit/golden tests may validate query selection and serialization without claiming real SQL Server permission behavior is proven.

## Non-goals

Issue #18 does not provision accounts or store credentials, create a general SQL console, export application rows, execute jobs/procedures/functions, parse/rewrite T-SQL, design PostgreSQL schemas, materialize test data, implement snapshot diffing, automatically resolve business-rule ownership, add an enterprise evidence store, close OQ-013 before real evidence exists, or implement the script/agent/skill changes in this design pass.

## Acceptance criteria

The design is ready for later implementation when:

- the inspector has one bounded read-only responsibility and no arbitrary SQL escape hatch;
- the shared `mssql-prod-ro` profile contract is consumed rather than duplicated;
- raw operational evidence is separated from Git-tracked summaries;
- metadata visibility/definition unavailability cannot be mistaken for absence;
- job visibility is represented independently;
- JSON/Markdown have one normalized source model;
- `db-dependency-report.md` records capture provenance/completeness;
- Phase 1 has explicit live-validation conditions;
- `db-analyzer` and `db-migration-analysis` have an unambiguous integration point without weakening the existing coordinator/read-only-agent boundary.
