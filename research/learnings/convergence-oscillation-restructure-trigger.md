---
title: Convergence oscillation = restructure (rule 08 in action)
aliases: [oscillation-trigger, restructure-not-grind, rule-08-restructure]
tags: [verify-kit, learnings, atomic, reviews, gsd, rule-08, convergence]
created: 2026-05-22
last_updated: 2026-05-22
source_session: [[session-2026-05-22-phase-5-llm-and-verification]]
---

# Convergence oscillation = restructure (rule 08 in action)

> [!abstract] Pattern
> When the convergence-loop HIGH count stops trending monotone-decreasing — especially when it oscillates in a narrow band like 1 → 3 → 1 — the problem is **structural plan coupling**, not surface drift. More cycles won't help. Restructure instead.

## The data point this came from

Phase 5 LLM Add-on convergence trajectory:

| Cycle | HIGHs | Source |
|---|---|---|
| internal | 0 | gsd-plan-checker |
| 1 | 8 | Codex first adversarial |
| 2 | 5 | Codex post-replan |
| 3 | 2 | Codex post-replan, exit at max-cycles |
| (manual fix 1) | — | commit [`823b71c`](#) |
| 4 | 3 | Codex adversarial re-review of fix 1 |
| (manual fix 2) | — | commit [`8366ac9`](#) |
| 5 | 1 | Codex re-review |
| (manual fix 3) | — | commit [`26625c5`](#) |
| 6 | **3** | Codex — non-monotone, **rule 08 fires** |
| **(restructure)** | — | commit [`48604cc`](#) — moved gate test to pytester contract test |
| 7 | 1 | post-restructure — substantive surgical bug only |
| (surgical fix) | — | commit [`d367b65`](#) — `sys.path.insert` for pytester |
| 8 | 0 | CONVERGED |

Trajectory: ∞ → 8 → 5 → 2 → 1 → **3** → 1 → 0. The 1 → 3 oscillation in cycles 5 → 6 is the signal.

## What the oscillation actually was

Three rounds of manual-fix on the **same fragile inline `<verify>` subprocess probe**. Each fix introduced a fresh meta-bug:

1. **Cycle 4 → fix 1:** added substring checks for `record_mode != "none"`. Codex caught: boolean precedence bug — `assert '!=' in text and '"none"' in text or "'none'" in text` parses as `(A and B) or C`, so the assertion passed against the OLD self-defeating shape.
2. **Cycle 5 → fix 2:** replaced substring check with `pytest --collect-only --record-mode=once`. Codex caught: `--collect-only` doesn't execute autouse fixtures, so the probe wasn't actually exercising the gate.
3. **Cycle 6 → fix 3:** materialized a probe test in the scratch render. Codex caught:
   - Case (b) assertion (`returncode != 0 + no "skipped"`) was a false-positive sieve — missing pytest-recording (exit 4), collection errors, ImportError all pass while the fixture is never exercised.
   - `uv run --no-project` bypasses pyproject so `pytest-recording` is not even installed.
   - No clean env passed to subprocess — `VIRTUAL_ENV` / `UV_PROJECT_ENVIRONMENT` leak in.

The fixes had grown more complex than the fixture they were verifying. Each cycle added another defensive substring or subprocess flag; each cycle introduced a new way for it to be wrong.

> [!quote] Evidence
> File: `.planning/phases/05-llm-add-on/05-REVIEWS.md` cycles 4-6.
> Source rule: `~/.claude/rules/08-plan-convergence-workflow.md`:
> > "Diagnostic signal: two consecutive cycles with HIGH count ≥ 2 and the trajectory is not monotone-decreasing. That's the moment to switch from 'tighten contracts inside the existing structure' to 'change the structure.'"

## What the restructure actually did

Per REVIEW-CHECKLIST §3 (contracts live with producers): move the record-mode gate **out** of the inline `<verify>` subprocess probe and **into** a real pytest contract test owned by the producer plan.

- Before: `<verify>` block tried to assert fixture behavior via `subprocess.run(['uv', 'run', 'pytest', ...])` with substring + exit-code parsing.
- After: a real test file `template/tests/llm/{% if has_llm %}test_skip_fixture_contract.py{% endif %}.jinja2` uses pytest's `pytester` plugin (canonical pytest-fixture-testing mechanism). The `<verify>` block just runs that test and checks exit 0.

The structural change eliminated the entire class of meta-bug because the new shape uses pytest's documented API for testing fixtures instead of cobbling together subprocess + substring + flag.

> [!quote] Evidence
> Commit [`48604cc`](#): "docs(phase-5): restructure record-mode gate per rule 08 oscillation"
> File: `template/tests/llm/{% if has_llm %}test_skip_fixture_contract.py{% endif %}.jinja2`
> Plan: `.planning/phases/05-llm-add-on/05-03-PLAN.md` Task 2 `<action>` block

## What to do about it

> [!tip] Apply
> - **Watch the trajectory.** If cycle-N HIGH count ≥ cycle-(N-1) HIGH count AND both are ≥ 2, that's the trigger.
> - **Don't keep grinding the same fragile shape.** "One more tightening" on a verify-block that has had 3+ rounds of fixes is rarely the right move.
> - **Move contract tests to the producer plan.** Inline `<verify>` blocks are fine for cheap shape checks (file exists, regex matches). They are NOT fine for behavioral contracts that need to run in an environment that matches production.
> - **Use the canonical tooling.** When testing pytest fixtures, use pytest's `pytester`. When testing template renders, use `render_scratch_project` (the project's Python API, not raw `subprocess.run` with copier).

## Cost of getting it wrong

3 manual-fix rounds (cycles 4, 5, 6) + 3 adversarial re-reviews. ~30-60 minutes total. Restructure took ~5 minutes to design + execute and closed the loop in one cycle.

If I had skipped Codex's 1 → 3 signal and applied a fourth surgical fix, I'd have just introduced another meta-bug. The signal was right; the restructure was the correct response.

## Related patterns

- [[internal-checker-vs-external-reviewer]] — Codex's adversarial framing surfaces these meta-bugs that the planner's own perspective hides.
- [[manual-fix-meta-bug-cascade]] — the failure mode that triggers oscillation in the first place.
- *memory: `contracts_live_with_producers`* — REVIEW-CHECKLIST §3, the underlying principle.

## See also

- Project rule 08: `~/.claude/rules/08-plan-convergence-workflow.md`
- *memory: `convergence_oscillation_means_restructure`*
- *memory: `post_restructure_prose_drift`* — after restructure, expect 1-2 cycles of stale-prose cleanup
