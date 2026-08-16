from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OQ_FILE = Path("docs/05-open-questions.md")

STATUSES = ("OPEN", "CONFIRMED", "NOT-APPLICABLE", "DEFERRED")
ROW_RE = re.compile(r"^\|\s*(OQ-\d+)\s*\|\s*([A-Z-]+)\s*\|")
EVIDENCE_MARKERS = ("**Evidence:**", "## Resolved")


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def git_diff(revision: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", revision, "--", str(OQ_FILE)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        fail(f"git diff failed: {result.stderr.strip()}")
    return result.stdout.splitlines()


def pick_diff() -> list[str]:
    working = git_diff("HEAD")
    if working:
        return working
    if not (ROOT / ".git").exists():
        fail("not a git repository")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if head.returncode != 0 or not head.stdout.strip():
        print("No commits yet; nothing to check.")
        raise SystemExit(0)
    has_parent = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD~1"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if has_parent.returncode != 0:
        print("First commit; nothing to compare against.")
        raise SystemExit(0)
    return git_diff("HEAD~1")


def status_changes(lines: list[str]) -> dict[str, tuple[str, str]]:
    """Map OQ id -> (old status, new status) for rows whose status changed."""
    removed: dict[str, str] = {}
    added: dict[str, str] = {}
    for line in lines:
        if line.startswith("-") and not line.startswith("---") and (
            match := ROW_RE.match(line[1:])
        ):
            removed[match.group(1)] = match.group(2)
        elif line.startswith("+") and not line.startswith("+++") and (
            match := ROW_RE.match(line[1:])
        ):
            added[match.group(1)] = match.group(2)
    return {
        oq: (removed[oq], added[oq])
        for oq, status in added.items()
        if oq in removed and removed[oq] != status
    }


def has_evidence(lines: list[str], oq_id: str) -> bool:
    added = [line[1:] for line in lines if line.startswith("+") and not line.startswith("+++")]
    if any(f"### {oq_id}" in line for line in added):
        return True
    if any(any(marker in line for marker in EVIDENCE_MARKERS) for line in added):
        return True
    return False


def main() -> None:
    lines = pick_diff()
    changes = status_changes(lines)
    if not changes:
        print(f"No status changes in {OQ_FILE}; nothing to check.")
        return
    missing = [
        f"{oq}: {old} -> {new}"
        for oq, (old, new) in sorted(changes.items())
        if not has_evidence(lines, oq)
    ]
    if missing:
        fail(
            "status changed without recorded evidence in the same change "
            f"(expected '## Resolved' section or '**Evidence:**' entry): {', '.join(missing)}. "
            "See the Update rule in docs/05-open-questions.md."
        )
    checked = ", ".join(f"{oq}: {old}->{new}" for oq, (old, new) in sorted(changes.items()))
    print(f"OQ update rule satisfied for: {checked}")


if __name__ == "__main__":
    main()
