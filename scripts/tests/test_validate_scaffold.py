"""Tests for the A-1 feature-artifact checks in scripts/validate_scaffold.py.

Canonical contract: docs/08-feature-artifact-validation.md ("Validator
behavior", "Test requirements"). A-1 checks structure and machine-readable
feature-card metadata only — no heading/content or evidence-grade checks
(Non-goals).

Synthetic cases build a minimal fixture repository under tmp_path rather
than depending on the real migration/features/ tree, whose synthetic-demo
normalization lands on a separate branch. One test at the bottom does run
against the real tree and only asserts that no feature other than the
known-pending synthetic-demo structurally regresses.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.validate_scaffold import (
    ROOT,
    CANONICAL_SINGLETON_FILES,
    STAGES,
    STAGE_REQUIRED_FILES,
    validate_features,
)

FEATURES = "migration/features"


def make_repo(tmp_path: Path) -> Path:
    """Fixture repo root with same-basename templates for all singletons."""
    templates = tmp_path / "docs" / "templates"
    templates.mkdir(parents=True)
    for name in CANONICAL_SINGLETON_FILES:
        (templates / name).write_text(f"# {name} template\n", encoding="utf-8")
    return tmp_path


def add_feature(
    root: Path,
    name: str,
    *,
    stage: str = "discovered",
    blocked: str = "false",
    feature_id: str | None = None,
    documents: tuple[str, ...] = (),
    card_text: str | None = None,
    extra_files: dict[str, str] | None = None,
) -> Path:
    """Create a feature directory with a default-valid feature-card.md.

    ``documents`` are additional canonical singleton files to create;
    ``extra_files`` are arbitrary supporting files (evidence, aliases).
    """
    feature = root / FEATURES / name
    feature.mkdir(parents=True)
    if card_text is None:
        if feature_id is None:
            feature_id = name
        card_text = (
            "---\n"
            f"id: {feature_id}\n"
            f"stage: {stage}\n"
            f"blocked: {blocked}\n"
            "---\n"
        )
    (feature / "feature-card.md").write_text(card_text, encoding="utf-8")
    for document in documents:
        (feature / document).write_text(f"# {document}\n", encoding="utf-8")
    for filename, content in (extra_files or {}).items():
        (feature / filename).write_text(content, encoding="utf-8")
    return feature


def test_canonical_singleton_contract_is_exactly_six_files() -> None:
    assert CANONICAL_SINGLETON_FILES == (
        "feature-card.md",
        "legacy-map.md",
        "behavior-contract.md",
        "target-feature-design.md",
        "review.md",
        "verification.md",
    )


def test_stage_table_is_cumulative_and_complete() -> None:
    assert set(STAGE_REQUIRED_FILES) == set(STAGES)
    assert STAGE_REQUIRED_FILES["discovered"] == frozenset(
        {"feature-card.md", "legacy-map.md"}
    )
    assert STAGE_REQUIRED_FILES["specified"] == frozenset(
        {"feature-card.md", "legacy-map.md", "behavior-contract.md"}
    )
    assert STAGE_REQUIRED_FILES["implementing"] == STAGE_REQUIRED_FILES["designed"]
    assert STAGE_REQUIRED_FILES["done"] == frozenset(CANONICAL_SINGLETON_FILES)
    for earlier, later in zip(STAGES, STAGES[1:]):
        assert STAGE_REQUIRED_FILES[earlier] <= STAGE_REQUIRED_FILES[later]


def test_no_feature_directories_passes(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    assert validate_features(root) == []

    (root / FEATURES).mkdir(parents=True)
    (root / FEATURES / "README.md").write_text("not a feature\n", encoding="utf-8")
    assert validate_features(root) == []


def test_valid_metadata_passes(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    add_feature(root, "greeting-concat", documents=("legacy-map.md",))
    assert validate_features(root) == []


def test_invalid_directory_name_fails(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    add_feature(root, "Bad_Name", documents=("legacy-map.md",))
    errors = validate_features(root)
    assert len(errors) == 1
    assert "invalid feature directory name" in errors[0]
    assert "Bad_Name" in errors[0]


def test_missing_feature_card_fails(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    (root / FEATURES / "alpha").mkdir(parents=True)
    errors = validate_features(root)
    assert errors == [
        f"{FEATURES}/alpha/feature-card.md: required file missing",
    ]


def test_id_mismatch_fails(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    add_feature(root, "alpha", feature_id="beta", documents=("legacy-map.md",))
    errors = validate_features(root)
    assert len(errors) == 1
    assert "id 'beta' does not match directory name 'alpha'" in errors[0]


def test_unknown_stage_fails(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    add_feature(root, "alpha", stage="complete", documents=("legacy-map.md",))
    errors = validate_features(root)
    assert len(errors) == 1
    assert "unknown stage 'complete'" in errors[0]


def test_malformed_blocked_fails(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    add_feature(root, "alpha", blocked="maybe", documents=("legacy-map.md",))
    errors = validate_features(root)
    assert len(errors) == 1
    assert "blocked must be 'true' or 'false', got 'maybe'" in errors[0]


def test_missing_metadata_key_fails(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    card = "---\nid: alpha\nstage: discovered\n---\n"
    add_feature(root, "alpha", card_text=card, documents=("legacy-map.md",))
    errors = validate_features(root)
    assert errors == [
        f"{FEATURES}/alpha/feature-card.md: missing frontmatter key: blocked",
    ]


def test_done_with_blocked_true_is_invalid(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    add_feature(
        root,
        "alpha",
        stage="done",
        blocked="true",
        documents=tuple(CANONICAL_SINGLETON_FILES[1:]),
    )
    errors = validate_features(root)
    assert errors == [
        f"{FEATURES}/alpha/feature-card.md: stage 'done' cannot be blocked "
        "(completed and currently blocked are mutually exclusive)",
    ]


@pytest.mark.parametrize("stage", STAGES)
def test_complete_document_set_passes_for_every_stage(
    tmp_path: Path, stage: str
) -> None:
    root = make_repo(tmp_path)
    documents = tuple(
        sorted(STAGE_REQUIRED_FILES[stage] - {"feature-card.md"})
    )
    add_feature(root, "alpha", stage=stage, documents=documents)
    assert validate_features(root) == []


@pytest.mark.parametrize(
    "stage,missing",
    [
        (stage, missing)
        for stage in STAGES
        for missing in sorted(STAGE_REQUIRED_FILES[stage] - {"feature-card.md"})
    ],
)
def test_each_stage_requires_every_cumulative_document(
    tmp_path: Path, stage: str, missing: str
) -> None:
    root = make_repo(tmp_path)
    documents = tuple(
        sorted(STAGE_REQUIRED_FILES[stage] - {"feature-card.md"} - {missing})
    )
    add_feature(root, "alpha", stage=stage, documents=documents)
    assert validate_features(root) == [
        f"{FEATURES}/alpha/{missing}: required by stage '{stage}' but missing",
    ]


def test_blocked_feature_retains_stage_requirements(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    documents = ("legacy-map.md", "behavior-contract.md", "target-feature-design.md")
    add_feature(root, "alpha", stage="reviewing", blocked="true", documents=documents)
    errors = validate_features(root)
    assert errors == [
        f"{FEATURES}/alpha/review.md: required by stage 'reviewing' but missing",
    ]

    add_feature(root, "beta", stage="reviewing", blocked="true",
                documents=documents + ("review.md",))
    assert validate_features(root) == [errors[0]]


def test_optional_evidence_and_supporting_files_are_ignored(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    feature = add_feature(
        root,
        "alpha",
        stage="done",
        documents=tuple(CANONICAL_SINGLETON_FILES[1:]),
    )
    evidence = feature / "evidence"
    evidence.mkdir()
    (evidence / "capture-foobar.md").write_text("evidence record\n", encoding="utf-8")
    (feature / "characterization-record.md").write_text("extra\n", encoding="utf-8")
    (feature / "notes.txt").write_text("extra\n", encoding="utf-8")
    assert validate_features(root) == []


def test_multiple_failures_across_features_reported_together(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    add_feature(root, "alpha", stage="discovered")  # missing legacy-map.md
    add_feature(root, "beta", stage="done", blocked="true",
                documents=tuple(CANONICAL_SINGLETON_FILES[1:]))
    add_feature(root, "gamma", feature_id="gamma-x",
                documents=("legacy-map.md",))
    errors = validate_features(root)
    assert len(errors) == 3
    assert f"{FEATURES}/alpha/legacy-map.md: required by stage 'discovered' but missing" in errors
    assert f"{FEATURES}/beta/feature-card.md: stage 'done' cannot be blocked (completed and currently blocked are mutually exclusive)" in errors
    assert (
        f"{FEATURES}/gamma/feature-card.md: id 'gamma-x' does not match directory name 'gamma'"
        in errors
    )


@pytest.mark.parametrize("template_name", CANONICAL_SINGLETON_FILES)
def test_template_basename_drift_fails(
    tmp_path: Path, template_name: str
) -> None:
    root = make_repo(tmp_path)
    (root / "docs" / "templates" / template_name).unlink()
    assert validate_features(root) == [
        f"docs/templates/{template_name}: canonical singleton template missing "
        "(template basename must equal the runtime filename)",
    ]


@pytest.mark.parametrize(
    "alias,canonical,stage,documents",
    [
        ("feature.md", "feature-card.md", "discovered", ("legacy-map.md",)),
        (
            "target-design.md",
            "target-feature-design.md",
            "designed",
            ("legacy-map.md", "behavior-contract.md"),
        ),
        (
            "verification-report.md",
            "verification.md",
            "verifying",
            (
                "legacy-map.md",
                "behavior-contract.md",
                "target-feature-design.md",
                "review.md",
            ),
        ),
    ],
)
def test_legacy_alias_does_not_satisfy_canonical_requirement(
    tmp_path: Path,
    alias: str,
    canonical: str,
    stage: str,
    documents: tuple[str, ...],
) -> None:
    root = make_repo(tmp_path)
    card = (
        "---\n"
        "id: alpha\n"
        f"stage: {stage}\n"
        "blocked: false\n"
        "---\n"
    )
    if canonical == "feature-card.md":
        feature = root / FEATURES / "alpha"
        feature.mkdir(parents=True)
        (feature / alias).write_text(card, encoding="utf-8")
        for document in documents:
            (feature / document).write_text("x\n", encoding="utf-8")
        assert validate_features(root) == [
            f"{FEATURES}/alpha/feature-card.md: required file missing "
            f"(legacy alias '{alias}' found; rename it to 'feature-card.md')",
        ]
    else:
        add_feature(
            root,
            "alpha",
            stage=stage,
            documents=documents,
            card_text=card,
            extra_files={alias: "# legacy alias\n"},
        )
        assert validate_features(root) == [
            f"{FEATURES}/alpha/{canonical}: required by stage '{stage}' but missing "
            f"(legacy alias '{alias}' found; rename it to '{canonical}')",
        ]


def test_duplicate_frontmatter_key_fails(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    card = "---\nid: alpha\nstage: discovered\nstage: done\nblocked: false\n---\n"
    add_feature(root, "alpha", card_text=card, documents=("legacy-map.md",))
    errors = validate_features(root)
    assert errors == [
        f"{FEATURES}/alpha/feature-card.md: duplicate frontmatter key: stage",
    ]


def test_card_without_frontmatter_reports_missing_metadata_without_crash(
    tmp_path: Path,
) -> None:
    """Current shape of the real synthetic-demo card until normalization lands."""
    root = make_repo(tmp_path)
    card = "# Feature: alpha\n\n- ID: alpha\n- Status: done (dry-run only)\n"
    add_feature(root, "alpha", card_text=card)
    errors = validate_features(root)
    assert f"{FEATURES}/alpha/feature-card.md: missing YAML frontmatter" in errors
    assert f"{FEATURES}/alpha/feature-card.md: missing frontmatter key: id" in errors
    assert f"{FEATURES}/alpha/feature-card.md: missing frontmatter key: stage" in errors
    assert f"{FEATURES}/alpha/feature-card.md: missing frontmatter key: blocked" in errors


def test_normalized_synthetic_demo_fixture_passes_as_done(tmp_path: Path) -> None:
    """The normalized synthetic-demo shape from docs/08 must pass as done."""
    root = make_repo(tmp_path)
    card = (
        "---\n"
        "id: synthetic-demo\n"
        "stage: done\n"
        "blocked: false\n"
        "---\n"
    )
    feature = add_feature(
        root,
        "synthetic-demo",
        stage="done",
        feature_id="synthetic-demo",
        documents=tuple(CANONICAL_SINGLETON_FILES[1:]),
        card_text=card,
    )
    (feature / "characterization-record.md").write_text("extra\n", encoding="utf-8")
    (feature / "DRY-RUN-REPORT.md").write_text("extra\n", encoding="utf-8")
    evidence = feature / "evidence"
    evidence.mkdir()
    (evidence / "s011-dry-run.md").write_text("evidence\n", encoding="utf-8")
    assert validate_features(root) == []


def test_real_features_tree_has_no_structural_regressions_beyond_synthetic_demo() -> None:
    """Real-tree smoke test: the only tolerated failures are synthetic-demo's
    known normalization gaps (frontmatter/stage files land on a sibling branch
    per docs/08 "Repository normalization"); no feature may be exempted."""
    errors = validate_features(ROOT)
    assert all("synthetic-demo" in error for error in errors), errors
