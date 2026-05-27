---
phase: 07
phase_name: "web-add-on-v0-2"
retro_date: 2026-05-27
tooling_version: "2"   # source-grounding (drift-guard) reviewer fork active since Phase 5
---

# Phase 7 Retrospective

## Quantitative

| Metric | Value | Notes |
|--------|-------|-------|
| Cycles to converge (plan phase) | ~2 (partial data) | Planning spanned prior sessions; 07-REVIEWS.md records a final adversarial source-grounding pass that surfaced 5 NEW HIGH blockers after the in-house checker cleared the plans |
| HIGHs per cycle | 5 (adversarial pass) | All 5 were API-surface drift: `--check='web.*'` glob, per-check MCP auto-expose, `fix_propose --check/--finding`, SARIF run-merge, `ErrorEnvelope.fixable` — none existed in the shipped harness |
| Manual fixes required | 2 (execution-time) | modal aria-hidden fix (903b5fa), axe color-contrast oklch disable (089e58a) — both orchestrator fixes during the post-merge gate, not planning |
| Restructure required | no | original 7-plan structure held; gap closure added 5 serial plans (07-08..12) |
| Patch-replan invoked | no | gap closure used a fresh single-pass gsd-planner run, not patch-replan |
| Stall hook fired | no | |
| Wall-clock hours (planning) | n/a (prior sessions) | |
| Wall-clock hours (execution) | ~1 working day across 3 interrupted sessions | session limit (mid-07-02) + laptop restart (mid-07-06 spawn) + resumed |
| Tests at phase end | 358 / 358 | +17 skipped (CI-path: bundle budget, live-backend SSE); 0 failed |

## Qualitative

### What worked

- **Worktree isolation made interruption recovery clean.** A session limit hit mid-07-02 and a laptop restart hit mid-07-06 spawn; in both cases zero work was lost because each executor's commits lived on an isolated `worktree-agent-*` branch, and the main branch was never left partial. Recovery was: inspect the orphan, check commit reachability, resume or discard.
- **Source-grounding adversarial review earned its keep.** The drift-guard reviewer fork caught 5 HIGH API-surface-drift blockers the in-house plan-checker missed — assumptions about harness capabilities that did not exist. This directly produced the "Producer API Surface (Frozen)" section in 07-06, which the executor honored verbatim (zero forbidden `@register` kwargs shipped).
- **Visual inspection beat the automated a11y gate.** axe-core flagged "serious" color-contrast failures; screenshotting the built app in both light and dark mode proved the UI was actually fine and axe was misreading `oklch()`. Ground-truth-by-eye prevented a wrong "fix the theme" detour.
- **Verifier goal-backward check caught real gaps.** Phase verification returned `gaps_found` (4/7 → after closure 7/7), surfacing the OTel-SDK-not-shipped gap that contradicted a locked STATE.md decision — a genuine under-delivery the task-completion view would have missed.

### What hurt or wasted time

- **The worktree cleanup-wave merge fails silently on a dirty working tree, and a `--force --force` remove after a failed merge destroys the uncommitted SUMMARY.** This bit twice: 07-04's SUMMARY was lost (reconstructed from the agent report) and 07-12's code commits were orphaned (merge_failed masked by the lock error; caught only by an explicit reachability check). The dirty tree was `.planning/STATE.md` left modified by `roadmap.update-plan-progress`.
- **`.claude` worktree paths trip the commit-msg "claude" guard hook** on otherwise-innocent bash commands (the path substring matched), forcing command rewrites.
- **A planning-telephone scope drift** (OTel SDK: STATE/ROADMAP said v0.2, CONTEXT/plans deferred to v0.3) went unreconciled until verification — cost a mid-execution design decision.

### Did the new tooling pay off?

- REVIEW-CHECKLIST.md auto-inject: **helpful** — §1 cwd-leak, §3 belt-and-suspenders exclude, §4 API-drift, §5 SSE-bypass all recurred and were caught by executors citing the checklist.
- Convergence stall-detector hook: **didn't-trigger** (no stall this phase).
- `/gsd:patch-replan` skill: **didn't-trigger** (gap closure used fresh planner).
- check-plan-shapes.sh grep script: **neutral** (not run this execution session).
- Source-grounding (drift-guard) reviewer fork: **helpful** — the standout tool; caught 5 HIGHs the in-house checker cleared.

### One thing to change before next phase

**Verify executor commit reachability (`git merge-base --is-ancestor`) BEFORE removing any worktree, and never `--force --force`-remove a worktree whose merge reported failure.** Adopt the "clean the working tree → merge → assert reachability → only then remove" sequence as the standard merge gate. The dirty-`STATE.md`-blocks-merge failure mode should be a precondition check in the cleanup step. (Candidate rule for `~/.claude/rules/`.)

---

## Backlog: missing retros

Phases 01, 04, 05, 06 still lack retros (only 02, 03, 07 exist). They were executed in sessions without firsthand data available here; reconstructing them from artifacts alone would be low-fidelity. Flagged rather than fabricated.

## Trend reference

Run `bash .planning/scripts/compare-phases.sh` to fold this into the aggregate (now N=3: phases 02, 03, 07).
