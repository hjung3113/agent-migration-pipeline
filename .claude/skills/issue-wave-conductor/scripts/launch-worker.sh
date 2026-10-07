#!/bin/zsh
# launch-worker.sh <issue> <slug> — Orca worktree from origin/main → branch hjung3113/issue<issue>-<slug>, copy the brief
# ($WAVE_BRIEFS/<issue>-task.md) + rules templates into .review/, close the setup shells, then delegate launch and
# worker state to the shared worker-ops script.
# WORKER_ROLE defaults to impl; use impl-fallback when Orca hangs. Optional WORKER_MODEL / WORKER_EFFORT override routing.tsv.
# Needs: WAVE_STATE, WAVE_BRIEFS, AMP_MAIN (main checkout path).
: "${WAVE_STATE:?}"; : "${WAVE_BRIEFS:?}"; : "${AMP_MAIN:?}"; set -u
N=$1; SLUG=$2; NAME="issue$N-$SLUG"; SKILL=$AMP_MAIN/.claude/skills/issue-wave-conductor
SHARED_LAUNCH=$HOME/.claude/skills/orca-dispatch-recipes/scripts/worker-launch.sh
[ -f "$SHARED_LAUNCH" ] || { echo "Missing shared launcher: $SHARED_LAUNCH (install orca-dispatch-recipes worker-ops scripts)" >&2; exit 2; }
[ -f "$WAVE_BRIEFS/$N-task.md" ] || { echo "Missing brief: $WAVE_BRIEFS/$N-task.md" >&2; exit 2; }
W=$HOME/orca/workspaces/agent-migration-pipeline/$NAME
orca worktree create --repo path:"$AMP_MAIN" --name "$NAME" --base-branch origin/main --issue "$N" --json >/dev/null 2>&1 || { echo "worktree create failed"; exit 1; }
cd "$W" || exit 1; mkdir -p .review
cp "$SKILL/templates/impl-rules.md" .review/00-IMPL-RULES.md
cp "$SKILL/templates/review-rules.md" .review/00-REVIEW-RULES.md
# The shared launcher reads only the task; prepend the rules pointer without moving the brief's final sentinel.
{ printf 'Read .review/00-IMPL-RULES.md first.\n\n'; cat "$WAVE_BRIEFS/$N-task.md"; } > ".review/W-$N-TASK.md"
for h in $(orca terminal list --worktree path:"$W" --json 2>/dev/null | grep -o 'term_[a-z0-9-]*' | sort -u); do orca terminal close --terminal "$h" >/dev/null 2>&1; done
args=(--role "${WORKER_ROLE:-impl}" --cwd "$W" --task "$W/.review/W-$N-TASK.md"
  --report "$W/.review/W-$N-REPORT.md" --sentinel "<!-- W-$N-DONE -->" --name "W-$N"
  --state-dir "$WAVE_STATE")
[ -n "${WORKER_MODEL:-}" ] && args+=(--model "$WORKER_MODEL")
[ -n "${WORKER_EFFORT:-}" ] && args+=(--effort "$WORKER_EFFORT")
bash "$SHARED_LAUNCH" "${args[@]}"
