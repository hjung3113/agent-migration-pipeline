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


# A-2 artifact schema/reference validation:
# docs/issue-2-artifact-schema-validation.md. Closed value domains, ID
# formats/scopes, and explicitly structured references only — no semantic
# completeness, no prose scanning, no revision-aware grade history (#9).

BR_ID_RE = re.compile(r"^BR-\d{3}$")
OQ_ID_RE = re.compile(r"^OQ-\d{3}$")
OQ_ID_PREFIX_RE = re.compile(r"^OQ-[0-9A-Za-z]+$")
GRADES = ("A", "B", "C", "D", "?")
ITEM_GRADES = GRADES + ("N/A",)
PROVENANCE_VALUES = ("observed", "inferred")
SOURCE_TYPES = (
    "automated-test",
    "runtime",
    "db",
    "log",
    "callback",
    "source",
    "manual",
    "other",
)
VERIFICATION_RESULTS = ("PASS", "FAIL", "PARTIAL", "BLOCKED")
OQ_STATUSES = ("OPEN", "CONFIRMED", "NOT-APPLICABLE", "DEFERRED")
OQ_REGISTRY_PATH = "docs/05-open-questions.md"
EVIDENCE_H1_RE = re.compile(r"^Evidence:\s*(.*)$")
CHARACTERIZATION_H1_RE = re.compile(r"^Characterization:\s*(.*)$")
OQ_HEADING_RE = re.compile(r"^###\s+OQ-(\S+)")
HEADING2_RE = re.compile(r"^#{2,6}\s+(.*?)\s*$")
KV_FIELD_RE = re.compile(r"^-\s+([^:]+):\s*(.*)$")
CLAIM_MARKER_RE = re.compile(r"^\s*[-*]\s+\[([^\]]+)\]")
MARKDOWN_LINK_RE = re.compile(r"^\s*[-*]\s+\[[^\]]*\]\(")
# Markdown task-list checkbox states (`- [ ]`, `- [x]`, `- [X]`) are list
# syntax, not provenance markers, and must not be mistaken for one.
TASK_LIST_MARKER_RE = re.compile(r"^[ xX]?$")
ITEM_FIELD_KEYS = frozenset({"Format", "Value", "Grade", "Ref"})
# Optional dedicated BR-reference field names on evidence records. The
# current evidence template has none; when an instance declares one it is
# a structured reference and must resolve.
BR_REF_FIELD_KEYS = ("Behavior contract ref", "BR ref")


def _visible_numbered(lines):
    """Yield (lineno, line) skipping fenced code blocks and HTML comments,
    preserving the caller's line numbers. Shared by `_visible_lines` (whole
    file text) and durable-state checks (a pre-sliced body line range)."""
    in_fence = False
    in_comment = False
    for lineno, line in lines:
        stripped = line.lstrip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if in_comment:
            if "-->" in stripped:
                in_comment = False
            continue
        if stripped.startswith("<!--"):
            if "-->" not in stripped:
                in_comment = True
            continue
        yield lineno, line


def _visible_lines(text: str):
    """Yield (lineno, line) skipping fenced code blocks and HTML comments."""
    yield from _visible_numbered(enumerate(text.splitlines(), start=1))


def _split_row(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [cell.strip() for cell in s.split("|")]


def _is_separator_row(cells: list[str]) -> bool:
    return bool(cells) and all(
        re.fullmatch(r":?-+:?", cell) for cell in cells if cell
    )


def _parse_tables(lines: list[tuple[int, str]]):
    """Yield (header_lineno, headers, rows); rows are (lineno, cells)."""
    i = 0
    while i < len(lines):
        if not lines[i][1].lstrip().startswith("|"):
            i += 1
            continue
        j = i + 1
        if (
            j >= len(lines)
            or not lines[j][1].lstrip().startswith("|")
            or not _is_separator_row(_split_row(lines[j][1]))
        ):
            i += 1
            continue
        headers = _split_row(lines[i][1])
        rows: list[tuple[int, list[str]]] = []
        k = j + 1
        while k < len(lines) and lines[k][1].lstrip().startswith("|"):
            rows.append((lines[k][0], _split_row(lines[k][1])))
            k += 1
        yield lines[i][0], headers, rows
        i = k


def _cell(headers: list[str], cells: list[str], name: str) -> str | None:
    try:
        index = headers.index(name)
    except ValueError:
        return None
    if index >= len(cells):
        return ""
    return cells[index]


def _split_sections(
    lines: list[tuple[int, str]]
) -> tuple[list[tuple[int, str]], list[tuple[str, list[tuple[int, str]]]]]:
    """Split into (header block, sections) at level-2+ headings.

    The header block is everything before the first such heading; section
    titles are lowercased for case-insensitive lookup.
    """
    header: list[tuple[int, str]] = []
    sections: list[tuple[str, list[tuple[int, str]]]] = []
    title: str | None = None
    current: list[tuple[int, str]] = []
    for lineno, line in lines:
        match = HEADING2_RE.match(line)
        if match:
            if title is not None:
                sections.append((title, current))
            title = match.group(1).strip().lower()
            current = []
        elif title is None:
            header.append((lineno, line))
        else:
            current.append((lineno, line))
    if title is not None:
        sections.append((title, current))
    return header, sections


def _parse_kv(lines: list[tuple[int, str]]) -> list[tuple[int, str, str]]:
    """Parse `- Key: value` fields; returns (lineno, key, value) triples."""
    fields = []
    for lineno, line in lines:
        match = KV_FIELD_RE.match(line)
        if match:
            fields.append((lineno, match.group(1).strip(), match.group(2).strip()))
    return fields


def _unique_fields(
    fields: list[tuple[int, str, str]]
) -> tuple[dict[str, tuple[int, str]], list[tuple[int, str]]]:
    """Map keys to (lineno, value); duplicates are reported, never merged."""
    seen: dict[str, tuple[int, str]] = {}
    duplicates: list[tuple[int, str]] = []
    for lineno, key, value in fields:
        if key in seen:
            duplicates.append((lineno, key))
        else:
            seen[key] = (lineno, value)
    return seen, duplicates


def _err(rel: str, lineno: int, category: str, message: str) -> str:
    return f"{rel}:{lineno} [{category}] {message}"


def _check_br_reference(
    rel: str, lineno: int, value: str, br_ids: dict[str, int], errors: list[str]
) -> None:
    if not BR_ID_RE.fullmatch(value):
        errors.append(_err(rel, lineno, "invalid-id", f"`{value}`; expected BR-###"))
    elif value not in br_ids:
        errors.append(
            _err(
                rel,
                lineno,
                "missing-ref",
                f"`{value}` does not resolve in this feature's behavior-contract.md",
            )
        )


def _validate_grade_cells(
    rel: str,
    tables,
    br_scope: bool,
    br_ids: dict[str, int],
    errors: list[str],
) -> None:
    """Validate Basis/Grade cells (and Rule IDs in the BR table) of tables."""
    for _header_lineno, headers, rows in tables:
        for row_lineno, cells in rows:
            if not any(cells):
                continue
            if br_scope:
                rule_id = _cell(headers, cells, "Rule ID")
                if rule_id:
                    if not BR_ID_RE.fullmatch(rule_id):
                        errors.append(
                            _err(
                                rel,
                                row_lineno,
                                "invalid-id",
                                f"`{rule_id}`; expected BR-###",
                            )
                        )
                    elif rule_id in br_ids:
                        errors.append(
                            _err(
                                rel,
                                row_lineno,
                                "duplicate-id",
                                f"duplicate Rule ID `{rule_id}` within this "
                                f"behavior contract (first defined at line "
                                f"{br_ids[rule_id]})",
                            )
                        )
                    else:
                        br_ids[rule_id] = row_lineno
            basis = _cell(headers, cells, "Basis")
            if basis and basis not in PROVENANCE_VALUES:
                errors.append(
                    _err(
                        rel,
                        row_lineno,
                        "invalid-enum",
                        f"Basis `{basis}`; expected observed|inferred",
                    )
                )
            grade = _cell(headers, cells, "Grade")
            if grade and grade not in GRADES:
                errors.append(
                    _err(
                        rel,
                        row_lineno,
                        "invalid-enum",
                        f"Grade `{grade}`; expected A|B|C|D|?",
                    )
                )


def validate_behavior_contract(
    path: Path, rel: str, errors: list[str]
) -> dict[str, int]:
    """A-2 checks for one behavior-contract.md; returns its BR-ID map."""
    lines = list(_visible_lines(path.read_text(encoding="utf-8")))
    br_ids: dict[str, int] = {}
    _header, sections = _split_sections(lines)
    for title, section_lines in sections:
        tables = _parse_tables(section_lines)
        _validate_grade_cells(
            rel, tables, br_scope=(title == "business rules"), br_ids=br_ids,
            errors=errors,
        )
    # Claim provenance markers: bullets that open with a bracketed marker
    # (but not markdown links) must be exactly [observed] or [inferred].
    for lineno, line in lines:
        match = CLAIM_MARKER_RE.match(line)
        if not match or MARKDOWN_LINK_RE.match(line):
            continue
        marker = match.group(1)
        if TASK_LIST_MARKER_RE.fullmatch(marker):
            continue
        if marker not in PROVENANCE_VALUES:
            errors.append(
                _err(
                    rel,
                    lineno,
                    "invalid-marker",
                    f"claim marker `[{marker}]`; expected [observed] or [inferred]",
                )
            )
    return br_ids


def validate_feature_card_oq(
    path: Path, rel: str, oq_ids: set[str], errors: list[str]
) -> None:
    """Structured OQ references in the feature-card `## Open questions`
    section: a bullet whose leading token is OQ-shaped must be well-formed
    and resolve in the global registry. Prose is ignored."""
    lines = list(_visible_lines(path.read_text(encoding="utf-8")))
    _header, sections = _split_sections(lines)
    for title, section_lines in sections:
        if title != "open questions":
            continue
        for lineno, line in section_lines:
            match = re.match(r"^\s*[-*]\s+(\S+)", line)
            if not match:
                continue
            token = match.group(1)
            if not OQ_ID_PREFIX_RE.fullmatch(token):
                continue
            if not OQ_ID_RE.fullmatch(token):
                errors.append(
                    _err(rel, lineno, "invalid-id", f"`{token}`; expected OQ-###")
                )
            elif token not in oq_ids:
                errors.append(
                    _err(
                        rel,
                        lineno,
                        "missing-ref",
                        f"`{token}` is not defined in {OQ_REGISTRY_PATH}",
                    )
                )


def validate_verification(path: Path, rel: str, errors: list[str]) -> None:
    """A-2 checks for a canonical verification.md instance."""
    lines = list(_visible_lines(path.read_text(encoding="utf-8")))
    header, sections = _split_sections(lines)
    seen, duplicates = _unique_fields(_parse_kv(header))
    for lineno, key in duplicates:
        errors.append(
            _err(rel, lineno, "duplicate-key", f"duplicate field `{key}` in report header")
        )
    result = seen.get("Result")
    if result and result[1] and result[1] not in VERIFICATION_RESULTS:
        errors.append(
            _err(
                rel,
                result[0],
                "invalid-enum",
                f"Result `{result[1]}`; expected PASS|FAIL|PARTIAL|BLOCKED",
            )
        )
    all_lines = header + [line for _, section in sections for line in section]
    for _header_lineno, headers, rows in _parse_tables(all_lines):
        if "Grade" not in headers:
            continue
        for row_lineno, cells in rows:
            grade = _cell(headers, cells, "Grade")
            if grade and grade not in GRADES:
                errors.append(
                    _err(
                        rel,
                        row_lineno,
                        "invalid-enum",
                        f"Grade `{grade}`; expected A|B|C|D|?",
                    )
                )


def validate_evidence_record(
    path: Path, rel: str, record_id: str, id_lineno: int, br_ids: dict[str, int],
    errors: list[str],
) -> None:
    """A-2 checks for one evidence-record instance (identified by its
    `# Evidence: <ID>` H1)."""
    if not record_id:
        errors.append(
            _err(
                rel,
                id_lineno,
                "invalid-id",
                "empty record ID; expected `# Evidence: <ID>`",
            )
        )
    lines = list(_visible_lines(path.read_text(encoding="utf-8")))
    header, _sections = _split_sections(lines)
    seen, duplicates = _unique_fields(_parse_kv(header))
    for lineno, key in duplicates:
        errors.append(
            _err(rel, lineno, "duplicate-key", f"duplicate field `{key}` in record header")
        )
    grade = seen.get("Grade")
    if grade and grade[1] and grade[1] not in GRADES:
        errors.append(
            _err(rel, grade[0], "invalid-enum", f"Grade `{grade[1]}`; expected A|B|C|D|?")
        )
    source_type = seen.get("Source type")
    if source_type and source_type[1] and source_type[1] not in SOURCE_TYPES:
        errors.append(
            _err(
                rel,
                source_type[0],
                "invalid-enum",
                f"Source type `{source_type[1]}`; expected "
                + "|".join(SOURCE_TYPES),
            )
        )
    for key in BR_REF_FIELD_KEYS:
        ref = seen.get(key)
        if ref and ref[1]:
            _check_br_reference(rel, ref[0], ref[1], br_ids, errors)


def validate_characterization_record(
    path: Path, rel: str, record_id: str, id_lineno: int, br_ids: dict[str, int],
    errors: list[str],
) -> None:
    """A-2 checks for one characterization-record instance (`- Key: value`
    header fields plus fixed capture-item sections)."""
    if not record_id:
        errors.append(
            _err(
                rel,
                id_lineno,
                "invalid-id",
                "empty record ID; expected `# Characterization: <ID>`",
            )
        )
    lines = list(_visible_lines(path.read_text(encoding="utf-8")))
    header, sections = _split_sections(lines)
    seen, duplicates = _unique_fields(_parse_kv(header))
    for lineno, key in duplicates:
        errors.append(
            _err(rel, lineno, "duplicate-key", f"duplicate field `{key}` in record header")
        )
    rollup = seen.get("Record grade rollup")
    if rollup and rollup[1] and rollup[1] not in GRADES:
        errors.append(
            _err(
                rel,
                rollup[0],
                "invalid-enum",
                f"Record grade rollup `{rollup[1]}`; expected A|B|C|D|?",
            )
        )
    behavior_ref = seen.get("Behavior contract ref")
    if behavior_ref and behavior_ref[1]:
        _check_br_reference(rel, behavior_ref[0], behavior_ref[1], br_ids, errors)
    for title, section_lines in sections:
        fields = _parse_kv(section_lines)
        if not any(key in ITEM_FIELD_KEYS for _lineno, key, _value in fields):
            continue
        item_seen, item_duplicates = _unique_fields(fields)
        for lineno, key in item_duplicates:
            errors.append(
                _err(
                    rel,
                    lineno,
                    "duplicate-key",
                    f"duplicate field `{key}` in capture item `{title}`",
                )
            )
        grade = item_seen.get("Grade")
        value = item_seen.get("Value")
        if grade and grade[1] and grade[1] not in ITEM_GRADES:
            errors.append(
                _err(
                    rel,
                    grade[0],
                    "invalid-enum",
                    f"Grade `{grade[1]}`; expected A|B|C|D|?|N/A",
                )
            )
        if grade and grade[1] == "N/A" and value:
            if value[1] == "none observed":
                errors.append(
                    _err(
                        rel,
                        grade[0],
                        "invalid-invariant",
                        "`none observed` is an observation, not N/A; it "
                        "requires a real evidence grade (A|B|C|D|?)",
                    )
                )
            elif not (value[1] == "N/A" or value[1].startswith("N/A (")):
                errors.append(
                    _err(
                        rel,
                        grade[0],
                        "invalid-invariant",
                        f"Grade N/A is valid only when Value is N/A or "
                        f"`N/A (...)`, got Value `{value[1]}`",
                    )
                )
        ref = item_seen.get("Ref")
        if ref and ref[1]:
            _check_br_reference(rel, ref[0], ref[1], br_ids, errors)


def _first_h1(lines: list[tuple[int, str]]) -> tuple[int, str] | None:
    for lineno, line in lines:
        if line.startswith("# "):
            return lineno, line[2:].strip()
    return None


def validate_feature_schemas(root: Path, oq_ids: set[str]) -> list[str]:
    """A-2 schema/reference validation across every feature directory."""
    errors: list[str] = []
    features_root = root / FEATURES_DIR
    if not features_root.is_dir():
        return errors
    for entry in sorted(p for p in features_root.iterdir() if p.is_dir()):
        rel = f"{FEATURES_DIR}/{entry.name}"

        contract = entry / "behavior-contract.md"
        br_ids: dict[str, int] = {}
        if contract.is_file():
            br_ids = validate_behavior_contract(
                contract, f"{rel}/behavior-contract.md", errors
            )

        card = entry / FEATURE_CARD
        if card.is_file():
            validate_feature_card_oq(card, f"{rel}/{FEATURE_CARD}", oq_ids, errors)

        verification = entry / "verification.md"
        if verification.is_file():
            validate_verification(verification, f"{rel}/verification.md", errors)

        # Evidence/characterization instances are identified by first
        # non-comment H1 anywhere inside the feature directory (including
        # evidence/ subdirectories), never under docs/templates/.
        for md_path in sorted(entry.rglob("*.md")):
            md_rel = md_path.relative_to(root).as_posix()
            visible = list(_visible_lines(md_path.read_text(encoding="utf-8")))
            h1 = _first_h1(visible)
            if h1 is None:
                continue
            id_lineno, title = h1
            evidence_match = EVIDENCE_H1_RE.fullmatch(title)
            if evidence_match:
                validate_evidence_record(
                    md_path, md_rel, evidence_match.group(1).strip(), id_lineno,
                    br_ids, errors,
                )
                continue
            characterization_match = CHARACTERIZATION_H1_RE.fullmatch(title)
            if characterization_match:
                validate_characterization_record(
                    md_path, md_rel, characterization_match.group(1).strip(),
                    id_lineno, br_ids, errors,
                )
    return errors


def validate_oq_registry(root: Path) -> tuple[list[str], set[str]]:
    """Validate the global OQ registry table and resolved-OQ headings.

    Returns (errors, known_ids) so feature OQ references can resolve
    against the same registry view."""
    errors: list[str] = []
    path = root / OQ_REGISTRY_PATH
    if not path.is_file():
        return [f"{OQ_REGISTRY_PATH}: registry file missing"], set()
    lines = list(_visible_lines(path.read_text(encoding="utf-8")))
    ids: dict[str, int] = {}
    for _header_lineno, headers, rows in _parse_tables(lines):
        if "ID" not in headers or "Status" not in headers:
            continue
        for row_lineno, cells in rows:
            row_id = _cell(headers, cells, "ID") or ""
            status = _cell(headers, cells, "Status") or ""
            if not row_id and not status:
                continue
            if not OQ_ID_RE.fullmatch(row_id):
                errors.append(
                    _err(OQ_REGISTRY_PATH, row_lineno, "invalid-id",
                         f"`{row_id}`; expected OQ-###")
                )
            elif row_id in ids:
                errors.append(
                    _err(OQ_REGISTRY_PATH, row_lineno, "duplicate-id",
                         f"duplicate OQ ID `{row_id}` (first defined at line "
                         f"{ids[row_id]})")
                )
            else:
                ids[row_id] = row_lineno
            if status and status not in OQ_STATUSES:
                errors.append(
                    _err(OQ_REGISTRY_PATH, row_lineno, "invalid-enum",
                         f"Status `{status}`; expected "
                         + "|".join(OQ_STATUSES))
                )
    for lineno, line in lines:
        match = OQ_HEADING_RE.match(line)
        if not match:
            continue
        token = f"OQ-{match.group(1)}"
        if not OQ_ID_RE.fullmatch(token):
            errors.append(
                _err(OQ_REGISTRY_PATH, lineno, "invalid-id",
                     f"`{token}`; expected OQ-###")
            )
        elif token not in ids:
            errors.append(
                _err(OQ_REGISTRY_PATH, lineno, "missing-ref",
                     f"`{token}` heading has no row in the registry table")
            )
    return errors, set(ids)


# Durable-state validation (Issue #14): docs/11-durable-state-protocol.md.
# Validates the migration/STATE.md frontmatter, the migration/QUEUE.md
# frontmatter plus its single canonical live table, and the cross-file
# generation / dependency / blocker / derived-summary invariants that
# docs/issue-2-artifact-schema-validation.md explicitly deferred until a
# machine-readable queue contract existed.
#
# NOTE (Issue #13, not yet implemented): when STOP handling is implemented,
# its coordinator persistence must reuse this same schema/generation/
# invariant logic (or call this validator) instead of adding a second
# free-form STATE/QUEUE write path.
#
# GATE_CRITERIA below is a static registry of the canonical gate criteria
# owned by docs/02-migration-pipeline.md; a docs/02 gate change must update
# it in the same commit.

STATE_PATH = "migration/STATE.md"
QUEUE_PATH = "migration/QUEUE.md"
DURABLE_SCHEMA_VERSION = 1
PROJECT_STATUSES = ("ACTIVE", "BLOCKED", "PAUSED", "COMPLETE")
GATE_RESULTS = ("PENDING", "PASS", "BLOCKED", "NONE")
QUEUE_STATUSES = ("TODO", "IN_PROGRESS", "BLOCKED", "DONE")
QUEUE_COLUMNS = (
    "ID",
    "Status",
    "Phase",
    "Depends on",
    "Blocker",
    "Work item",
    "Completion artifact",
)
QUEUE_ID_RE = re.compile(r"^[QS]-\d{3}$")
RFC3339_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
GATE_CRITERION_RE = re.compile(r"^G\d+\.\d+$")
EXT_BLOCKER_RE = re.compile(r"^EXT:[a-z0-9]+(?:-[a-z0-9]+)*$")
HUMAN_BLOCKER_RE = re.compile(r"^HUMAN:[a-z0-9]+(?:-[a-z0-9]+)*$")

# Canonical gate -> criterion IDs (docs/02-migration-pipeline.md G0/G2/G3).
GATE_CRITERIA = {
    "G0": ("G0.1", "G0.2", "G0.3"),
    "G2": ("G2.1", "G2.2", "G2.3"),
    "G3": ("G3.1", "G3.2", "G3.3", "G3.4", "G3.5"),
}
KNOWN_CURRENT_GATES = tuple(GATE_CRITERIA) + ("NONE",)
ALL_CRITERIA = frozenset(
    criterion for criteria in GATE_CRITERIA.values() for criterion in criteria
)

STATE_REQUIRED_KEYS = (
    "schema_version",
    "generation",
    "phase",
    "phase_name",
    "status",
    "current_gate",
    "gate_result",
    "failed_gate_criteria",
    "active_queue_items",
    "next_queue_items",
    "blocked_queue_items",
    "last_updated",
)
QUEUE_REQUIRED_KEYS = ("schema_version", "generation", "status_values")


def _parse_durable_frontmatter(
    text: str, rel: str, errors: list[str]
) -> tuple[dict[str, tuple[int, str]], list[tuple[int, str]]]:
    """Parse the constrained flat frontmatter of STATE/QUEUE files.

    Values are scalars (optionally quoted) or one bracket list
    ``[A, B]``/``[]`` per docs/11's canonical examples; nested/indented YAML
    is rejected. Returns (fields mapping key -> (lineno, raw value), body
    lines); duplicates are reported, never merged.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        errors.append(
            _err(rel, 1, "missing-frontmatter",
                 "file must start with YAML frontmatter delimited by ---")
        )
        return {}, []
    closing = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            closing = index
            break
    if closing is None:
        errors.append(
            _err(rel, max(1, len(lines)), "missing-frontmatter",
                 "unterminated YAML frontmatter (missing closing ---)")
        )
        return {}, []
    fields: dict[str, tuple[int, str]] = {}
    for lineno, line in enumerate(lines[1:closing], start=2):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if line.startswith((" ", "\t")):
            errors.append(
                _err(rel, lineno, "invalid-frontmatter",
                     f"indented line is not part of the flat frontmatter "
                     f"contract: {stripped!r}")
            )
            continue
        if ":" not in line:
            errors.append(
                _err(rel, lineno, "invalid-frontmatter",
                     f"unparseable frontmatter line: {stripped!r}")
            )
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        if not key:
            errors.append(
                _err(rel, lineno, "invalid-frontmatter",
                     f"empty frontmatter key: {stripped!r}")
            )
            continue
        if key in fields:
            errors.append(
                _err(rel, lineno, "duplicate-key",
                     f"duplicate frontmatter key: {key}")
            )
            continue
        fields[key] = (lineno, value.strip())
    body = list(enumerate(lines[closing + 1:], start=closing + 2))
    return fields, body


def _fm_unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def _fm_str(fields: dict[str, tuple[int, str]], key: str) -> str | None:
    entry = fields.get(key)
    if entry is None:
        return None
    return _fm_unquote(entry[1])


def _fm_int(fields: dict[str, tuple[int, str]], key: str) -> int | None:
    entry = fields.get(key)
    if entry is None:
        return None
    try:
        return int(_fm_unquote(entry[1]), 10)
    except ValueError:
        return None


def _fm_list(
    fields: dict[str, tuple[int, str]], key: str, rel: str, errors: list[str]
) -> list[str] | None:
    entry = fields.get(key)
    if entry is None:
        return None
    raw = entry[1]
    if not (raw.startswith("[") and raw.endswith("]")):
        errors.append(
            _err(rel, entry[0], "invalid-type",
                 f"{key} must be a bracket list like [A, B] or [], got {raw!r}")
        )
        return None
    inner = raw[1:-1].strip()
    if not inner:
        return []
    return [item.strip() for item in inner.split(",")]


def _validate_durable_common(
    fields: dict[str, tuple[int, str]], required: tuple[str, ...],
    rel: str, errors: list[str],
) -> dict[str, int]:
    """schema_version/generation/required-key checks shared by both files.

    Returns the successfully parsed positive-integer fields."""
    parsed: dict[str, int] = {}
    for key in required:
        if key not in fields:
            errors.append(
                _err(rel, 1, "missing-key",
                     f"missing required frontmatter key: {key}")
            )
    for key in ("schema_version", "generation"):
        if key not in fields:
            continue
        value = _fm_int(fields, key)
        if value is None:
            errors.append(
                _err(rel, fields[key][0], "invalid-type",
                     f"{key} must be a positive integer, got "
                     f"{fields[key][1]!r}")
            )
        elif value < 1:
            category = "invalid-generation" if key == "generation" else "invalid-type"
            errors.append(
                _err(rel, fields[key][0], category,
                     f"{key} must be a positive integer, got {value}")
            )
        else:
            parsed[key] = value
    if parsed.get("schema_version") is not None and (
        parsed["schema_version"] != DURABLE_SCHEMA_VERSION
    ):
        errors.append(
            _err(rel, fields["schema_version"][0], "unsupported-schema-version",
                 f"schema_version {parsed['schema_version']} is not supported "
                 f"(expected {DURABLE_SCHEMA_VERSION})")
        )
    return parsed


def _validate_state_file(root: Path) -> tuple[list[str], dict | None]:
    errors: list[str] = []
    path = root / STATE_PATH
    if not path.is_file():
        return [f"{STATE_PATH}: durable-state file missing"], None
    fields, _body = _parse_durable_frontmatter(
        path.read_text(encoding="utf-8"), STATE_PATH, errors
    )
    if not fields:
        return errors, None
    parsed = _validate_durable_common(fields, STATE_REQUIRED_KEYS, STATE_PATH, errors)

    state: dict = {"_fields": fields}
    state.update(parsed)
    state["phase"] = _fm_str(fields, "phase")

    status = _fm_str(fields, "status")
    state["status"] = status
    if status is not None and status not in PROJECT_STATUSES:
        errors.append(
            _err(STATE_PATH, fields["status"][0], "invalid-enum",
                 f"status `{status}`; expected " + "|".join(PROJECT_STATUSES))
        )

    gate = _fm_str(fields, "current_gate")
    state["current_gate"] = gate
    if gate is not None and gate not in KNOWN_CURRENT_GATES:
        errors.append(
            _err(STATE_PATH, fields["current_gate"][0], "invalid-enum",
                 f"current_gate `{gate}`; expected " + "|".join(KNOWN_CURRENT_GATES)
                 + " (canonical gates from docs/02-migration-pipeline.md)")
        )

    result = _fm_str(fields, "gate_result")
    state["gate_result"] = result
    if result is not None and result not in GATE_RESULTS:
        errors.append(
            _err(STATE_PATH, fields["gate_result"][0], "invalid-enum",
                 f"gate_result `{result}`; expected " + "|".join(GATE_RESULTS))
        )

    if gate is not None and result is not None and (gate == "NONE") != (
        result == "NONE"
    ):
        errors.append(
            _err(STATE_PATH, fields["current_gate"][0], "invalid-relationship",
                 "current_gate: NONE exactly when gate_result: NONE (no gate "
                 "applies)")
        )

    criteria = _fm_list(fields, "failed_gate_criteria", STATE_PATH, errors)
    if criteria is not None:
        state["failed_gate_criteria"] = criteria
        if result == "BLOCKED" and not criteria:
            errors.append(
                _err(STATE_PATH, fields["gate_result"][0],
                     "invalid-relationship",
                     "gate_result BLOCKED requires a non-empty "
                     "failed_gate_criteria list")
            )
        elif result in ("PENDING", "PASS", "NONE") and criteria:
            errors.append(
                _err(STATE_PATH, fields["failed_gate_criteria"][0],
                     "invalid-relationship",
                     f"gate_result {result} requires failed_gate_criteria to "
                     f"be empty, got {criteria}")
            )
        if gate in GATE_CRITERIA:
            for item in criteria:
                if item not in GATE_CRITERIA[gate]:
                    errors.append(
                        _err(STATE_PATH, fields["failed_gate_criteria"][0],
                             "invalid-ref",
                             f"criterion `{item}` does not belong to gate "
                             f"{gate} (criteria: "
                             + ", ".join(GATE_CRITERIA[gate]) + ")")
                    )

    last_updated = _fm_str(fields, "last_updated")
    if last_updated is not None and not RFC3339_UTC_RE.fullmatch(last_updated):
        errors.append(
            _err(STATE_PATH, fields["last_updated"][0], "invalid-timestamp",
                 f"last_updated `{last_updated}`; expected UTC RFC 3339 like "
                 "2026-08-19T15:20:46Z")
        )

    for key in ("active_queue_items", "next_queue_items", "blocked_queue_items"):
        items = _fm_list(fields, key, STATE_PATH, errors)
        if items is None:
            continue
        state[key] = items
        seen: set[str] = set()
        for item in items:
            if not QUEUE_ID_RE.fullmatch(item):
                errors.append(
                    _err(STATE_PATH, fields[key][0], "invalid-id",
                         f"`{item}` in {key}; expected Q-### or S-###")
                )
            elif item in seen:
                errors.append(
                    _err(STATE_PATH, fields[key][0], "duplicate-id",
                         f"duplicate `{item}` in {key}")
                )
            else:
                seen.add(item)
    return errors, state


def _parse_queue_deps(raw: str) -> tuple[list[str] | None, str | None]:
    """Returns (tokens, bad_token); tokens is None when raw is malformed."""
    if raw == "-":
        return [], None
    tokens = [token.strip() for token in raw.split(",")]
    for token in tokens:
        if not QUEUE_ID_RE.fullmatch(token):
            return None, token
    return tokens, None


def _parse_queue_blockers(raw: str) -> tuple[list[str] | None, str | None]:
    """Returns (tokens, bad_token); OQ-### syntax, canonical gate criterion,
    EXT:<kebab-token>, or HUMAN:<kebab-token> per docs/11's Blocker grammar."""
    if raw == "-":
        return [], None
    tokens = [token.strip() for token in raw.split(";")]
    for token in tokens:
        if OQ_ID_RE.fullmatch(token):
            continue
        if GATE_CRITERION_RE.fullmatch(token):
            if token not in ALL_CRITERIA:
                return None, token
            continue
        if EXT_BLOCKER_RE.fullmatch(token) or HUMAN_BLOCKER_RE.fullmatch(token):
            continue
        return None, token
    return tokens, None


def _validate_queue_file(root: Path) -> tuple[list[str], dict | None]:
    errors: list[str] = []
    path = root / QUEUE_PATH
    if not path.is_file():
        return [f"{QUEUE_PATH}: durable-state file missing"], None
    fields, body = _parse_durable_frontmatter(
        path.read_text(encoding="utf-8"), QUEUE_PATH, errors
    )
    if not fields:
        return errors, None
    parsed = _validate_durable_common(fields, QUEUE_REQUIRED_KEYS, QUEUE_PATH, errors)

    status_values = _fm_list(fields, "status_values", QUEUE_PATH, errors)
    if status_values is not None and tuple(status_values) != QUEUE_STATUSES:
        errors.append(
            _err(QUEUE_PATH, fields["status_values"][0], "invalid-enum",
                 "status_values must be exactly ["
                 + ", ".join(QUEUE_STATUSES) + "], got [" + ", ".join(status_values) + "]")
        )

    visible = list(_visible_numbered(body))
    tables = list(_parse_tables(visible))
    live = [
        (header_lineno, headers, rows)
        for header_lineno, headers, rows in tables
        if headers[:2] == ["ID", "Status"]
    ]
    if not live:
        errors.append(
            _err(QUEUE_PATH, visible[0][0] if visible else 1, "missing-table",
                 "no canonical live queue table (header must start with "
                 "ID | Status)")
        )
    for header_lineno, headers, _rows in live:
        if tuple(headers) != QUEUE_COLUMNS:
            errors.append(
                _err(QUEUE_PATH, header_lineno, "invalid-header",
                     "live queue table columns must be exactly "
                     + " | ".join(QUEUE_COLUMNS) + ", got " + " | ".join(headers))
            )
    for header_lineno, _headers, _rows in live[1:]:
        errors.append(
            _err(QUEUE_PATH, header_lineno, "duplicate-table",
                 "more than one live queue table; QUEUE.md must contain "
                 "exactly one")
        )

    queue: dict = {"_fields": fields}
    queue.update(parsed)
    rows: dict[str, dict] = {}
    queue["rows"] = rows
    if live and tuple(live[0][1]) == QUEUE_COLUMNS:
        for row_lineno, cells in live[0][2]:
            if not any(cells):
                continue
            if len(cells) != len(QUEUE_COLUMNS):
                errors.append(
                    _err(QUEUE_PATH, row_lineno, "invalid-row",
                         f"expected {len(QUEUE_COLUMNS)} columns, got "
                         f"{len(cells)}")
                )
                continue
            row_id, status, phase, deps_raw, blocker_raw, _work, artifact = cells
            if not QUEUE_ID_RE.fullmatch(row_id):
                errors.append(
                    _err(QUEUE_PATH, row_lineno, "invalid-id",
                         f"`{row_id}`; expected Q-### or S-###")
                )
            elif row_id in rows:
                errors.append(
                    _err(QUEUE_PATH, row_lineno, "duplicate-id",
                         f"duplicate queue ID `{row_id}` (first defined at "
                         f"line {rows[row_id]['lineno']})")
                )
            if status not in QUEUE_STATUSES:
                errors.append(
                    _err(QUEUE_PATH, row_lineno, "invalid-enum",
                         f"Status `{status}`; expected " + "|".join(QUEUE_STATUSES))
                )
            deps, bad_dep = _parse_queue_deps(deps_raw)
            if bad_dep is not None:
                errors.append(
                    _err(QUEUE_PATH, row_lineno, "invalid-id",
                         f"Depends on token `{bad_dep}`; expected Q-### or S-###")
                )
            blockers, bad_blocker = _parse_queue_blockers(blocker_raw)
            if bad_blocker is not None:
                errors.append(
                    _err(QUEUE_PATH, row_lineno, "invalid-ref",
                         f"Blocker `{bad_blocker}`; expected OQ-###, canonical "
                         "gate criterion (e.g. G0.1), EXT:<kebab-token>, or "
                         "HUMAN:<kebab-token>")
                )
            if QUEUE_ID_RE.fullmatch(row_id) and row_id not in rows:
                rows[row_id] = {
                    "lineno": row_lineno,
                    "status": status,
                    "phase": phase,
                    "deps": deps if deps is not None else [],
                    "blockers": blockers if blockers is not None else [],
                    "artifact": artifact,
                }
    return errors, queue


PHASE_RANGE_RE = re.compile(r"^(\d+)-(\d+)$")


def _phase_matches(row_phase: str, current_phase: str) -> bool:
    """A queue row's `Phase` may be a single stable phase identifier (exact
    match) or a hyphenated numeric range for a row spanning multiple phases
    (e.g. `5-6` for a combined review+verification row); it is
    current-phase-relevant when `current_phase` falls inside that range."""
    if row_phase == current_phase:
        return True
    match = PHASE_RANGE_RE.fullmatch(row_phase)
    if not match or not current_phase.isdigit():
        return False
    low, high = int(match.group(1)), int(match.group(2))
    return low <= int(current_phase) <= high


def _depends_on_cycle(start: str, rows: dict[str, dict]) -> bool:
    stack = list(rows[start]["deps"])
    seen: set[str] = set()
    while stack:
        node = stack.pop()
        if node == start:
            return True
        if node in seen or node not in rows:
            continue
        seen.add(node)
        stack.extend(rows[node]["deps"])
    return False


def validate_durable_state(
    root: Path | None = None, oq_ids: set[str] | None = None
) -> list[str]:
    """Issue #14 durable-state validation for STATE.md + QUEUE.md.

    Covers frontmatter schema, enums, gate/result/criterion relationships,
    the single canonical live queue table, dependency/blocker reference
    grammar and invariants, STATE/QUEUE generation equality, STATE summary
    lists versus current-phase queue rows, project status versus queue
    actionability, and DONE completion-artifact existence (best effort, only
    for cells that are unambiguously a single repo path).

    `oq_ids` is the known-good OQ registry (from `validate_oq_registry`); a
    `Blocker: OQ-###` reference that isn't a real registry entry is a
    dangling reference, same as an unresolved `Depends on` queue ID. When
    the caller can't supply it (e.g. isolated tests), OQ blocker resolution
    is skipped rather than treated as an automatic failure.
    """
    base = ROOT if root is None else root
    state_errors, state = _validate_state_file(base)
    queue_errors, queue = _validate_queue_file(base)
    errors = state_errors + queue_errors
    if state is None or queue is None:
        return errors

    state_fields = state["_fields"]
    queue_fields = queue["_fields"]
    state_generation = state.get("generation")
    queue_generation = queue.get("generation")
    if state_generation is not None and queue_generation is not None and (
        state_generation != queue_generation
    ):
        errors.append(
            _err(QUEUE_PATH, queue_fields["generation"][0], "invalid-generation",
                 f"QUEUE generation {queue_generation} != STATE generation "
                 f"{state_generation}; every durable transaction must update "
                 "both files to the same new generation")
        )

    rows = queue["rows"]
    for row_id, row in rows.items():
        for dep in row["deps"]:
            if dep not in rows:
                errors.append(
                    _err(QUEUE_PATH, row["lineno"], "missing-ref",
                         f"`{row_id}` depends on `{dep}` which is not a live "
                         "queue row")
                )
        if oq_ids is not None:
            for blocker in row["blockers"]:
                if OQ_ID_RE.fullmatch(blocker) and blocker not in oq_ids:
                    errors.append(
                        _err(QUEUE_PATH, row["lineno"], "missing-ref",
                             f"`{row_id}` Blocker `{blocker}` does not "
                             f"resolve in {OQ_REGISTRY_PATH}")
                    )
    for row_id in rows:
        if _depends_on_cycle(row_id, rows):
            errors.append(
                _err(QUEUE_PATH, rows[row_id]["lineno"], "cyclic-dependency",
                     f"`{row_id}` depends (transitively) on itself")
            )

    for row_id, row in rows.items():
        status = row["status"]
        if status not in QUEUE_STATUSES:
            continue
        deps_done = all(
            dep in rows and rows[dep]["status"] == "DONE" for dep in row["deps"]
        )
        unmet_dep = any(
            dep not in rows or rows[dep]["status"] != "DONE" for dep in row["deps"]
        )
        has_blocker = bool(row["blockers"])
        if status == "TODO" and not (deps_done and not has_blocker):
            errors.append(
                _err(QUEUE_PATH, row["lineno"], "invalid-invariant",
                     f"`{row_id}` is TODO but not actionable; TODO requires "
                     "every dependency DONE and Blocker `-`")
            )
        elif status == "IN_PROGRESS" and (has_blocker or not deps_done):
            errors.append(
                _err(QUEUE_PATH, row["lineno"], "invalid-invariant",
                     f"`{row_id}` is IN_PROGRESS with violated preconditions; "
                     "IN_PROGRESS requires dependencies DONE and Blocker `-`")
            )
        elif status == "BLOCKED" and not (unmet_dep or has_blocker):
            errors.append(
                _err(QUEUE_PATH, row["lineno"], "invalid-invariant",
                     f"`{row_id}` is BLOCKED without an unfinished dependency "
                     "or blocker reference")
            )
        elif status == "DONE":
            if has_blocker or not deps_done:
                errors.append(
                    _err(QUEUE_PATH, row["lineno"], "invalid-invariant",
                         f"`{row_id}` is DONE with an unmet dependency or "
                         "active Blocker; DONE is terminal and requires "
                         "every dependency DONE and Blocker `-` (the normal "
                         "IN_PROGRESS -> DONE transition already requires "
                         "this)")
                )
            artifact = row["artifact"].strip()
            if (
                "/" in artifact
                and re.fullmatch(r"[^\s{},;()]+", artifact)
                and not (base / artifact).exists()
            ):
                errors.append(
                    _err(QUEUE_PATH, row["lineno"], "missing-artifact",
                         f"DONE row `{row_id}` declares completion artifact "
                         f"`{artifact}` which does not exist in the repository")
                )

    phase = state.get("phase")
    if phase is not None:
        relevant = {
            row_id: row
            for row_id, row in rows.items()
            if _phase_matches(row["phase"], phase) and row["status"] in QUEUE_STATUSES
        }
        expected: dict[str, set[str]] = {
            "active_queue_items": {
                row_id for row_id, row in relevant.items()
                if row["status"] == "IN_PROGRESS"
            },
            "next_queue_items": {
                row_id for row_id, row in relevant.items()
                if row["status"] == "TODO"
            },
            "blocked_queue_items": {
                row_id for row_id, row in relevant.items()
                if row["status"] == "BLOCKED"
            },
        }
        for key, want in expected.items():
            got = state.get(key)
            if got is None:
                continue
            got_set = set(got)
            for item in sorted(got_set - set(rows)):
                errors.append(
                    _err(STATE_PATH, state_fields[key][0], "missing-ref",
                         f"`{item}` in {key} is not a live queue row")
                )
            if {item for item in got_set if item in rows} != want:
                errors.append(
                    _err(STATE_PATH, state_fields[key][0], "invalid-invariant",
                         f"{key} {sorted(got_set)} does not match the "
                         f"current-phase (phase {phase}) rows with that "
                         f"status: {sorted(want)}")
                )

        status = state.get("status")
        if status in PROJECT_STATUSES and status not in ("PAUSED", "COMPLETE"):
            actionable = any(
                row["status"] in ("IN_PROGRESS", "TODO")
                for row in relevant.values()
            )
            any_blocked = any(
                row["status"] == "BLOCKED" for row in relevant.values()
            )
            if actionable and status != "ACTIVE":
                errors.append(
                    _err(STATE_PATH, state_fields["status"][0],
                         "invalid-invariant",
                         f"status {status} but current-phase queue rows "
                         "include actionable TODO/IN_PROGRESS work (expected "
                         "ACTIVE)")
                )
            elif not actionable and any_blocked and status != "BLOCKED":
                errors.append(
                    _err(STATE_PATH, state_fields["status"][0],
                         "invalid-invariant",
                         f"status {status} but no current-phase queue row is "
                         "actionable and at least one is BLOCKED (expected "
                         "BLOCKED)")
                )
            elif not actionable and not any_blocked:
                errors.append(
                    _err(STATE_PATH, state_fields["status"][0],
                         "invalid-invariant",
                         f"status {status} but no current-phase queue row is "
                         "actionable, in progress, or BLOCKED (neither ACTIVE "
                         "nor BLOCKED is justified; expected PAUSED or "
                         "COMPLETE)")
                )
        if status == "COMPLETE":
            gate = state.get("current_gate")
            result = state.get("gate_result")
            criteria = state.get("failed_gate_criteria")
            if gate is not None and gate != "NONE":
                errors.append(
                    _err(STATE_PATH, state_fields["status"][0],
                         "invalid-invariant",
                         f"status COMPLETE requires current_gate: NONE "
                         f"(no further gate applies); got `{gate}`")
                )
            if result is not None and result != "NONE":
                errors.append(
                    _err(STATE_PATH, state_fields["status"][0],
                         "invalid-invariant",
                         f"status COMPLETE requires gate_result: NONE; got "
                         f"`{result}`")
                )
            if criteria is not None and criteria:
                errors.append(
                    _err(STATE_PATH, state_fields["status"][0],
                         "invalid-invariant",
                         "status COMPLETE requires an empty "
                         f"failed_gate_criteria; got {sorted(criteria)}")
                )
            unfinished = sorted(
                row_id for row_id, row in rows.items()
                if row["status"] in ("TODO", "IN_PROGRESS", "BLOCKED")
            )
            if unfinished:
                errors.append(
                    _err(STATE_PATH, state_fields["status"][0],
                         "invalid-invariant",
                         "status COMPLETE requires every queue row DONE; "
                         f"not DONE: {unfinished}")
                )
    return errors


def collect_validation_errors(root: Path | None = None) -> list[str]:
    """Run A-1, A-2, and durable-state validation together (no fail-fast)."""
    base = ROOT if root is None else root
    oq_errors, oq_ids = validate_oq_registry(base)
    return (
        validate_features(base)
        + oq_errors
        + validate_feature_schemas(base, oq_ids)
        + validate_durable_state(base, oq_ids)
    )


def main() -> None:
    validate_required()
    validate_json()
    validate_skills()
    validate_agents_and_commands()
    errors = collect_validation_errors()
    if errors:
        raise SystemExit(
            "ERROR: repository validation failed "
            f"({len(errors)} issue(s)):\n"
            + "\n".join(f"- {error}" for error in errors)
        )
    print("Scaffold validation passed.")


if __name__ == "__main__":
    main()
