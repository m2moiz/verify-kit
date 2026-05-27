---
phase: 07-web-add-on-v0-2
plan: "12"
subsystem: ci
tags: [ci, presets, copier, cron, cold-install, gap-closure]
completed: 2026-05-27

dependency_graph:
  requires: [07-07, 07-11]
  provides: [PRESET-06, WCI-02]
  affects: [.github/workflows/template-selftest.yml, tests/test_web_polarity.py]

tech_stack:
  added: []
  patterns:
    - "GitHub Actions preset-render job: copier copy --data-file presets/<x>.yml + just verify"
    - "Weekly schedule cron with cold-install cache-skip via github.event_name != 'schedule'"

key_files:
  modified:
    - .github/workflows/template-selftest.yml
  created:
    - tests/test_web_polarity.py
    - presets/oss-minimalist.yml
    - presets/personal.yml
    - presets/README.md

decisions:
  - "Preset-render runs as a parallel job (not a matrix combo of selftest) for clear attribution"
  - "Both presets are has_web=false so no Node/pnpm setup needed; comment notes future requirement"
  - "Cold-install achieved via github.event_name != 'schedule' on cache steps, not separate job"
  - "_schema_version key silently ignored by copier (extra data keys allowed); no preprocessing"

metrics:
  duration: "~8 minutes"
  tasks_completed: 2
  files_changed: 4
---

# Phase 7 Plan 12: CI Preset-Render + Weekly Cold-Install Summary

**One-liner:** Weekly cold-install cron + preset-render job running `copier copy --data-file presets/<x>.yml + just verify` for both public presets, closing PRESET-06 and WCI-02.

## What Was Built

### Task 1: template-selftest.yml — preset-render job + schedule trigger

Added two capabilities to `.github/workflows/template-selftest.yml`:

**PRESET-06 — preset-render job:**
- New parallel job `preset-render` with `strategy.matrix.preset: [oss-minimalist, personal]`
- Each matrix row runs: `copier copy --trust --defaults --data-file presets/<preset>.yml $GITHUB_WORKSPACE $SCRATCH`
- Then: `just verify` in the scratch directory
- Auth contract honored: `VERIFYKIT_AUTH_TOKEN: dev-token-for-tests` + `ENV: dev` at job level
- Both current presets are `has_web=false` (no Node/pnpm needed); YAML comment notes future web-true presets would need Node setup
- `_schema_version` key handled: copier silently ignores extra data keys not in prompts

**WCI-02 — weekly schedule + cold-install:**
- Added `on.schedule: - cron: "0 2 * * 1"` (weekly Monday 02:00 UTC)
- Added `workflow_dispatch:` for manual cold-install triggers
- Cache steps gated with `if: matrix.has_web == true && github.event_name != 'schedule'` so scheduled runs get cold installs (pnpm store + Playwright browser caches both skipped)

### Task 2: Polarity guard test (test_web_polarity.py)

Appended `test_web_preset_render_and_schedule` to `tests/test_web_polarity.py`. The function:
1. Parses `template-selftest.yml` from a cwd-safe path (`Path(__file__).parent.parent / ".github/workflows/..."`)
2. Asserts `preset-render` job exists with matrix containing both `oss-minimalist` and `personal`
3. Asserts at least one step run block contains `--data-file presets/`
4. Asserts `on.schedule` is present with a cron entry
5. Asserts at least one step `if` condition contains `github.event_name != 'schedule'`

All assertions pass: `uv run pytest tests/test_web_polarity.py -k "ci_matrix or preset_render or schedule"` exits 0.

Also committed the preset files (oss-minimalist.yml, personal.yml, README.md) which are required by the CI job.

## Commits

| Hash | Description |
|------|-------------|
| 127c521 | feat(ci): preset-render job + weekly cold-install schedule |
| a668108 | feat(ci): polarity guards for preset-render job and schedule trigger |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. Both preset files contain PII-free placeholder values that copier accepts; no stub data paths.

## Threat Flags

None. Both presets are placeholder-only (verified by existing `check-preset-pii` hook). No new network endpoints or auth paths introduced.

## Self-Check

Files committed:
- `.github/workflows/template-selftest.yml` — modified, committed at 127c521
- `tests/test_web_polarity.py` — created, committed at a668108
- `presets/oss-minimalist.yml` — committed at a668108
- `presets/personal.yml` — committed at a668108

Acceptance criteria:
- [x] `grep -q -- '--data-file presets/' .github/workflows/template-selftest.yml` — passes
- [x] `grep -q 'schedule:' .github/workflows/template-selftest.yml` — passes
- [x] `grep -q "github.event_name != 'schedule'" .github/workflows/template-selftest.yml` — passes
- [x] `python3 -c "import yaml; yaml.safe_load(...)"` — YAML valid
- [x] `uv run pytest tests/test_web_polarity.py -k "ci_matrix or preset_render or schedule"` — 2 passed

CI run status: expected to pass on next PR/push — not yet observed (first scheduled cold-install run validates WCI-02; PR run validates preset-render job).
