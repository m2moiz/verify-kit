---
phase: 07-web-add-on-v0-2
verified: 2026-05-27T22:00:00Z
status: human_needed
score: 7/7
overrides_applied: 2
overrides:
  - must_have: "axe color-contrast rule disabled in axe.spec.ts"
    reason: "axe-core <=4.11.4 produces false positives on oklch() colors used by Tailwind v4 + shadcn/ui default theme. Rendered contrast was verified visually as passing WCAG AA in both light and dark mode. Disable removed by removing 'color-contrast' from DISABLED_RULES once axe-core ships correct oklch() support. All other WCAG 2 A/AA rules remain active. (Orchestrator-applied fix — commit 089e58a)"
    accepted_by: "m2moiz"
    accepted_at: "2026-05-27T00:00:00Z"
  - must_have: "axe SARIF written via harness.reports.sarif.emit()"
    reason: "Hand-rolled SARIF 2.1.0 in write_sarif() used instead, scoping tool.driver.name='axe-core' not 'verify-kit'. The plan explicitly documented this fallback path; the outcome (per-check SARIF at .verify/web/axe.sarif readable by VS Code) is equivalent."
    accepted_by: "m2moiz"
    accepted_at: "2026-05-27T00:00:00Z"
re_verification:
  previous_status: gaps_found
  previous_score: 5/7
  gaps_closed:
    - "PRESET-06: preset-render job now present in template-selftest.yml (lines 235-267) with copier copy --data-file presets/oss-minimalist.yml + just verify and same for personal.yml. Commits 783a269 + e9b3777 confirmed reachable from HEAD. test_web_preset_render_and_schedule passes (1 passed in 0.02s)."
    - "WCI-02: schedule: cron '0 2 * * 1' (Monday 02:00 UTC) and workflow_dispatch now present in template-selftest.yml on: block (lines 37-41). Cache-skip condition github.event_name != 'schedule' present on both pnpm store and Playwright cache steps (lines 99, 122). Confirmed via test_web_preset_render_and_schedule."
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Start a full-stack scaffold (has_web=true, has_backend=true), run `just trace-up` then `just dev`, open browser at http://localhost:5173, click 'Fire test fetch' in the gallery"
    expected: "just trace --last shows a waterfall with browser fetch span and FastAPI /api/healthz span linked by the injected traceparent header (single traceparent, two spans, one in browser one in FastAPI)"
    why_human: "Requires a running dev environment with Jaeger, browser interaction, and visual inspection of the Jaeger waterfall. OTel SDK is installed and wired; the live trace path requires runtime environment."

  - test: "Run `just verify-web` in a freshly scaffolded full-stack project (has_web=true, has_backend=true, has_llm=true) with Docker available. Run `just web-baseline` first."
    expected: "web.lost_pixel exits pass after baseline capture; diff PNG output is empty"
    why_human: "Requires Docker, a running server, and visual inspection that the baseline PNG looks correct before acceptance."

  - test: "In a scaffold with has_web=true, manually verify the index.css dark-mode renders with correct WCAG AA contrast in a real browser for the primary button (oklch near-black on near-white)."
    expected: "Buttons and text should be visually distinguishable in both light and dark modes at WCAG AA contrast ratio (4.5:1 for normal text)"
    why_human: "color-contrast axe rule is intentionally disabled due to axe-core <=4.11.4 false positives on oklch(). Human visual inspection is the only verification path until axe-core ships correct oklch() support."
---

# Phase 7: Web Add-on (v0.2) Verification Report

**Phase Goal:** When a consumer answers `has_web=true`, the scaffolded project gets a working Vite + React + TypeScript + shadcn/ui + Tailwind v4 frontend under `web/` that builds, tests (Vitest unit + Playwright e2e), and folds three web-specific verifier checks (axe-core a11y, Lighthouse CI perf budgets, Lost Pixel visual regression) into `just verify --web` — with browser OTel SDK (`@opentelemetry/sdk-trace-web`) wired but inert by default so click → fetch → FastAPI → DB appears as a single Jaeger waterfall when enabled. Bundled: preset answers files (`personal.yml` + `oss-minimalist.yml`, PII-protected) resolving verify-kit-q8t, and CI matrix expanded from 5 → 6 meaningful combos.

**Verified:** 2026-05-27T22:00:00Z
**Status:** human_needed (all 7/7 automated truths pass; 3 runtime/visual items require human)
**Re-verification:** Yes — final pass after 07-12 gap-closure merge confirmed

---

## Final Gap-Closure Audit

| Prior Gap | Plan | Resolution | Codebase Status |
|-----------|------|-----------|-----------------|
| TRACE-01/02/04: OTel SDK absent | 07-08 | CLOSED | `package.json.jinja2` has 5 `@opentelemetry/*` packages. `src/otel.ts` implements inert-by-default provider. `main.tsx` calls `initOtel()` before `createRoot()`. TRACE-04 bundle-delta guard at `tests/test_web_polarity.py:988`. |
| DEV-W04: web/.vscode/ absent | 07-09 | CLOSED | `extensions.json` + `settings.json` present under `template/{% if has_web %}web{% endif %}/.vscode/`. copier.yml lines 56-57 have two-guard entries. |
| DEV-W03/SC-2: SSE Playwright assertion absent | 07-10 | CLOSED | `tests/e2e/sse.spec.ts` present, asserts `>=1 MessageEvent` from `/__debug/events` within 3s via `page.evaluate()` Promise. copier.yml line 66 gates it to `has_web+has_backend`. |
| VIZ-03: lost-pixel-approve CLI shim absent | 07-11 | CLOSED | `lostpixel_adapter.py.jinja2` has `def main()` (line 137) with argparse, `--dry-run`/`--confirm` mutually-exclusive flags, and explicit-cwd subprocess. `pyproject.toml.jinja2` lines 109-110 register it under `{% if has_web %}` guard. |
| PRESET-06: CI never invokes `--data-file presets/` | 07-12 | **CLOSED** | Commits 783a269 + e9b3777 confirmed reachable from HEAD (visible in `git log`). `template-selftest.yml` now has `preset-render` job (lines 235-267) with `copier copy --trust --defaults --data-file presets/${{ matrix.preset }}.yml` for matrix `[oss-minimalist, personal]`. `test_web_preset_render_and_schedule` passes (1 passed in 0.02s). |
| WCI-02: no weekly cold-install cron | 07-12 | **CLOSED** | `template-selftest.yml` `on:` block now has `schedule: - cron: "0 2 * * 1"` (Monday 02:00 UTC) and `workflow_dispatch` (lines 37-41). Cache-skip condition `github.event_name != 'schedule'` present on pnpm + Playwright cache steps (lines 99, 122). Same commit set as PRESET-06. |

All 6 prior gaps are now confirmed closed against the live codebase at HEAD.

---

## Goal Achievement

### Observable Truths (from ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC-1 | Scaffold + build: `pnpm install + pnpm build + pnpm preview` exits 0; `has_web=false` leaves zero artifacts | VERIFIED | `template/{% if has_web %}web{% endif %}/` with full Vite config; `test_web_baseline_builds` + `test_web_polarity_directory_presence` pass; 358+ passed, 0 failed |
| SC-2 | Dev loop: `just dev` works across 4 polarities; Playwright smoke asserts SSE event reaches UI within 3s | VERIFIED | `just dev` polarity branches in justfile.jinja2 verified. `tests/e2e/sse.spec.ts` asserts `>=1 MessageEvent` within 3s from `/__debug/events` (gap 07-10 closed). |
| SC-3 | Three verifier checks land green (vitest, playwright, lighthouse/axe/lost_pixel) | VERIFIED | 5 `@register` entries in `web.py.jinja2`; axe.spec.ts (light+dark, WCAG 2.1 AA minus oklch false-positive rule); `lighthouserc.json` with 5-run budgets; `lostpixel_adapter.py.jinja2` Docker-pinned |
| SC-4 | MCP twins: 5 web check IDs discoverable; `--check=lighthose` did-you-mean | VERIFIED | Registry smoke confirms `web.axe`, `web.lighthouse`, `web.lost_pixel`, `web.playwright`, `web.vitest`; CLI did-you-mean in `cli.py.jinja2:192` |
| SC-5 | Browser OTel SDK installed and inert by default; single Jaeger waterfall when `VITE_OTEL_EXPORTER_OTLP_ENDPOINT` set | VERIFIED (code) | `package.json.jinja2` has 5 OTel packages; `src/otel.ts` implements full inert-by-default init; `main.tsx` calls `initOtel()` before `createRoot()`. Live Jaeger waterfall requires human verification (runtime dependency). |
| SC-6 | Preset files `oss-minimalist.yml` + `personal.yml` with `_schema_version: "0.2"`, PII protection, CI schema check | VERIFIED | Both preset files present with `_schema_version: "0.2"`; `.gitignore` excludes `*.local.yml`; `check-preset-pii` hook; `preset-schema-check.yml` workflow present |
| SC-7 | CI matrix: 6 combos, no `+web+llm`, pnpm + Playwright caches, Lighthouse/LostPixel gated to full, `timeout-minutes: 20`, `fail-fast: false` — AND CI preset-render job + weekly cold-install schedule | VERIFIED | All components confirmed: 6-combo matrix, caches keyed by lockfile SHA + PW version, Lighthouse/LostPixel gated to `full` combo, `timeout-minutes: 20`, `fail-fast: false`. `preset-render` job (lines 235-267) with `--data-file presets/<preset>.yml` matrix. `schedule: cron "0 2 * * 1"` + `workflow_dispatch` + cache-skip condition on scheduled runs. |

**Score: 7/7 ROADMAP success criteria fully verified**

---

### Requirement ID Coverage

| Req ID | Description (abbreviated) | Status | Evidence / Notes |
|--------|--------------------------|--------|-----------------|
| WEB-01 | `copier copy` with `has_web=true` → working `pnpm build + pnpm preview` | VERIFIED | Build smoke + polarity tests green |
| WEB-02 | Pinned package versions (Vite ^7.1, React ^19.2, TS ~5.7, etc.) | VERIFIED | `package.json.jinja2` matches all STACK.md pins |
| WEB-03 | `.mise.toml` adds Node + pnpm + mprocs only when `has_web=true` | VERIFIED | `.mise.toml.jinja2` uses `{% if has_web %}` guards |
| WEB-04 | Two-guard path gating per REVIEW-CHECKLIST §3; polarity test | VERIFIED | 11 `_exclude` entries in `copier.yml`; polarity tests green |
| WEB-05 | All .tsx/.ts verbatim; parameterized values in single `config.ts.jinja2` | VERIFIED | `src/config.ts.jinja2` is the only Jinja-templated TS file |
| UI-01 | `components.json` for shadcn v4, 7 components vendored | VERIFIED | `components.json` present; 7 `.tsx` files in `src/components/ui/` |
| UI-02 | `index.css` uses `@import "tailwindcss"` + `@theme`, no `tailwind.config.js` | VERIFIED | Confirmed; no `tailwind.config.*` in web template |
| UI-03 | TS path aliases `@/*` in sync between tsconfig + vite.config; verify check on drift | PARTIAL | Aliases in sync; no standalone verify check — typecheck catches drift at build time (acceptable) |
| UI-04 | `App.tsx` renders components against config shim | VERIFIED | `App.tsx` is a full 7-section component gallery importing from `./config` |
| DEV-W01 | `just dev` works across all four polarities | VERIFIED | `justfile.jinja2` has 3-branch polarity-aware `dev:` recipe |
| DEV-W02 | Vite proxy `/api/*` → FastAPI :8000 when `has_backend=true`; absent when `has_backend=false` | VERIFIED | `vite.config.ts.jinja2` wraps proxy in `{% if has_backend %}` |
| DEV-W03 | SSE bypasses proxy via absolute URL; Playwright smoke asserts SSE within 3s | VERIFIED | `events.ts.jinja2` uses `http://localhost:8000/__debug/events`; `sse.spec.ts` asserts `>=1 MessageEvent` within 3s (gap 07-10 closed) |
| DEV-W04 | `web/.vscode/extensions.json` + `web/.vscode/settings.json` | VERIFIED | Both files exist under `has_web` Guard-2 path with two-guard copier.yml exclusions (gap 07-09 closed) |
| TEST-W01 | `vitest.config.ts` + happy-dom + testing-library; passing example test | VERIFIED | `vitest.config.ts`, `vitest.setup.ts`, `App.test.tsx`, `DarkModeToggle.test.tsx` present |
| TEST-W02 | `playwright.config.ts.jinja2` with smoke spec against `vite preview` | VERIFIED | `playwright.config.ts.jinja2` uses `pnpm exec vite preview --port 4173`; `smoke.spec.ts` asserts gallery + dark-mode |
| TEST-W03 | Playwright fixture injects `traceparent` header; FastAPI echoes it back when `has_backend=true` | VERIFIED | `trace.ts` fixture uses `page.setExtraHTTPHeaders({traceparent})`; fixture test passes |
| A11Y-01 | `web.axe` check runs `@axe-core/playwright` against `vite preview`; ErrorEnvelope format | VERIFIED | `check_web_axe` in `web.py.jinja2`; `axe.spec.ts` writes `.verify/web/axe.json` |
| A11Y-02 | `harness/web/axe_to_sarif.py` converts axe JSON → SARIF at `.verify/report.sarif` | PARTIAL | Hand-rolled SARIF 2.1.0 in `write_sarif()`; file named `axe_adapter` not `axe_to_sarif`; SARIF at `.verify/web/axe.sarif` not `.verify/report.sarif`. OVERRIDE applied — functionally equivalent. |
| A11Y-03 | `fix_propose --check=axe --finding=<id>` returns unified diff for 12-15 fixable rules | PARTIAL | `FIXABLE_RULES` frozenset exists; per-finding `fix_command` deferred to v0.3 bead verify-kit-pc8 |
| A11Y-04 | `web.axe` exit codes semantic; JSON output stable for agent re-verify | VERIFIED | `check_web_axe` returns `status="pass"/"fail"/"skip"` |
| PERF-01 | `web.lighthouse` runs LHCI with `numberOfRuns:5` + median-run against `vite preview` | VERIFIED | `lighthouserc.json` has `numberOfRuns:5`; `check_web_lighthouse` uses `lhci autorun` |
| PERF-02 | `lighthouserc.json` with LCP/CLS/INP budget assertions; size budgets | VERIFIED | LCP/CLS/interactive assertions + total-byte-weight 512KB present |
| PERF-03 | `lighthouse_adapter.py` maps LHCI JSON → envelopes; `fix_command` for asset failures | VERIFIED | `lighthouse_adapter.py.jinja2` parses LHCI manifest.json; `_BUDGET_HINT` present |
| PERF-04 | Lighthouse refuses to run against vite dev (HMR markers in headers) | VERIFIED | `check_web_lighthouse` HEAD-requests target; rejects if `"Vite"` in Server header |
| VIZ-01 | `web.lost_pixel` runs Lost Pixel against preview; results in `.verify/visual/` | VERIFIED | `check_web_lost_pixel` in `web.py.jinja2`; `lost-pixel.config.ts` in template |
| VIZ-02 | Lost Pixel pinned to Docker image; outside-Docker emits status=fail with fix_command | VERIFIED | `_DOCKER_IMAGE = "mcr.microsoft.com/playwright:v1.60.0-jammy"`; Docker unavailable → `status="fail"` + `fix_command="just web-baseline"` |
| VIZ-03 | `lostpixel_adapter.py` exposes `lost-pixel-approve` CLI shim with `--dry-run` flag | VERIFIED | `def main()` (line 137) with argparse, `--dry-run`/`--confirm` mutually-exclusive flags, explicit cwd; registered in `pyproject.toml.jinja2` (gap 07-11 closed). MCP `fix_propose --check=visual --approve` wiring deferred to v0.3 (bead verify-kit-pc8) — intentional scope boundary. |
| VIZ-04 | Baseline storage: in-git under `web/.lost-pixel/baseline/` | VERIFIED | `lost-pixel.config.ts` sets `imagePathBaseline: "./.lost-pixel/baseline"`; `.gitkeep` in template |
| TRACE-01 | `@opentelemetry/sdk-trace-web` + `instrumentation-fetch` installed, inert by default | VERIFIED | Both packages in `package.json.jinja2` dependencies (lines 23-27); `src/otel.ts` implements inert-by-default init (gap 07-08 closed) |
| TRACE-02 | When `VITE_OTEL_EXPORTER_OTLP_ENDPOINT` set, browser spans land in Jaeger waterfall | VERIFIED (code) | `otel.ts` creates `OTLPTraceExporter` + `WebTracerProvider` + `FetchInstrumentation` when env var is set; live Jaeger waterfall is a human-verify item (requires runtime) |
| TRACE-03 | CORS `expose_headers=["traceparent"]` in FastAPI middleware when `has_web=true` | VERIFIED | `main.py.jinja2:136-151` adds `expose_headers` under `{% if has_web %}`; 4-combo polarity test asserts presence/absence |
| TRACE-04 | Bundle-size guard: OTel adds ≤100KB gzipped when `VITE_OTEL=on` | VERIFIED (skippable) | `test_web_otel_bundle_budget` at line 988 in `tests/test_web_polarity.py`; skipped locally with `VERIFY_KIT_SKIP_BUNDLE_BUDGET=1`; CI validates without skip flag |
| WMCP-01 | 5 new check IDs discoverable via `verify_check(name=...)` + `list_checks()` | VERIFIED | Registry smoke confirms all 5 `web.*` IDs |
| WMCP-02 | Each web check annotated with MCP hints (`readOnlyHint`/`destructiveHint`) | PARTIAL | Per-check MCP tool auto-generation deferred to v0.3 (bead verify-kit-964). Static `verify_check(name=...)` carries `readOnlyHint=True` only. |
| WMCP-03 | `verify-kit describe` includes 5 new check IDs; misspelled `--check=lighthose` did-you-mean | VERIFIED | `cli.py.jinja2:192` has did-you-mean logic; all 5 checks registered |
| PRESET-01 | `presets/personal.yml` + `presets/oss-minimalist.yml` + `presets/README.md` | VERIFIED | All three files present |
| PRESET-02 | `oss-minimalist.yml` matches public defaults; no PII | VERIFIED | `has_web: false`, safe placeholder values |
| PRESET-03 | `personal.yml` is PII-free placeholder; `_schema_version: "0.2"` | VERIFIED | Placeholder values; `_schema_version: "0.2"` present |
| PRESET-04 | `.gitignore` excludes `*.local.yml`; pre-commit hook greps for PII patterns | VERIFIED | `.gitignore` has `presets/*.local.yml`; `check-preset-pii` hook present |
| PRESET-05 | Both presets declare `_schema_version: "0.2"`; CI fails on drift | VERIFIED | Both presets have `_schema_version: "0.2"`; `preset-schema-check.yml` enforces coverage |
| PRESET-06 | CI matrix self-validates both presets via `copier copy --data-file presets/<x>.yml + just verify` | VERIFIED | `preset-render` job at lines 235-267 in `template-selftest.yml`. Matrix `[oss-minimalist, personal]`. Each step renders `copier copy --trust --defaults --data-file presets/${{ matrix.preset }}.yml` then `just verify`. Commits 783a269 + e9b3777 reachable from HEAD. `test_web_preset_render_and_schedule` passes. |
| WCI-01 | Matrix: 6 combos, `+web+llm` explicitly absent | VERIFIED | Combos `[base, backend, llm, web, backend-web, full]`; no web-llm present |
| WCI-02 | pnpm store + Playwright cache keyed by lockfile SHA + PW version; cold install weekly | VERIFIED | pnpm store cache keyed by `hashFiles('template/...pnpm-lock.yaml')` present; Playwright cache keyed by version present; `schedule: cron "0 2 * * 1"` present; cache-skip condition `github.event_name != 'schedule'` on both cache steps. `test_web_preset_render_and_schedule` asserts schedule + condition. |
| WCI-03 | Lighthouse + Lost Pixel only on full-stack combo | VERIFIED | `run_lighthouse: true` and `run_lost_pixel: true` only on `combo: full` |
| WCI-04 | `timeout-minutes: 20` + `fail-fast: false` on all matrix jobs | VERIFIED | `timeout-minutes: 20` on `selftest` job; `fail-fast: false` on strategy |

**Requirements summary:**

| Req Group | Total IDs | Verified | Partial | Failed | Notes |
|-----------|-----------|---------|---------|--------|-------|
| WEB-01..05 | 5 | 5 | 0 | 0 | All met |
| UI-01..04 | 4 | 3 | 1 | 0 | UI-03 partial: no standalone drift verify check (tsc covers it) |
| DEV-W01..04 | 4 | 4 | 0 | 0 | All met |
| TEST-W01..03 | 3 | 3 | 0 | 0 | All met |
| A11Y-01..04 | 4 | 2 | 2 | 0 | A11Y-02 partial (override applied); A11Y-03 partial (fix_propose deferred v0.3) |
| PERF-01..04 | 4 | 4 | 0 | 0 | All met |
| VIZ-01..04 | 4 | 4 | 0 | 0 | All met |
| TRACE-01..04 | 4 | 4 | 0 | 0 | All met |
| WMCP-01..03 | 3 | 2 | 1 | 0 | WMCP-02 partial (per-check destructiveHint deferred v0.3) |
| PRESET-01..06 | 6 | 6 | 0 | 0 | All met — PRESET-06 gap closed by 07-12 merge |
| WCI-01..04 | 4 | 4 | 0 | 0 | All met — WCI-02 gap closed by 07-12 merge |
| **TOTAL** | **45** | **41** | **4** | **0** | 4 partials are all intentional v0.3 deferrals or accepted overrides |

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `template/{% if has_web %}web{% endif %}/package.json.jinja2` | Vite 7 + React 19 + TS 5.7 + 5 OTel packages | VERIFIED | All pinned versions + `@opentelemetry/sdk-trace-web` + 4 sibling packages |
| `template/{% if has_web %}web{% endif %}/src/otel.ts` | Inert-by-default OTel init; VITE_OTEL_EXPORTER_OTLP_ENDPOINT gate | VERIFIED | 89-line implementation; module-level `_initialised` guard; plain `.ts` (Pitfall §1) |
| `template/{% if has_web %}web{% endif %}/src/main.tsx` | Calls `initOtel()` before `createRoot()` | VERIFIED | Line 12: `initOtel()` called before `createRoot()` |
| `template/{% if has_web %}web{% endif %}/.vscode/extensions.json` | Recommends Tailwind IntelliSense, ESLint, Playwright, Prettier | VERIFIED | 4 recommendations present |
| `template/{% if has_web %}web{% endif %}/.vscode/settings.json` | `eslint.useFlatConfig: true`, `tailwindCSS.experimental.configFile: src/index.css` | VERIFIED | Both keys present |
| `template/{% if has_web %}web{% endif %}/tests/e2e/sse.spec.ts` | SSE EventSource asserts >=1 MessageEvent within 3s | VERIFIED | `page.evaluate()` Promise pattern; 3000ms timeout; absolute URL |
| `template/harness/{% if has_web %}web{% endif %}/lostpixel_adapter.py.jinja2` | `parse_lostpixel_output` + `main()` CLI shim | VERIFIED | `def main()` at line 137; argparse with `--dry-run`/`--confirm`; `__all__` includes both |
| `template/pyproject.toml.jinja2` | `lost-pixel-approve` entry under `{% if has_web %}` | VERIFIED | Lines 109-110 register `lost-pixel-approve = "harness.web.lostpixel_adapter:main"` |
| `.github/workflows/template-selftest.yml` | preset-render job + `schedule: cron '0 2 * * 1'` + `workflow_dispatch` | VERIFIED | 266-line file. `preset-render` job at lines 235-267 with `--data-file presets/${{ matrix.preset }}.yml`. `schedule: - cron: "0 2 * * 1"` at lines 37-38. `workflow_dispatch:` at line 40. Cache-skip condition at lines 99 + 122. Commits 783a269 + e9b3777 reachable from HEAD. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `otel.ts` | `main.tsx` | `import { initOtel } from "./otel"` + `initOtel()` call | VERIFIED | `main.tsx` line 7 imports; line 12 calls before `createRoot()` |
| `package.json.jinja2` OTel packages | `otel.ts` imports | `@opentelemetry/sdk-trace-web`, `instrumentation-fetch`, `exporter-trace-otlp-http`, `instrumentation`, `context-zone` | VERIFIED | All 5 import sources in `package.json.jinja2`; all 5 consumed in `otel.ts` |
| `sse.spec.ts` | `has_web+has_backend` polarity | `copier.yml` line 66: `{% if not has_backend or not has_web %}` guard | VERIFIED | Guard present; 4-combo polarity test `test_web_backend_four_combos` passes |
| `lostpixel_adapter.py.jinja2` `main()` | `pyproject.toml.jinja2` `[project.scripts]` | `lost-pixel-approve = "harness.web.lostpixel_adapter:main"` | VERIFIED | Entry present under `{% if has_web %}` guard |
| `.vscode/extensions.json` + `settings.json` | `has_web` copier guard | `copier.yml` lines 56-57 two-guard exclusion | VERIFIED | `grep -c 'web/.vscode' copier.yml` returns 2 |
| `config.ts.jinja2` | All `.tsx` files | `import { PROJECT_NAME } from "./config"` | VERIFIED | `App.tsx` imports from `./config` |
| `vite.config.ts.jinja2` proxy block | `has_backend` Jinja conditional | Block-level `{% if has_backend %}` | VERIFIED | Confirmed in `vite.config.ts.jinja2` |
| `events.ts.jinja2` | absolute `http://localhost:8000/__debug/events` | EventSource URL (Pitfall §5) | VERIFIED | `new EventSource("http://localhost:8000/__debug/events")` |
| `main.py.jinja2` CORS | `{% if has_web %}` gate | `expose_headers=["traceparent","X-Request-ID"]` | VERIFIED | Lines 136-152 in main.py.jinja2 |
| `preset-render` job | `presets/oss-minimalist.yml` + `presets/personal.yml` | `--data-file presets/${{ matrix.preset }}.yml` in workflow step | VERIFIED | Lines 257-262 in `template-selftest.yml`; matrix contains both preset names |
| `schedule: cron` | cache-skip condition | `github.event_name != 'schedule'` on cache steps | VERIFIED | Lines 99, 122 in `template-selftest.yml`; polarity test asserts string presence |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| `App.tsx` gallery sections | `PROJECT_NAME`, `PROJECT_DESCRIPTION` | `config.ts.jinja2` ← Copier render | Yes (Jinja substitution) | FLOWING |
| `otel.ts` span exporter | `VITE_OTEL_EXPORTER_OTLP_ENDPOINT` | Vite static env at build time | Yes (when set; inert when absent) | FLOWING (conditional) |
| `axe_adapter.py` SARIF output | violations from axe JSON | `axe.spec.ts` writes `.verify/web/axe.json` | Yes (real browser scan) | FLOWING |
| `lighthouse_adapter.py` envelopes | LHCI budget failures | `lhci autorun` writes manifest.json + lhr JSONs | Yes (real Lighthouse data) | FLOWING |
| `lostpixel_adapter.py` diffs | `comparison-results.json` | Docker-based Lost Pixel comparison | Yes (real pixel comparison) | FLOWING |
| `sse.spec.ts` EventSource | MessageEvent data | FastAPI `/__debug/events` SSE stream | Yes (live backend; CI full-stack combo) | FLOWING (runtime) |
| `preset-render` job | `copier copy` render output | `presets/oss-minimalist.yml` + `presets/personal.yml` via `--data-file` | Yes (real preset file values) | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Evidence | Status |
|----------|---------|--------|
| `has_web=false` leaves zero `web/` artifacts | `test_web_polarity_directory_presence[False]` PASS | PASS |
| `has_web=true` scaffold builds (`pnpm build` exits 0) | `test_web_baseline_builds` PASS | PASS |
| OTel SDK present in rendered `package.json` | `test_web_vitest_and_playwright` Tier 2b asserts `@opentelemetry/sdk-trace-web` in rendered `package.json` | PASS |
| `otel.ts` inert when no env var | Code inspection: `if (!endpoint) { return; }` at lines 61-64 in `otel.ts` | PASS |
| web/.vscode files present + no leak under has_web=false | `test_web_vscode_presence` + `test_web_vscode_no_leak` PASS | PASS |
| sse.spec.ts present in `(True,True)` combo, absent in others | `test_web_backend_four_combos` 4/4 PASS | PASS |
| lost-pixel-approve shim present in has_web=true scaffold | `test_lostpixel_approve_shim_present` PASS | PASS |
| lost-pixel-approve absent in has_web=false scaffold; TOML valid | `test_lostpixel_approve_shim_absent_when_no_web` PASS | PASS |
| CI matrix shape: 6 combos, `fail-fast: false`, `timeout-minutes: 20` | `test_web_ci_matrix_shape` PASS | PASS |
| Preset schema coverage: both presets match copier.yml | `test_web_preset_schema_coverage` PASS | PASS |
| CI preset-render job + weekly cold-install cron present | `test_web_preset_render_and_schedule` — **1 passed in 0.02s** (observed, not predicted) | PASS |

All 11 behavioral spot-checks pass.

---

### Probe Execution

No `scripts/*/tests/probe-*.sh` probes declared in Phase 7 plans. The polarity test suite and full pytest suite serve as the phase's automated verification signal. Orchestrator-reported baseline: 358 passed, 17 skipped, 0 failed (exit 0). The 07-12 merge adds `test_web_preset_render_and_schedule` which passes (1 passed in 0.02s — directly observed).

---

### Requirements Coverage

All 45 requirement IDs accounted for. Zero FAILED. Zero ORPHANED (all IDs appear in phase plan frontmatter). 4 PARTIAL items are all intentional: UI-03 (tsc coverage acceptable), A11Y-02 (override applied), A11Y-03 (v0.3 bead verify-kit-pc8), WMCP-02 (v0.3 bead verify-kit-964).

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `template/{% if has_web %}web{% endif %}/src/App.tsx` | 41-48 | `handleTraceFetch` makes `/api/healthz` fetch that fails if backend not running | INFO | Expected gallery behavior — catches errors and shows toast |
| `template/harness/checks/{% if has_web %}web.py{% endif %}.jinja2` | 239-241 | `except (FileNotFoundError, Exception): envelopes = []` broad catch | WARNING | Silences parse errors in lighthouse output; low risk in template context |

No `TBD`, `FIXME`, or `XXX` debt markers found in Phase 7 modified files. No new anti-patterns introduced by 07-12 changes (only CI YAML was modified).

---

### v0.3-Deferred Items (Intentional Scope Boundaries)

These items were explicitly ruled out of v0.2 scope. They are NOT gaps.

| Item | Deferred To | Bead | Notes |
|------|-------------|------|-------|
| OTel auto-init Vite plugin (automatic activation without env-var) | v0.3 | — | v0.2 scope: SDK ships inert, activation is manual. |
| `fix_propose --check=visual --approve` MCP wiring for `lost-pixel-approve` | v0.3 | verify-kit-pc8 | v0.2 scope: CLI shim only. Zero-arg `fix_propose()` signature incompatible with per-check `--approve` routing. |
| Per-check `destructiveHint: true` MCP annotation for `web.lost_pixel` | v0.3 | verify-kit-964 | v0.2 scope: static `verify_check(name=...)` with `readOnlyHint=True`. |
| `fix_propose --check=axe --finding=<id>` unified diff for fixable rules | v0.3 | verify-kit-pc8 | v0.2 scope: `FIXABLE_RULES` frozenset ships; per-finding `fix_command` not implemented. |

---

### Human Verification Required

#### 1. OTel Jaeger Waterfall

**Test:** Start a full-stack scaffold (`has_web=true, has_backend=true`), run `just trace-up` then `just dev`, open `http://localhost:5173`, click "Fire test fetch" button in the gallery.
**Expected:** `just trace --last` shows a waterfall with browser fetch span and FastAPI `/api/healthz` span linked by the injected traceparent header (single traceparent, two spans: one in browser, one in FastAPI).
**Why human:** Requires live dev environment with Jaeger, browser interaction, and visual inspection of the Jaeger waterfall. The OTel SDK is correctly installed and wired — this tests the live activation path.

#### 2. Lost Pixel Baseline Acceptance (Docker required)

**Test:** In a freshly scaffolded project, run `just web-baseline` inside Docker, then `just verify-web`. Inspect the baseline PNG before committing.
**Expected:** `web.lost_pixel` reports pass; `.lost-pixel/baseline/gallery-full.png` shows the full component gallery correctly rendered in the pinned Playwright Docker image.
**Why human:** Requires Docker, baseline PNG visual inspection, and deliberate `git add` approval. Automated checks verify the check runs — not whether the visual output is correct.

#### 3. Dark-Mode WCAG AA Contrast (axe color-contrast disabled)

**Test:** Render a scaffold, run `pnpm dev`, visually inspect primary buttons and text in both light and dark modes.
**Expected:** Text and interactive elements should meet WCAG AA contrast (4.5:1 for normal text) in both modes.
**Why human:** `color-contrast` axe rule disabled due to axe-core <=4.11.4 oklch false positives. Human visual inspection is the only verification path until axe ships correct oklch support.

---

### Known Tooling Limitation

**axe-core color-contrast + oklch colors:**
axe-core <=4.11.4 computes luminance incorrectly for `oklch()` colors, producing false-positive contrast failures on the shadcn/ui + Tailwind v4 default theme. The `color-contrast` rule is intentionally disabled in `tests/e2e/axe.spec.ts` via `DISABLED_RULES = ["color-contrast"]`. All other WCAG 2 A/AA rules remain active. Re-enable by removing `"color-contrast"` from `DISABLED_RULES` once axe-core ships correct oklch() support.

---

*Verified: 2026-05-27T22:00:00Z*
*Verifier: Claude (gsd-verifier)*
*Re-verification: Final — after 07-12 gap-closure merge (commits 783a269 + e9b3777)*
