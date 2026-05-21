---
phase: 4
plan: "04-04"
title: "Typer CLI sibling + Ralph host wiring"
subsystem: backend-template
tags: [typer, cli, api-09, harn-06, ralph, shared-model]
dependency_graph:
  requires:
    - "04-01 two-guard path-gating contract"
    - "04-02 app.models (EchoRequest, EchoResponse) + app.services (echo)"
    - "Phase 3 harness.ralph.run canonical shape"
  provides:
    - "template/app/cli.py: Typer CLI sharing Pydantic models with FastAPI (API-09)"
    - "template/pyproject.toml: app-cli entry point gated in {% if has_backend %}"
    - "template/tests/backend/test_cli.py: API-09 contract test"
    - "template/tests/backend/test_ralph_in_app_context.py: HARN-06 canonical-shape test"
  affects:
    - downstream plans 04-07 (verify-backend slice, README)
tech_stack:
  added:
    - typer>=0.12 (already in pyproject base deps — used explicitly from app.cli)
  patterns:
    - "API-09 single-schema two-interfaces: app.cli imports from app.models, not redefines"
    - "@app.callback() forces multi-command mode to prevent single-command Typer hoisting"
    - "_spawn hook (not executor str) is the injectable test seam in harness.ralph.run"
    - "ralph._spawn callable returns {done: bool, cost_usd: float} — NOT {status: str}"
    - "filename-level Jinja gate for test files: {% if has_backend %}test_*.py{% endif %}.jinja2"
key_files:
  created:
    - "template/{% if has_backend %}app{% endif %}/cli.py.jinja2"
    - "template/tests/backend/{% if has_backend %}test_cli.py{% endif %}.jinja2"
    - "template/tests/backend/{% if has_backend %}test_ralph_in_app_context.py{% endif %}.jinja2"
  modified:
    - "template/pyproject.toml.jinja2"
decisions:
  - "@app.callback() added to prevent Typer single-command hoisting (echo subcommand works regardless of has_db)"
  - "_spawn used as injectable test seam (not executor=callable); executor remains a str per ralph.run signature"
  - "Ralph stub returns {done, cost_usd} per _default_executor contract, not {status}"
metrics:
  duration: "~20 minutes"
  completed: "2026-05-21"
  tasks_completed: 4
  files_count: 4
requirements: [API-09, HARN-06]
---

# Phase 4 Plan 04-04: Typer CLI Sibling + Ralph Host Summary

## One-liner

Typer CLI sharing Pydantic models with FastAPI (API-09 single-schema two-interfaces), with a Ralph canonical-shape contract test that uses the correct `_spawn` hook and `{done, cost_usd}` stub protocol.

## What Was Built

### CLI (`template/{% if has_backend %}app{% endif %}/cli.py.jinja2`)

- `from app.models import EchoRequest` and `from app.services import echo` — single source of truth, same classes as the FastAPI app (API-09 contract).
- `@app.command("echo")` subcommand: builds `EchoRequest`, calls `echo(req, request_id=rid)`, outputs `resp.model_dump_json()`.
- `@app.command("db-ping")` wrapped in `{% if has_db %}` — reads `DATABASE_URL` via `typer.Option(..., envvar="DATABASE_URL")`, no module-level `os.environ` read.
- `@app.callback()` added as an explicit no-op to prevent Typer's single-command hoisting (when `has_db=false`, only one `@app.command` is registered; without `@app.callback()`, Typer makes it the root interface, breaking `app-cli echo`).
- No bare `Path(...)` literals anywhere.

### pyproject.toml (`template/pyproject.toml.jinja2`)

Added `{% if has_backend %}` block in `[project.scripts]`:
```toml
[project.scripts]
verify-kit = "harness.cli:app_entry"
{% if has_backend %}
app-cli = "app.cli:main"
{% endif %}
```
Kept in a separate section from 04-03's db deps (`asyncpg`, `sqlalchemy`, `alembic`).

### Test: CLI contract (`template/tests/backend/{% if has_backend %}test_cli.py{% endif %}.jinja2`)

- `test_cli_echo_outputs_valid_echo_response`: invokes `uv run app-cli echo --message hello` via subprocess with `cwd=scratch_root` (REVIEW-CHECKLIST §1); deserializes stdout into `EchoResponse` from `app.models` (REVIEW-CHECKLIST §3 shared-model assertion).
- `test_cli_help_lists_echo`: asserts `--help` exits 0 and contains "echo".
- Both subprocess calls have explicit `cwd=` and `timeout=60`.

### Test: Ralph canonical-shape contract (`template/tests/backend/{% if has_backend %}test_ralph_in_app_context.py{% endif %}.jinja2`)

- `test_ralph_run_returns_canonical_shape`: uses `_spawn=stub_spawn` (the correct injectable hook; NOT `executor=callable`). Stub returns `{"done": bool, "cost_usd": float}` per `_default_executor` protocol. Asserts result fields `status`, `iters`, `cost_usd`, `output_path` by exact name — NO drift aliases (`iters_completed`, `stop_reason`, `last_iter_at`, `total_iters` from Phase 3 cycle-3 bug).
- `test_ralph_run_emits_state_file_at_cwd_relative_path`: asserts `.verify/ralph.json` exists under `tmp_path` (cwd-rooted, REVIEW-CHECKLIST §1).
- Required `prompt` parameter passed to `ralph.run()`.
- Both tests pass `cwd=tmp_path` — never process cwd.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Plan test code used wrong injectable hook and wrong stub protocol**

- **Found during:** T04 implementation + verification
- **Issue:** The plan's `test_ralph_in_app_context.py` code called `ralph.run(executor=stub_executor, ...)` but the actual `ralph.run()` signature is `_spawn: Callable | None = None` for the injectable test seam; `executor` is a `str` (the command name). Additionally, the stub returned `{"status": "continue", "cost_usd": 0.01}` but the real `_default_executor` contract requires `{"done": bool, "cost_usd": float}` — `status` is the OUTPUT shape, not the INPUT. Finally, the required `prompt: str` parameter was missing from the plan's `ralph.run(...)` call.
- **Fix:** Changed to `_spawn=stub_spawn` with stub returning `{"done": False, "cost_usd": 0.01}` / `{"done": True, "cost_usd": 0.01}`. Added `prompt="just verify"`. Added inline docstring explaining the contract distinction.
- **Files modified:** `template/tests/backend/{% if has_backend %}test_ralph_in_app_context.py{% endif %}.jinja2`
- **Commit:** 9760575

**2. [Rule 1 - Bug] Typer single-command hoisting breaks `app-cli echo` when has_db=false**

- **Found during:** T01 verification (rendered scratch + pytest run)
- **Issue:** When `has_db=false`, only `@app.command("echo")` is registered. Typer's default behavior hoists a sole `@app.command()` to the root interface, so `app-cli echo --message hi` fails with "Got unexpected extra argument (echo)". The caller must instead invoke `app-cli --message hi` — but the plan's acceptance criterion and test both expect `app-cli echo --message hi`.
- **Fix:** Added `@app.callback()` as an explicit no-op decorator on the Typer app. This signals to Typer that the app always has a root-level callback, forcing multi-command mode unconditionally.
- **Files modified:** `template/{% if has_backend %}app{% endif %}/cli.py.jinja2`
- **Commit:** 7b3ea12

## Known Stubs

None. The CLI is fully wired to `app.services.echo` and `app.models`. The `db-ping` command is gated on `has_db` and relies on `app.db.make_engine` from Plan 04-03.

## Threat Flags

None. The CLI adds no network endpoints or auth paths. The `db-ping` command reads `DATABASE_URL` from environment (no module-level reads) and is only rendered when `has_db=true`.

## Self-Check: PASSED

- [x] `template/{% if has_backend %}app{% endif %}/cli.py.jinja2` exists with `from app.models import EchoRequest` and `from app.services import echo`
- [x] `template/tests/backend/{% if has_backend %}test_cli.py{% endif %}.jinja2` exists with `test_cli_echo_outputs_valid_echo_response` and `test_cli_help_lists_echo`
- [x] `template/tests/backend/{% if has_backend %}test_ralph_in_app_context.py{% endif %}.jinja2` exists with `_spawn=stub_spawn` (not `executor=callable`) and correct `{done, cost_usd}` stub protocol
- [x] `template/pyproject.toml.jinja2` contains `app-cli = "app.cli:main"` inside `{% if has_backend %}` block
- [x] Rendered scratch (has_backend=true, has_db=false): `app/cli.py` exists, `tests/backend/test_cli.py` exists, `tests/backend/test_ralph_in_app_context.py` exists
- [x] Rendered scratch (has_backend=false): none of the above files exist; `pyproject.toml` has no `app-cli`
- [x] `pytest tests/backend/test_ralph_in_app_context.py -v` in scratch exits 0 (2 passed)
- [x] `pytest tests/backend/test_cli.py -v` in scratch exits 0 (2 passed)
- [x] `tests/test_phase04_scaffold_polarity.py` still passes (3 passed)
- [x] Commits b1929e5, 9760575, 7b3ea12 exist on `worktree-agent-a4d6dc750dd0bdd57`
- [x] REVIEW-CHECKLIST §1 (cwd): subprocess calls have `cwd=scratch_root`; ralph tests pass `cwd=tmp_path`; no bare `Path(".")` literals
- [x] REVIEW-CHECKLIST §2 (after return): no dead code after return; db-ping's `asyncio.run(_ping())` completes before return
- [x] REVIEW-CHECKLIST §3 (contract drift): test_cli imports `EchoResponse` from `app.models`; test_ralph asserts `{status, iters, cost_usd, output_path}` only (no drift aliases)
