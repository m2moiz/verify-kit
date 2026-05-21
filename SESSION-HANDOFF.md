# Session Handoff — verify-kit

> **Read this first if you're a fresh Claude session opening this repo.** Then read `CLAUDE.md` and `research/README.md`.
>
> This file is a *map of pointers*, not a snapshot. It rots slowly; the live sources of truth (`STATE.md`, `ROADMAP.md`, `bd prime`, git log) update themselves. When this file disagrees with them, trust them.

## Project in one paragraph

verify-kit is a **Copier-based scaffold template** that bundles a self-verifiable agentic-coding harness. The thesis: Claude Code (and any autonomous coding agent) is half-blind — it can't click buttons, hear audio, or watch a game render — so without feedback loops baked in from day one, "done" claims are unfounded and the developer becomes the QA function. The template ships a project skeleton where every feature is verifiable end-to-end without human intervention: structured logs, dev-only debug endpoints, headless browser smoke tests, audio round-trip checks, LLM eval gates, and a single `just verify` ground-truth command.

**Scope (locked):** Path 3 — Universal Foundation + Backend add-on + LLM add-on in v0.1 (~3–4 weeks). v0.2 adds Web / Audio / Game. **Standalone portfolio project**, not coupled to any other repo.

**Dual first-class citizen** is the load-bearing constraint: every feature serves human (terminal + IDE) AND coding agent (MCP + JSON) equally. Six-row checklist in `research/00-architecture-overview.md` gates every feature.

## Where things stand (auto-derive, don't memorize)

For the *current* position, always read in this order:

1. `.planning/STATE.md` — current phase, current plan, last activity. Machine-maintained.
2. `.planning/ROADMAP.md` — all 6 phases with their requirement coverage.
3. `bd prime` — auto-injects current task state at session start (Beads is the persistent issue tracker).
4. `git log --oneline -20` — what actually shipped.

At the time this file was last touched, the roadmap was:

| Phase | Title | Status anchor (verify with `STATE.md`) |
|-------|-------|----------------------------------------|
| 1 | Template Skeleton & Toolchain | first phase completed |
| 2 | Universal Harness Core | second phase completed |
| 3 | Agent Integration & IDE (MCP server + 13 tools) | third phase completed |
| 4 | Backend (FastAPI) Add-on | active / queued — 7 plans, 5 waves |
| 5 | LLM Add-on | pending |
| 6 | Template Self-Test & Documentation | pending |

Don't trust the table above to be current — confirm against `STATE.md`.

## Operating model

- **GSD is mandatory for all file-changing work** (see `CLAUDE.md` and the global rules in `~/.claude/rules/`). Enter through `/gsd:execute-phase N`, `/gsd:quick`, or `/gsd:debug`. Do not freelance edits.
- **Beads (`bd`) tracks tasks.** Use `bd ready` to find work, `bd update <id> --status=in_progress` to claim, `bd close <id>` when done. NEVER use TodoWrite/markdown lists as substitutes. NEVER use `bd edit` (opens vim, blocks the agent) — use `bd update <id> --notes="..."`.
- **`.planning/REVIEW-CHECKLIST.md`** is required reading before any plan, review, or replan. It accumulates per-project landmines (cwd leaks, dead-code-via-narrative-ordering, cross-plan contract drift). The convergence workflow auto-injects it; manual sessions should `cat` it explicitly.
- **Convergence loop is the default** (not the upsell) per global rule 08. Never skip GSD ceremonies (plan-review-convergence, secure-phase, verify-work, validate-phase) without a concrete zero-value reason.
- **Branching:** new phases branch off `main` (not the previous phase's branch — origin/main is the pinned base, see plan-convergence rule).

## Key files / pointers

```
.planning/STATE.md                    # live position
.planning/ROADMAP.md                  # the 6 phases
.planning/REQUIREMENTS.md             # v0.1 requirements
.planning/REVIEW-CHECKLIST.md         # project landmines
.planning/phases/<NN>-<slug>/         # phase artifacts (PLAN.md, RESEARCH.md, REVIEWS.md, SUMMARY.md)
.planning/scripts/check-plan-shapes.sh# dead-shape grep after every convergence
.planning/learnings/                  # phase retros — read before planning new work

CLAUDE.md                             # project-specific GSD/agent context
~/.claude/rules/                      # global rules (security, sessions, beads, plan convergence)
~/.claude/projects/.../memory/        # auto-memory (MEMORY.md index + per-topic .md files)

research/README.md                    # MOC for the research knowledge base
research/00-*.md                      # synthesis docs (architecture, autonomous workflow, stack, decisions)
research/agent-reports/               # raw research wave outputs
research/tools/*.md                   # tool quick-cards
research/scripts/audit-obsidian.py    # validates wikilinks/embeds across the vault
```

## Failure modes to avoid

These have actually bitten this project — they are not hypothetical.

1. **Trusting STATE.md without sanity-checking.** STATE.md can drift if a workflow exits mid-run. Cross-check against `git log` and SUMMARY.md presence in the active phase directory before claiming a plan is/isn't done.
2. **Grep is not verification.** After manual plan fixes, run an independent Codex semantic re-review — `check-plan-shapes.sh` only catches textual patterns.
3. **Convergence oscillation = structural problem.** If HIGH count bounces (e.g., 2→3→2→3 across cycles), restructure the plan division (move contracts to producers); don't grind another cycle.
4. **Post-restructure prose drift.** After any structural restructure, expect 1–2 cycles of title/objective/threat-model alignment — stale references in prose are not real bugs but cleanup.
5. **`git add .` is forbidden.** Stage files by name. The repo has been near-misses with stray credentials in untracked files.

## Step zero for any new session

```bash
cd /Users/moiz/Documents/code/verify-kit
cat .planning/STATE.md           # current phase + plan
bd ready                          # what's actually queued
git log --oneline -10             # what just shipped
cat .planning/REVIEW-CHECKLIST.md # landmines
```

Then enter through a GSD command (`/gsd:execute-phase N`, `/gsd:debug`, or `/gsd:quick`).
