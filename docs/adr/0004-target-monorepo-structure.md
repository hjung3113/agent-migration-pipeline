# ADR-0004: Target monorepo skeleton structure

- Status: Accepted
- Date: 2026-08-16

## Context

The migration target (React/FastAPI/PostgreSQL per `docs/00-project-context.md`) needs a place to live before the first feature slice is implemented. The repo already contains pipeline assets (`migration/`, `docs/`, `.opencode/`) that must stay separate from target application code. Phase 0 forbids business logic and feature endpoints, so this ADR covers structure and tooling only.

## Decision

### Layout

Create `target/` at the repo root with `target/backend` and `target/frontend`. No business logic, no feature endpoints; the only endpoint is `GET /health`. Layer directories (`api/routes`, `domain`, `services`, `repositories`) exist as empty placeholders for the application/service/repository boundaries.

### Backend package manager: uv

Use **uv** with `pyproject.toml`, src-layout (`src/app/`), and a committed `uv.lock`.

- deterministic lockfile for reproducible dev/CI/Docker installs;
- already installed on the dev machine (`uv 0.11.8`), no extra bootstrap;
- manages Python 3.12 itself (system Python is 3.9), avoiding interpreter drift;
- pip + requirements offers no lockfile without extra tooling (pip-tools).

Quality gate config is minimal: pytest + httpx2 for tests, ruff (E/F/I/UP/B), mypy on `src` and `tests`.

### ORM and migrations: SQLAlchemy 2 + Alembic

Adopt **SQLAlchemy 2** (Core/ORM, psycopg 3 driver) and **Alembic** for versioned target schema migrations.

- feature slices need typed models and a reviewable migration history against PostgreSQL;
- RULEBOOK Database #1 forbids mechanically translating MSSQL DDL/SP — that rule governs *where schema semantics come from*; this decision only chooses the *target-side* schema management tool. Target schemas will be designed from behavior contracts, not pasted from MSSQL DDL;
- Alembic is configured but `versions/` is intentionally empty (no tables yet).

### docker-compose scope: PostgreSQL + backend only

`docker-compose.yml` at the repo root provides `postgres` (port 5432, named volume, healthcheck) and `backend` (builds `target/backend`, port 8000, waits for postgres health).

The frontend is **not** in compose:

- local `npm run dev` (Vite HMR) is the primary frontend workflow; a container adds image-build latency and breaks HMR ergonomics with no current benefit;
- there is no deployment topology yet (open question), so a frontend container would be speculative.

Revisit when a staging/preview environment or production packaging story exists.

## Consequences

- pipeline assets and target code stay separated; `target/` can later be extracted without touching `migration/` or `docs/`;
- all skeleton commands verified green: `uv run pytest` / `ruff` / `mypy` (strict) / `lint-imports`, `npm run build` / `lint` / `prettier --check`, `docker compose config`;
- `uv.lock` and `package-lock.json` are committed; build artifacts (`.venv`, `node_modules`, `dist`, caches) are gitignored;
- adapter/platform boundary (RULEBOOK Platform/DLL) is deliberately absent here; it is scoped to S-008.

## Amendments (post-review, 2026-08-16)

Opus-reviewed after initial build; four changes applied:

- **`import-linter` layer contract** added (`app.api -> app.services -> app.repositories -> app.domain`, `pyproject.toml [tool.importlinter]`, run via `uv run lint-imports`). An empty `__init__.py` per layer does not by itself stop a route from importing a repository directly; the contract makes that a CI failure instead of a convention nobody enforces. Cheapest to add before any feature code crosses the boundary.
- **mypy tightened to `strict = true`** with explicit `files = ["src", "tests"]`. Loosening a strict config later is free; retrofitting strict typing across an existing feature codebase is not — cheapest to set now, while there are zero business modules to fix.
- **Backend `docker-compose` healthcheck** added (hits `GET /health` via a Dockerfile-image Python call, no `curl` in the slim image), and both `postgres`/`backend` ports bound to `127.0.0.1` instead of all interfaces to avoid colliding with a local Postgres install. Previously only `postgres` had a healthcheck, so `/health` was exercised by tests but not by compose itself.
- **`POSTGRES_PASSWORD`** changed from a literal to `${POSTGRES_PASSWORD:-app}` (same zero-config default locally, but the substitution point already exists if this compose file is ever copied toward a non-local environment).

One dependency flagged in review (`httpx2` in the backend dev group) was investigated and found correct, not a defect: Starlette 1.6.0's `TestClient` requires `httpx2` and treats the legacy `httpx` package as deprecated (`starlette/testclient.py`, confirmed by reading the installed package). No change made.

Deferred, not applied: a CI workflow enforcing these checks (noted as a gap; no CI exists yet for this repo at all, tracked as a future slice rather than folded into this one).
