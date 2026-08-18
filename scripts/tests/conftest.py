"""Makes ``scripts`` importable without manually setting PYTHONPATH.

Mirrors migration/judge/tests/conftest.py: scripts/ is pipeline tooling
with no packaging of its own, so tests import it from the repo root.
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
