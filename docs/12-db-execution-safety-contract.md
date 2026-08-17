# DB Execution Safety Contract

Issue: #20 — repository-owned DB tooling currently has no enforceable boundary that prevents a write-capable operation from reaching a production database.

This document defines the design only. It does not implement `scripts/db/db_guard.py`, change DB credentials, add connection profiles, or modify DB tools. Those changes remain implementation work gated by `AGENTS.md` rule 13.

## Goal

Make the safe DB execution boundary deterministic for low-reasoning agents:

- production databases are read-only evidence sources for repository tooling;
- every operation capable of changing DB state is allowed only against an attested test target;
- a mislabeled or misconfigured logical profile fails closed rather than being trusted by name;
- stored procedures, batches, DDL, and parser-ambiguous SQL cannot bypass the same boundary;
- hazardous attempts are auditable without leaking credentials, parameters, PII, or production rows;
- Issue #18/#19/#21/#22 DB tools consume one guard instead of inventing per-tool safety rules.

The design applies to repository-owned migration/verification DB tooling for legacy MSSQL and target PostgreSQL. It does not replace database-server permissions, network controls, or the canonical secret-injection contract.

## Adversarial findings

The issue identifies the correct blast-radius risk, but the literal recommendation is insufficient as a safety design.

1. Blocking only `INSERT`, `UPDATE`, `DELETE`, and `EXEC` misses `MERGE`, `TRUNCATE`, DDL, privilege changes, `SELECT ... INTO`, bulk-load commands, and vendor-specific operations that can change state.
2. Keyword matching is not a trustworthy authorization mechanism. Comments, batches, dynamic SQL, quoted text, stored-procedure bodies, and dialect differences make naive string scanning bypassable or overly restrictive.
3. A profile name containing `test` or `readwrite` is not proof that the resolved connection reaches a test system. A name-only guard authorizes the exact configuration mistake it is meant to stop.
4. A warning that a test hostname “looks similar” to production is not a safety boundary. Hazardous execution requires a positive target-identity match; ambiguity blocks.
5. Application-level guards are secondary controls. If the production credential can write, one missed code path, raw cursor leak, ad-hoc script, or guard bug can still damage production.
6. Treating `EXEC` as safe when a procedure name looks read-only is unsafe. Stored procedures can hide DML, dynamic SQL, trigger effects, cross-database calls, or external side effects.
7. Logging full SQL with literal values can leak PII, secrets, or business data. Auditability requires a redacted statement representation plus a stable hash, not unconditional raw-value logging.
8. A `--force`, `--unsafe`, confirmation prompt, or environment-variable bypass would move the safety decision back to the low-reasoning caller. The production-write invariant must have no routine runtime override.
9. A common helper is insufficient if callers can still import DB drivers directly and obtain raw writable connections. Repository-owned tooling needs a detectable narrow driver boundary.
10. Issue #23 has now defined the canonical logical profiles and environment-variable injection contract. Issue #20 must consume that registry rather than creating competing profile names or a second secret/config path.
11. “Run the production mutation inside a transaction and roll it back” is not a safe exception. Locks, identity/sequence consumption, trigger or external side effects, and operational impact can occur before rollback.

## Authority and dependency boundary

This contract owns:

- runtime target-identity attestation;
- issuance of read-only versus test-write capabilities;
- operation hazard classification;
- production write/DDL/procedure blocking;
- hazardous-operation audit semantics;
- guard bypass prevention for repository-owned DB tooling.

`docs/12-db-connection-secrets-contract.md` (Issue #23) remains authoritative for:

- canonical logical profile names;
- fixed environment-variable mappings;
- secret injection and redaction rules;
- configuration-resolution failures.

`docs/issue-19-mssql-test-materialization.md` remains authoritative for the one-way production-to-test materialization manifest, data/object allowlisting, sanitization provenance, and source-consistency semantics.

If these documents differ, #23 owns profile/injection vocabulary, #19 owns materialization semantics, and this document owns runtime DB execution safety.

## Safety model

The safety boundary is layered. Later implementation must preserve this order of trust.

```text
DB server/network policy
        |
        v
Issue #23 logical profile + secret injection
        |
        v
connection + actual target identity attestation
        |
        v
capability-specific guarded API
        |
        v
operation classification + audit
        |
        v
approved engine connector / DB driver
```

No lower layer may weaken a failed higher-layer check.

### Layer 1 — server-side least privilege is primary

The canonical production profile `mssql-prod-ro` is a read-only profile and must use a DB-server-enforced read-only credential for production-facing repository tooling.

Production inspection credentials must:

- allow only the metadata/catalog reads and `SELECT` access required by approved discovery/snapshot work;
- deny DML and DDL;
- deny write-capable stored-procedure execution;
- avoid ownership/admin roles and broad inherited permissions;
- be network-separated from test-write credentials where infrastructure permits.

The guard must never verify read-only status by attempting a write. Provisioning/grant evidence establishes the server-side control; the code guard independently refuses production hazardous execution even if the credential is accidentally over-privileged.

A production credential known to have write privileges is a safety defect. Repository tooling must not treat the Python guard as justification for continuing with that credential.

### Layer 2 — consume the canonical profile registry

Issue #23 defines the initial public profile set:

| Profile | Environment variable | Engine | Environment | Capability |
| --- | --- | --- | --- | --- |
| `mssql-prod-ro` | `MSSQL_PROD_RO_CONN` | MSSQL | production | read-only |
| `mssql-test-rw` | `MSSQL_TEST_RW_CONN` | MSSQL | test | read-write |
| `postgres-test-rw` | `PG_TEST_RW_CONN` | PostgreSQL | test | read-write |

The guard accepts these logical profiles through the #23 resolver. It does not accept raw connection strings, arbitrary environment-variable names, host/user/password triples, caller-defined profile aliases, or a production read-write profile.

For execution safety, each profile also needs non-secret expected-target metadata owned by this contract:

```text
profile_id: <Issue #23 canonical profile>
expected_target:
  server_identity: <approved exact identity sufficient to distinguish environment>
  database_identity: <approved exact database identity>
```

The expected identity is safety metadata, not a credential. The implementation may choose a minimal repository/config representation later, but it must not create a second path for connection secrets.

Configuration/preflight rejects execution when:

- the profile is not in the #23 registry;
- profile engine/environment/capability metadata differs from #23;
- expected target identity is missing or ambiguous;
- a write-capable profile is not `test + read-write`;
- a test target identity equals an approved production identity;
- required safety metadata cannot be resolved exactly.

Unknown or malformed safety metadata fails closed.

### Layer 3 — attest the actual connected target

Before exposing a usable DB session, the guard queries the connected server with engine-specific read-only identity probes and compares the result with the expected target.

Attestation establishes at minimum:

- actual DB engine;
- actual server/instance identity sufficient to distinguish environments;
- actual database identity.

A test-write capability is issued only when all are true:

```text
profile is canonical under Issue #23
AND profile.environment == test
AND profile.capability == read-write
AND actual engine == profile.engine
AND actual server identity == expected server identity
AND actual database identity == expected database identity
```

Any mismatch, missing identity, probe failure, timeout, or ambiguous result blocks the session before caller SQL is executed.

Production read sessions also require identity attestation. A wrong production database is not acceptable merely because the requested operation is read-only.

Hostname similarity may be emitted as a diagnostic, but it is never an authorization rule and cannot convert an identity mismatch into PASS.

### Layer 4 — expose capabilities, not raw connections

Repository DB tools must not receive a raw connection/cursor as their normal public interface.

The common guard should expose separate capabilities conceptually equivalent to:

```text
open_readonly(profile) -> ReadOnlySession
open_test_readwrite(profile) -> TestWriteSession
```

`ReadOnlySession` exposes query/metadata operations only. It does not expose a generic raw driver `execute` path that callers can reuse for mutation.

`TestWriteSession` is created only after test-target attestation and exposes hazardous execution through one guarded path that classifies and audits the operation before delegating to the approved engine connector.

The capability API is the authorization boundary. SQL text inspection is defense in depth, not the sole permission mechanism.

### Layer 5 — operation classes

Every repository-owned DB action has one effective operation class before execution:

| Class | Examples | Allowed target |
| --- | --- | --- |
| `read` | catalog queries, schema inspection, ordinary `SELECT` | attested production read-only or attested test |
| `mutation` | `INSERT`, `UPDATE`, `DELETE`, `MERGE`, data load, `SELECT INTO` | attested test read-write only |
| `ddl` | `CREATE`, `ALTER`, `DROP`, `TRUNCATE`, schema migration/reset | attested test read-write only |
| `procedure-exec` | stored-procedure execution, including unknown side effects | attested test read-write only |
| `privileged` | permission/role/server configuration operations | denied by default; separate design/approval if ever required |
| `unknown` | unclassified or parser-ambiguous statement | denied |

Rules:

- `EXEC`/procedure calls are hazardous by default; procedure naming never proves read-only behavior.
- a multi-statement batch inherits the most hazardous class of any statement;
- a batch containing `unknown` is denied rather than downgraded to read;
- comments, whitespace, case, or statement ordering must not change authorization;
- dynamic SQL hidden inside a procedure is one reason procedure execution remains hazardous even when the outer call text is simple;
- transaction/rollback wrapping does not downgrade a hazardous operation;
- if a later implementation uses a SQL parser, parser failure is a block, never a reason to permit execution.

## Required execution flow

Every repository-owned DB call follows the same sequence:

```text
1. resolve canonical profile through Issue #23
2. validate non-secret safety metadata / tool profile allowlist
3. obtain the opaque connection value through Issue #23
4. connect through the approved engine connector
5. attest actual engine/server/database identity
6. construct only the capability permitted for that profile
7. classify the requested operation
8. enforce capability + target rule
9. emit required pre-execution audit event for hazardous operations
10. execute through the guarded connector boundary
11. emit result/failure audit event without sensitive values
```

If steps 1-9 do not complete successfully, the driver must not receive a hazardous statement.

## Production read-only behavior

Production is a discovery/evidence source, not an execution target for characterization side effects.

Allowed examples on `mssql-prod-ro` after identity attestation:

- schema/catalog queries required by Issue #18;
- authorized table/view reads needed for evidence or #19 materialization input;
- reading stored-procedure/function/trigger definitions from metadata/catalogs;
- read-only snapshot extraction for parity preparation.

Disallowed through repository tooling:

- DML or DDL;
- production-to-test materialization writes on the source connection;
- characterization execution that mutates production state;
- stored-procedure execution, even when its name appears read-only;
- mutation experiments followed by rollback;
- privilege or administrative commands.

A production read-only capability rejects hazardous requests before driver execution even if the underlying account was accidentally granted broader permissions.

## Test read-write behavior

Writable execution is allowed only on an attested canonical test profile and for a concrete repository workflow such as:

- Issue #19 applying reviewed schema/data into `mssql-test-rw`;
- characterization tests that intentionally reproduce legacy side effects on `mssql-test-rw`;
- Issue #21 bootstrapping/resetting `postgres-test-rw`;
- target-side schema migrations or fixture setup on `postgres-test-rw`.

A test read-write capability does not authorize arbitrary administration. `privileged` remains denied until a later requirement explicitly designs and authorizes that path.

## Related DB tooling contract

All DB tooling issues compose with this boundary rather than creating connection safety independently.

### Issue #18 — MSSQL production inspection

- allowed profile: `mssql-prod-ro`;
- capability: `ReadOnlySession` only;
- no writable connection API and no procedure execution merely to inspect a definition;
- procedure/trigger/function text is read from metadata/catalog sources.

### Issue #19 — MSSQL test materialization

The one-way materializer uses two fixed roles:

```text
source = mssql-prod-ro   -> ReadOnlySession
target = mssql-test-rw  -> TestWriteSession
```

The source can only extract. Every schema/data apply or reset action is executed through the attested test write session. Source/target identity collision, role swapping, or configuration that points the test profile at production fails before a write.

The guard does not own #19's manifest, masking/classification, fresh-target, source-consistency, or evidence rules.

### Issue #21 — PostgreSQL test bootstrap

Future PostgreSQL schema/reset tooling uses `postgres-test-rw` under the same `test + read-write + attested target` rule. Engine differences may change the identity probe/connector, not the safety semantics.

### Issue #22 — DB snapshot/diff

Snapshot capture is read-only. A snapshot tool does not receive a writable execution path merely because it may read from a test read-write profile.

### Issue #23 — DB connection/secrets

`docs/12-db-connection-secrets-contract.md` supplies the fixed profiles and environment-variable injection. The guard consumes that resolver and adds target attestation/capability enforcement; it does not auto-load `.env`, accept raw connection strings, or expose secret values in diagnostics.

## Audit contract

Every hazardous execution attempt that reaches guarded pre-execution emits a structured audit event to stdout/stderr or an explicit caller-provided sink.

At minimum:

```text
timestamp
tool/workflow identifier
profile_id
engine
environment
capability
attested server identity
attested database identity
operation class
normalized/redacted SQL preview
statement hash
outcome: allowed | blocked | succeeded | failed
block/failure reason when applicable
```

Do not log:

- passwords, tokens, connection strings, or expanded secret environment variables;
- raw parameter values by default;
- production/sanitized row values;
- unredacted SQL literals when they may contain PII or confidential business data.

The statement hash allows correlation without turning the audit log into a second data-leak surface.

Issue #19 may persist higher-level materialization evidence under its own contract; that evidence references guard/run metadata rather than weakening these redaction rules.

## No bypass contract

The routine implementation must not provide:

- `--force-production-write`;
- `--unsafe`;
- “type YES to continue” production bypasses;
- an environment variable that disables identity attestation;
- a caller flag that reclassifies `unknown` as `read`;
- a caller-supplied raw connection string;
- access to the underlying raw writable cursor/connection from normal tooling APIs.

If an exceptional production-changing operation is ever genuinely required, it is a separate operational procedure with separate authorization and infrastructure controls, not an escape hatch in migration tooling.

## Bypass prevention in repository structure

A common helper is useful only if repository-owned DB tooling cannot silently bypass it.

Later implementation should establish a narrow boundary such as:

```text
scripts/db/
  db_guard.py                    profile/safety/capability boundary
  connectors/                    engine-specific driver + identity probes
  mssql_inspect.py               Issue #18 caller
  mssql_materialize_test.py      Issue #19 caller
  ...
```

CI/static validation should reject direct DB-driver imports or direct connection creation in repository-owned migration DB tools outside the approved connector/guard boundary. The implementation may use AST/import checks or an equivalent deterministic rule; it must not rely only on code-review convention.

Explicit test/fake exceptions that cannot reach a real DB may be enumerated. Exceptions are never inferred from filenames or caller intent.

This restriction applies to repository-owned migration/verification DB tooling, not automatically to the future FastAPI application's normal persistence layer; that layer has a different runtime responsibility and must not be accidentally coupled to migration-tooling policy.

## Failure behavior

The guard fails closed for all safety uncertainty.

| Condition | Result |
| --- | --- |
| unknown/non-canonical profile | block |
| Issue #23 profile resolution fails | block |
| missing/ambiguous expected target | block |
| actual engine/server/database differs from expected target | block |
| target identity probe fails | block |
| write-capable request is not canonical `test + read-write` | block |
| hazardous operation requested from `ReadOnlySession` | block before driver execution |
| procedure execution on production | block |
| mixed batch contains mutation/DDL/procedure/unknown | production: block; test: require attested write session |
| operation classifier/parser cannot decide | block |
| required hazardous pre-audit cannot be emitted | block hazardous execution |

A blocked hazardous request is a safety result, not an invitation for the agent to retry through a lower-level driver API.

## Interaction with STOP conditions

This contract does not redefine `docs/11-stop-condition-contract.md`.

Examples:

- an unknown stored procedure's side effects remain `SC-05`; production execution must not be used to resolve that unknown;
- a destructive migration assumption remains `SC-04` when a design decision depends on it;
- a guard block caused by a known safety policy is not automatically a new open question;
- if the project cannot identify which actual server/database corresponds to a configured test profile, that deployment/target fact is unresolved and must not be guessed into expected-target metadata.

The guard protects execution even when the unknown is non-blocking for unrelated discovery work.

## Implementation acceptance criteria

Issue #20 implementation is complete only when all of the following are true:

1. the guard consumes the canonical Issue #23 profile resolver (`mssql-prod-ro`, `mssql-test-rw`, `postgres-test-rw`) and does not introduce a second secret/config path;
2. production-facing repository DB tooling uses a documented DB-server-enforced read-only production credential; known write-capable production credentials are rejected as a safety defect;
3. every canonical profile used by the guard has explicit expected server/database identity metadata;
4. every opened session attests actual engine/server/database identity before becoming usable;
5. writable capability is issued only for canonical `test + read-write` profiles after exact target attestation;
6. production/read-only sessions expose no generic mutation execution API;
7. stored-procedure execution is hazardous by default and cannot reach production;
8. mutation, DDL, procedure execution, unknown statements, rollback-wrapped mutations, and hazardous mixed batches cannot reach production through the guard;
9. hazardous execution has pre-execution audit records with target/profile/operation identity but without connection values, secrets, parameters, or row values;
10. no routine runtime override disables production-write protection, profile allowlists, or target attestation;
11. Issue #18/#19/#21/#22 tools consume the common boundary instead of creating direct connections independently;
12. CI or an equivalent deterministic repository check detects unauthorized direct driver/connection usage in repository-owned migration DB tooling;
13. tests cover at least:
   - `mssql-prod-ro` read query allowed after correct identity attestation;
   - production mutation blocked before driver execution;
   - production DDL blocked;
   - production procedure execution blocked;
   - production mutation remains blocked when wrapped in an explicit rollback transaction;
   - `mssql-test-rw` mutation allowed only after exact test identity match;
   - test profile misconfigured to a production identity blocked;
   - source/target identity collision blocked;
   - missing/ambiguous target identity blocked;
   - mixed read/write batch cannot be downgraded to read;
   - classifier failure blocks rather than permits;
   - audit output omits connection values, credentials, parameters, and row values;
   - normal tooling cannot obtain/use a raw writable connection to bypass the guard.

Actual production mutation is never used as a test case for this guard. Unit/integration tests use fakes or approved test infrastructure to prove the production branch blocks before the driver sees the hazardous operation.

## Non-goals

This design does not:

- implement a SQL parser;
- redefine Issue #23's canonical profiles or secret-injection mechanism;
- decide #19 masking/subsetting/materialization semantics;
- implement Issue #18/#19/#21/#22 tools;
- grant or alter database-server permissions;
- define an emergency production-write procedure;
- govern arbitrary external scripts that intentionally bypass this repository;
- define the future FastAPI application's ordinary PostgreSQL persistence architecture.

It defines the repository-owned execution-safety contract those migration/verification tools must follow.
