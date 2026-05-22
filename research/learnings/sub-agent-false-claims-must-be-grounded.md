---
title: Sub-agent false claims must be grounded — "X is unavailable" needs evidence
aliases: [sub-agent-false-claims, agent-claim-verification, ground-negative-claims]
tags: [verify-kit, learnings, atomic, sub-agents, gsd]
created: 2026-05-22
last_updated: 2026-05-22
source_session: [[session-2026-05-22-phase-5-llm-and-verification]]
---

# Sub-agent false claims must be grounded

> [!abstract] Pattern
> When a spawned sub-agent reports a **negative claim** (X tool not installed, Y file not present, Z library doesn't support feature W), verify the claim before letting it propagate into planning artifacts. Sub-agents often guess at environmental facts they didn't actually check. False negative claims become entrenched contracts (checkpoint tasks, manual workarounds) that should never have existed.

## The incident this came from

Phase 5 research stage. The `gsd-phase-researcher` sub-agent produced `05-RESEARCH.md` and explicitly wrote (line 967):

> *"the slopcheck step was skipped (binary unavailable in the research env), so the Package Legitimacy Audit promotes all packages to `[ASSUMED]` rather than `[VERIFIED]`. Planner should add a checkpoint:human-verify task that runs `slopcheck install pydantic-ai instructor litellm langfuse autoevals vcrpy tokencost tokenx-core traceloop-sdk opentelemetry-instrumentation-httpx claude-agent-sdk pytest-recording --json` before the first install task."*

Reality:

```bash
$ which slopcheck
/opt/homebrew/bin/slopcheck
```

slopcheck was installed all along. The research agent never ran `which slopcheck`, never tried calling the tool, never tested its availability — it just *claimed* it was unavailable.

## The downstream damage

The planner consumed `05-RESEARCH.md` as authoritative input. It dutifully added a `checkpoint:human-verify` Task 1 to `05-01-PLAN.md` that required me (the executing agent) to **manually verify 12 PyPI URLs by clicking through them**.

The Phase 5 execution then:
1. Hit the checkpoint
2. Surfaced "slopcheck not installed" to the user as a finding
3. User asked *"what is slopcheck and can we install it?"*
4. I (Claude) ran `which slopcheck` and found it at `/opt/homebrew/bin/slopcheck`
5. We then actually ran slopcheck, which caught 2 SUS (vcrpy false-positive, tokenx-core with 81 downloads → D-22 to drop)

The whole checkpoint task should never have existed. It was a real cost: the plan was authored against a false premise, then re-authored when the premise was corrected (commit [`0fd475a`](#) — "docs(phase-5): D-22 drop tokenx-core after slopcheck SUS").

> [!quote] Evidence
> `05-RESEARCH.md:967` original claim
> `05-01-PLAN.md` Task 1 (now record-only after correction)
> `.slopcheck` allowlist file (added during the actual run)
> Commit [`0fd475a`](#) — D-22 record + Task 1 demoted

## Why this happens

- **Sub-agents are aggressively confident about negative claims** (the absence of something) because they look easy to verify. They often aren't checked.
- **No verify-tool-availability step** is built into the GSD researcher prompt. The agent decides whether to run the tool based on its own confidence, not on an explicit check.
- **The planner trusts research as authoritative.** Once a claim is in `RESEARCH.md`, it propagates into plans, threat models, success criteria. The downstream layers don't re-verify.

## What to do about it

> [!tip] Apply
> - **When a sub-agent reports a negative claim about a tool/library/file, do one of:**
>   1. Run a one-shot verification command yourself (`which <tool>`, `python -c "import X"`, `ls <path>`).
>   2. Ask the user before propagating the claim downstream ("the research agent says X is unavailable — can you confirm?").
>   3. At minimum, add a `[VERIFY]` flag on the claim in the artifact so downstream consumers know it's unverified.
> - **For tools that the GSD workflow assumes exist** (slopcheck, beads, gh, uv), have a pre-flight check at session start that confirms they're on PATH and surfaces an obvious error if not.
> - **For sub-agent prompts going forward**, include explicit instructions: "If a tool you need is not available, run `which <tool>` to confirm, attempt `<tool> --version` to test, and report the exact error before concluding it's unavailable. Do NOT assume unavailability without empirical evidence."

## The general principle

This is a specific case of "sub-agents hallucinate environmental facts." Other examples I've seen / can imagine:
- "package version X is not on PyPI" (when it is)
- "tool Y doesn't support flag --z" (when it does)
- "file at path P doesn't exist" (when it does, but in a slightly different location)
- "the test passes" (when the agent never ran it)

The asymmetry: **positive claims** like "I ran the test and got output Z" are easy to verify (look at the output). **Negative claims** like "I couldn't run the test because X" hide the missing verification.

## Cost of getting it wrong

This session: ~1 commit of wasted plan work (re-authoring 05-01 Task 1), some confusion in the execution loop, and a near-miss on D-22 (we caught tokenx-core's 81-download red flag because we DID run slopcheck eventually; if we'd accepted the agent's false premise, we'd have shipped a redundant niche dep).

The broader pattern: every sub-agent false claim is a load-bearing lie. The plans, threat models, and code that depend on it are now wrong in a way that's hard to detect because the original claim looks authoritative in `RESEARCH.md`.

## Related patterns

- [[internal-checker-vs-external-reviewer]] — even external review can't catch this; the false claim is buried in research that the reviewer treats as ground truth.
- [[session-2026-05-22-phase-5-llm-and-verification]] §❌ Mistakes #5

## Open question

Should `gsd-phase-researcher` get an explicit "tool availability" sub-step that runs `which` / `pip show` / equivalent for every tool it references in its output? Probably yes; cheap to add, and it would catch the slopcheck-class lie at the source.
