from __future__ import annotations

import json
import re
from pathlib import Path

try:
    from scripts.sync_agent_stop_conditions import (
        validate_agent_stop_conditions as _validate_agent_stop_conditions,
    )
except ModuleNotFoundError:  # direct ``python3 scripts/validate_scaffold.py``
    from sync_agent_stop_conditions import (
        validate_agent_stop_conditions as _validate_agent_stop_conditions,
    )

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


# Issue #7 agent routing contract: docs/09-agent-skill-routing.md.
# Lightweight structural enforcement so a future agent definition cannot
# silently omit its deterministic routing sections: every
# .opencode/agents/*.md must carry a frontmatter description, the three
# routing sections (positive triggers, negative triggers, primary output
# ownership), and the standard `## Escalation` section delegating its payload
# to the common STOP contract. Permission-frontmatter shape is intentionally
# NOT validated here (role-boundary permission work is owned separately, e.g.
# Issue #8).

AGENTS_DIR = ".opencode/agents"

AGENT_ROUTING_SECTIONS = (
    "Invoke when",
    "Do not invoke for",
    "Primary output ownership",
)

ESCALATION_HEADING = "Escalation"
ESCALATION_STOP_PAYLOAD_MARKER = "common 12-field STOP payload"

# docs/09's "Frontmatter description contract": a discoverable description
# states the positive trigger, primary output ownership, and nearest
# confusing exclusion. Checking only "non-empty" lets a description regress
# to something ambiguous (e.g. "migration helper") without failing
# validation, silently reopening the exact ambiguity Issue #7 closed — so
# require the three markers every current agent description actually uses.
DESCRIPTION_TRIGGER_RE = re.compile(r"^invoke when\b", re.IGNORECASE)
DESCRIPTION_OWNERSHIP_MARKER = "owns"
DESCRIPTION_EXCLUSION_MARKER = "do not use for"

# docs/09's "Skill routing contract": the four overlapping skills are
# separated by primary artifact, with a tie-break algorithm for composing
# them. Only these four canonical skills carry the boundary/tie-break
# sections; other skills are out of scope for Issue #7.
ROUTING_CONTRACT_SKILLS = (
    "behavior-contract",
    "evidence-grading",
    "uncertainty-management",
    "parity-verification",
)
SKILL_ROUTING_SECTIONS = (
    "Primary artifact boundary",
    "Skill tie-break",
)

H2_RE = re.compile(r"^##\s+(.+?)\s*$")


def _h2_sections(text: str) -> dict[str, str]:
    """Map lowercased H2 titles to their raw body text (no fenced-code
    awareness needed: agent definitions keep headings outside fences)."""
    sections: dict[str, str] = {}
    title: str | None = None
    body: list[str] = []
    for line in text.splitlines():
        match = H2_RE.match(line)
        if match:
            if title is not None:
                sections[title] = "\n".join(body)
            title = match.group(1).lower()
            body = []
        elif title is not None:
            body.append(line)
    if title is not None:
        sections[title] = "\n".join(body)
    return sections


def _agent_description(text: str) -> str:
    """Extract the top-level frontmatter `description:` line's value
    without a YAML parser (frontmatter may contain nested blocks)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line.startswith("description:"):
            return line.split(":", 1)[1].strip()
    return ""


def validate_agent_routing(root: Path | None = None) -> list[str]:
    """Issue #7 structural routing checks for every .opencode/agents/*.md."""
    base = ROOT if root is None else root
    agents_dir = base / AGENTS_DIR
    if not agents_dir.is_dir():
        return [f"{AGENTS_DIR}: agent definition directory missing"]
    paths = sorted(agents_dir.glob("*.md"))
    if not paths:
        return [f"{AGENTS_DIR}: no agent definitions found"]
    errors: list[str] = []
    for path in paths:
        rel = path.relative_to(base).as_posix()
        text = path.read_text(encoding="utf-8")
        description = _agent_description(text)
        if not description:
            errors.append(
                f"{rel}: missing frontmatter description "
                "(docs/09 frontmatter description contract)"
            )
        else:
            missing_markers = []
            if not DESCRIPTION_TRIGGER_RE.search(description):
                missing_markers.append("positive trigger ('Invoke when ...')")
            if DESCRIPTION_OWNERSHIP_MARKER not in description.lower():
                missing_markers.append("primary output ownership ('owns ...')")
            if DESCRIPTION_EXCLUSION_MARKER not in description.lower():
                missing_markers.append("nearest exclusion ('do not use for ...')")
            if missing_markers:
                errors.append(
                    f"{rel}: frontmatter description missing "
                    f"{', '.join(missing_markers)} "
                    "(docs/09 frontmatter description contract)"
                )
        sections = _h2_sections(text)
        for title in AGENT_ROUTING_SECTIONS:
            body = sections.get(title.lower())
            if body is None:
                errors.append(
                    f"{rel}: missing required routing section "
                    f"'## {title}' (docs/09-agent-skill-routing.md)"
                )
            elif not body.strip():
                errors.append(f"{rel}: routing section '## {title}' is empty")
        escalation = sections.get(ESCALATION_HEADING.lower())
        if escalation is None:
            errors.append(
                f"{rel}: missing required routing section "
                f"'## {ESCALATION_HEADING}' (docs/09 escalation contract)"
            )
        elif ESCALATION_STOP_PAYLOAD_MARKER not in escalation:
            errors.append(
                f"{rel}: '## {ESCALATION_HEADING}' must delegate to the "
                "common STOP payload (docs/11-stop-condition-contract.md)"
            )
    return errors


def validate_skill_routing_contract(root: Path | None = None) -> list[str]:
    """Issue #7 structural checks for the four overlapping skills' primary-
    artifact boundary / tie-break sections (docs/09 "Skill routing
    contract"). Only ``ROUTING_CONTRACT_SKILLS`` are in scope; other skills
    are unaffected."""
    base = ROOT if root is None else root
    skills_dir = base / ".opencode" / "skills"
    errors: list[str] = []
    for name in ROUTING_CONTRACT_SKILLS:
        skill_file = skills_dir / name / "SKILL.md"
        rel = f".opencode/skills/{name}/SKILL.md"
        if not skill_file.is_file():
            errors.append(f"{rel}: canonical routing-contract skill file missing")
            continue
        sections = _h2_sections(skill_file.read_text(encoding="utf-8"))
        for title in SKILL_ROUTING_SECTIONS:
            body = sections.get(title.lower())
            if body is None:
                errors.append(
                    f"{rel}: missing required section '## {title}' "
                    "(docs/09-agent-skill-routing.md skill routing contract)"
                )
            elif not body.strip():
                errors.append(f"{rel}: section '## {title}' is empty")
    return errors


# Issue #6 skill execution contract: docs/10-skill-execution-contract.md.
# The execution contract applies to the nine skills in the design matrix. It
# checks deterministic structure and path vocabulary only; branch meaning is
# intentionally left to review work.
SKILL_EXECUTION_CONTRACT_SKILLS = (
    "behavior-contract",
    "db-migration-analysis",
    "dll-boundary-analysis",
    "evidence-grading",
    "feature-migration",
    "legacy-discovery",
    "parity-verification",
    "target-feature-design",
    "uncertainty-management",
)
SKILL_EXECUTION_CONTRACT_SECTIONS = (
    "Inputs",
    "Outputs",
    "Procedure",
    "Branches",
    "Done means",
)
SKILL_EXECUTION_SUPPORTING_ARTIFACTS = frozenset(
    {
        "db-dependency-report.md",
        "dll-boundary-report.md",
        "evidence",
    }
)


def validate_skill_execution_contract(root: Path | None = None) -> list[str]:
    """Issue #6 structural checks for every migration skill.

    The check deliberately stays deterministic: it validates the required
    section shape, durable procedure markers, canonical feature-path
    vocabulary, and the common BLOCKED/PARTIAL branch vocabulary. Semantic
    correctness of each branch remains review work under docs/10.
    """
    base = ROOT if root is None else root
    skills_dir = base / ".opencode" / "skills"
    errors: list[str] = []
    allowed_artifacts = set(CANONICAL_SINGLETON_FILES)
    allowed_artifacts.update(SKILL_EXECUTION_SUPPORTING_ARTIFACTS)

    for name in SKILL_EXECUTION_CONTRACT_SKILLS:
        skill_file = skills_dir / name / "SKILL.md"
        rel = f".opencode/skills/{name}/SKILL.md"
        if not skill_file.is_file():
            errors.append(
                f"{rel}: skill execution contract file missing "
                "(docs/10-skill-execution-contract.md)"
            )
            continue

        text = skill_file.read_text(encoding="utf-8")
        sections = _h2_sections(text)
        heading_positions: dict[str, int] = {}
        for index, line in enumerate(text.splitlines()):
            match = H2_RE.match(line)
            if match:
                heading_positions[match.group(1).lower()] = index

        for title in SKILL_EXECUTION_CONTRACT_SECTIONS:
            body = sections.get(title.lower())
            if body is None:
                errors.append(
                    f"{rel}: missing required execution section '## {title}' "
                    "(docs/10-skill-execution-contract.md)"
                )
            elif not body.strip():
                errors.append(
                    f"{rel}: execution section '## {title}' is empty "
                    "(docs/10-skill-execution-contract.md)"
                )

        required_positions = [
            heading_positions[title.lower()]
            for title in SKILL_EXECUTION_CONTRACT_SECTIONS
            if title.lower() in heading_positions
        ]
        if (
            len(required_positions) == len(SKILL_EXECUTION_CONTRACT_SECTIONS)
            and required_positions != sorted(required_positions)
        ):
            errors.append(
                f"{rel}: execution sections must appear in this order: "
                "Inputs, Outputs, Procedure, Branches, Done means "
                "(docs/10-skill-execution-contract.md)"
            )

        procedure = sections.get("procedure")
        if procedure is not None and procedure.strip():
            for marker in ("[Input]", "[Output]"):
                if marker not in procedure:
                    errors.append(
                        f"{rel}: '## Procedure' must contain at least one "
                        f"{marker} marker "
                        "(docs/10-skill-execution-contract.md)"
                    )

        branches = sections.get("branches")
        if branches is not None and branches.strip():
            if not re.search(r"\b(?:BLOCKED|PARTIAL)\b", branches):
                errors.append(
                    f"{rel}: '## Branches' must mention BLOCKED or PARTIAL "
                    "(docs/10-skill-execution-contract.md)"
                )

        for alias, canonical in LEGACY_SINGLETON_ALIASES.items():
            alias_re = re.compile(
                rf"(?<![A-Za-z0-9_-]){re.escape(alias)}(?![A-Za-z0-9_.-])"
            )
            if alias_re.search(text):
                errors.append(
                    f"{rel}: non-canonical feature artifact reference "
                    f"'{alias}'; use '{canonical}' "
                    "(docs/08-feature-artifact-validation.md)"
                )

        feature_paths = list(_FEATURE_PATH_RE.finditer(text))
        if not feature_paths:
            errors.append(
                f"{rel}: must reference at least one canonical feature artifact "
                "path using 'migration/features/<feature-id>/' "
                "(docs/10-skill-execution-contract.md)"
            )
        for match in feature_paths:
            placeholder = match.group("placeholder")
            artifact = match.group("artifact")
            if placeholder != "feature-id":
                errors.append(
                    f"{rel}: feature artifact path uses '<{placeholder}>'; "
                    "expected '<feature-id>' "
                    "(docs/08-feature-artifact-validation.md)"
                )
            if (
                artifact not in allowed_artifacts
                and artifact not in LEGACY_SINGLETON_ALIASES
            ):
                errors.append(
                    f"{rel}: feature artifact reference '{artifact}' is not "
                    "canonical "
                    "(docs/08-feature-artifact-validation.md)"
                )

    return errors


# Issue #13 generated STOP-condition contract: docs/11-stop-condition-contract.md.
# The parser/sync helper owns marked-registry extraction and agent enumeration;
# this isolated wrapper makes the contract part of scaffold validation without
# changing the existing routing or durable-state checks.
def validate_stop_condition_contract(root: Path | None = None) -> list[str]:
    return _validate_agent_stop_conditions(ROOT if root is None else root)


# Issue #5 command execution contract: docs/10-command-execution-contract.md.
# This check is intentionally limited to the seven command entrypoints and
# their structural contract/path references. Command semantics remain owned by
# the command documents and their canonical designs.

COMMAND_CONTRACT_DIR = ".opencode/commands"
COMMAND_CONTRACT_FILES = (
    "migration-discover.md",
    "migration-spec.md",
    "migration-design.md",
    "migration-implement.md",
    "migration-review.md",
    "migration-verify.md",
    "migration-status.md",
)
COMMAND_CONTRACT_SECTIONS = (
    "Arguments",
    "Inputs",
    "Preconditions",
    "Outputs",
    "State updates",
    "Failure behavior",
)

_FEATURE_PATH_RE = re.compile(
    r"migration/features/<(?P<placeholder>[^>]+)>/"
    r"(?P<artifact>[A-Za-z0-9][A-Za-z0-9.-]*)"
)

_FENCED_CODE_BLOCK_RE = re.compile(r"```[^\n]*\n(?P<body>.*?)\n```", re.DOTALL)
_ARGUMENT_FLAG_RE = re.compile(r"(?<![A-Za-z0-9_])--[A-Za-z0-9][A-Za-z0-9-]*")
_FEATURE_SCOPED_COMMANDS = frozenset(
    {
        "migration-spec.md",
        "migration-design.md",
        "migration-implement.md",
        "migration-review.md",
        "migration-verify.md",
    }
)
_STATE_PATH_MARKERS = (
    "state.md",
    "queue.md",
    "feature-card",
    "open-questions",
    "oq registry",
)
_STATE_MUTATION_VERB_RE = re.compile(
    r"\b(?:change|changes|changed|create|creates|delete|deletes|"
    r"modify|modifies|mutate|mutates|mutation|persist|persists|"
    r"repair|repairs|set|sets|transition|transitions|update|updates|"
    r"write|writes|written)\b",
    re.IGNORECASE,
)
_READ_ONLY_STATE_RE = re.compile(
    r"(?:^none\b|\bnever\s+mutat\w*\b|\bread[- ]only\b|"
    r"\bno\s+(?:durable\s+)?mutation\b)",
    re.IGNORECASE,
)


def _fenced_code_blocks(section: str) -> list[str]:
    return [match.group("body") for match in _FENCED_CODE_BLOCK_RE.finditer(section)]


def _contains_unbracketed_argument(grammar: str, token: str) -> bool:
    """Return whether ``token`` appears as a required, unbracketed argument."""

    for match in re.finditer(re.escape(token), grammar):
        line_start = grammar.rfind("\n", 0, match.start()) + 1
        line_end = grammar.find("\n", match.end())
        if line_end == -1:
            line_end = len(grammar)
        line = grammar[line_start:line_end]
        offset = match.start() - line_start
        before = line[:offset]
        after = line[offset + len(token) :]
        if re.search(r"\[\s*$", before) or re.match(r"^\s*\]", after):
            continue
        return True
    return False


def _has_positive_state_mutation(body: str) -> bool:
    """Detect a positive mutation statement involving known durable state."""

    for clause in re.split(r"[\n.!?;]+", body.lower()):
        if not any(marker in clause for marker in _STATE_PATH_MARKERS):
            continue
        for match in _STATE_MUTATION_VERB_RE.finditer(clause):
            prefix = clause[: match.start()]
            if re.search(
                r"(?:\bnever|\bno|\bnot|\bwithout|\bdoesn't|\bdoes\s+not)\s*$",
                prefix,
            ):
                continue
            return True
    return False


def _validate_command_argument_grammar(
    filename: str,
    rel: str,
    sections: dict[str, str],
) -> list[str]:
    errors: list[str] = []
    arguments = sections.get("arguments")
    if arguments is None:
        return errors
    code_blocks = _fenced_code_blocks(arguments)
    if not code_blocks:
        return [
            f"{rel}: '## Arguments' must contain a fenced argument grammar "
            "(docs/10-command-execution-contract.md)"
        ]
    grammar = "\n".join(code_blocks)

    if filename == "migration-status.md":
        if _ARGUMENT_FLAG_RE.search(grammar):
            errors.append(
                f"{rel}: migration-status must accept no arguments; its "
                "fenced Arguments grammar contains a flag token"
            )
        state_updates = sections.get("state updates")
        if state_updates is None:
            return errors
        if not _READ_ONLY_STATE_RE.search(" ".join(state_updates.split())):
            errors.append(
                f"{rel}: '## State updates' must affirmatively state that "
                "migration-status never mutates durable state"
            )
        if _has_positive_state_mutation(state_updates):
            errors.append(
                f"{rel}: '## State updates' must not describe writing "
                "STATE.md, QUEUE.md, feature artifacts, or the OQ registry"
            )
        return errors

    if not _contains_unbracketed_argument(grammar, "--queue <queue-id>"):
        errors.append(
            f"{rel}: '## Arguments' must require '--queue <queue-id>'"
        )
    if filename in _FEATURE_SCOPED_COMMANDS and not _contains_unbracketed_argument(
        grammar, "--feature <feature-id>"
    ):
        errors.append(
            f"{rel}: '## Arguments' must require '--feature <feature-id>'"
        )
    return errors


def validate_command_contract(root: Path | None = None) -> list[str]:
    """Issue #5 structural checks for all seven command documents.

    Every command must expose the six shared contract sections. Any feature
    artifact path it references must use the ``<feature-id>`` placeholder and
    the canonical singleton names from docs/08; legacy singleton aliases are
    rejected in both feature and template paths.
    """
    base = ROOT if root is None else root
    commands_dir = base / COMMAND_CONTRACT_DIR
    errors: list[str] = []
    for filename in COMMAND_CONTRACT_FILES:
        path = commands_dir / filename
        rel = f"{COMMAND_CONTRACT_DIR}/{filename}"
        if not path.is_file():
            errors.append(f"{rel}: command contract file missing")
            continue

        text = path.read_text(encoding="utf-8")
        sections = _h2_sections(text)
        for title in COMMAND_CONTRACT_SECTIONS:
            body = sections.get(title.lower())
            if body is None:
                errors.append(
                    f"{rel}: missing required command contract section "
                    f"'## {title}' (docs/10-command-execution-contract.md)"
                )
            elif not body.strip():
                errors.append(f"{rel}: command contract section '## {title}' is empty")

        for alias, canonical in LEGACY_SINGLETON_ALIASES.items():
            alias_re = re.compile(
                rf"(?<![A-Za-z0-9_-]){re.escape(alias)}(?![A-Za-z0-9_.-])"
            )
            if alias_re.search(text):
                errors.append(
                    f"{rel}: non-canonical feature artifact reference "
                    f"'{alias}'; use '{canonical}' "
                    "(docs/08-feature-artifact-validation.md)"
                )

        for match in _FEATURE_PATH_RE.finditer(text):
            placeholder = match.group("placeholder")
            artifact = match.group("artifact")
            if placeholder != "feature-id":
                errors.append(
                    f"{rel}: feature artifact path uses '<{placeholder}>'; "
                    "expected '<feature-id>' "
                    "(docs/08-feature-artifact-validation.md)"
                )
            if (
                artifact not in CANONICAL_SINGLETON_FILES
                and artifact not in LEGACY_SINGLETON_ALIASES
                and artifact != "evidence"
            ):
                errors.append(
                    f"{rel}: feature artifact reference '{artifact}' is not "
                    "a canonical singleton name "
                    "(docs/08-feature-artifact-validation.md)"
                )

        errors.extend(_validate_command_argument_grammar(filename, rel, sections))

    return errors


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


def validate_env_example_contract(root: Path | None = None) -> list[str]:
    """Validate the canonical empty .env.example and its ignore protection."""
    base = ROOT if root is None else root
    errors: list[str] = []

    def report(path: str, line: int, message: str) -> None:
        errors.append(f"{path}:{line} [env-example] {message}")

    env_path = base / ENV_EXAMPLE_PATH
    parsed: dict[str, tuple[int, str | None]] = {}
    if not env_path.is_file():
        report(ENV_EXAMPLE_PATH, 1, "required file missing")
    else:
        for line_number, raw_line in enumerate(
            env_path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" in raw_line:
                raw_key, rhs = raw_line.split("=", 1)
                key = raw_key.strip()
            else:
                key = stripped
                rhs = None
            parsed[key] = (line_number, rhs)

        expected_keys = set(ENV_EXAMPLE_KEYS)
        actual_keys = set(parsed)
        for key in sorted(expected_keys - actual_keys):
            report(ENV_EXAMPLE_PATH, 1, f"missing canonical key: {key}")
        for key in sorted(actual_keys - expected_keys):
            report(
                ENV_EXAMPLE_PATH,
                parsed[key][0],
                f"unexpected key: {key}",
            )
        for key in ENV_EXAMPLE_KEYS:
            if key not in parsed:
                continue
            line_number, rhs = parsed[key]
            if rhs != "":
                report(
                    ENV_EXAMPLE_PATH,
                    line_number,
                    f"{key} must have an empty value",
                )

    gitignore_path = base / ".gitignore"
    rule_lines = {rule: [] for rule in GITIGNORE_ENV_RULES}
    if not gitignore_path.is_file():
        report(".gitignore", 1, "required file missing")
    else:
        for line_number, raw_line in enumerate(
            gitignore_path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            normalized = raw_line.strip()
            if normalized in rule_lines:
                rule_lines[normalized].append(line_number)

        for rule in GITIGNORE_ENV_RULES:
            if not rule_lines[rule]:
                report(".gitignore", 1, f"required rule missing: {rule}")

        wildcard_lines = rule_lines[".env.*"]
        exception_lines = rule_lines["!.env.example"]
        if wildcard_lines and exception_lines:
            wildcard_line = wildcard_lines[-1]
            exception_line = exception_lines[-1]
            if exception_line <= wildcard_line:
                report(
                    ".gitignore",
                    exception_line,
                    "!.env.example must appear after .env.*",
                )

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
GRADE_HISTORY_COLUMNS = (
    "Recorded date",
    "From",
    "To",
    "Reason",
    "Evidence refs",
)
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
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
JUDGE_SELF_CHECK_RESULTS = ("PASS", "FAIL", "BLOCKED")
SELF_CHECK_MODES = ("executed", "reused")
JUDGE_SELF_CHECK_FIELDS = (
    "Effective judge configuration",
    "Configuration fingerprint",
    "Self-check mode",
    "Reused self-check evidence ref",
    "Safety/isolation note",
    "Blocker",
)
JUDGE_SELF_CHECK_COLUMNS = (
    "Control ID",
    "Material rule/source",
    "Injection boundary",
    "Baseline",
    "Known-wrong mutation",
    "Expected detector(s)",
    "Actual detector result(s)",
    "Outcome",
)
REUSED_SELF_CHECK_EMPTY_SENTINELS = frozenset({"n/a", "none", "tbd", "-"})
JUDGE_SELF_CHECK_REQUIRED_ROW_FIELDS = (
    "Control ID",
    "Material rule/source",
    "Injection boundary",
    "Baseline",
    "Known-wrong mutation",
    "Expected detector(s)",
    "Actual detector result(s)",
)
OQ_STATUSES = ("OPEN", "CONFIRMED", "NOT-APPLICABLE", "DEFERRED")
OQ_REGISTRY_PATH = "docs/05-open-questions.md"
ENV_EXAMPLE_PATH = ".env.example"
ENV_EXAMPLE_KEYS = (
    "MSSQL_PROD_RO_CONN",
    "MSSQL_TEST_RW_CONN",
    "PG_TEST_RW_CONN",
)
GITIGNORE_ENV_RULES = (".env", ".env.*", "!.env.example")
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
    if s.endswith("|") and not s.endswith(r"\|"):
        s = s[:-1]

    cells = []
    current = []
    index = 0
    while index < len(s):
        char = s[index]
        if char == "\\" and index + 1 < len(s) and s[index + 1] == "|":
            current.append("|")
            index += 2
            continue
        if char == "|":
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(char)
        index += 1
    cells.append("".join(current).strip())
    return cells


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

    self_check = seen.get("Judge self-check")
    if self_check is None or not self_check[1]:
        errors.append(
            _err(
                rel,
                self_check[0] if self_check else 1,
                "missing-field",
                "verification report must contain a non-empty `Judge self-check` field",
            )
        )
        self_check_value = ""
    else:
        self_check_value = self_check[1]
        if self_check_value not in JUDGE_SELF_CHECK_RESULTS:
            errors.append(
                _err(
                    rel,
                    self_check[0],
                    "invalid-enum",
                    f"Judge self-check `{self_check_value}`; expected PASS|FAIL|BLOCKED",
                )
            )

    result_value = result[1] if result else ""
    if (
        result_value in VERIFICATION_RESULTS
        and result_value != "BLOCKED"
        and self_check_value != "PASS"
    ):
        errors.append(
            _err(
                rel,
                result[0],
                "invalid-coupling",
                f"Result `{result_value}` requires Judge self-check `PASS`; "
                f"got `{self_check_value or '<missing>'}`",
            )
        )

    judge_headings = [
        (lineno, line)
        for lineno, line in lines
        if re.fullmatch(r"##\s+Judge self-check\s*", line)
    ]
    if len(judge_headings) != 1:
        errors.append(
            _err(
                rel,
                judge_headings[1][0] if len(judge_headings) > 1 else 1,
                "section-count",
                "verification report must contain exactly one `## Judge self-check` section",
            )
        )
        judge_section: list[tuple[int, str]] = []
    else:
        judge_sections = [
            section_lines
            for title, section_lines in sections
            if title == "judge self-check"
        ]
        if len(judge_sections) != 1:
            errors.append(
                _err(
                    rel,
                    judge_headings[0][0],
                    "section-count",
                    "verification report must contain exactly one `## Judge self-check` section",
                )
            )
            judge_section = []
        else:
            judge_section = judge_sections[0]

    self_check_fields, self_check_duplicates = _unique_fields(
        _parse_kv(judge_section)
    )
    for lineno, key in self_check_duplicates:
        errors.append(
            _err(
                rel,
                lineno,
                "duplicate-key",
                f"duplicate field `{key}` in Judge self-check section",
            )
        )
    for field in JUDGE_SELF_CHECK_FIELDS:
        entry = self_check_fields.get(field)
        if entry is None or not entry[1]:
            errors.append(
                _err(
                    rel,
                    entry[0] if entry else (judge_headings[0][0] if judge_headings else 1),
                    "missing-field",
                    f"Judge self-check must contain a non-empty `{field}` field",
                )
            )

    mode_entry = self_check_fields.get("Self-check mode")
    mode_value = mode_entry[1] if mode_entry else ""
    if mode_value and mode_value not in SELF_CHECK_MODES:
        errors.append(
            _err(
                rel,
                mode_entry[0],
                "invalid-enum",
                f"Self-check mode `{mode_value}`; expected executed|reused",
            )
        )
    reused_ref = self_check_fields.get("Reused self-check evidence ref")
    reused_ref_value = reused_ref[1].strip().casefold() if reused_ref else ""
    if mode_value == "reused" and (
        reused_ref is None
        or not reused_ref[1]
        or reused_ref_value in REUSED_SELF_CHECK_EMPTY_SENTINELS
    ):
        errors.append(
            _err(
                rel,
                reused_ref[0] if reused_ref else (judge_headings[0][0] if judge_headings else 1),
                "missing-reference",
                "reused self-check requires a non-empty, non-`N/A` `Reused self-check evidence ref`",
            )
        )

    control_tables = list(_parse_tables(judge_section))
    valid_control_tables = []
    for table_lineno, headers, rows in control_tables:
        if tuple(headers) != JUDGE_SELF_CHECK_COLUMNS:
            errors.append(
                _err(
                    rel,
                    table_lineno,
                    "invalid-columns",
                    "Judge self-check control table must use exactly these columns: "
                    + " | ".join(JUDGE_SELF_CHECK_COLUMNS),
                )
            )
            continue
        valid_control_tables.append((headers, rows))

    if not control_tables:
        errors.append(
            _err(
                rel,
                judge_headings[0][0] if judge_headings else 1,
                "missing-table",
                "Judge self-check section must contain its control table",
            )
        )

    control_rows = [
        (headers, row_lineno, cells)
        for headers, rows in valid_control_tables
        for row_lineno, cells in rows
    ]
    if mode_value != "reused" and not control_rows:
        errors.append(
            _err(
                rel,
                judge_headings[0][0] if judge_headings else 1,
                "missing-row",
                "Judge self-check control table must contain at least one row "
                "when Self-check mode is not `reused`",
            )
        )

    for headers, row_lineno, cells in control_rows:
        for field in JUDGE_SELF_CHECK_REQUIRED_ROW_FIELDS:
            if not (_cell(headers, cells, field) or "").strip():
                errors.append(
                    _err(
                        rel,
                        row_lineno,
                        "missing-field",
                        f"Judge self-check control row must contain a non-empty `{field}` cell",
                    )
                )
        outcome = _cell(headers, cells, "Outcome") or ""
        if outcome not in JUDGE_SELF_CHECK_RESULTS:
            errors.append(
                _err(
                    rel,
                    row_lineno,
                    "invalid-enum",
                    f"Outcome `{outcome}`; expected PASS|FAIL|BLOCKED",
                )
            )
        if self_check_value == "PASS" and outcome != "PASS":
            errors.append(
                _err(
                    rel,
                    row_lineno,
                    "invalid-coupling",
                    f"Judge self-check `PASS` requires every control Outcome to be `PASS`; "
                    f"got `{outcome}`",
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


def _validate_grade_history(
    rel: str,
    sections: list[tuple[str, list[tuple[int, str]]]],
    grade: tuple[int, str] | None,
    history_lineno: int,
    errors: list[str],
) -> None:
    """Validate the append-only grade-history table of one evidence record."""
    history_sections = [
        section_lines
        for title, section_lines in sections
        if title == "grade history"
    ]
    if not history_sections:
        errors.append(
            _err(
                rel,
                history_lineno,
                "missing-history",
                "evidence record must contain a `## Grade history` section",
            )
        )
        return
    if len(history_sections) > 1:
        errors.append(
            _err(
                rel,
                history_lineno,
                "invalid-schema",
                "evidence record must contain only one `## Grade history` section",
            )
        )

    section_lines = history_sections[0]
    tables = list(_parse_tables(section_lines))
    if not tables:
        errors.append(
            _err(
                rel,
                section_lines[0][0] if section_lines else history_lineno,
                "invalid-schema",
                "`## Grade history` must contain a Markdown table",
            )
        )
        return
    if len(tables) > 1:
        errors.append(
            _err(
                rel,
                tables[1][0],
                "invalid-schema",
                "`## Grade history` must contain exactly one Markdown table",
            )
        )

    header_lineno, headers, rows = tables[0]
    expected_headers = list(GRADE_HISTORY_COLUMNS)
    if headers != expected_headers:
        errors.append(
            _err(
                rel,
                header_lineno,
                "invalid-schema",
                "grade history columns must be exactly "
                + " | ".join(expected_headers),
            )
        )
    if not rows:
        errors.append(
            _err(
                rel,
                header_lineno,
                "missing-history",
                "grade history must contain at least one decision row",
            )
        )
        return

    previous_to: str | None = None
    final_to: str | None = None
    for index, (row_lineno, original_cells) in enumerate(rows):
        cells = list(original_cells)
        if len(cells) != len(GRADE_HISTORY_COLUMNS):
            errors.append(
                _err(
                    rel,
                    row_lineno,
                    "invalid-schema",
                    "grade history rows must contain exactly five cells",
                )
            )
            cells.extend([""] * (len(GRADE_HISTORY_COLUMNS) - len(cells)))
            cells = cells[: len(GRADE_HISTORY_COLUMNS)]

        recorded_date, from_grade, to_grade, reason, evidence_refs = cells
        if not ISO_DATE_RE.fullmatch(recorded_date):
            errors.append(
                _err(
                    rel,
                    row_lineno,
                    "invalid-format",
                    "Recorded date must use YYYY-MM-DD",
                )
            )

        if index == 0:
            if from_grade != "—":
                errors.append(
                    _err(
                        rel,
                        row_lineno,
                        "invalid-invariant",
                        "initial row From must be `—`",
                    )
                )
        elif from_grade not in GRADES:
            errors.append(
                _err(
                    rel,
                    row_lineno,
                    "invalid-enum",
                    f"history From `{from_grade}`; expected A|B|C|D|?",
                )
            )
        elif previous_to is not None and from_grade != previous_to:
            errors.append(
                _err(
                    rel,
                    row_lineno,
                    "invalid-invariant",
                    "history chain is broken: From must equal the preceding row's To",
                )
            )

        if to_grade not in GRADES:
            errors.append(
                _err(
                    rel,
                    row_lineno,
                    "invalid-enum",
                    f"history To `{to_grade}`; expected A|B|C|D|?",
                )
            )
        else:
            final_to = to_grade
            previous_to = to_grade

        if not reason:
            errors.append(
                _err(
                    rel,
                    row_lineno,
                    "invalid-invariant",
                    "Reason must not be empty in grade history",
                )
            )

        if not evidence_refs and not (index == 0 and to_grade == "?"):
            errors.append(
                _err(
                    rel,
                    row_lineno,
                    "invalid-invariant",
                    "Evidence refs must not be empty for this grade decision",
                )
            )

    if grade is None or not grade[1]:
        errors.append(
            _err(
                rel,
                grade[0] if grade else history_lineno,
                "missing-field",
                "Grade is required when grade history exists",
            )
        )
    elif final_to is not None and grade[1] in GRADES and grade[1] != final_to:
        errors.append(
            _err(
                rel,
                grade[0],
                "invalid-invariant",
                f"Grade `{grade[1]}` must equal the final history To `{final_to}`",
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
    header, sections = _split_sections(lines)
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

    history_lineno = next(
        (
            lineno
            for lineno, line in lines
            if (match := HEADING2_RE.match(line))
            and match.group(1).strip().lower() == "grade history"
        ),
        id_lineno,
    )
    _validate_grade_history(rel, sections, grade, history_lineno, errors)


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
    """Run artifact, durable-state, and STOP-contract checks (no fail-fast)."""
    base = ROOT if root is None else root
    oq_errors, oq_ids = validate_oq_registry(base)
    return (
        validate_command_contract(base)
        + validate_features(base)
        + oq_errors
        + validate_feature_schemas(base, oq_ids)
        + validate_durable_state(base, oq_ids)
        + validate_stop_condition_contract(base)
    )


def main() -> None:
    validate_required()
    validate_json()
    validate_skills()
    validate_agents_and_commands()
    errors = (
        validate_agent_routing()
        + validate_skill_routing_contract()
        + validate_skill_execution_contract()
        + validate_env_example_contract()
        + collect_validation_errors()
    )
    if errors:
        raise SystemExit(
            "ERROR: repository validation failed "
            f"({len(errors)} issue(s)):\n"
            + "\n".join(f"- {error}" for error in errors)
        )
    print("Scaffold validation passed.")


if __name__ == "__main__":
    main()
