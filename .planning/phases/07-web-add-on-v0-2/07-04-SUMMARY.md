---
phase: 07-web-add-on-v0-2
plan: "04"
subsystem: web-scaffold
tags: [vite-proxy, mprocs, sse, dev-orchestration, cors, polarity, trace-04]
dependency_graph:
  requires:
    - "07-02: vite.config.ts.jinja2 proxy stub comment, src/config.ts.jinja2 shim"
    - "Phase 4: template/app/main.py.jinja2 CORS middleware structure"
  provides:
    - "template/web/vite.config.ts.jinja2: real /api proxy block under block-level {% if has_backend %}"
    - "template/web/src/config.ts.jinja2: API_BASE_URL polarity split (empty string vs VITE_API_BASE_URL env)"
    - "template/web/src/lib/api.ts.jinja2: fetch wrapper using API_BASE_URL from @/config"
    - "template/web/src/lib/events.ts.jinja2: SSE subscriber with absolute localhost:8000 URL (Pitfall §5)"
    - "template/web/README.md.jinja2: 7-section dev doc (quickstart, polarity, D-W04, SSE rationale, dark mode, gallery replace, shadcn extend)"
    - "template/justfile.jinja2: polarity-aware dev recipe (mprocs/vite/uvicorn/none)"
    - "template/.mise.toml.jinja2: npm:mprocs under has_web and has_backend guard"
    - "template/app/main.py.jinja2: CORSMiddleware with expose_headers under has_web (TRACE-04)"
    - "template/app/settings.py.jinja2: CORS_ALLOW_ORIGINS field + cors_allow_origins property under has_web"
    - "copier.yml: events.ts exclude guard (not has_backend or not has_web)"
    - "tests/test_web_polarity.py: 4-combo (has_web x has_backend) polarity test"
  affects:
    - "template/web/src/lib/ (new files: api.ts.jinja2, events.ts.jinja2)"
    - "tests/test_web_polarity.py (extended: _render helper + 4-combo test)"
tech_stack:
  added:
    - "mprocs (npm:mprocs via mise, web+backend dev orchestration)"
  patterns:
    - "Block-level Jinja conditionals (REVIEW-CHECKLIST §5) in vite.config and justfile"
    - "SSE EventSource with absolute URL to bypass Vite Connect middleware buffering (Pitfall §5)"
    - "CORSMiddleware import gated under {% if has_web %} (prevents import error when has_web=False)"
    - "CORS_ALLOW_ORIGINS as pydantic-settings field with property accessor"
key_files:
  created:
    - "template/{% if has_web %}web{% endif %}/src/lib/api.ts.jinja2"
    - "template/{% if has_web %}web{% endif %}/src/lib/events.ts.jinja2"
    - "template/{% if has_web %}web{% endif %}/README.md.jinja2"
  modified:
    - "template/{% if has_web %}web{% endif %}/vite.config.ts.jinja2"
    - "template/{% if has_web %}web{% endif %}/src/config.ts.jinja2"
    - "template/justfile.jinja2"
    - "template/.mise.toml.jinja2"
    - "template/{% if has_backend %}app{% endif %}/main.py.jinja2"
    - "template/{% if has_backend %}app{% endif %}/settings.py.jinja2"
    - "copier.yml"
    - "tests/test_web_polarity.py"
decisions:
  - "CORSMiddleware and its comment block gated inside {% if has_web %} — not just the app.add_middleware call — to prevent 'expose_headers' token appearing in comments when has_web=False, which would false-trigger the TRACE-04 polarity assertion."
  - "cors_allow_origins added to settings.py.jinja2 as CORS_ALLOW_ORIGINS pydantic field (defaulting to localhost:5173 and localhost:3000) since Phase 4 did not include a CORS settings field. The plan assumed 'allow_origins=settings.cors_allow_origins' would exist; it did not, so the field was added as a Rule 2 deviation."
  - "mprocs chosen as default dev orchestrator (concurrently named as fallback per 07-CONTEXT.md clause). The fallback swap point is the justfile.jinja2 dev: recipe body."
  - "src/config.ts.jinja2 API_BASE_URL split: empty string when has_backend (relative paths proxied by Vite), env-var fallback when not has_backend (D-W05 decoupled polarity)."
requirements: [DEV-W01, DEV-W02, DEV-W03, TRACE-04, D-W04, D-W05, D-W06]
metrics:
  duration: ~35m
  completed: "2026-05-27T07:15:00Z"
  tasks_completed: 3
  files_changed: 11
---

# Phase 7 Plan 04: Vite Proxy + Dev Orchestration + CORS expose_headers Summary

One-liner: Polarity-aware Vite dev proxy (`/api/*` → :8000 under `{% if has_backend %}`), SSE bypass-proxy subscriber (`events.ts` with absolute URL per Pitfall §5), mprocs-orchestrated `just dev` recipe across all 4 `(has_web × has_backend)` polarities, and TRACE-04 `expose_headers` added to CORS middleware — guarded by an 11-test polarity suite covering all four combos (observed green).

## Completed Tasks

| Task | Description | Commit | Key Files |
|------|-------------|--------|-----------|
| 1 | Wire Vite dev proxy + api/events lib files | 8af8a2a | vite.config.ts.jinja2, src/config.ts.jinja2, src/lib/api.ts.jinja2, src/lib/events.ts.jinja2, copier.yml |
| 2 | Polarity-aware dev recipe + mprocs + CORS cross-phase edit | 9b3748d | justfile.jinja2, .mise.toml.jinja2, main.py.jinja2, settings.py.jinja2 |
| 3 | web/README.md + 4-combo polarity test | e4b16b4 | web/README.md.jinja2, main.py.jinja2 (CORS gate fix), tests/test_web_polarity.py |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] cors_allow_origins field missing from settings**

- **Found during:** Task 2 implementation
- **Issue:** The plan said `allow_origins=settings.cors_allow_origins` but Phase 4's `settings.py.jinja2` had no `cors_allow_origins` attribute. Without it, the rendered app would fail at startup with `AttributeError`.
- **Fix:** Added `CORS_ALLOW_ORIGINS: list[str]` field with a `cors_allow_origins` property to `settings.py.jinja2` under `{% if has_web %}`, defaulting to `["http://localhost:5173", "http://localhost:3000"]`.
- **Files modified:** `template/{% if has_backend %}app{% endif %}/settings.py.jinja2`
- **Commit:** 9b3748d

**2. [Rule 1 - Bug] CORSMiddleware import and comment block rendered unconditionally**

- **Found during:** Task 3 polarity test run (False-True combo)
- **Issue:** The import `from fastapi.middleware.cors import CORSMiddleware` and the comment block containing "expose_headers" were outside the `{% if has_web %}` gate. The polarity test for `has_web=False, has_backend=True` correctly asserted `expose_headers not in main.py` but the comment text "expose_headers lets browser code..." rendered even when `has_web=False`.
- **Fix:** Moved the import and the entire comment block inside the `{% if has_web %}` conditional. This also prevents an unnecessary import at runtime for projects that don't include the web add-on.
- **Files modified:** `template/{% if has_backend %}app{% endif %}/main.py.jinja2`
- **Commit:** e4b16b4

## Verification Results

All 11 polarity tests pass (observed, not predicted):

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
11 passed in 85.83s
```

The 4-combo test verified the full matrix of structural properties:
- `(False, False)`: no web dir, no dev recipe — confirmed
- `(False, True)`: no web dir, uvicorn-only dev recipe, no expose_headers in main.py — confirmed
- `(True, False)`: web dir present, no proxy in vite.config, no events.ts, vite-only dev recipe — confirmed
- `(True, True)`: web dir present, proxy in vite.config, events.ts with absolute URL, mprocs dev recipe, expose_headers in main.py — confirmed

## Known Stubs

None — all polarity branches are wired. The `concurrently` fallback for mprocs (documented in 07-CONTEXT.md) is a named escape hatch, not a stub; the default path (mprocs) is fully functional.

## Threat Surface Scan

STRIDE register items from the plan's threat model addressed:

| Flag | File | Description |
|------|------|-------------|
| T-07-11 (CORS) | template/app/main.py.jinja2 | CORSMiddleware expose_headers adds traceparent + X-Request-ID only; origin restriction via CORS_ALLOW_ORIGINS (locked to localhost:5173/3000 by default); consumers must lock down for prod |
| T-07-14 (cross-phase regression) | template/app/main.py.jinja2 | has_backend=True, has_web=False polarity asserted in test — expose_headers absent; Phase 4 CORS invariant holds |

No new network endpoints, auth paths, or trust boundaries introduced beyond what the plan's threat model anticipated.

## Self-Check: PASSED
