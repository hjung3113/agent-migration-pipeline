---
schema_version: 1
generation: 1
status_values: [TODO, IN_PROGRESS, BLOCKED, DONE]
---

# Migration Queue

Queue items must be small enough to resume from disk and have an observable
completion artifact. Machine-readable state is the frontmatter plus exactly
one canonical live table (`docs/11-durable-state-protocol.md`): columns are
exactly `ID | Status | Phase | Depends on | Blocker | Work item |
Completion artifact`; `Depends on` holds `-` or comma-separated queue IDs;
`Blocker` holds `-` or semicolon-separated references (`OQ-###`, canonical
gate criterion IDs such as `G0.1`, `EXT:<kebab-token>`, `HUMAN:<kebab-token>`).

Status semantics: `TODO` means actionable now (all dependencies `DONE`,
`Blocker: -`), not merely "not done yet"; `IN_PROGRESS` means durable
execution has begun; `BLOCKED` means an unfinished dependency or durable
blocker prevents progress; `DONE` means the row's completion artifact exists
and its applicable completion/gate condition is satisfied.

| ID | Status | Phase | Depends on | Blocker | Work item | Completion artifact |
|---|---|---|---|---|---|---|
| Q-001 | BLOCKED | 0 | - | EXT:legacy-source-access | Inspect DLL public surface and host integration | DLL boundary report + OQ updates |
| Q-002 | BLOCKED | 0 | - | EXT:legacy-source-access | Inventory existing tests/CI | test inventory + evidence assessment |
| Q-003 | BLOCKED | 0 | - | EXT:legacy-source-access | Identify observable outputs available outside UI | judge capability matrix |
| Q-004 | BLOCKED | 1 | - | G0.1; G0.2; G0.3 | Generate legacy feature inventory | feature cards in `migration/features/` |
| Q-005 | BLOCKED | 1 | - | G0.1; G0.2; G0.3 | Map MSSQL business logic objects | DB dependency report |
| Q-006 | BLOCKED | 2 | - | G0.1; G0.2; G0.3 | Select one pilot feature | approved pilot feature card |
| Q-007 | BLOCKED | 2 | Q-004, Q-006 | - | Build pilot behavior contract | pilot `behavior-contract.md` with G2 PASS |
| Q-008 | BLOCKED | 3 | Q-007 | - | Design pilot target slice | pilot `target-feature-design.md` with G3 PASS |
| Q-009 | BLOCKED | 4 | Q-008 | - | Implement pilot | approved implementation change + deviation record |
| Q-010 | BLOCKED | 5-6 | Q-009 | - | Independent review + verification | pilot `review.md` + `verification.md` PASS |
| S-001 | DONE | 0 | - | - | Verification judge framework skeleton | migration/judge/{ports,composite,__init__,README}.py |
| S-002 | DONE | 0 | - | - | Characterization capture schema | docs/templates/characterization-record.md |
| S-003 | DONE | 0 | - | - | Equality/normalization comparison rules → RULEBOOK | RULEBOOK.md Evidence section addition |
| S-004 | DONE | 0 | - | - | DLL boundary report template | docs/templates/dll-boundary-report.md |
| S-005 | DONE | 0 | - | - | MSSQL DB dependency report template | docs/templates/db-dependency-report.md |
| S-006 | DONE | 0 | - | - | Pilot selection rubric | docs/templates/pilot-selection-rubric.md |
| S-007 | DONE | 0 | - | - | Target monorepo skeleton (React/FastAPI/Postgres, no business logic) | target/{backend,frontend}, docker-compose.yml, docs/adr/0004 |
| S-008 | DONE | 0 | - | - | Platform adapter boundary contract + lint guard | app.platform/, 4 import-linter contracts, docs/adr/0005 |
| S-009 | DONE | 0 | - | - | FastAPI request/response/error contract convention | app/api/errors.py, app/domain/errors.py, docs/templates/api-contract-checklist.md |
| S-010 | DONE | 0 | - | - | Repo guard automation (validate_scaffold.py + OQ update checks) | .github/workflows/ci.yml, scripts/check_oq_updates.py, scripts/check_doc_links.py |
| S-011 | DONE | 0 | - | - | Pipeline dry-run with synthetic feature + mutation self-test | migration/features/synthetic-demo/, migration/judge/tests/ |
| S-012 | DONE | 0 | - | - | Register approved slices into QUEUE/STATE | this table |

## Slice details (legacy-independent, from `migration/SLICES-DRAFT.md`, approved 2026-08-16)

S-rows are Phase 0 legacy-independent environment slices, runnable regardless
of legacy access; see `migration/SLICES-DRAFT.md` for rationale/citations per
slice. Difficulty/lock-in-risk and review-note detail that does not fit the
canonical live-table columns is preserved here:

- S-001 — difficulty 보통, lock-in 중; Opus reviewed, 5 findings, 4 fixed + 2 tracked as known limitations.
- S-002 — difficulty 보통, lock-in 중; Opus reviewed, 4 findings fixed.
- S-003 — difficulty 간단, lock-in 중; Opus reviewed, 4 findings fixed.
- S-004 — difficulty 간단, lock-in 하.
- S-005 — difficulty 간단, lock-in 하.
- S-006 — difficulty 간단, lock-in 하.
- S-007 — difficulty 보통, lock-in 중; Opus reviewed, import-linter/mypy-strict/compose-healthcheck/port-binding fixed; httpx2 false-positive verified clean.
- S-008 — difficulty 보통, lock-in 상; Opus reviewed, scoped sole-namespace to behavior + named dependency_overrides mechanism + constrained platform->core direction + app.main leaf guard.
- S-009 — difficulty 간단, lock-in 중; Opus reviewed, 6 fixes: 500-handler envelope gap, phrase-derived code instability, status_code raise-site default, OpenAPI 422 mismatch, scalar-detail leak, dropped headers.
- S-010 — difficulty 보통, lock-in 하; lock-in low, no Opus review per policy.
- S-011 — difficulty 복잡, lock-in 하; mutation self-test PASS — judge catches injected mismatch; 1 process fix (judge test PYTHONPATH); lock-in low, no Opus review per policy.
- S-012 — difficulty 간단, lock-in 하.

## Normalization notes (2026-08-19)

Applied when the two historical tables were merged into the canonical live
table per `docs/11-durable-state-protocol.md` ("Migration of existing durable
files"):

- Q-001..Q-003 moved `TODO -> BLOCKED` with `EXT:legacy-source-access`: no
  legacy repository access exists yet, so they are not actionable.
- Q-004..Q-006 moved `TODO -> BLOCKED` with the currently failed G0 criteria:
  `docs/02-migration-pipeline.md` allows only gate-enabling inspection before
  G0 passes, so broad discovery/pilot work cannot start. These blockers clear
  when G0 is re-evaluated as `PASS`.
- Q-007..Q-010 keep their historical `BLOCKED` status; the old
  "blocked by Q-###" prose in the completion-artifact column moved into
  `Depends on`, and each row now states its real completion artifact.
