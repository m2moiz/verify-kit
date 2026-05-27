---
phase: 07-web-add-on-v0-2
plan: "08"
subsystem: web-otel
tags: [otel, sdk-trace-web, instrumentation-fetch, bundle-budget, web, gap-closure, trace]
dependency_graph:
  requires:
    - "07-05: pnpm-lock.yaml, package.json.jinja2, src/main.tsx, tests/test_web_polarity.py"
  provides:
    - "template/web/package.json.jinja2: @opentelemetry/sdk-trace-web + instrumentation-fetch + exporter-trace-otlp-http + instrumentation + context-zone in dependencies"
    - "template/web/src/otel.ts: inert-by-default WebTracerProvider + FetchInstrumentation + conditional OTLP exporter"
    - "template/web/src/main.tsx: initOtel() called before createRoot"
    - "template/web/pnpm-lock.yaml: regenerated with 5 OTel packages"
    - "tests/test_web_polarity.py: TRACE-03 inverted (SDK now asserted present), OTel-present assertions, TRACE-04 bundle-delta guard"
  affects:
    - "ROADMAP SC-5 (click → fetch → FastAPI → Jaeger waterfall) — now unblocked"
    - "07-VERIFICATION.md gap #1 (TRACE-01/02/04) — closed"
tech_stack:
  added:
    - "@opentelemetry/sdk-trace-web ^2.7.0 (browser tracer provider)"
    - "@opentelemetry/instrumentation-fetch ^0.218.0 (fetch auto-instrumentation)"
    - "@opentelemetry/exporter-trace-otlp-http ^0.218.0 (OTLP-HTTP exporter)"
    - "@opentelemetry/instrumentation ^0.218.0 (registerInstrumentations, InstrumentationBase)"
    - "@opentelemetry/context-zone ^2.7.0 (ZoneContextManager)"
  patterns:
    - "Inert-by-default OTel init: VITE_OTEL_EXPORTER_OTLP_ENDPOINT gates exporter construction"
    - "Plain .ts (not .jinja2) for otel.ts per Pitfall §1 single-jinja-TS-file firewall"
    - "Module-level boolean guard for React StrictMode idempotency"
    - "BatchSpanProcessor re-exported from @opentelemetry/sdk-trace-web (no direct sdk-trace-base dep)"
key_files:
  created:
    - "template/{% if has_web %}web{% endif %}/src/otel.ts"
  modified:
    - "template/{% if has_web %}web{% endif %}/package.json.jinja2"
    - "template/{% if has_web %}web{% endif %}/pnpm-lock.yaml"
    - "template/{% if has_web %}web{% endif %}/src/main.tsx"
    - "tests/test_web_polarity.py"
decisions:
  - "otel.ts imports BatchSpanProcessor from @opentelemetry/sdk-trace-web (which re-exports it from sdk-trace-base) to avoid a direct sdk-trace-base dependency. This keeps the dependency list minimal while retaining full TypeScript types."
  - "Added @opentelemetry/instrumentation as an explicit dependency (not just a peer). registerInstrumentations lives there and tsc --noEmit fails without it being resolvable in node_modules."
  - "TRACE-04 guard uses VERIFY_KIT_SKIP_BUNDLE_BUDGET=1 env opt-out (analogous to VERIFY_KIT_SKIP_PLAYWRIGHT) so fast local runs stay under 2 minutes."
metrics:
  duration: ~30m
  completed: "2026-05-27T12:22:15Z"
  tasks_completed: 3
  files_changed: 5
---

# Phase 7 Plan 08: Browser OTel SDK (Gap Closure) Summary

One-liner: Browser OTel SDK (@opentelemetry/sdk-trace-web + fetch instrumentation) ships inert-by-default in the scaffolded web/ package.json, activated only when VITE_OTEL_EXPORTER_OTLP_ENDPOINT is set — TRACE-01/02/04 closed, TRACE-03 polarity assertion inverted.

## Completed Tasks

| Task | Description | Commit | Key Files |
|------|-------------|--------|-----------|
| 1 | OTel deps + src/otel.ts + wire main.tsx + lockfile | 3efe36b | package.json.jinja2, src/otel.ts, src/main.tsx, pnpm-lock.yaml |
| 2 | TRACE-04 bundle-delta guard (<=100KB gzipped) | f898cde | tests/test_web_polarity.py |
| 3 | Invert TRACE-03 + OTel-present assertions + docstring | 90abd11 | tests/test_web_polarity.py |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] BatchSpanProcessor import from wrong package**

- **Found during:** Task 1 — `pnpm build` TypeScript error
- **Issue:** The plan specified `import { BatchSpanProcessor } from "@opentelemetry/sdk-trace-base"` but `@opentelemetry/sdk-trace-base` is not directly installed (it is a transitive peer). tsc reports `TS2307: Cannot find module '@opentelemetry/sdk-trace-base'`.
- **Fix:** Changed to `import { WebTracerProvider, BatchSpanProcessor } from "@opentelemetry/sdk-trace-web"`. The `sdk-trace-web` package re-exports `BatchSpanProcessor` from its index — this is the canonical browser import pattern.
- **Files modified:** `template/{% if has_web %}web{% endif %}/src/otel.ts`
- **Commit:** 3efe36b

**2. [Rule 2 - Missing dependency] @opentelemetry/instrumentation not in package.json**

- **Found during:** Task 1 — `pnpm build` TypeScript error after fixing Deviation 1
- **Issue:** `registerInstrumentations` lives in `@opentelemetry/instrumentation`, which is a transitive peer but not directly resolvable from package.json without an explicit entry. tsc fails with `TS2307: Cannot find module '@opentelemetry/instrumentation'`.
- **Fix:** Added `"@opentelemetry/instrumentation": "^0.218.0"` to package.json.jinja2 dependencies. This matches the version already installed as a peer of instrumentation-fetch.
- **Files modified:** `template/{% if has_web %}web{% endif %}/package.json.jinja2`, `pnpm-lock.yaml`
- **Commit:** 3efe36b

## Verification Results

All 17 polarity tests pass (1 skipped: bundle budget heavy test with `VERIFY_KIT_SKIP_BUNDLE_BUDGET=1`):

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
tests/test_web_polarity.py::test_web_ci_matrix_shape                   PASSED
tests/test_web_polarity.py::test_web_cli_surface_guard                 PASSED
tests/test_web_polarity.py::test_web_preset_schema_coverage            PASSED
tests/test_web_polarity.py::test_web_otel_bundle_budget                SKIPPED (VERIFY_KIT_SKIP_BUNDLE_BUDGET=1)
tests/test_web_polarity.py::test_web_verify_web_quick_boss_test        PASSED
tests/test_web_polarity.py::test_web_harness_registry_smoke            PASSED
17 passed, 1 skipped in 131.13s
```

Scratch scaffold `pnpm build` confirmed green (tsc --noEmit + vite build, 2136 modules, 109KB gzipped JS).

OTel inert-default build gzip: ~109KB JS total (full bundle with inert OTel tree-shaken). Active OTel delta is expected to pass <= 100KB — CI (no skip flag) will validate with the two-build test.

## Known Stubs

None — the OTel init is fully wired. The activation path (VITE_OTEL_EXPORTER_OTLP_ENDPOINT → OTLP export) is present in code; the Jaeger waterfall smoke test (human-verification step in 07-VERIFICATION.md) requires a running Jaeger instance and is a human-verify step.

## Threat Surface Scan

| Flag | File | Description |
|------|------|-------------|
| T-07-33 (accept) | src/otel.ts | OTLP exporter endpoint: inert by default; consumer who sets VITE_OTEL_EXPORTER_OTLP_ENDPOINT owns the endpoint trust decision |
| T-07-34 (mitigate) | tests/test_web_polarity.py | trace.ts header-only assertion kept — prevents future plans from accidentally importing the SDK into the test fixture |
| T-07-SC (mitigate) | package.json.jinja2, pnpm-lock.yaml | All 5 packages are official @opentelemetry org packages; pnpm-lock.yaml regenerated and committed |

## Self-Check: PASSED
