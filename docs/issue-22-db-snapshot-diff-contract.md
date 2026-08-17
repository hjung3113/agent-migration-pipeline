# DB Snapshot and Diff Contract Design

Issue: #22 — DB before/after snapshot and diff tooling is missing from the parity-verification path.

This document defines the design only. It does **not** add `scripts/db/db_snapshot_diff.py`, concrete MSSQL/PostgreSQL drivers, a DB judge adapter, or runtime credentials. Those are implementation work and remain behind `AGENTS.md` rule 13.

## Goal

Make DB evidence reproducible enough that a low-reasoning verifier can answer, without manually eyeballing `SELECT` output:

1. what DB state was observed before a scenario;
2. what DB state was observed after it;
3. what logical DB delta the legacy run produced;
4. what logical DB delta the target run produced; and
5. whether those deltas match under comparison semantics already declared by the feature behavior contract.

The design must support legacy MSSQL and target PostgreSQL while preventing the verification tool from becoming a write-capable DB utility or a second source of business comparison rules.

## Current repository facts

The issue is valid against current `main`:

- `README.md` names `DB diff` as one of the verifier evidence paths.
- `docs/03-evidence-and-verification.md` requires initial and resulting DB state capture.
- `migration/judge/ports.py` already defines `DbAssertionPort` around the before/after capture items.
- `.opencode/skills/parity-verification/SKILL.md` lists DB before/after comparisons, but no concrete capture/diff procedure exists.
- `docs/templates/verification.md` has a `DB comparison` section but no deterministic evidence shape.
- there is no `scripts/db/db_snapshot_diff.py` or equivalent implementation.

The repository also already contains stricter adjacent contracts that this design must preserve:

- Issue #11: the effective judge configuration needs a mandatory negative control before its verdict is trusted.
- Issue #12: comparison semantics belong to `behavior-contract.md` / explicitly referenced Rulebook rules, not to test helpers or adapters.
- Issue #18: MSSQL read-only inspection is a separate tooling concern.
- Issue #19: reproducible/sanitized legacy test data is a separate provisioning concern.
- Issue #20: DB write safety/profile enforcement is a separate mandatory safety boundary.
- Issue #21: PostgreSQL test DB bootstrap/schema reset is a separate provisioning concern.

## Adversarial findings

The literal recommendation in Issue #22 is directionally correct but incomplete.

1. **Comparing full legacy and target DB states is usually the wrong oracle.** The engines intentionally have different physical schemas, unrelated reference rows, generated identifiers, and migration-era data. Whole-state comparison would create false failures and pressure agents to add unsafe normalization. The primary parity object must be the **business-relevant delta produced by the same logical scenario**, not two whole databases.
2. **A generic injected connector is too permissive.** An arbitrary connector can silently expose write methods. The snapshot boundary must accept only a read-only capability and must fail closed when that property cannot be established.
3. **Parsing free-form comparison prose inside the snapshot tool is unsafe.** It would make `db_snapshot_diff.py` an undeclared specification engine. The tool may capture and calculate deterministic structural deltas; the DB judge adapter applies only the already-declared behavior-contract semantics.
4. **CSV is not an authoritative snapshot format.** It loses type fidelity and conflates values such as null/empty text. Canonical JSON is the source of truth; Markdown is a report rendering only. CSV is deferred until a concrete need exists.
5. **Row order cannot be an accidental key.** Every multi-row subject needs an explicit stable identity/correlation rule. Duplicate or missing identities are blockers, not reasons to sort rows heuristically.
6. **Silent truncation makes a PASS meaningless.** A row limit is allowed only as a safety bound; exceeding it blocks the subject instead of comparing a partial result.
7. **Raw DB rows are potentially sensitive.** This repository is Git-backed and may not be an approved store for production-derived row values. Raw snapshots therefore stay outside version control by default; durable reports store metadata, hashes, and sanitized summaries.
8. **The judge self-check must challenge the DB comparator without mutating a database.** The safe negative-control boundary is a staged snapshot/delta artifact, not deliberate DB corruption.
9. **Provisioning and observation are separate responsibilities.** This tool must not clone production, seed/reset test DBs, execute the business scenario, or write test data. Issues #19/#20/#21 own those boundaries.

## Canonical comparison model

### Comparison subject

A DB comparison subject is one logical business-state projection, not a physical table dump.

Examples:

- rows representing the order affected by the scenario;
- an aggregate balance for one account;
- status/history rows created by the operation.

A subject may use different MSSQL and PostgreSQL queries, but both queries must project the same declared logical column names.

### Capture sides and moments

For a side-effect comparison, each subject has four captures:

```text
legacy / before
legacy / after
target / before
target / after
```

The tool computes:

```text
legacy_delta = diff(legacy_before, legacy_after)
target_delta = diff(target_before, target_after)
```

Parity comparison is then performed between `legacy_delta` and `target_delta` under the behavior contract.

Absolute legacy-vs-target state comparison is allowed only when the feature contract explicitly requires it and the fixture contract establishes that the two starting states are logically equivalent. It is never the default.

### Delta shape

For keyed record sets, the structural delta is:

- `added`: keys absent before and present after;
- `removed`: keys present before and absent after;
- `updated`: same key present on both sides with one or more changed projected fields;
- `unchanged_count`: informational only.

Updated rows preserve the old and new raw canonical values so a later comparator can apply exact/tolerant/normalized semantics without re-querying the database.

## Feature-local capture plan

When DB assertions are required for a feature, use one optional supporting artifact:

```text
migration/features/<feature-id>/db-comparison-plan.json
```

This is not a seventh canonical singleton artifact and is not required for features with no decision-relevant DB comparison.

The plan is version-controlled because it contains the reproducible **definition of what to capture**, not credentials or captured row values.

Minimum v1 shape:

```json
{
  "version": 1,
  "feature_id": "example-feature",
  "subjects": [
    {
      "subject_id": "db-001",
      "mode": "delta",
      "comparison_rule_ref": "behavior-contract.md :: <comparison subject>",
      "key_columns": ["business_id"],
      "columns": ["business_id", "status", "amount"],
      "required_parameters": ["business_id"],
      "max_rows": 1000,
      "legacy_query": "SELECT ... AS business_id, ...",
      "target_query": "SELECT ... AS business_id, ...",
      "safe_to_render_values": false
    }
  ]
}
```

Rules:

1. `subject_id` is stable within the feature and used by snapshots, diffs, reports, and negative-control records.
2. Queries must explicitly project the declared `columns`; `SELECT *` is invalid.
3. Query results must expose exactly the declared logical column names after aliases are applied.
4. `key_columns` are required for multi-row record sets. A one-row aggregate subject may use an empty key list only when the plan declares that one row is expected.
5. Keys should represent business identity/correlation where possible. A physical surrogate key may be used only when the behavior contract makes it comparison-significant.
6. Runtime parameter **values** are supplied from the scenario fixture/run and are not stored in the plan.
7. `max_rows` is a hard safety bound. Exceeding it makes the subject BLOCKED; no snapshot may silently truncate and continue.
8. `safe_to_render_values` defaults to `false`. Raw values are not written into Markdown/stdout unless a subject has been explicitly approved as sanitized/non-sensitive.

The initial implementation should use JSON and the Python standard library; adding YAML or an ORM is not justified by the current requirement.

## Read-only source boundary

The future tool should expose a minimal read-only source protocol conceptually equivalent to:

```text
capture(query, parameters) -> columns + rows + source metadata
```

It must not expose `execute`, `commit`, migration, seed, reset, stored-procedure execution, or arbitrary write methods through the snapshot interface.

Safety requirements:

1. The DB principal used for capture must be read-only at the database/server permission layer wherever technically possible. This is the primary control.
2. Connection-profile enforcement from Issue #20 is mandatory before real DB capture is considered production-ready.
3. The capture layer additionally rejects statements it cannot conservatively classify as read-only. `EXEC`, DML, DDL, multi-statement batches, and write-capable constructs such as `SELECT INTO` are not valid snapshot queries.
4. Where the engine supports a read-only transaction/session mode, enable it as defense in depth.
5. If the tool cannot prove that the configured source is read-only, it returns BLOCKED before executing the query.
6. Credentials and connection strings are supplied through the future profile/secret mechanism and never appear in the capture plan, snapshot JSON, report, or logs.

MSSQL and PostgreSQL do not need a shared SQL dialect. The common abstraction is only the read-only row-capture result; engine-specific query text remains explicit in the plan.

## Snapshot format

Canonical snapshots are JSON with a versioned envelope. A snapshot records, at minimum:

- format version;
- feature ID;
- run ID;
- scenario/fixture reference;
- subject ID;
- side (`legacy` or `target`);
- moment (`before` or `after`);
- engine name;
- non-secret environment/profile identity;
- schema/build revision metadata needed for reproduction;
- query digest and parameter-name set, but not credential material;
- declared columns and key columns;
- row count;
- canonical typed row values;
- capture timestamp;
- content SHA-256.

Canonical value encoding must preserve distinctions that ordinary JSON/CSV can lose. At minimum, the implementation must distinguish null, boolean, integer, decimal, floating-point, text, date/time, and binary values. Decimal values must not be coerced through binary floating point; binary values use an explicit encoding. Unsupported driver-specific types fail capture until an explicit canonical representation is defined.

Rows are stored in deterministic key order after duplicate-key validation. Sorting is an encoding detail only; order significance still comes from the behavior contract.

## Snapshot pairing invariants

A before/after pair is valid only when:

- feature, subject, side, and run identity match;
- query digest, logical columns, key columns, and capture-plan version match;
- the same fixture/scenario identity is recorded;
- neither capture exceeded the row bound;
- no duplicate logical key exists;
- both captures completed successfully.

A legacy/target comparison is valid only when the two deltas share the same feature, scenario/fixture identity, subject ID, logical columns, and declared comparison-rule reference. Physical engine/schema revision metadata may differ and must remain visible in the report.

Mixing artifacts from different runs or different query revisions is BLOCKED, never best-effort matched.

## Comparison-semantics ownership

`db_snapshot_diff.py` owns deterministic capture serialization and **raw structural delta calculation**. It does not invent business equivalence.

The concrete future `DbAssertionPort` adapter owns orchestration of those artifacts and applies only comparison semantics already declared by:

- the subject's referenced row in `migration/features/<feature-id>/behavior-contract.md` `## Comparison semantics`; or
- an explicit Rulebook rule referenced from that row.

Consequences:

1. No normalization/tolerance/order rule may live only in `db_snapshot_diff.py`, the capture plan, or the adapter.
2. The capture plan's `comparison_rule_ref` is traceability, not a second specification of the rule.
3. If the behavior-contract rule is missing, ambiguous, placeholder-only, or requires a comparator the implementation does not support, DB verification is BLOCKED rather than defaulting to exact or permissive comparison.
4. Initial implementation may support a narrow comparator set. Unsupported declared semantics are a truthful blocker; they are not a reason to build a general expression language.
5. The adapter must compare deltas at the logical subject level. Physical table/column/schema similarity is not parity evidence by itself.

## Judge integration

`DbAssertionPort` remains the single composite-judge source name (`db-assertions`). One scenario may contain several DB subjects; the concrete adapter aggregates them:

- every required subject compared successfully and matches -> `PASS`;
- at least one required subject compared successfully and mismatches -> `FAIL`;
- comparison completed but the available evidence is genuinely incomplete and still meaningful -> `INSUFFICIENT`;
- required capture/comparison preconditions are absent, unsafe, or specification-blocked -> do not claim a DB result; the expected source remains unsatisfied and the verification is `BLOCKED` under the existing composite-judge rules.

The adapter detail/report must list the per-subject result rather than collapsing all DB evidence into one opaque sentence.

A feature with no decision-relevant DB effect does not add `db-assertions` to `expected_sources`. “DB source not required” and “DB source required but unavailable” are distinct states.

## Mandatory negative control

When `db-assertions` is decision-relevant, the Issue #11 self-check must include the effective DB adapter/configuration.

The safe control boundary is the comparator input:

1. capture or stage a valid baseline snapshot/delta pair;
2. create a **local synthetic mutation** of one comparison-significant canonical value or row operation;
3. declare which DB subject/comparator must detect it;
4. run the same adapter/comparison configuration used for the real verdict;
5. require the DB detector to reject the known-wrong pair.

Do not modify a shared MSSQL/PostgreSQL database just to test the judge. A no-op mutation after the feature's declared normalization is a failed self-check, matching the existing judge-self-check contract.

## Runtime artifact and data-safety policy

Raw snapshots and raw row-level diff artifacts are runtime evidence and may contain sensitive company data. Default location:

```text
.artifacts/db/<feature-id>/<run-id>/
```

The implementation pass must add the runtime artifact root to `.gitignore` before the first real capture.

Git-tracked durable artifacts may contain:

- capture/diff format version;
- subject/run IDs;
- query/plan/snapshot digests;
- row/change counts;
- changed column names;
- PASS/FAIL/BLOCKED reason;
- explicitly sanitized values only when policy permits them;
- an approved external secure-artifact reference if one exists.

They must not contain unreviewed production-derived row values, DB credentials, or connection strings.

Because the current repository does not define an approved secure raw-evidence store, Git is **not** treated as one by default. If long-term raw snapshot retention becomes required, that storage decision is a separate design item.

## Verification report contract

`migration/features/<feature-id>/verification.md` remains the canonical report. Its DB section should record one row per subject with:

- subject ID;
- mode (`delta` or explicitly approved `state`);
- comparison-rule reference;
- legacy capture/delta digest/reference;
- target capture/delta digest/reference;
- structural change summary;
- semantic comparison result;
- evidence grade / caveat.

Markdown rendering from the tool is a convenience renderer for this structure, not an alternative source of truth. By default it omits raw values unless `safe_to_render_values` is explicitly true.

## Future CLI boundary

The implementation should remain small. A sufficient initial interface is conceptually:

```text
python scripts/db/db_snapshot_diff.py capture ...
python scripts/db/db_snapshot_diff.py delta ...
python scripts/db/db_snapshot_diff.py render ...
```

`capture` reads one side/moment from a declared plan subject and produces canonical JSON.

`delta` consumes two compatible snapshots and produces a deterministic raw delta without contacting a database.

`render` produces a sanitized Markdown summary from snapshot/delta metadata.

Semantic legacy-vs-target PASS/FAIL belongs to the concrete DB judge adapter, not a hidden `compare --guess-rules` path inside the utility.

## Test requirements for implementation

At minimum, later implementation tests should cover:

- deterministic canonical JSON and digest for identical inputs;
- null versus empty string distinction;
- decimal fidelity without float coercion;
- binary/date/time encoding;
- unordered input rows producing the same keyed snapshot;
- duplicate keys rejected;
- missing keys for a multi-row subject rejected;
- query/column mismatch rejected;
- row-limit overflow BLOCKED with no partial success;
- added/removed/updated delta calculation;
- cross-run or query-digest mismatch rejected;
- non-read-only query rejection;
- read-only-profile failure before query execution;
- raw values omitted from Markdown by default;
- a staged known-wrong DB mutation being detected by the same adapter used for parity.

Driver-specific tests for MSSQL/PostgreSQL come only after the relevant connection/profile/bootstrap issues are implemented and a safe test environment exists.

## Dependency and sequencing rules

- The file-to-file canonicalization/delta engine can be implemented and unit-tested without live DB access.
- Live MSSQL capture must not be treated as ready until the Issue #18 read-only access path and Issue #20 safety/profile contract are implemented.
- Legacy side-effect parity requires a reproducible test MSSQL fixture from Issue #19 or another approved equivalent; do not run side-effect characterization against production.
- Target side-effect parity requires a reproducible PostgreSQL test fixture/bootstrap path from Issue #21 or another approved equivalent.
- The DB adapter cannot produce a trusted judge result until the Issue #11 negative-control gate passes for its exact effective configuration.
- Non-exact comparison remains governed by Issue #12; this design does not create a second semantics language.

## Non-goals

Issue #22 does not design or implement:

- production-to-test data synchronization or masking;
- PostgreSQL schema migration/reset tooling;
- DB write routing/authorization;
- execution of the legacy or target business scenario;
- schema equivalence or automatic MSSQL-to-PostgreSQL DDL comparison;
- a general SQL abstraction layer or ORM;
- a free-form comparison-rule expression language;
- secure long-term storage for sensitive raw evidence.

## Acceptance criteria

The design is ready for a later implementation pass when:

- a low-reasoning verifier has a deterministic capture -> delta -> semantic DB assertion flow;
- whole-database comparison is not the default oracle;
- DB queries are feature-scoped, explicitly projected, keyed, bounded, and reproducible;
- the tool can never require write capability to capture/diff evidence;
- canonical snapshots preserve material value distinctions and cannot silently truncate;
- comparison semantics remain owned by the behavior contract/Rulebook;
- raw sensitive rows are not committed by default;
- `DbAssertionPort` integration and the mandatory negative-control boundary are explicit;
- MSSQL/PostgreSQL provisioning and write-safety responsibilities remain in their separate issues instead of being duplicated here.
