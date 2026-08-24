"""Public-seam tests for the Issue #23 DB connection-profile resolver."""

from __future__ import annotations

import pytest

from scripts.db.connection_profiles import (
    CAPABILITY_READ_ONLY,
    CAPABILITY_READ_WRITE,
    ConnectionProfile,
    ENGINE_MSSQL,
    ENGINE_POSTGRESQL,
    ENVIRONMENT_PRODUCTION,
    ENVIRONMENT_TEST,
    PROFILES,
    ProfileResolutionError,
    resolve_connection_profile,
)


EXPECTED_PROFILES = {
    "mssql-prod-ro": (
        "MSSQL_PROD_RO_CONN",
        ENGINE_MSSQL,
        ENVIRONMENT_PRODUCTION,
        CAPABILITY_READ_ONLY,
    ),
    "mssql-test-rw": (
        "MSSQL_TEST_RW_CONN",
        ENGINE_MSSQL,
        ENVIRONMENT_TEST,
        CAPABILITY_READ_WRITE,
    ),
    "postgres-test-rw": (
        "PG_TEST_RW_CONN",
        ENGINE_POSTGRESQL,
        ENVIRONMENT_TEST,
        CAPABILITY_READ_WRITE,
    ),
}


def test_registry_is_fixed_to_the_three_canonical_profiles() -> None:
    assert set(PROFILES) == set(EXPECTED_PROFILES)
    for name, expected in EXPECTED_PROFILES.items():
        profile = PROFILES[name]
        assert (
            profile.name,
            profile.env_var,
            profile.engine,
            profile.environment,
            profile.capability,
        ) == (name, *expected)


def test_registry_has_no_production_read_write_profile() -> None:
    assert not any(
        profile.environment == ENVIRONMENT_PRODUCTION
        and profile.capability == CAPABILITY_READ_WRITE
        for profile in PROFILES.values()
    )


def test_profile_registry_is_runtime_immutable_and_rejects_injected_profile() -> None:
    injected = ConnectionProfile(
        "injected",
        "INJECTED_CONN",
        ENGINE_MSSQL,
        ENVIRONMENT_TEST,
        CAPABILITY_READ_WRITE,
    )

    with pytest.raises(TypeError):
        PROFILES["injected"] = injected  # type: ignore[index]

    with pytest.raises(ProfileResolutionError) as raised:
        resolve_connection_profile(
            "injected",
            environ={"INJECTED_CONN": "injected-value"},
        )

    assert "unrecognized connection profile input" in str(raised.value)


@pytest.mark.parametrize(
    ("profile_name", "operation", "env_var", "value"),
    [
        ("mssql-prod-ro", "read", "MSSQL_PROD_RO_CONN", "mssql-prod-read-value"),
        ("mssql-test-rw", "write", "MSSQL_TEST_RW_CONN", "mssql-test-write-value"),
        (
            "postgres-test-rw",
            "write",
            "PG_TEST_RW_CONN",
            "postgres-test-write-value",
        ),
    ],
)
def test_resolves_each_allowed_operation_and_returns_injected_value(
    profile_name: str, operation: str, env_var: str, value: str
) -> None:
    resolved = resolve_connection_profile(
        profile_name,
        operation=operation,
        environ={env_var: value},
    )
    assert resolved.profile is PROFILES[profile_name]
    assert resolved.connection_value == value


def test_unknown_profile_fails_closed_with_known_profiles() -> None:
    with pytest.raises(ProfileResolutionError) as raised:
        resolve_connection_profile("unknown-profile", environ={})

    assert str(raised.value) == (
        "unrecognized connection profile input; known profiles: "
        "mssql-prod-ro, mssql-test-rw, postgres-test-rw (see "
        "docs/12-db-connection-secrets-contract.md)"
    )


def test_unknown_profile_error_does_not_echo_raw_profile_input() -> None:
    raw_input = "mssql://user:SUPER-SECRET@host.example:1433/db"

    with pytest.raises(ProfileResolutionError) as raised:
        resolve_connection_profile(raw_input, environ={})

    rendered = str(raised.value)
    assert raw_input not in rendered
    assert "SUPER-SECRET" not in rendered
    assert "known profiles: mssql-prod-ro, mssql-test-rw, postgres-test-rw" in rendered


def test_unset_environment_variable_fails_closed_with_variable_name() -> None:
    with pytest.raises(ProfileResolutionError) as raised:
        resolve_connection_profile("mssql-prod-ro", environ={})

    assert str(raised.value) == (
        "MSSQL_PROD_RO_CONN is not set (connection profile 'mssql-prod-ro'); "
        "populate the environment — see .env.example"
    )


@pytest.mark.parametrize("value", ["", "   "])
def test_empty_or_whitespace_environment_variable_fails_closed(value: str) -> None:
    with pytest.raises(ProfileResolutionError) as raised:
        resolve_connection_profile(
            "mssql-prod-ro",
            environ={"MSSQL_PROD_RO_CONN": value},
        )

    assert str(raised.value) == (
        "MSSQL_PROD_RO_CONN is empty or whitespace-only "
        "(connection profile 'mssql-prod-ro')"
    )


def test_profile_outside_tool_allowlist_fails_closed() -> None:
    with pytest.raises(ProfileResolutionError) as raised:
        resolve_connection_profile(
            "mssql-test-rw",
            allowed_profiles={"mssql-prod-ro"},
            environ={"MSSQL_TEST_RW_CONN": "mssql-test-write-value"},
        )

    assert str(raised.value) == (
        "connection profile 'mssql-test-rw' is not allowed for this tool; "
        "allowed profiles: mssql-prod-ro"
    )


def test_error_rendering_never_includes_connection_secret() -> None:
    sentinel = "mssql://user:SECRET-VALUE@host.example:1433/db"
    all_values = {
        "MSSQL_PROD_RO_CONN": sentinel,
        "MSSQL_TEST_RW_CONN": sentinel,
        "PG_TEST_RW_CONN": sentinel,
    }

    cases = (
        lambda: resolve_connection_profile("unknown-profile", environ=all_values),
        lambda: resolve_connection_profile(
            "mssql-prod-ro",
            environ={
                key: value
                for key, value in all_values.items()
                if key != "MSSQL_PROD_RO_CONN"
            },
        ),
        lambda: resolve_connection_profile(
            "mssql-prod-ro",
            environ={**all_values, "MSSQL_PROD_RO_CONN": "   "},
        ),
        lambda: resolve_connection_profile(
            "mssql-test-rw",
            allowed_profiles={"mssql-prod-ro"},
            environ=all_values,
        ),
    )

    for resolve in cases:
        with pytest.raises(ProfileResolutionError) as raised:
            resolve()
        rendered = f"{raised.value}\n{raised.value.args!r}"
        assert sentinel not in rendered
        assert "SECRET-VALUE" not in rendered


def test_resolved_profile_repr_never_includes_connection_secret() -> None:
    secret = "mssql://user:SUPER-SECRET@host.example:1433/db"

    resolved = resolve_connection_profile(
        "mssql-prod-ro",
        environ={"MSSQL_PROD_RO_CONN": secret},
    )

    assert secret not in repr(resolved)


def test_invalid_operation_fails_closed() -> None:
    with pytest.raises(ProfileResolutionError) as raised:
        resolve_connection_profile(
            "mssql-test-rw",
            operation="admin",
            environ={"MSSQL_TEST_RW_CONN": "mssql-test-write-value"},
        )

    assert str(raised.value) == (
        "invalid operation 'admin'; expected one of: read, write"
    )
