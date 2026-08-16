from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.errors import ErrorResponse, register_exception_handlers
from app.domain.errors import AppError
from app.main import app


def test_unknown_path_returns_standard_error_schema() -> None:
    client = TestClient(app)

    response = client.get("/does-not-exist")

    assert response.status_code == 404
    body = response.json()
    ErrorResponse.model_validate(body)
    assert body["code"] == "NOT_FOUND"
    assert isinstance(body["message"], str)


def test_method_not_allowed_returns_standard_error_schema() -> None:
    client = TestClient(app)

    response = client.post("/health")

    assert response.status_code == 405
    assert response.json()["code"] == "METHOD_NOT_ALLOWED"


def test_request_validation_error_returns_standard_error_schema() -> None:
    test_app = FastAPI()
    register_exception_handlers(test_app)

    @test_app.get("/validation-probe")
    async def validation_probe(limit: int) -> dict[str, int]:
        return {"limit": limit}

    response = TestClient(test_app).get("/validation-probe", params={"limit": "NaN"})

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert isinstance(body["detail"], list)


def test_app_error_returns_standard_error_schema() -> None:
    test_app = FastAPI()
    register_exception_handlers(test_app)

    @test_app.get("/app-error-probe")
    async def app_error_probe() -> None:
        raise AppError("PROBE_ERROR", "probe failure", detail={"probe": True})

    response = TestClient(test_app).get("/app-error-probe")

    assert response.status_code == 400
    assert response.json() == {
        "code": "PROBE_ERROR",
        "message": "probe failure",
        "detail": {"probe": True},
    }


def test_openapi_documents_standard_error_responses() -> None:
    client = TestClient(app)

    spec = client.get("/openapi.json").json()

    responses = spec["paths"]["/health"]["get"]["responses"]
    assert "4XX" in responses
    schema = responses["4XX"]["content"]["application/json"]["schema"]
    assert schema["$ref"] == "#/components/schemas/ErrorResponse"
    # FastAPI's auto-generated "422" (HTTPValidationError shape) must be
    # overwritten -- this backend never actually returns that shape.
    assert (
        responses["422"]["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/ErrorResponse"
    )


def test_uncaught_exception_still_returns_standard_error_schema() -> None:
    test_app = FastAPI()
    register_exception_handlers(test_app)

    @test_app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("something exploded with a secret path in it")

    client = TestClient(test_app, raise_server_exceptions=False)
    response = client.get("/boom")

    assert response.status_code == 500
    body = response.json()
    assert body == {"code": "INTERNAL_ERROR", "message": "Internal server error."}
    assert "boom" not in response.text
    assert "secret" not in response.text


def test_error_codes_are_explicit_not_derived_from_http_phrase() -> None:
    # Guards against a repeat of the original bug: deriving `code` from
    # HTTPStatus(status).phrase, which is not stable across Python versions
    # (e.g. 422's phrase changed between 3.12 and 3.13).
    client = TestClient(app)

    response = client.get("/does-not-exist")
    assert response.json()["code"] == "NOT_FOUND"

    response = client.post("/health")
    assert response.json()["code"] == "METHOD_NOT_ALLOWED"


def test_app_error_status_falls_back_to_code_table_when_no_override() -> None:
    test_app = FastAPI()
    register_exception_handlers(test_app)

    @test_app.get("/conflict-probe")
    async def conflict_probe() -> None:
        raise AppError("CONFLICT", "already exists")

    response = TestClient(test_app).get("/conflict-probe")

    assert response.status_code == 409
    assert response.json()["code"] == "CONFLICT"


def test_app_error_status_override_is_respected() -> None:
    test_app = FastAPI()
    register_exception_handlers(test_app)

    @test_app.get("/override-probe")
    async def override_probe() -> None:
        raise AppError("WEIRD_CASE", "explicit override", status_code=418)

    response = TestClient(test_app).get("/override-probe")

    assert response.status_code == 418
    assert response.json()["code"] == "WEIRD_CASE"


def test_http_exception_string_detail_is_dropped_not_duplicated() -> None:
    # A Starlette HTTPException's default `detail` is a bare string (e.g.
    # "Not Found"). The envelope's `detail` must be an object/array or
    # absent, never a scalar duplicating `message`.
    client = TestClient(app)

    response = client.get("/does-not-exist")

    assert "detail" not in response.json()
