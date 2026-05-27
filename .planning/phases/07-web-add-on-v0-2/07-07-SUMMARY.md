---
phase: 07-web-add-on-v0-2
plan: "07"
subsystem: consumer-surface
tags: [justfile, presets, ci-matrix, docs, pre-commit, web, pii-protection]
dependency_graph:
  requires:
    - "07-06: 5 web check IDs in registry (web.vitest, web.playwright, web.lighthouse, web.axe, web.lost_pixel)"
    - "07-06: Lost Pixel adapter + D-W02 Docker image tag"
    - "07-04: web/README.md.jinja2 already authored; not re-authored here"
    - "07-01..07-05: bounded path-shapes + working scaffold"
    - "Phase 6: template-selftest.yml 5-combo matrix (extended, not replaced)"
  provides:
    - "template/justfile.jinja2: 4 web recipes under {% if has_web %}"
    - "template/AGENTS.md.jinja2: 8-point web add-on rules section"
    - "presets/personal.yml: PII-free placeholder template (D-W11)"
    - "presets/oss-minimalist.yml: OSS-default preset"
    - "presets/README.md: 5-section D-W15 documentation"
    - ".gitignore: presets/*.local.yml exclusion (D-W12)"
    - ".pre-commit-config.yaml: check-preset-pii local hook (D-W13)"
    - "scripts/check_preset_pii.sh: email + maintainer-name regex guard"
    - ".github/workflows/preset-schema-check.yml: _schema_version + coverage CI"
    - ".github/workflows/template-selftest.yml: expanded to 6 combos (D-W14)"
    - "tests/test_web_polarity.py: 4 new tests (matrix shape, CLI guard, preset schema, boss test)"
  affects:
    - "tests/test_web_polarity.py (4 new test functions added)"
    - ".github/workflows/template-selftest.yml (5 -> 6 combos)"
    - "template/justfile.jinja2 (4 new recipes)"
    - "template/AGENTS.md.jinja2 (web add-on rules appended)"
tech_stack:
  added:
    - "presets/*.yml: _schema_version convention (D-W11..D-W14)"
    - "pre-commit hook: POSIX sh PII grep (email + configurable maintainer-name regex)"
    - "treosh/lighthouse-ci-action@v12 in CI (Pitfall §10 chrome-version drift)"
    - "pnpm + Playwright caches in CI (Pitfall §10)"
  patterns:
    - "two-file preset convention: personal.yml (public placeholder) + personal.local.yml (gitignored real values)"
    - "three-layer PII protection: gitignore + pre-commit grep + CI schema drift detection"
    - "matrix expansion capped at 6 combos; Lighthouse + Lost Pixel gated to full-stack only (Pitfall §8)"
    - "exact-match --check= flag enumeration in justfile (no web.* glob per core.py:101)"
key_files:
  created:
    - "presets/personal.yml"
    - "presets/oss-minimalist.yml"
    - "presets/README.md"
    - ".pre-commit-config.yaml"
    - "scripts/check_preset_pii.sh"
    - ".github/workflows/preset-schema-check.yml"
  modified:
    - "template/justfile.jinja2 (4 new web recipes under {% if has_web %})"
    - "template/AGENTS.md.jinja2 (web add-on rules section appended)"
    - ".gitignore (presets/*.local.yml added)"
    - ".github/workflows/template-selftest.yml (5 -> 6 combos)"
    - "tests/test_web_polarity.py (4 new test functions)"
decisions:
  - "Lost Pixel run via just verify-web (tier=slow); full-stack combo includes it; other web combos run verify-web-quick in CI (expected fail on lost_pixel without Docker is acceptable)"
  - "Lighthouse CI uses treosh/lighthouse-ci-action@v12 to avoid Chrome version drift (Pitfall §10)"
  - "preset-schema-check.yml skips when: false prompts (project_slug, package_name) — these are auto-derived and should not be in preset files"
  - "boss test gated behind VERIFY_KIT_SKIP_E2E=1 so devs without Node still get green for cheap assertions"
  - "act dry-run not executed in this worktree session — local act dry-run is documented as a manual step; CI will be the first observed run"
metrics:
  duration: ~40m
  completed: "2026-05-27T14:30:00Z"
  tasks_completed: 3
  files_changed: 9
---

# Phase 7 Plan 07: Consumer Surface (Recipes, Presets, CI Matrix, Docs) Summary

One-liner: Four `just verify-web` recipes with exact-match `--check=` enumeration, two public preset files (D-W11) with three-layer PII protection (gitignore + pre-commit grep + CI schema drift), CI matrix expanded 5->6 combos with pnpm/Playwright cache and Lighthouse on full-stack, plus four polarity test extensions guarding matrix shape, CLI surface, and preset schema coverage.

## Completed Tasks

| Task | Description | Commit | Key Files |
|------|-------------|--------|-----------|
| 1 | Justfile web recipes + AGENTS.md web-add-on rules | 495656c | template/justfile.jinja2, template/AGENTS.md.jinja2 |
| 2 | Preset files + .gitignore + pre-commit PII hook + schema-check workflow | 75ce1bb | presets/{personal,oss-minimalist}.yml, presets/README.md, .gitignore, .pre-commit-config.yaml, scripts/check_preset_pii.sh, .github/workflows/preset-schema-check.yml |
| 3 | CI matrix expansion (5->6 combos) + polarity test extensions | 7b6d2c4 | .github/workflows/template-selftest.yml, tests/test_web_polarity.py |

## Exact-Match `--check=<id>` Enumeration Evidence

The `verify-web` recipe (from `template/justfile.jinja2`):

```make
{% if has_web %}
verify-web:
    uv run verify-kit verify --check=web.vitest --check=web.playwright --check=web.lighthouse --check=web.axe --check=web.lost_pixel
```

Each check ID is enumerated explicitly. No `web.*` glob. The CLI's `by_id.get(cid)` at `template/harness/core.py.jinja2:101` would return `None` for a glob pattern and produce a did-you-mean error. This is guarded by `test_web_cli_surface_guard` in the polarity test.

## D-W11..D-W15 Implementation Status

| Decision | Status | Evidence |
|----------|--------|---------|
| D-W11: Two-file preset convention | Implemented | `presets/personal.yml` (placeholder) + pattern for `personal.local.yml` |
| D-W12: `--data-file` invocation | Implemented | Documented in `presets/README.md` + CI base JSON uses it |
| D-W13: Three-layer PII protection | Implemented | `.gitignore` + `scripts/check_preset_pii.sh` + `preset-schema-check.yml` |
| D-W14: CI self-validates public presets | Implemented | CI matrix includes `web` combo; preset schema check runs on every PR |
| D-W15: Preset README with 5 sections | Implemented | `presets/README.md` with all 5 sections |

## `act` Dry-Run Results

`act` was not invoked in this worktree session (no Docker daemon available in this environment). The first observed CI run will validate the 6-combo matrix. The workflow YAML was validated for structural correctness locally:

- `yaml.safe_load(template-selftest.yml)` parsed without error
- `test_web_ci_matrix_shape` confirmed 6 combos, timeout=20, fail-fast=false
- Workflow uses `actions/checkout@v4`, `jdx/mise-action@v4`, `actions/setup-node@v4`, `actions/cache@v4`, `treosh/lighthouse-ci-action@v12` — all pinned to major versions

CI will be the first observed run (expected to fix: not yet observed green).

## Bead `verify-kit-q8t` Resolution

The three design questions behind `verify-kit-q8t` (personal preset defaults vs OSS-minimalist) are now resolved:

1. **Two-file convention** shipped — `personal.yml` (PII-free template) + `oss-minimalist.yml` (OSS defaults).
2. **Local personal preset** pattern documented — `personal.local.yml` gitignored, `--data-file` invocation works.
3. **PII protection** layered — all three layers from D-W13 implemented.

The bead is resolvable.

## Polarity Test Extensions (4 new tests)

Full polarity test suite observed green (VERIFY_KIT_SKIP_E2E=1, 116s):

```
tests/test_web_polarity.py::test_web_polarity_directory_presence[True]   PASSED
tests/test_web_polarity.py::test_web_polarity_directory_presence[False]  PASSED
tests/test_web_polarity.py::test_web_false_no_dotfile_leaks              PASSED
tests/test_web_polarity.py::test_web_false_no_literal_jinja_brace_filenames PASSED
tests/test_web_polarity.py::test_web_true_no_literal_jinja_brace_filenames  PASSED
tests/test_web_polarity.py::test_web_baseline_builds                     PASSED
tests/test_web_polarity.py::test_web_tailwind_shadcn_baseline            PASSED
tests/test_web_polarity.py::test_web_backend_four_combos[False-False]    PASSED
tests/test_web_polarity.py::test_web_backend_four_combos[False-True]     PASSED
tests/test_web_polarity.py::test_web_backend_four_combos[True-False]     PASSED
tests/test_web_polarity.py::test_web_backend_four_combos[True-True]      PASSED
tests/test_web_polarity.py::test_web_vitest_and_playwright               PASSED
tests/test_web_polarity.py::test_web_ci_matrix_shape                     PASSED
tests/test_web_polarity.py::test_web_cli_surface_guard                   PASSED
tests/test_web_polarity.py::test_web_preset_schema_coverage              PASSED
tests/test_web_polarity.py::test_web_verify_web_quick_boss_test          SKIPPED (VERIFY_KIT_SKIP_E2E=1)
tests/test_web_polarity.py::test_web_harness_registry_smoke              PASSED
16 passed, 1 skipped in 116.93s
```

The boss test (`test_web_verify_web_quick_boss_test`) requires Node + full scaffold and is gated behind `VERIFY_KIT_SKIP_E2E=1`. CI will run it without the skip flag.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Preset schema check initially failed on `package_name` / `project_slug`**

- **Found during:** Task 2 — running the preset schema validator locally
- **Issue:** `copier.yml` includes `project_slug` and `package_name` as computed prompts with `when: false` (auto-derived from `project_name`). The initial schema check counted them as required prompt keys and flagged their absence in both presets.
- **Fix:** Updated `preset-schema-check.yml` and the inline test `test_web_preset_schema_coverage` to skip prompts with `when: false`. These are auto-derived values that copier computes internally — they should not appear in preset files.
- **Files modified:** `.github/workflows/preset-schema-check.yml`, `tests/test_web_polarity.py`
- **Commit:** 75ce1bb (detected and fixed inline before commit)

No other auto-deviation rules triggered. All other plan instructions were executed as written.

## Verification Results

Observed green (not predicted):

```
tests/test_web_polarity.py::test_web_ci_matrix_shape PASSED
tests/test_web_polarity.py::test_web_cli_surface_guard PASSED
tests/test_web_polarity.py::test_web_preset_schema_coverage PASSED
3 passed in 0.03s
```

Task 1 verification (manual grep):
- `verify-web:` recipe present in justfile.jinja2: confirmed
- `verify-web-quick:` recipe present: confirmed
- `smoke-web:` recipe present: confirmed
- `web-baseline:` recipe with `mcr.microsoft.com/playwright:v1.60.0-jammy`: confirmed
- No `--check='web.*'` glob: confirmed
- `Web Add-on Agent Rules` section in AGENTS.md.jinja2: confirmed

Task 2 verification:
- `presets/personal.yml` with `_schema_version: "0.2"`: confirmed
- `presets/oss-minimalist.yml` with `_schema_version: "0.2"`: confirmed
- `presets/README.md` with 5 sections: confirmed
- `scripts/check_preset_pii.sh` executable: confirmed
- PII detection test: `real.person@gmail.com` blocked, `you@example.com` allowed: confirmed
- `.gitignore` has `presets/*.local.yml`: confirmed
- `.pre-commit-config.yaml` has `check-preset-pii` hook: confirmed
- `.github/workflows/preset-schema-check.yml` exists: confirmed

## Known Stubs

None — all recipes are implemented, both preset files have real structure, PII hook exits with real detection logic.

## Threat Surface Scan

This plan introduces the preset mechanism which has these security-relevant surfaces:

| Flag | File | Description |
|------|------|-------------|
| T-07-26 (PII leak) | presets/personal.yml | Mitigated: three-layer guard per D-W13 — gitignore + PII grep hook + CI schema check |
| T-07-27 (hook bypass) | .pre-commit-config.yaml | Accepted: `--no-verify` documented in README as bypass; CI doesn't see bypassed local commits until push |
| T-07-28 (supply chain: Lighthouse action) | .github/workflows/template-selftest.yml | Mitigated: pinned to `treosh/lighthouse-ci-action@v12` (major version pin) |
| T-07-30 (DoS: matrix runtime) | .github/workflows/template-selftest.yml | Mitigated: timeout-minutes=20 per combo; fail-fast=false |
| T-07-31 (shell injection in PII script) | scripts/check_preset_pii.sh | Mitigated: script uses grep on file contents, not eval; file paths come from argv, not file contents |
| T-07-32 (schema drift) | .github/workflows/preset-schema-check.yml | Mitigated: asserts 1:1 key coverage on every PR |

No new network endpoints or auth paths introduced.

## Self-Check: PASSED

Files exist:
- [x] `template/justfile.jinja2` — contains `verify-web:` recipe
- [x] `template/AGENTS.md.jinja2` — contains `Web Add-on Agent Rules`
- [x] `presets/personal.yml` — exists with `_schema_version: "0.2"`
- [x] `presets/oss-minimalist.yml` — exists with `_schema_version: "0.2"`
- [x] `presets/README.md` — exists
- [x] `scripts/check_preset_pii.sh` — exists and is executable
- [x] `.pre-commit-config.yaml` — exists with `check-preset-pii` hook
- [x] `.github/workflows/preset-schema-check.yml` — exists
- [x] `.github/workflows/template-selftest.yml` — 6 combos confirmed by test

Commits exist:
- [x] 495656c — feat(web-recipes): add justfile recipes and AGENTS.md web rules
- [x] 75ce1bb — feat(presets): add preset files, PII hook, and schema-check workflow
- [x] 7b6d2c4 — feat(ci-matrix): expand selftest matrix 5->6 combos + polarity guards

Polarity tests observed green (VERIFY_KIT_SKIP_E2E=1):
- [x] test_web_ci_matrix_shape: PASSED
- [x] test_web_cli_surface_guard: PASSED
- [x] test_web_preset_schema_coverage: PASSED
