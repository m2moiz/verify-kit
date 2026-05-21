---
title: GSD Autonomous + Spec-Driven Workflows
aliases: [Wave 5 - GSD Autonomous, Spec-Driven Development, GSD Cross-AI]
tags: [research, wave-5, gsd, autonomous, spec-driven, plan-review-convergence]
wave: 5
source_agent: gsd-autonomous
created: 2026-05-17
---

# GSD Autonomous + Cross-AI + Spec-Driven Development Landscape (2026)

> [!abstract] Headline
> **GSD already does most of what's needed.** v1.42.3 ships `/gsd:autonomous`, `/gsd:plan-review-convergence --codex`, `/gsd:review`, plus `npx get-shit-done-cc@latest --codex` installs skills for Codex CLI too (so Codex can run GSD skills directly). Gaps: no Stop-hook-triggered phase advance, no cost/time caps, no worktree-per-phase isolation. Smallest shim is a bash wrapper + Stop hook.

## 1. GSD Skill Ecosystem — Deep Dive

User has GSD installed at `~/.claude/get-shit-done/` (workflows, references, bin) and `~/.claude/skills/gsd-*` (49 skills). Canonical repo is **[gsd-build/get-shit-done](https://github.com/gsd-build/get-shit-done)** by TÂCHES (npm: `get-shit-done-cc`, v1.42.3, ~58.9K stars).

Verified from `~/.claude/skills/gsd-autonomous/SKILL.md` and workflow file:

- **`/gsd:autonomous`** *(skill: `gsd-autonomous`)* — Driver loop. Reads `ROADMAP.md` via `gsd-sdk query roadmap.analyze`, filters incomplete phases, then for each: **discuss → plan → execute** by spawning `Agent(...)` calls that invoke other Skills (`Skill('gsd-plan-phase', ...)`, `Skill('gsd-execute-phase', ...)`). Flags `--from N | --to N | --only N | --interactive`. Pauses only for grey-area decisions, blockers, validation requests. **Maturity: production.** Subagents get fresh 200k contexts; main context stays at 30–40%
- **`/gsd:plan-review-convergence`** *(skill: `gsd-plan-review-convergence`)* — Outer loop around plan + review. Repeats `plan-phase → review → if HIGH concerns: plan-phase --reviews → review` until convergence or `--max-cycles N` (default 3). **Gated behind `workflow.plan_review_convergence=true`** in `gsd config-set`. Flags select reviewers: `--codex --gemini --claude --opencode --ollama --lm-studio --llama-cpp --all`. **This is the user's lever for autonomous cross-AI**
- **`/gsd:review`** *(skill: `gsd-review`)* — Detects which external CLIs are present via `command -v`. Probes Ollama/LM Studio/llama.cpp via HTTP. Builds one review prompt (PROJECT.md + ROADMAP phase section + all `*-PLAN.md`), invokes each reviewer's CLI in non-interactive mode, writes structured `REVIEWS.md`. Self-skip logic via `CLAUDE_CODE_ENTRYPOINT` / `CURSOR_SESSION_ID` env vars — running inside Claude Code, it auto-skips `--claude` so review is genuinely external
- **`/gsd:fast`** — Inline trivial task, no subagents
- **`/gsd:quick`** — Atomic commit + state tracking, no optional agents

**Model profile system** (`balanced | quality | budget | inherit`) configured via `gsd config` and applied per skill — different agents can use different models, but routing is by GSD's internal profile, not arbitrary per-call.

**Hooks**: GSD installs many in `~/.claude/hooks/` (verified): `gsd-phase-boundary.sh`, `gsd-validate-commit.sh`, `gsd-workflow-guard.js`, `gsd-context-monitor.js`, `gsd-session-state.sh`. These enforce phase transitions and commit discipline but are not autonomous-loop triggers.

**Codex routability** (v1.42.3): `npx get-shit-done-cc@latest --codex` installs skills under Codex CLI 0.130+. So **Codex CLI can run GSD skills directly** — meaning Codex can execute `gsd-execute-phase` on a `PLAN.md` Claude wrote. ([Releases](https://github.com/gsd-build/get-shit-done/releases))

## 2. Planning Artifact Protocol — Agent-Agnostic Contract

Files: `.planning/PROJECT.md`, `REQUIREMENTS.md`, `ROADMAP.md`, per-phase `CONTEXT.md` + `NN-NN-PLAN.md` + `STATE.md` + `SUMMARY.md` + `VERIFICATION.md`. Plus beads-backed task IDs and atomic-commit discipline. **This is the inter-agent contract.** Because `gsd-sdk` is a CLI (`node ~/.claude/get-shit-done/bin/gsd-tools.cjs`), any runtime that can shell out — Codex CLI, Gemini CLI, OpenCode — can query/update it. **Fit: excellent.** PLANs are markdown with explicit success criteria; Codex picks them up without translation.

## 3. Spec-Driven Development Movement (2026)

| Tool | What | Maturity | Fit |
|---|---|---|---|
| **[GitHub Spec-Kit](https://github.com/github/spec-kit)** (71k★) | `specify → plan → tasks → implement` slash commands; supports 29 agents incl. Claude Code + Codex CLI | Production | Excellent for greenfield, overlaps GSD; **do not run both on same repo** |
| **GSD** (~59k★) | Same idea, richer phase/audit/eval coverage | Production | Already installed |
| **Aider CONVENTIONS.md** | Single markdown file injected each session | Mature | Marginal (no phase loop) |
| **Linear spec mode** | Specs as Linear issues, agent picks up | Beta | Marginal for solo |
| **Specstory** | Captures + replays agent sessions | Beta | Niche |
| **Sourcegraph Cody specs** | Spec-bound agents over Cody index | Production | Enterprise-leaning |

Convergent pattern across all: **spec is source of truth, any agent implements, verifier validates, loop until verdict APPROVED.** GSD already implements this end-to-end.

## 4. Cross-AI Workflows

[SmartScope's 2026 walkthrough](https://smartscope.blog/en/blog/claude-code-codex-review-loop-automation-2026/) is the cleanest published recipe. Pattern:

1. Claude writes `PLAN.md`
2. Bash invokes `codex exec -m gpt-5.3-codex -s read-only "Review /tmp/plan.md. End with VERDICT: APPROVED or VERDICT: REVISE"`
3. Parse stdout for `VERDICT:`
4. If REVISE, Claude revises; `codex exec resume <uuid>` continues same Codex thread. Max 5 rounds
5. Read-only sandbox enforces reviewer can't touch implementation

**GSD's `gsd-plan-review-convergence` is essentially this pattern, productized, with HIGH-concern severity gating.**

## 5. Spotify Honk

Nothing substantive public; Honk is internal and references to "spec discipline" are mostly rumor. Skip.

## 6. Autonomous-Loop Patterns

| Pattern | Source | Maturity | Fit |
|---|---|---|---|
| **[Ralph Wiggum Loop](https://ghuntley.com/ralph/)** (Geoffrey Huntley, mid-2025) | Bash `while` loop, single agent, `IMPLEMENTATION_PLAN.md` accumulates, fresh context each iteration | Battle-tested ($297 finishes $50k contract; YC team shipped 6 MVPs overnight) | **Excellent** — composes with GSD |
| **[snarktank/ralph](https://github.com/snarktank/ralph)** | Reference implementation | Production | Good |
| **[Claude Squad](https://github.com/smtg-ai/claude-squad)** | tmux + worktree per agent; supports Claude Code, Codex, OpenCode, Aider | Production | Good for parallel workstreams |
| **[claude-tmux MCP](https://github.com/Ilm-Alan/claude-tmux)** | Spawn subagents in tmux from Claude itself | Beta | Marginal |
| **OpenHands** ($18.8M, 65k★) | Full autonomous platform | Production | Heavy for solo |
| **Cline / RooCode** | Cline alive; **Roo Code shut down May 15, 2026** | — | Avoid Roo |
| **Claude Code Routines** (Anthropic) | Cloud-scheduled autonomous Claude Code | Production beta | Good for cron-driven |

## 7. "Human-Not-In-Loop" Safety

From [dev.to: "10 Claude Code Hooks I Collected From 108 Hours of Autonomous Operation"](https://dev.to/yurukusa/10-claude-code-hooks-i-collected-from-108-hours-of-autonomous-operation-now-open-source-5633) and the Anthropic [hooks guide](https://code.claude.com/docs/en/hooks-guide): working pattern is **Stop hook with `stop_hook_active` guard** (mandatory — otherwise infinite loop), **exit-2 to block + force continuation**, **JSON `{"decision":"block","reason":"..."}`** for richer signaling, plus counter file to cap iterations. Wake-human triggers via `osascript -e 'display notification'` (macOS) or `gh issue create`.

## 8. GSD Tactical Answers

- *"Run Phase 1 via Codex instead of Claude?"* — Yes since v1.42.3. Install GSD with `--codex`, then `codex exec "/gsd:execute-phase 1"`
- *"Codex reviews Phase 1 while Claude plans Phase 2?"* — Native via `gsd-plan-review-convergence --codex` for Phase 1 in one terminal; manually start Claude planning Phase 2 in another (worktree). GSD does not orchestrate cross-phase parallelism today
- *"Does GSD detect Codex CLI?"* — Yes, `gsd-review` workflow does `command -v codex`
- *`text_mode`* — Non-Claude runtime fallback that replaces `AskUserQuestion` with numbered text prompts. Required for Codex/Gemini CLI which lack structured-question API
- *Example projects* — None of note; GSD-driven multi-AI repos aren't public yet

## 9. What GSD Lacks for True Overnight Autonomy

1. **No native Stop-hook-triggered phase advance.** `/gsd:autonomous` runs only while Claude session is live; if Claude stops, loop dies
2. **No cost/time caps** — autonomous mode runs until ROADMAP is empty or it hits grey-area decision
3. **No failure-counter circuit breaker.** Stall detection exists for convergence loop but not broader autonomous driver
4. **No notification on grey-area pause.** It just waits silently
5. **No worktree-per-phase isolation** — phases run in main worktree, so broken plan can poison subsequent phases

**These are exactly the shims you write yourself.**

## 10. Published Recipes (2025–2026)

- [Inventing the Ralph Wiggum Loop](https://devinterrupted.substack.com/p/inventing-the-ralph-wiggum-loop-creator) — interview
- [paddo.dev: Ralph Wiggum for Claude Code](https://paddo.dev/blog/ralph-wiggum-autonomous-loops/) — Claude-specific
- [SmartScope: Claude × Codex Review Loop Automation 2026](https://smartscope.blog/en/blog/claude-code-codex-review-loop-automation-2026/) — three levels: SKILL.md, plugin, pipeline
- [Augment Code: GSD hits 58.9K stars](https://www.augmentcode.com/learn/gsd-58k-stars-claude-code)
- [Pulumi: Superpowers, GSD, GSTACK comparison](https://www.pulumi.com/blog/claude-code-orchestration-frameworks/)
- [Spec-Kit + Claude Code gist (Arun Gupta)](https://gist.github.com/arun-gupta/e1c2c3a826a0605f6b615d25da918f75)

---

## Deliverable A — GSD-Native Autonomous Cross-AI Recipe

For verify-kit, one repo, Claude as driver + Codex as adversarial reviewer:

```bash
# One-time setup (DONE on 2026-05-17)
gsd-sdk query config-set workflow.plan_review_convergence true
gsd-sdk query config-set review.default_reviewers '["codex"]'
npx get-shit-done-cc@latest --codex --global   # makes GSD skills resolvable from Codex too

# Per milestone — fire-and-forget loop, run from Claude Code session:
/gsd:new-milestone "verify-kit v0.1"
/gsd:plan-review-convergence 1 --codex --max-cycles 3   # plan + Codex adversarial review until APPROVED
/gsd:autonomous --from 1                                # execute all phases, fresh subagent per task
```

**What's missing natively** for "Codex executes Phase N while Claude plans Phase N+1":
- Gap 1: cross-phase parallelism — GSD is per-phase sequential
- Gap 2: no Stop-hook-driven resumption

**Smallest shim** — bash wrapper that runs Claude on plan(N+1) and Codex on execute(N) in two worktrees, then merges:

```bash
git worktree add ../verify-kit-exec   # for Codex
git worktree add ../verify-kit-plan   # for Claude
( cd ../verify-kit-exec && codex exec -s workspace-write "/gsd:execute-phase $N" ) &
( cd ../verify-kit-plan && claude -p "/gsd:plan-phase $((N+1))" ) &
wait
```

[Claude Squad](https://github.com/smtg-ai/claude-squad) automates exactly this — install (`brew install claude-squad`) and skip the bash.

## Deliverable B — Stop-Hook → Codex Review Setup

Create `.claude/hooks/codex-review.sh` (executable):

```bash
#!/usr/bin/env bash
# Stop hook: when Claude finishes, ask Codex to adversarial-review the last PLAN.md.
# If Codex says REVISE, force Claude to keep working with feedback.
set -euo pipefail

INPUT=$(cat)
# Guard against infinite loop — REQUIRED.
if [ "$(echo "$INPUT" | jq -r '.stop_hook_active // false')" = "true" ]; then
  exit 0
fi

# Cap iterations per session.
STATE_DIR="${CLAUDE_PROJECT_DIR:-$PWD}/.claude/state"
mkdir -p "$STATE_DIR"
COUNTER="$STATE_DIR/codex-review-count"
COUNT=$(cat "$COUNTER" 2>/dev/null || echo 0)
if [ "$COUNT" -ge 5 ]; then
  osascript -e 'display notification "Codex review cap hit — human needed" with title "GSD"' || true
  exit 0
fi
echo $((COUNT + 1)) > "$COUNTER"

# Find the most recent PLAN.md to review.
PLAN=$(ls -t .planning/phases/*/[0-9]*-PLAN.md 2>/dev/null | head -1)
[ -z "$PLAN" ] && exit 0

# Run Codex in an isolated worktree so it can't mutate Claude's HEAD.
WORKTREE="/tmp/codex-review-$$"
git worktree add -q "$WORKTREE" HEAD 2>/dev/null || { exit 0; }
trap 'git worktree remove --force "$WORKTREE" >/dev/null 2>&1 || true' EXIT

REVIEW=$(cd "$WORKTREE" && timeout 600 codex exec -m gpt-5.3-codex -s read-only \
  "Adversarially review $PLAN against .planning/PROJECT.md and .planning/REQUIREMENTS.md. \
   List HIGH-severity concerns only. End your reply with exactly one line: \
   VERDICT: APPROVED   or   VERDICT: REVISE" 2>&1 || echo "VERDICT: APPROVED")

if echo "$REVIEW" | grep -q "VERDICT: REVISE"; then
  REASON=$(echo "$REVIEW" | sed -n '/VERDICT:/!p' | tail -50)
  # JSON decision tells Claude to keep working with this feedback.
  jq -n --arg r "Codex review found HIGH concerns. Address them:\n\n$REASON" \
        '{decision:"block", reason:$r}'
  exit 0
fi

# APPROVED — reset counter, let Claude stop.
rm -f "$COUNTER"
exit 0
```

Register in `.claude/settings.json`:

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          { "type": "command", "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/codex-review.sh", "timeout": 900 }
        ]
      }
    ]
  }
}
```

Behavior: every time Claude tries to stop, Codex reads latest PLAN.md in read-only worktree, returns verdict, and on REVISE the JSON decision forces Claude to continue with feedback inline. Capped at 5 cycles, then macOS notification fires.

## Deliverable C — Honest Assessment for verify-kit Overnight

**Realistic tonight, with current 2026 stack:**
- Plan→review→replan convergence for 2–3 phases (`/gsd:plan-review-convergence` with `--codex`). High confidence
- Execute single well-spec'd phase (`/gsd:execute-phase`) with Stop-hook above gating completion via Codex. Medium-high confidence
- Ralph-loop a tightly-scoped slice (single PLAN.md, clear DONE criteria, comprehensive test suite). Medium confidence

**Still needs the human:**
- Initial `REQUIREMENTS.md` quality — autonomous loops amplify spec ambiguity into wasted hours. Spend 30 min on REQUIREMENTS before bed; that's highest-leverage move
- Grey-area accept/reject decisions GSD pauses for. Set `workflow.skip_discuss=true` and accept that some plans will be wrong
- Anything touching secrets, infra, or destructive git ops
- Multi-phase architectural choices — Codex catches tactical errors, not strategic ones

**Failure-recovery story at 3am:**
- **GSD circuit breaker:** add `MAX_PHASES=2` env check to wrapper, hard-exit after
- **Cost cap:** wrap session in `timeout 6h claude -p ...` and trust Stop-hook counter for inner loops
- **Damage containment:** run entire session in `git worktree` of `main`, never on `main` directly. Morning review is `git diff main worktree-branch`. If broken, `git worktree remove` and you've lost compute, not code
- **Wake triggers:** `osascript` notification on cap-hit, plus `gh issue create` on any hook returning non-zero unhandled exit. Optionally pipe to ntfy.sh for phone push
- **Eval gate:** before merging worktree, run `backend/.venv/bin/python -m compileall` and test suite; if either fails, leave worktree for human review

**Opinionated recommendation for tonight:** install [Claude Squad](https://github.com/smtg-ai/claude-squad), enable `workflow.plan_review_convergence=true`, drop Stop-hook from Deliverable B into repo, then run single `/gsd:autonomous --from 1 --to 2` in worktree with 6-hour `timeout`. **Two phases done well overnight beats five phases of garbage to clean up at breakfast.** Scale up only after one clean overnight run.

**Files referenced (absolute paths):**
- `/Users/moiz/.claude/get-shit-done/workflows/autonomous.md`
- `/Users/moiz/.claude/get-shit-done/workflows/review.md`
- `/Users/moiz/.claude/get-shit-done/workflows/plan-review-convergence.md`
- `/Users/moiz/.claude/skills/gsd-autonomous/SKILL.md`
- `/Users/moiz/.claude/skills/gsd-plan-review-convergence/SKILL.md`
- `/Users/moiz/.claude/skills/gsd-review/SKILL.md`
- `/Users/moiz/.claude/hooks/` (existing GSD hooks)

## Sources

- [gsd-build/get-shit-done](https://github.com/gsd-build/get-shit-done/) · [Releases](https://github.com/gsd-build/get-shit-done/releases) · [USER-GUIDE.md](https://github.com/gsd-build/get-shit-done/blob/main/docs/USER-GUIDE.md) · [npm get-shit-done-cc](https://www.npmjs.com/package/get-shit-done-cc)
- [GitHub Spec-Kit](https://github.com/github/spec-kit) · [GitHub blog: spec-driven development](https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/) · [Arun Gupta gist](https://gist.github.com/arun-gupta/e1c2c3a826a0605f6b615d25da918f75)
- [Claude Squad](https://github.com/smtg-ai/claude-squad) · [Anthropic: agent-teams](https://code.claude.com/docs/en/agent-teams) · [claude-tmux MCP](https://github.com/Ilm-Alan/claude-tmux)
- [Ralph Wiggum: ghuntley.com](https://ghuntley.com/ralph/) · [everything is a ralph loop](https://ghuntley.com/loop/) · [snarktank/ralph](https://github.com/snarktank/ralph) · [paddo.dev Ralph for Claude](https://paddo.dev/blog/ralph-wiggum-autonomous-loops/)
- [Anthropic hooks guide](https://code.claude.com/docs/en/hooks-guide) · [Anthropic hooks reference](https://code.claude.com/docs/en/hooks) · [10 hooks from 108h autonomous](https://dev.to/yurukusa/10-claude-code-hooks-i-collected-from-108-hours-of-autonomous-operation-now-open-source-5633) · [Claude Code Routines](https://pasqualepillitteri.it/en/news/851/claude-code-routines-cloud-automation-guide)
- [SmartScope: Claude×Codex review loop](https://smartscope.blog/en/blog/claude-code-codex-review-loop-automation-2026/) · [Codex non-interactive mode](https://developers.openai.com/codex/noninteractive)
- [Pulumi: orchestration frameworks](https://www.pulumi.com/blog/claude-code-orchestration-frameworks/) · [Augment Code: GSD 58.9K](https://www.augmentcode.com/learn/gsd-58k-stars-claude-code) · [One Codebase, Three Runtimes (GSD multi-runtime)](https://medium.com/@richardhightower/one-codebase-three-runtimes-how-gsd-targets-claude-code-opencode-and-gemini-cli-29c98cfe96c6)
- [OpenHands](https://www.openhands.dev/) · [Best open-source coding agents 2026](https://wetheflywheel.com/en/guides/open-source-ai-coding-agents-2026/)

## Related notes

- [[wave-5-multi-agent-case-studies]] · [[wave-5-coordination-primitives]] · [[wave-5-claude-codex-mechanics]]
- [[00-autonomous-workflow]] · [[00-architecture-overview]] · [[00-decision-log]]
