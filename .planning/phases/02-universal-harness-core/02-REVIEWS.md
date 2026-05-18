---
phase: 2
cycle: 2
reviewers: [codex]
reviewed_at: 2026-05-18T14:01:07Z
plans_reviewed:
  - 02-01-PLAN.md
  - 02-02-PLAN.md
  - 02-03-PLAN.md
  - 02-04-PLAN.md
  - 02-05-PLAN.md
  - 02-06-PLAN.md
  - 02-07-PLAN.md
prior_cycle_highs: 5
current_cycle_highs_unresolved: 4
---

# Cross-AI Plan Review — Phase 2 (Cycle 2)

This is cycle 2 of plan-review-convergence. Cycle 1 raised 5 HIGH concerns;
the plans were replanned per `02-REVIEWS-RESPONSE.md`. This cycle re-reviews
the updated plans.

## Codex Review

### Summary

The updated plans resolve most of the cycle-1 HIGH issues. The dependency
ordering, `just` degradation, cache-budget split, and local-only Biome
strategy are materially improved. Two of the original five are only
partially resolved because the plans still contain executor-visible
contradictions or missing file/dependency declarations.

The biggest new risk is in the generated test scaffold: some templated
tests run `verify-kit` from a minimal `fake_project` that does not contain
or install the harness package. That will likely fail in rendered projects.

### Status of Prior HIGH Concerns

1. **Plan 04 missing `02-03` dependency: FULLY RESOLVED**

   Evidence: `02-04-PLAN.md` now has `depends_on: ["02-01", "02-02", "02-03"]`,
   `wave: 3`. The runner explicitly imports `CacheStore`, `make_cache_key`,
   `hash_inputs`, and `get_tool_version` from Plan 03.

2. **Rendered-project helpers may not exist: PARTIALLY RESOLVED**

   Resolution: `02-01-PLAN.md` adds `tests/_helpers.py` and `tests/conftest.py`
   with `render_scratch_project`, `install_scratch_harness`,
   `render_and_install`. Later plans consume these helpers.

   Remaining gap: Plan 01 says to add `copier` to verify-kit's own dev
   dependencies "if absent," but the owning `pyproject.toml` is not listed in
   `files_modified`. Test files `tests/test_phase2_helpers_smoke.py`,
   `tests/test_phase2_models.py`, etc., are not listed in Plan 01 frontmatter.
   The helper infrastructure is planned, but the execution manifest is
   incomplete.

3. **`verify --quick` hard-requires `just`: FULLY RESOLVED**

   Evidence: `02-04-PLAN.md` registers `just-list.renders` with
   `tool="just", skip_if_unavailable=True`; check returns `skip` with a hint
   on `FileNotFoundError`. Plan 07 documents the Makefile shim and
   non-failure behavior.

4. **`<500ms` cache-hit test measured via `uv run` subprocess: FULLY RESOLVED (minor wording caveat)**

   Evidence: `02-07-PLAN.md` splits the budget:
   - hard gate: `report.summary.duration_ms < 500`
   - soft gate: subprocess wall time `<1500ms`, strict only when
     `VERIFY_KIT_STRICT_WALL_CLOCK=1`

   Caveat: must-haves still say "2nd run completes in <500ms" which could be
   misread as wall-clock. Tighten must-have wording.

5. **Biome via `pnpm dlx` violates offline-first UX: PARTIALLY RESOLVED**

   Resolution: Plan 04 task action removes `pnpm dlx` and resolves Biome via
   `node_modules/.bin/biome` → `shutil.which("biome")` → skip.

   Remaining issue: Plan 04's threat model is stale — still references
   "pnpm dlx downloads from npm registry," `T-02-13` "Supply chain via
   pnpm dlx," and "README to call out that biome runs via pnpm dlx." This
   contradicts the implementation instructions.

### New Concerns

- **HIGH: Generated golden test runs `verify-kit` from a non-harness fake project.**

  In `02-07-PLAN.md`, `template/tests/golden/test_json_output.py.jinja2`
  runs `verify-kit verify --quick --format=json` in `tmp_project` copied
  from `tests/fixtures/fake_project`. That fixture's `pyproject.toml` only
  declares `name = "fake-fixture-project"` — no `harness/`,
  `[project.scripts] verify-kit`, or deps. The smoke test was corrected but
  the golden test still appears broken.

- **HIGH: `cwd` is passed through runner/cache but checks execute relative to process CWD.**

  `run_check(spec, cwd=...)` hashes inputs using `cwd` but calls `spec.fn()`
  without `cwd`. Check functions use relative paths and `subprocess.run(...)`
  without `cwd=cwd`. `core.verify(cwd=some_path)` can hash one project and
  execute checks against another. CLI works because process CWD is the
  project, but the public API and tests are inconsistent.

- **MEDIUM: SARIF still ignores new file/line/column fields.**

  Plan 01 adds `ErrorEnvelope.file/line/column/snippet` and Plan 04 says
  Ruff/Biome populate them, but Plan 05's SARIF emitter still emits
  `"artifactLocation": {"uri": "."}`. Clickable Problems-panel goal
  remains only partially served.

- **MEDIUM: Config plan drifts from locked context example.**

  Context shows `[tool.verify-kit.checks.lint.ruff]`. Plan 03 now requires
  `[tool.verify-kit.checks."lint.ruff"]`. If intentional, update
  `02-CONTEXT.md` or mark it as a deliberate correction.

- **MEDIUM: Truth/action contradictions remain.**

  - Plan 05 behavior says `otlp.emit` flushes via `shutdown()`; action says
    use `force_flush()`.
  - Plan 06 must-have says `describe` uses `CheckSpec` / `TypeAdapter`;
    action correctly uses `CheckCatalogEntry`.
  - Plan 05 behavior says CI uses `force_terminal=False`; action says
    `force_terminal=True` with `no_color=True`.

- **LOW: Plan 01 helper default answers are underspecified.**

  `_DEFAULT_ANSWERS` should mirror Phase-1 `copier.yml`, then introspect and
  fill missing defaults with `_`. Vague enough to produce brittle Copier
  helper behavior. Prefer reading actual question names and only supplying
  known answers.

### Suggestions

- Fix `template/tests/golden/test_json_output.py.jinja2` to run from the
  rendered scaffold root, or copy the full harness host into `tmp_path` as
  the smoke test does.
- Make checks cwd-aware. Pass `cwd` into check functions or wrap `spec.fn()`
  in a `chdir(cwd)` context. Pass `cwd=cwd` to every `subprocess.run`.
- Update SARIF emitter to use `ErrorEnvelope.file`, `line`, `column` when
  present; keep `"."` only as fallback.
- Remove all stale `pnpm dlx` references from Plan 04's threat model.
- Align contradictory must-have/action text around `force_flush`,
  `CheckCatalogEntry`, and CI console behavior.
- Add root `pyproject.toml` to Plan 01 `files_modified` if it may add
  `copier` to verify-kit's own dev dependencies. List new
  `tests/test_phase2_*.py` files in Plan 01 frontmatter.

### Risk Assessment

**MEDIUM.** The original HIGH concerns are mostly addressed and phase
architecture is sound. Remaining risk is execution ambiguity: a broken
generated golden test, cwd mismatch between cache and checks, stale Biome
threat-model text, and a few contradictory instructions. These are fixable
before execution without changing the core design.

---

## Consensus Summary

Single reviewer this cycle (codex), so "consensus" reflects codex's
synthesis against the cycle-1 baseline.

### Cycle-1 → Cycle-2 HIGH resolution

| # | Cycle-1 HIGH | Cycle-2 status |
|---|---|---|
| 1 | Plan 04 missing `02-03` dependency | FULLY RESOLVED |
| 2 | Rendered-project helpers may not exist | PARTIALLY RESOLVED |
| 3 | `verify --quick` hard-requires `just` | FULLY RESOLVED |
| 4 | `<500ms` cache-hit test via `uv run` subprocess | FULLY RESOLVED |
| 5 | Biome via `pnpm dlx` violates offline-first UX | PARTIALLY RESOLVED |

### Current HIGH Concerns (unresolved, count = 4)

1. **[Carryover #2 — PARTIAL]** Plan 01 execution manifest incomplete:
   missing `pyproject.toml` and several `tests/test_phase2_*.py` in
   `files_modified`.
2. **[Carryover #5 — PARTIAL]** Plan 04 threat model still references
   `pnpm dlx` despite implementation removing it; executor-visible
   contradiction.
3. **[NEW]** Generated golden test
   `template/tests/golden/test_json_output.py.jinja2` runs `verify-kit`
   inside `fake_project`, which does not install the harness.
4. **[NEW]** `cwd` flows into `run_check` for hashing but checks execute
   against process CWD; public API and tests are inconsistent.

### Recommendation

Run one more replan cycle to address the 4 unresolved HIGHs before
execution. All four are surgical fixes — no architectural rework needed.
