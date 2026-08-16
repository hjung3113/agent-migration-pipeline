# Migration State

- Phase: 0 — Environment scaffold
- Status: ACTIVE — blocked on legacy repository access (Q-001/Q-002/Q-003)
- Last updated: 2026-08-17

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

## Next gate

Legacy source access is required to make further progress: Q-001/Q-002/Q-003
(DLL boundary inspection, test/CI inventory, observable-output survey) and
downstream Q-004..Q-010 all depend on it. Nothing further in
`migration/SLICES-DRAFT.md` is reachable without it. Before broad migration
work, inspect the actual legacy repository and resolve enough P0 questions
to define:

1. the DLL public boundary;
2. available observable outputs;
3. the minimum viable characterization/parity judge (framework now exists —
   `migration/judge/` — concrete adapters are what's blocked).
