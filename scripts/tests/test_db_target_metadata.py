"""Public-seam tests for the Issue #20 expected-target registry."""

from __future__ import annotations

from types import MappingProxyType

import pytest

from scripts.db.connection_profiles import (
    CAPABILITY_READ_WRITE,
    ENGINE_MSSQL,
    ENVIRONMENT_TEST,
    ConnectionProfile,
    PROFILES,
)
from scripts.db.target_metadata import (
    EXPECTED_TARGETS,
    ExpectedTarget,
    TargetMetadataError,
    get_expected_target,
    validate_target_metadata,
)


def _resolved_targets() -> dict[str, ExpectedTarget]:
    return {
        "mssql-prod-ro": ExpectedTarget("prod-sql", "app"),
        "mssql-test-rw": ExpectedTarget("test-sql", "app_test"),
        "postgres-test-rw": ExpectedTarget("pg-test", "app_test"),
    }


def test_expected_target_registry_has_exactly_the_canonical_profiles() -> None:
    assert set(EXPECTED_TARGETS) == set(PROFILES)
    assert isinstance(EXPECTED_TARGETS, MappingProxyType)
    assert all(
        target == ExpectedTarget("", "") for target in EXPECTED_TARGETS.values()
    )


def test_unresolved_server_identity_is_rejected() -> None:
    targets = {
        "mssql-prod-ro": ExpectedTarget("", "app"),
    }
    with pytest.raises(TargetMetadataError) as raised:
        get_expected_target("mssql-prod-ro", targets=targets)
    assert "mssql-prod-ro" in str(raised.value)
    assert "server_identity" in str(raised.value)


def test_unresolved_database_identity_is_rejected() -> None:
    targets = {
        "mssql-prod-ro": ExpectedTarget("prod-sql", ""),
    }
    with pytest.raises(TargetMetadataError) as raised:
        get_expected_target("mssql-prod-ro", targets=targets)
    assert "mssql-prod-ro" in str(raised.value)
    assert "database_identity" in str(raised.value)


def test_resolved_target_is_returned_and_unknown_profile_is_rejected() -> None:
    expected = ExpectedTarget("prod-sql", "app")
    assert get_expected_target(
        "mssql-prod-ro", targets={"mssql-prod-ro": expected}
    ) == expected

    with pytest.raises(TargetMetadataError) as raised:
        get_expected_target("not-a-profile", targets={})
    assert "unknown profile" in str(raised.value)


def test_validate_target_metadata_reports_missing_and_extra_keys() -> None:
    missing = _resolved_targets()
    del missing["mssql-test-rw"]
    missing_errors = validate_target_metadata(profiles=PROFILES, targets=missing)
    assert any("mssql-test-rw" in error and "missing" in error for error in missing_errors)

    extra = _resolved_targets()
    extra["unexpected"] = ExpectedTarget("other-sql", "other")
    extra_errors = validate_target_metadata(profiles=PROFILES, targets=extra)
    assert any("unexpected" in error and "extra" in error for error in extra_errors)


def test_validate_target_metadata_reports_test_target_equal_to_production() -> None:
    targets = _resolved_targets()
    targets["mssql-test-rw"] = targets["mssql-prod-ro"]
    errors = validate_target_metadata(profiles=PROFILES, targets=targets)
    assert any("production" in error and "mssql-test-rw" in error for error in errors)


def test_validate_target_metadata_reports_case_variant_production_collision() -> None:
    targets = _resolved_targets()
    targets["mssql-test-rw"] = ExpectedTarget("PROD-SQL", "APP")
    errors = validate_target_metadata(profiles=PROFILES, targets=targets)

    assert any(
        "production" in error
        and "mssql-test-rw" in error
        and "mssql-prod-ro" in error
        for error in errors
    )


def test_validate_target_metadata_reports_same_engine_profile_pair_collision() -> None:
    targets = _resolved_targets()
    targets["postgres-test-rw"] = ExpectedTarget("test-sql", "app_test")
    profiles = dict(PROFILES)
    profiles["postgres-test-rw"] = ConnectionProfile(
        "postgres-test-rw",
        "PG_TEST_RW_CONN",
        ENGINE_MSSQL,
        ENVIRONMENT_TEST,
        CAPABILITY_READ_WRITE,
    )
    errors = validate_target_metadata(profiles=profiles, targets=targets)
    assert any(
        "ambiguous" in error
        and "mssql-test-rw" in error
        and "postgres-test-rw" in error
        for error in errors
    )


def test_validate_target_metadata_ignores_same_pair_across_different_engines() -> None:
    targets = _resolved_targets()
    targets["postgres-test-rw"] = targets["mssql-test-rw"]
    errors = validate_target_metadata(profiles=PROFILES, targets=targets)
    assert not any("ambiguous" in error for error in errors)


@pytest.mark.parametrize(
    ("field", "target"),
    [
        ("server_identity", ExpectedTarget(" prod-sql ", "app")),
        ("database_identity", ExpectedTarget("prod-sql", " app ")),
    ],
)
def test_validate_target_metadata_reports_identity_whitespace(
    field: str, target: ExpectedTarget
) -> None:
    targets = _resolved_targets()
    targets["mssql-prod-ro"] = target
    errors = validate_target_metadata(profiles=PROFILES, targets=targets)
    assert any("mssql-prod-ro" in error and field in error for error in errors)


def test_unresolved_shipped_registry_is_a_valid_transition_state() -> None:
    assert validate_target_metadata() == []


def test_target_metadata_errors_never_include_identity_or_secret_values() -> None:
    sentinel = "SECRET-VALUE"
    targets = {
        "mssql-prod-ro": ExpectedTarget("", sentinel),
        "mssql-test-rw": ExpectedTarget(sentinel, "test-db"),
    }
    errors = validate_target_metadata(profiles=PROFILES, targets=targets)
    assert all(sentinel not in error for error in errors)

    with pytest.raises(TargetMetadataError) as raised:
        get_expected_target("mssql-prod-ro", targets=targets)
    assert sentinel not in str(raised.value)
