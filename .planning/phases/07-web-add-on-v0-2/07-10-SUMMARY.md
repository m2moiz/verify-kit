---
phase: 07-web-add-on-v0-2
plan: "10"
subsystem: web-scaffold
tags: [sse, playwright, eventsource, e2e, web, gap-closure, dev-w03]
dependency_graph:
  requires:
    - "07-04: events.ts SSE client (absolute URL http://localhost:8000/__debug/events, Pitfall §5)"
    - "07-05: playwright.config.ts.jinja2, tests/e2e/fixtures/trace.ts, smoke.spec.ts, _CLEAN_ENV pattern"
  provides:
    - "template/web/tests/e2e/sse.spec.ts: EventSource subscription + 3s MessageEvent assertion (DEV-W03)"
    - "copier.yml: sse.spec.ts excluded under {% if not has_backend or not has_web %} guard"
    - "tests/test_web_polarity.py: sse.spec.ts presence/absence in 4-combo matrix"
  affects:
    - "template/{% if has_web %}web{% endif %}/tests/e2e/ (new file: sse.spec.ts)"
    - "copier.yml (new _exclude entry for sse.spec.ts)"
    - "tests/test_web_polarity.py (extended test_web_backend_four_combos)"
tech_stack:
  added: []
  patterns:
    - "Playwright page.evaluate() to run in-browser EventSource Promise with 3000ms race"
    - "Plain .ts spec (no .jinja2) — Pitfall §1 compliance"
    - "Two-flag _exclude guard mirroring events.ts: {% if not has_backend or not has_web %}"
key_files:
  created:
    - "template/{% if has_web %}web{% endif %}/tests/e2e/sse.spec.ts"
  modified:
    - "copier.yml"
    - "tests/test_web_polarity.py"
decisions:
  - "Used page.evaluate() Promise pattern (not page.request or CDP) — runs fully in-browser, matching how events.ts EventSource actually behaves in the rendered app."
  - "Spec excludes itself via the same {% if not has_backend or not has_web %} guard as events.ts. This is option (B) from the plan's interface notes — plain .ts excluded by copier.yml, not a .ts.jinja2 file (Pitfall §1)."
  - "Live 3s MessageEvent assertion requires a running uvicorn backend — polarity test only asserts file presence/absence. The live event path is exercised by CI's full-stack combo (backend-web / full) where uvicorn + vite preview both run."
requirements: [DEV-W03]
metrics:
  duration: ~15m
  completed: "2026-05-27T15:00:00Z"
  tasks_completed: 2
  files_changed: 3
---

# Phase 7 Plan 10: SSE Playwright Assertion (DEV-W03 Gap Closure) Summary

One-liner: Added `sse.spec.ts` Playwright E2E test that opens an EventSource to the FastAPI `/__debug/events` stream and asserts at least one MessageEvent arrives within 3 seconds — gated to the `has_web + has_backend` polarity via the same `{% if not has_backend or not has_web %}` copier.yml guard as `events.ts`, with 4-combo polarity test proving presence/absence (observed green).

## Completed Tasks

| Task | Description | Commit | Key Files |
|------|-------------|--------|-----------|
| 1 | Add sse.spec.ts asserting MessageEvent within 3s | f52b7c7 | template/web/tests/e2e/sse.spec.ts |
| 2 | Gate sse.spec.ts + extend polarity test | cc49db2 | copier.yml, tests/test_web_polarity.py |

## Deviations from Plan

None — plan executed exactly as written.

## Verification Results

Four-combo polarity test (`test_web_backend_four_combos`) observed green (4 passed, 30s):

```
tests/test_web_polarity.py::test_web_backend_four_combos[False-False] PASSED
tests/test_web_polarity.py::test_web_backend_four_combos[False-True]  PASSED
tests/test_web_polarity.py::test_web_backend_four_combos[True-False]  PASSED
tests/test_web_polarity.py::test_web_backend_four_combos[True-True]   PASSED
4 passed in 30.20s
```

Matrix confirmed:
- `(False, False)`: no web dir, no sse.spec.ts — absence check passed
- `(False, True)`: no web dir, no sse.spec.ts — absence check passed
- `(True, False)`: web dir present, no sse.spec.ts (no backend) — absence check passed
- `(True, True)`: web dir present, sse.spec.ts present — presence check passed

The live 3s MessageEvent assertion in `sse.spec.ts` is exercised by CI's full-stack combo (`backend-web` / `full`) where both uvicorn and vite preview run. The polarity test only asserts spec presence/absence, not the live event.

## Known Stubs

None — sse.spec.ts is fully wired. The live SSE event path requires a running backend, which is an intentional runtime dependency (not a stub). CI's full-stack combo exercises the live path.

## Threat Surface Scan

| Flag | File | Description |
|------|------|-------------|
| T-07-39 (DoS mitigated) | tests/e2e/sse.spec.ts | 3000ms timeout rejects the Promise; Playwright test fails fast rather than hanging |
| T-07-40 (polarity gate) | copier.yml + tests/test_web_polarity.py | sse.spec.ts absent when no backend — 4-combo test proves it |

No new network endpoints introduced. The spec exercises the existing /__debug/events endpoint (Phase 4 HARN-03 debug router, dev-only).

## Self-Check: PASSED

Files verified:
- `template/{% if has_web %}web{% endif %}/tests/e2e/sse.spec.ts` — present (f52b7c7)
- copier.yml sse.spec.ts guard — present (cc49db2)
- tests/test_web_polarity.py sse.spec.ts assertion — present (cc49db2)
- No sse.spec.ts.jinja2 exists (Pitfall §1 compliance)
- 4-combo polarity test: 4/4 observed green
