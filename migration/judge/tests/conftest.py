"""Makes ``migration.judge`` importable without manually setting PYTHONPATH.

Discovered during the S-011 pipeline dry-run: migration/judge has no
pyproject.toml/pytest config of its own (it is pipeline tooling, not part of
the target/backend Python project), so ``python3 -m pytest
migration/judge/tests/`` fails to resolve ``from migration.judge...`` imports
without this. Minimal process fix per README principle 7 ("fix the process")
— no structural change to composite.py/ports.py.
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
