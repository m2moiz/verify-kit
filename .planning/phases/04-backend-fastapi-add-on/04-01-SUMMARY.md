---
phase: 4
plan: "04-01"
title: "Copier prompts + add-on path gating"
subsystem: copier-template
tags: [copier, path-gating, has_backend, has_db, has_logfire, has_fastapi_mcp]
dependency_graph:
  requires: []
  provides:
    - "two-guard contract: copier.yml _exclude block (primary gate)"
    - "template/{% if has_backend %}app{% endif %}/.gitkeep (top-level unique-dir gate)"
    - "template/tests/backend/{% if has_backend %}.gitkeep{% endif %} (filename-level gate)"
    - "tests/test_phase04_scaffold_polarity.py (polarity contract enforcement)"
  affects:
    - copier.yml
    - .gitignore
    - template/
    - tests/
tech_stack:
  added: []
  patterns:
    - "Two-guard path gating: _exclude (primary) + Jinja path conditional (defense-in-depth)"
    - "filename-level gate for dirs whose parent is universal (tests/backend/)"
    - "top-level unique-dir gate for dirs with no collision risk (app/)"
key_files:
  created:
    - template/{% if has_backend %}app{% endif %}/.gitkeep
    - template/tests/backend/{% if has_backend %}.gitkeep{% endif %}
    - tests/test_phase04_scaffold_polarity.py
  modified:
    - copier.yml
    - .gitignore
decisions:
  - "Use copier Python API (not subprocess) in polarity tests to avoid worktree-submodule false positive"
  - "Exclude .claude/worktrees/ from .gitignore (Rule 3 auto-fix) so copier git clone operations succeed"
metrics:
  duration: "~12 minutes"
  completed: "2026-05-21"
  tasks_completed: 4
  files_count: 5
requirements: [API-01]
---

# Phase 4 Plan 04-01: Copier Prompts + Add-on Path Gating Summary

## One-liner

Declarative `_exclude` block in copier.yml gates backend/db files at render time; Jinja path conditionals provide defense-in-depth via two permitted shapes only (top-level unique-dir + filename-level).

## Two-Guard Contract (canonical reference for downstream plans)

This plan defines the **authoritative path-gating contract** for Phase 4. All downstream plans (04-02..04-07) must use one of the two permitted gate shapes below and MUST NOT introduce new shapes.

### Primary gate: `_exclude` block in copier.yml

Location: `copier.yml` lines 20–34 (after `_envops` block).

When `has_backend=false`, the following exclusion rules fire:
```yaml
_exclude:
  - "{% if not has_backend %}app{% endif %}"
  - "{% if not has_backend %}app/**{% endif %}"
  - "{% if not has_backend %}tests/backend{% endif %}"
  - "{% if not has_backend %}tests/backend/**{% endif %}"
  - "{% if not has_backend %}Dockerfile{% endif %}"
  - "{% if not has_backend %}docker-compose.yml{% endif %}"
  - "{% if not has_backend %}.dockerignore{% endif %}"
  - "{% if not has_db %}alembic{% endif %}"
  - "{% if not has_db %}alembic/**{% endif %}"
  - "{% if not has_db %}alembic.ini{% endif %}"
```

### Secondary gate: two permitted Jinja path shapes

**Shape 1 — top-level unique-dir** (use when the dir name is unique at template root):
```
template/{% if has_backend %}app{% endif %}/leaf.py.jinja2
```
Example: `template/{% if has_backend %}app{% endif %}/.gitkeep`

**Shape 2 — filename-level gate** (use when the parent dir is pre-existing/universal):
```
template/tests/backend/{% if has_backend %}leaf.py{% endif %}.jinja2
```
Example: `template/tests/backend/{% if has_backend %}.gitkeep{% endif %}`

### BANNED shape (enforced by T03 polarity test)
```
template/{% if has_backend %}tests{% endif %}/backend/leaf.py   ← BANNED
template/{% if has_backend and has_db %}app{% endif %}/db.py    ← BANNED
```
The `rglob('*')` walk in `test_has_backend_false_has_no_empty_segment_leaks` catches any leak.

### Polarity test enforcement

`tests/test_phase04_scaffold_polarity.py` (commit 279f149) asserts the contract for all required polarities. Downstream plans that add files must ensure these three tests continue to pass.

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| T00  | `_exclude` block in copier.yml (primary gate, 13 entries) | 330d3f3 |
| T01  | Verified `has_backend`, `has_db`, `has_logfire`, `has_fastapi_mcp` prompts with correct `when:` chains | 330d3f3 |
| T02  | Created two placeholder .gitkeep files using the two permitted gate shapes | 330d3f3 |
| T03  | Polarity test with 3 test functions (true-tree, zero-files, no-leaks) | 279f149 |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree directory breaks copier git submodule update**

- **Found during:** T03 (all copier invocations failed)
- **Issue:** The GSD agent worktree at `.claude/worktrees/agent-ae5aba42808d0edba/` has a `.git` file (standard git worktree structure). When copier clones the repo to render the template, it runs `git submodule update --recursive --force`. Git detects the worktree directory as an unregistered submodule candidate and aborts with "No url found for submodule path". This blocked every copier render — including all pre-existing tests (test_copier_render.py, test_p3_template_smoke.py).
- **Fix:** Added `.claude/worktrees/` to `.gitignore`. Git no longer surfaces the directory during submodule discovery. Copier renders proceed normally.
- **Files modified:** `.gitignore`
- **Commit:** 330d3f3

**2. [Rule 1 - Design] Used Python API instead of subprocess for T03**

- **Found during:** T03 design
- **Issue:** The plan called for `subprocess.run(..., cwd=tmp_path, timeout=60)` invocations. Using subprocess would have triggered the same worktree/submodule error (worktree fix in deviation #1 addresses this at the root). However, the copier Python API (`run_copy`) is cleaner — it accepts `dst_path` directly, requires no shell PATH, and makes the `cwd=` requirement moot (the API never changes process cwd).
- **Fix:** T03 uses `render_scratch_project()` from `tests/_helpers.py` which wraps `run_copy()`. The `tmp_path` pytest fixture provides the scratch directory; process cwd is irrelevant.
- **Files modified:** `tests/test_phase04_scaffold_polarity.py`
- **Impact:** Functionally equivalent to the plan's subprocess approach; simpler and more robust. The REVIEW-CHECKLIST §1 cwd-leak invariant is satisfied because `render_scratch_project` always renders into the caller-supplied `tmp_path`.

## Known Stubs

None. The placeholder `.gitkeep` files are intentional stubs that downstream plans (04-02..04-07) will expand. They are not stubs blocking this plan's goal — the gate contract is fully implemented and tested.

## Threat Flags

None. This plan adds no network endpoints, auth paths, or schema changes. It only modifies the template rendering path (copier.yml exclusion rules) and adds test infrastructure.

## Self-Check: PASSED

- [x] `template/{% if has_backend %}app{% endif %}/.gitkeep` exists on disk
- [x] `template/tests/backend/{% if has_backend %}.gitkeep{% endif %}` exists on disk
- [x] `copier.yml` contains `_exclude` block with 13 entries
- [x] `tests/test_phase04_scaffold_polarity.py` exists with 3 test functions
- [x] `uv run pytest tests/test_phase04_scaffold_polarity.py -v` exits 0 (3 passed)
- [x] Commits 330d3f3 (production) and 279f149 (test) exist on `feat/phase-4-backend`
