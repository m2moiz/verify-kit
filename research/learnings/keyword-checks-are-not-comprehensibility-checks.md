---
title: Keyword checks are not comprehensibility checks
aliases: [grep-mitigation-is-weak, keyword-vs-prose, documentation-as-mitigation]
tags: [verify-kit, learnings, atomic, documentation, secure-phase, code-review]
created: 2026-05-22
last_updated: 2026-05-22
source_session: [[session-2026-05-22-phase-5-llm-and-verification]]
---

# Keyword checks are not comprehensibility checks

> [!abstract] Pattern
> A polarity test that greps a generated document for keywords confirms the strings exist, NOT that the prose makes sense. Treating a keyword-presence check as a "mitigation" for a documentation-correctness threat is a category error. The same applies to commit-message hooks that only check for forbidden vocab — they catch the negative class but say nothing about whether the positive content is correct.

## The incident this came from

Phase 5 `05-SECURITY.md` threat **T-05-18**:

> **Threat:** README documents the API-key path as the operator's default
> **Disposition:** mitigate
> **Mitigation:** "T3 explicit two-section split (personal vs consumer); test could grep for the specific 'claude-agent-sdk' personal-path label"

The implementation: a polarity test in `tests/test_phase05_polarity.py` greps the rendered README for the string `claude-agent-sdk`. The test passes when the string exists.

**The string exists.** It might appear in:
- A coherent "personal vs consumer" section that clearly distinguishes the two paths ✓ (the intended state)
- A garbled paragraph that mentions both terms in a confusing order ✗
- A code-fence example with no surrounding explanation ✗
- A section header with nothing underneath ✗

The polarity test cannot tell which is which. It says only "yes, `claude-agent-sdk` appears somewhere in the rendered README."

When the user asked me late in the session to elaborate on the two accepted risks, I had to admit: **no human ever read the README LLM section to confirm the prose works.** The keyword check is technically a "mitigation"; it is not what reviewers and consumers actually need.

> [!quote] Evidence
> `.planning/phases/05-llm-add-on/05-SECURITY.md` T-05-18 row
> `.planning/phases/05-llm-add-on/05-UAT.md` test 5 — README/SKILL.md human-read explicitly **skipped** ("scope: automated-only per user request 2026-05-22")
> Filed beads `verify-kit-1v6` (P1) for the human-read pass as OSS-release blocker

## Why this happens

- **Polarity tests are easy to write.** `assert "claude-agent-sdk" in readme_text` is one line. A real comprehensibility check is hard.
- **Comprehensibility is fundamentally a human-judgment task.** No automated tool today reliably tells you whether a documentation section reads cleanly to a new reader.
- **Threat-model rubrics reward "mitigation: yes/no"**, not "mitigation: yes-but-the-quality-is-actually-a-human-judgment." So the rubric pushes toward keyword tests.
- **Documentation-correctness threats look like security threats** at the modeling stage. They're closer to UX threats. They demand a different kind of mitigation (human review, A/B test with new readers, structured review checklist).

## The general principle

| Check shape | What it actually verifies |
|---|---|
| `assert "X" in text` | The string "X" appears somewhere. Nothing else. |
| `assert "X" not in text` | The string "X" does not appear (D-22 regression guard for `tokenx`). Useful for negative-presence guards. |
| `assert text.count("X") == 1` | "X" appears exactly once. Useful for uniqueness. |
| `assert "X" in section_under_heading("Y")` | "X" appears under heading "Y". Better than bare presence. |
| LLM-as-judge scoring | Probabilistic; can be biased, but at least evaluates prose-level coherence. |
| Human-read pass | Highest-confidence comprehensibility check; expensive but irreplaceable for OSS-quality docs. |

## What to do about it

> [!tip] Apply
> - **Be honest about what a keyword check buys.** It's a regression guard, not a comprehensibility guarantee.
> - **For threats whose mitigation requires understanding prose**, the mitigation MUST include a human-read pass at some milestone (PR review, release gate, periodic re-read). Bake this into Phase 6's dual-audience checklist.
> - **Distinguish negative-presence from positive-presence.** A test like "must NOT contain `result.data`" (Pitfall 4 D-22-style regression guard) is strong — it gates a specific bug. A test like "must contain `claude-agent-sdk`" is weak — it just confirms a string exists.
> - **For "consumer-facing documentation" specifically**, treat human-read as a required gate. The cost (~10 min/section) is dwarfed by the cost of consumers reading hallucinated setup steps.
> - **Consider LLM-as-judge as a middle layer**: an evaluation that says "does this README LLM section clearly distinguish the personal-dev path from the consumer-prod path?" using a separate LLM. Not a replacement for human read; a cheap pre-screen.

## What about negative-presence checks?

Negative-presence checks are stronger because they target a specific known-bad shape. Examples that work well in verify-kit:

- `test_pyproject_has_no_tokenx` — must NOT contain `"tokenx"` OR `"tokenx-core"`. D-22 regression guard. Specific bug shape it prevents.
- `test_no_result_data_anywhere` — Pitfall 4 forcing function. Specific anti-pattern.
- `test_no_empty_segment_leaks` — must NOT contain `{% if` or `//` in rendered tree. Specific Jinja shape.

These are useful because they encode "we know this exact pattern is wrong; never let it ship." That's a true contract, not a comprehensibility proxy.

## Related patterns

- [[accepted-risk-must-match-distribution-intent]] — T-05-18 was accepted (then "mitigated" by keyword check) under a stale "portfolio scope" framing; under OSS distribution the keyword check is not enough.
- [[manual-fix-meta-bug-cascade]] — the verify-block bugs in Phase 5 cycles 4-6 were all "string exists" / "exit-code is N" checks pretending to verify behavior.
- [[each-gate-catches-different-classes-of-bug]] — documentation correctness lives in a class that none of the four automated gates catches reliably.

## Open questions

- Is there a tractable "documentation comprehensibility eval" we could ship in the LLM add-on for consumers to use on their own docs? E.g., a Promptfoo eval that runs an LLM-as-judge prompt against the README. Worth scoping for Phase 6 or a future v0.2.
