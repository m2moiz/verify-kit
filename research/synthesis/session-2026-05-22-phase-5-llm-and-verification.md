---
title: Session 2026-05-22 — Phase 5 LLM Add-on planning, execution, and full verification
aliases: [Session Retro 2026-05-22, Phase 5 Buildout, Phase 5 Verification Retro]
tags: [verify-kit, retro, learnings, mistakes, session-log, synthesis, phase-5]
created: 2026-05-22
last_updated: 2026-05-22
status: completed-session
phases_touched: [05-llm-add-on]
gates_passed: [plan-review-convergence, execute-phase, verify-work, secure-phase, code-review]
---

# 🪞 Session Retrospective — Phase 5 LLM Add-on

> [!abstract] What this is
> Honest record of one long session: Phase 5 (LLM add-on) from planning through five GSD gates (convergence → execute → verify-work → secure-phase → code-review). Every gate caught something real. Several mistakes I (Claude) made along the way, each with concrete commit + file evidence. Companion atomic notes in `research/learnings/` capture the reusable patterns.

> [!info] About *memory:* references
> Italic refs like *memory: `state-md-is-source-of-truth`* point to files in `~/.claude/projects/-Users-moiz-Documents-code-verify-kit/memory/` — Claude Code's per-project memory store, outside this vault. They persist across sessions and inform every conversation about this project.

## ⚡ Quick navigation

| Want to know… | Jump to |
|---|---|
| Headline outcome | [[#📊 What shipped]] |
| Convergence-loop story (∞→8→5→2→1→3→1→0) | [[#🔁 Convergence loop the trajectory]] |
| **My mistakes — what I got wrong** | [[#❌ Mistakes — what I got wrong]] |
| **External reviewer wins** | [[#🎯 What only the external reviewer caught]] |
| **Surprises that bit us** | [[#😲 Surprises — what wasn't in any plan]] |
| Atomic learning notes | [[#📚 Atomic learnings]] |
| Process insights | [[#🛠 Process insights]] |
| Open items | [[#📌 Carry-forward]] |

---

## 📊 What shipped

| Artifact | Status | Citation |
|---|---|---|
| 5 plans (05-01..05-05) | ✅ All executed | commits `0fd475a` → `af37dfb` |
| Convergence loop (8 cycles) | ✅ Converged to 0 HIGHs | `05-REVIEWS.md`; commits `45cd4dc`, `6233038`, `27c873a`, `78e5d6d`, `1c47ebc`, `24ca06f`, `925bae4` |
| `/gsd:verify-work 5` | ✅ Passed 69/69 polarity | `05-UAT.md`; commit `05d0dae` |
| `/gsd:secure-phase 5` | ✅ 19/19 threats SECURED | `05-SECURITY.md`; commit `0861c4f` |
| `/gsd:code-review 5` | ✅ 0 critical, 5 warnings fixed | `05-REVIEW.md`; commits `b406bd0` (fixes) + `43cddad` (artifact) |
| D-22 decision (drop tokenx-core) | Added during execution | `05-CONTEXT.md:11`; commit `0fd475a` |
| Dep-pin fixes (3 total) | Caught at runtime, not at spec-time | `ed1854a`, `daba26f` |
| OSS-blocker beads filed | 4 P1 issues | `verify-kit-3u2`, `verify-kit-yr7`, `verify-kit-93h`, `verify-kit-1v6` |

**Total Phase 5 commits:** 50 substantive commits across the convergence + execution + verification trail.

---

## 🔁 Convergence loop — the trajectory

The single most important data point of this session. The internal `gsd-plan-checker` said "0 issues" after the planner finished. Then Codex (external adversarial reviewer) found **8 HIGHs**. Eight more cycles followed. Trajectory:

| Cycle | Source | HIGHs | Notes |
|---|---|---|---|
| (init) | gsd-plan-checker | 0 | Internal — shared perspective with planner |
| 1 | Codex | **8** | First adversarial pass found what internal missed |
| 2 | Codex post-replan | 5 | 4 fully resolved + 2 partial + 3 new HIGHs |
| 3 | Codex post-replan | 2 | Surgical, not structural |
| (exit max-cycles) | manual fix | — | Applied 2 surgical fixes → commit `823b71c` |
| 4 | Codex adversarial re-review | 3 | Caught precedence bug + cwd leak my manual fix introduced |
| (manual fix) | — | — | commit `26625c5` (executing-probe test) |
| 5 | Codex | 1 | Boolean precedence + false-positive sieve in MY fix |
| (rule 08 restructure) | — | — | commit `48604cc` (pytester contract test) |
| 6 | Codex | 3 | Surfaced 1→3 oscillation = restructure signal (rule 08) |
| 7 | Codex | 1 | pytester sys.path inject missing — real implementation bug |
| (manual fix) | — | — | commit `d367b65` |
| 8 | Codex | **0** | CONVERGED |

```mermaid
graph LR
    A["internal: 0"] -.->|"perspective bias"| B["Codex c1: 8"]
    B --> C[c2: 5]
    C --> D[c3: 2]
    D -->|manual fix| E[c4: 3]
    E -->|fix introduced new HIGHs| F[c5: 1]
    F -->|fix introduced new HIGHs| G[c6: 3]
    G -->|"rule 08: restructure"| H[c7: 1]
    H -->|surgical implementation fix| I["c8: 0 ✓"]
    style B fill:#f99
    style G fill:#fc6
    style I fill:#9f9
```

**Key signal:** the 1 → 3 oscillation in cycles 5 → 6 is exactly the rule 08 trigger ("two consecutive cycles with HIGH count ≥ 2 and trajectory not monotone-decreasing → restructure, don't grind"). When triggered, restructuring (move the gate test out of inline `<verify>` into a real pytester contract test) closed the oscillation in one cycle.

See [[convergence-oscillation-restructure-trigger]].

---

## ❌ Mistakes — what I got wrong

Each entry: **what**, **how I noticed**, **how it was fixed**, **citation**.

### 1. Said Phases 1/2/3 weren't done; they were

> [!failure] Read the wrong source of truth for phase status
> **What:** Multiple times across this session I told the user "Phases 1, 2, 3 are NOT done — Phase 6 only happens after they execute." Source: I was reading `.planning/ROADMAP.md` checkboxes (`- [ ]`).
>
> **Reality:** `.planning/STATE.md:33-37` shows all of Phases 1–4 as ✅, with `02-VERIFICATION.md` (status: `gaps_found`, dated 2026-05-18) and `03-VERIFICATION.md` (status: `passed`, dated 2026-05-19) on disk. Phase 1 had 4/4 plan SUMMARYs. The ROADMAP checkboxes were never flipped post-completion — they're stale.
>
> **How I noticed:** the user pushed back: *"I'm pretty sure that phase one was we started phase one, then went to two, then one to three… Can you please check that and verify that you're not making a mistake?"*
>
> **Fix:** Read `STATE.md` directly. Confirmed user's memory was right. Wrote two memories to prevent recurrence: *memory: `state-md-is-source-of-truth`* + corrected *memory: `verify-kit-project`*.
>
> **Atomic learning:** [[state-md-vs-roadmap-checkbox-confusion]]

### 2. Framed risks as "portfolio scope" when scope was OSS

> [!failure] Wrong distribution model assumed
> **What:** In my Phase 5 security explanations and the original `05-SECURITY.md` accepted risks (T-05-15 `/summarize` prompt injection, T-05-18 README not human-read), I framed acceptance as defensible "for portfolio scope."
>
> **Reality:** The user clarified: *"this is not exactly a portfolio piece… It's primarily designed to help me speed up development on my other projects reliably… I am planning on open sourcing it… any security risk we should use the best design practices with no trade-offs, so that it's safe for everyone."*
>
> **How I noticed:** the user said it directly.
>
> **Fix:** Updated *memory: `verify-kit-project`* with corrected stance: "zero security tradeoffs, best practices throughout, no 'portfolio scope' excuses." Filed 4 P1 beads (`verify-kit-3u2`, `verify-kit-yr7`, `verify-kit-93h`, `verify-kit-1v6`) as OSS-blockers.
>
> **Atomic learning:** [[accepted-risk-must-match-distribution-intent]]

### 3. Manual-fix cascade — my fixes introduced fresh meta-bugs across cycles 4/5/6

> [!failure] Loop of meta-bugs inside the verify-block
> **What:** Phase 5 convergence exit at max-cycles with 2 surgical HIGHs (cassette lifecycle). I applied a manual fix (commit `823b71c`). Cycle 4 Codex re-review caught 2 new HIGHs my fix introduced. I fixed those (commit `8366ac9`). Cycle 5 caught 1 more meta-bug (boolean precedence + pytest --collect-only doesn't execute autouse fixtures). I fixed that (commit `26625c5`). Cycle 6 caught 3 more meta-bugs (false-positive sieve + env leak + missing dev deps in scratch). At that point trajectory hit 1 → 3 — rule 08 oscillation signal.
>
> **Pattern:** every "tighten the inline subprocess probe" attempt introduced a fresh meta-bug. The verify block became more complex than the fixture it was verifying.
>
> **Fix:** Per rule 08, **restructure** rather than grind. Moved the gate test from inline `<verify>` block into a real pytester contract test (`tests/llm/test_skip_fixture_contract.py.jinja2`) owned by the producer plan. Commit `48604cc`. Closed oscillation in 1 cycle.
>
> **Citations:** REVIEWS.md cycles 3–7; commits `823b71c`, `26625c5`, `48604cc`, `d367b65`; *memory: `convergence_oscillation_means_restructure`*.
>
> **Atomic learning:** [[manual-fix-meta-bug-cascade]] + [[convergence-oscillation-restructure-trigger]]

### 4. Internal gsd-plan-checker said "0 issues" — Codex found 8

> [!failure] Internal reviewer has perspective bias toward the planner
> **What:** The standard `/gsd:plan-phase` flow ran the internal `gsd-plan-checker`, which reported **VERIFICATION PASSED** after the planner's first pass (`0019335`). I committed those plans assuming they were clean. Then `/gsd:plan-review-convergence 5 --codex` ran and immediately found **8 HIGHs**, including:
> - "05-02 does not actually implement D-03 routing: `@llm_call` is a passthrough"
> - "05-01 appends dev deps under `[dependency-groups]`, but template uses `[project.optional-dependencies].dev`"
> - "Promptfoo config lacks a `prompts:` entry — `just eval` likely will not run"
> - "Eval output path drift: SKILL.md documents `.verify/eval-results.json` but 05-04 only uploads `./.promptfoo/`"
>
> These were substantive HIGHs the internal checker missed — not edge cases.
>
> **Why:** Internal checker shares the planner's blind spots. Codex is orthogonal.
>
> **Fix:** Run convergence loop as default for any phase with 3+ cross-referencing plans (matches *memory: `run_all_gsd_ceremonies`* + project rule 08).
>
> **Citations:** REVIEWS.md cycle 1; commits `0019335` (internal pass), `45cd4dc` (Codex first pass), `bb201fd` (replan).
>
> **Atomic learning:** [[internal-checker-vs-external-reviewer]]

### 5. Research-phase agent claimed slopcheck wasn't installed when it was

> [!failure] Sub-agent false claim → wasted planning artifact
> **What:** During Phase 5 research, the `gsd-phase-researcher` agent's output in `05-RESEARCH.md:967` said: *"the slopcheck step was skipped (binary unavailable in the research env), so the Package Legitimacy Audit promotes all packages to `[ASSUMED]` rather than `[VERIFIED]`."*
>
> **Reality:** `slopcheck` is installed at `/opt/homebrew/bin/slopcheck` and was the entire time. The agent never ran it. As a consequence, the planner inserted a `checkpoint:human-verify` Task 1 into 05-01 requiring me to eyeball 12 PyPI URLs by hand.
>
> **How I noticed:** I asked the user *"What is the slop check tool?"* and they replied *"What do you mean it's not installed? Can we install it?"* — I ran `which slopcheck`, got the path, and confirmed it's been installed.
>
> **Fix:** Ran slopcheck directly (caught 2 SUS: vcrpy false-positive + tokenx-core 81 downloads → D-22 drop). Updated `05-01-PLAN.md` Task 1 from `checkpoint:human-verify` to record-only auto task. Commit `0fd475a`.
>
> **Citation:** `05-RESEARCH.md:967`; `.slopcheck` allowlist file (commit `0fd475a`); `05-CONTEXT.md:11` D-22 record.
>
> **Atomic learning:** [[sub-agent-false-claims-must-be-grounded]]

### 6. Transitive dep conflicts caught only by `uv sync`, not by any spec-time check

> [!failure] Spec-time checks cannot see the full resolver graph
> **What:** Three separate transitive-dep conflicts surfaced AFTER plan execution committed code:
>
> 1. **Commit `ed1854a`** — `opentelemetry-instrumentation-httpx>=0.63b1` requires `semantic-conventions==0.63b1`, conflicts with Phase 2's `opentelemetry-sdk==1.41.1` (pulls 0.62b1). Caught by 05-03 executor during `uv sync`. Filed and closed beads `verify-kit-x60`.
> 2. **Commit `daba26f` (a)** — `pydantic-ai` (meta-pkg) transitively pulls `pydantic-ai-slim[mistral]` → `mistralai≥2` → `semantic-conventions≥0.60b1,<0.61` — conflicts with the same Phase 2 pin. Fix: switch to `pydantic-ai-slim[anthropic,openai]>=1.100,<2`. Caught by `/gsd:verify-work 5`'s first cold-start render.
> 3. **Commit `daba26f` (b)** — `pydantic-ai-slim 1.100` transitively requires `fastmcp>=3.3`, but Phase 3 had speculatively pinned `fastmcp>=2.0,<3.0` in commit `163d63a`. Fix: bump pin to `>=3.3,<4`. Filed beads `verify-kit-fastmcp-3x` (P2) to flag Phase 3 API revalidation.
>
> **Why:** The convergence loop ran 8 review cycles and never caught these. Spec-time review walks documented pip metadata in isolation; only `uv sync` walks the full transitive resolver against your other pins. This is the kind of conflict that's unreachable until you actually try to install.
>
> **Fix:** the `/gsd:verify-work 5` cold-start render is now the canonical place these surface. Worth knowing up front: if a phase adds packages with extras (especially provider meta-packages like `pydantic-ai`), prefer `*-slim` + explicit extras to limit transitive surface.
>
> **Citation:** `05-UAT.md`; commits `ed1854a`, `daba26f`; beads `verify-kit-x60` (closed), `verify-kit-fastmcp-3x` (open).
>
> **Atomic learning:** [[transitive-dep-conflicts-only-uv-sync-catches]]

### 7. Code review caught a real cost-accounting bug the prior 4 gates missed

> [!failure] Polarity matrix + threat register + convergence couldn't see runtime semantics
> **What:** `/gsd:code-review 5` WR-04 found that `call_via_litellm` in `harness/llm.py.jinja2:235-248` was computing cost via `tokencost.calculate_prompt_cost(prompt, model)` + `calculate_completion_cost(content, model)`. tokencost's per-string variants re-tokenize the input with their own tokenizer, which can drift from the provider's billed tokens. So `verify_kit.cost_usd` was drifting from actual cost — directly undermining threat T-05-05 (Repudiation: LLM call cost reporting) which the secure-phase audit had marked closed.
>
> **Why prior gates missed it:**
> - convergence loop: reviewed plans, not runtime code
> - polarity matrix: tested template renders, not the inside of `call_via_litellm`'s response handling
> - secure-phase: line-cited the `verify_kit.cost_usd` attribute *exists* on the span, didn't validate the value's accuracy
>
> **Fix:** swap to `litellm.completion_cost(completion_response=response)` which reads the provider's reported usage block. Commit `b406bd0`.
>
> **Citation:** `05-REVIEW.md` WR-04; `harness/llm.py.jinja2:235-248` (post-fix); commit `b406bd0`.
>
> **Atomic learning:** [[cost-double-tokenization-pattern]] + [[each-gate-catches-different-classes-of-bug]]

### 8. Phase 5 README LLM section was never read by a human

> [!failure] Keyword-presence check ≠ comprehensibility check
> **What:** T-05-18 was marked "mitigated" because the polarity test asserted the README contained the keywords `claude-agent-sdk` and `cost_usd=0`. That confirms strings exist, not that the prose makes sense. When the user later asked me to read it, I realized: no human has read what the LLM wrote into `template/README.md.jinja2`'s LLM section.
>
> **Why this happened:** during UAT scoping the user (legitimately) chose "automated only — skip human-eye reads." This was defensible for the verification cycle but is **not** defensible under the OSS distribution stance.
>
> **Fix:** filed beads `verify-kit-1v6` (P1) for a human-read pass before OSS release.
>
> **Citation:** `05-UAT.md` test 5 (scope decision); `05-SECURITY.md` T-05-18; beads `verify-kit-1v6`.
>
> **Atomic learning:** [[keyword-checks-are-not-comprehensibility-checks]]

### 9. 05-05 executor hung silently for 39 minutes

> [!warning] Sub-agent runtime timeout without a clear signal
> **What:** The Phase 5 capstone plan (05-05) included Task 4 — run the 12-cell polarity matrix inline as part of the executor's verify step. The agent committed Tasks 1-3 cleanly, then hung. 39 minutes passed with no commits, no SUMMARY, no progress signal. The user asked "what's the status?" twice.
>
> **Why:** rendering 12 scratch projects + `uv sync` per cell legitimately takes ~3 minutes. 39 min is well past that. Best guess: the agent's internal token/turn budget got exhausted partway through the matrix run.
>
> **Fix:** manually committed Task 4's already-written code (commit `f7e6037`), wrote 05-05-SUMMARY.md (commit `af37dfb`), advanced state. Filed an observation in the SUMMARY: "the deferred 12-cell render-and-assert pass should run during phase verification, not inline during plan execution." The `/gsd:verify-work 5` step then ran the matrix cleanly in 6:25.
>
> **Citation:** `05-05-SUMMARY.md` "Issues encountered" section; commit `af37dfb`.
>
> **Atomic learning:** [[heavy-verify-belongs-in-verify-work-not-execute-plan]]

### 10. AskUserQuestion when a plain answer would do

> [!warning] Overstructured response pattern
> **What:** When the user asked "whats the status?" mid-execution, I responded with a structured AskUserQuestion menu instead of a plain status report. Also: when proposing the security clarification, I asked AskUserQuestion when the user wanted to clarify a different thing.
>
> **Why:** Default to AskUserQuestion for decision points became reflex. Status queries are not decision points; they want plain data.
>
> **Fix:** keep AskUserQuestion for true decision branches; for status / "what is X" queries, just answer.
>
> **Citation:** conversation log mid-Phase-5 execution.

### 11. Commit-hook collisions on AI vocabulary + 72-char subject

> [!warning] Repeated commit-message friction
> **What:** Across the session I hit the `git-commit-msg-guard.sh` hook three times:
> 1. Wrote "claude-agent-sdk path" in a commit subject → blocked on "claude"
> 2. Wrote "ANTHROPIC_API_KEY" in a commit message body → blocked on "ANTHROPIC"
> 3. Wrote a 74-char commit subject → blocked (max 72)
>
> **Why:** The hook is correctly strict for public-repo hygiene. I should have internalized it earlier.
>
> **Fix:** rewrote messages using "agent-sdk" / "provider" / "vendor" generics. Kept subject lines ≤72.
>
> **Pattern for future:** drop AI vendor names from commits by default; subject ≤72 chars; detail goes in body.

---

## 🎯 What only the external reviewer caught

The reason convergence is the load-bearing gate, ranked by impact:

| Finding | First caught by | Cycle/gate |
|---|---|---|
| `@llm_call` was a passthrough — D-03 routing not actually wired | Codex c1 | cycle 1, HIGH #2 |
| Promptfoo config missing `prompts:` entry — `just eval` wouldn't run | Codex c1 | cycle 1, HIGH #4 |
| Eval output path drift (`.verify/eval-results.json` vs `./.promptfoo/`) | Codex c1 | cycle 1, HIGH #5 |
| `fix_propose` signature drift in SKILL.md | Codex c1 | cycle 1, HIGH #6 |
| `[dependency-groups]` vs `[project.optional-dependencies]` table mismatch | Codex c1 | cycle 1, HIGH #3 |
| LLM `.env.example` had no destination in `(has_llm=true, has_backend=false)` cell | Codex c1 | cycle 1, HIGH #1 |
| Self-contradicting paragraphs in same `<action>` block | gsd-plan-checker | revision iter 1 |
| Mid-path Jinja shape `tests/{% if has_llm %}llm{% endif %}/...` violates two-guard contract | Codex c2 | cycle 2, HIGH #2 |
| Boolean precedence bug in my own manual fix | Codex c5 | cycle 5 |
| Cost double-tokenization | gsd-code-reviewer | code-review WR-04 |
| Langfuse functional placeholder secrets | gsd-code-reviewer | code-review WR-05 |
| Meta-comments leaking into rendered consumer code | gsd-code-reviewer | code-review WR-01 |
| `pydantic-ai[mistral]` transitive vs Phase 2 otel pin | `uv sync` in verify-work | UAT test 1 |
| `fastmcp<3.0` vs `pydantic-ai-slim 1.100` requirement | `uv sync` in verify-work | UAT test 1 |
| `otel-instrumentation-httpx 0.63b1` vs Phase 2 sdk pin | `uv sync` in 05-03 execution | exec time |

**Pattern:** each gate catches a different class of bug. None of the gates is redundant. See [[each-gate-catches-different-classes-of-bug]].

---

## 😲 Surprises — what wasn't in any plan

| Surprise | Detail |
|---|---|
| `tokenx-core` has only 81 PyPI downloads | The research/agent-reports/wave-4-ai-sdk-ergonomics.md recommended it as a token-cost lib. Slopcheck flagged it. Investigation showed redundancy with our own `@llm_call`. Dropped via D-22 in `05-CONTEXT.md:11`. |
| `pydantic-ai` meta-pkg pulls all provider extras | Including `[mistral]` which has incompatible OTel pin transitives. Need `pydantic-ai-slim[anthropic,openai]` to avoid. |
| Copier `trim_blocks: true` + inline `{% raw %}…{% endraw %}` collapse newlines | Reported in 05-04-SUMMARY.md. First verify attempt failed YAML parse. Fix: wrap the ENTIRE YAML body in a single outer raw block, never mix raw fragments with structured YAML content. |
| pytest's `--collect-only` doesn't execute autouse fixtures | The cycle-4 verify-block tried to assert fixture behavior via `pytest --collect-only`. That doesn't run fixtures. Codex c5 caught it. |
| pytester's `runpytest_subprocess` has tmpdir but no project on PYTHONPATH | Cycle 6 restructure moved the gate test to pytester; cycle 7 caught that my `_CONFTEST_BRIDGE` imports would `ModuleNotFoundError`. Fixed via explicit `sys.path.insert(0, _PROJECT_ROOT)` derived from `Path(__file__).resolve().parents[2]`. Commit `d367b65`. |
| `claude-agent-sdk` v0.2.83 exposes no token usage | Listed in RESEARCH.md as Pitfall 5 — confirmed during 05-02 implementation. Cost path returns `cost_usd=0.0` for this branch; documented in code comment + README. |

---

## ✅ Worked well — keep doing

- **Codex as external reviewer.** First adversarial pass found 8 HIGHs the internal checker missed. Every subsequent cycle paid off (even cycles that caught meta-bugs my own manual fixes introduced).
- **`/gsd:verify-work` cold-start render.** This is where transitive-dep conflicts surface. Two of the three I hit (`pydantic-ai[mistral]`, `fastmcp<3`) were not caught by any earlier gate.
- **`/gsd:code-review` post-verify-work.** Caught the cost double-tokenization bug (WR-04) that polarity tests + threat model both missed. Different gate, different class of bug.
- **Rule 08 restructure trigger.** When trajectory hit 1 → 3, restructuring closed it in one cycle. Grinding more would have wasted hours.
- **Beads-first task tracking.** All four OSS blockers filed cleanly: `verify-kit-3u2`, `verify-kit-yr7`, `verify-kit-93h`, `verify-kit-1v6`. Future-me reading `bd ready` will see them grouped.

---

## 🛠 Process insights

> [!tip] Insights worth promoting to project rules
>
> **1. Match "accepted risk" disposition to distribution intent.**
> The Phase 5 SECURITY.md "accepted" T-05-15 (prompt injection) is technically resolvable per-phase but materially unresolved per-project-intent (OSS release). Future phases that consider `accept` dispositions should explicitly ask: "accepted under what distribution scope?" If the answer changes, the disposition changes. See [[accepted-risk-must-match-distribution-intent]].
>
> **2. The four-gate sequence (convergence → verify-work → secure-phase → code-review) is non-redundant.**
> Each gate caught bugs the prior gates missed. Tempting to skip code-review on "small" phases — don't. WR-04 was a real production bug. See [[each-gate-catches-different-classes-of-bug]].
>
> **3. ROADMAP checkboxes are stale by design; STATE.md is the source of truth.**
> Two memories now enforce this. *memory: `state-md-is-source-of-truth`*.
>
> **4. Sub-agent claims must be verified.**
> The research agent's "slopcheck unavailable" claim cost a `checkpoint:human-verify` task in 05-01 that should never have existed. Verify negative claims by sub-agents before they propagate into plans. See [[sub-agent-false-claims-must-be-grounded]].
>
> **5. Slim-package + explicit extras > meta-packages with implicit transitives.**
> `pydantic-ai` (meta) pulls all extras → conflicts. `pydantic-ai-slim[anthropic,openai]` (slim) pulls only what's needed. General rule: for any extras-heavy package, prefer slim + explicit extras.

---

## 📚 Atomic learnings

Each links to a standalone reusable note in `research/learnings/`:

- [[internal-checker-vs-external-reviewer]] — internal reviewers share planner perspective; external reviewers are orthogonal
- [[convergence-oscillation-restructure-trigger]] — 1→3 oscillation = rule 08 restructure signal
- [[manual-fix-meta-bug-cascade]] — each manual fix to a fragile verify can introduce fresh meta-bugs
- [[transitive-dep-conflicts-only-uv-sync-catches]] — spec-time reviews can't see the full resolver
- [[cost-double-tokenization-pattern]] — tokencost per-string vs `litellm.completion_cost`
- [[sub-agent-false-claims-must-be-grounded]] — verify negative claims by sub-agents
- [[state-md-vs-roadmap-checkbox-confusion]] — read STATE.md, not ROADMAP checkboxes
- [[accepted-risk-must-match-distribution-intent]] — "accept" disposition is relative to distribution scope
- [[each-gate-catches-different-classes-of-bug]] — convergence, verify-work, secure-phase, code-review are non-redundant
- [[keyword-checks-are-not-comprehensibility-checks]] — grep-for-string ≠ human-read
- [[heavy-verify-belongs-in-verify-work-not-execute-plan]] — inline 12-cell renders hang executors

---

## 📌 Carry-forward

For the next session (likely Phase 6 + OSS hardening pass), the open items are:

| Item | Source | Priority |
|---|---|---|
| Run Phase 6 (template self-test CI matrix + README + CHANGELOG + CONTRIBUTING + architecture diagram + dual-audience checklist) | ROADMAP.md | next phase |
| OSS hardening — route auth scaffold | beads `verify-kit-3u2` | P1, blocks OSS release |
| OSS hardening — `/summarize` prompt-injection defenses + input cap | beads `verify-kit-yr7` | P1, blocks OSS release |
| OSS hardening — `/echo` same hardening | beads `verify-kit-93h` | P1, blocks OSS release |
| OSS hardening — Phase 5 README human-read pass | beads `verify-kit-1v6` | P1, blocks OSS release; could fold into Phase 6 |
| Phase 3 — re-validate `fastmcp>=3.3` API surface (bearer-auth, ToolAnnotations namespaces) | beads `verify-kit-fastmcp-3x` | P2 |
| Phase 2 — partial SC#1: `<2s first-run` budget not enforced | `02-VERIFICATION.md` `gaps_found` | P2-3 |
| Flip ROADMAP.md checkboxes for Phases 1-5 to `[x]` | (presentation lag) | trivial |

> [!success] What landed this session in commits
> ```
> 50 commits total. Highlights:
> 8f24983  initial 5 plans
> 0019335  + RESEARCH + revised plans after internal checker
> 45cd4dc  Codex c1 review (8 HIGHs)
> bb201fd  replan cycle 1
> 6233038  Codex c2 review (5 HIGHs)
> 23b28a3  replan cycle 2
> 27c873a  Codex c3 review (2 HIGHs)
> 823b71c..d367b65  manual-fix + adversarial loop (cycles 4-7)
> 48604cc  rule 08 restructure
> 925bae4  Codex c8 review (0 HIGHs) — CONVERGED
> 0fd475a  D-22 drop tokenx-core
> 718cc8b  T2: copier.yml _exclude block
> 76cbbea  T3: pyproject deps
> 2b60b3f  T4: app/.env.example LLM block
> 01edb81  T5: root .env.example
> ed1854a  fix(deps): otel-instrumentation-httpx pin (beads verify-kit-x60)
> 85c0cee..98c2b48  05-02 harness/llm.py
> 616a3f1..58cfe1f  05-04 eval + nightly + langfuse compose
> 8987022..2fcb523  05-03 vcr + tests/llm + eval check
> 280ea33..659d4d5  05-05 /summarize + SKILL.md + README
> f7e6037  T4 polarity test (manually committed)
> af37dfb  05-05 SUMMARY (manually written)
> daba26f  fix(deps): pydantic-ai-slim + fastmcp 3.3 (caught by verify-work)
> 05d0dae  05-UAT.md PASSED 69/69
> 0861c4f  05-SECURITY.md 19/19 SECURED
> b406bd0  code-review fixes (5 warnings)
> 43cddad  05-REVIEW.md artifact
> ```
