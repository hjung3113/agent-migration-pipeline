"""Public-seam tests for the Issue #20 import-boundary validator."""

from __future__ import annotations

from pathlib import Path

import pytest

import scripts.validate_scaffold as validate_scaffold
from scripts.validate_scaffold import (
    BANNED_DRIVER_ROOTS,
    CONNECTORS_ALLOWED_IMPORTERS,
    CONNECTORS_PACKAGE,
    CONNECTORS_TEST_EXCEPTIONS,
    validate_db_driver_boundary,
)


def _write(root: Path, relative: str, content: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_boundary_constants_are_the_explicit_contract() -> None:
    assert BANNED_DRIVER_ROOTS == (
        "pyodbc",
        "pymssql",
        "psycopg",
        "psycopg2",
        "sqlalchemy",
        "asyncpg",
        "pg8000",
        "adodbapi",
    )
    assert CONNECTORS_PACKAGE == "scripts.db.connectors"
    assert CONNECTORS_ALLOWED_IMPORTERS == ("scripts/db/db_guard.py",)
    assert CONNECTORS_TEST_EXCEPTIONS == ("scripts/tests/test_db_connectors.py",)


@pytest.mark.parametrize("driver", BANNED_DRIVER_ROOTS)
def test_each_banned_driver_root_is_rejected(tmp_path: Path, driver: str) -> None:
    _write(tmp_path, "scripts/tool.py", f"import {driver}\n")
    errors = validate_db_driver_boundary(tmp_path)
    assert len(errors) == 1
    assert errors[0].startswith("scripts/tool.py:1 [db-driver-boundary]")
    assert driver in errors[0]


def test_from_driver_submodule_is_rejected(tmp_path: Path) -> None:
    _write(tmp_path, "scripts/tool.py", "from psycopg2 import connect\n")
    errors = validate_db_driver_boundary(tmp_path)
    assert len(errors) == 1
    assert "psycopg2" in errors[0]


def test_connector_directory_is_allowed_to_import_its_driver(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "scripts/db/connectors/fake.py",
        "import pyodbc\nfrom psycopg import connect\n",
    )
    assert validate_db_driver_boundary(tmp_path) == []


@pytest.mark.parametrize(
    "content",
    [
        "from scripts.db.connectors import mssql\n",
        "from .connectors import mssql\n",
        "from . import connectors\n",
    ],
)
def test_connector_imports_are_rejected_outside_the_boundary(
    tmp_path: Path, content: str
) -> None:
    relative = "scripts/db/tool.py" if content.startswith("from .") else "scripts/tool.py"
    _write(tmp_path, relative, content)
    errors = validate_db_driver_boundary(tmp_path)
    assert len(errors) == 1
    assert "connector" in errors[0]


def test_parent_relative_connector_import_is_resolved(tmp_path: Path) -> None:
    _write(tmp_path, "scripts/app/tool.py", "from ..db.connectors import mssql\n")
    errors = validate_db_driver_boundary(tmp_path)
    assert len(errors) == 1
    assert "connector" in errors[0]


def test_guard_is_the_only_non_test_connector_importer(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "scripts/db/db_guard.py",
        "from scripts.db.connectors import mssql\n",
    )
    assert validate_db_driver_boundary(tmp_path) == []


def test_only_the_enumerated_connector_test_is_excepted(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "scripts/tests/test_db_connectors.py",
        "from scripts.db.connectors import mssql\n",
    )
    _write(
        tmp_path,
        "scripts/tests/test_other.py",
        "from scripts.db.connectors import mssql\n",
    )
    errors = validate_db_driver_boundary(tmp_path)
    assert len(errors) == 1
    assert errors[0].startswith("scripts/tests/test_other.py:1")


@pytest.mark.parametrize(
    "content",
    [
        "import importlib\n",
        "import importlib\nimportlib.import_module('pyodbc')\n",
        "def load(importlib):\n    return importlib.import_module('pyodbc')\n",
        "__import__('pyodbc')\n",
        "import builtins\nbuiltins.__import__('pyodbc')\n",
    ],
)
def test_dynamic_import_paths_are_rejected(tmp_path: Path, content: str) -> None:
    _write(tmp_path, "scripts/tool.py", content)
    errors = validate_db_driver_boundary(tmp_path)
    assert errors
    assert all("[db-driver-boundary]" in error for error in errors)


def test_dynamic_import_paths_are_allowed_in_connectors_and_test_exception(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "scripts/db/connectors/fake.py", "import importlib\n")
    _write(tmp_path, "scripts/tests/test_db_connectors.py", "__import__('pyodbc')\n")
    assert validate_db_driver_boundary(tmp_path) == []


def test_target_metadata_validation_is_wired_into_collection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    marker = "synthetic target metadata collision"
    monkeypatch.setattr(validate_scaffold, "validate_required", lambda: None)
    monkeypatch.setattr(validate_scaffold, "validate_json", lambda: None)
    monkeypatch.setattr(validate_scaffold, "validate_skills", lambda: None)
    monkeypatch.setattr(
        validate_scaffold, "validate_agents_and_commands", lambda: None
    )
    monkeypatch.setattr(validate_scaffold, "validate_agent_routing", lambda: [])
    monkeypatch.setattr(
        validate_scaffold, "validate_skill_routing_contract", lambda: []
    )
    monkeypatch.setattr(
        validate_scaffold, "validate_skill_execution_contract", lambda: []
    )
    monkeypatch.setattr(
        validate_scaffold, "validate_env_example_contract", lambda: []
    )
    monkeypatch.setattr(validate_scaffold, "validate_db_driver_boundary", lambda: [])
    monkeypatch.setattr(validate_scaffold, "collect_validation_errors", lambda: [])
    monkeypatch.setattr(
        validate_scaffold,
        "validate_target_metadata",
        lambda: [marker],
    )
    with pytest.raises(SystemExit) as raised:
        validate_scaffold.main()
    assert marker in str(raised.value)


def test_real_repository_has_no_boundary_violations() -> None:
    assert validate_db_driver_boundary(validate_scaffold.ROOT) == []
