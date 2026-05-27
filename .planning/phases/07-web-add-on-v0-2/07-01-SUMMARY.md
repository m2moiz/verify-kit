---
phase: 07-web-add-on-v0-2
plan: "01"
subsystem: copier-template
tags: [copier, polarity, path-gating, add-on, web, two-guard]
dependency_graph:
  requires: []
  provides:
    - has_web boolean prompt in copier.yml
    - Guard-2 bounded path-shape directories for web/ and harness/web/
    - template/harness/checks/{% if has_web %}web.py{% endif %}.jinja2 stub
    - tests/test_web_polarity.py bidirectional polarity self-test
    - render_scratch_project _vcs_ref parameter for Phase 7+ tests
  affects:
    - copier.yml (_exclude block, prompts, _message_after_copy)
    - tests/_helpers.py (render_scratch_project signature, _KNOWN_DEFAULTS)
tech_stack:
  added:
    - has_web Copier boolean prompt (default false)
  patterns:
    - Two-guard path-gating (Guard 1 = _exclude block, Guard 2 = bounded Jinja path shapes)
    - _vcs_ref parameter for rendering post-tag prompts in polarity tests
key_files:
  created:
    - template/{% if has_web %}web{% endif %}/.gitkeep
    - template/harness/{% if has_web %}web{% endif %}/.gitkeep
    - template/harness/checks/{% if has_web %}web.py{% endif %}.jinja2
    - tests/test_web_polarity.py
  modified:
    - copier.yml
    - tests/_helpers.py
decisions:
  - "_vcs_ref='HEAD' required in Phase 7+ polarity tests: without it, Copier clones the v0.1.0 tag which predates has_web, causing Guard-2 conditionals to silently resolve to empty string and the web/ directory to not be created. Addressed by adding optional _vcs_ref parameter to render_scratch_project."
metrics:
  duration: 17m
  completed: "2026-05-27T00:37:42Z"
  tasks_completed: 3
  files_changed: 5
---

# Phase 7 Plan 01: Copier Prompt + Two-Guard Path Gating Summary

One-liner: has_web Copier prompt with two-guard path gating (11 _exclude entries + Guard-2 Jinja directories) guarded by a 5-test bidirectional polarity suite.

## Completed Tasks

| Task | Description | Commit | Key Files |
|------|-------------|--------|-----------|
| 1 | Add has_web prompt + 11 _exclude entries | ca676f6 | copier.yml |
| 2 | Create Guard-2 bounded path-shape placeholders | 39c05ee | template/{%if has_web%}web{%endif%}/.gitkeep, template/harness/{%if has_web%}web{%endif%}/.gitkeep, template/harness/checks/{%if has_web%}web.py{%endif%}.jinja2 |
| 3 | Write bidirectional polarity self-test | 717fa3e | tests/test_web_polarity.py, tests/_helpers.py |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] render_scratch_project used tag-pinned vcs_ref, breaking Phase 7 prompts**

- **Found during:** Task 3 (test execution)
- **Issue:** `render_scratch_project` in `tests/_helpers.py` did not pass `vcs_ref` to Copier. Without it, Copier defaulted to the latest git tag (`v0.1.0`), which predates the `has_web` prompt. The Worker rendered `{% if has_web %}web{% endif %}` as empty string (since `has_web` was absent from the answer context), causing the Guard-2 directory to be silently omitted from the scaffold even with `has_web=True`.
- **Fix:** Added optional `_vcs_ref` parameter to `render_scratch_project`. Phase 7+ tests pass `_vcs_ref="HEAD"` to force rendering from current HEAD. All existing Phase 1-6 tests continue to use the default (no `_vcs_ref`), preserving backward compatibility. Also added `has_web: False` to `_KNOWN_DEFAULTS` so future copier.yml introspection picks it up.
- **Files modified:** `tests/_helpers.py`
- **Commit:** 717fa3e (part of Task 3 commit)

## Verification Results

All 5 polarity tests pass (observed, not predicted):

```
tests/test_web_polarity.py::test_web_polarity_directory_presence[True] PASSED
tests/test_web_polarity.py::test_web_polarity_directory_presence[False] PASSED
tests/test_web_polarity.py::test_web_false_no_dotfile_leaks PASSED
tests/test_web_polarity.py::test_web_false_no_literal_jinja_brace_filenames PASSED
tests/test_web_polarity.py::test_web_true_no_literal_jinja_brace_filenames PASSED
5 passed in 12.93s
```

`copier.yml` parses as valid YAML. Guard-2 source paths (`find template -name '*has_web*'`) returns exactly the three Task 2 artifacts.

## Known Stubs

`template/harness/checks/{% if has_web %}web.py{% endif %}.jinja2` — intentional placeholder. Plan 07-06 will overwrite with `@register` entries for web.vitest, web.playwright, web.lighthouse, web.axe, web.lost_pixel. The stub ships as an importable no-op so the import path succeeds when has_web=true without any actual check registrations.

## Threat Surface Scan

No new network endpoints, auth paths, or trust boundaries introduced. This plan adds a Copier prompt and template path guards only. The STRIDE threat register items T-07-01 (dotfile coverage) and T-07-02 (_CLEAN_ENV) from the plan were both addressed: dotfile patterns were added to _exclude, and _CLEAN_ENV is imported in the test file.

## Self-Check: PASSED

---
