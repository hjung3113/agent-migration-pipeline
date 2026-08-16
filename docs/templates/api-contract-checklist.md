# API Contract Checklist

Not a fill-in-the-blanks record like the other templates — a checklist to apply
when designing a feature's FastAPI endpoints (Target Feature Design step).
Grounded in RULEBOOK Backend #1-#3 (endpoints are transport boundaries, define
stable request/response/error contracts, keep host-compatibility logic
separate from application services) and the standard error envelope in
`target/backend/src/app/api/errors.py` (S-009).

## Error responses

- [ ] Failures raise `app.domain.errors.AppError(code, message, detail=..., status_code=...)` from service/domain code — never construct an HTTP response by hand in a route for a business failure.
- [ ] `code` is UPPER_SNAKE_CASE, stable, and documented in the feature's behavior contract — clients may branch on it.
- [ ] `status_code` is a transport hint chosen by the raiser, not guessed by the route.
- [ ] Do not invent a second error shape. Every error response uses `ErrorResponse` (`code`, `message`, optional `detail`) via the handlers already registered in `app.main` — including uncaught exceptions (500 -> `INTERNAL_ERROR`, no leaked exception text).
- [ ] `detail` is a JSON object or array, or **absent** (omitted from the response body when `None`, not serialized as `null`) — never a bare string/scalar. A handler that would otherwise send a scalar `detail` must drop it instead.
- [ ] `code -> HTTP status` is an explicit table in `app.api.errors` (`_STATUS_BY_CODE`/`_CODE_BY_STATUS`), never derived from `HTTPStatus(...).phrase` (that text is not stable across Python versions) and never left to default silently on the raise site. Add new codes to the table when a feature needs one it doesn't cover.

## Request/response shape

- [ ] Request and response bodies are Pydantic models in the feature's own module, not raw dicts.
- [ ] A field's presence/absence has one meaning per model — do not overload `null` for both "not provided" and "explicitly empty" without documenting which.
- [ ] Response models exclude internal-only fields (repository row IDs that aren't part of the contract, etc.) by construction, not by hoping nobody serializes them.

## Open questions — resolve per feature, do not assume a project-wide default yet

- [ ] **Pagination.** No project-wide convention chosen yet (no feature has needed one). If a feature list-endpoint needs it, decide cursor vs offset in that feature's design doc and record it as a decision, not silently copy whatever the previous feature did.
- [ ] **Versioning.** No project-wide URL/header versioning scheme chosen yet — there is exactly one skeleton endpoint (`GET /health`) and no external consumers. Decide when the first breaking change is needed, not preemptively.
- [ ] **Idempotency / retries.** Not yet decided whether write endpoints need idempotency keys. Relevant once a feature has a host-platform caller that may retry (see `docs/04-dll-integration-boundary.md` OQ-006 error propagation).
- [ ] **Auth/session shape.** Blocked on OQ-019 (host session/identity representation). Endpoints needing identity should depend on a host-agnostic, protocol-typed FastAPI dependency (see `app.platform` docstring, ADR-0005 amendment) rather than assuming a concrete auth mechanism.

## Verification

- [ ] `uv run pytest` covers at least: a happy path, one `AppError` case, and (if the endpoint takes input) one validation-failure case asserting the standard error envelope.
- [ ] `uv run ruff check .`, `uv run mypy`, `uv run lint-imports` all pass — the layer/platform-boundary contracts in `pyproject.toml` apply to feature code too, not just the skeleton.
