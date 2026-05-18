---
phase: 02-universal-harness-core
plan: "07"
subsystem: harness
tags: [tests, harn-07, obs-01-gate, tool-05-gate, ux-08-gate, obs-05-docs, hypothesis, golden-snapshot]
requires: ["02-01", "02-02", "02-03", "02-04", "02-05", "02-06"]
provides:
  - "template/tests/: 4-subdir templated test scaffold (smoke, golden, properties, fixtures) for rendered projects"
  - "tests/test_phase2_otel_inert.py: OBS-01 import-time gate (zero opentelemetry.* on stderr with endpoint unset)"
  - "tests/test_phase2_cache_budget.py: TOOL-05 <500ms cache-hit gate (hard internal + soft wall-clock)"
  - "tests/test_phase2_first_run_30s.py: UX-08 <30s first-run gate"
  - "template/README.md: OBS-05 Observability + Verifying-Changes sections"
  - "tests/_helpers.venv_python(): explicit interpreter for scratch project subprocess calls"
affects:
  - "tests/_helpers.install_scratch_harness now creates an isolated `.venv` via `uv venv --python 3.13` (was: shared host venv, broken for 3.13-pinned scratch)"
  - "pyproject.toml: registers `requires_network` pytest marker"
tech-stack:
  added: []
  patterns:
    - "shape-only golden snapshot (resilient to timing drift and pass/skip degradation)"
    - "two-tier perf gate: hard internal `duration_ms` + soft advisory wall-clock"
    - "scratch-project venv isolation via `uv venv --python 3.13`"
key-files:
  created:
    - "template/tests/conftest.py.jinja2"
    - "template/tests/smoke/test_verify_smoke.py.jinja2"
    - "template/tests/golden/test_json_output.py.jinja2"
    - "template/tests/golden/snapshots/report_pass.json.jinja2"
    - "template/tests/properties/test_check_result_serde.py.jinja2"
    - "template/tests/fixtures/fake_project/pyproject.toml.jinja2"
    - "template/tests/fixtures/fake_project/.mise.toml.jinja2"
    - "tests/test_phase2_otel_inert.py"
    - "tests/test_phase2_cache_budget.py"
    - "tests/test_phase2_first_run_30s.py"
    - ".planning/phases/02-universal-harness-core/02-07-SUMMARY.md"
  modified:
    - "template/README.md.jinja2 (+ Verifying-Changes, + Observability sections)"
    - "tests/_helpers.py (install_scratch_harness now creates isolated 3.13 venv; new venv_python helper)"
    - "pyproject.toml (register `requires_network` marker)"
decisions:
  - "Shape-only golden snapshot comparison — keys + format_version + check_id set + status ⊆ {pass, skip}; tolerates duration_ms drift and `just`-missing degradation (review HIGH-3)."
  - "Golden test runs against PROJECT_ROOT (the rendered scaffold root), NOT the minimal fake_project fixture — the fixture lacks the verify-kit console script (review carryover HIGH-3 from CONTEXT.md)."
  - "fake_project fixture is documented as a UNIT-test fixture only (minimal pyproject root for config/cache loaders); end-to-end smoke/golden tests use shutil.copytree of the rendered tree or run against PROJECT_ROOT."
  - "Two-tier cache gate (review HIGH-4): hard `report.summary.duration_ms < 500` (always enforced); soft subprocess wall-clock < 1500ms (warning-only unless VERIFY_KIT_STRICT_WALL_CLOCK=1). `uv run` cold-imports alone can blow the wall budget on slow CI."
  - "Shared _helpers.install_scratch_harness upgraded to provision its own `.venv` via `uv venv --python 3.13` — the verify-kit repo runs on 3.11+ but scratch projects pin 3.13. Without this, every scratch-based subprocess test failed with `requires-python ≥ 3.13`."
  - "@pytest.mark.slow + RUN_SLOW_TESTS=1 gate preserved from Phase 1 for all subprocess-heavy tests; first-run test additionally tagged @pytest.mark.requires_network (PyPI on first install)."
  - "README extension (vs. standalone OBSERVABILITY.md): keeps a single-file scaffold readable for solo devs per PROJECT.md UX-05; users land on README and immediately see the trace workflow."
metrics:
  duration_minutes: 22
  completed: "2026-05-18"
  tasks: 3
  commits: 3
---

# Phase 2 Plan 07: HARN-07 + OBS-01/TOOL-05/UX-08 Gates + OBS-05 Docs Summary

Final Phase-2 plan: shipped the HARN-07 templated test scaffold (7 files
under `template/tests/`) so every rendered scaffold gets `smoke/`, `golden/`,
`properties/`, and `fixtures/` test trees out of the box; wired the three
hardest non-functional gates as tests in verify-kit's OWN repo (OBS-01
import-time inertness, TOOL-05 <500ms cache hit, UX-08 30-second first run);
and extended the scaffolded README with the OBS-05 Observability + Verifying-
Changes sections.

## What got built

### Task 1 — HARN-07 templated test scaffold (7 files)

Lives under `template/tests/`; Copier renders these into every new scaffold:

- `conftest.py` — shared fixtures. `tmp_project` provides a minimal pyproject
  root for unit tests of config/cache loaders (it is **not** a harness host).
  Autouse `_structlog_reset` calls `structlog.reset_defaults()` per RESEARCH.md
  §11 mitigation R4 so `cache_logger_on_first_use=True` doesn't leak config
  across tests.
- `smoke/test_verify_smoke.py` — copies the rendered scaffold's `pyproject.toml`,
  `.mise.toml`, `justfile`, and `harness/` into `tmp_path`, then runs
  `uv run verify-kit verify --quick` there. Asserts exit 0 and that
  `.verify/report.json` was written. Gated by `@pytest.mark.slow` +
  `RUN_SLOW_TESTS=1`.
- `golden/test_json_output.py` — runs `verify-kit verify --quick --format=json`
  against `PROJECT_ROOT = Path(__file__).resolve().parents[2]` (the rendered
  scaffold root, **not** `fake_project`). Snapshot comparison is shape-only:
  top-level keys, summary keys, `format_version`, the set of `check_id`s, and
  `status ⊆ {pass, skip}`. Bootstraps on first run; to update an existing
  snapshot, delete and re-run.
- `golden/snapshots/report_pass.json` — literal JSON snapshot (mise pass, copier
  skip, just-list pass). `duration_ms=0` placeholder; shape comparison ignores
  it.
- `properties/test_check_result_serde.py` — Hypothesis `model_dump_json →
  model_validate_json` round-trip per RESEARCH.md §10, `@settings(max_examples=200)`
  per R8 mitigation. Verified passing on rendered scratch.
- `fixtures/fake_project/{pyproject.toml,.mise.toml}` — the minimal pyproject
  root for unit-test fixtures.

### Task 2 — Verify-kit's own-repo gates (3 tests)

These live in `tests/` and validate the *template*, not the rendered project:

- `test_phase2_otel_inert.py` — implements CONTEXT.md Decision 3.1's
  verification clause. Renders + installs a scratch project, then runs
  `python -X importtime -c "import harness.observability"` with
  `OTEL_EXPORTER_OTLP_ENDPOINT` cleared from the env. Asserts zero
  `opentelemetry.*` and zero `grpc.` lines on stderr.
- `test_phase2_cache_budget.py` — TOOL-05 two-tier gate. Hard
  (always-enforced): `report.summary.duration_ms < 500`. Soft (advisory,
  warning-only unless `VERIFY_KIT_STRICT_WALL_CLOCK=1`): subprocess wall
  clock < 1500ms. A second test (`test_failed_check_is_also_cached`)
  corrupts `.mise.toml`, runs twice, and asserts the failing check is
  cached on the second run (Decision 2.3).
- `test_phase2_first_run_30s.py` — UX-08 end-to-end. Times `copier copy →
  install → just verify --quick` and asserts wall clock < 30.0s.
  `@pytest.mark.requires_network` registered for the first-install PyPI fetch.

All three tests reuse `tests/_helpers.py` per review HIGH-2 (single render
path). Verified locally: 4/4 tests pass under `RUN_SLOW_TESTS=1` in ~20.6s.

#### Helper changes (Rule 3 — blocking infrastructure)

`tests/_helpers.install_scratch_harness` previously did
`uv pip install -e .` reusing the verify-kit host venv (Python 3.12 in this
worktree). Scratch projects pin Python 3.13 via `template/pyproject.toml`,
so every scratch-install failed with `requires-python ≥ 3.13`. Fixed by
creating an isolated `.venv` per scratch via `uv venv --python 3.13` then
installing with `VIRTUAL_ENV` pointed at the new venv. New `venv_python()`
helper returns the explicit interpreter path; OTel and cache tests call it
directly rather than `uv run` to avoid a redundant re-sync on every
subprocess.

### Task 3 — README OBS-05 extension

`template/README.md.jinja2` gains two sections before the License footer:

- **Verifying Changes** — flag reference (`--quick`, `--full`, `--no-cache`,
  `verify-clean`), output format matrix, JSONL `type == "summary"` end-of-
  stream contract, did-you-mean, graceful-degradation rules (`just-list`
  skips when `just` is missing; biome checks skip when biome is missing),
  and the full exit-code table including `EXIT_WRITE_FAILED=12 > EXIT_CHECK_FAIL=1`
  precedence (review MEDIUM-6).
- **Observability** — "inert by default" guarantee with reference to
  `tests/test_phase2_otel_inert.py`, the `just trace-up` / `just trace --last`
  workflow with Jaeger UI at <http://localhost:16686>, three non-Docker
  alternatives (otel-desktop-viewer, otel-tui, Grafana Tempo) per RESEARCH.md
  §9, and a minimal `docker-compose.observability.yml` snippet for teams.
  Conditional `{% if has_backend %}` footer notes that the Backend addon
  reuses the same Jaeger endpoint.

Verified: rendered scratch project's README contains 6 of the required
markers (plan-required ≥4).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocker] `install_scratch_harness` failed under Python 3.13 mismatch**

- **Found during:** Task 2 (otel_inert test)
- **Issue:** `tests/_helpers.install_scratch_harness` ran `uv pip install -e .`
  inside the verify-kit worktree's host venv (Python 3.12.9 on this machine),
  but scratch projects render with `requires-python = ">=3.13"`. Every
  scratch-based subprocess test failed with "Because the current Python
  version (3.12.9) does not satisfy Python>=3.13 ...".
- **Fix:** `install_scratch_harness` now creates an isolated `.venv` inside
  the scratch tree via `uv venv --python 3.13`, then installs with
  `VIRTUAL_ENV` set. This mirrors the proven pattern from the pre-existing
  `tests/test_phase2_observability.py::installed_scratch` fixture. New
  `venv_python(scratch)` helper exported so tests can call the explicit
  interpreter (avoids `uv run`'s re-sync overhead on each subprocess).
- **Files modified:** `tests/_helpers.py`
- **Commit:** `4f0aab5`

**2. [Rule 2 - Critical] Missing `requires_network` pytest marker registration**

- **Found during:** Task 2 (writing test_phase2_first_run_30s.py)
- **Issue:** The 30-second test is plan-tagged `@pytest.mark.requires_network`,
  but `pyproject.toml`'s `[tool.pytest.ini_options].markers` only registered
  `slow`. Unregistered markers print a warning under strict mode and obscure
  intentional filtering.
- **Fix:** Added `requires_network: test requires network access (e.g. PyPI
  fetch on first install)` to the marker list.
- **Files modified:** `pyproject.toml`
- **Commit:** `4f0aab5`

### Architectural Changes

None. Plan executed as specified.

### Path-Discipline Deviation (Process)

On the first Task-1 Write calls, files were written to the **main repo**
(`/Users/moiz/Documents/code/verify-kit/template/tests/`) instead of the
worktree (`/Users/moiz/Documents/code/verify-kit/.claude/worktrees/
agent-addb70f0b623da32e/template/tests/`). The Write tool's absolute paths
resolved to the orchestrator's `pwd`, not the worktree. Detected immediately
(rendered scratch had no `tests/` tree); recovered by `mv`-ing the entire
`template/tests/` subtree into the worktree. No data loss; no main-repo
commit was created. Subsequent writes used absolute paths with the worktree
root prefix or relative paths, verified by `git status` showing the staged
files.

## Self-Check: PASSED

Verified all created files exist in worktree and all 3 commits land on the
worktree branch:

- `template/tests/conftest.py.jinja2` — FOUND
- `template/tests/smoke/test_verify_smoke.py.jinja2` — FOUND
- `template/tests/golden/test_json_output.py.jinja2` — FOUND
- `template/tests/golden/snapshots/report_pass.json.jinja2` — FOUND
- `template/tests/properties/test_check_result_serde.py.jinja2` — FOUND
- `template/tests/fixtures/fake_project/pyproject.toml.jinja2` — FOUND
- `template/tests/fixtures/fake_project/.mise.toml.jinja2` — FOUND
- `tests/test_phase2_otel_inert.py` — FOUND
- `tests/test_phase2_cache_budget.py` — FOUND
- `tests/test_phase2_first_run_30s.py` — FOUND
- Commit `d1f76a7` (HARN-07 scaffold) — FOUND
- Commit `4f0aab5` (3 gate tests + helper fix) — FOUND
- Commit `524cb5f` (README OBS-05) — FOUND

Empirical verification: `RUN_SLOW_TESTS=1 uv run pytest tests/test_phase2_otel_inert.py tests/test_phase2_cache_budget.py tests/test_phase2_first_run_30s.py` passes 4/4 in 20.61s.

Rendered scratch project: README contains 6 OBS-05 markers (otel-desktop-viewer, otel-tui, docker-compose.observability, just trace-up — required ≥4).

Golden test: confirmed to run against `PROJECT_ROOT = Path(__file__).resolve().parents[2]` (the rendered scaffold root) — NOT against `fake_project`.
