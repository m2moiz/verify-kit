---
phase: 02-universal-harness-core
plan: "06"
subsystem: harness
tags: [cli, core-facade, jaeger, justfile, atomic-writes, did-you-mean, atexit]
requires: ["02-01", "02-02", "02-03", "02-04", "02-05"]
provides:
  - "harness.core: thin facade verify() / list_checks() preserving Phase-1 signature"
  - "harness.cli: 4-command Typer app (verify, list-checks, describe, trace) with did-you-mean wrapping"
  - "harness.jaeger: fetch_latest_trace + render_trace_waterfall over Jaeger HTTP API"
  - "template/justfile: verify-clean, trace-up (Jaeger 1.76.0), trace-down, trace recipes (8 total)"
  - "template/pyproject.toml: pinned OTel deps + httpx + structlog + hypothesis/jsonschema dev"
affects: ["harness.__init__ public re-exports", "console_script verify-kit → harness.cli:app_entry"]
tech-stack:
  added: ["typer>=0.12", "rich>=13", "httpx>=0.27", "opentelemetry-api/sdk/exporter-otlp-proto-grpc ==1.41.1"]
  patterns: ["standalone_mode=False UsageError handling", "atomic disk writes via tmp + os.replace", "module-level atexit one-shot registration"]
key-files:
  created:
    - "template/harness/jaeger.py.jinja2"
    - "tests/test_phase2_core_facade.py"
    - "tests/test_phase2_cli.py"
    - "tests/test_phase2_jaeger_justfile_deps.py"
    - ".planning/phases/02-universal-harness-core/02-06-SUMMARY.md"
  modified:
    - "template/harness/core.py.jinja2 (rewritten as thin facade)"
    - "template/harness/cli.py.jinja2 (rewritten as 4-command Typer app)"
    - "template/harness/__init__.py.jinja2 (re-export Phase-2 surface)"
    - "template/justfile.jinja2 (+4 recipes)"
    - "template/pyproject.toml.jinja2 (deps + scripts entrypoint)"
    - "pyproject.toml (rich/httpx/typer added to dev deps for test harness)"
    - "tests/test_toolchain.py (Phase-1 forbid-list updated for Phase-2 recipes)"
decisions:
  - "app_entry indirection: console_script targets app_entry, not app, so the did-you-mean wrapper applies to console-script invocations, not just `python -m harness.cli`"
  - "Split --quick/--full flags instead of single --tier enum: `just verify --quick` reads more naturally than `just verify --tier=quick` (CLI ergonomics over textual uniformity)"
  - "Disk artifacts (.verify/report.{json,junit.xml,sarif}) always written regardless of --format: HARN-02 requires these files exist after every verify, independent of stdout format choice"
  - "Atomic writes via tmp file + os.replace prevent agents from reading partial JSON/SARIF while `verify` is still emitting (review post-MEDIUM suggestion)"
  - "EXIT_WRITE_FAILED=12 supersedes EXIT_CHECK_FAIL=1: missing .verify/report.junit.xml is more severe than a check failure because it breaks downstream CI tooling silently (review MEDIUM-6)"
  - "Module-level atexit registration with a _ATEXIT_REGISTERED sentinel, NOT inside @app.callback(), so handlers do not stack under CliRunner.invoke (review MEDIUM-5)"
  - "standalone_mode=False returns the exit code (does not re-raise) — app_entry checks the return value and sys.exits explicitly on non-zero (Click internals observed at runtime)"
  - "describe envelope uses CheckCatalogEntry.model_json_schema(), not CheckSpec.model_json_schema() — CheckSpec.fn is a Callable and produces poor schema output (review MEDIUM-1)"
metrics:
  duration_minutes: 28
  completed: "2026-05-18"
  tasks: 3
  commits: 6
---

# Phase 2 Plan 06: Final CLI + Core Facade Wiring Summary

Wired the user-facing surface for verify-kit Phase 2: rewrote `harness.core`
as a thin facade over `harness.runner.run_phase`, replaced the single-command
Phase-1 Typer CLI with a four-command Typer app that includes did-you-mean
wrapping on two surfaces (unknown options + unknown subcommands), atomic disk
writes with `EXIT_WRITE_FAILED` precedence over `EXIT_CHECK_FAIL`, module-level
one-shot `atexit` registration of the OTel shutdown handler, a `harness.jaeger`
client for the `trace --last` Jaeger HTTP API call, and four new justfile
recipes for the Jaeger lifecycle and cache cleanup.

## What got built

### Task 1 — `harness.core` thin facade + `harness.__init__` exports
Old Phase-1 body (with inlined `_check_*` functions) deleted; new body imports
`harness.checks` (side-effect: `@register` fires for every in-tree check),
performs tier filtering, applies optional `check_ids` selection (with
did-you-mean on unknown ids), filters `config.checks.disabled`, builds a
`CacheStore` (or `None` for `--no-cache`), calls `run_phase`, packages results
into a `VerifyReport`, and **evicts cache entries before returning**.

Two convergence-HIGH guards honored:
1. **CWD contract:** `core.verify(cwd: Path = Path("."))` calls
   `load_config(cwd / "pyproject.toml")` when no config is passed — NOT
   `load_config()` with the process-CWD default. See `core.py.jinja2:69-71`.
2. **Cache eviction order:** `cache.evict_if_needed(...)` runs **before**
   `return report`. See `core.py.jinja2:131-138` for the inline rationale and
   `tests/test_phase2_core_facade.py::test_verify_evicts_before_return` for
   the spy-based regression guard (asserts `evict_spy.call_count == 1` at the
   moment `verify()` returns).

### Task 2 — `harness.cli` multi-command Typer rewrite
Four commands wired:
- `verify` — runs the standard tier by default, `--quick`/`--full` switch
  tier, `--no-cache` bypasses cache, `--check=<id>` (repeatable + CSV) narrows
  selection, `--format=<fmt>` selects from FORMATTERS (auto-pretty on TTY,
  auto-json piped). Always writes 3 disk artifacts.
- `list-checks` — `--format=plain` (one id per line) or `--format=json`
  (CheckCatalogEntry array, never CheckSpec).
- `describe` — FMT-04 envelope: version, commands, exit_codes,
  exit_code_precedence note, check_catalog_schema, report_schema, checks,
  jsonl_summary_marker.
- `trace --last` — calls `harness.jaeger.fetch_latest_trace()` and renders
  a Rich tree via `render_trace_waterfall`. Lazy-imports `harness.jaeger`
  so the httpx dep doesn't pay on every CLI call.

`app_entry()` wraps `app(standalone_mode=False)` and translates
`click.UsageError` into did-you-mean messages. Token extraction uses a regex
(`-{1,2}([A-Za-z0-9...])`) to handle both `"No such option: --x"` and
`"No such option '--x'."` spellings emitted by different Click code paths.
The wrapper also checks the return value of `app()` because
`standalone_mode=False` causes Click to **return** the exit code on
`typer.Exit` (not re-raise) — without `sys.exit(rv)`, a `typer.Exit(2)` in a
subcommand would surface as a 0-exit subprocess.

`_ATEXIT_REGISTERED` sentinel + module-level call to
`atexit.register(observability.shutdown)` registers the OTel flush exactly
once, independent of how many `CliRunner.invoke` calls a test makes.

### Task 3 — `harness.jaeger` + justfile + pyproject deps
`harness.jaeger`: `fetch_latest_trace(service="verify-kit")` hits
`http://localhost:16686/api/traces?service=verify-kit&limit=1` with
`httpx.get(..., timeout=2.0)`; swallows `RequestError`/`HTTPStatusError`
and empty-data into `None` (UX-06). `render_trace_waterfall(trace, console)`
sorts spans by `startTime`, builds a Rich Tree, threads children via
`span.references[refType==CHILD_OF]`.

`template/justfile.jinja2` extends from 4 → 8 recipes: `verify-clean` wipes
`.verify/`, `trace-up` docker-runs `jaegertracing/all-in-one:1.76.0` with all
three OTLP ports + UI port, `trace-down` stops the container, `trace *FLAGS`
sets `OTEL_EXPORTER_OTLP_ENDPOINT` and shells to `verify-kit trace`.

`template/pyproject.toml.jinja2` pins the OTel triplet at `==1.41.1`, adds
`httpx>=0.27`, `structlog>=25`, dev extras `hypothesis>=6.100` and
`jsonschema>=4.23`, and points `verify-kit` console_script at
`harness.cli:app_entry`.

## Test coverage

- `tests/test_phase2_core_facade.py` — 9 tests covering Task 1's plan-verify
  subcases (a)–(g), including the two convergence-HIGH guards
- `tests/test_phase2_cli.py` — 8 tests covering Task 2's plan-verify subcases
  (a)–(g) plus an extra (i) for `EXIT_WRITE_FAILED` precedence
- `tests/test_phase2_jaeger_justfile_deps.py` — 6 tests covering Task 3
  subcases (a)–(e)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] Dev venv missing rich/httpx/typer**
- **Found during:** Task 1 first GREEN test run (`test_phase2_reports_json.py` started
  failing with `ModuleNotFoundError: rich`)
- **Issue:** Plan 02-05's `reports/pretty.py` imports `rich`, Plan 02-06's
  `jaeger.py` imports `rich`+`httpx`, and `cli.py` imports `typer`. Tests use
  `sys.path.insert(scratch)` to drive the rendered harness, so the dev venv
  must also have these importable.
- **Fix:** Added `rich>=13`, `httpx>=0.27`, `typer>=0.12` to root
  `pyproject.toml` `[dependency-groups] dev`.
- **Files modified:** `pyproject.toml`
- **Commit:** `0f0124f`

**2. [Rule 1 — Bug] Phase-1 toolchain test forbade Phase-2 recipes**
- **Found during:** Task 3 GREEN, full suite run
- **Issue:** `tests/test_toolchain.py::test_justfile_lists_only_phase_1_recipes`
  explicitly listed `trace-up` in its "forbidden stubs" set. Phase-2 plan 06
  legitimately adds `trace-up` (with a working Jaeger docker container behind
  it — not a stub).
- **Fix:** Updated the test to require Phase-1 + Phase-2 recipes (verify, lint,
  format, shell, verify-clean, trace-up, trace-down, trace) and kept
  smoke/eval/mutation in the forbid list (those have not landed).
- **Files modified:** `tests/test_toolchain.py`
- **Commit:** `8c4637d`

### Authentication Gates

None — entirely local execution. Jaeger docker step is documented as a user
action in the justfile recipe but is not exercised in the automated tests
(those mock `httpx.get`).

## Convergence-HIGH Contract Confirmations

Both critical contracts called out at executor spawn are honored:

**1. CWD CONTRACT — `core.verify(cwd: Path = Path("."))` calls
`load_config(cwd / "pyproject.toml")`, not `load_config()`.**
- File: `template/harness/core.py.jinja2`, lines 69-71 (GREEN commit `0f0124f`)
- Inline rationale comment at lines 64-68
- Regression test:
  `tests/test_phase2_core_facade.py::test_verify_cwd_contract_reads_argument_pyproject`
  (uses `monkeypatch.chdir(tmp_path.parent)` then asserts captured
  `load_config` arg equals `cwd / "pyproject.toml"`)

**2. CACHE EVICTION ORDER — `cache.evict_if_needed` runs BEFORE
`return report`, not after.**
- File: `template/harness/core.py.jinja2`, lines 131-138 (GREEN commit `0f0124f`)
- Inline rationale comment at lines 130-134 ("Placing this AFTER `return report`
  would make the call dead code and the cache cap would never be enforced")
- Regression test:
  `tests/test_phase2_core_facade.py::test_verify_evicts_before_return`
  (mock-patches `CacheStore.evict_if_needed` with autospec and asserts
  `call_count == 1` at the moment `verify()` returns to the test frame)

## Self-Check: PASSED
- `template/harness/core.py.jinja2`: FOUND
- `template/harness/cli.py.jinja2`: FOUND
- `template/harness/__init__.py.jinja2`: FOUND
- `template/harness/jaeger.py.jinja2`: FOUND
- `template/justfile.jinja2`: FOUND
- `template/pyproject.toml.jinja2`: FOUND
- `tests/test_phase2_core_facade.py`: FOUND
- `tests/test_phase2_cli.py`: FOUND
- `tests/test_phase2_jaeger_justfile_deps.py`: FOUND
- Commits `1f53e3f` `0f0124f` `8d8507b` `1fa4006` `212199a` `8c4637d`: FOUND (`git log` verified)
