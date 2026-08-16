"""Domain-level application errors.

AppError is the error type application/domain code raises to signal business
failures. It is transport-agnostic: the API layer (app.api.errors) translates
it into the standard error envelope at the FastAPI boundary, so domain and
service code never shape HTTP responses.
"""

from typing import Any


class AppError(Exception):
    """Business-level failure with a stable machine-readable code.

    ``code`` is part of the public API contract (clients may branch on it), so
    it must be stable and UPPER_SNAKE_CASE, e.g. ``"VALIDATION_ERROR"``.
    Feature slices define their codes in their behavior contract.

    ``detail`` carries structured, endpoint-specific context. It must be a
    JSON object or array, or omitted — never a bare scalar/string. That rule
    is what keeps ``detail: Any`` safe to leave untyped in the shared
    envelope: a client can always assume "object/array or absent", never
    "sometimes a string".

    ``status_code`` is an explicit override only; leave it ``None`` in normal
    use. The HTTP status for a given ``code`` is resolved by
    ``app.api.errors`` from a ``code -> status`` table, so ``app.domain``
    does not have to know or default to an HTTP status (RULEBOOK Backend #1:
    endpoints are the transport boundary, not domain code).
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        detail: Any = None,
        status_code: int | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.detail = detail
        self.status_code = status_code
        super().__init__(message)
