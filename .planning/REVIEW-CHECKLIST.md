# Plan-Review Checklist (Living Document)

This file accumulates patterns the convergence loop has missed but humans caught during manual review. Each entry adds a one-line check to the next phase's reviewer prompt and to `scripts/check-plan-shapes.sh`.

**Workflow:** any time you fix something manually after `/gsd:plan-review-convergence` exits, add the pattern here. Future reviewer agents are given this file as additional context so they hunt for these specific shapes explicitly.

---

## Patterns to scan for

### 1. Bare relative paths (cwd leak)

A plan that hands an executor a relative path like `Path("node_modules/.bin/biome")` or `load_config()` (defaulting to `Path("pyproject.toml")`) will resolve against process CWD, not against any caller-supplied `cwd` parameter. When the verify command is called from a parent directory, the cache hashes one tree while subprocesses run against another.

- **Look for:** any `Path("<relative>")` in a plan body, any function call that defaults to a relative path
- **Fix shape:** route through the explicit `cwd` argument — `cwd / "node_modules" / ".bin" / "biome"`, `load_config(cwd / "pyproject.toml")`
- **Test shape:** call the function with `cwd=tmp_path` while the test process stands in a different directory; assert the function reads/writes `tmp_path`, not process CWD
- **First caught:** Phase 2 cycles 2–3 (Codex flagged the pattern but the planner re-introduced it during the cycle-2 rewrite). Manual fix applied at `02-04-PLAN.md:177` and `02-06-PLAN.md:152`.

### 2. Statements after `return` (dead code via narrative ordering)

A plan body written in English narrative ("after the report is built, evict old cache entries") may place the cleanup step *after* the return statement when transcribed to code. The executor copies the order literally and the cleanup never runs.

- **Look for:** any plan body where a `return X` line is followed by additional action steps, especially the words "after", "before returning", "once X is done"
- **Fix shape:** rewrite as `result = X; <cleanup>; return result`
- **Test shape:** spy/mock the cleanup function; assert it was called *and* the call frame is inside the function under test (not from an `atexit` or post-return hook)
- **First caught:** Phase 2 cycle 3, `02-06-PLAN.md:159-161` — cache eviction described after `return VerifyReport.from_checks(...)`.

### 3. Cross-plan contract drift (test plan asserts shapes that don't match the producer plan)

When a phase has a test/integration plan (e.g., 03-05) that asserts contracts on outputs produced by other plans (e.g., Ralph results from 03-02, fix_propose envelope from 03-01, CLI command names already implemented in earlier phases), the test plan can drift from the producer plan during late-cycle replans. The replan may rename fields, invent new ones, or reference a CLI command name that doesn't exist. Each producer plan looks fine in isolation; each test assertion looks reasonable in isolation; only when you read them side-by-side do the contracts disagree.

- **Look for:** test/assertion plans that reference field names, return shapes, or CLI command names that should be sourced from another plan. Trace each asserted name back to its producer plan and confirm exact match (field-by-field, name-by-name).
- **Fix shape:** quote the producer plan's signature directly in the test plan ("per Plan 03-02 T05's `harness.ralph.run` return shape: `{status, iters, cost_usd, output_path}`"); pick one schema, make every plan reference that schema by file:line.
- **Test shape:** add a meta-test that imports the producer's actual type/dict-schema and uses it to validate the integration test's assertions, so a producer-side rename forces a test-side rename at type-check time. For CLI names, integration tests should invoke through the actual Typer app catalog, not hardcoded subcommand strings.
- **First caught:** Phase 3 cycle 3 — 03-05 asserted Ralph result fields `iters_completed`/`stop_reason`/`last_iter_at`/`total_iters` that didn't exist (real names per 03-02 are `status`/`iters`/`cost_usd`/`output_path`); 03-05 used CLI `verify-kit trace-last` when 03-RESEARCH + Phase 2 reality use `verify-kit trace --last`; 03-05 demanded a full SARIF envelope while 03-01 said "SARIF findings list" (ambiguous). All three landed in 03-05 during cycle-2 replan and were caught by cycle-3 review.

### 4. Plan API-surface drift (plan invents names that don't match the producing codebase)

Distinct from §3 cross-plan drift: this one is **plan vs. landed-codebase drift**. A plan describes calling `@register_check` / `CheckSeverity.ERROR` / `CheckResult(ok=False)` / `verify-kit verify --only=backend` — but the actual harness package shipped in an earlier phase uses `@register` / `CheckResult(status=..., envelope=ErrorEnvelope(...))` / `--check=backend`. The plan looks coherent because the invented names sound right, but the executor stalls on the first import. The convergence loop can't catch this because it reads only plan files, not the source.

- **Look for:** in plan bodies, decorator names (`@register_check`, `@register`, `@check`), result-class field names (`ok`, `status`, `pass`, `failed`), CLI flag names (`--only`, `--check`, `--skip`, `--filter`), and registry/module paths (`harness/registry.py`, `harness/checks/__init__.py`). For every such symbol, grep the actual codebase: `rg -n '<symbol_name>' template/harness/ harness/`. If the plan's spelling doesn't match what's there, it's drift.
- **Fix shape:** before plan-review-convergence runs on any phase that consumes a previously-landed API, run the API extraction step: `rg -n 'def (register|check|verify)' template/harness/checks/__init__.py template/harness/registry.py.jinja2 2>/dev/null` and inject the actual function/class signatures into the plan as a "Producer API surface (frozen)" block. Plan must reference those exact names.
- **Test shape:** in the executor flow, run `python -c "from app.cli import app; app(['--help'])"` (or equivalent) as a smoke check before declaring T01 done — proves the registered names exist. For CLI flags, parametrize the test over the actual flag strings: `pytest.mark.parametrize("flag", ["--check", "--skip"])` and let the test break loudly if a non-existent flag is asserted.
- **First caught:** Phase 4 cycle 2/3 didn't catch — landed during execute-phase. Plan 04-04 invented Ralph stub protocol (`executor=stub_executor` returning `{"status":"continue"}` when real API is `_spawn=stub_spawn` returning `{"done":bool,"cost_usd":float}` with required `prompt` parameter). Plan 04-07 invented `@register_check`/`CheckSeverity`/`CheckResult(ok=)`/`--only=backend` (real names: `@register`/`CheckResult(status=)/ErrorEnvelope`/`--check=backend`) and `registry.py.jinja2` as the registration site (real site: `harness/checks/__init__.py.jinja2`). Both auto-fixed by executors but cost ~10–15 min each to discover and adapt.

### 5. Inline Jinja conditionals in YAML break line boundaries

`{% if has_db %}DATABASE_URL: postgresql://...{% endif %}` written on a single line inside a YAML template can cause adjacent lines to merge when Jinja renders the conditional empty. The rendered output becomes `<previous-line><next-line>` with no separator and YAML parsing fails — or worse, parses silently into the wrong structure.

- **Look for:** in `.jinja2` templates whose output is YAML / TOML / structured text, any `{% if … %}<inline content>{% endif %}` where the inline content contains a key:value pair, a list item, or a service block.
- **Fix shape:** put the `{% if %}` and `{% endif %}` on their own lines so the conditional spans a block, not a fragment of a line. The closing `{% endif %}` should appear before the next sibling content.
- **Test shape:** polarity tests that render the template in BOTH polarities and parse the output with the appropriate parser (e.g., `yaml.safe_load`, `docker compose config -q`). Asserting "key not in output" alone is insufficient — parse + structural assertion is required.
- **First caught:** Phase 4 plan 04-05 execute-time — docker-compose `DATABASE_URL: ...` merged with adjacent `depends_on:` block when `has_db=false`.

### 6. Meta-comments inside template files render to consumer output

Explanatory comments authored *inside* a `.jinja2` template ("cycle-3 sweep: this block was added to address Codex HIGH #X") render literally into the consumer's project. The consumer then ships a docker-compose.yml or pyproject.toml with executor-process commentary baked in. Worse: such comments can defeat polarity tests by containing forbidden tokens (`"postgres"` referenced in a comment shows up in `has_db=false` output and trips `"postgres" not in compose_text` assertions).

- **Look for:** in plan bodies (and the resulting template files), any block that reads like "cycle-N sweep:", "per Codex HIGH #X", "REPLAN NOTE:", or anything that's clearly authored-for-the-reviewer rather than authored-for-the-user. These belong in the plan file, NOT the template.
- **Fix shape:** strip meta-comments from templates entirely. Authored explanations live in the PLAN.md / SUMMARY.md / git commit body. Templates emit only user-facing content.
- **Test shape:** for templates rendered as docker-compose / pyproject / settings files, polarity tests should assert `<flag-specific-token> not in <opposite-polarity-output>` for every gated flag, and assert the file parses cleanly.
- **First caught:** Phase 4 plan 04-05 execute-time — meta-comments mentioning "postgres" rendered into both polarities, breaking the polarity test until stripped.

### 7. Test files inside a path the harness recursively invokes

Tests at `tests/backend/test_X.py` are run by `pytest tests/backend/`. If the test itself calls the harness (`verify-kit verify --check=backend`), and the harness implementation walks `pytest tests/backend/` to run the check, you get **infinite recursion**. The test passes once locally (terminates by timeout) but hangs CI or scratch renders.

- **Look for:** in plan bodies, any test file under a directory the production harness uses as a pytest target. Cross-check the producer plan's pytest-invocation paths against the asserter plan's test-file locations.
- **Fix shape:** put forcing-function / umbrella tests that exercise the production harness at the top-level `tests/` (or another out-of-band location), NOT inside the directory the harness pytest-invokes. If the harness uses `tests/backend/` as its target, the umbrella test belongs at `tests/test_umbrella_includes_backend.py`.
- **Test shape:** parametrize the umbrella test over harness invocation paths, and use a recursion guard env var (`VERIFY_KIT_RECURSION_GUARD=1` set during the harness's pytest call) so the umbrella test self-excludes.
- **First caught:** Phase 4 plan 04-07 execute-time — `tests/backend/test_verify_umbrella_includes_backend.py` recursed; moved to `tests/test_verify_umbrella_includes_backend.py`.

### 8. Outer-process VIRTUAL_ENV / env leak into subprocess calls to scratch projects

When a polarity test renders a scratch scaffold to `tmp_path` and runs `uv sync` / `pytest` / `just verify` inside it via `subprocess.run`, the outer test runner's `VIRTUAL_ENV` (and `PATH`, `PYTHONPATH`, `UV_PROJECT_ENVIRONMENT`) leaks into the subprocess by default. The subprocess then resolves binaries / Python modules against the outer venv, not the scratch project's own, producing false passes or confusing import errors.

- **Look for:** in plan bodies, any `subprocess.run(...)` invocation that targets a scratch project but does not explicitly pass `env=<clean_env>`. Especially `subprocess.run([..., "uv", "sync", ...], cwd=tmp_path)` with no env scrubbing.
- **Fix shape:** define a `_CLEAN_ENV` / `_scratch_env()` helper that strips outer-process vars before calling subprocess. At minimum drop: `VIRTUAL_ENV`, `UV_PROJECT_ENVIRONMENT`, `PYTHONPATH`, and a curated set of `PYTHON*` vars. Pass the cleaned env via `env=` to every subprocess targeting a scratch project.
- **Test shape:** add a meta-test that runs `uv sync` in a scratch scaffold while the outer process has `VIRTUAL_ENV=/some/wrong/path` set, then asserts the resulting scratch venv lives under `tmp_path` (not under the outer VIRTUAL_ENV target).
- **First caught:** Phase 4 plan 04-07 execute-time — scratch `uv sync` was resolving the outer feat/phase-4-backend venv. Manual fix added `_CLEAN_ENV` helpers.

---

## How this file is used

`/gsd:plan-review-convergence` will (once the orchestrator picks up this convention) include this file's contents in the reviewer prompt so Codex explicitly hunts for each pattern. Until that's automated, the project-local protocol is:

1. After `/gsd:plan-review-convergence` exits, run `bash .planning/scripts/check-plan-shapes.sh <phase>` to grep for the patterns above.
2. After any manual fix, add a new entry here with the same four fields (Look for / Fix shape / Test shape / First caught).
