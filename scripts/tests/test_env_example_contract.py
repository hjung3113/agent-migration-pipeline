"""Public-seam tests for the repository .env.example contract validator."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.validate_scaffold import ROOT, validate_env_example_contract


VALID_ENV_EXAMPLE = """# Safe comments are allowed.

MSSQL_PROD_RO_CONN=

# The values are injected by the process environment.
MSSQL_TEST_RW_CONN=
PG_TEST_RW_CONN=
"""
VALID_GITIGNORE = ".env\n.env.*\n!.env.example\n"


def write_fixture(
    root: Path,
    *,
    env_example: str = VALID_ENV_EXAMPLE,
    gitignore: str = VALID_GITIGNORE,
    write_env_example: bool = True,
) -> None:
    if write_env_example:
        (root / ".env.example").write_text(env_example, encoding="utf-8")
    (root / ".gitignore").write_text(gitignore, encoding="utf-8")


def test_missing_env_example_is_reported(tmp_path: Path) -> None:
    write_fixture(tmp_path, write_env_example=False)

    errors = validate_env_example_contract(tmp_path)

    assert any(
        ".env.example:1 [env-example] required file missing" in error
        for error in errors
    )


def test_missing_canonical_key_is_reported(tmp_path: Path) -> None:
    write_fixture(
        tmp_path,
        env_example=(
            "MSSQL_PROD_RO_CONN=\n"
            "MSSQL_TEST_RW_CONN=\n"
        ),
    )

    errors = validate_env_example_contract(tmp_path)

    assert any("missing canonical key: PG_TEST_RW_CONN" in error for error in errors)


def test_extra_key_is_reported(tmp_path: Path) -> None:
    write_fixture(
        tmp_path,
        env_example=VALID_ENV_EXAMPLE + "UNDECLARED_CONN=\n",
    )

    errors = validate_env_example_contract(tmp_path)

    assert any("unexpected key: UNDECLARED_CONN" in error for error in errors)


@pytest.mark.parametrize(
    "malformed_key_line",
    [
        "MSSQL_PROD_RO_CONN =",
        "  MSSQL_PROD_RO_CONN=",
    ],
)
def test_canonical_key_token_must_not_have_surrounding_whitespace(
    tmp_path: Path, malformed_key_line: str
) -> None:
    write_fixture(
        tmp_path,
        env_example=VALID_ENV_EXAMPLE.replace(
            "MSSQL_PROD_RO_CONN=\n",
            f"{malformed_key_line}\n",
        ),
    )

    errors = validate_env_example_contract(tmp_path)

    assert any(
        "unexpected key:" in error and "MSSQL_PROD_RO_CONN" in error
        for error in errors
    )


@pytest.mark.parametrize(
    "env_example",
    [
        VALID_ENV_EXAMPLE.replace(
            "MSSQL_PROD_RO_CONN=", "MSSQL_PROD_RO_CONN=value"
        ),
        VALID_ENV_EXAMPLE.replace(
            "MSSQL_PROD_RO_CONN=", "MSSQL_PROD_RO_CONN=   "
        ),
        VALID_ENV_EXAMPLE.replace(
            "MSSQL_PROD_RO_CONN=\n",
            "MSSQL_PROD_RO_CONN=secret\nMSSQL_PROD_RO_CONN=\n",
        ),
    ],
)
def test_canonical_keys_require_strictly_empty_rhs(
    tmp_path: Path, env_example: str
) -> None:
    write_fixture(
        tmp_path,
        env_example=env_example,
    )

    errors = validate_env_example_contract(tmp_path)

    assert any(
        "MSSQL_PROD_RO_CONN must have an empty value" in error
        for error in errors
    )


def test_duplicate_canonical_key_is_reported_even_when_both_values_are_empty(
    tmp_path: Path,
) -> None:
    write_fixture(
        tmp_path,
        env_example=VALID_ENV_EXAMPLE.replace(
            "MSSQL_PROD_RO_CONN=\n",
            "MSSQL_PROD_RO_CONN=\nMSSQL_PROD_RO_CONN=\n",
        ),
    )

    errors = validate_env_example_contract(tmp_path)

    assert any(
        "duplicate key: MSSQL_PROD_RO_CONN" in error for error in errors
    )


def test_missing_dotenv_ignore_rule_is_reported(tmp_path: Path) -> None:
    write_fixture(tmp_path, gitignore=".env.*\n!.env.example\n")

    errors = validate_env_example_contract(tmp_path)

    assert any("required rule missing: .env" in error for error in errors)


def test_missing_dotenv_wildcard_ignore_rule_is_reported(tmp_path: Path) -> None:
    write_fixture(tmp_path, gitignore=".env\n!.env.example\n")

    errors = validate_env_example_contract(tmp_path)

    assert any("required rule missing: .env.*" in error for error in errors)


def test_env_example_negation_rule_must_follow_wildcard_rule(tmp_path: Path) -> None:
    write_fixture(tmp_path, gitignore=".env\n!.env.example\n.env.*\n")

    errors = validate_env_example_contract(tmp_path)

    assert any("!.env.example must appear after .env.*" in error for error in errors)


def test_env_negation_rule_that_unignores_secret_file_is_reported(
    tmp_path: Path,
) -> None:
    write_fixture(
        tmp_path,
        gitignore=".env\n.env.*\n!.env.example\n!.env.local\n",
    )

    errors = validate_env_example_contract(tmp_path)

    assert any(
        "protection-defeating env negation rule: !.env.local" in error
        for error in errors
    )


def test_comments_and_blank_lines_are_allowed(tmp_path: Path) -> None:
    write_fixture(tmp_path)

    assert validate_env_example_contract(tmp_path) == []


def test_actual_repository_env_example_contract_passes() -> None:
    assert validate_env_example_contract(ROOT) == []
