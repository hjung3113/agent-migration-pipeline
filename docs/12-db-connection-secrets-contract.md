# DB Connection and Secret Injection Contract

Issue: #23 — migration DB tooling needs one deterministic way to select database targets and receive credentials without committing secrets or letting agents pass arbitrary connection strings.

This document defines the design only. `.env.example`, DB helper modules, DB scripts, validators, and agent/skill changes are implementation work and remain gated by `AGENTS.md` rule 13 until the user explicitly authorizes implementation.

## Goal

Provide a minimal connection contract that every migration DB tool can consume consistently while making the safe path the easiest path for low-reasoning agents.

The contract must answer, before any DB tool runs:

1. which logical database profile is allowed;
2. which environment variable supplies that profile's opaque connection value;
3. whether the profile is production/test and read-only/read-write;
4. what must happen when configuration is missing, malformed, or ambiguous;
5. what data must never be written to Git, logs, evidence, or command history.

## Current repository facts

- `.gitignore` already ignores `.env` and `.env.*`, with `!.env.example` explicitly re-allowing the example file.
- No `.env.example` currently exists.
- `docs/05-open-questions.md` OQ-021 asks how the **legacy DLL** receives configuration/secrets. That question remains open and is not the same decision as this pipeline's own DB-tooling secret injection mechanism.
- Issues #18 through #22 introduce DB inspection, synchronization, write guarding, PostgreSQL test bootstrap, and DB snapshot/diff needs. They must share one connection-profile vocabulary rather than inventing per-tool conventions.

## Adversarial findings

Issue #23 identifies a real prerequisite, but several literal fixes would create new failure modes.

1. A committed `config/db_connections.example.json` encourages a parallel file-based configuration path. If tools support both config files and environment variables, agents can choose inconsistently and secret-bearing local files become an attractive accidental source of truth.
2. Accepting raw connection strings as CLI arguments leaks credentials into shell history, process listings, logs, copied command transcripts, and evidence artifacts.
3. Environment-variable names alone are insufficient if each tool independently decides what a name means. The profile must also encode environment and capability.
4. A production read-write profile should not exist in the migration-tooling contract. Merely telling agents not to use one is weaker than making it unavailable.
5. Missing credentials must not trigger fallback defaults such as localhost, integrated authentication, a developer account, or a neighboring profile. Silent fallback can redirect a supposedly safe operation to the wrong database.
6. Logging the selected profile is useful for auditability; logging the underlying connection value is not. Exception handling and debug output must preserve this distinction.
7. OQ-021 must remain independent. Discovering that the legacy DLL uses app.config, registry, encrypted files, or another mechanism does not change this pipeline contract unless a later approved design explicitly does so.

## Canonical logical profiles

The initial profile set is deliberately small:

| Logical profile | Environment variable | Engine | Environment | Capability | Intended consumers |
| --- | --- | --- | --- | --- | --- |
| `mssql-prod-ro` | `MSSQL_PROD_RO_CONN` | MSSQL | production | read-only | legacy schema/source inspection, production-side snapshot reads |
| `mssql-test-rw` | `MSSQL_TEST_RW_CONN` | MSSQL | test | read-write | test synchronization destination, characterization runs that require writes |
| `postgres-test-rw` | `PG_TEST_RW_CONN` | PostgreSQL | test | read-write | target bootstrap/migrations, target characterization/parity runs |

Rules:

- These logical names are the public interface used by migration tooling.
- The environment-variable names are fixed mappings, not user-selectable aliases.
- There is no production read-write profile.
- Adding another profile is a design change, not an ad hoc runtime option.
- Connection values are opaque driver-specific strings. Tooling must not rewrite credentials, invent missing fields, or silently switch authentication modes.

## Injection contract

DB tools receive only a logical profile selector such as `--profile mssql-prod-ro`.

They must not accept any of the following as supported CLI input:

- raw connection strings;
- database passwords;
- arbitrary environment-variable names;
- host/user/password triples;
- paths to secret-bearing connection config files.

The tool resolves the fixed environment-variable mapping internally and reads the value from the process environment.

A local `.env` file may be used by a developer's shell, IDE, container runtime, or external environment loader to populate the process environment, but repository DB scripts must not require or auto-load `.env`. This avoids adding a second configuration mechanism or a dotenv dependency solely for secret loading.

CI or a future secret manager may inject the same environment variables. The DB tools remain unaware of the upstream secret store.

## Fail-closed behavior

Connection resolution returns an error before opening a DB connection when any of these conditions hold:

- the logical profile is unknown;
- the mapped environment variable is unset;
- the mapped environment variable is empty or whitespace;
- a tool requests a profile outside its explicit allowlist;
- a write-capable operation requests a profile whose declared capability is read-only.

There is no profile fallback, inferred alias, implicit default database, or automatic substitution.

Target-identity verification and SQL write enforcement are owned by Issue #20's DB guard design. This contract supplies the declared profile metadata that the guard consumes; it does not claim that a profile name alone proves the actual server identity or server-side permissions.

## Secret-handling invariants

The following values are secrets and must never be committed or persisted as migration evidence:

- full connection strings;
- passwords, access tokens, client secrets, or embedded credentials;
- expanded environment-variable values;
- exception/debug output that reproduces any of the above.

Allowed durable/audit data is limited to non-secret metadata such as:

- logical profile name;
- engine/environment/capability;
- environment-variable **name**;
- operation type;
- sanitized target identity returned by a DB guard when that later design permits it.

Logs and errors may say `MSSQL_PROD_RO_CONN is not set`; they must not include the value of `MSSQL_PROD_RO_CONN`.

DB scripts must not emit all environment variables, driver diagnostics containing connection strings, or command examples containing real-looking credentials.

## `.env.example` contract for later implementation

The repository example file exists only to document the required variable names. Its canonical payload is:

```dotenv
MSSQL_PROD_RO_CONN=
MSSQL_TEST_RW_CONN=
PG_TEST_RW_CONN=
```

Requirements:

- right-hand sides remain empty;
- comments may explain profile purpose but must not include production-looking hosts, usernames, passwords, tokens, or realistic secret examples;
- `.env.example` is safe to commit;
- `.env`, `.env.*`, and other secret-bearing local variants remain ignored, with `.env.example` as the only intended exception;
- because the current `.gitignore` already provides those rules, implementation should not churn `.gitignore` unless the chosen implementation introduces an additional secret-bearing local path.

## Tool-specific consumption

### Issue #18 — MSSQL production inspection

- allowed profile: `mssql-prod-ro` only;
- no raw connection input;
- operation remains read-only even if the underlying account is misconfigured with broader server permissions.

### Issue #19 — production-to-test MSSQL synchronization

- source profile: `mssql-prod-ro`;
- destination profile: `mssql-test-rw`;
- source and destination roles are fixed, not swappable free-form CLI arguments;
- the later DB guard must reject unsafe target identity/capability combinations before writes.

### Issue #20 — DB write guard

- consumes the canonical profile registry above;
- enforces operation capability and verifies actual target identity independently of the profile label;
- treats server-side least privilege as the primary defense and application guard logic as defense in depth.

### Issue #21 — PostgreSQL test bootstrap

- allowed write profile: `postgres-test-rw` only;
- no production PostgreSQL profile is introduced by this issue.

### Issue #22 — DB snapshot/diff

- accepts only logical profiles needed by the selected comparison scenario;
- snapshots are read operations even when executed through a test read-write profile;
- snapshot/evidence output must never contain connection values.

## Ownership and dependency boundary

This contract owns:

- profile names;
- fixed environment-variable mapping;
- injection method;
- fail-closed configuration resolution;
- secret redaction/persistence rules.

It does not own:

- DB server account provisioning or grants;
- production/test host identity checks;
- SQL classification or write blocking;
- PII masking/sanitization;
- DB migration/reset strategy;
- snapshot comparison semantics;
- the legacy DLL's current secret/config mechanism.

Those concerns remain with their dedicated issues/designs.

## Later implementation shape

After explicit implementation authorization, use the smallest shared implementation that prevents convention drift:

1. add `.env.example` with the three empty canonical variables;
2. add one shared DB connection-profile resolver under `scripts/db/` containing the fixed registry and fail-closed lookup/redaction behavior;
3. require all DB tools from Issues #18-#22 to consume logical profiles through that resolver instead of reading arbitrary connection inputs directly;
4. make the DB guard from Issue #20 consume the resolver's engine/environment/capability metadata;
5. extend scaffold/CI validation only enough to ensure the canonical `.env.example` keys stay present and empty and the ignore rules continue to protect secret-bearing `.env` variants;
6. add focused tests for unknown profile, missing/empty environment variable, forbidden profile/tool combination, and no-secret error rendering.

No secret manager SDK, configuration framework, credential rotation service, or extra profile abstraction is required for Phase 0.

## Acceptance criteria for later implementation

Issue #23 implementation is complete when:

- the three canonical logical profiles resolve only through their fixed environment variables;
- no migration DB script accepts raw credentials/connection strings on the CLI;
- `.env.example` contains only empty canonical keys;
- secret-bearing `.env` variants remain ignored;
- missing/unknown/forbidden configuration fails before connection establishment;
- connection values never appear in normal logs, errors, migration evidence, or committed files;
- Issues #18-#22 use the same resolver/profile vocabulary;
- production read-write access is absent from the tooling profile registry;
- OQ-021 remains open until the legacy DLL mechanism is actually observed.

## Non-goals

This design does not add `.env.example`, change `.gitignore`, implement DB connection code, add DB drivers, provision accounts, connect to any database, change Issues #18-#22 implementation, or resolve OQ-021.