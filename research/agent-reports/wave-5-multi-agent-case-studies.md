---
title: Multi-Agent Autonomous Coding Case Studies
aliases: [Wave 5 - Multi-Agent Cases, Spotify Honk, Cursor, Devin, Ralph Loop]
tags: [research, wave-5, autonomous, multi-agent, spotify-honk]
wave: 5
source_agent: multi-agent-case-studies
created: 2026-05-17
---

# Multi-Agent Autonomous Coding Workflows in Production (2024–2026)

> [!abstract] Headline
> **The production winners (Spotify Honk, Cursor 2.0, Anthropic research, Factory.ai) all converged on the same shape:** Isolated sandboxes per agent + deterministic verifier as trust anchor + LLM judge as scope-creep guard + human at PR review. Solo-dev version: two worktrees, `VERIFY.sh`, judge prompt, Ralph loop with budget caps.

## 1. Spotify Honk — Canonical Industrial Reference

- **Sources:** [Honk Part 1](https://engineering.atspotify.com/2025/11/spotifys-background-coding-agent-part-1) · [Part 2 Context Engineering](https://engineering.atspotify.com/2025/11/context-engineering-background-coding-agents-part-2) · [Part 3 Feedback Loops](https://engineering.atspotify.com/2025/12/feedback-loops-background-coding-agents-part-3) · [QCon London 2026 InfoQ](https://www.infoq.com/news/2026/03/spotify-honk-rewrite/)
- **What:** Engineers Slack a request. Honk (built on Claude Agent SDK) spawns sandboxed container, reads repo, edits, runs formatters/linters/builds/tests, opens PR. Sits on "Fleet Management" (since 2022) which fans changes across thousands of repos, and Backstage for ownership lookup
- **Coordination:** Per-repo isolation in K8s sandboxes; orchestration *external* (Fleet Management) not agent-to-agent. **Two-layer verification:** (a) **deterministic verifiers** auto-discovered from repo contents (Maven verifier if `pom.xml` exists, etc.), and (b) **LLM judge** comparing diff to original prompt — vetoes ~25% of PRs for scope creep; about half self-correct. Stop hook blocks PR creation if verifiers fail
- **Human checkpoint:** PR review by code owners. Humans never see PRs failing inner verifier loop
- **Failure mode they obsess over:** "Passes CI but is functionally wrong" — they consider this the trust-killer
- **Solo fit:** Marginal as architecture (you don't have Fleet Management) — but *patterns* (deterministic verifiers + LLM judge + stop hook) are directly stealable
- **Catch:** Whole thing rests on ~3 years of pre-existing platform work

## 2. Cognition / Devin — Cautionary Tale

- **Sources:** [Cognition's own 2025 review](https://cognition.ai/blog/devin-annual-performance-review-2025) · [Devin Review](https://cognition.ai/blog/devin-review) · [The Register on Answer.AI eval](https://www.theregister.com/2025/01/23/ai_developer_devin_poor_reviews/)
- **What:** Async agent assigned ticket; works in cloud VM; opens PR
- **Failure modes:** Answer.AI's 20-task eval = 3 wins, 14 fails, 3 inconclusive. Persisted on infeasible paths instead of failing fast. "Senior at codebase understanding, junior at execution." Cognition now scopes Devin to "tasks junior would do in 4–8h with clear up-front requirements" — migrations, vuln fixes, unit-test backfill
- **Solo fit:** N/A (closed SaaS, expensive, hosted)
- **Catch:** Honest lesson is "narrow the task class until success rate is acceptable" — the meta-pattern

## 3. Cursor 2.0 Cloud Agents (Oct 2025)

- **Sources:** [Cursor 2.0 changelog](https://cursor.com/changelog/2-0) · [CometAPI deep dive](https://www.cometapi.com/cursor-2-0-what-changed-and-why-it-matters/)
- **What:** Up to **8 parallel agents** on single prompt, each in own **git worktree** or remote VM. Each lands a PR. New "plan with one model, build with another" workflow
- **Coordination:** Worktree isolation is entire conflict-prevention mechanism. No inter-agent messaging; human picks best PR
- **Human checkpoint:** PR selection
- **Solo fit:** Good as *pattern* (worktrees + branch-per-agent + merge-best)
- **Catch:** "Pick the best of 8" is fan-out, not collaboration

## 4. GitHub Copilot Coding Agent + Agent HQ

- **Sources:** [GA announcement](https://github.blog/news-insights/product-news/github-copilot-meet-the-new-coding-agent/) · [Agent HQ](https://github.blog/news-insights/company-news/pick-your-agent-use-claude-and-codex-on-agent-hq/) · [VS Code multi-agent](https://code.visualstudio.com/blogs/2026/02/05/multi-agent-development)
- **What:** `@copilot` on issue → draft PR in background via GitHub Actions → request review. Agent HQ (2026) lets you pick Claude / Codex / Copilot on same task
- **Coordination:** GitHub Issues/PRs are message bus. Branch per agent. PR comments re-trigger agent
- **Solo fit:** Good if GitHub-native. Useful pattern: **issue = task contract, PR = output contract, PR comments = feedback loop**

## 5. OpenHands (formerly OpenDevin)

- **Sources:** [arXiv paper](https://arxiv.org/pdf/2407.16741v2) · [docs](https://docs.openhands.dev/openhands/usage/agents)
- **What:** Generalist `CodeActAgent` whose tool surface is just `bash`, `python`, browser DSL — "express anything as code." Multi-agent via `AgentDelegateAction`: agent hands subtask to another (coder delegates web research to BrowsingAgent). Central **event stream** as state
- **Coordination:** Typed-event hub; delegation primitive; shared event log
- **Solo fit:** Good reference architecture; event-stream-as-truth and bash-as-universal-tool patterns generalize

## 6. SWE-agent / mini-swe-agent

- **Sources:** [GitHub](https://github.com/SWE-agent/mini-swe-agent) · [DeepWiki architecture](https://deepwiki.com/SWE-agent/mini-swe-agent/1.1-architecture-overview)
- **What:** ~100 lines of Python. `while` loop: LLM emits bash command → run in sandboxed Docker → stdout+returncode appended to context → repeat. **Stateless** (each command via `subprocess.run`). Scores 74%+ on SWE-bench Verified
- **Lesson:** Smallest viable autonomous coding agent is while-loop + bash + sandbox. Everything else is optimization

## 7. Aider Architect/Editor Mode

- **Source:** [Aider docs](https://aider.chat/2024/09/26/architect.html)
- **What:** Two-model pattern. Architect model reasons about change in natural language; Editor model converts prose into exact diff edits. Measurably reduces multi-file refactor errors at **30–50% lower cost** than running strong model end-to-end
- **Solo fit:** **Excellent** — directly maps to "Claude (architect) + Codex (editor)" or vice-versa. Cheapest real-world two-agent win

## 8. Factory.ai Droids

- **Sources:** [Sid Bharath guide](https://sidbharath.com/blog/factory-ai-guide/) · [Custom Droids docs](https://docs.factory.ai/cli/configuration/custom-droids)
- **What:** Coordinator decomposes Linear/Jira ticket, dispatches to **specialized droids** (Code, Review, Knowledge, Test, Reliability) each with own system prompt + model + tool policy, each in own sandbox. DroidShield does pre-commit static analysis
- **Coordination:** Hierarchical (coordinator → specialists). Explicit role boundaries
- **Solo fit:** Good *pattern* (specialization-by-role with explicit prompts), feasible to mimic with Claude Code subagents

## 9. Anthropic's Multi-Agent Research System (June 2025)

- **Source:** [Anthropic engineering post](https://www.anthropic.com/engineering/multi-agent-research-system)
- **Pattern:** **Orchestrator-worker**. Lead Claude plans → spawns N parallel subagent Claudes, each with own context window and tools → subagents return **condensed findings** via shared memory store (not raw chat) → lead reconciles
- **Wins:** +90.2% over single Claude Opus 4 on research eval. Token usage explains 80% of variance
- **Catch:** ~15× token cost of single chat. Anthropic explicitly says pattern fits "research-shaped" tasks, not all coding (coding more sequential/interdependent)

## 10. The Ralph Wiggum Loop (Geoffrey Huntley, May 2025)

- **Sources:** [ghuntley.com/loop](https://ghuntley.com/loop/) · [LinearB podcast](https://devinterrupted.substack.com/p/inventing-the-ralph-wiggum-loop-creator) · [Vercel ralph-loop-agent](https://github.com/vercel-labs/ralph-loop-agent)
- **What:** Literally `while true; do claude -p "$(cat PROMPT.md)"; done`. Agent re-reads its instructions every loop; verification failures get fed back into next iteration. Huntley runs this on bare-metal NixOS pushing straight to master, ~$10/hr
- **Multi-agent extension:** Run *two* Ralph loops on different worktrees — one as "implementer," one as "reviewer/verifier" — sharing markdown task file
- **Solo fit:** **Excellent** for overnight use case. Simplest thing that demonstrably works
- **Catch:** Needs hard cost caps and verifier with teeth, or wake up to $1k bill and 200 broken commits

## 11. Decomposition Patterns — What Actually Works

| Pattern | Where it works | Where it fails |
|---|---|---|
| **Hierarchical (planner→executor→verifier)** | Aider architect, Factory, Anthropic research. Best general default | Planner hallucinates work that doesn't exist; executor blindly implements |
| **Pipeline (each agent = stage)** | Spotify Honk inner loop (generate → format → test → judge) | Pipeline stalls when stages disagree |
| **Swarm / fan-out** | Cursor 2.0's "8 worktrees on same prompt, pick best" | Pure waste of compute if tasks aren't truly independent |
| **Peer-to-peer negotiation** | Mostly academic | Loops, deadlocks, infinite "let me consult the other agent." **Don't** |
| **Supervisor + worker** | Anthropic research, OpenHands delegation | Works when subtasks factorable; collapses when they share state |

**Empirical consensus:** hierarchical + pipeline beats peer-to-peer in every production report. Swarm only when fan-out is actual goal.

## 12. Failure Modes & Mitigations (Honest List)

| Failure | Mitigation that actually works |
|---|---|
| Agents step on each other's edits | **Git worktrees, one branch per agent.** Non-negotiable |
| Infinite loops (ping-pong) | Hard iteration cap + cost cap. Ralph loops need `MAX_ITERS` |
| Cost runaway (1.67B-token, $50k Claude Code incident, July 2025 — see [sanj.dev](https://sanj.dev/post/llm-cost-control)) | Daily budget enforcement at API key level. Anthropic + OpenAI both support usage caps |
| Hallucinated completion | **LLM judge** against original spec (Spotify's outer loop), or separate "verifier" agent that has *only* spec + diff |
| Context drift across handoffs | Persistent `PLAN.md` / `SPEC.md` re-read each iteration (Ralph pattern) |
| Architecture disagreement | Single source of truth = spec file. Don't let agents argue; let them edit shared markdown doc |
| CI-passing-but-wrong | Deterministic verifiers + LLM judge before PR (Honk pattern) |

## 13. Structured Artifacts as Inter-Agent Contracts

Convergent consensus across [Addy Osmani](https://addyosmani.com/blog/good-spec/), [Spec Kit](https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/), [AGENTS.md spec](https://developers.openai.com/codex/guides/agents-md), Factory's custom-droid configs:

- `AGENTS.md` / `CLAUDE.md` — repo-level operating instructions. Industry-wide convention
- `SPEC.md` — what to build (user-facing)
- `PLAN.md` — how to build (step list, files touched, verification commands)
- `contracts/` — typed interfaces (OpenAPI, TS types) as hand-off boundary
- `TASKS.md` with `[ ] / [in-progress] / [x]` markers is cheapest functional inter-agent message bus on single repo

## 14. Sandboxing & Safety

[Vercel Sandbox](https://vercel.com/docs/vercel-sandbox) (Firecracker microVMs, GA Jan 2026), [Modal](https://northflank.com/blog/modal-vs-vercel-sandbox) (gVisor, 24h sessions, GPUs), [E2B](https://www.firecrawl.dev/blog/ai-agent-sandbox) — production-grade options. For solo: Docker container + non-root user + read-only mount of secrets is enough.

---

## Recommendation for verify-kit: Claude Code + Codex CLI, Single Repo, Overnight Autonomy

> [!warning] Be honest up front
> **"Fully autonomous overnight with zero supervision"** is achievable, but **"fully autonomous overnight with zero damage when it goes wrong"** requires hard caps. Plan for the failure.

### Architecture

**Pattern: Hierarchical pipeline with Aider-style two-agent specialization, in two worktrees, coordinated by markdown task file, supervised by Ralph loop with verifier gates.**

### Coordination Mechanism

- **Two git worktrees** off `main`: `wt-claude/` and `wt-codex/`. Conflict-free substrate. Use Claude Code's `--worktree` flag, or `dux` ([Patrick D'Appollonio's writeup](https://www.patrickdap.com/post/how-to-run-multiple-agents/))
- **Shared `.agents/` directory at repo root**, committed:
  - `AGENTS.md` — house rules both agents read every loop
  - `SPEC.md` — goal for this run, written by you before bed
  - `PLAN.md` — Claude (architect) writes/updates
  - `TASKS.md` — checklist; both agents read, only one mutates row at a time
  - `VERIFY.sh` — deterministic gate (`copier copy --pretend && pytest && ruff check && pyright`). Exits 0 = pass
  - `JUDGE_PROMPT.md` — LLM-judge instructions ("does this diff match SPEC.md? PASS or FAIL with reason")

### Decomposition

- **Claude Code = Architect.** Reads `SPEC.md`, updates `PLAN.md` and `TASKS.md`. Never edits source. (Mirrors Aider's Architect role and Anthropic's lead-agent pattern)
- **Codex CLI = Implementer.** Reads `PLAN.md` + `TASKS.md`, edits source in its worktree, runs `VERIFY.sh`, commits on green
- **Verifier loop** (also Claude Code, separate cheap-model invocation, headless): on every commit, runs `VERIFY.sh`; if green, runs LLM judge against `SPEC.md`; if judge says PASS, opens PR; if FAIL, appends reason to `TASKS.md` as new task. (Spotify's two-layer verification at solo-dev scale)
- Outer **Ralph loop** is 30-line bash script with `MAX_ITERS=20`, `MAX_USD=15`, exits on either cap or `TASKS.md` shows all done

### Human Checkpoints That Should Remain

1. **Morning PR review.** Even Honk has this; you should too. Never auto-merge to `main`
2. **`SPEC.md` writing.** You write spec before bed. Don't let agents author it
3. **Cost cap tripwire** — script `git push` to `wip/overnight-YYYYMMDD` branch and exit cleanly if budget hits 80%
4. **First-three-runs supervision.** Watch first 3 overnight cycles end-to-end before trusting unwatched. Devin lesson is real

### Three Anti-Patterns to Avoid By Name

1. **"Let the agents talk to each other directly."** Peer-to-peer agent chat loops are where infinite loops and cost explosions live. **Force every handoff through file commit. Filesystem is your message bus**
2. **"One agent, both roles."** Don't have Codex do both planning and implementation in same context window — lose Architect/Editor cost+quality win and judge has nothing independent to compare against
3. **"`--dangerously-skip-permissions` + no budget cap + auto-push to main."** [$50k Claude Code recursion incident](https://sanj.dev/post/llm-cost-control) in three flags. Always cap iterations, always cap USD, always push to feature branch

### First Three Steps for verify-kit Tonight

1. **Stand up contract files.** Create `.agents/{AGENTS.md, SPEC.md, PLAN.md, TASKS.md, VERIFY.sh, JUDGE_PROMPT.md}`. `VERIFY.sh` runs existing Copier dry-render + pytest + ruff + pyright. Test it manually exits 0 on clean tree and non-zero on broken one. **Single most important step** — without credible verifier, no autonomous loop is safe
2. **Set up two worktrees and Ralph loop.** `git worktree add ../verify-kit-arch -b agent/architect` and `../verify-kit-impl -b agent/implementer`. Write ~50-line `overnight.sh` that alternates: Claude headless against architect worktree updates `PLAN.md`/`TASKS.md`; Codex headless against implementer worktree picks next `[ ]` task, edits, runs `VERIFY.sh`, commits on green; verifier Claude runs judge; loop with `MAX_ITERS=20` and cost check via Anthropic + OpenAI usage APIs
3. **Do daylight dry run with tiny spec.** Pick real but trivial verify-kit task (e.g., "add `--dry-run` flag to post-gen hook"). Write `SPEC.md`. Run `overnight.sh` while you watch. Observe where it gets stuck. Fix verifier or prompts — not agents. Once it cleanly produces mergeable PR on 30-minute task while you watch, *then* trust it for 8-hour run

### Honest Summary

In 2026 the production winners (Spotify, Cursor, Factory, Anthropic) all converge on the same shape — **isolated sandboxes per agent, deterministic verifier as trust anchor, LLM judge as scope-creep guard, human at PR review.** Solo-dev version of that is two worktrees, a `VERIFY.sh`, a judge prompt, and a Ralph loop with budget caps. Everything else is decoration.

## Sources

- [Spotify Honk Part 1](https://engineering.atspotify.com/2025/11/spotifys-background-coding-agent-part-1)
- [Spotify Honk Part 2 — Context Engineering](https://engineering.atspotify.com/2025/11/context-engineering-background-coding-agents-part-2)
- [Spotify Honk Part 3 — Feedback Loops](https://engineering.atspotify.com/2025/12/feedback-loops-background-coding-agents-part-3)
- [QCon London 2026 on Honk (InfoQ)](https://www.infoq.com/news/2026/03/spotify-honk-rewrite/)
- [Cognition: Devin 2025 Performance Review](https://cognition.ai/blog/devin-annual-performance-review-2025)
- [Cursor 2.0 changelog](https://cursor.com/changelog/2-0)
- [CometAPI: Cursor 2.0 multi-agent rethink](https://www.cometapi.com/cursor-2-0-what-changed-and-why-it-matters/)
- [GitHub Copilot coding agent GA](https://github.blog/news-insights/product-news/github-copilot-meet-the-new-coding-agent/)
- [Agent HQ — Claude & Codex on GitHub](https://github.blog/news-insights/company-news/pick-your-agent-use-claude-and-codex-on-agent-hq/)
- [OpenHands ICLR 2025 paper](https://arxiv.org/pdf/2407.16741)
- [OpenHands docs — Main Agent](https://docs.openhands.dev/openhands/usage/agents)
- [mini-swe-agent GitHub](https://github.com/SWE-agent/mini-swe-agent)
- [Aider Architect/Editor blog](https://aider.chat/2024/09/26/architect.html)
- [Factory.ai guide (Sid Bharath)](https://sidbharath.com/blog/factory-ai-guide/)
- [Factory Custom Droids docs](https://docs.factory.ai/cli/configuration/custom-droids)
- [Anthropic: How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- [Geoffrey Huntley: everything is a ralph loop](https://ghuntley.com/loop/)
- [Dev Interrupted: Inventing the Ralph Wiggum Loop](https://devinterrupted.substack.com/p/inventing-the-ralph-wiggum-loop-creator)
- [Vercel Labs ralph-loop-agent](https://github.com/vercel-labs/ralph-loop-agent)
- [Patrick D'Appollonio: running multiple agents in parallel](https://www.patrickdap.com/post/how-to-run-multiple-agents/)
- [Git worktrees parallel AI agents (MindStudio)](https://www.mindstudio.ai/blog/parallel-agentic-development-git-worktrees)
- [sanj.dev: AI agents don't crash, they spend ($50k incident)](https://sanj.dev/post/llm-cost-control)
- [Addy Osmani: How to write a good spec for AI agents](https://addyosmani.com/blog/good-spec/)
- [GitHub Spec Kit](https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/)
- [OpenAI AGENTS.md spec](https://developers.openai.com/codex/guides/agents-md)
- [Vercel Sandbox docs](https://vercel.com/docs/vercel-sandbox)
- [Modal vs Vercel Sandbox comparison](https://northflank.com/blog/modal-vs-vercel-sandbox)

## Related notes

- [[wave-5-coordination-primitives]] · [[wave-5-claude-codex-mechanics]] · [[wave-5-gsd-autonomous]]
- [[00-autonomous-workflow]] · [[00-architecture-overview]] · [[00-decision-log]]
