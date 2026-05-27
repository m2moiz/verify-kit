---
phase: 07-web-add-on-v0-2
plan: "09"
subsystem: copier-template
tags: [vscode, ide, tailwind-intellisense, eslint, playwright, web, gap-closure, DEV-W04]
dependency_graph:
  requires:
    - has_web boolean prompt in copier.yml (07-01)
    - template/{% if has_web %}web{% endif %} Guard-2 directory (07-01)
    - two-guard _exclude block for web/ (07-01)
  provides:
    - template/{% if has_web %}web{% endif %}/.vscode/extensions.json
    - template/{% if has_web %}web{% endif %}/.vscode/settings.json
    - two-guard copier.yml _exclude entries for web/.vscode
    - polarity tests: test_web_vscode_presence + test_web_vscode_no_leak
  affects:
    - copier.yml (_exclude block)
    - tests/test_web_polarity.py (two new test functions appended)
tech_stack:
  added: []
  patterns:
    - Two-guard path-gating for dotfile directory (REVIEW-CHECKLIST §3)
    - Plain JSON .vscode files (no Jinja — no template substitution needed)
key_files:
  created:
    - "template/{% if has_web %}web{% endif %}/.vscode/extensions.json"
    - "template/{% if has_web %}web{% endif %}/.vscode/settings.json"
  modified:
    - copier.yml
    - tests/test_web_polarity.py
decisions:
  - "shadcn has no first-party VS Code extension; the shadcn-aware IDE story IS Tailwind CSS IntelliSense (bradlc.vscode-tailwindcss) + Prettier (esbenp.prettier-vscode). These four extensions cover the full stack: Tailwind completions, ESLint linting, Playwright test runner, Prettier formatting."
  - "tailwindCSS.experimental.configFile set to 'src/index.css' (Tailwind v4 CSS-first entry). IntelliSense v4 auto-detects CSS-first mode via the @import 'tailwindcss' directive in that file."
  - "Two-guard _exclude entries added explicitly even though the existing web/.* glob already covers .vscode (a dotfile-prefixed directory). Belt-and-suspenders: explicit entries make DEV-W04 intent legible and survive any future narrowing of the dotfile globs."
  - "Polarity leak assertion uses web_dir.rglob('.vscode') (scoped to web/) rather than scratch.rglob('*') filtering on '.vscode' in p.parts — the top-level .vscode/ ships in all scaffold polarities and must not be flagged as a leak."
metrics:
  duration: 25m
  completed: "2026-05-27T00:00:00Z"
  tasks_completed: 2
  files_changed: 4
---

# Phase 7 Plan 09: web/.vscode/ DEV-W04 Gap Closure Summary

One-liner: Closes DEV-W04 by shipping `web/.vscode/extensions.json` + `web/.vscode/settings.json` under the `has_web` Guard-2 path with two-guard `_exclude` entries and bidirectional polarity tests.

## Completed Tasks

| Task | Description | Commit | Key Files |
|------|-------------|--------|-----------|
| 1 | Create web/.vscode/extensions.json + settings.json | 2b37c16 | template/{%if has_web%}web{%endif%}/.vscode/extensions.json, settings.json |
| 2 | Two-guard _exclude entries + polarity tests | 745c917 | copier.yml, tests/test_web_polarity.py |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Polarity leak assertion was too broad**

- **Found during:** Task 2 test execution
- **Issue:** `test_web_vscode_no_leak` used `scratch.rglob("*") filtering on ".vscode" in p.parts` which matched the top-level `.vscode/` directory that ships in ALL scaffold polarities (has_web=True and has_web=False). The test failed with:
  ```
  web/.vscode files leaked when has_web=False:
    .vscode
    .vscode/settings.json
    .vscode/extensions.json
    .vscode/launch.json
    .vscode/tasks.json
  ```
  These are the repo-level .vscode files (shipped unconditionally), not web/.vscode files.
- **Fix:** Narrowed the rglob to `web_dir.rglob(".vscode")` scoped to `scratch / "web"`. Since web/ itself doesn't exist when has_web=False, the list is always empty in the failing polarity.
- **Files modified:** `tests/test_web_polarity.py`
- **Commit:** 745c917 (included in Task 2 commit)

## Verification Results

All 5 targeted tests pass (observed):

```
tests/test_web_polarity.py::test_web_polarity_directory_presence[True] PASSED
tests/test_web_polarity.py::test_web_polarity_directory_presence[False] PASSED
tests/test_web_polarity.py::test_web_false_no_dotfile_leaks PASSED
tests/test_web_polarity.py::test_web_vscode_presence PASSED
tests/test_web_polarity.py::test_web_vscode_no_leak PASSED
5 passed in 6.97s
```

`grep -c 'web/.vscode' copier.yml` returns 2 (two-guard entries confirmed).

## What "shadcn-aware" means in this context

shadcn/ui ships no first-party VS Code extension. The IDE experience it expects is:
1. **Tailwind CSS IntelliSense** (`bradlc.vscode-tailwindcss`) — autocompletes Tailwind v4 utility classes and CSS variables in class attributes and TSX props.
2. **Prettier** (`esbenp.prettier-vscode`) — formats `.tsx` files with consistent JSX formatting that shadcn components use.

The `extensions.json` recommendation set (Tailwind IntelliSense + ESLint + Playwright Test + Prettier) fully covers the verify-kit web add-on IDE story.

## Known Stubs

None. Both `.vscode` files are complete with all required keys.

## Threat Surface Scan

T-07-37 (web/.vscode leak under has_web=false) is mitigated: polarity test `test_web_vscode_no_leak` proves no leak under has_web=false. T-07-36 (recommended extension IDs) is accepted: all four recommended IDs are well-known marketplace publishers.

No new trust boundaries introduced.

## Self-Check: PASSED

Files present:
- `template/{% if has_web %}web{% endif %}/.vscode/extensions.json` — FOUND
- `template/{% if has_web %}web{% endif %}/.vscode/settings.json` — FOUND
- `copier.yml` with 2 web/.vscode entries — FOUND (grep -c returns 2)

Commits present:
- 2b37c16 — feat(vscode): add web/.vscode/extensions.json + settings.json (DEV-W04)
- 745c917 — feat(vscode): two-guard .vscode _exclude + polarity leak guard
