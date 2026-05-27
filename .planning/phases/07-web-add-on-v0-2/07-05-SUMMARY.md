---
phase: 07-web-add-on-v0-2
plan: "05"
subsystem: web-scaffold
tags: [vitest, playwright, e2e, trace-fixture, testing, web, happy-dom]
dependency_graph:
  requires:
    - "07-03: App.tsx gallery (7 data-lost-pixel-id sections), DarkModeToggle component"
    - "07-04: CORS expose_headers=[traceparent], src/lib/api.ts polarity-aware base URL"
    - "07-02: @ path alias, src/config.ts.jinja2 shim, _CLEAN_ENV polarity helper"
  provides:
    - "template/web/vitest.config.ts: happy-dom env + @ alias parity with vite.config"
    - "template/web/vitest.setup.ts: @testing-library/jest-dom/vitest + cleanup hook"
    - "template/web/src/__tests__/App.test.tsx: gallery heading + 7 sections assertions"
    - "template/web/src/__tests__/DarkModeToggle.test.tsx: dark class flip guard"
    - "template/web/playwright.config.ts.jinja2: chromium-only, vite preview webServer"
    - "template/web/tests/e2e/fixtures/trace.ts: W3C traceparent header injection (no SDK)"
    - "template/web/tests/e2e/smoke.spec.ts: gallery + dark-mode toggle E2E assertions"
    - "tests/test_web_polarity.py: extended with test_web_vitest_and_playwright"
  affects:
    - "template/web/package.json.jinja2 (vitest + @playwright/test devDeps + test scripts)"
    - "template/web/pnpm-lock.yaml (regenerated with testing packages)"
    - "template/web/tsconfig.json (exclude src/__tests__/** from tsc compilation)"
    - "template/web/src/App.tsx (h1 updated to include Component Gallery for test contract)"
tech_stack:
  added:
    - "vitest ^3.2.0 (unit/component test runner)"
    - "@vitest/ui ^3.2.0 (vitest UI mode)"
    - "happy-dom ^17.0.0 (DOM environment for vitest)"
    - "@testing-library/react ^16.1.0 (React component testing)"
    - "@testing-library/jest-dom ^6.6.0 (custom matchers)"
    - "@testing-library/user-event ^14.5.0 (realistic user interactions)"
    - "@playwright/test ^1.60.0 (E2E browser automation, chromium only)"
  patterns:
    - "vitest.config.ts with happy-dom + @ alias parity (Pitfall §4)"
    - "W3C traceparent header injection via Playwright setExtraHTTPHeaders (TRACE-01..03)"
    - "Playwright webServer with vite preview (not vite dev) per architectural decision"
    - "tsconfig.json excludes src/__tests__/** to prevent jest-dom type errors in tsc"
    - "3-tier polarity test: file guards → TRACE-03 → runtime vitest + playwright"
key_files:
  created:
    - "template/{% if has_web %}web{% endif %}/vitest.config.ts"
    - "template/{% if has_web %}web{% endif %}/vitest.setup.ts"
    - "template/{% if has_web %}web{% endif %}/src/__tests__/App.test.tsx"
    - "template/{% if has_web %}web{% endif %}/src/__tests__/DarkModeToggle.test.tsx"
    - "template/{% if has_web %}web{% endif %}/playwright.config.ts.jinja2"
    - "template/{% if has_web %}web{% endif %}/tests/e2e/fixtures/trace.ts"
    - "template/{% if has_web %}web{% endif %}/tests/e2e/smoke.spec.ts"
  modified:
    - "template/{% if has_web %}web{% endif %}/package.json.jinja2"
    - "template/{% if has_web %}web{% endif %}/pnpm-lock.yaml"
    - "template/{% if has_web %}web{% endif %}/tsconfig.json"
    - "template/{% if has_web %}web{% endif %}/src/App.tsx"
    - "tests/test_web_polarity.py"
decisions:
  - "App.tsx h1 updated to include '— Component Gallery' so App.test.tsx can assert /Component Gallery/ on the heading. This is a forward contract — tests verify the gallery title, not just PROJECT_NAME."
  - "App.test.tsx uses getByRole('heading', { level: 1, hidden: true }) because Dialog/Sheet with defaultOpen causes Radix to set aria-hidden on the rest of the DOM. Using hidden: true sees the full DOM tree."
  - "tsconfig.json excludes src/__tests__/**  from tsc --noEmit so @testing-library/jest-dom matchers don't cause TS2339 type errors during pnpm build. Vitest has its own tsconfig resolution via vitest.config.ts."
  - "Playwright config uses vite preview (not vite dev) per ARCHITECTURE.md + 07-RESEARCH.md Pitfall §6 — axe/Lighthouse/Lost Pixel must run against production builds."
  - "TRACE-03 polarity assertion uses regex to detect actual imports (not comments) — trace.ts contains a prohibition comment 'NO @opentelemetry/sdk-trace-web SDK init' which would false-trigger a naive substring check."
requirements: [TEST-W01, TEST-W02, TEST-W03, TRACE-01, TRACE-02, TRACE-03]
metrics:
  duration: ~25m
  completed: "2026-05-27T07:00:49Z"
  tasks_completed: 3
  files_changed: 11
---

# Phase 7 Plan 05: Vitest + Playwright + Trace Fixture Summary

One-liner: Vitest 3 with happy-dom, @testing-library, and `@` alias parity wired for unit tests; Playwright 1.60 with chromium-only smoke spec and a W3C traceparent header-injection fixture (no OTel SDK init, deferred to v0.3) — all guarded by a 12-test polarity suite (observed green, playwright skipped in local run).

## Completed Tasks

| Task | Description | Commit | Key Files |
|------|-------------|--------|-----------|
| 1 | Wire Vitest + happy-dom + 2 component tests | 3869e18 | vitest.config.ts, vitest.setup.ts, App.test.tsx, DarkModeToggle.test.tsx, package.json.jinja2, pnpm-lock.yaml |
| 2 | Wire Playwright + smoke spec + trace fixture | 3666e2b | playwright.config.ts.jinja2, tests/e2e/fixtures/trace.ts, tests/e2e/smoke.spec.ts |
| 3 | Extend polarity test + tsconfig fix | abd58aa | tests/test_web_polarity.py, tsconfig.json |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] App.tsx h1 missing "Component Gallery" text**

- **Found during:** Task 1 vitest verification
- **Issue:** App.test.tsx asserts `getByRole("heading", { level: 1 })` contains `/Component Gallery/` but the h1 in App.tsx was `{PROJECT_NAME}` only (from 07-03). The plan description says the gallery title should be `<h1>{PROJECT_NAME} — Component Gallery</h1>`.
- **Fix:** Updated App.tsx h1 to `{PROJECT_NAME} — Component Gallery`. This is semantically correct (it's the component gallery page) and matches the plan's stated contract.
- **Files modified:** `template/{% if has_web %}web{% endif %}/src/App.tsx`
- **Commit:** 3869e18

**2. [Rule 1 - Bug] App.test.tsx heading query blocked by Dialog aria-hidden**

- **Found during:** Task 1 vitest run in scratch scaffold
- **Issue:** `getByRole("heading", { level: 1 })` returned nothing because Dialog/Sheet with `defaultOpen` causes Radix UI to set `aria-hidden="true"` on the main app DOM. The heading exists but is not accessible by default.
- **Fix:** Updated query to `getByRole("heading", { level: 1, hidden: true })` with comment explaining the Dialog aria-hidden mechanism. The `hidden: true` option makes the query see the full DOM including aria-hidden regions, which is appropriate for unit tests.
- **Files modified:** `template/{% if has_web %}web{% endif %}/src/__tests__/App.test.tsx`
- **Commit:** 3869e18

**3. [Rule 1 - Bug] tsconfig.json included test files in tsc --noEmit compilation**

- **Found during:** Task 3 polarity test run (pnpm build fails in scratch scaffold)
- **Issue:** The `include: ["src"]` in tsconfig.json includes `src/__tests__/` which has `@testing-library/jest-dom` matchers. These matchers aren't typed in the production tsconfig — they're added via vitest.setup.ts for vitest's own compilation. Running `tsc --noEmit` (part of `pnpm build`) fails with `TS2339: Property 'toHaveTextContent' does not exist`.
- **Fix:** Added `exclude` to tsconfig.json to exclude `src/**/__tests__/**` and `*.{test,spec}.{ts,tsx}` patterns. This matches standard practice — test files are compiled by vitest separately with its own tsconfig resolution.
- **Files modified:** `template/{% if has_web %}web{% endif %}/tsconfig.json`
- **Commit:** abd58aa

**4. [Rule 1 - Bug] TRACE-03 polarity assertion naive substring check false-triggered on comment**

- **Found during:** Task 3 first polarity test run
- **Issue:** The plan specified asserting `"@opentelemetry/sdk-trace-web" not in trace_text`. The trace.ts file has a docstring comment: `* NOTE: Header-injection ONLY. NO @opentelemetry/sdk-trace-web SDK init`. This comment containing the package name caused the assertion to fail even though there is no actual import.
- **Fix:** Changed assertion to use `re.search()` matching import/require patterns (`^\s*(import\s|require\s*\()\s*['"]{package-name}['"]`) so only actual imports trigger the guard, not prohibition comments.
- **Files modified:** `tests/test_web_polarity.py`
- **Commit:** abd58aa

## Verification Results

All 12 polarity tests pass (observed, playwright skipped in local run via `VERIFY_KIT_SKIP_PLAYWRIGHT=1`):

```
tests/test_web_polarity.py::test_web_polarity_directory_presence[True]  PASSED
tests/test_web_polarity.py::test_web_polarity_directory_presence[False] PASSED
tests/test_web_polarity.py::test_web_false_no_dotfile_leaks             PASSED
tests/test_web_polarity.py::test_web_false_no_literal_jinja_brace_filenames PASSED
tests/test_web_polarity.py::test_web_true_no_literal_jinja_brace_filenames  PASSED
tests/test_web_polarity.py::test_web_baseline_builds                    PASSED
tests/test_web_polarity.py::test_web_tailwind_shadcn_baseline           PASSED
tests/test_web_polarity.py::test_web_backend_four_combos[False-False]   PASSED
tests/test_web_polarity.py::test_web_backend_four_combos[False-True]    PASSED
tests/test_web_polarity.py::test_web_backend_four_combos[True-False]    PASSED
tests/test_web_polarity.py::test_web_backend_four_combos[True-True]     PASSED
tests/test_web_polarity.py::test_web_vitest_and_playwright              PASSED
12 passed in 136.68s
```

Vitest run observed green in scratch scaffold (3 tests, 2 test files):
```
✓ src/__tests__/DarkModeToggle.test.tsx (1 test) 91ms
✓ src/__tests__/App.test.tsx (2 tests) 182ms
Tests  3 passed (3)
```

Playwright Chromium smoke test: expected to pass — not observed locally due to `VERIFY_KIT_SKIP_PLAYWRIGHT=1`. CI (07-07) will install Chromium and validate. The playwright.config.ts.jinja2 + trace fixture + smoke spec are structurally correct (verified by file-content checks in the polarity test).

## Known Stubs

None — vitest and playwright infrastructure is fully wired. The deferred OTel SDK init (v0.3) is explicitly documented in trace.ts with a prohibition comment and enforced by the TRACE-03 polarity assertion.

## Threat Surface Scan

STRIDE register items from the plan's threat model addressed:

| Flag | File | Description |
|------|------|-------------|
| T-07-15 (crypto.randomBytes) | tests/e2e/fixtures/trace.ts | newTraceparent() uses node:crypto randomBytes for W3C trace + span IDs; format-string assertion in smoke.spec.ts validates structure |
| T-07-17 (DoS, Playwright CI) | playwright.config.ts.jinja2 | workers: CI ? 1 : undefined + timeout: 60_000 on webServer |
| T-07-18 (future SDK re-introduction) | tests/test_web_polarity.py | TRACE-03 polarity assertion catches any future import of @opentelemetry/sdk-trace-web |

No new network endpoints or auth paths introduced beyond what the plan's threat model anticipated.

## Self-Check: PASSED
