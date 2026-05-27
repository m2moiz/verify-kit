---
phase: 07-web-add-on-v0-2
plan: "11"
subsystem: harness-adapters
tags: [lost-pixel, cli-shim, argparse, visual-baseline, web, gap-closure, VIZ-03]
dependency_graph:
  requires:
    - "07-06: lostpixel_adapter.py.jinja2 parse_lostpixel_output + D-W03 git-add contract"
    - "07-10: test_web_polarity.py (append-only; serialized access)"
  provides:
    - "template/harness/web/lostpixel_adapter.py: lost-pixel-approve CLI shim (argparse main)"
    - "template/pyproject.toml.jinja2: has_web-gated lost-pixel-approve console_scripts entry"
    - "tests/test_web_polarity.py: two new polarity guards (shim present / absent + TOML validity)"
  affects:
    - "template/harness/{% if has_web %}web{% endif %}/lostpixel_adapter.py.jinja2 (main() added)"
    - "template/pyproject.toml.jinja2 ([project.scripts] extended)"
    - "tests/test_web_polarity.py (two new test functions appended)"
tech_stack:
  added:
    - "argparse (stdlib — no new dep)"
    - "subprocess (stdlib — explicit cwd, REVIEW-CHECKLIST §1 guard)"
  patterns:
    - "default-safe CLI: no flags = --dry-run (preview only); --confirm required for mutation"
    - "mutually exclusive argparse group for --dry-run / --confirm"
    - "subprocess git add with .git-walk cwd resolution (never bare relative Path)"
    - "has_web-gated console_scripts TOML entry via {% if has_web %} block"
key_files:
  modified:
    - "template/harness/{% if has_web %}web{% endif %}/lostpixel_adapter.py.jinja2 (main() + imports)"
    - "template/pyproject.toml.jinja2 (lost-pixel-approve entry)"
    - "tests/test_web_polarity.py (two test functions appended)"
decisions:
  - "MCP fix_propose --check=visual --approve wiring deliberately deferred to v0.3 (bead verify-kit-pc8) — zero-arg fix_propose() signature incompatible; documented in adapter docstring and SUMMARY"
  - "Default-safe CLI pattern: omitting flags behaves as --dry-run, never mutates without explicit --confirm"
  - "cwd for git add resolved by walking .git parents, with fallback to Path.cwd() + stderr warning"
metrics:
  duration: ~20m
  completed: "2026-05-27T19:30:00Z"
  tasks_completed: 2
  files_changed: 3
---

# Phase 7 Plan 11: lost-pixel-approve CLI Shim (VIZ-03) Summary

One-liner: Argparse-based `lost-pixel-approve` CLI shim added to `lostpixel_adapter.py.jinja2` — `--dry-run` (default-safe preview) + `--confirm` (explicit baseline staging via git add) — registered as a has_web-gated console_scripts entry, with two polarity tests proving presence/absence and valid TOML in both polarities.

## Completed Tasks

| Task | Description | Commit | Key Files |
|------|-------------|--------|-----------|
| 1 | Add lost-pixel-approve argparse shim to lostpixel_adapter.py.jinja2 | 90267a3 | template/harness/{% if has_web %}web{% endif %}/lostpixel_adapter.py.jinja2 |
| 2 | Register console_scripts entry + polarity guards | 96757dd | template/pyproject.toml.jinja2, tests/test_web_polarity.py |

## Implementation Details

### CLI shim (Task 1)

`main(argv: list[str] | None = None) -> int` added to `lostpixel_adapter.py.jinja2`:

- `--lostpixel-dir` (Path, default `web/.lost-pixel`) — where comparison-results.json lives
- `--repo-root` (Path, optional) — explicit git root for the git add subprocess cwd
- `--dry-run` — preview mode: print baselines that would be staged, exit 0, no mutation
- `--confirm` — destructive mode: run `git add <baselinePath>` for each new/updated snapshot
- Flags are mutually exclusive via argparse (error if both provided)
- No flags given → behaves as `--dry-run` (default-safe, T-07-41 mitigated)
- `subprocess.run(["git", "add", path], cwd=repo_root)` with explicit cwd (T-07-42 / REVIEW-CHECKLIST §1)
- cwd resolved by walking `.git` parents from `lostpixel_dir`; fallback to `Path.cwd()` with stderr warning
- `__all__ = ["parse_lostpixel_output", "main"]`
- `if __name__ == "__main__": raise SystemExit(main())`
- Docstring explicitly records v0.3 MCP deferral (bead verify-kit-pc8)

### Console script registration (Task 2)

`template/pyproject.toml.jinja2` [project.scripts] extended:

```toml
{% if has_web %}
lost-pixel-approve = "harness.web.lostpixel_adapter:main"
{% endif %}
```

The Jinja2 block is on its own line inside the TOML table — renders cleanly in both polarities without leaving dangling blank lines that would break TOML parsing.

### Polarity tests (Task 2)

Two new test functions appended to `tests/test_web_polarity.py`:

- `test_lostpixel_approve_shim_present`: has_web=True renders a scaffold where pyproject.toml contains `lost-pixel-approve` AND `harness/web/lostpixel_adapter.py` contains `def main` and `argparse`
- `test_lostpixel_approve_shim_absent_when_no_web`: has_web=False renders a scaffold where pyproject.toml does NOT contain `lost-pixel-approve`; both polarities verified as valid TOML via `tomllib.loads`

## MCP Deferral (Scope Ruling)

The MCP `fix_propose --check=visual --approve` wiring is **deliberately not implemented** in this plan. The current `fix_propose()` signature is zero-arg (verified `tools.py.jinja2:144`); adding per-check `--approve` routing requires a v0.3 MCP shape change tracked as bead `verify-kit-pc8`. This deferral is documented in:

1. The adapter docstring (`lostpixel_adapter.py.jinja2` module header, lines 35–40)
2. The `main()` docstring (lines 147–152)
3. This SUMMARY

The verifier must not re-flag the MCP half as a gap — it is an accepted scope boundary, not a missing feature.

## Deviations from Plan

None — plan executed exactly as written. The subprocess cwd pattern (walk .git parents) matches REVIEW-CHECKLIST §1 requirements. The TOML block placement passes the "no dangling blank" validation confirmed by the polarity tests.

## Verification Results

Tests observed green locally:

```
tests/test_web_polarity.py::test_lostpixel_approve_shim_present          PASSED
tests/test_web_polarity.py::test_lostpixel_approve_shim_absent_when_no_web PASSED
2 passed in 5.18s
```

Full non-heavy polarity subset (18 tests, including all prior phase-07 tests) also observed green in 90.33s.

Acceptance criteria checks:

- `grep -q 'argparse' lostpixel_adapter.py.jinja2` — PASSES
- `grep -q 'def main' lostpixel_adapter.py.jinja2` — PASSES
- `grep -q '__main__' lostpixel_adapter.py.jinja2` — PASSES
- `grep -qE 'dry.?run' lostpixel_adapter.py.jinja2` — PASSES
- `grep -q 'confirm' lostpixel_adapter.py.jinja2` — PASSES
- `grep -q 'lost-pixel-approve' template/pyproject.toml.jinja2` wrapped in `{% if has_web %}` — PASSES
- Rendered has_web=true pyproject.toml contains the script entry — PASSES
- Rendered has_web=false pyproject.toml does not contain the entry — PASSES
- Both polarities parse as valid TOML — PASSES (tomllib.loads asserted in test)
- `subprocess git add` uses explicit cwd (no bare relative Path) — PASSES

## Known Stubs

None — the CLI shim is fully functional. The MCP wiring deferral is an explicit scope boundary, not a stub.

## Threat Surface Scan

| Flag | File | Description |
|------|------|-------------|
| T-07-41 (mitigated) | lostpixel_adapter.py.jinja2 | --dry-run default; --confirm required for mutation; mutually exclusive guard |
| T-07-42 (mitigated) | lostpixel_adapter.py.jinja2 | subprocess git add with explicit cwd (REVIEW-CHECKLIST §1) |
| T-07-43 (accepted) | lostpixel_adapter.py.jinja2 | baseline paths from Lost Pixel's own JSON output (trusted local tool) |

No new network endpoints, auth paths, or schema changes introduced.

## Self-Check: PASSED
