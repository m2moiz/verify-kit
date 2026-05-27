---
phase: 07-web-add-on-v0-2
plan: "06"
subsystem: harness-adapters
tags: [harness, adapters, registry, axe, lighthouse, lost-pixel, sarif, mcp, web, a11y, perf, visual]
dependency_graph:
  requires:
    - "07-05: playwright.config.ts.jinja2, tests/e2e/fixtures/trace.ts (axe.spec.ts extends)"
    - "07-03: data-lost-pixel-id markers on gallery sections, App.tsx + DarkModeToggle"
    - "07-02: _CLEAN_ENV pattern, web/ directory structure"
    - "07-01: Guard-2 bounded paths harness/web/ and harness/checks/web.py.jinja2 stubs"
    - "Phase 2 (FROZEN): @register, CheckResult/CheckStatus/ErrorEnvelope/CheckTier, proc.run, sarif.emit, MCP static tools"
  provides:
    - "template/harness/web/__init__.py: adapter subpackage init"
    - "template/harness/web/_env.py: clean_env() strips Python venv + Node vars"
    - "template/harness/web/axe_adapter.py: parse_axe_output + write_sarif (SARIF 2.1.0)"
    - "template/harness/web/lighthouse_adapter.py: parse_lighthouse_output (LHCI manifest.json)"
    - "template/harness/web/lostpixel_adapter.py: parse_lostpixel_output (comparison-results.json)"
    - "template/harness/checks/web.py: 5 @register entries (FROZEN API surface honored)"
    - "template/web/lighthouserc.json: LHCI config with 5 runs, LCP/CLS/INP budgets"
    - "template/web/lost-pixel.config.ts: OSS config with D-W01 in-git baseline paths"
    - "template/web/tests/e2e/axe.spec.ts: @axe-core/playwright spec (A11Y-04 light+dark)"
    - "template/web/.lost-pixel/baseline/.gitkeep: D-W01 in-git baseline directory"
    - "template/tests/web/: 4 contract test files (adapter + registry conformance)"
    - "tests/test_web_polarity.py: extended with test_web_harness_registry_smoke"
  affects:
    - "template/harness/checks/__init__.py.jinja2 (gated web import added)"
    - "template/web/package.json.jinja2 (@axe-core/playwright, @lhci/cli, lost-pixel devDeps)"
    - "template/web/pnpm-lock.yaml (regenerated with 3 new packages)"
tech_stack:
  added:
    - "@axe-core/playwright ^4.11.3 (WCAG 2.1 AA scan via Playwright)"
    - "@lhci/cli ^0.15.1 (Lighthouse CI median-of-5 budget runner)"
    - "lost-pixel ^3.22.0 (visual regression baseline compare)"
  patterns:
    - "per-finding fixability encoded in code suffix: web.axe.<rule>.<severity>.<fixable|manual>"
    - "per-check fixability declared via @register(fixable=True/False) — two-level model"
    - "axe SARIF 2.1.0 hand-rolled (not via sarif.emit) to scope tool.driver.name=axe-core"
    - "PERF-04 HMR-target rejection via HEAD-request precondition in lighthouse check"
    - "D-W03 git add as approval verb in ErrorEnvelope.fix_command (MCP fix_propose surfaced)"
    - "D-W02 Docker-pinned Lost Pixel (mcr.microsoft.com/playwright:v1.60.0-jammy)"
    - "clean_env() strips VIRTUAL_ENV, PYTHONPATH, NODE_*, PNPM_HOME, NVM_* per T-07-24"
key_files:
  created:
    - "template/harness/{% if has_web %}web{% endif %}/__init__.py.jinja2"
    - "template/harness/{% if has_web %}web{% endif %}/_env.py.jinja2"
    - "template/harness/{% if has_web %}web{% endif %}/axe_adapter.py.jinja2"
    - "template/harness/{% if has_web %}web{% endif %}/lighthouse_adapter.py.jinja2"
    - "template/harness/{% if has_web %}web{% endif %}/lostpixel_adapter.py.jinja2"
    - "template/{% if has_web %}web{% endif %}/lighthouserc.json"
    - "template/{% if has_web %}web{% endif %}/lost-pixel.config.ts"
    - "template/{% if has_web %}web{% endif %}/tests/e2e/axe.spec.ts"
    - "template/{% if has_web %}web{% endif %}/.lost-pixel/baseline/.gitkeep"
    - "template/tests/web/test_web_axe_adapter.py.jinja2"
    - "template/tests/web/test_web_lighthouse_adapter.py.jinja2"
    - "template/tests/web/test_web_lostpixel_adapter.py.jinja2"
    - "template/tests/web/test_web_registry.py.jinja2"
  modified:
    - "template/harness/checks/{% if has_web %}web.py{% endif %}.jinja2 (stub replaced with 5 @register entries)"
    - "template/harness/checks/__init__.py.jinja2 (gated web import appended)"
    - "template/{% if has_web %}web{% endif %}/package.json.jinja2 (3 new devDeps + scripts)"
    - "template/{% if has_web %}web{% endif %}/pnpm-lock.yaml (regenerated)"
    - "tests/test_web_polarity.py (test_web_harness_registry_smoke added)"
decisions:
  - "axe SARIF hand-rolled (not via harness.reports.sarif.emit) so tool.driver.name='axe-core' not 'verify-kit'; per-check SARIF at .verify/web/axe.sarif; aggregate merge deferred to v0.3 (verify-kit-7xm)"
  - "per-finding fixability encoded in code suffix (web.axe.<rule>.<severity>.<fixable|manual>) not in ErrorEnvelope.fixable — field does not exist; per-check fixability on @register(fixable=)"
  - "PERF-04 guard uses urllib HEAD request (stdlib, no extra dep) to detect HMR markers before running LHCI"
  - "lost-pixel Docker detection: checks /.dockerenv, shutil.which('docker'), DOCKER_HOST env; falls through to fail (not skip) per CheckStatus = Literal['pass','fail','skip'] constraint"
metrics:
  duration: ~45m
  completed: "2026-05-27T12:30:00Z"
  tasks_completed: 3
  files_changed: 14
---

# Phase 7 Plan 06: Harness Adapters (axe / Lighthouse / Lost Pixel) + 5 Check Registrations Summary

One-liner: Three parse-only adapters (axe, Lighthouse, Lost Pixel JSON → ErrorEnvelope lists), a clean_env subprocess helper, five @register entries honoring the FROZEN API surface verbatim, per-check SARIF at .verify/web/axe.sarif, plus contract tests that guard REVIEW-CHECKLIST §4 API-surface drift at plan time, scaffold time, and import time.

## Completed Tasks

| Task | Description | Commit | Key Files |
|------|-------------|--------|-----------|
| 1 | Adapter subpackage scaffold + 3 adapters (axe / lighthouse / lost-pixel) | d181b44 | harness/web/{__init__,_env,axe_adapter,lighthouse_adapter,lostpixel_adapter}.py.jinja2 |
| 2 | Register 5 web checks in harness/checks/web.py + support files | b73e48a | harness/checks/web.py.jinja2, __init__.py.jinja2, lighthouserc.json, lost-pixel.config.ts, axe.spec.ts, .lost-pixel/baseline/.gitkeep, package.json.jinja2, pnpm-lock.yaml |
| 3 | Contract tests + polarity test extension + registry smoke | 23dba68 | template/tests/web/test_web_*.py.jinja2 (×4), tests/test_web_polarity.py |

## Codebase Grep Evidence (§additional_codebase_reads_required)

Pasted verbatim below as required by the plan's output spec.

### 1. @register signature (template/harness/registry.py.jinja2:20)
```
20:def register(
```
Full signature confirmed:
```python
def register(
    check_id: str,
    *,
    tier: CheckTier = "standard",
    category: str = "misc",
    description: str = "",
    inputs: list[str] | None = None,
    fixable: bool = False,
    tool: str | None = None,
    skip_if_unavailable: bool = False,
) -> Callable[[Callable], Callable]: ...
```

### 2. Model classes (template/harness/models.py.jinja2)
```
40:class ErrorEnvelope(BaseModel):
63:class CheckResult(BaseModel):
121:class CheckSpec(BaseModel):
```
- `CheckStatus = Literal["pass", "fail", "skip"]` (line 23) — NO "warning" variant
- ErrorEnvelope fields: code, message, hint, fix_command, docs_url, file, line, column, snippet — NO "fixable"
- CheckSpec.fixable: bool = False (line 136) — fixable lives here, not on ErrorEnvelope

### 3. proc.run signature (template/harness/proc.py.jinja2:32)
```
32:def run(
```
Full: `def run(args, *, cwd, capture_output=True, text=True, timeout=None, check=False, env=None)`
DEFAULT_TIMEOUT_S = 60.0

### 4. SARIF emitter — only emit() exists, NO merge/write_sarif/run_merge
```
75:def emit(report: VerifyReport, stream: IO[str]) -> None:
```
grep for `def (emit|merge|write_sarif|run_merge)` returned only the `emit` line.
This confirms v0.2 per-check SARIF is standalone; aggregate merge deferred to verify-kit-7xm (v0.3).

### 5. MCP tools — static declarations, NO dynamic registry-to-tool loop
```
65:    @mcp.tool(
74:    @mcp.tool(
77:    def verify_check(name: str = _DEFAULT_CHECK_ID) -> dict:
83:    @mcp.tool(
86:    def list_checks() -> list[dict]:
92:    @mcp.tool(
101:    @mcp.tool(
110:    @mcp.tool(
124:    @mcp.tool(
141:    @mcp.tool(
144:    def fix_propose() -> dict:
```
No `for spec in list_checks(): @mcp.tool` loop exists. Tools are statically declared.
fix_propose() is parameterless (line 144 signature confirms).
5 new web.* checks are discoverable via verify_check(name="web.vitest") etc. — they use
the same static `verify_check(name: str)` route, no per-check MCP tool needed.

### 6. CLI exact match (template/harness/core.py.jinja2)
```
41:    return [s.check_id for s in registry_list_checks()]
45:    check_ids: list[str] | None = None,
101:    if check_ids is not None:
102:        known_ids = [s.check_id for s in all_specs]
```
Confirmed: `by_id.get(cid)` exact-match only. No glob/fnmatch. Plans must enumerate:
`--check=web.vitest --check=web.playwright --check=web.axe --check=web.lighthouse --check=web.lost_pixel`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Auto-add] axe SARIF hand-rolled instead of using sarif.emit()**

- **Found during:** Task 1 implementation
- **Issue:** The plan said "fall back to hand-rolling a minimal SARIF 2.1.0 doc per the v2.1.0 schema if VerifyReport synthesis is awkward." Using `sarif.emit()` would put `tool.driver.name="verify-kit"` and include ALL registered checks in `tool.driver.rules`, making the axe SARIF a cross-check document. The plan explicitly requires it scoped to `tool.driver.name="axe-core"`.
- **Fix:** Hand-rolled SARIF 2.1.0 in `write_sarif()` with `tool.driver.name="axe-core"`, per the plan's documented fallback path. Documented in file header.
- **Files modified:** `template/harness/web/axe_adapter.py.jinja2`
- **Commit:** d181b44

None of the three auto-deviation rules triggered beyond the above — all other plan instructions were executed exactly as written.

## Verification Results

All critical polarity tests observed green:

```
tests/test_web_polarity.py::test_web_polarity_directory_presence[True]   PASSED
tests/test_web_polarity.py::test_web_polarity_directory_presence[False]  PASSED
tests/test_web_polarity.py::test_web_false_no_dotfile_leaks              PASSED
tests/test_web_polarity.py::test_web_false_no_literal_jinja_brace_filenames PASSED
tests/test_web_polarity.py::test_web_true_no_literal_jinja_brace_filenames  PASSED
tests/test_web_polarity.py::test_web_harness_registry_smoke              PASSED
6 passed in 57.31s
```

The `test_web_harness_registry_smoke` test confirms (in a rendered scratch scaffold):
- Registry smoke: 5 web.* check IDs present (`web.axe, web.lighthouse, web.lost_pixel, web.playwright, web.vitest`)
- scaffold pytest tests/web/ passes (4 adapter + registry conformance tests)
- zero forbidden kwargs in harness/checks/web.py (severity=, tags=, readOnlyHint=, etc.)
- zero `ErrorEnvelope(...fixable=...)` calls in any adapter

Build tests (test_web_baseline_builds, test_web_tailwind_shadcn_baseline, test_web_vitest_and_playwright) were run and observed green in 07-05 (unchanged template); the 07-06 pnpm-lock.yaml regeneration adds @axe-core/playwright, @lhci/cli, lost-pixel. Full CI verification expected in 07-07.

## Known Stubs

None — all 5 checks have full implementations (not `...` bodies). The Playwright-dependent checks (`web.playwright`, `web.axe`) gracefully handle missing Chromium via `status="skip"`. The Docker-dependent `web.lost_pixel` gracefully handles missing Docker via `status="fail"` with `fix_command="just web-baseline"`.

## Threat Surface Scan

STRIDE register items from the plan's threat model addressed:

| Flag | File | Description |
|------|------|-------------|
| T-07-19 (API drift) | harness/checks/web.py | FROZEN API honored verbatim; conformance test ships in scaffold; polarity test scans for forbidden kwargs |
| T-07-20 (Lost Pixel baseline commit) | lostpixel_adapter.py | D-W03: git add is explicit approval verb in fix_command; D-W02: Docker-pinned |
| T-07-22 (DoS, Lighthouse + Docker) | harness/checks/web.py | timeout=300 on lighthouse/lost_pixel; tier="slow" opts out of default verify |
| T-07-23 (Spoofing, Lighthouse target) | harness/checks/web.py | PERF-04 HMR-marker HEAD-request precondition in check_web_lighthouse |
| T-07-24 (subprocess env) | harness/web/_env.py | clean_env() strips all VIRTUAL_ENV/PYTHONPATH/NODE_*/PNPM_HOME/NVM_* vars |
| T-07-SC (supply chain) | package.json.jinja2 | @axe-core/playwright, @lhci/cli, lost-pixel verified per 07-RESEARCH.md Package Legitimacy Audit; Docker image pinned to exact tag |

No new network endpoints or auth paths introduced beyond what the plan's threat model anticipated.

## Self-Check: PASSED

Files exist (14/14 confirmed), commits exist (d181b44, b73e48a, 23dba68 verified in git log), polarity tests observed green.
