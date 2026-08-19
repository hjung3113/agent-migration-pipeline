---
schema_version: 1
generation: 1
phase: "0"
phase_name: "Environment and feasibility"
status: BLOCKED
current_gate: G0
gate_result: BLOCKED
failed_gate_criteria: [G0.1, G0.2, G0.3]
active_queue_items: []
next_queue_items: []
blocked_queue_items: [Q-001, Q-002, Q-003]
last_updated: "2026-08-19T15:20:46Z"
---

# Migration State

The frontmatter above is the machine-readable state contract
(`docs/11-durable-state-protocol.md`); commands and validators never infer
state from the prose below.

## Active phase gate

- Gate: G0 — FOUNDATION_READY
- Result: BLOCKED — failed criteria: G0.1, G0.2, G0.3 (authoritative values
  live in the frontmatter above)
- Evidence:
  - legacy repository access required for the real DLL-boundary report is not yet available;
  - `migration/evidence/dll-boundary-report.md` does not yet contain the required analyzed host-callable entry points;
  - `migration/evidence/observable-output-survey.md` does not yet contain a parity-usable observable output;
  - `docs/05-open-questions.md` still has OQ-001 and OQ-010 as `OPEN`.

Project `status: BLOCKED` is the operational derivation from the queue, not a
copy of the gate result: every current-gate (Phase 0) queue row is `BLOCKED`
on external legacy-source access, so no useful Phase 0 work is actionable
right now. A failed gate alone would not force project `BLOCKED` while
gate-enabling work remains actionable. The canonical criterion definitions
and failure protocol are in `docs/02-migration-pipeline.md`.

## Completed

- initial project goal documented
- OpenCode-native environment structure drafted
- agent/skill/command roles drafted
- DLL invocation constraint recorded
- incomplete-test / limited-UI verification strategy drafted
- project-level open questions created
- OQ-024 resolved (Superpowers pinned to v6.3.0)
- S-001..S-012 (`migration/SLICES-DRAFT.md`): every legacy-independent slice
  reachable from currently-confirmed decisions is done — evidence/judge
  tooling (composite judge + mutation-self-test-verified, characterization
  schema, equality rules, DLL/DB/pilot templates), a full target monorepo
  skeleton (FastAPI + React/Tailwind + PostgreSQL, no business logic),
  the platform adapter boundary guard, the API error contract, repo-guard
  CI, and a full synthetic pipeline dry-run confirming the process itself
  is runnable end-to-end. See `migration/QUEUE.md` for per-slice detail and
  review notes.

## Next gate work

Only G0-enabling inspection is allowed before broad feature discovery:

1. obtain legacy source access and create `migration/evidence/dll-boundary-report.md` from `docs/templates/dll-boundary-report.md`;
2. create `migration/evidence/observable-output-survey.md` from `docs/templates/observable-output-survey.md`;
3. resolve OQ-001 and OQ-010 from evidence;
4. re-evaluate G0.1-G0.3 and advance to Phase 1 only if all are `PASS`.
