---
phase: 4
plan: "04-03"
title: "Async SQLAlchemy + asyncpg + Alembic + Testcontainers Postgres fixture"
subsystem: backend-template
tags: [sqlalchemy, asyncpg, alembic, testcontainers, postgres, db-fixtures, polyfactory, dirty-equals]
dependency_graph:
  requires:
    - "04-01 two-guard contract: copier _exclude block + filename-level gating"
    - "04-02 FastAPI app skeleton: conftest.py ownership + settings.py DATABASE_URL pattern"
  provides:
    - "template/app/db.py: make_engine(database_url) + make_sessionmaker(engine)"
    - "template/app/schema.py: Base(DeclarativeBase) + User model"
    - "template/alembic/: async env.py + script.py.mako + versions/0001_initial.py"
    - "template/alembic.ini: DATABASE_URL env-var substitution"
    - "template/tests/backend/conftest.py: pg_container + db_session fixtures (appended)"
    - "template/tests/backend/test_db_integration.py: insert/query + unique constraint tests"
  affects:
    - template/pyproject.toml.jinja2
    - downstream plans 04-05 (Dockerfile DATABASE_URL), 04-07 (schemathesis)
tech_stack:
  added:
    - sqlalchemy[asyncio]>=2.0
    - asyncpg>=0.29
    - alembic>=1.13
    - testcontainers[postgres]>=4.7 (dev)
    - polyfactory>=2.16 (already added in 04-02; used here for UserCreateFactory)
    - dirty-equals>=0.8 (already added in 04-02; used here for IsInt/IsDatetime assertions)
  patterns:
    - "Two-guard path gating: has_backend segment gate + has_db filename gate for app/* files"
    - "Single-flag segment gate for alembic/* (safe per Copier when: clause guarantees)"
    - "make_engine(database_url: str) — no cwd or env reads inside; caller supplies URL"
    - "pg_container fixture uses docker info (not shutil.which) to detect daemon liveness"
    - "scratch_root = Path(__file__).resolve().parent.parent.parent (3 parents from conftest)"
    - "DB fixtures inlined in conftest.py under {% if has_db %} block (no pytest_plugins)"
key_files:
  created:
    - "template/{% if has_backend %}app{% endif %}/{% if has_db %}db.py{% endif %}.jinja2"
    - "template/{% if has_backend %}app{% endif %}/{% if has_db %}schema.py{% endif %}.jinja2"
    - "template/{% if has_db %}alembic.ini{% endif %}.jinja2"
    - "template/{% if has_db %}alembic{% endif %}/env.py.jinja2"
    - "template/{% if has_db %}alembic{% endif %}/script.py.mako"
    - "template/{% if has_db %}alembic{% endif %}/versions/0001_initial.py.jinja2"
    - "template/tests/backend/{% if has_db %}test_db_integration.py{% endif %}.jinja2"
  modified:
    - "template/pyproject.toml.jinja2 (added DB + testcontainers deps in separate block)"
    - "template/tests/backend/{% if has_backend %}conftest.py{% endif %}.jinja2 (appended has_db block)"
decisions:
  - "Two-guard path shape for app/* DB files: top-level has_backend segment + filename-level has_db gate prevents db.py leaking to scaffold root when has_backend=true/has_db=false"
  - "_docker_daemon_running() uses subprocess.run(['docker','info'], timeout=5) not shutil.which() — which returns non-None even when daemon is stopped (cycle-2 Codex HIGH #9)"
  - "scratch_root uses 3 .parent calls (conftest.py is at scratch/tests/backend/conftest.py; 2 parents only reaches scratch/tests/ with no alembic.ini — cycle-3 HIGH E)"
  - "DB fixtures merged inline into conftest.py under {% if has_db %} block — eliminates fragile pytest_plugins = ['tests.backend.conftest_db'] import path (cycle-2 HIGH #10)"
  - "aiosqlite not declared as dependency; import-sanity test for make_engine uses postgresql+asyncpg:// URL (engine construction is lazy, no actual connection)"
metrics:
  duration: "~20 minutes"
  completed: "2026-05-21"
  tasks_completed: 6
  files_count: 9
requirements: [API-04, API-13, API-14]
---

# Phase 4 Plan 04-03: DB Stack + Testcontainers Summary

## One-liner

Async SQLAlchemy 2.x + asyncpg + Alembic with a users model and initial migration, plus a Testcontainers Postgres session fixture with docker-info daemon detection, all gated on `has_backend AND has_db` via the two-guard path contract.

## What Was Built

### DB Engine + Session Factory (`app/db.py`)

- `make_engine(database_url: str)` — builds `AsyncEngine` lazily (no connection at construction time). Takes URL explicitly from caller; reads no environment variables or filesystem paths.
- `make_sessionmaker(engine)` — returns `async_sessionmaker` configured with `expire_on_commit=False` and `class_=AsyncSession`.
- REVIEW-CHECKLIST §1 compliant: zero bare `Path()` literals, zero `os.environ` reads.

### Declarative Models (`app/schema.py`)

- `Base(DeclarativeBase)` — shared metadata base for all models.
- `User` model with columns: `id` (PK integer), `email` (String(255), unique, not null), `created_at` (DateTime with timezone, server_default=func.now()).
- `__tablename__ = "users"` matches the initial Alembic migration.

### Alembic Configuration

- **`alembic.ini`**: `sqlalchemy.url = ${DATABASE_URL}` — env-var substitution. Standard loggers/handlers/formatters.
- **`alembic/env.py`**: Async migration runner using `async_engine_from_config` + `NullPool`. DATABASE_URL pulled from `os.environ.get("DATABASE_URL")` (not Path.cwd). Replaces `%` to `%%` for URL safety.
- **`alembic/script.py.mako`**: Standard Alembic async migration template.
- **`alembic/versions/0001_initial.py`**: Creates `users` table with id, email, created_at. Downgrade drops the table.

### Test Fixtures (conftest.py append)

Added `{% if has_db %}` block to the existing Plan 04-02 conftest:

- `_docker_daemon_running()` — runs `subprocess.run(["docker", "info"], capture_output=True, timeout=5)`. Returns `True` iff exit code is 0. Handles `FileNotFoundError` (docker CLI not installed) and `subprocess.TimeoutExpired` (daemon unresponsive).
- `pg_container` (session-scoped) — starts `PostgresContainer("postgres:16-alpine")`, converts URL to `postgresql+asyncpg://`, runs `alembic upgrade head` with `cwd=scratch_root` and `timeout=120`. `scratch_root = Path(__file__).resolve().parent.parent.parent` (3 parents from `scratch/tests/backend/conftest.py` → `scratch/`). Yields db_url; stops container on teardown.
- `db_session` (async, `@pytest_asyncio.fixture`) — builds engine + sessionmaker from pg_container URL. Yields session. Calls `await engine.dispose()` after yield.

### Integration Tests (`tests/backend/test_db_integration.py`)

- `test_can_insert_and_query_user`: Uses `UserCreateFactory.build()` (polyfactory), inserts a `User`, re-queries via `select(User).where(...)`, asserts `row.id == IsInt` and `row.created_at == IsDatetime` (dirty-equals API-13 demonstration).
- `test_unique_email_constraint`: Inserts duplicate email, expects `Exception` on second commit (IntegrityError or driver-wrapped form).

### Dependency Updates (pyproject.toml)

DB deps in a clearly-separated `{% if has_backend and has_db %}` block (distinct from 04-02's FastAPI block and 04-04's CLI block):
- Production: `sqlalchemy[asyncio]>=2.0`, `asyncpg>=0.29`, `alembic>=1.13`
- Dev: `testcontainers[postgres]>=4.7`

## Polarity Verification

Both polarities verified with copier render:

| Condition | app/db.py | alembic.ini | test_db_integration.py | sqlalchemy in pyproject |
|---|---|---|---|---|
| has_backend=true AND has_db=true | PRESENT | PRESENT | PRESENT | PRESENT |
| has_backend=true AND has_db=false | ABSENT | ABSENT | ABSENT | ABSENT |

## Deviations from Plan

None. The plan was executed exactly as written. The cycle-2 and cycle-3 replan notes were already incorporated into the plan before execution began — all replan decisions (3-parent scratch_root, docker info check, inline conftest fixtures, postgresql+asyncpg sanity test) were followed as specified.

## Known Stubs

None. The DB layer is fully functional when rendered. The integration tests skip cleanly when Docker daemon is not running (via `_docker_daemon_running()` check), which is correct behavior for CI environments without Docker.

## Threat Flags

None. No new HTTP endpoints or auth paths introduced. The DB layer adds a postgres connection surface but only when has_db=true; the connection URL is always supplied by the caller (never auto-detected).

## Self-Check: PASSED

- [x] `template/{% if has_backend %}app{% endif %}/{% if has_db %}db.py{% endif %}.jinja2` exists
- [x] `template/{% if has_backend %}app{% endif %}/{% if has_db %}schema.py{% endif %}.jinja2` exists
- [x] `template/{% if has_db %}alembic.ini{% endif %}.jinja2` exists
- [x] `template/{% if has_db %}alembic{% endif %}/env.py.jinja2` exists
- [x] `template/{% if has_db %}alembic{% endif %}/script.py.mako` exists
- [x] `template/{% if has_db %}alembic{% endif %}/versions/0001_initial.py.jinja2` exists
- [x] `template/tests/backend/{% if has_db %}test_db_integration.py{% endif %}.jinja2` exists
- [x] has_db=true render: all DB files present (app/db.py, app/schema.py, alembic.ini, alembic/, test_db_integration.py)
- [x] has_db=false render: all DB files absent
- [x] sqlalchemy in pyproject.toml when has_db=true; absent when has_db=false
- [x] pg_container in conftest.py when has_db=true; absent when has_db=false
- [x] No pytest_plugins in rendered conftest.py
- [x] scratch_root uses 3 .parent calls (not 2)
- [x] _docker_daemon_running() uses "docker info" (not shutil.which)
- [x] No bare Path() literals in app/db.py
- [x] engine.dispose() called after yield in db_session
- [x] Commits 2723fa8, a2fba31, a5e03b7, 88592c8, 2c6db4a, 6b3cf24 all exist on worktree-agent-a09d9c4cc8c01df91 branch
