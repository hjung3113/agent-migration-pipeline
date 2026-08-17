# Migration State

- Phase: 0 — Environment scaffold
- Status: BLOCKED — G0: G0.1, G0.2, G0.3
- Last updated: 2026-08-18

## Active phase gate

- Gate: G0 — FOUNDATION_READY
- Result: BLOCKED
- Failed criteria: G0.1, G0.2, G0.3
- Evidence:
  - legacy repository access required for the real DLL-boundary report is not yet available;
  - `migration/evidence/dll-boundary-report.md` does not yet contain the required analyzed host-callable entry points;
  - `migration/evidence/observable-output-survey.md` does not yet contain a parity-usable observable output;
  - `docs/05-open-questions.md` still has OQ-001 and OQ-010 as `OPEN`.

The canonical criterion definitions and failure protocol are in `docs/02-migration-pipeline.md`.

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
