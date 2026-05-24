---
phase: 06-template-self-test-documentation
plan: "06-13"
plan_name: backlog-closeout
type: execute
wave: 8
gap_closure: true
closes_beads:
  - verify-kit-r7v
  - verify-kit-plk
  - verify-kit-c5a
  - verify-kit-xw4
files_modified:
  - template/justfile.jinja2
  - template/pyproject.toml.jinja2
  - "template/{% if has_backend %}app{% endif %}/settings.py.jinja2"
  - tests/test_phase04_integration.py
  - tests/test_phase04_scaffold_polarity.py
  - tests/test_logfire_opt_in.py  # NEW
  - tests/test_phase03_fastmcp3_compat.py  # NEW
commits:
  - 8ff26ff fix(justfile): trap cleanup in verify-backend recipe
  - 38c190e test(scaffold): assert no orphan containers after verify-backend
  - 9822d9d test(scaffold): polarity cell for has_backend=T, has_db=F
  - cc90d99 test(logfire): assert LOGFIRE_TOKEN runtime guard in rendered app/main.py
  - c7219fb test(mcp): fastmcp 3.x compat — harness.mcp imports + ToolAnnotations
duration: ~25 minutes
completed: 2026-05-24
---

# Phase 6 Plan 06-13: backlog-closeout Summary

Closes the 4 pre-Phase-6 backlog beads (`r7v`, `plk`, `c5a`, `xw4`) in one
bundled plan. Per-task fixes landed inline; 5 atomic conventional commits.

## Tasks executed

### Task 1 — verify-kit-r7v: orphan-container teardown (P2)

**(a) Recipe fix:** `template/justfile.jinja2:verify-backend` now uses
`trap '... EXIT'` with project-label-based teardown (`docker compose -p
"$_vk_project" down -v --remove-orphans`) instead of compose-file-based
teardown. The original `|| true` silently swallowed compose-parse errors
when the compose file itself was broken — leaking jaeger/postgres containers.

**(b) Test:** new `test_verify_backend_full_path_leaves_no_orphan_containers`
in `tests/test_phase04_integration.py` exercises both success and failure
paths. Success path renders + runs `just verify-backend` end-to-end; failure
path corrupts `docker-compose.yml` mid-recipe and verifies the trap STILL
tears down via project label.

**Verify output:** `tests/test_phase04_integration.py::test_verify_backend_full_path_leaves_no_orphan_containers PASSED [100%] in 33.56s`

**First red iteration** caught the actual bug: when compose file is
unparseable, the old `docker compose down` failed, `|| true` masked it,
and `scratch-jaeger-1` survived. Fix is project-label routing.

### Task 2 — verify-kit-plk: (has_backend=T, has_db=F) polarity cell (P2)

**Test:** new `test_has_backend_true_has_db_false_no_db_files_in_scaffold`
in `tests/test_phase04_scaffold_polarity.py` asserts the missing polarity
cell.

**Surfaced two real bugs (Rule 2 — missing critical gating):**
1. `template/{% if has_backend %}app{% endif %}/settings.py.jinja2`: the
   `DATABASE_URL` field on `Settings` was UNGATED — it appeared in every
   has_backend=True render regardless of has_db. Now wrapped in
   `{% if has_db %}`.
2. `template/pyproject.toml.jinja2`: the `[tool.ruff.lint.per-file-ignores]`
   entries for `alembic/env.py` and `alembic/versions/*` were UNGATED —
   alembic appearing in pyproject when has_db=False. Now wrapped in
   `{% if has_db %}`.

**Verify output:** `tests/test_phase04_scaffold_polarity.py 4 passed in 16.46s`
(3 existing cells + 1 new — no regressions).

### Task 3 — verify-kit-c5a: LOGFIRE_TOKEN runtime guard (P2)

**Test:** new `tests/test_logfire_opt_in.py` (file did not exist at repo
level — only at template level). Two tests:
- `test_logfire_not_imported_when_has_logfire_false` — negative polarity
- `test_logfire_token_guard_present_when_has_logfire_true` — asserts
  `LOGFIRE_TOKEN` + `os.environ.get/os.getenv` + `send_to_logfire=False`
  fallback all appear in rendered `app/main.py`.

**Source state:** the guard pattern is already wired in
`template/{% if has_backend %}app{% endif %}/main.py.jinja2:148-163`
(present since Phase 4). This test pins it so a future replan can't
silently drop it.

**Verify output:** `tests/test_logfire_opt_in.py 2 passed in 8.56s`.

### Task 4 — verify-kit-xw4: fastmcp 3.x compat (P2)

**Test:** new `tests/test_phase03_fastmcp3_compat.py`. Renders
has_backend=True+has_llm=True scratch, `uv sync` to materialize fastmcp
3.x per Phase 5's `fastmcp>=3.3,<4` pin, then exercises:
- import `harness.mcp.server.serve` + `harness.mcp.tools.register_tools`,
  construct a `FastMCP(name='probe')`, call `register_tools(mcp, cwd=Path('.'))`.
- construct `mcp.types.ToolAnnotations(readOnlyHint=..., destructiveHint=...,
  idempotentHint=...)`.

**Plan deviation:** the plan's body referenced a non-existent `build_server`
symbol; the actual public API per `template/harness/mcp/server.py.jinja2`
is `serve(...)`. The test was written against the real symbol surface.

**Verify output:** `tests/test_phase03_fastmcp3_compat.py 2 passed in 22.01s`.
Phase 3 MCP code is fully 3.x-compatible as-is; no source changes required.

## Beads closed

```
✓ Closed verify-kit-r7v: Closed by 06-13 backlog-closeout sweep
✓ Closed verify-kit-plk: Closed by 06-13 backlog-closeout sweep
✓ Closed verify-kit-c5a: Closed by 06-13 backlog-closeout sweep
✓ Closed verify-kit-xw4: Closed by 06-13 backlog-closeout sweep
```

## Final cold-start gate result

Per completion-checklist last item: render fresh all-on scratch + `just verify`
end-to-end. Result: **`just verify` exited 1** because the harness backend
check timed out at 600s.

**This is NOT a regression from this plan.** Drill-down:
- 24 backend tests collect cleanly in 0.16s.
- Hang is during execution — backend pytest needs the docker stack up.
- The harness `verify` umbrella runs `pytest tests/backend/` directly,
  WITHOUT calling `verify-backend` first to bring up the stack.
- r7v's scope was the `verify-backend` recipe's container leak, which IS
  fixed (asserted by Task 1's test, passing).

The umbrella-vs-recipe timeout is a separate, pre-existing issue logged
in `.planning/phases/06-template-self-test-documentation/deferred-items.md`
with a suggested follow-up bead for v0.1.2 or Phase 7 review.

## Deviations from Plan

### Rule 2 — auto-add missing critical functionality

Task 2 surfaced two unguarded template fragments (`DATABASE_URL` field
in `app/settings.py.jinja2`; `alembic/*` ruff-ignores in
`pyproject.toml.jinja2`) that were leaking into has_db=False scaffolds.
Both gated inline; documented in commit `9822d9d`.

### Plan body referenced non-existent symbol

Task 4's plan body wrote a test calling `from harness.mcp.server import
build_server` — but the actual exported symbol is `serve` per
`harness/mcp/server.py.jinja2:88` (`__all__ = ["serve"]`). Test written
against the real API. No follow-up filed; plan-body typo only.

### Pre-existing test failure (out of scope)

`tests/test_phase04_optin_polarity.py::test_optin_polarity_matrix[True-False]`
fails because `logfire>=` dep is missing from `pyproject.toml` when
`has_logfire=true`. Confirmed pre-existing via `git stash` round-trip
against this plan's edits. Not in plan scope; not fixed.

## Known Stubs

None.

## Self-Check: PASSED

- Files exist:
  - `template/justfile.jinja2` (modified — trap)
  - `template/pyproject.toml.jinja2` (modified — alembic gate)
  - `template/{% if has_backend %}app{% endif %}/settings.py.jinja2` (modified — DATABASE_URL gate)
  - `tests/test_phase04_integration.py` (modified — orphan test)
  - `tests/test_phase04_scaffold_polarity.py` (modified — TF cell)
  - `tests/test_logfire_opt_in.py` (NEW)
  - `tests/test_phase03_fastmcp3_compat.py` (NEW)
- Commits exist: 8ff26ff, 38c190e, 9822d9d, cc90d99, c7219fb (all in `git log --oneline -7`)
- All 4 beads confirmed closed by `bd close` output.
