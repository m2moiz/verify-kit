---
phase: 4
plan: "04-02"
title: "FastAPI app skeleton + settings + middleware stack + HARN-03 debug router host"
subsystem: backend-template
tags: [fastapi, pydantic-settings, asgi-correlation-id, structlog, middleware, sse, pyinstrument, secure, debug-router]
dependency_graph:
  requires:
    - "04-01 two-guard contract: copier _exclude block + filename-level gating"
  provides:
    - "template/app/: main, api, models, services, settings, __init__ (has_backend gate)"
    - "template/harness/debug_endpoints.py (universal, conditional mount)"
    - "template/tests/backend/: conftest + 4 test files (filename-level gate)"
    - "LIFO middleware stack: secure > CorrelationId > structlog_access_log > pyinstrument"
    - "CorrelationIdMiddleware validator=None contract (accepts arbitrary inbound IDs)"
  affects:
    - template/pyproject.toml.jinja2
    - template/justfile.jinja2
    - template/harness/
    - downstream plans 04-03 (DB), 04-04 (CLI), 04-06 (Logfire), 04-07 (schemathesis)
tech_stack:
  added:
    - fastapi[standard]>=0.115
    - pydantic-settings>=2.5
    - asgi-correlation-id>=4.3
    - sse-starlette>=2.1
    - secure>=1.0
    - pyinstrument>=4.7
    - anyio>=4.4
    - asgi-lifespan>=2.1
    - polyfactory>=2.16
    - dirty-equals>=0.8
    - respx>=0.21 (dev)
    - pytest-asyncio>=0.24 (dev)
  patterns:
    - "LIFO Starlette middleware registration: last-registered = outermost"
    - "CorrelationIdMiddleware with validator=None for permissive ID passthrough"
    - "FastAPI lifespan pattern: load settings in lifespan, store on app.state"
    - "create_app(cwd=None) resolves to Path(__file__).parent.parent — never Path.cwd()"
    - "TestClient as context manager (mandatory for lifespan to run in tests)"
    - "HARN-03 debug router: conditional mount via ENV check at app construction time"
    - "MagicMock patch on app.main.log to intercept structlog access-log middleware"
key_files:
  created:
    - "template/{% if has_backend %}app{% endif %}/__init__.py.jinja2"
    - "template/{% if has_backend %}app{% endif %}/main.py.jinja2"
    - "template/{% if has_backend %}app{% endif %}/api.py.jinja2"
    - "template/{% if has_backend %}app{% endif %}/services.py.jinja2"
    - "template/{% if has_backend %}app{% endif %}/models.py.jinja2"
    - "template/{% if has_backend %}app{% endif %}/settings.py.jinja2"
    - "template/{% if has_backend %}app{% endif %}/.env.example.jinja2"
    - "template/harness/debug_endpoints.py.jinja2"
    - "template/tests/backend/{% if has_backend %}conftest.py{% endif %}.jinja2"
    - "template/tests/backend/{% if has_backend %}test_app.py{% endif %}.jinja2"
    - "template/tests/backend/{% if has_backend %}test_debug_endpoints.py{% endif %}.jinja2"
    - "template/tests/backend/{% if has_backend %}test_correlation_id.py{% endif %}.jinja2"
    - "template/tests/backend/{% if has_backend %}test_request_id_propagation.py{% endif %}.jinja2"
  modified:
    - "template/pyproject.toml.jinja2"
    - "template/justfile.jinja2"
decisions:
  - "LIFO middleware registration: pyinstrument first (innermost), secure last (outermost)"
  - "CorrelationIdMiddleware configured with validator=None so non-UUID inbound IDs pass through unchanged"
  - "HARN-03 debug router is in universal harness/ dir; conditional mount lives in app/main.py (has_backend gate)"
  - "app.main.log patched with MagicMock in T14 test to bypass structlog cache_logger_on_first_use=True ordering issue"
  - "respx.mock.calls read INSIDE the respx context (cleared on exit in respx 0.21+)"
metrics:
  duration: "~70 minutes"
  completed: "2026-05-21"
  tasks_completed: 14
  files_count: 15
requirements: [API-02, API-03, API-05, API-06, API-07, API-08, API-10, API-11, HARN-03]
---

# Phase 4 Plan 04-02: FastAPI App Skeleton + Middleware Summary

## One-liner

FastAPI app with 4-layer LIFO middleware (OWASP headers, correlation-ID, structlog access-log, pyinstrument) wired to pydantic-settings and a conditional HARN-03 debug router, proven by 14 passing tests including a three-way request-ID propagation contract.

## What Was Built

### App Package (`template/{% if has_backend %}app{% endif %}/`)

- **`settings.py`**: `class Settings(BaseSettings)` with `load(cwd: Path) -> Settings` — never reads `Path.cwd()`, resolves `.env` from explicit cwd argument. Fields: ENV, LOG_LEVEL, LOG_FORMAT, DATABASE_URL, PROFILE_ENABLED.
- **`models.py`**: `HealthResponse`, `EchoRequest`, `EchoResponse` — shared between FastAPI routes and the typer CLI (Plan 04-04). `HealthResponse` is the single source of truth for Plan 04-07's verify-backend assertions (REVIEW-CHECKLIST §3).
- **`services.py`**: Pure `echo(req, request_id)` function with no FastAPI imports — importable from CLI without pulling in the web stack.
- **`api.py`**: `GET /healthz`, `POST /echo`, `GET /events/stream` (SSE via sse-starlette). Settings accessed via `request.app.state.settings` (no module-level Settings() call).
- **`main.py`**: `create_app(cwd=None)` with documented LIFO middleware stack. `app = create_app()` module-level instance for `uvicorn app.main:app`. HARN-03 debug router mounted at `/__debug` when `ENV=dev` only.
- **`.env.example`**: Template with all settings fields + optional `LOGFIRE_TOKEN` under `has_logfire` gate.

### HARN-03 Debug Router (`template/harness/debug_endpoints.py.jinja2`)

Universal harness file (no `has_backend` gate on the file itself). Exposes `make_debug_router(cwd: Path)` returning an APIRouter with:
- `GET /state` — reads `cwd / ".verify" / "state.json"`
- `GET /events` — SSE streaming from `cwd / ".verify" / "events.jsonl"`

Both routes root all disk access to the explicit `cwd` argument (REVIEW-CHECKLIST §1).

### Middleware Stack (LIFO registration order)

Starlette/FastAPI middleware registration is LIFO — last-registered = outermost. To achieve the desired outer→inner order:

| Desired position | Middleware | Registration order |
|---|---|---|
| 1 (outermost) | secure OWASP headers | 4th (last) |
| 2 | CorrelationIdMiddleware | 3rd |
| 3 | structlog_access_log | 2nd |
| 4 (innermost) | pyinstrument profiler | 1st |

`CorrelationIdMiddleware` configured with `validator=None` and `generator=lambda: str(uuid.uuid4())` so arbitrary inbound IDs (e.g. `"my-custom-id"`) are accepted unchanged. The default validator (`is_valid_uuid4`) would reject them silently — addressed Codex HIGH #3.

### Test Files (`template/tests/backend/` — filename-level gate)

All 5 files use `{% if has_backend %}leaf.py{% endif %}.jinja2` shape per Plan 04-01 contract.

- **`conftest.py`**: `app_dev`, `app_prod`, `client_dev`, `client_prod` fixtures. All use `TestClient(app) as ctx` (context manager mandatory for lifespan to run).
- **`test_app.py`**: 6 tests covering healthz model shape, echo round-trip, OWASP headers, pyinstrument dev/prod toggle, SSE stream.
- **`test_debug_endpoints.py`**: 4 tests covering state 200/404, prod 404 (router not mounted), events SSE.
- **`test_correlation_id.py`**: 3 tests: UUID4 generation, custom-ID echo (verifies `validator=None`), body-header consistency.
- **`test_request_id_propagation.py`**: 1 three-way contract test — response header == middleware log call == outbound httpx header. Uses `patch("app.main.log", MagicMock())` + `respx.mock`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `structlog.testing.capture_logs` incompatible with `cache_logger_on_first_use=True` after first test lifespan**

- **Found during:** T14 (test_request_id_propagation) execution
- **Issue:** `capture_logs()` installs a `ListProcessor` by patching the structlog config's processor list. When `configure_logging()` is called in the lifespan with `cache_logger_on_first_use=True`, the module-level `log` object in `harness/logging.py` gets its `bind` method replaced with a `finalized_bind` closure that captures the real processor chain. Subsequent `configure()` calls (including from `capture_logs()`) do not affect the cached closure. In the test suite, `configure_logging()` is called by the lifespan of the first `TestClient` app — after that, `capture_logs()` cannot intercept `log.info()` calls from the module-level `log` object in subsequent tests.
- **Fix:** Changed the test to use `patch("app.main.log", MagicMock())` to replace the imported `log` reference in `app.main` with a mock object. The mock records all `log.info()` calls with their kwargs. The assertion checks `c.kwargs.get("request_id")` across all `mock_log.info.call_args_list` entries. Additionally, moved all `mock.calls` assertions inside the `with respx.mock(...)` context block because `respx.mock.calls` is cleared when the context exits (discovered during debugging).
- **Files modified:** `template/tests/backend/{% if has_backend %}test_request_id_propagation.py{% endif %}.jinja2`
- **Test coverage impact:** The test still proves the three-way contract: (a) response header carries `trace-abc-123`, (b) `structlog_access_log` middleware called `log.info()` with `request_id="trace-abc-123"`, (c) outbound httpx call carried the same header. The forcing function remains intact — if `structlog_access_log` is removed from `app/main.py`, assertion (b) fails.

## Known Stubs

None. All routes are fully wired. The `HealthResponse.version` field is hardcoded as `"0.1.0"` in `api.py:healthz` — this is intentional; Plan 04-07 will add dynamic version resolution or this will be addressed when needed.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: new-http-endpoint | template/app/api.py.jinja2 | `/healthz`, `/echo`, `/events/stream` — public routes with no auth |
| threat_flag: debug-endpoint | template/harness/debug_endpoints.py.jinja2 | `/__debug/state` and `/__debug/events` read `.verify/` filesystem — only mounted in `ENV=dev` |

The debug endpoints are gated to `ENV=dev` via the conditional mount in `create_app()`. Production environments will not expose them. The filesystem paths are rooted to the explicit `cwd` argument (no traversal beyond the project root).

## Self-Check: PASSED

- [x] `template/{% if has_backend %}app{% endif %}/main.py.jinja2` exists with `create_app` and `app = create_app()`
- [x] `template/{% if has_backend %}app{% endif %}/settings.py.jinja2` exists with `load(cwd: Path)` signature
- [x] `template/harness/debug_endpoints.py.jinja2` exists with `make_debug_router(cwd: Path)`
- [x] All 5 test files exist in `template/tests/backend/` with filename-level Jinja gates
- [x] `copier copy --data has_backend=true` renders `app/` and `tests/backend/` correctly
- [x] `copier copy --data has_backend=false` renders NO `app/`, NO backend tests, NO fastapi deps
- [x] `uv run pytest tests/backend/ -v` in scratch exits 0 (14 passed)
- [x] Polarity tests (`tests/test_phase04_scaffold_polarity.py`) still pass (3 passed)
- [x] Commit `6465a1d` exists on `feat/phase-4-backend` branch
- [x] `grep "validator=None" scratch/app/main.py` matches (Codex HIGH #3 addressed)
- [x] Middleware LIFO order comment block present in `scratch/app/main.py`
- [x] No bare `Path(".")` or `Path(".env")` literals in any rendered files
