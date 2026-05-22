---
title: Heavy verify suites belong in /gsd:verify-work, not inline in execute-plan
aliases: [heavy-verify-placement, inline-polarity-hangs-executor, verify-cadence]
tags: [verify-kit, learnings, atomic, gsd, execute-plan, verify-work]
created: 2026-05-22
last_updated: 2026-05-22
source_session: [[session-2026-05-22-phase-5-llm-and-verification]]
---

# Heavy verify suites belong in /gsd:verify-work, not inline

> [!abstract] Pattern
> A plan's inline `<verify>` block should run a single fast subprocess check (~seconds). Multi-minute test matrices (e.g., 12-cell polarity tests that render 12 scratch projects + `uv sync` each) belong in the **phase-level** `/gsd:verify-work` gate, not inline in `execute-plan`. Inline heavy verify hangs the executor and produces no useful signal.

## The incident this came from

Phase 5 plan 05-05 Task 4 was the 12-cell polarity matrix (`tests/test_phase05_polarity.py`). Its inline `<verify>` block called:

```bash
uv run pytest tests/test_phase05_polarity.py -v
```

This renders 12 scratch projects (each with `copier copy` + `uv sync`) and runs 69 forcing-function assertions across them. Real runtime: **6:25 minutes**.

The executor sub-agent committed Tasks 1-3 cleanly in ~3 minutes total, then hung on Task 4. **39 minutes later** with no new commits, no SUMMARY.md, the executor still hadn't returned. The user (correctly) asked "what's the status?" twice.

When I (Claude orchestrator) finally manually closed it out:
- The polarity test file itself was complete and correct
- The `_CLEAN_ENV` addition to `tests/_helpers.py` was complete
- Neither change was committed
- No SUMMARY.md was written

I committed T4 as `f7e6037`, wrote 05-05-SUMMARY.md as `af37dfb`, advanced state. The actual polarity test then ran cleanly under `/gsd:verify-work` in the canonical 6:25 with 69/69 pass.

> [!quote] Evidence
> `.planning/phases/05-llm-add-on/05-05-SUMMARY.md` "Issues encountered" section
> `.planning/phases/05-llm-add-on/05-UAT.md` test 2 (the same matrix, properly placed)
> Commits: [`f7e6037`](#) (manually committed T4), [`af37dfb`](#) (manually written SUMMARY)

## Why this fails

- **Executor sub-agents have an internal budget** (tokens, turns, wall-clock). A 6+ minute test suite consumes a lot of that budget while doing nothing the executor needs to know about.
- **The executor's role is to write code and commit each task atomically.** A polarity matrix run is a phase-level concern, not a task-level concern.
- **When the executor hangs, the orchestrator has no clean signal.** It just sees "no completion marker" for 30+ minutes. The orchestrator has to guess whether the executor is making progress or stuck.
- **The matrix is the same matrix `/gsd:verify-work` exists to run.** Running it twice (inline + at verify-work) is wasted compute.

## What to do about it

> [!tip] Apply
> - **Inline `<verify>` blocks should run in seconds, not minutes.** Examples that are appropriate inline: a copier render of ONE cell + regex assertions on the rendered files; a single unit test for the specific feature being added; a syntax check.
> - **Multi-cell polarity matrices belong in `/gsd:verify-work`.** Add the test file in execute-plan; defer the run to verify-work. The plan's `<verify>` should just confirm the test file exists, has expected structure, and parses (e.g., `pytest --collect-only` against ONLY this file).
> - **Phase-level smoke tests** (cold-start render + `uv sync`) also belong in `/gsd:verify-work`, for the same reason — they take minutes and only make sense at end-of-phase.
> - **Estimate `<verify>` runtime when authoring plans.** If a verify would take >30 seconds, that's a signal to defer to verify-work or split.

## How Phase 5's 05-05 plan should have been written

Inline `<verify>` for Task 4:

```bash
# Confirm the test file exists, parses, and has the expected named tests.
test -f tests/test_phase05_polarity.py
uv run pytest tests/test_phase05_polarity.py --collect-only -q | head -20
# Expect: 16 forcing-function test names appear in collect output
```

That's a 2-second check. It proves the file is in place and pytest can load it. The actual 12-cell matrix run then happens during `/gsd:verify-work 5`, which is exactly where it belongs.

## Implication for plan authoring

This shape mistake comes from a misalignment in the GSD workflow's mental model: each plan's verify is described as "confirm the deliverable works." For most tasks that means "run the function and check output." For test-suite-creation tasks, "confirm the suite works" pulls toward running the suite — which is the wrong cadence.

A clarification I'd add to the planner's instructions: **for tasks whose deliverable IS a test suite, the inline `<verify>` confirms the suite is parseable and collects the right test names. Running the suite happens at phase-level verify-work.**

## What I added to project context

The 05-05-SUMMARY.md "Issues encountered" + "Verify-run deferred" sections now document this for next time. The pattern is also surfaced via [[session-2026-05-22-phase-5-llm-and-verification]] §❌ Mistakes #9.

## Related patterns

- [[each-gate-catches-different-classes-of-bug]] — verify-work owns full-system smoke; execute-plan owns task-atomic-write.
- [[manual-fix-meta-bug-cascade]] — when an inline verify-block gets too clever (which polarity-run-inline is a more extreme example of), it becomes the new bug source.

## Cost of getting it wrong

This session: 39 minutes of hung executor + manual recovery (~10 min). The actual polarity matrix run was perfectly fine when called from verify-work where it belongs.

If this pattern repeats (inline heavy verify in future phases), each occurrence costs another lost executor session.
