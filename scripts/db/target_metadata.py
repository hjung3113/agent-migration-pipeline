"""Non-secret expected-target identity registry for the DB safety guard.

Identity values are deployment facts, not credentials.  They intentionally
remain unresolved until an approved deployment supplies the real values; the
guard then fails closed rather than guessing.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

try:
    from scripts.db.connection_profiles import (
        ENVIRONMENT_PRODUCTION,
        ENVIRONMENT_TEST,
        PROFILES,
        ConnectionProfile,
    )
except ModuleNotFoundError:  # direct ``python3 scripts/validate_scaffold.py``
    from db.connection_profiles import (
        ENVIRONMENT_PRODUCTION,
        ENVIRONMENT_TEST,
        PROFILES,
        ConnectionProfile,
    )


@dataclass(frozen=True)
class ExpectedTarget:
    server_identity: str
    database_identity: str


EXPECTED_TARGETS: Mapping[str, ExpectedTarget] = MappingProxyType(
    {
        "mssql-prod-ro": ExpectedTarget("", ""),
        "mssql-test-rw": ExpectedTarget("", ""),
        "postgres-test-rw": ExpectedTarget("", ""),
    }
)


class TargetMetadataError(Exception):
    """Raised when expected-target metadata cannot safely be consumed."""


def get_expected_target(
    profile_name: str,
    *,
    targets: Mapping[str, ExpectedTarget] = EXPECTED_TARGETS,
) -> ExpectedTarget:
    """Return a resolved target or fail closed without exposing its values."""
    if profile_name not in targets:
        raise TargetMetadataError("unknown profile target metadata")

    target = targets[profile_name]
    if not isinstance(target, ExpectedTarget):
        raise TargetMetadataError(
            f"invalid target metadata for profile '{profile_name}'"
        )

    for field_name, value in (
        ("server_identity", target.server_identity),
        ("database_identity", target.database_identity),
    ):
        if not isinstance(value, str) or not value.strip():
            raise TargetMetadataError(
                f"missing target metadata for profile '{profile_name}': {field_name}"
            )
    return target


def validate_target_metadata(
    *,
    profiles: Mapping[str, ConnectionProfile] = PROFILES,
    targets: Mapping[str, ExpectedTarget] = EXPECTED_TARGETS,
) -> list[str]:
    """Report registry shape defects while allowing unresolved empty values."""
    errors: list[str] = []
    profile_names = set(profiles)
    target_names = set(targets)

    for profile_name in sorted(profile_names - target_names):
        errors.append(f"target metadata missing profile: {profile_name}")
    for profile_name in sorted(target_names - profile_names):
        errors.append(f"target metadata has extra profile: {profile_name}")

    usable: dict[str, ExpectedTarget] = {}
    for profile_name in sorted(profile_names & target_names):
        target = targets[profile_name]
        if not isinstance(target, ExpectedTarget):
            errors.append(f"invalid target metadata for profile: {profile_name}")
            continue

        for field_name, value in (
            ("server_identity", target.server_identity),
            ("database_identity", target.database_identity),
        ):
            if not isinstance(value, str):
                errors.append(
                    f"invalid {field_name} for profile: {profile_name}"
                )
            elif value != value.strip():
                errors.append(
                    f"{field_name} has surrounding whitespace for profile: "
                    f"{profile_name}"
                )

        if (
            isinstance(target.server_identity, str)
            and target.server_identity
            and isinstance(target.database_identity, str)
            and target.database_identity
        ):
            usable[profile_name] = target

    production_pairs = {
        (target.server_identity, target.database_identity): profile_name
        for profile_name, target in usable.items()
        if profiles[profile_name].environment == ENVIRONMENT_PRODUCTION
    }
    test_profiles = [
        (profile_name, target)
        for profile_name, target in usable.items()
        if profiles[profile_name].environment == ENVIRONMENT_TEST
    ]
    for profile_name, target in test_profiles:
        pair = (target.server_identity, target.database_identity)
        production_name = production_pairs.get(pair)
        if production_name is not None:
            errors.append(
                "test profile target equals production identity: "
                f"{profile_name} and {production_name}"
            )

    pair_groups: dict[tuple[str, str, str], list[str]] = {}
    for profile_name, target in usable.items():
        profile = profiles[profile_name]
        pair_groups.setdefault(
            (profile.engine, target.server_identity, target.database_identity),
            [],
        ).append(profile_name)
    for (engine, _server, _database), names in sorted(pair_groups.items()):
        if len(names) > 1:
            errors.append(
                "ambiguous target identity for same engine "
                f"'{engine}': {', '.join(sorted(names))}"
            )

    return errors
