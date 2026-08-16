"""Standard API error contract.

Every error response from this backend uses one envelope (ErrorResponse):
``{"code": str, "message": str, "detail": <optional object/array>}``. ``detail``
is a JSON object or array, or omitted entirely (``exclude_none``) — never a
bare scalar. This includes uncaught exceptions and Starlette-level errors
(404/405/...), not just ``AppError``: a client hardening against the
documented contract must never observe an unenveloped response.

``register_exception_handlers(app)`` wires the envelope onto a FastAPI app for:

- Starlette HTTP errors (404 -> NOT_FOUND, 405 -> METHOD_NOT_ALLOWED, ...),
  via an explicit status->code table, not derived from ``HTTPStatus.phrase``
  (that text is not a stable contract across Python versions -- e.g. 422's
  phrase changed between 3.12 and 3.13)
- request validation failures (422 -> VALIDATION_ERROR, detail = error list)
- ``AppError`` raised by application/domain code: HTTP status resolved from
  ``exc.status_code`` if the raiser set an explicit override, otherwise from
  the same status<->code table keyed by ``exc.code``, defaulting to 400
- any other uncaught exception (500 -> INTERNAL_ERROR, detail always None --
  never leak exception text to clients)

It also documents the standard error envelope in the OpenAPI spec: the
FastAPI-generated "422" response is overwritten (not left as the default
``HTTPValidationError`` shape, which this backend does not actually return),
and a "4XX" range response is added for every other undeclared error case.
"""

from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

from app.domain.errors import AppError

_ERROR_SCHEMA_REF = "#/components/schemas/ErrorResponse"

_OPERATION_METHODS = frozenset(
    {"get", "put", "post", "delete", "options", "head", "patch", "trace"}
)

#: Explicit status<->code table. This is the single source of truth for the
#: mapping in both directions (Starlette HTTP errors derive `code` from
#: `status`; `AppError` without an explicit `status_code` override derives
#: `status` from `code`). Deriving `code` from `HTTPStatus(status).phrase`
#: was tried and rejected: the phrase text is not a stable API contract (it
#: changed between Python versions for at least 422 and 413).
_CODE_BY_STATUS: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "TOO_MANY_REQUESTS",
    500: "INTERNAL_ERROR",
    503: "SERVICE_UNAVAILABLE",
}
_STATUS_BY_CODE: dict[str, int] = {code: status for status, code in _CODE_BY_STATUS.items()}


class ErrorResponse(BaseModel):
    """Standard error envelope returned by every endpoint on failure."""

    code: str
    message: str
    detail: Any | None = None


def _code_for_status(status_code: int) -> str:
    known = _CODE_BY_STATUS.get(status_code)
    if known is not None:
        return known
    return f"HTTP_{status_code}"


def _as_detail(value: Any) -> Any | None:
    """Coerce a value into the envelope's detail rule: object/array or None.

    A bare scalar (e.g. Starlette's ``exc.detail`` string on a 404) is
    dropped rather than passed through, because it would duplicate
    ``message`` and break the "detail is structured, per-code" convention
    before any feature endpoint gets a chance to rely on it.
    """
    if value is None or isinstance(value, dict | list):
        return value
    return None


def _error_response(
    status_code: int,
    code: str,
    message: str,
    detail: Any = None,
    *,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body = ErrorResponse(code=code, message=message, detail=_as_detail(detail))
    content = jsonable_encoder(body.model_dump(exclude_none=True))
    return JSONResponse(status_code=status_code, content=content, headers=headers)


def _document_standard_error_responses(app: FastAPI) -> None:
    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema is not None:
            return app.openapi_schema
        schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
        error_content = {
            "application/json": {"schema": {"$ref": _ERROR_SCHEMA_REF}}
        }
        for path_item in schema.get("paths", {}).values():
            for method, operation in path_item.items():
                if method not in _OPERATION_METHODS or not isinstance(operation, dict):
                    continue
                responses = operation.setdefault("responses", {})
                # FastAPI auto-adds "422" with the HTTPValidationError shape
                # for any route with validated params; this backend never
                # returns that shape, so overwrite it rather than leaving a
                # spec that disagrees with the actual handler.
                responses["422"] = {
                    "description": "Validation error (standard envelope)",
                    "content": error_content,
                }
                responses.setdefault("4XX", {
                    "description": "Error response (standard envelope)",
                    "content": error_content,
                })
        schema.setdefault("components", {}).setdefault("schemas", {})[
            "ErrorResponse"
        ] = ErrorResponse.model_json_schema()
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi  # type: ignore[method-assign]


def register_exception_handlers(app: FastAPI) -> None:
    """Register the standard error handlers and OpenAPI documentation."""

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http_exception(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        message = (
            str(exc.detail) if exc.detail else HTTPStatus(exc.status_code).phrase
        )
        return _error_response(
            exc.status_code,
            _code_for_status(exc.status_code),
            message,
            _as_detail(exc.detail),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return _error_response(
            422, "VALIDATION_ERROR", "Request validation failed.", exc.errors()
        )

    @app.exception_handler(AppError)
    async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        status_code = exc.status_code or _STATUS_BY_CODE.get(exc.code, 400)
        return _error_response(status_code, exc.code, exc.message, exc.detail)

    @app.exception_handler(Exception)
    async def _handle_uncaught_exception(
        request: Request, exc: Exception
    ) -> JSONResponse:
        # Never leak exception text to the client. This is the backstop that
        # keeps the envelope guarantee true for genuinely unhandled failures,
        # not just AppError/HTTP/validation cases.
        return _error_response(500, "INTERNAL_ERROR", "Internal server error.")

    _document_standard_error_responses(app)
