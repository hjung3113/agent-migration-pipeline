"""Public-seam tests for the Issue #20 SQL classifier and redaction."""

from __future__ import annotations

import pytest

from scripts.db.sql_classification import (
    OPERATION_CLASSES,
    classify_batch,
    classify_statement,
    redact,
)


def test_operation_class_contract_is_fixed() -> None:
    assert OPERATION_CLASSES == (
        "read",
        "mutation",
        "ddl",
        "procedure-exec",
        "privileged",
        "unknown",
    )


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT id, name FROM accounts",
        "WITH rows AS (SELECT id FROM accounts) SELECT id FROM rows",
    ],
)
def test_select_allowlist_is_read(sql: str) -> None:
    assert classify_statement(sql).operation_class == "read"


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO accounts (name) VALUES ('Ada')",
        "UPDATE accounts SET name = 'Ada' WHERE id = 1",
        "DELETE FROM accounts WHERE id = 1",
        "MERGE accounts AS target USING source AS input ON target.id = input.id "
        "WHEN MATCHED THEN UPDATE SET name = input.name",
        "BULK INSERT accounts FROM 'accounts.csv'",
        "COPY accounts FROM STDIN",
        "SELECT id INTO archive_accounts FROM accounts",
    ],
)
def test_mutation_verbs_are_mutation(sql: str) -> None:
    assert classify_statement(sql).operation_class == "mutation"


@pytest.mark.parametrize(
    "sql",
    [
        "CREATE TABLE accounts (id INT)",
        "ALTER TABLE accounts ADD COLUMN active BIT",
        "DROP TABLE accounts",
        "TRUNCATE TABLE accounts",
        "RENAME TABLE accounts TO archived_accounts",
        "COMMENT ON TABLE accounts IS 'directory'",
    ],
)
def test_ddl_verbs_are_ddl(sql: str) -> None:
    assert classify_statement(sql).operation_class == "ddl"


@pytest.mark.parametrize(
    "sql",
    [
        "EXEC dbo.refresh_accounts @scope = 1",
        "EXECUTE sp_refreshview 'dbo.accounts'",
        "CALL refresh_accounts(1)",
        "dbo.refresh_accounts @scope = 1",
        "sp_executesql N'SELECT 1'",
    ],
)
def test_procedure_execution_forms_are_procedure_exec(sql: str) -> None:
    assert classify_statement(sql).operation_class == "procedure-exec"


@pytest.mark.parametrize(
    "sql",
    [
        "GRANT SELECT ON accounts TO analyst",
        "REVOKE SELECT ON accounts FROM analyst",
        "DENY SELECT ON accounts TO analyst",
        "BACKUP DATABASE app TO DISK = 'backup.bak'",
        "RESTORE DATABASE app FROM DISK = 'backup.bak'",
        "SHUTDOWN",
        "KILL 52",
        "RECONFIGURE",
        "ALTER SERVER CONFIGURATION SET PROCESS AFFINITY CPU = 0",
        "CREATE ROLE analyst",
        "ALTER LOGIN analyst ENABLE",
        "DROP USER analyst",
    ],
)
def test_privileged_operations_are_privileged(sql: str) -> None:
    assert classify_statement(sql).operation_class == "privileged"


@pytest.mark.parametrize(
    "sql",
    [
        "ALTER [SERVER] CONFIGURATION SET PROCESS AFFINITY CPU = 0",
        "CREATE [ROLE] analyst",
        "DROP \"USER\" analyst",
    ],
)
def test_quoted_server_role_and_user_targets_remain_privileged(sql: str) -> None:
    assert classify_statement(sql).operation_class == "privileged"


@pytest.mark.parametrize(
    "sql",
    [
        "SET NOCOUNT ON",
        "BEGIN TRANSACTION",
        "COMMIT",
        "ROLLBACK",
        "USE app",
        "DECLARE @id INT",
        "PRINT 'hello'",
        "WAITFOR DELAY '00:00:01'",
        "GO",
        "",
    ],
)
def test_non_allowlisted_operations_are_unknown(sql: str) -> None:
    assert classify_statement(sql).operation_class == "unknown"


def test_literals_and_comments_cannot_hide_a_mutation_or_change_read() -> None:
    assert classify_statement("SELECT 'INSERT', 1 FROM accounts").operation_class == "read"
    assert classify_statement("/* INSERT */ SELECT 1").operation_class == "read"
    assert classify_statement("-- DROP\nSELECT 1").operation_class == "read"
    assert classify_statement("/* outer /* INSERT */ still comment */ SELECT 1").operation_class == "read"


def test_keyword_matching_is_exact_and_quote_aware() -> None:
    assert classify_statement("SELECT [delete], \"insert\", fn_delete_rows FROM t").operation_class == "read"
    assert classify_statement("iNsErT INTO t VALUES (1)").operation_class == "mutation"


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * INTO archive FROM source",
        "SELECT *\nINTO archive\nFROM source",
        "SELECT * /* gap */ INTO archive FROM source",
        "WITH x AS (SELECT * INTO archive FROM source) SELECT * FROM x",
        "WITH d AS (DELETE FROM source RETURNING *) SELECT * FROM d",
    ],
)
def test_select_into_and_data_modifying_ctes_are_not_read(sql: str) -> None:
    assert classify_statement(sql).operation_class == "mutation"


@pytest.mark.parametrize(
    ("sql", "expected"),
    [
        ("SELECT 1 TRUNCATE TABLE t", "ddl"),
        ("SELECT 1 DELETE FROM t", "mutation"),
        ("SELECT 1 GO TRUNCATE TABLE t", "ddl"),
    ],
)
def test_dangerous_tokens_anywhere_prevent_read_demotion(
    sql: str, expected: str
) -> None:
    assert classify_batch(sql).operation_class == expected


def test_semicolons_in_strings_and_parentheses_do_not_split_a_batch() -> None:
    result = classify_batch("SELECT ';', COALESCE((SELECT 1), 0) FROM t")
    assert result.operation_class == "read"


def test_cte_final_statement_controls_allowlist() -> None:
    assert classify_statement(
        "WITH x AS (SELECT id FROM source) SELECT id FROM x"
    ).operation_class == "read"
    assert classify_statement(
        "WITH x AS (SELECT id FROM source) INSERT INTO archive SELECT id FROM x"
    ).operation_class == "mutation"


@pytest.mark.parametrize(
    ("sql", "expected"),
    [
        ("SELECT 1; INSERT INTO t VALUES (1)", "mutation"),
        ("SELECT 1; SET NOCOUNT ON", "unknown"),
        ("INSERT INTO t VALUES (1); SET NOCOUNT ON", "unknown"),
        ("BEGIN TRAN; INSERT INTO t VALUES (1); ROLLBACK", "mutation"),
        ("INSERT INTO t VALUES (1); SELECT 1", "mutation"),
        ("SELECT 1; INSERT INTO t VALUES (1)", "mutation"),
    ],
)
def test_batch_inherits_the_highest_safety_rank(
    sql: str, expected: str
) -> None:
    assert classify_batch(sql).operation_class == expected


def test_go_is_a_batch_separator_but_a_standalone_go_is_unknown() -> None:
    assert classify_batch("SELECT 1 GO TRUNCATE TABLE t").operation_class == "ddl"
    assert classify_batch("GO").operation_class == "unknown"


def test_empty_or_comment_only_batch_is_unknown() -> None:
    assert classify_batch("   ; /* comment */ -- another\n ; ").operation_class == "unknown"


def test_malformed_sql_is_unknown() -> None:
    assert classify_batch("SELECT 'unterminated").operation_class == "unknown"
    assert classify_batch("SELECT (1").operation_class == "unknown"


def test_malformed_literal_is_still_masked_in_the_safe_preview() -> None:
    result = classify_batch("SELECT 'SECRET-VALUE")
    assert result.operation_class == "unknown"
    assert "SECRET-VALUE" not in result.preview


def test_redaction_removes_comments_and_masks_literals_and_numbers() -> None:
    assert redact(
        "-- note\nSELECT 'SECRET-VALUE', 42, 0xAB FROM accounts"
    ) == "SELECT ?, ?, ? FROM accounts"


def test_literal_values_do_not_change_hash_or_preview() -> None:
    first = classify_batch("SELECT 'alpha', 42 FROM accounts")
    second = classify_batch("SELECT 'SECRET-VALUE', 7 FROM accounts")
    assert first.statement_hash == second.statement_hash
    assert first.preview == second.preview
    assert "SECRET-VALUE" not in second.preview


def test_structurally_different_normalized_sql_has_a_different_hash() -> None:
    first = classify_batch("SELECT id FROM accounts")
    second = classify_batch("SELECT name FROM accounts")
    assert first.statement_hash != second.statement_hash


def test_preview_is_redacted_and_limited_to_200_characters() -> None:
    result = classify_batch("SELECT " + ", ".join("'SECRET-VALUE'" for _ in range(80)))
    assert len(result.preview) == 200
    assert "SECRET-VALUE" not in result.preview


def test_statement_normalized_sql_is_the_redacted_form() -> None:
    result = classify_statement("/* comment */ SELECT 'SECRET-VALUE' FROM accounts")
    assert result.normalized_sql == "SELECT ? FROM accounts"
    assert "SECRET-VALUE" not in result.normalized_sql


@pytest.mark.parametrize(
    ("sql", "replacement", "secret"),
    [
        (
            'SELECT "DOUBLE-QUOTED-SECRET" FROM accounts',
            'SELECT "DOUBLE-QUOTED-OTHER" FROM accounts',
            "DOUBLE-QUOTED-SECRET",
        ),
        (
            "SELECT $$DOLLAR-QUOTED-SECRET$$ FROM accounts",
            "SELECT $$DOLLAR-QUOTED-OTHER$$ FROM accounts",
            "DOLLAR-QUOTED-SECRET",
        ),
    ],
)
def test_double_and_dollar_quoted_literals_are_masked_from_preview_and_hash(
    sql: str, replacement: str, secret: str
) -> None:
    first = classify_batch(sql)
    second = classify_batch(replacement)

    assert redact(sql) == "SELECT ? FROM accounts"
    assert secret not in first.preview
    assert first.preview == second.preview
    assert first.statement_hash == second.statement_hash
