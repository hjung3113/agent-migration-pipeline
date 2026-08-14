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


def main() -> None:
    validate_required()
    validate_json()
    validate_skills()
    validate_agents_and_commands()
    print("Scaffold validation passed.")


if __name__ == "__main__":
    main()
