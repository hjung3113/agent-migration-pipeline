from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "README.md",
    "AGENTS.md",
    "opencode.json",
    "docs/00-project-context.md",
    "docs/05-open-questions.md",
    "migration/RULEBOOK.md",
    "migration/STATE.md",
    "migration/QUEUE.md",
]

SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

# A-1 feature-artifact contract: docs/08-feature-artifact-validation.md.

FEATURES_DIR = "migration/features"
TEMPLATES_DIR = "docs/templates"
FEATURE_CARD = "feature-card.md"

CANONICAL_SINGLETON_FILES = (
    "feature-card.md",
    "legacy-map.md",
    "behavior-contract.md",
    "target-feature-design.md",
    "review.md",
    "verification.md",
)

# Non-canonical singleton names that must never satisfy a canonical
# requirement (docs/08 "Canonical singleton feature artifacts").
LEGACY_SINGLETON_ALIASES = {
    "feature.md": "feature-card.md",
    "target-design.md": "target-feature-design.md",
    "verification-report.md": "verification.md",
}

STAGES = (
    "discovered",
    "specified",
    "designed",
    "implementing",
    "reviewing",
    "verifying",
    "done",
)

BOOLEAN_VALUES = ("true", "false")

# Cumulative stage requirements (docs/08 "Artifact requirements by stage"):
# every stage keeps all documents required by earlier stages; feature-card.md
# is required from the first stage. "implementing" adds no Markdown artifact
# because implementation is the code/data/configuration change itself.
_STAGE_NEW_DOCUMENTS = {
    "discovered": ("legacy-map.md",),
    "specified": ("behavior-contract.md",),
    "designed": ("target-feature-design.md",),
    "implementing": (),
    "reviewing": ("review.md",),
    "verifying": ("verification.md",),
    "done": (),
}


def _stage_requirements() -> dict[str, frozenset[str]]:
    required: set[str] = {FEATURE_CARD}
    table: dict[str, frozenset[str]] = {}
    for stage in STAGES:
        required = required | set(_STAGE_NEW_DOCUMENTS[stage])
        table[stage] = frozenset(required)
    return table


STAGE_REQUIRED_FILES = _stage_requirements()


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def validate_required() -> None:
    missing = [path for path in REQUIRED if not (ROOT / path).exists()]
    if missing:
        fail(f"missing required files: {', '.join(missing)}")


def validate_json() -> None:
    with (ROOT / "opencode.json").open(encoding="utf-8") as f:
        data = json.load(f)
    if data.get("$schema") != "https://opencode.ai/config.json":
        fail("opencode.json has unexpected or missing $schema")


def parse_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        fail(f"missing YAML frontmatter: {path.relative_to(ROOT)}")
    try:
        _, raw, _ = text.split("---", 2)
    except ValueError:
        fail(f"invalid frontmatter delimiters: {path.relative_to(ROOT)}")
    result: dict[str, str] = {}
    for line in raw.splitlines():
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip()
    return result


def validate_skills() -> None:
    skill_root = ROOT / ".opencode" / "skills"
    for skill_dir in sorted(p for p in skill_root.iterdir() if p.is_dir()):
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            fail(f"skill directory has no SKILL.md: {skill_dir.name}")
        fm = parse_frontmatter(skill_file)
        name = fm.get("name", "")
        if name != skill_dir.name:
            fail(f"skill name mismatch: {skill_dir.name} != {name}")
        if not SKILL_NAME_RE.fullmatch(name):
            fail(f"invalid skill name: {name}")
        if not fm.get("description"):
            fail(f"skill has no description: {name}")


def validate_agents_and_commands() -> None:
    for directory in [ROOT / ".opencode" / "agents", ROOT / ".opencode" / "commands"]:
        for path in directory.glob("*.md"):
            fm = parse_frontmatter(path)
            if not fm.get("description"):
                fail(f"missing description: {path.relative_to(ROOT)}")


def parse_feature_card(text: str) -> tuple[dict[str, str], list[str]]:
    """Parse the constrained flat frontmatter of a feature-card.md.

    Returns (metadata, errors) instead of failing fast so every feature's
    failures can be aggregated into one repair list. Duplicate keys are
    reported rather than silently overwriting.
    """
    errors: list[str] = []
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, ["missing YAML frontmatter"]
    closing = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            closing = index
            break
    if closing is None:
        return {}, ["unterminated YAML frontmatter"]
    metadata: dict[str, str] = {}
    for line in lines[1:closing]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if line.startswith((" ", "\t")):
            errors.append(
                f"invalid indented frontmatter line (nested/malformed YAML is "
                f"not part of the constrained flat contract): {stripped!r}"
            )
            continue
        if ":" not in line or not line.split(":", 1)[0].strip():
            errors.append(f"unparseable frontmatter line: {stripped!r}")
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        if key in metadata:
            errors.append(f"duplicate frontmatter key: {key}")
            continue
        metadata[key] = value.strip()
    return metadata, errors


def validate_feature(feature_dir: Path, rel: str) -> list[str]:
    """Structural A-1 checks for one feature directory (aggregate, no fail-fast)."""
    errors: list[str] = []
    name = feature_dir.name
    if not SKILL_NAME_RE.fullmatch(name):
        errors.append(
            f"{rel}: invalid feature directory name {name!r} "
            f"(must match {SKILL_NAME_RE.pattern})"
        )

    # A legacy singleton alias must never coexist with (or substitute for) its
    # canonical file — two files could otherwise diverge with no deterministic
    # source of truth (docs/08 "Adversarial findings" #3). Check unconditionally,
    # independent of whether the canonical file is present.
    for alias, canonical in LEGACY_SINGLETON_ALIASES.items():
        if (feature_dir / alias).is_file():
            errors.append(
                f"{rel}/{alias}: non-canonical legacy alias present "
                f"(rename to {canonical!r}; canonical and alias must not coexist)"
            )

    card_rel = f"{rel}/{FEATURE_CARD}"
    card_path = feature_dir / FEATURE_CARD
    if not card_path.is_file():
        errors.append(f"{card_rel}: required file missing")
        return errors

    metadata, card_errors = parse_feature_card(
        card_path.read_text(encoding="utf-8")
    )
    errors.extend(f"{card_rel}: {detail}" for detail in card_errors)
    for key in ("id", "stage", "blocked"):
        if key not in metadata:
            errors.append(f"{card_rel}: missing frontmatter key: {key}")

    feature_id = metadata.get("id")
    if feature_id is not None and feature_id != name:
        errors.append(
            f"{card_rel}: id {feature_id!r} does not match directory name {name!r}"
        )

    stage = metadata.get("stage")
    if stage is not None and stage not in STAGE_REQUIRED_FILES:
        errors.append(
            f"{card_rel}: unknown stage {stage!r} "
            f"(expected one of: {' | '.join(STAGES)})"
        )
        stage = None

    blocked: bool | None = None
    blocked_raw = metadata.get("blocked")
    if blocked_raw is not None:
        if blocked_raw not in BOOLEAN_VALUES:
            errors.append(
                f"{card_rel}: blocked must be 'true' or 'false', got {blocked_raw!r}"
            )
        else:
            blocked = blocked_raw == "true"
    if stage == "done" and blocked:
        errors.append(
            f"{card_rel}: stage 'done' cannot be blocked "
            "(completed and currently blocked are mutually exclusive)"
        )

    if stage is None:
        return errors

    for required in sorted(STAGE_REQUIRED_FILES[stage]):
        if (feature_dir / required).is_file():
            continue
        errors.append(f"{rel}/{required}: required by stage {stage!r} but missing")
    return errors


def validate_features(root: Path | None = None) -> list[str]:
    """A-1 feature-artifact validation; returns every structural failure."""
    base = ROOT if root is None else root
    errors: list[str] = []

    for singleton in CANONICAL_SINGLETON_FILES:
        template = base / TEMPLATES_DIR / singleton
        if not template.is_file():
            errors.append(
                f"{TEMPLATES_DIR}/{singleton}: canonical singleton template missing "
                "(template basename must equal the runtime filename)"
            )

    features_root = base / FEATURES_DIR
    if not features_root.is_dir():
        return errors
    for entry in sorted(features_root.iterdir()):
        if not entry.is_dir():
            continue  # e.g. migration/features/README.md is not a feature
        errors.extend(validate_feature(entry, f"{FEATURES_DIR}/{entry.name}"))
    return errors


def main() -> None:
    validate_required()
    validate_json()
    validate_skills()
    validate_agents_and_commands()
    feature_errors = validate_features()
    if feature_errors:
        raise SystemExit(
            "ERROR: feature artifact validation failed "
            f"({len(feature_errors)} issue(s)):\n"
            + "\n".join(f"- {error}" for error in feature_errors)
        )
    print("Scaffold validation passed.")


if __name__ == "__main__":
    main()
