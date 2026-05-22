---
title: Manual-fix cascade — each fix can introduce a fresh meta-bug
aliases: [manual-fix-cascade, meta-bug-cascade, grep-is-not-verification]
tags: [verify-kit, learnings, atomic, gsd, rule-08]
created: 2026-05-22
last_updated: 2026-05-22
source_session: [[session-2026-05-22-phase-5-llm-and-verification]]
---

# Manual-fix cascade — each fix can introduce a fresh meta-bug

> [!abstract] Pattern
> When the convergence loop exits at max-cycles with N HIGHs and you apply manual fixes, **the manual fix is itself code that can be wrong**. Without an independent semantic re-review, you'll often introduce a fresh class of bug. The rule "grep is not verification" applies: a local script that confirms the new substring is present doesn't confirm the gate semantics are right.

## The data point this came from

Phase 5 convergence cycles 4, 5, 6 each caught a fresh meta-bug introduced by the prior cycle's manual fix:

### Cycle 4 fix introduced

**The substring assertion shape:**
```python
assert '!=' in text and '"none"' in text or "'none'" in text
```

This **parses as** `(A and B) or C` — Python's `or` is lower precedence than `and`. The assertion passes whenever **`'none'` (single-quoted)** appears anywhere in the file, including in a comment. The OLD self-defeating shape would still pass.

> [!quote] Source
> Diff (now reverted): `.planning/phases/05-llm-add-on/05-03-PLAN.md` cycle-4 `<verify>` block.
> Commit history: `8366ac9` (the bad fix) → `26625c5` (the next fix).
> Codex cycle-5 review found this.

### Cycle 5 fix introduced

**The collect-only assumption:**
```python
_proc = subprocess.run(['uv','run','--no-project','pytest','--collect-only','-q', ...])
```

The fix was meant to assert that running pytest with the missing-cassette probe AND `--record-mode=once` does NOT skip. But `pytest --collect-only` doesn't execute autouse fixtures — only loads tests. So the assertion couldn't actually exercise the fixture being tested.

> [!quote] Source
> Codex cycle-6 review: `.planning/phases/05-llm-add-on/05-REVIEWS.md` cycle 6 section. "pytest --collect-only does not execute autouse fixtures — collection-only cannot prove _skip_when_no_cassette actually avoids skipping during cassette refresh."

### Cycle 6 fix introduced (3 separate meta-bugs)

The fix replaced collect-only with an executing probe. Codex caught:

1. **False-positive sieve** — case (b) assertion was "non-zero exit + no 'skipped' string". Many failure modes (missing pytest-recording → exit 4 usage error, collection errors, ImportError, fixture errors) satisfy that condition while the fixture was never exercised.
2. **`uv run --no-project` bypasses pyproject** — so `pytest-recording` (declared as dev optional dep) is not even installed, and `--record-mode=once` may be an unrecognized flag.
3. **No clean env** — outer `VIRTUAL_ENV` / `UV_PROJECT_ENVIRONMENT` leak into the subprocess (REVIEW-CHECKLIST §8).

> [!quote] Source
> Codex cycle-6 review: `.planning/phases/05-llm-add-on/05-REVIEWS.md` cycle 6 section, all three points enumerated.
> Trajectory hit 1 → 3 here, triggering rule-08 restructure.

## What broke each time

Each manual fix targeted the prior cycle's named bug. Each fix introduced a NEW way for the verify-block to be wrong. The verify block grew more complex than the fixture it was verifying:

- Cycle 3 fix: ~8 lines, 2 substring asserts
- Cycle 4 fix: ~15 lines, substring + subprocess
- Cycle 5 fix: ~25 lines, substring + subprocess + materialized probe test + 2 subprocess invocations

By cycle 6 the verify block had more code than the fixture it tested. That's a red flag.

## What to do about it

> [!tip] Apply
> - **Run an adversarial re-review after every manual fix.** Local grep / "does my new substring appear" check is not verification — it confirms the string exists, not that the semantics are right.
> - **Match the verifier to the thing under test.** Testing a pytest fixture? Use pytest's `pytester`. Testing a template render? Use the project's `render_scratch_project` helper. Don't cobble together subprocess + string parsing.
> - **Verify-block complexity is a smell.** If the verify-block grows larger than the artifact it's verifying, the structure is wrong. Move the test into a real test file owned by the producer plan.
> - **Boolean precedence is a real footgun.** Any compound assert with `and` + `or` needs parens — or replace with `assert all([...])`.
> - **`subprocess.run` calls in templates/tests need:** explicit `cwd=` (REVIEW-CHECKLIST §1), explicit `env=` with `VIRTUAL_ENV`/`UV_PROJECT_ENVIRONMENT`/`PYTHONPATH`/`PYTHONHOME` stripped (REVIEW-CHECKLIST §8).

## The "grep is not verification" rule

This is the project's accumulated form of the lesson:

> After manual fixes, must spawn an independent semantic re-review (Codex), not just run `check-plan-shapes.sh`; the user explicitly caught this earlier in Phase 3.
> — *memory: `grep_is_not_verification`*

## Related patterns

- [[convergence-oscillation-restructure-trigger]] — when manual-fix cascade triggers oscillation, restructure rather than continue patching.
- [[internal-checker-vs-external-reviewer]] — why "ran my own grep" isn't enough; need an orthogonal reviewer.
- [[each-gate-catches-different-classes-of-bug]] — verify-block bugs are a class that only adversarial re-review catches.

## Cost of getting it wrong

This session: 3 manual-fix rounds + 3 adversarial re-reviews after convergence-loop exit. ~30-60 minutes wasted.

The structural restructure that resolved it took ~5 minutes to design and 1 cycle to verify.
