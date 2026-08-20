"""Generate and validate the agent-local Issue #13 STOP contract.

``AGENTS.md`` owns the policy text.  This module only reads the marked
canonical block and publishes that same normalized body into every Markdown
agent definition.  Role-specific instructions belong in each agent's
``## Stop handling`` section and are deliberately not generated here.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENTS_PATH = "AGENTS.md"
AGENTS_DIR = ".opencode/agents"

CANONICAL_STOP_BEGIN_MARKER = "<!-- BEGIN MANAGED STOP CONDITIONS -->"
CANONICAL_STOP_END_MARKER = "<!-- END MANAGED STOP CONDITIONS -->"
AGENT_STOP_BEGIN_MARKER = "<!-- BEGIN GENERATED STOP CONDITIONS -->"
AGENT_STOP_END_MARKER = "<!-- END GENERATED STOP CONDITIONS -->"

CANONICAL_STOP_IDS = tuple(f"SC-{index:02d}" for index in range(1, 8))
STOP_CONDITION_LINE_RE = re.compile(r"^-\s+(SC-\d{2})\s*:\s+.+$")
H2_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)

STOP_PAYLOAD_FIELDS = (
    "Reason:",
    "Stop condition:",
    "Scope:",
    "Feature:",
    "Queue item:",
    "Completed:",
    "Evidence:",
    "Unresolved:",
    "Impact:",
    "Recommended next route:",
    "Stop current gate:",
    "Partial artifact:",
)

STOP_HANDLING_MARKERS = (
    "common STOP payload",
    "migration-coordinator",
)
STOP_PAYLOAD_FENCE_RE = re.compile(r"```text\s*\n(?P<body>.*?)\n```", re.DOTALL)


def _normalize(text: str) -> str:
    """Normalize only line endings, trailing whitespace, and outer blanks."""

    return "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").splitlines()).strip()


def _marked_body(
    text: str,
    begin_marker: str,
    end_marker: str,
    *,
    label: str,
) -> tuple[str | None, list[str]]:
    errors: list[str] = []
    begin_positions = [match.start() for match in re.finditer(re.escape(begin_marker), text)]
    end_positions = [match.start() for match in re.finditer(re.escape(end_marker), text)]
    if len(begin_positions) != 1:
        errors.append(
            f"{label}: expected exactly one begin marker {begin_marker!r}; "
            f"found {len(begin_positions)}"
        )
    if len(end_positions) != 1:
        errors.append(
            f"{label}: expected exactly one end marker {end_marker!r}; "
            f"found {len(end_positions)}"
        )
    if errors:
        return None, errors
    start = begin_positions[0] + len(begin_marker)
    end = end_positions[0]
    if start > end:
        return None, [f"{label}: stop-condition markers are out of order"]
    return _normalize(text[start:end]), []


def _validate_canonical_body(body: str, label: str) -> list[str]:
    errors: list[str] = []
    found: list[str] = []
    for line in body.splitlines():
        if line.lstrip().startswith("- SC-"):
            match = STOP_CONDITION_LINE_RE.fullmatch(line.strip())
            if match is None:
                errors.append(
                    f"{label}: malformed canonical stop-condition entry: {line!r}"
                )
            else:
                found.append(match.group(1))
    if found != list(CANONICAL_STOP_IDS):
        errors.append(
            f"{label}: canonical stop-condition IDs must be exactly "
            f"{', '.join(CANONICAL_STOP_IDS)} in order; found {found or 'none'}"
        )
    return errors


def load_canonical_stop_conditions(
    root: Path | None = None,
) -> tuple[str, list[str]]:
    """Return the normalized AGENTS.md registry body and structural errors."""

    base = ROOT if root is None else root
    path = base / AGENTS_PATH
    if not path.is_file():
        return "", [f"{AGENTS_PATH}: canonical policy file missing"]
    text = path.read_text(encoding="utf-8")
    headings = [match.group(1).strip().lower() for match in H2_RE.finditer(text)]
    errors: list[str] = []
    if headings.count("stop conditions") != 1:
        errors.append(
            f"{AGENTS_PATH}: expected exactly one '## Stop conditions' heading; "
            f"found {headings.count('stop conditions')}"
        )
    body, marker_errors = _marked_body(
        text,
        CANONICAL_STOP_BEGIN_MARKER,
        CANONICAL_STOP_END_MARKER,
        label=AGENTS_PATH,
    )
    errors.extend(marker_errors)
    if body is None:
        return "", errors
    errors.extend(_validate_canonical_body(body, AGENTS_PATH))
    return body, errors


def _section_body(text: str, title: str) -> str | None:
    matches = [match for match in H2_RE.finditer(text) if match.group(1).strip().lower() == title.lower()]
    if not matches:
        return None
    heading = matches[0]
    next_heading = H2_RE.search(text, heading.end())
    end = next_heading.start() if next_heading else len(text)
    return text[heading.end():end].strip()


def _agent_stop_block(canonical_body: str) -> str:
    return (
        f"{AGENT_STOP_BEGIN_MARKER}\n"
        f"{canonical_body}\n"
        f"{AGENT_STOP_END_MARKER}"
    )


def _replace_agent_block(text: str, canonical_body: str) -> str:
    block = _agent_stop_block(canonical_body)
    begin_positions = [match.start() for match in re.finditer(re.escape(AGENT_STOP_BEGIN_MARKER), text)]
    end_positions = [match.start() for match in re.finditer(re.escape(AGENT_STOP_END_MARKER), text)]
    if len(begin_positions) == 1 and len(end_positions) == 1:
        start = begin_positions[0]
        end = end_positions[0] + len(AGENT_STOP_END_MARKER)
        updated = text[:start] + block + text[end:]
        if not re.search(r"^##\s+Stop conditions\s*$", updated, re.MULTILINE):
            updated = "## Stop conditions\n\n" + updated
        return updated

    headings = list(H2_RE.finditer(text))
    stop_headings = [
        match for match in headings if match.group(1).strip().lower() == "stop conditions"
    ]
    if stop_headings:
        heading = stop_headings[0]
        next_heading = H2_RE.search(text, heading.end())
        end = next_heading.start() if next_heading else len(text)
        prefix = text[: heading.end()].rstrip()
        suffix = text[end:].lstrip()
        return f"{prefix}\n\n{block}\n\n{suffix}" if suffix else f"{prefix}\n\n{block}\n"

    escalation = next(
        (
            match
            for match in headings
            if match.group(1).strip().lower() == "escalation"
        ),
        None,
    )
    section = f"## Stop conditions\n\n{block}\n\n"
    if escalation is not None:
        prefix = text[: escalation.start()].rstrip()
        suffix = text[escalation.start():].lstrip()
        return f"{prefix}\n\n{section}{suffix}"
    return f"{text.rstrip()}\n\n{section.rstrip()}\n"


def sync_agent_files(root: Path | None = None) -> list[Path]:
    """Refresh the managed block in every ``.opencode/agents/*.md`` file."""

    base = ROOT if root is None else root
    canonical_body, errors = load_canonical_stop_conditions(base)
    if errors:
        raise ValueError("\n".join(errors))
    agent_dir = base / AGENTS_DIR
    paths = sorted(agent_dir.glob("*.md")) if agent_dir.is_dir() else []
    changed: list[Path] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        updated = _replace_agent_block(text, canonical_body)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
            changed.append(path)
    return changed


def validate_agent_stop_conditions(root: Path | None = None) -> list[str]:
    """Check canonical publication and the common STOP payload structure."""

    base = ROOT if root is None else root
    canonical_body, errors = load_canonical_stop_conditions(base)
    if errors:
        return errors
    agent_dir = base / AGENTS_DIR
    if not agent_dir.is_dir():
        return [f"{AGENTS_DIR}: agent definition directory missing"]
    paths = sorted(agent_dir.glob("*.md"))
    if not paths:
        return [f"{AGENTS_DIR}: no agent definitions found"]

    common_payload: str | None = None
    for path in paths:
        rel = path.relative_to(base).as_posix()
        text = path.read_text(encoding="utf-8")
        headings = [match.group(1).strip().lower() for match in H2_RE.finditer(text)]
        if headings.count("stop conditions") != 1:
            errors.append(
                f"{rel}: expected exactly one '## Stop conditions' heading; "
                f"found {headings.count('stop conditions')}"
            )
        agent_body, marker_errors = _marked_body(
            text,
            AGENT_STOP_BEGIN_MARKER,
            AGENT_STOP_END_MARKER,
            label=rel,
        )
        if marker_errors:
            errors.append(
                f"{rel}: missing managed/generated Stop conditions block"
            )
            errors.extend(marker_errors)
        elif agent_body != canonical_body:
            errors.append(
                f"{rel}: generated Stop conditions block drifts from AGENTS.md"
            )

        handling = _section_body(text, "Stop handling")
        if not handling:
            errors.append(f"{rel}: missing required '## Stop handling' section")
            continue
        for marker in STOP_HANDLING_MARKERS:
            if marker not in handling:
                errors.append(
                    f"{rel}: '## Stop handling' missing required marker {marker!r}"
                )
        for field in STOP_PAYLOAD_FIELDS:
            if field not in handling:
                errors.append(
                    f"{rel}: '## Stop handling' missing common STOP payload field "
                    f"'{field}'"
                )
        payloads = [
            _normalize(match.group("body"))
            for match in STOP_PAYLOAD_FENCE_RE.finditer(handling)
            if "Reason:" in match.group("body")
        ]
        if len(payloads) != 1:
            errors.append(
                f"{rel}: '## Stop handling' must contain exactly one fenced "
                f"common STOP payload; found {len(payloads)}"
            )
        elif common_payload is None:
            common_payload = payloads[0]
        elif payloads[0] != common_payload:
            errors.append(
                f"{rel}: common STOP payload drifts from the other agent definitions"
            )
    return errors


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="refresh every agent block")
    mode.add_argument("--check", action="store_true", help="validate without writing")
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.write:
            changed = sync_agent_files(args.root)
            for path in changed:
                print(path.relative_to(args.root).as_posix())
            return 0
        errors = validate_agent_stop_conditions(args.root)
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    if errors:
        print("ERROR: agent STOP-condition validation failed", file=sys.stderr)
        print("\n".join(f"- {error}" for error in errors), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
