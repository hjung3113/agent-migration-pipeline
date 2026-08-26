"""Conservative SQL classification and secret-safe normalization.

This module is intentionally a tokenizer, not a SQL parser.  It recognizes
only the shapes needed by the DB execution guard and treats everything else
as unsafe or unknown.  The normalized form is also the only source used for
audit previews and hashes.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Iterable, Sequence


OPERATION_CLASSES = (
    "read",
    "mutation",
    "ddl",
    "procedure-exec",
    "privileged",
    "unknown",
)
BATCH_RANK = {
    "read": 0,
    "mutation": 2,
    "ddl": 2,
    "procedure-exec": 2,
    "unknown": 3,
    "privileged": 4,
}


@dataclass(frozen=True)
class StatementClassification:
    operation_class: str
    normalized_sql: str


@dataclass(frozen=True)
class BatchClassification:
    operation_class: str
    statement_hash: str
    preview: str


@dataclass(frozen=True)
class _Token:
    kind: str
    value: str


_DANGEROUS_VERBS = frozenset(
    {
        "INSERT",
        "UPDATE",
        "DELETE",
        "MERGE",
        "COPY",
        "CREATE",
        "ALTER",
        "DROP",
        "TRUNCATE",
        "RENAME",
        "COMMENT",
        "EXEC",
        "EXECUTE",
        "CALL",
        "SP_EXECUTESQL",
        "GRANT",
        "REVOKE",
        "DENY",
        "BACKUP",
        "RESTORE",
        "SHUTDOWN",
        "KILL",
        "RECONFIGURE",
    }
)
_PRIVILEGED_VERBS = frozenset(
    {
        "GRANT",
        "REVOKE",
        "DENY",
        "BACKUP",
        "RESTORE",
        "SHUTDOWN",
        "KILL",
        "RECONFIGURE",
    }
)
_UNKNOWN_STARTS = frozenset(
    {
        "SET",
        "BEGIN",
        "COMMIT",
        "ROLLBACK",
        "USE",
        "DECLARE",
        "PRINT",
        "WAITFOR",
        "GO",
    }
)
_PRIVILEGED_TARGETS = frozenset({"SERVER", "ROLE", "LOGIN", "USER"})
_FUNCTION_NAMES = frozenset(
    {
        "ABS",
        "COALESCE",
        "CONCAT",
        "COUNT",
        "CURRENT_DATABASE",
        "DB_NAME",
        "ISNULL",
        "MAX",
        "MIN",
        "SUM",
    }
)
_TIE_BREAK = {
    "mutation": 0,
    "ddl": 1,
    "procedure-exec": 2,
}


def classify_statement(sql: str) -> StatementClassification:
    """Classify one SQL statement and return its redacted normalized form."""
    tokens, malformed = _tokenize(sql)
    operation_class = "unknown" if malformed else _classify_tokens(tokens)
    return StatementClassification(
        operation_class=operation_class,
        normalized_sql=_normalize_tokens(tokens),
    )


def classify_batch(sql: str) -> BatchClassification:
    """Classify a semicolon/GO-delimited SQL batch conservatively."""
    tokens, malformed = _tokenize(sql)
    statements, split_malformed = _split_batch_tokens(tokens)
    normalized_sql = _normalize_batch(statements)

    if malformed or split_malformed or not statements:
        operation_class = "unknown"
    else:
        operation_class = "read"
        classifications = [(_classify_tokens(statement), statement) for statement in statements]
        has_non_control_hazard = any(
            BATCH_RANK[operation] >= BATCH_RANK["mutation"]
            for operation, statement in classifications
            if not _is_transaction_control(statement)
        )
        for statement_class, statement in classifications:
            # BEGIN/COMMIT/ROLLBACK are unknown as standalone statements, but
            # a transaction wrapper must not hide the mutation it contains.
            # Other unknown statements still dominate a batch as required.
            if (
                has_non_control_hazard
                and statement_class == "unknown"
                and _is_transaction_control(statement)
            ):
                continue
            operation_class = _safer_class(operation_class, statement_class)

    statement_hash = hashlib.sha256(normalized_sql.encode("utf-8")).hexdigest()
    return BatchClassification(
        operation_class=operation_class,
        statement_hash=statement_hash,
        preview=normalized_sql[:200],
    )


def redact(sql: str) -> str:
    """Return the canonical comment-free, literal-masked SQL representation."""
    tokens, _ = _tokenize(sql)
    statements, _ = _split_batch_tokens(tokens)
    if statements:
        return _normalize_batch(statements)
    return _normalize_tokens(tokens)


def _tokenize(sql: str) -> tuple[list[_Token], bool]:
    if not isinstance(sql, str):
        raise TypeError("sql must be a string")

    tokens: list[_Token] = []
    index = 0
    length = len(sql)
    malformed = False

    while index < length:
        char = sql[index]

        if char.isspace():
            index += 1
            continue

        if sql.startswith("--", index):
            newline = sql.find("\n", index + 2)
            index = length if newline == -1 else newline + 1
            continue

        if sql.startswith("/*", index):
            index, closed = _consume_block_comment(sql, index)
            if not closed:
                malformed = True
                break
            continue

        if char in "'\"[":
            token, index, closed = _consume_quoted(sql, index)
            if not closed:
                malformed = True
                break
            tokens.append(token)
            continue

        if char in "NnEe" and index + 1 < length and sql[index + 1] == "'":
            token, index, closed = _consume_quoted(sql, index + 1)
            if not closed:
                malformed = True
                break
            tokens.append(token)
            continue

        if char.isdigit() or (
            char == "." and index + 1 < length and sql[index + 1].isdigit()
        ):
            index = _consume_number(sql, index)
            tokens.append(_Token("literal", "?"))
            continue

        if _is_identifier_start(char) or char == "@":
            end = index + 1
            while end < length and _is_identifier_part(sql[end]):
                end += 1
            tokens.append(_Token("word", sql[index:end]))
            index = end
            continue

        operator = _longest_operator(sql, index)
        tokens.append(_Token("symbol", operator))
        index += len(operator)

    return tokens, malformed


def _consume_block_comment(sql: str, start: int) -> tuple[int, bool]:
    depth = 1
    index = start + 2
    while index < len(sql):
        if sql.startswith("/*", index):
            depth += 1
            index += 2
        elif sql.startswith("*/", index):
            depth -= 1
            index += 2
            if depth == 0:
                return index, True
        else:
            index += 1
    return len(sql), False


def _consume_quoted(sql: str, start: int) -> tuple[_Token, int, bool]:
    opener = sql[start]
    closer = "]" if opener == "[" else opener
    index = start + 1
    while index < len(sql):
        if sql[index] == closer:
            if index + 1 < len(sql) and sql[index + 1] == closer:
                index += 2
                continue
            index += 1
            if opener == "'":
                return _Token("literal", "?"), index, True
            return _Token("quoted", sql[start:index]), index, True
        index += 1
    if opener == "'":
        return _Token("literal", "?"), len(sql), False
    return _Token("quoted", "?"), len(sql), False


def _consume_number(sql: str, start: int) -> int:
    index = start
    if sql.startswith(("0x", "0X"), start):
        index += 2
        while index < len(sql) and (sql[index].isdigit() or sql[index].lower() in "abcdef"):
            index += 1
        return index

    saw_exponent = False
    while index < len(sql):
        char = sql[index]
        if char.isdigit() or char == "_":
            index += 1
        elif char == "." and not saw_exponent:
            index += 1
        elif char in "eE" and not saw_exponent:
            saw_exponent = True
            index += 1
            if index < len(sql) and sql[index] in "+-":
                index += 1
        else:
            break
    return index


def _is_identifier_start(char: str) -> bool:
    return char == "_" or char == "$" or char.isalpha()


def _is_identifier_part(char: str) -> bool:
    return char == "_" or char == "$" or char.isalnum()


def _longest_operator(sql: str, start: int) -> str:
    for operator in ("::", "<=", ">=", "<>", "!=", "+=", "-=", "*=", "/=", "||", "&&"):
        if sql.startswith(operator, start):
            return operator
    return sql[start]


def _split_batch_tokens(tokens: Sequence[_Token]) -> tuple[list[list[_Token]], bool]:
    statements: list[list[_Token]] = []
    current: list[_Token] = []
    depth = 0
    malformed = False

    def flush() -> None:
        nonlocal current
        if current:
            statements.append(current)
            current = []

    for token in tokens:
        if token.kind == "symbol" and token.value == "(":
            depth += 1
            current.append(token)
        elif token.kind == "symbol" and token.value == ")":
            if depth == 0:
                malformed = True
            else:
                depth -= 1
            current.append(token)
        elif depth == 0 and token.kind == "symbol" and token.value == ";":
            flush()
        elif depth == 0 and _word_is(token, "GO"):
            flush()
        else:
            current.append(token)

    if depth != 0:
        malformed = True
    flush()
    return statements, malformed


def _normalize_batch(statements: Iterable[Sequence[_Token]]) -> str:
    return "; ".join(_normalize_tokens(statement) for statement in statements)


def _normalize_tokens(tokens: Sequence[_Token]) -> str:
    result = ""
    previous: _Token | None = None
    for token in tokens:
        value = token.value
        if not result:
            result = value
        elif _needs_space(previous, token):
            result += " " + value
        else:
            result += value
        previous = token
    return result


def _needs_space(previous: _Token | None, current: _Token) -> bool:
    if previous is None:
        return False
    if current.value in {",", ")", ".", "::", "]", ";"}:
        return False
    if previous.value in {"(", ".", "::"}:
        return False
    if current.value == "(":
        return not (
            previous.kind in {"word", "quoted"}
            and previous.value.upper() in _FUNCTION_NAMES
        )
    return True


def _classify_tokens(tokens: Sequence[_Token]) -> str:
    if not tokens:
        return "unknown"

    danger_classes = _danger_classes(tokens)
    first_class = _first_class(tokens)
    if first_class == "read":
        operation_class = "read"
    else:
        operation_class = first_class
    for danger_class in danger_classes:
        operation_class = _safer_class(operation_class, danger_class)
    return operation_class


def _is_transaction_control(tokens: Sequence[_Token]) -> bool:
    if not tokens or tokens[0].kind != "word":
        return False
    return tokens[0].value.upper() in {"BEGIN", "COMMIT", "ROLLBACK"}


def _first_class(tokens: Sequence[_Token]) -> str:
    first = tokens[0]
    if first.kind == "word":
        keyword = first.value.upper()
        if keyword == "SELECT":
            return "read" if not _has_word(tokens, "INTO") else "mutation"
        if keyword == "WITH":
            final = _cte_final_token(tokens)
            if final is None:
                return "unknown"
            if final.kind == "word" and final.value.upper() == "SELECT":
                return "read" if not _has_word(tokens, "INTO") else "mutation"
            return _verb_class(tokens, _token_index(tokens, final))
        if keyword == "BULK" and _next_word(tokens, 0) == "INSERT":
            return "mutation"
        if keyword == "COMMENT" and _next_word(tokens, 0) == "ON":
            return "ddl"
        if keyword in {"INSERT", "UPDATE", "DELETE", "MERGE", "COPY"}:
            return "mutation"
        if keyword in {"CREATE", "ALTER", "DROP", "TRUNCATE", "RENAME"}:
            return (
                "privileged"
                if _has_privileged_target_after(tokens, 0)
                else "ddl"
            )
        if keyword in _PRIVILEGED_VERBS:
            return "privileged"
        if keyword in {"EXEC", "EXECUTE", "CALL", "SP_EXECUTESQL"}:
            return "procedure-exec"
        if keyword in _UNKNOWN_STARTS:
            return "unknown"
        return "procedure-exec"

    if first.kind == "quoted":
        return "procedure-exec"
    return "unknown"


def _danger_classes(tokens: Sequence[_Token]) -> list[str]:
    classes: list[str] = []
    for index, token in enumerate(tokens):
        if token.kind != "word":
            continue
        keyword = token.value.upper()
        if keyword == "INTO":
            classes.append("mutation")
        elif keyword in {"INSERT", "UPDATE", "DELETE", "MERGE", "COPY"}:
            classes.append("mutation")
        elif keyword == "BULK" and _next_word(tokens, index) == "INSERT":
            classes.append("mutation")
        elif keyword in {"CREATE", "ALTER", "DROP"}:
            classes.append(
                "privileged"
                if _has_privileged_target_after(tokens, index)
                else "ddl"
            )
        elif keyword in {"TRUNCATE", "RENAME", "COMMENT"}:
            if keyword == "COMMENT" and _next_word(tokens, index) != "ON":
                continue
            classes.append("ddl")
        elif keyword in {"EXEC", "EXECUTE", "CALL", "SP_EXECUTESQL"}:
            classes.append("procedure-exec")
        elif keyword in _PRIVILEGED_VERBS:
            classes.append("privileged")
    return classes


def _verb_class(tokens: Sequence[_Token], index: int | None) -> str:
    if index is None:
        return "unknown"
    token = tokens[index]
    if token.kind != "word":
        return "unknown"
    keyword = token.value.upper()
    if keyword == "BULK" and _next_word(tokens, index) == "INSERT":
        return "mutation"
    if keyword == "COMMENT" and _next_word(tokens, index) == "ON":
        return "ddl"
    if keyword in {"INSERT", "UPDATE", "DELETE", "MERGE", "COPY"}:
        return "mutation"
    if keyword in {"CREATE", "ALTER", "DROP", "TRUNCATE", "RENAME"}:
        return "privileged" if _has_privileged_target_after(tokens, index) else "ddl"
    if keyword in _PRIVILEGED_VERBS:
        return "privileged"
    if keyword in {"EXEC", "EXECUTE", "CALL", "SP_EXECUTESQL"}:
        return "procedure-exec"
    if keyword in _UNKNOWN_STARTS:
        return "unknown"
    if keyword == "SELECT":
        return "read"
    return "unknown"


def _cte_final_token(tokens: Sequence[_Token]) -> _Token | None:
    index = 1
    if _word_is_at(tokens, index, "RECURSIVE"):
        index += 1

    while index < len(tokens):
        if tokens[index].kind not in {"word", "quoted"}:
            return None
        index += 1

        if index < len(tokens) and tokens[index].value == "(":
            index = _after_matching_parenthesis(tokens, index)
            if index is None:
                return None

        if not _word_is_at(tokens, index, "AS"):
            return None
        index += 1
        if index >= len(tokens) or tokens[index].value != "(":
            return None
        index = _after_matching_parenthesis(tokens, index)
        if index is None:
            return None

        if index < len(tokens) and tokens[index].value == ",":
            index += 1
            continue
        return tokens[index] if index < len(tokens) else None
    return None


def _after_matching_parenthesis(tokens: Sequence[_Token], start: int) -> int | None:
    depth = 0
    for index in range(start, len(tokens)):
        value = tokens[index].value
        if value == "(":
            depth += 1
        elif value == ")":
            depth -= 1
            if depth == 0:
                return index + 1
            if depth < 0:
                return None
    return None


def _has_privileged_target_after(tokens: Sequence[_Token], index: int) -> bool:
    next_word = _next_word(tokens, index)
    return next_word in _PRIVILEGED_TARGETS


def _has_word(tokens: Sequence[_Token], wanted: str) -> bool:
    return any(_word_is(token, wanted) for token in tokens)


def _next_word(tokens: Sequence[_Token], index: int) -> str | None:
    for token in tokens[index + 1 :]:
        if token.kind == "word":
            return token.value.upper()
        if token.kind == "quoted":
            identifier = _quoted_identifier(token.value)
            if identifier is not None:
                return identifier.upper()
            return None
        if token.kind == "symbol" and token.value in {".", "[", "]"}:
            continue
        return None
    return None


def _quoted_identifier(value: str) -> str | None:
    if value.startswith("[") and value.endswith("]"):
        return value[1:-1].replace("]]", "]")
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1].replace('""', '"')
    return None


def _word_is(token: _Token, wanted: str) -> bool:
    return token.kind == "word" and token.value.upper() == wanted


def _word_is_at(tokens: Sequence[_Token], index: int, wanted: str) -> bool:
    return index < len(tokens) and _word_is(tokens[index], wanted)


def _token_index(tokens: Sequence[_Token], target: _Token) -> int | None:
    for index, token in enumerate(tokens):
        if token is target:
            return index
    return None


def _safer_class(current: str, candidate: str) -> str:
    current_key = (BATCH_RANK[current], _TIE_BREAK.get(current, 0))
    candidate_key = (BATCH_RANK[candidate], _TIE_BREAK.get(candidate, 0))
    return candidate if candidate_key > current_key else current
