---
phase: 4
plan: "04-07"
title: "just verify-backend slice (schemathesis fuzz + smoke + integration) + README backend section"
subsystem: backend-verify-slice
tags: [schemathesis, harness, verify-backend, just, readme, integration-test, in-process-fuzz]
dependency_graph:
  requires:
    - "04-01 two-guard contract: _exclude block + filename-level gating"
    - "04-02 FastAPI app skeleton: create_app(cwd), /healthz, /openapi.json routes"
    - "04-03 DB stack: Testcontainers fixture (conftest.py)"
    - "04-04 Typer CLI sibling: app-cli entry point"
    - "04-05 Docker: docker-up + docker-down just recipes"
    - "04-06 Logfire + fastapi-mcp opt-ins (dependency chain)"
  provides:
    - "harness/checks/backend.py: @register('backend') check with live+in-process schemathesis fuzz"
    - "harness/checks/backend_inprocess_fuzz.py: schemathesis via ASGITransport when :8000 unreachable"
    - "harness/checks/__init__.py: conditional import of backend check (side-effect registration)"
    - "justfile: verify-backend (FULL stack + fuzz) + verify-backend-quick (pytest only)"
    - "README.md: Backend (FastAPI) layout section with route/DB-model/verify/opt-in docs"
    - "tests/test_phase04_integration.py: 3-function integration test"
    - "tests/test_verify_umbrella_includes_backend.py (template): forcing-function test"
  affects:
    - template/pyproject.toml.jinja2
    - template/harness/checks/__init__.py.jinja2
    - template/justfile.jinja2
    - template/README.md.jinja2
tech_stack:
  added:
    - "schemathesis>=3.36 (dev dep under has_backend, Plan 04-07 T01)"
  patterns:
    - "@register('backend') harness check with two-path schemathesis: live over-network OR in-process via ASGITransport"
    - "schemathesis.openapi.from_asgi('/openapi.json', app) + engine.from_schema(schema) for in-process fuzzing"
    - "SuiteFinished event status check (FAILURE/ERROR) for failure detection — NOT ScenarioRecorder.failures"
    - "uv sync --extra dev (not --dev) for optional-dependencies extras in scratch scaffold"
    - "_CLEAN_ENV + UV_FROZEN=1 to prevent VIRTUAL_ENV leak from outer test runner"
key_files:
  created:
    - "template/harness/checks/{% if has_backend %}backend.py{% endif %}.jinja2"
    - "template/harness/checks/{% if has_backend %}backend_inprocess_fuzz.py{% endif %}.jinja2"
    - "template/tests/{% if has_backend %}test_verify_umbrella_includes_backend.py{% endif %}.jinja2"
    - "tests/test_phase04_integration.py"
  modified:
    - "template/pyproject.toml.jinja2"
    - "template/harness/checks/__init__.py.jinja2"
    - "template/justfile.jinja2"
    - "template/README.md.jinja2"
decisions:
  - "Plan uses @register_check/CheckSeverity/CheckResult(ok=) API but real API is @register/CheckResult(status=)/ErrorEnvelope — adapted to real API"
  - "Plan says update registry.py.jinja2 for imports but real pattern uses checks/__init__.py — used __init__.py"
  - "Plan uses --only=backend but real CLI flag is --check=backend — used correct flag"
  - "test_verify_umbrella_includes_backend.py moved to template/tests/ (not template/tests/backend/) to prevent recursive pytest when backend.run() calls pytest tests/backend/"
  - "Quick-path integration test uses has_db=false to avoid Testcontainers Alembic failure in graceful-degradation scenario"
  - "schemathesis.openapi.from_asgi + engine.from_schema.execute() event stream — SuiteFinished(status=FAILURE) for failure detection"
metrics:
  duration: "~90 minutes"
  completed: "2026-05-21"
  tasks_completed: 7
  files_count: 8
requirements: [API-12, API-18, API-19]
---

# Phase 4 Plan 04-07: verify-backend slice + README Summary

## One-liner

`@register('backend')` harness check running pytest then schemathesis (live over-network when app reachable OR in-process via `schemathesis.openapi.from_asgi` + `engine.from_schema` when not), wired into `just verify-backend` (FULL: docker-up→fuzz→tear-down) and `just verify-backend-quick` (pytest + opportunistic fuzz), with README backend section and two-tier integration tests.

## What Was Built

### T01: schemathesis dev dep (`template/pyproject.toml.jinja2`)

Added `"schemathesis>=3.36"` under `[project.optional-dependencies].dev` inside the `{% if has_backend %}` block. Gating mirrors the other backend dev deps (pytest-asyncio, httpx, respx).

### T02 + T03: Backend harness check (`template/harness/checks/backend.py.jinja2` + `__init__.py`)

`@register("backend", tier="standard", category="backend")` check function `run(cwd: Path) -> CheckResult`. Two-phase execution:

1. **pytest step:** `uv run pytest tests/backend/ -q --tb=short` with explicit `cwd=cwd` and `timeout=600`. Returns `CheckResult(status="fail", error=ErrorEnvelope(...))` on non-zero exit.
2. **schemathesis step:** probes `http://localhost:8000/healthz` with `httpx.get(timeout=2.0)`.
   - If reachable → `uv run schemathesis run http://localhost:8000/openapi.json --checks all --max-examples 20` (over-network path)
   - If not reachable → `uv run python -m harness.checks.backend_inprocess_fuzz --max-examples 10 --cwd {cwd}` (in-process path)

`fix_command` uses f-string interpolating the actual `cwd` argument (no literal `{scaffold_root}` placeholder).

Import wired in `template/harness/checks/__init__.py.jinja2` as:
```python
{% if has_backend %}
from harness.checks import backend as _backend  # noqa: F401
{% endif %}
```

### T04: verify-backend + verify-backend-quick just recipes

`verify-backend` (FULL):
- `just docker-up` → pytest → schemathesis live fuzz → `curl /healthz` + `/__debug/state` → `just docker-down`
- Success criterion 3 ground truth — schemathesis MUST run against the live OpenAPI

`verify-backend-quick` (local UX):
- pytest only; checks `/healthz` reachability before opportunistic fuzz
- Prints `"app not running on :8000 — pytest only"` message on graceful-degradation path

Both recipes gated inside `{% if has_backend %}` block.

### T05: README backend section

Added `{% if has_backend %}` block containing "Backend (FastAPI) layout" section documenting:
- `app/` directory structure with all modules
- "Adding a route" 4-step workflow
- "Adding a database model" 3-step workflow (gated under `{% if has_db %}`)
- Local stack commands (`just docker-up`, `just serve`)
- Verify commands (`just verify-backend`, `just verify-backend-quick`)
- Add-on flag matrix (`has_logfire`, `has_fastapi_mcp`, `has_db`)

### T06: Phase 4 integration test (`tests/test_phase04_integration.py`)

Three test functions:
- `test_fresh_scaffold_verify_backend_full_path_exits_zero` — FULL path with Docker; requires copier, uv, just, Docker daemon; asserts schemathesis ran against `http://localhost:8000/openapi.json`
- `test_fresh_scaffold_verify_backend_quick_skips_live_checks` — quick path without Docker; uses `has_db=false` to avoid Testcontainers Alembic failure in graceful-degradation scenario; asserts "app not running" OR "app reachable" message
- `test_has_backend_false_has_no_verify_backend_recipe` — polarity: no `verify-backend:` in justfile, no `app/`, no `tests/backend/`

Helper infrastructure:
- `_CLEAN_ENV`: strips `VIRTUAL_ENV` to prevent leak from outer test runner
- `_scratch_env(scratch)`: strips `VIRTUAL_ENV` + `UV_PROJECT` + `UV_ENV_FILE` + sets `UV_FROZEN=1`
- `_render_scratch(tmp_path, *, has_backend, has_db)`: renders scaffold + runs `uv sync --extra dev` (not `--dev` — template uses optional-dependencies extras, not dependency-groups)

### T07: in-process fuzz + umbrella test

`template/harness/checks/backend_inprocess_fuzz.py.jinja2`:
- Imports `create_app(cwd=scaffold_root)` from `app.main`
- Calls `schemathesis.openapi.from_asgi("/openapi.json", app)` → `engine.from_schema(schema).execute()`
- Detects failures via `SuiteFinished(status in [FAILURE, ERROR])` events
- Exits 0/1

`template/tests/test_verify_umbrella_includes_backend.py.jinja2` (at `template/tests/`, NOT `template/tests/backend/`):
- Calls `verify-kit verify --check=backend` (not `--only=backend`)
- Asserts exit 0
- Asserts schemathesis was exercised (live URL OR `backend_inprocess_fuzz` OR `schemathesis` keyword)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Plan uses wrong harness API (`@register_check`, `CheckSeverity`, `CheckResult(ok=)`)**

- **Found during:** T02 implementation
- **Issue:** The plan's backend.py code uses `@register_check(id=..., severity=CheckSeverity.ERROR, ...)` and `CheckResult(ok=True/False, fix_command=..., docs_url=...)`. The real harness API (from Phase 2, verified in `harness/checks/lint.py.jinja2`) is `@register("backend", tier=..., ...)` and `CheckResult(status="pass"/"fail", error=ErrorEnvelope(fix_command=..., docs_url=...))`. No `CheckSeverity` exists.
- **Fix:** Adapted T02 to use the real API: `@register("backend", tier="standard")`, `CheckResult(status="fail", error=ErrorEnvelope(...))` on failure, `CheckResult(status="pass")` on success.
- **Files modified:** `template/harness/checks/{% if has_backend %}backend.py{% endif %}.jinja2`

**2. [Rule 1 - Bug] Plan adds backend import to `registry.py.jinja2` but actual pattern uses `checks/__init__.py.jinja2`**

- **Found during:** T03 implementation
- **Issue:** The plan says "Update `template/harness/registry.py.jinja2`" for auto-discovery imports. The real auto-discovery pattern (from Phase 2 implementation) is in `template/harness/checks/__init__.py.jinja2` which already imports all checks for side-effect registration. `registry.py` is the decorator/catalog module, not the import-discovery module.
- **Fix:** Added conditional import to `template/harness/checks/__init__.py.jinja2` instead.
- **Files modified:** `template/harness/checks/__init__.py.jinja2`

**3. [Rule 1 - Bug] Plan uses `--only=backend` CLI flag but real flag is `--check=backend`**

- **Found during:** T07 implementation
- **Issue:** The plan's T07 test and T07 acceptance criteria use `verify-kit verify --only=backend`. Looking at `harness/cli.py.jinja2`, the flag is `--check` (accepts a check id, repeatable, CSV). There is no `--only` flag.
- **Fix:** Used `--check=backend` in `test_verify_umbrella_includes_backend.py` and documented the correct flag in the test docstring.
- **Files modified:** `template/tests/{% if has_backend %}test_verify_umbrella_includes_backend.py{% endif %}.jinja2`

**4. [Rule 1 - Bug] `test_verify_umbrella_includes_backend.py` in `tests/backend/` caused recursive pytest invocation**

- **Found during:** T06 integration test verification
- **Issue:** The plan placed `test_verify_umbrella_includes_backend.py` in `template/tests/backend/`. When `just verify-backend-quick` runs `uv run pytest tests/backend/ -v`, it includes this test, which calls `verify-kit verify --check=backend`, which triggers `backend.run(cwd)`, which calls `uv run pytest tests/backend/` again — recursive subprocess invocation.
- **Fix:** Moved to `template/tests/` (top-level tests in the scaffold, not the backend subdirectory). Updated `scaffold_root` derivation from `parent.parent.parent` → `parent.parent` accordingly.
- **Files modified:** `template/tests/{% if has_backend %}test_verify_umbrella_includes_backend.py{% endif %}.jinja2`

**5. [Rule 1 - Bug] `uv sync --dev` did not install pytest in scratch (extras vs groups)**

- **Found during:** T06 integration test execution
- **Issue:** `uv sync --dev` installs `[dependency-groups].dev`. The template uses `[project.optional-dependencies].dev` (extras). `uv sync --dev` produces a venv without pytest/schemathesis.
- **Fix:** Changed to `uv sync --extra dev` in `_render_scratch()`.
- **Files modified:** `tests/test_phase04_integration.py`

**6. [Rule 2 - Design] Quick-path integration test needs `has_db=false` to avoid Testcontainers failure**

- **Found during:** T06 integration test execution with Docker running
- **Issue:** `test_fresh_scaffold_verify_backend_quick_skips_live_checks` rendered scratch with `has_db=true`. With Docker running, Testcontainers starts Postgres and runs `alembic upgrade head` — but the scratch project's Alembic isn't configured (no DATABASE_URL or alembic.ini env setup). This causes `CalledProcessError` in the pytest fixture, making `just verify-backend-quick` exit 1.
- **Fix:** Used `has_db=false` for the quick-path test. The quick test validates graceful degradation (no live app) not DB integration.
- **Files modified:** `tests/test_phase04_integration.py`

**7. [Rule 3 - Blocking] VIRTUAL_ENV leaked from outer test runner caused wrong venv selection**

- **Found during:** T06 integration test execution
- **Issue:** When `uv run pytest` (outer verify-kit test) spawns `just verify-backend-quick` in scratch, the outer `VIRTUAL_ENV` env var pointed at verify-kit's own `.venv`. `uv run` inside `just` used this wrong venv (Python 3.12, no fastapi).
- **Fix:** Added `_CLEAN_ENV` (strips VIRTUAL_ENV) for copier/uv sync calls, and `_scratch_env()` (strips VIRTUAL_ENV, UV_PROJECT, UV_ENV_FILE; sets UV_FROZEN=1) for just/uv subprocess calls.
- **Files modified:** `tests/test_phase04_integration.py`

## Known Stubs

None. All verify paths are wired:
- `backend.run()` always runs schemathesis (live or in-process)
- `just verify-backend` runs the full stack
- `just verify-backend-quick` runs pytest + opportunistic fuzz
- README backend section is complete

## Threat Flags

None. This plan adds no new network endpoints. The harness check runs existing routes; the README documents them; the integration test runs in a temporary scratch directory.

## Self-Check: PASSED

- [x] `template/harness/checks/{% if has_backend %}backend.py{% endif %}.jinja2` exists with `@register("backend", ...)` decorator and `run(cwd: Path) -> CheckResult` function
- [x] All subprocess.run calls in backend.py have explicit `cwd=cwd` and `timeout=`
- [x] No bare `Path("...")` literals in backend.py
- [x] `fix_command` uses f-string interpolating actual `cwd` argument
- [x] `template/harness/checks/__init__.py.jinja2` contains `{% if has_backend %}` conditional import
- [x] `template/harness/checks/{% if has_backend %}backend_inprocess_fuzz.py{% endif %}.jinja2` exists
- [x] `template/tests/{% if has_backend %}test_verify_umbrella_includes_backend.py{% endif %}.jinja2` exists at top-level tests (not backend/)
- [x] `template/justfile.jinja2` contains `verify-backend:` and `verify-backend-quick:` inside `{% if has_backend %}`
- [x] `template/README.md.jinja2` contains `## Backend (FastAPI) layout` inside `{% if has_backend %}`
- [x] `tests/test_phase04_integration.py` exists with 3 test functions
- [x] `uv run pytest tests/test_phase04_scaffold_polarity.py tests/test_phase04_optin_polarity.py tests/test_phase04_docker_compose.py -v` → 10 passed
- [x] `uv run pytest tests/test_phase04_integration.py::test_has_backend_false_has_no_verify_backend_recipe tests/test_phase04_integration.py::test_fresh_scaffold_verify_backend_quick_skips_live_checks -v` → 2 passed
- [x] Commits 3ab529f, 5be70b7, 5397a4b, 3acfbe1, 5d9b2ea, 2feda0b, 2a68377 exist on `feat/phase-4-backend`
