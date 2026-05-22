---
title: Internal reviewer vs external reviewer — perspective bias is real
aliases: [internal-vs-external-reviewer, perspective-bias, codex-finds-what-internal-misses]
tags: [verify-kit, learnings, atomic, reviews, gsd, rule-08]
created: 2026-05-22
last_updated: 2026-05-22
source_session: [[session-2026-05-22-phase-5-llm-and-verification]]
---

# Internal reviewer vs external reviewer

> [!abstract] Pattern
> A reviewer drawn from the same model family / instruction set as the planner shares the planner's blind spots. An "internal pass" reporting "0 issues" is not evidence the plan is clean — it's evidence the reviewer agrees with the planner. An orthogonal external reviewer (different model, different system prompt, adversarial framing) catches a different class of bug.

## The data point this came from

Phase 5 LLM Add-on planning. Sequence:

1. `gsd-planner` produced 5 plans (commit [`8f24983`](#)).
2. `gsd-plan-checker` (internal) ran — caught 1 blocker + 4 warnings on first pass (acceptable shape), then **VERIFICATION PASSED** on revision iter 1 with 0 remaining issues. Plans committed as [`0019335`](#).
3. `/gsd:plan-review-convergence 5 --codex` was run as a separate gate per project rule 08.
4. Codex cycle 1 found **8 HIGHs**, all substantive:
   - `@llm_call` was a passthrough — D-03 routing not actually wired
   - `[dependency-groups]` table name didn't exist in repo's pyproject layout
   - Promptfoo config missing `prompts:` entry — `just eval` wouldn't run
   - `.verify/eval-results.json` path drift across 3 files
   - `fix_propose` signature drift in SKILL.md
   - LLM `.env.example` had no destination in (has_llm=true, has_backend=false) cell
   - `@cost_budget` decorator ordering not enforced
   - VCR `record_mode="none"` without seeded cassettes — clean scaffold first-run would fail

None of these are nitpicks. Each is a real implementation contract that would have shipped broken if execution had proceeded from the "0 issues" internal pass.

> [!quote] Evidence
> File: `.planning/phases/05-llm-add-on/05-REVIEWS.md` cycle 1 section.
> Commit: [`45cd4dc`](#) — "docs: cross-AI review for phase 5".
> Replan commit: [`bb201fd`](#) — "docs(phase-5): replan addressing 8 HIGH concerns from 05-REVIEWS.md".

## Why this happens

- **Same training-data biases.** Internal checker and planner are sibling agents in the same harness. They share priors about what "correct" looks like.
- **Same instruction-set framing.** Both load `agent-skills/gsd-*` skill files from the same directory; both interpret the planner's prose with the same conventions.
- **Reviewer instructed to verify shape, not adversarially attack.** `gsd-plan-checker`'s default mode is "check the plan against the success criteria." Codex is invoked with explicit adversarial framing ("find at least one HIGH the prior reviewer missed").

## What to do about it

> [!tip] Apply
> - For any phase with **3+ cross-referencing plans**, run `/gsd:plan-review-convergence --codex` as the default, not as an upsell. (matches project rule 08 + *memory: `run_all_gsd_ceremonies`*).
> - For trivial phases (single-file refactor, doc-only, dep bump), the internal pass is fine.
> - Treat "internal: 0 issues" as a calibration signal, not a clearance — if internal says 0 and external says N, the gap is informative for future planning prompts.
> - The convergence loop's **first cycle** is the highest-value cycle. If Codex finds nothing in cycle 1, you really are clean. If Codex finds 5+ HIGHs in cycle 1, that's a signal the planning artifacts need more rigor up-front (more research depth, more explicit decisions in CONTEXT.md).

## When NOT to apply

- Trivial phases (per the project rule 08 carve-out).
- Phases where the user has time pressure that exceeds the convergence loop's cost.

## Related patterns

- [[convergence-oscillation-restructure-trigger]] — when convergence stops being monotone-decreasing, the issue isn't review quality, it's structural plan coupling.
- [[each-gate-catches-different-classes-of-bug]] — convergence is the FIRST gate, not the only one. Verify-work, secure-phase, code-review each catch different things.
- *memory: `drift_guard_fork_applied`* — the local fork of `~/.claude/get-shit-done/workflows/review.md` adds source-grounding to the reviewer prompt, making Codex's adversarial framing tighter.

## Open questions

- Could the internal checker be improved by giving it Codex-style adversarial framing? Probably some — but it would still share underlying biases.
- Is there a cheaper "first-pass adversarial" we can run without spending a Codex cycle? E.g., the planner's own self-critique step before the internal pass. Worth exploring as a future GSD enhancement.
