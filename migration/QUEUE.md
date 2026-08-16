# Migration Queue

Queue items must be small enough to resume from disk and have an observable completion artifact.

| ID | Status | Phase | Work item | Completion artifact |
|---|---|---|---|---|
| Q-001 | TODO | 0 | Inspect DLL public surface and host integration | DLL boundary report + OQ updates |
| Q-002 | TODO | 0 | Inventory existing tests/CI | test inventory + evidence assessment |
| Q-003 | TODO | 0 | Identify observable outputs available outside UI | judge capability matrix |
| Q-004 | TODO | 1 | Generate legacy feature inventory | feature cards in `migration/features/` |
| Q-005 | TODO | 1 | Map MSSQL business logic objects | DB dependency report |
| Q-006 | TODO | 2 | Select one pilot feature | approved pilot feature card |
| Q-007 | BLOCKED | 2 | Build pilot behavior contract | blocked by Q-004/Q-006 |
| Q-008 | BLOCKED | 3 | Design pilot target slice | blocked by Q-007 |
| Q-009 | BLOCKED | 4 | Implement pilot | blocked by Q-008 |
| Q-010 | BLOCKED | 5-6 | Independent review + verification | blocked by Q-009 |

## Legacy-independent slices (from `migration/SLICES-DRAFT.md`, approved 2026-08-16)

Runnable regardless of legacy access. See SLICES-DRAFT.md for rationale/citations per slice.

| ID | Status | Difficulty | Lock-in risk | Work item | Completion artifact |
|---|---|---|---|---|---|
| S-003 | DONE | 간단 | 중 | Equality/normalization comparison rules → RULEBOOK | RULEBOOK.md Evidence section addition (Opus reviewed, 4 findings fixed) |
| S-004 | DONE | 간단 | 하 | DLL boundary report template | docs/templates/dll-boundary-report.md |
| S-005 | DONE | 간단 | 하 | MSSQL DB dependency report template | docs/templates/db-dependency-report.md |
| S-006 | DONE | 간단 | 하 | Pilot selection rubric | docs/templates/pilot-selection-rubric.md |
| S-002 | DONE | 보통 | 중 | Characterization capture schema | docs/templates/characterization-record.md (Opus reviewed, 4 findings fixed) |
| S-001 | DONE | 보통 | 중 | Verification judge framework skeleton | migration/judge/{ports,composite,__init__,README}.py (Opus reviewed, 5 findings, 4 fixed + 2 tracked as known limitations) |
| S-007 | DONE | 보통 | 중 | Target monorepo skeleton (React/FastAPI/Postgres, no business logic) | target/{backend,frontend}, docker-compose.yml, docs/adr/0004 (Opus reviewed, import-linter/mypy-strict/compose-healthcheck/port-binding fixed; httpx2 false-positive verified clean) |
| S-008 | DONE | 보통 | 상 | Platform adapter boundary contract + lint guard | app.platform/, 4 import-linter contracts, docs/adr/0005 (Opus reviewed, scoped sole-namespace to behavior + named dependency_overrides mechanism + constrained platform->core direction + app.main leaf guard) |
| S-009 | TODO | 간단 | 중 | FastAPI request/response/error contract convention | shared schema + convention doc |
| S-010 | TODO | 보통 | 하 | Repo guard automation (validate_scaffold.py + OQ update checks) | CI/script additions |
| S-011 | TODO | 복잡 | 하 | Pipeline dry-run with synthetic feature + mutation self-test | dry-run report + rulebook/skill fixes |
| S-012 | DONE | 간단 | 하 | Register approved slices into QUEUE/STATE | this table |
