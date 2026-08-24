"""Canonical DB connection-profile registry and fail-closed resolver.

Contract: docs/12-db-connection-secrets-contract.md (Issue #23).
No DB drivers, no connections — profile resolution and secret
injection contract only. Issues #18/#20/#22 consume this module.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Collection, Mapping

ENGINE_MSSQL = "mssql"
ENGINE_POSTGRESQL = "postgresql"
ENVIRONMENT_PRODUCTION = "production"
ENVIRONMENT_TEST = "test"
CAPABILITY_READ_ONLY = "read-only"
CAPABILITY_READ_WRITE = "read-write"
OPERATIONS = ("read", "write")


@dataclass(frozen=True)
class ConnectionProfile:
    name: str       # logical profile name, e.g. "mssql-prod-ro"
    env_var: str    # fixed environment-variable name, e.g. "MSSQL_PROD_RO_CONN"
    engine: str
    environment: str
    capability: str


PROFILES: Mapping[str, ConnectionProfile] = {
    profile.name: profile
    for profile in (
        ConnectionProfile("mssql-prod-ro", "MSSQL_PROD_RO_CONN",
                          ENGINE_MSSQL, ENVIRONMENT_PRODUCTION, CAPABILITY_READ_ONLY),
        ConnectionProfile("mssql-test-rw", "MSSQL_TEST_RW_CONN",
                          ENGINE_MSSQL, ENVIRONMENT_TEST, CAPABILITY_READ_WRITE),
        ConnectionProfile("postgres-test-rw", "PG_TEST_RW_CONN",
                          ENGINE_POSTGRESQL, ENVIRONMENT_TEST, CAPABILITY_READ_WRITE),
    )
}


class ProfileResolutionError(Exception):
    """Raised before any connection attempt. Message carries only
    non-secret metadata (profile name, env-var NAME, capability) —
    never the environment-variable value."""


@dataclass(frozen=True)
class ResolvedProfile:
    profile: ConnectionProfile
    connection_value: str


def resolve_connection_profile(
    profile_name: str,
    *,
    allowed_profiles: Collection[str] | None = None,
    operation: str = "read",
    environ: Mapping[str, str] | None = None,
) -> ResolvedProfile:
    """Resolve a logical profile to its connection value, fail-closed.

    Raises ProfileResolutionError (before any connection attempt) when:
    the profile is unknown; the profile is outside this tool's allowlist;
    the operation is not one of OPERATIONS; a write operation targets a
    read-only profile; the mapped env var is unset; or it is empty or
    whitespace-only. No fallback, no aliasing, no default database.
    """
    if profile_name not in PROFILES:
        known_profiles = ", ".join(PROFILES)
        raise ProfileResolutionError(
            f"unknown connection profile '{profile_name}'; known profiles: "
            f"{known_profiles} (see docs/12-db-connection-secrets-contract.md)"
        )

    profile = PROFILES[profile_name]

    if allowed_profiles is not None and profile_name not in allowed_profiles:
        allowed = ", ".join(sorted(allowed_profiles))
        raise ProfileResolutionError(
            f"connection profile '{profile_name}' is not allowed for this tool; "
            f"allowed profiles: {allowed}"
        )

    if operation not in OPERATIONS:
        expected = ", ".join(OPERATIONS)
        raise ProfileResolutionError(
            f"invalid operation '{operation}'; expected one of: {expected}"
        )

    if operation == "write" and profile.capability == CAPABILITY_READ_ONLY:
        raise ProfileResolutionError(
            f"connection profile '{profile.name}' declares capability "
            f"'{profile.capability}'; write operations are forbidden"
        )

    environment = os.environ if environ is None else environ
    if profile.env_var not in environment:
        raise ProfileResolutionError(
            f"{profile.env_var} is not set (connection profile '{profile.name}'); "
            "populate the environment — see .env.example"
        )

    connection_value = environment[profile.env_var]
    if not connection_value.strip():
        raise ProfileResolutionError(
            f"{profile.env_var} is empty or whitespace-only "
            f"(connection profile '{profile.name}')"
        )

    return ResolvedProfile(profile=profile, connection_value=connection_value)
