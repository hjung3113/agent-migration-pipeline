<!-- This schema is the shared base for evidence storage, judge composition, and reproduction procedures. Renaming any field below forces re-conversion of existing evidence records. -->

# Characterization: <ID>

- Feature card: (`unbound` if captured before a feature card exists)
- Behavior contract ref:
- Harness/boundary:
- Capture date:
- Environment: (must name the legacy build/binary version and the MSSQL schema version, not just "dev"/"staging")
- Harness invocation:
- Artifact root: (base path/URI that every relative path below is resolved against)
- Record grade rollup: A | B | C | D | ?

Each section below is one capture item defined in docs/03-evidence-and-verification.md; keep the item names unchanged. Each item's `Ref:` narrows the header's `Feature card`/`Behavior contract ref` when set, and defaults to them when blank. Capture raw values first; normalization and comparison rules live in the behavior contract.

For every `Value:` field, use exactly one of: an actual captured value; `none observed` (captured, nothing happened — a real, assertable fact); `not captured (see caveats)` (we didn't look); or `N/A` (item does not apply to this scenario). Do not leave `Value:` blank.

## exact input fixture

Exact inputs used to invoke the boundary: arguments, parameters, request payload, input files. Must be replayable as-is.

- Format: JSON fixture file (path + hash) or inline input table
- Value:
- Grade: A | B | C | D | ?
- Ref:

## initial DB state or relevant records

Relevant rows/tables before invocation. Scope to records the scenario touches, not a full dump.

- Format: SQL query + result snapshot (path) or row table
- Value:
- Grade: A | B | C | D | ?
- Ref:

## return/output value

Exact value returned or emitted by the boundary call. No normalization at capture time.

- Format: JSON literal or verbatim text block
- Value:
- Grade: A | B | C | D | ?
- Ref:

## resulting DB state

Relevant rows/tables after invocation, ideally as a diff against the initial state above.

- Format: changed-rows table (before -> after) or query + snapshot path
- Value:
- Grade: A | B | C | D | ?
- Ref:

## files generated/modified

Every file created, changed, or deleted by the scenario, including temporary files.

- Format: table (path | action | hash or size)
- Value:
- Grade: A | B | C | D | ?
- Ref:

## logs/events

Log lines or events emitted during the scenario, with source and timestamp.

- Format: verbatim log excerpt in a code block + source
- Value:
- Grade: A | B | C | D | ?
- Ref:

## callbacks to platform

Calls the legacy component makes into the host platform, in observed order.

- Format: ordered table (seq | entry point/API | payload)
- Value:
- Grade: A | B | C | D | ?
- Ref:

## exception/error code

Exact error code, message, and detail (stack trace, HRESULT) observed. Record `none observed` explicitly on happy-path captures.

- Format: exact code + message (+ stack or HRESULT if present)
- Value:
- Grade: A | B | C | D | ?
- Ref:

## timing/order only when business-significant

Only when ordering or timing changes the business outcome (sequencing rules, deadlines, side-effect order). Otherwise leave as N/A.

- Format: ordered sequence with timestamps or relative-order list
- Value: N/A (not business-significant)
- Grade: N/A
- Ref:

## Capture caveats

What could not be captured, known gaps, and observed-vs-inferred distinctions for this record.
