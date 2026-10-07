#!/bin/zsh
# verify.sh <checkout> — host gate for one checkout: repo guards (same as CI repo-guards), scripts/tests pytest
# (not in CI), and the target/backend and target/frontend CI gates when the diff vs origin/main touches them.
# Stops at the first failure and prints which check failed.
set -u
ROOT=${1:?usage: verify.sh <checkout>}; cd "$ROOT" || exit 2
run() { local name=$1; shift; echo "== $name"; "$@" || { echo "FAIL: $name"; exit 1; }; }
run scaffold python3 scripts/validate_scaffold.py
run oq-updates python3 scripts/check_oq_updates.py
run doc-links python3 scripts/check_doc_links.py
run scripts-tests python3 -m pytest scripts/tests/ -q
changed=$(git diff --name-only origin/main...HEAD; git diff --name-only HEAD)
if print -r -- "$changed" | grep -q '^target/backend/'; then
  ( cd target/backend && run be-sync uv sync && run be-test uv run pytest && run be-ruff uv run ruff check . \
    && run be-mypy uv run mypy && run be-imports uv run lint-imports ) || exit 1
fi
if print -r -- "$changed" | grep -q '^target/frontend/'; then
  ( cd target/frontend && run fe-install npm ci && run fe-build npm run build && run fe-lint npm run lint \
    && run fe-format npm run format -- --check ) || exit 1
fi
echo "ALL PASS"
