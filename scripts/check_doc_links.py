from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC_ROOT = ROOT / "docs" / "templates"

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:", "#", "/")


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def is_internal_relative(target: str) -> bool:
    return not target.startswith(EXTERNAL_PREFIXES)


def check_links(path: Path) -> list[str]:
    problems: list[str] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        for target in LINK_RE.findall(line):
            if not is_internal_relative(target):
                continue
            target_path = target.split("#", 1)[0]
            if not target_path:
                continue
            resolved = (path.parent / target_path).resolve()
            try:
                resolved.relative_to(ROOT)
            except ValueError:
                problems.append(f"{path.relative_to(ROOT)}:{lineno}: link escapes repo: {target}")
                continue
            if not resolved.exists():
                problems.append(f"{path.relative_to(ROOT)}:{lineno}: broken link: {target}")
    return problems


def main() -> None:
    if not DOC_ROOT.exists():
        fail(f"missing directory: {DOC_ROOT.relative_to(ROOT)}")
    problems: list[str] = []
    for path in sorted(DOC_ROOT.rglob("*.md")):
        problems.extend(check_links(path))
    if problems:
        fail("broken doc links:\n  " + "\n  ".join(problems))
    print("Doc link check passed.")


if __name__ == "__main__":
    main()
