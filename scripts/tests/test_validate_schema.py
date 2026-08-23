"""Tests for the A-2 schema/reference checks in scripts/validate_scaffold.py.

Canonical contract: docs/issue-2-artifact-schema-validation.md ("Test
requirements"). A-2 validates closed values, ID formats/scopes, and
explicitly structured references — templates, prose, fenced code, and
docs/templates/ are never instance data (docs/08 + issue-2 design).

Synthetic cases build a minimal fixture repository under tmp_path; one
test at the bottom runs the real tree end to end (normalized synthetic-demo
plus the current OQ registry must pass A-1 + A-2 together).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.validate_scaffold import (
    ROOT,
    validate_feature_schemas,
    validate_oq_registry,
    collect_validation_errors,
)

FEATURES = "migration/features"

VALID_CONTRACT = """# Behavior Contract: alpha

## Business rules

| Rule ID | Basis | Rule | Evidence | Grade |
|---|---|---|---|---|
| BR-001 | observed | concat a+b with no separator | e1 | ? |

"""

VALID_VERIFICATION = """# Verification Report: alpha

- Result: PASS

## Evidence used

| Item | Match | Grade |
|---|---|---|
| case-1 | Yes | ? |

"""

VALID_CARD = """---
id: {name}
stage: done
blocked: false
---

# Feature: {name}

## Open questions

None.
"""


def make_repo(tmp_path: Path) -> Path:
    return tmp_path


def write_oq_registry(root: Path) -> None:
    registry = root / "docs"
    registry.mkdir(parents=True, exist_ok=True)
    (registry / "05-open-questions.md").write_text(
        "# Open Questions\n\n"
        "| ID | Status | Question |\n"
        "|---|---|---|\n"
        "| OQ-001 | OPEN | Question one? |\n",
        encoding="utf-8",
    )


def add_feature(
    root: Path,
    name: str = "alpha",
    *,
    card_text: str | None = None,
    contract_text: str | None = None,
    verification_text: str | None = None,
    extra_files: dict[str, str] | None = None,
) -> Path:
    feature = root / FEATURES / name
    feature.mkdir(parents=True, exist_ok=True)
    (feature / "feature-card.md").write_text(
        card_text or VALID_CARD.format(name=name), encoding="utf-8"
    )
    (feature / "legacy-map.md").write_text("# Legacy Map\n", encoding="utf-8")
    (feature / "behavior-contract.md").write_text(
        contract_text or VALID_CONTRACT, encoding="utf-8"
    )
    (feature / "target-feature-design.md").write_text("# Design\n", encoding="utf-8")
    (feature / "review.md").write_text("# Review\n", encoding="utf-8")
    (feature / "verification.md").write_text(
        verification_text or VALID_VERIFICATION, encoding="utf-8"
    )
    for filename, content in (extra_files or {}).items():
        target = feature / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return feature


def run_schema(root: Path, oq_ids: set[str] | None = None):
    if oq_ids is None:
        _errors, oq_ids = validate_oq_registry(root)
    return validate_feature_schemas(root, oq_ids)


def contract_row(rule_id="BR-001", basis="observed", grade="?"):
    return f"| {rule_id} | {basis} | rule text | e1 | {grade} |\n"


def contract_with_row(**kwargs) -> str:
    return (
        "# Behavior Contract: alpha\n\n## Business rules\n\n"
        "| Rule ID | Basis | Rule | Evidence | Grade |\n"
        "|---|---|---|---|---|\n" + contract_row(**kwargs)
    )


# --- baseline -----------------------------------------------------------


def test_valid_feature_passes(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    add_feature(root)
    assert run_schema(root) == []


# --- behavior contract: Grade / Basis / Rule ID -------------------------


@pytest.mark.parametrize("grade", ["A", "B", "C", "D", "?"])
def test_contract_grade_accepted(tmp_path: Path, grade: str) -> None:
    root = make_repo(tmp_path)
    add_feature(root, contract_text=contract_with_row(grade=grade))
    assert run_schema(root) == []


@pytest.mark.parametrize("grade", ["B+", "a", "E", "??"])
def test_contract_grade_rejected(tmp_path: Path, grade: str) -> None:
    root = make_repo(tmp_path)
    add_feature(root, contract_text=contract_with_row(grade=grade))
    errors = run_schema(root)
    assert errors == [
        f"{FEATURES}/alpha/behavior-contract.md:7 [invalid-enum] "
        f"Grade `{grade}`; expected A|B|C|D|?"
    ]


@pytest.mark.parametrize("basis", ["observed", "inferred"])
def test_contract_basis_accepts_exact_domain(tmp_path: Path, basis: str) -> None:
    root = make_repo(tmp_path)
    add_feature(root, contract_text=contract_with_row(basis=basis))
    assert run_schema(root) == []


@pytest.mark.parametrize("basis", ["Observed", "INFERRED", "mixed", "inference"])
def test_contract_basis_near_misses_rejected(tmp_path: Path, basis: str) -> None:
    root = make_repo(tmp_path)
    add_feature(root, contract_text=contract_with_row(basis=basis))
    errors = run_schema(root)
    assert errors == [
        f"{FEATURES}/alpha/behavior-contract.md:7 [invalid-enum] "
        f"Basis `{basis}`; expected observed|inferred"
    ]


def test_contract_blank_wip_cells_are_not_violations(tmp_path: Path) -> None:
    """Blank work-in-progress values are skipped, never coerced valid."""
    contract = (
        "# Behavior Contract: alpha\n\n## Business rules\n\n"
        "| Rule ID | Basis | Rule | Evidence | Grade |\n"
        "|---|---|---|---|---|\n"
        "| BR-001 | | rule | | |\n"
    )
    root = make_repo(tmp_path)
    add_feature(root, contract_text=contract)
    assert run_schema(root) == []


@pytest.mark.parametrize("rule_id", ["BR-001", "BR-999"])
def test_br_id_format_accepted(tmp_path: Path, rule_id: str) -> None:
    root = make_repo(tmp_path)
    add_feature(root, contract_text=contract_with_row(rule_id=rule_id))
    assert run_schema(root) == []


@pytest.mark.parametrize("rule_id", ["BR-1", "BR-0001", "br-001", "BR-01A", "BR-00 1", "RULE-001"])
def test_br_id_format_rejected(tmp_path: Path, rule_id: str) -> None:
    root = make_repo(tmp_path)
    add_feature(root, contract_text=contract_with_row(rule_id=rule_id))
    errors = run_schema(root)
    assert errors == [
        f"{FEATURES}/alpha/behavior-contract.md:7 [invalid-id] "
        f"`{rule_id}`; expected BR-###"
    ]


def test_duplicate_br_id_rejected_within_one_contract(tmp_path: Path) -> None:
    contract = (
        "# Behavior Contract: alpha\n\n## Business rules\n\n"
        "| Rule ID | Basis | Rule | Evidence | Grade |\n"
        "|---|---|---|---|---|\n"
        "| BR-001 | observed | first | e1 | ? |\n"
        "| BR-001 | observed | second | e2 | ? |\n"
    )
    root = make_repo(tmp_path)
    add_feature(root, contract_text=contract)
    errors = run_schema(root)
    assert errors == [
        f"{FEATURES}/alpha/behavior-contract.md:8 [duplicate-id] "
        "duplicate Rule ID `BR-001` within this behavior contract "
        "(first defined at line 7)"
    ]


def test_same_br_id_across_different_features_is_legal(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    add_feature(root, "alpha")
    add_feature(root, "beta", card_text=VALID_CARD.format(name="beta"))
    assert run_schema(root) == []


@pytest.mark.parametrize("marker", ["observed", "inferred"])
def test_claim_markers_accepted(tmp_path: Path, marker: str) -> None:
    contract = (
        "# Behavior Contract: alpha\n\n## Scenario\n\n"
        f"- [{marker}] the legacy combines the two strings\n\n"
        "## Business rules\n\n"
        "| Rule ID | Basis | Rule | Evidence | Grade |\n"
        "|---|---|---|---|---|\n"
        "| BR-001 | observed | rule | e1 | ? |\n"
    )
    root = make_repo(tmp_path)
    add_feature(root, contract_text=contract)
    assert run_schema(root) == []


@pytest.mark.parametrize("marker", ["Observed", "inference", "mixed", "observed?", "note"])
def test_claim_marker_near_misses_rejected(tmp_path: Path, marker: str) -> None:
    contract = (
        "# Behavior Contract: alpha\n\n## Scenario\n\n"
        f"- [{marker}] claim text\n\n"
        "## Business rules\n\n"
        "| Rule ID | Basis | Rule | Evidence | Grade |\n"
        "|---|---|---|---|---|\n"
        "| BR-001 | observed | rule | e1 | ? |\n"
    )
    root = make_repo(tmp_path)
    add_feature(root, contract_text=contract)
    errors = run_schema(root)
    assert errors == [
        f"{FEATURES}/alpha/behavior-contract.md:5 [invalid-marker] "
        f"claim marker `[{marker}]`; expected [observed] or [inferred]"
    ]


def test_markdown_link_bullet_is_not_a_claim_marker(tmp_path: Path) -> None:
    contract = (
        "# Behavior Contract: alpha\n\n## Scenario\n\n"
        "- [the docs](docs/foo.md) describe the behavior\n\n"
        "## Business rules\n\n"
        "| Rule ID | Basis | Rule | Evidence | Grade |\n"
        "|---|---|---|---|---|\n"
        "| BR-001 | observed | rule | e1 | ? |\n"
    )
    root = make_repo(tmp_path)
    add_feature(root, contract_text=contract)
    assert run_schema(root) == []


@pytest.mark.parametrize("checkbox", ["[ ]", "[x]", "[X]"])
def test_task_list_checkbox_is_not_a_claim_marker(tmp_path: Path, checkbox: str) -> None:
    contract = (
        "# Behavior Contract: alpha\n\n## Unresolved questions\n\n"
        f"- {checkbox} confirm with legacy owner\n\n"
        "## Business rules\n\n"
        "| Rule ID | Basis | Rule | Evidence | Grade |\n"
        "|---|---|---|---|---|\n"
        "| BR-001 | observed | rule | e1 | ? |\n"
    )
    root = make_repo(tmp_path)
    add_feature(root, contract_text=contract)
    assert run_schema(root) == []


# --- evidence records ----------------------------------------------------


EVIDENCE_TMPL = """# Evidence: ev-001

- Feature: alpha
- Rule/scenario: BR-001 concatenation
- Grade: {grade}
- Captured date: 2026-08-19
- Source type: {source}

## Grade history

| Recorded date | From | To | Reason | Evidence refs |
| --- | --- | --- | --- | --- |
| 2026-08-23 | — | {history_grade} | Initial grade from test fixture | fixture/evidence-001 |
"""


def evidence_text(grade: str, source: str, *, history_grade: str | None = None) -> str:
    return EVIDENCE_TMPL.format(
        grade=grade,
        source=source,
        history_grade=grade if history_grade is None else history_grade,
    )


def test_valid_evidence_record_passes(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    add_feature(
        root,
        extra_files={"evidence/ev-001.md": evidence_text("B", "runtime")},
    )
    assert run_schema(root) == []


@pytest.mark.parametrize("grade", ["A", "B", "C", "D", "?"])
def test_evidence_grade_accepted(tmp_path: Path, grade: str) -> None:
    root = make_repo(tmp_path)
    add_feature(
        root,
        extra_files={"evidence/ev-001.md": evidence_text(grade, "db")},
    )
    assert run_schema(root) == []


@pytest.mark.parametrize("grade", ["B+", "b", "E", "N/A"])
def test_evidence_grade_rejected(tmp_path: Path, grade: str) -> None:
    root = make_repo(tmp_path)
    add_feature(
        root,
        extra_files={
            "evidence/ev-001.md": evidence_text(grade, "db", history_grade="B")
        },
    )
    errors = run_schema(root)
    assert errors == [
        f"{FEATURES}/alpha/evidence/ev-001.md:5 [invalid-enum] "
        f"Grade `{grade}`; expected A|B|C|D|?"
    ]


@pytest.mark.parametrize(
    "source",
    ["automated-test", "runtime", "db", "log", "callback", "source", "manual", "other"],
)
def test_evidence_source_type_domain_accepted(tmp_path: Path, source: str) -> None:
    root = make_repo(tmp_path)
    add_feature(
        root,
        extra_files={"evidence/ev-001.md": evidence_text("B", source)},
    )
    assert run_schema(root) == []


@pytest.mark.parametrize("source", ["Automated-test", "tests", "db-log", "integration"])
def test_evidence_source_type_rejected(tmp_path: Path, source: str) -> None:
    root = make_repo(tmp_path)
    add_feature(
        root,
        extra_files={"evidence/ev-001.md": evidence_text("B", source)},
    )
    errors = run_schema(root)
    assert errors == [
        f"{FEATURES}/alpha/evidence/ev-001.md:7 [invalid-enum] "
        f"Source type `{source}`; expected "
        "automated-test|runtime|db|log|callback|source|manual|other"
    ]


def test_evidence_blank_wip_grade_and_source_require_grade_history(
    tmp_path: Path,
) -> None:
    record = (
        "# Evidence: ev-wip\n\n"
        "- Feature: alpha\n"
        "- Rule/scenario: wip\n"
        "- Grade:\n"
        "- Captured date:\n"
        "- Source type:\n"
    )
    root = make_repo(tmp_path)
    add_feature(root, extra_files={"evidence/ev-wip.md": record})
    assert any("[missing-history]" in error for error in run_schema(root))


def test_evidence_empty_h1_id_rejected(tmp_path: Path) -> None:
    record = (
        "# Evidence:\n\n"
        "- Feature: alpha\n"
        "- Grade: B\n"
        "\n## Grade history\n\n"
        "| Recorded date | From | To | Reason | Evidence refs |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| 2026-08-23 | — | B | Initial grade | fixture/evidence-001 |\n"
    )
    root = make_repo(tmp_path)
    add_feature(root, extra_files={"evidence/bad.md": record})
    errors = run_schema(root)
    assert errors == [
        f"{FEATURES}/alpha/evidence/bad.md:1 [invalid-id] "
        "empty record ID; expected `# Evidence: <ID>`"
    ]


def test_evidence_structured_br_ref_must_resolve(tmp_path: Path) -> None:
    record = (
        "# Evidence: ev-ref\n\n"
        "- Feature: alpha\n"
        "- Behavior contract ref: {ref}\n"
        "- Grade: B\n"
        "- Source type: runtime\n"
        "\n## Grade history\n\n"
        "| Recorded date | From | To | Reason | Evidence refs |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| 2026-08-23 | — | B | Initial grade | fixture/evidence-001 |\n"
    )
    root = make_repo(tmp_path)
    add_feature(root, extra_files={"evidence/ok.md": record.format(ref="BR-001")})
    assert run_schema(root) == []

    root2 = make_repo(tmp_path / "case2")
    add_feature(root2, extra_files={"evidence/missing.md": record.format(ref="BR-099")})
    errors = run_schema(root2)
    assert errors == [
        f"{FEATURES}/alpha/evidence/missing.md:4 [missing-ref] "
        "`BR-099` does not resolve in this feature's behavior-contract.md"
    ]

    root3 = make_repo(tmp_path / "case3")
    add_feature(root3, extra_files={"evidence/bad.md": record.format(ref="BR-1")})
    errors = run_schema(root3)
    assert errors == [
        f"{FEATURES}/alpha/evidence/bad.md:4 [invalid-id] `BR-1`; expected BR-###"
    ]


def test_evidence_free_form_rule_scenario_is_not_a_reference(tmp_path: Path) -> None:
    record = (
        "# Evidence: ev-free\n\n"
        "- Feature: alpha\n"
        "- Rule/scenario: something about BR-999 and OQ-999\n"
        "- Grade: B\n"
        "- Source type: manual\n"
        "\n## Grade history\n\n"
        "| Recorded date | From | To | Reason | Evidence refs |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| 2026-08-23 | — | B | Initial grade | fixture/evidence-001 |\n"
    )
    root = make_repo(tmp_path)
    add_feature(root, extra_files={"evidence/ev-free.md": record})
    assert run_schema(root) == []


def test_evidence_duplicate_header_key_rejected(tmp_path: Path) -> None:
    record = (
        "# Evidence: ev-dup\n\n"
        "- Feature: alpha\n"
        "- Grade: B\n"
        "- Grade: A\n"
        "- Source type: runtime\n"
        "\n## Grade history\n\n"
        "| Recorded date | From | To | Reason | Evidence refs |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| 2026-08-23 | — | B | Initial grade | fixture/evidence-001 |\n"
    )
    root = make_repo(tmp_path)
    add_feature(root, extra_files={"evidence/ev-dup.md": record})
    errors = run_schema(root)
    assert errors == [
        f"{FEATURES}/alpha/evidence/ev-dup.md:5 [duplicate-key] "
        "duplicate field `Grade` in record header"
    ]


def test_plain_feature_file_is_not_an_evidence_instance(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    add_feature(root, extra_files={"notes.md": "# Notes: not a record\n\n- Grade: B+\n"})
    assert run_schema(root) == []


# --- characterization records ---------------------------------------------


CHAR_HEADER = """# Characterization: char-001

- Feature card: `migration/features/alpha/feature-card.md`
- Behavior contract ref: BR-001
- Capture date: 2026-08-19
- Environment: legacy 1.2.3 / schema 7
- Artifact root: `migration/features/alpha/`
- Record grade rollup: {rollup}

## exact input fixture

- Format: inline input table
- Value: `a="foo"`
- Grade: {item_grade}
- Ref: {ref}

## files generated/modified

- Format: table
- Value: {value}
- Grade: {na_grade}
- Ref: BR-001
"""


def characterization(
    rollup="?",
    item_grade="?",
    value="none observed",
    na_grade="?",
    ref="BR-001",
) -> str:
    return CHAR_HEADER.format(
        rollup=rollup, item_grade=item_grade, value=value, na_grade=na_grade, ref=ref
    )


def test_valid_characterization_passes(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    add_feature(root, extra_files={"characterization-record.md": characterization()})
    assert run_schema(root) == []


@pytest.mark.parametrize("rollup", ["A", "B", "C", "D", "?"])
def test_rollup_grade_domain(tmp_path: Path, rollup: str) -> None:
    root = make_repo(tmp_path)
    add_feature(root, extra_files={"characterization-record.md": characterization(rollup=rollup)})
    assert run_schema(root) == []


@pytest.mark.parametrize("rollup", ["b", "E", "N/A", "B+"])
def test_rollup_grade_rejected(tmp_path: Path, rollup: str) -> None:
    root = make_repo(tmp_path)
    add_feature(root, extra_files={"characterization-record.md": characterization(rollup=rollup)})
    errors = run_schema(root)
    assert errors == [
        f"{FEATURES}/alpha/characterization-record.md:8 [invalid-enum] "
        f"Record grade rollup `{rollup}`; expected A|B|C|D|?"
    ]


@pytest.mark.parametrize("grade", ["A", "B", "C", "D", "?", "N/A"])
def test_item_grade_domain(tmp_path: Path, grade: str) -> None:
    value = "N/A" if grade == "N/A" else '`a="foo"`'
    record = characterization(item_grade=grade).replace(
        '- Value: `a="foo"`', f"- Value: {value}", 1
    )
    root = make_repo(tmp_path)
    add_feature(root, extra_files={"characterization-record.md": record})
    assert run_schema(root) == []


def test_item_grade_rejected(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    add_feature(
        root,
        extra_files={"characterization-record.md": characterization(item_grade="B+")},
    )
    errors = run_schema(root)
    assert errors == [
        f"{FEATURES}/alpha/characterization-record.md:14 [invalid-enum] "
        "Grade `B+`; expected A|B|C|D|?|N/A"
    ]


def test_value_na_with_grade_na_is_valid(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    add_feature(
        root,
        extra_files={
            "characterization-record.md": characterization(
                value="N/A", na_grade="N/A"
            )
        },
    )
    assert run_schema(root) == []


def test_documented_na_parenthesized_form_with_grade_na_is_valid(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    add_feature(
        root,
        extra_files={
            "characterization-record.md": characterization(
                value="N/A (not business-significant)", na_grade="N/A"
            )
        },
    )
    assert run_schema(root) == []


def test_none_observed_with_grade_na_is_invalid(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    add_feature(
        root,
        extra_files={
            "characterization-record.md": characterization(
                value="none observed", na_grade="N/A"
            )
        },
    )
    errors = run_schema(root)
    assert errors == [
        f"{FEATURES}/alpha/characterization-record.md:21 [invalid-invariant] "
        "`none observed` is an observation, not N/A; it requires a real "
        "evidence grade (A|B|C|D|?)"
    ]


def test_none_observed_with_real_grade_is_valid(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    add_feature(
        root,
        extra_files={
            "characterization-record.md": characterization(
                value="none observed", na_grade="?"
            )
        },
    )
    assert run_schema(root) == []


def test_real_value_with_grade_na_is_invalid(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    add_feature(
        root,
        extra_files={
            "characterization-record.md": characterization(
                value='`out.txt` created', na_grade="N/A"
            )
        },
    )
    errors = run_schema(root)
    assert errors == [
        f"{FEATURES}/alpha/characterization-record.md:21 [invalid-invariant] "
        "Grade N/A is valid only when Value is N/A or `N/A (...)`, got "
        "Value ``out.txt` created`"
    ]


def test_characterization_ref_must_resolve(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    add_feature(
        root,
        extra_files={"characterization-record.md": characterization(ref="BR-099")},
    )
    errors = run_schema(root)
    assert errors == [
        f"{FEATURES}/alpha/characterization-record.md:15 [missing-ref] "
        "`BR-099` does not resolve in this feature's behavior-contract.md"
    ]


def test_characterization_header_br_ref_must_resolve(tmp_path: Path) -> None:
    record = characterization().replace(
        "- Behavior contract ref: BR-001", "- Behavior contract ref: BR-099"
    )
    root = make_repo(tmp_path)
    add_feature(root, extra_files={"characterization-record.md": record})
    errors = run_schema(root)
    assert errors == [
        f"{FEATURES}/alpha/characterization-record.md:4 [missing-ref] "
        "`BR-099` does not resolve in this feature's behavior-contract.md"
    ]


def test_characterization_duplicate_item_field_rejected(tmp_path: Path) -> None:
    record = characterization().replace(
        "- Ref: BR-001\n\n## files", "- Ref: BR-001\n- Grade: ?\n\n## files", 1
    )
    root = make_repo(tmp_path)
    add_feature(root, extra_files={"characterization-record.md": record})
    errors = run_schema(root)
    assert errors == [
        f"{FEATURES}/alpha/characterization-record.md:16 [duplicate-key] "
        "duplicate field `Grade` in capture item `exact input fixture`"
    ]


def test_characterization_empty_h1_id_rejected(tmp_path: Path) -> None:
    record = "# Characterization:\n\n- Record grade rollup: ?\n"
    root = make_repo(tmp_path)
    add_feature(root, extra_files={"characterization-record.md": record})
    errors = run_schema(root)
    assert errors == [
        f"{FEATURES}/alpha/characterization-record.md:1 [invalid-id] "
        "empty record ID; expected `# Characterization: <ID>`"
    ]


# --- verification report ---------------------------------------------------


@pytest.mark.parametrize("result", ["PASS", "FAIL", "PARTIAL", "BLOCKED"])
def test_verification_result_domain(tmp_path: Path, result: str) -> None:
    root = make_repo(tmp_path)
    add_feature(root, verification_text=VALID_VERIFICATION.replace("- Result: PASS", f"- Result: {result}"))
    assert run_schema(root) == []


@pytest.mark.parametrize("result", ["pass", "PASSED", "PASS (partial scope)", "PASS*"])
def test_verification_result_rejected(tmp_path: Path, result: str) -> None:
    root = make_repo(tmp_path)
    add_feature(root, verification_text=VALID_VERIFICATION.replace("- Result: PASS", f"- Result: {result}"))
    errors = run_schema(root)
    assert errors == [
        f"{FEATURES}/alpha/verification.md:3 [invalid-enum] "
        f"Result `{result}`; expected PASS|FAIL|PARTIAL|BLOCKED"
    ]


def test_verification_blank_result_is_not_a_violation(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    add_feature(root, verification_text=VALID_VERIFICATION.replace("- Result: PASS", "- Result:"))
    assert run_schema(root) == []


def test_verification_evidence_table_grade_cells_validated(tmp_path: Path) -> None:
    report = VALID_VERIFICATION.replace("| case-1 | Yes | ? |", "| case-1 | Yes | B+ |")
    root = make_repo(tmp_path)
    add_feature(root, verification_text=report)
    errors = run_schema(root)
    assert errors == [
        f"{FEATURES}/alpha/verification.md:9 [invalid-enum] "
        "Grade `B+`; expected A|B|C|D|?"
    ]


def test_verification_duplicate_result_field_rejected(tmp_path: Path) -> None:
    report = VALID_VERIFICATION.replace(
        "- Result: PASS", "- Result: PASS\n- Result: FAIL", 1
    )
    root = make_repo(tmp_path)
    add_feature(root, verification_text=report)
    errors = run_schema(root)
    assert errors == [
        f"{FEATURES}/alpha/verification.md:4 [duplicate-key] "
        "duplicate field `Result` in report header"
    ]


# --- OQ registry ------------------------------------------------------------


def test_valid_oq_registry_passes(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    write_oq_registry(root)
    errors, ids = validate_oq_registry(root)
    assert errors == []
    assert ids == {"OQ-001"}


def test_oq_id_format_rejected(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    write_oq_registry(root)
    registry = root / "docs" / "05-open-questions.md"
    registry.write_text(
        "| ID | Status | Question |\n|---|---|---|\n| OQ-12 | OPEN | q? |\n",
        encoding="utf-8",
    )
    errors, _ = validate_oq_registry(root)
    assert errors == ["docs/05-open-questions.md:3 [invalid-id] `OQ-12`; expected OQ-###"]


@pytest.mark.parametrize("row_id", ["oq-001", "OQ-0001", "OQ-01A", "XQ-001"])
def test_oq_id_near_misses_rejected(tmp_path: Path, row_id: str) -> None:
    root = make_repo(tmp_path)
    write_oq_registry(root)
    registry = root / "docs" / "05-open-questions.md"
    registry.write_text(
        f"| ID | Status | Question |\n|---|---|---|\n| {row_id} | OPEN | q? |\n",
        encoding="utf-8",
    )
    errors, _ = validate_oq_registry(root)
    assert errors == [
        f"docs/05-open-questions.md:3 [invalid-id] `{row_id}`; expected OQ-###"
    ]


def test_duplicate_oq_id_rejected(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    registry = root / "docs"
    registry.mkdir(parents=True)
    (registry / "05-open-questions.md").write_text(
        "# Open Questions\n\n"
        "| ID | Status | Question |\n|---|---|---|\n"
        "| OQ-001 | OPEN | q1 |\n"
        "| OQ-001 | OPEN | duplicate |\n",
        encoding="utf-8",
    )
    errors, _ = validate_oq_registry(root)
    assert errors == [
        "docs/05-open-questions.md:6 [duplicate-id] duplicate OQ ID `OQ-001` "
        "(first defined at line 5)"
    ]


@pytest.mark.parametrize("status", ["OPEN", "CONFIRMED", "NOT-APPLICABLE", "DEFERRED"])
def test_oq_status_domain(tmp_path: Path, status: str) -> None:
    root = make_repo(tmp_path)
    write_oq_registry(root)
    registry = root / "docs" / "05-open-questions.md"
    registry.write_text(
        f"| ID | Status | Question |\n|---|---|---|\n| OQ-001 | {status} | q? |\n",
        encoding="utf-8",
    )
    errors, _ = validate_oq_registry(root)
    assert errors == []


@pytest.mark.parametrize("status", ["open", "Closed", "OPEN (dup)", "WIP", "RESOLVED"])
def test_oq_status_rejected(tmp_path: Path, status: str) -> None:
    root = make_repo(tmp_path)
    write_oq_registry(root)
    registry = root / "docs" / "05-open-questions.md"
    registry.write_text(
        f"| ID | Status | Question |\n|---|---|---|\n| OQ-001 | {status} | q? |\n",
        encoding="utf-8",
    )
    errors, _ = validate_oq_registry(root)
    assert errors == [
        f"docs/05-open-questions.md:3 [invalid-enum] Status `{status}`; "
        "expected OPEN|CONFIRMED|NOT-APPLICABLE|DEFERRED"
    ]


def test_resolved_heading_must_point_at_registry_row(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    write_oq_registry(root)
    registry = root / "docs" / "05-open-questions.md"
    registry.write_text(
        "# Open Questions\n\n"
        "| ID | Status | Question |\n|---|---|---|\n"
        "| OQ-001 | CONFIRMED | q1 |\n\n"
        "## Resolved\n\n### OQ-001 — resolved title\n\nAnswer text.\n",
        encoding="utf-8",
    )
    errors, _ = validate_oq_registry(root)
    assert errors == []

    registry.write_text(
        "# Open Questions\n\n"
        "| ID | Status | Question |\n|---|---|---|\n"
        "| OQ-001 | CONFIRMED | q1 |\n\n"
        "## Resolved\n\n### OQ-099 — unknown\n\nAnswer text.\n",
        encoding="utf-8",
    )
    errors, _ = validate_oq_registry(root)
    assert errors == [
        "docs/05-open-questions.md:9 [missing-ref] `OQ-099` heading has no "
        "row in the registry table"
    ]


# --- feature-card structured OQ references ----------------------------------


def oq_card(body: str) -> str:
    return (
        "---\nid: alpha\nstage: done\nblocked: false\n---\n\n"
        "# Feature: alpha\n\n## Open questions\n\n" + body
    )


def test_feature_card_oq_bullet_reference_resolves(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    write_oq_registry(root)
    add_feature(root, card_text=oq_card("- OQ-001 — what is the DLL contract?\n"))
    assert run_schema(root) == []


def test_feature_card_oq_bullet_reference_missing(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    write_oq_registry(root)
    add_feature(root, card_text=oq_card("- OQ-099 — not registered\n"))
    errors = run_schema(root)
    assert errors == [
        f"{FEATURES}/alpha/feature-card.md:11 [missing-ref] "
        "`OQ-099` is not defined in docs/05-open-questions.md"
    ]


def test_feature_card_oq_bullet_reference_bad_format(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    write_oq_registry(root)
    add_feature(root, card_text=oq_card("- OQ-12 — malformed id\n"))
    errors = run_schema(root)
    assert errors == [
        f"{FEATURES}/alpha/feature-card.md:11 [invalid-id] `OQ-12`; expected OQ-###"
    ]


def test_feature_card_oq_prose_is_ignored(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    write_oq_registry(root)
    add_feature(
        root,
        card_text=oq_card("None — see OQ-099 discussion elsewhere for context.\n"),
    )
    assert run_schema(root) == []


# --- templates / prose / fenced code are never instance data ----------------


def test_templates_are_never_instances(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    templates = root / "docs" / "templates"
    templates.mkdir(parents=True)
    (templates / "evidence-record.md").write_text(
        "# Evidence: <ID>\n\n- Grade: A | B | C | D | ?\n"
        "- Source type: automated-test | runtime | db\n",
        encoding="utf-8",
    )
    (templates / "behavior-contract.md").write_text(
        "| Rule ID | Basis | Grade |\n|---|---|---|\n| BR-001 | Observed | B+ |\n",
        encoding="utf-8",
    )
    assert run_schema(root) == []


def test_fenced_code_and_prose_occurrences_are_ignored(tmp_path: Path) -> None:
    contract = (
        "# Behavior Contract: alpha\n\n"
        "Prose mentioning BR-999, OQ-999, and grades like B+ without structure.\n\n"
        "```markdown\n"
        "| Rule ID | Basis | Grade |\n"
        "|---|---|---|\n"
        "| BR-999 | Observed | B+ |\n"
        "```\n\n"
        "## Business rules\n\n"
        "| Rule ID | Basis | Rule | Evidence | Grade |\n"
        "|---|---|---|---|---|\n"
        "| BR-001 | observed | rule | e1 | ? |\n"
    )
    root = make_repo(tmp_path)
    add_feature(root, contract_text=contract)
    assert run_schema(root) == []


# --- aggregation -------------------------------------------------------------


def test_multiple_errors_aggregate_with_file_and_line(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    contract = (
        "# Behavior Contract: alpha\n\n## Business rules\n\n"
        "| Rule ID | Basis | Rule | Evidence | Grade |\n"
        "|---|---|---|---|---|\n"
        "| BR-01A | Observed | bad row | e1 | B+ |\n"
    )
    add_feature(
        root,
        contract_text=contract,
        verification_text=VALID_VERIFICATION.replace("- Result: PASS", "- Result: DONE"),
        extra_files={
            "evidence/ev-bad.md": evidence_text("X", "tests", history_grade="B")
        },
    )
    errors = run_schema(root)
    assert errors == [
        f"{FEATURES}/alpha/behavior-contract.md:7 [invalid-id] `BR-01A`; expected BR-###",
        f"{FEATURES}/alpha/behavior-contract.md:7 [invalid-enum] Basis `Observed`; expected observed|inferred",
        f"{FEATURES}/alpha/behavior-contract.md:7 [invalid-enum] Grade `B+`; expected A|B|C|D|?",
        f"{FEATURES}/alpha/verification.md:3 [invalid-enum] Result `DONE`; expected PASS|FAIL|PARTIAL|BLOCKED",
        f"{FEATURES}/alpha/evidence/ev-bad.md:5 [invalid-enum] Grade `X`; expected A|B|C|D|?",
        f"{FEATURES}/alpha/evidence/ev-bad.md:7 [invalid-enum] Source type `tests`; expected "
        "automated-test|runtime|db|log|callback|source|manual|other",
    ]


# --- real tree ---------------------------------------------------------------


def test_real_repo_passes_a1_and_a2_end_to_end() -> None:
    """Normalized synthetic-demo and the current OQ registry must pass."""
    assert collect_validation_errors(ROOT) == []


def test_real_oq_registry_passes() -> None:
    errors, _ = validate_oq_registry(ROOT)
    assert errors == []
