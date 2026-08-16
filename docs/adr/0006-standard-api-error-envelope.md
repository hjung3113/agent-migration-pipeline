# ADR-0006: Standard API error envelope

- Status: Accepted
- Date: 2026-08-17 (records the S-009 decision, implemented 2026-08-16 in commit `c09df6e`)
- Implementation: `target/backend/src/app/api/errors.py`, `target/backend/src/app/domain/errors.py`
- Feature guidance: `docs/templates/api-contract-checklist.md`

## Context

RULEBOOK Backend #2 requires "stable request/response/error contracts per feature", but until S-009 nothing fixed what an error response actually looks like. FastAPI/Starlette defaults produce inconsistent shapes: framework `HTTPException`s return `{"detail": "<string>"}`, validation errors return FastAPI's `HTTPValidationError` shape, uncaught exceptions return a bare text 500. If the first feature endpoints each picked a shape, that choice would harden into a de-facto standard clients depend on.

Six additional defects were found in Opus review of the first implementation (commit `c09df6e` body): uncaught 500s bypassing the envelope, error codes derived from `HTTPStatus(...).phrase` (not stable across Python versions — 422's phrase differs between 3.12 and 3.13), `AppError` defaulting to `status_code=400` at the raise site, FastAPI's auto-generated OpenAPI "422" documenting a shape the backend never returns, bare-string `detail` values duplicating `message`, and exception headers (`WWW-Authenticate`, `Allow`, `Retry-After`) being silently dropped.

## Decision

### 1. One envelope for every error response

Every error response from the backend — business failures, request validation (422), framework/Starlette HTTP errors (404/405/...), and uncaught exceptions (500) — uses a single `ErrorResponse` model:

```json
{"code": "<UPPER_SNAKE_CASE>", "message": "<human-readable>", "detail": <optional object|array>}
```

A client hardening against the documented contract must never observe an unenveloped response body, including from genuinely unhandled failures. `register_exception_handlers(app)` wires all four handler classes and is registered once in `app.main.create_app`.

### 2. `detail` is structured or absent — never a scalar

`detail` carries per-code structured context as a JSON object or array. When `None`, it is omitted from the body (`model_dump(exclude_none=True)`), not serialized as `null`. A handler that would otherwise send a bare scalar (e.g. Starlette's default `"Not Found"` string) drops it rather than passing it through, so `detail` never duplicates `message`.

### 3. `code` is the stable contract; status↔code mapping is an explicit table

`code` values are stable, UPPER_SNAKE_CASE machine identifiers that clients may branch on; feature slices define their codes in their behavior contract. The HTTP status↔code mapping is a single explicit table (`_CODE_BY_STATUS` / `_STATUS_BY_CODE` in `app.api.errors`, seeded with 400/401/403/404/405/409/422/429/500/503; unknown statuses map to `HTTP_<status>`). New codes are added to the table when a feature needs one. Deriving `code` from `HTTPStatus(status).phrase` was implemented and rejected: that text is not a stable API contract across Python versions. The phrase remains in use only for the human-readable `message` fallback, which is not a stability contract.

### 4. `AppError` is transport-agnostic and lives in `app.domain`

Application/domain code signals business failure by raising `AppError(code, message, detail=..., status_code=...)`. Domain and service code never shape HTTP responses (RULEBOOK Backend #1). `status_code` is an explicit override only (`int | None = None`) — the HTTP status is resolved at the API boundary from the code→status table (default 400 for unknown codes). An earlier version defaulted `status_code=400` at the raise site; that was rejected because it made `app.domain` silently pick HTTP statuses.

### 5. Uncaught exceptions never leak internals

Any unhandled exception returns `500 INTERNAL_ERROR` with a generic message and `detail` always `None` — exception text, stack details, and paths must not reach clients. This is the backstop that keeps the envelope guarantee true for failures no handler anticipated.

### 6. Exception headers are forwarded

HTTP errors carrying headers (e.g. `Allow` on 405, `WWW-Authenticate` on 401, `Retry-After` on 429) keep them in the enveloped response instead of stripping them.

### 7. OpenAPI documents the envelope

The auto-generated OpenAPI spec is post-processed: FastAPI's default "422" entry (the `HTTPValidationError` shape this backend never returns) is overwritten with the `ErrorResponse` schema, and a "4XX" range response referencing the same schema is added to every operation, so the published spec cannot disagree with the actual handler behavior.

### 8. Cross-cutting API conventions stay per-feature decisions

Pagination, URL/header versioning, write idempotency, and auth/session shape are deliberately **not** fixed project-wide yet (no feature has needed them; auth is blocked on OQ-019). Each is decided in the feature's target design at first real need and recorded there as a decision — never silently copied from a previous feature. Tracked as open questions in `docs/templates/api-contract-checklist.md`.

## Consequences

- feature endpoints must not construct error responses by hand or invent a second error shape; they raise `AppError` and the shared handlers do the rest;
- every feature endpoint's test suite covers at minimum a happy path, one `AppError` case, and (if the endpoint takes input) one validation-failure case asserting the envelope (checklist "Verification");
- `code` values become part of the public contract and may not be renamed casually — renaming is a contract change;
- the explicit status↔code table must grow with new codes rather than handlers improvising statuses;
- envelope behavior is regression-tested in `target/backend/tests/test_api_errors.py` (envelope on 404/405/422/500, phrase-derived codes, override handling, scalar-detail dropping, OpenAPI documentation).
