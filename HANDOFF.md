# Handoff

Single handoff file for this repo. **Always update this file in place — do
not create dated/numbered handoff files.** See AGENTS.md "Handoff rule."

Last updated: 2026-08-17

## State

Phase 0 (environment scaffold). Every slice in `migration/SLICES-DRAFT.md`
that is reachable without legacy source access is done (S-001..S-012, see
`migration/QUEUE.md` for per-slice detail and review notes). Full detail in
`migration/STATE.md`.

Built this session:
- Legacy-independent slice reconstruction (`migration/SLICES-DRAFT.md`)
- Evidence/judge tooling: characterization schema, equality rules,
  DLL/DB/pilot templates, composite judge (`migration/judge/`,
  **mutation-self-test verified** — it genuinely catches an injected wrong
  result, see `migration/features/synthetic-demo/DRY-RUN-REPORT.md`)
- Target monorepo skeleton: `target/backend` (FastAPI, uv, SQLAlchemy2+Alembic,
  strict mypy, import-linter layer + platform-boundary contracts) and
  `target/frontend` (Vite+React+TS+Tailwind), `docker-compose.yml`
- Platform adapter boundary (`app.platform`, ADR-0005) — enforced by 4
  import-linter contracts, no implementation yet (host contract unresolved)
- API error contract convention (`app.api.errors`, `app.domain.errors`)
- Repo-guard CI (`.github/workflows/ci.yml`), OQ-update check, doc-link check
- Full synthetic pipeline dry-run (discover->spec->design->implement->verify)

All work committed to `main` in small, one-slice-per-commit history
(commits `e9f2d97`..`c03c832`). Nothing squashed — read `git log` for the
review findings behind each slice, they're in the commit bodies.

## Blocked

**Legacy source access.** Everything past this point needs it:

- Q-001 (DLL boundary inspection), Q-002 (test/CI inventory), Q-003
  (observable-output survey) — `migration/QUEUE.md`
- All of P0 `docs/05-open-questions.md` (OQ-001..OQ-010) — still OPEN
- Nothing else in `migration/SLICES-DRAFT.md` is reachable without it

## Next session should

1. If legacy repo access has opened: start Q-001/Q-002/Q-003, then
   Q-004 (feature inventory) and Q-005 (DB dependency map). Fill in the
   (currently empty) templates from S-004/S-005 with real findings.
2. If still blocked: nothing new to build here without guessing. Don't
   invent legacy facts — check with the user before assuming access has
   changed.
3. Workflow used this session, reusable if slice work resumes: dispatch
   implementation to `opencode run -m zai-coding-plan/glm-5.3 --variant
   low|high --format json --auto "<prompt>"` (low for simple+low-lock-in,
   high otherwise), then for any slice rated lock-in medium/high in
   `SLICES-DRAFT.md`, extract only the risky diff (not whole files) and
   send it to an Opus subagent (`Agent({model: "opus", ...})`) for review
   before committing. `opencode run` times out around 280s on multi-file
   tasks — re-run with `--continue` to resume the same session.

## Known gaps / not done

- `migration/judge/README.md` "known limitations": no uniform port method
  across the six adapter ports, `EvidenceResult.source` not validated
  against the port that produced it. Deferred — no concrete adapter exists
  yet to be shaped by fixing them now.
- No CI run has actually executed yet (workflow added S-010, unverified on
  a real push/PR — verify after this push).
