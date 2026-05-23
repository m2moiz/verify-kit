---
phase: 06-template-self-test-documentation
plan: "06-09"
plan_name: llm-readme-pass
subsystem: docs
tags: [phase-6, readme, llm, deferred]
status: partial
dependency_graph:
  requires: ["06-06"]
  provides: ["pre-checked-llm-readme-state"]
  affects: ["template/README.md.jinja2"]
tech_stack:
  added: []
  patterns: ["deferred human-checkpoint pattern (same as 06-06 visual-asset checkpoints)"]
key_files:
  created:
    - .planning/phases/06-template-self-test-documentation/06-09-SUMMARY.md
  modified: []
decisions:
  - "Human read-through deferred to follow-up bead per user direction; structural pre-checks done now, prose-quality judgment deferred"
  - "verify-kit-1v6 closed as superseded by verify-kit-adl (not closed as resolved) — the bead's substance is the read, which is still pending"
metrics:
  duration: ~17m (mostly polarity test render-and-grep loop)
  completed: 2026-05-23
---

# Phase 6 Plan 09: LLM README Pass (PARTIAL — read-through deferred)

Pre-checked the Phase 5 consumer-README LLM section for structural soundness; deferred the prose-quality human read to a follow-up bead per user direction (same execution pattern as 06-06's deferred visual-asset checkpoints).

## Status

**Partial.** The autonomous pre-check work is done. The human-judgment read-through is deferred to **bead verify-kit-adl**.

| Sub-task | Status |
|----------|--------|
| Render scratch project to `/tmp/scratch-06-09` with `has_llm=true` | DONE |
| Confirm `harness/llm.py` exports (`call_llm`, `llm_call`, `cost_budget`) | DONE — all three present (lines 409, 275, 369 of rendered `harness/llm.py`) |
| Confirm `justfile` `eval` recipe still exists | DONE — line 103 of rendered justfile |
| Confirm asserted README keywords present (call_llm, llm_call, cost_budget, cost_usd, pydantic_ai, output_type, Authorization=Basic, just eval) | DONE — grep hits all keywords |
| Phase 5 polarity test green (Task 2) | DONE — 69/69 passed in 956s |
| Human read-through of LLM section (Task 1 checkpoint) | **DEFERRED** to verify-kit-adl |
| Possible prose edits + re-render + re-test | **DEFERRED** to verify-kit-adl |
| Close verify-kit-1v6 | DONE — closed as superseded |

## Tasks Deferred

Per user direction, the human-read checkpoint (plan Task 1) is pre-authorized to defer. The deferred work is tracked in **bead verify-kit-adl** (priority 2):

> Phase 6 06-09: Phase 5 LLM README human-read pass (deferred)

That bead contains the full checklist for the deferred work:
1. Re-render the scratch project (command captured in bead description)
2. Open `/tmp/scratch-06-09/README.md` in a markdown previewer
3. Read §3 LLM section end-to-end, applying the plan's per-bullet accuracy checks
4. Edit `template/README.md.jinja2` if issues found
5. Re-run polarity test to confirm no keyword regression
6. Commit edits (or no-op) and close verify-kit-adl with disposition

## Bead Handoff

- **verify-kit-1v6** (original Phase 5 README LLM read-through tracker) → **CLOSED** with reason: *"Superseded by verify-kit-adl — Phase 6 plan 06-09 execution deferred the human read-through per user direction; new bead tracks the deferred read-through work explicitly."*
- **verify-kit-adl** (new) → **OPEN, P2** — the actual read-through work.

This pattern matches 06-06's handling of the deferred visual-asset checkpoints: structural work lands now, judgment work flows to a follow-up bead.

## Verification

Phase 5 polarity test (`tests/test_phase05_polarity.py`) green at the end of this plan with **69/69 passed** in 956.54s. The test grep-asserts the structural keywords the deferred read-through must preserve.

```
================== 69 passed, 1 warning in 956.54s (0:15:56) ===================
```

## Deviations from Plan

None. Pre-checks ran clean; deferral is per the documented execution-contract pattern, not a deviation from intent. No template files were edited.

## Threat Surface

None — no template content was modified.

## Self-Check: PASSED

- `/tmp/scratch-06-09/README.md` exists and contains the expected keywords (verified via grep)
- `verify-kit-1v6` closed (bead query confirms)
- `verify-kit-adl` open and carries the deferred work (bead query confirms)
- Polarity test passes (69/69)
