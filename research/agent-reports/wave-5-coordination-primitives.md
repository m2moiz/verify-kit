---
title: Multi-Agent Coordination Primitives
aliases: [Wave 5 - Coordination, Git Worktrees, jj, Tmux, Beads]
tags: [research, wave-5, coordination, git-worktrees, jujutsu, beads]
wave: 5
source_agent: coordination-primitives
created: 2026-05-17
---

# Multi-Agent Coding Coordination Primitives (2024–2026)

> [!abstract] Headline
> **Minimum stack: `git worktrees + tmux + Claude + codex exec + bd + bash + fswatch`** — no Temporal, no Redis, no Mergify, no Graphite, no advisory locks. Everything else is overkill at solo scale. `jj` (Jujutsu) with `--colocate` is the niche upgrade: auto-snapshots every action, free op-log undo. Filesystem is the message bus.

## 1. Git Worktrees — The Dominant Primitive

**Consensus answer.** Every serious tool in 2025–2026 (Cursor Parallel Agents, Claude Code subagents, Devin, Aider, ccswarm, agtx, muxtree, workmux) reaches for `git worktree add` first.

| Pattern | Adoption | Setup | Fit | Catch |
|---|---|---|---|---|
| `git worktree add ../wt-feat-x feat-x` per agent | **Mainstream** | 1 cmd | **Excellent** | Node_modules / `.venv` not shared — each worktree re-installs deps. Use `--lock` to prevent prune |
| Cursor Parallel Agents (auto-managed worktrees) | Mainstream in Cursor | Built-in | Excellent in Cursor | Locked to Cursor's TUI |
| Claude Code `isolation: worktree` subagent frontmatter | Mainstream | 1 line in agent .md | Excellent | Subagents only; main session still in main checkout |
| **`jj` (Jujutsu) workspaces** | Niche, growing fast | `brew install jj` + `jj git init --colocate` | **Excellent for AI** — oplog = free undo, auto-snapshots every action | Learning curve; some tooling assumes git CLI |
| `git-spice` (stacked branches) | Niche | One binary | Good *after* agents finish — for review/merge phase | Doesn't help with isolation; helps with shipping |
| Graphite / `ghstack` / `spr` / Sapling | Niche (Graphite paid) | Server | Marginal — overkill for solo | $/user/mo |
| GitHub native `gh-stack` (April 2026 preview) | Just launched | `gh extension install` | Good for PR submission | Preview only |

**Worktree convention that ships:** one worktree per task under `../wt-<task-id>/`, branch named identically, agent commits every meaningful step, PR opened on completion. **"Branch-per-task" convention is universal.**

**Merge conflicts in parallel:** Two agents touching same file = pain. Empirically-working mitigation is **task-level disjointness** (decompose so different agents touch different paths) enforced by orchestrator/planner, not by clever merge tooling. `jj`'s first-class conflicts help recovery but don't prevent collision.

**Cleanup:** `git worktree prune` + wrapper script. `muxtree` / `workmux` / `agtx` are OSS tools that automate worktree+tmux pairing.

## 2. Branch & PR Coordination

- **Stacked PRs** (Graphite, git-spice, gh-stack, ghstack, spr): emerging multi-agent pattern where each agent produces one focused PR in stack. Joe Buza's documented pattern: constrain agents to <200 LOC per PR. Practical for *teams* of humans + agents; **overkill for solo dev with two agents**
- **Merge queues** (Mergify $21/user/mo, Aviator $12, GitHub native Merge Queue free, Kodiak unmaintained): valuable only once you have >1 PR/hour landing. **GitHub's native Merge Queue is right answer when you need one** — free, integrated
- **Trunk-based for solo + 2 agents:** Don't bother with merge trains. Use feature branches per worktree, merge to main yourself with one-liner

## 3. Shared State Files as Inter-Agent Contract

The **actually-used** coordination layer for Claude Code Agent Teams and most published patterns.

| Pattern | Adoption | Fit | Catch |
|---|---|---|---|
| `STATE.md` / `PROGRESS.md` / `PHASE-EXEC-NOTES.md` markdown | **Mainstream** (Claude Code Agent Teams uses shared task list file) | **Excellent** | Race conditions on simultaneous writes — mitigate with one-writer-at-a-time |
| JSON state file (`.agent/state.json`) | Common | Good | Same race issue; harder to read than markdown |
| Append-only NDJSON event log | Growing | **Excellent** for audit + replay | Need reader to summarize |
| SQLite shared DB with WAL | Niche; **Claude Code itself uses `__store.db`** | Good | **Real bug in wild**: parallel subagents freeze on `__store.db` lock contention (anthropics/claude-code#14124). Tune PRAGMAs |
| `flock` / `fcntl` advisory locks | Almost nobody uses for agents | Marginal | Adds complexity for little real-world benefit at 2-agent scale |
| Postgres `pg_advisory_lock`, Redlock, ZooKeeper | Enterprise | **No** for solo | Requires server |

**Honest pattern:** markdown state file + git commits as event log. Agents read file, append section, commit. **Git's commit history IS your event log; reflog is audit trail.**

## 4. Message Buses

Mostly **overkill for solo use case**, but worth knowing:

- **MCP as message bus** — November 2025 MCP spec adds resource notifications, resumable streams, persistent resources; 2026 roadmap targets agent-to-agent. **Agent Bus MCP** ships this today: named topics, server-side cursors, resume-on-disconnect. Adoption: experimental but trending
- **Redis pub/sub** — production agent systems; needs redis-server. Marginal for solo
- **NATS, MQTT, gRPC streaming** — enterprise agent platforms; **no** for solo
- **filesystem events (`fswatch` / `inotifywait`)** — poor-man's bus and **excellent fit for solo**. `agent-teams-tmux` ships fswatch-based "stigmergic signals" pattern: agent writes file, watcher fires next agent. Zero infrastructure

## 5. Workflow Engines

| Engine | Setup | Solo fit |
|---|---|---|
| **Temporal** (durable execution) | Server / Temporal Cloud | **No** — designed for production agentic systems |
| **Inngest** (event-driven durable funcs) | SaaS or self-host | Marginal |
| **Trigger.dev** (TS-native durable agents) | SaaS | Marginal |
| **n8n / Pipedream / Zapier** | SaaS | No — wrong primitive |
| **Airflow / Dagster / Prefect** | Heavy | **No** |
| **GitHub Actions** | Free, repo-native | **Good** — `workflow_dispatch` + `repository_dispatch` triggers + `gh` CLI = real workflow engine you already have |
| **cron + bash loop** | Native | **Excellent** for overnight runs |
| **Tmux Orchestrator** (Jedward23) | Bash + tmux | **Excellent** — agents schedule own check-ins; built exactly for overnight Claude grinds |

## 6. Leader Election & Locks

For 2 agents on 1 repo: **don't.** Use **task-level partition** (Claude plans, Codex executes; or branch-per-agent) and let git's commit ordering be your serializer.

If you really want lock primitive: `.agent.lock` file + `flock` in bash works and ships in 5 lines. Database advisory locks and Redlock are overengineering.

**Beads (`bd`) as work-claimer:** issue tracker doubles as lock — `bd update <id> --status=in_progress` claims work, ready-queue prevents two agents grabbing same task. **Excellent fit** for solo dev already using GSD workflow.

## 7. Subagent / Spawned-Process Patterns

- **Claude Code Task tool** — orchestrator dispatches subagents in parallel; each can have `isolation: worktree`. Mainstream
- **Codex CLI `codex exec`** — non-interactive headless mode, `--output-schema` for structured JSON, `--sandbox workspace-write` for autonomy. **Right tool for scripted Codex runs.** Open issue (#4179, #4219) about TTY/orchestration rough edges
- **tmux + worktree wrappers**: `muxtree`, `workmux`, `agtx`, `agent-deck`, `ccswarm`, `pi-side-agents`, `ClawTeam`, `Tmux-Orchestrator`. Pick one or write 20 lines of bash
- **Overmind / Hivemind** — Procfile process managers. Overmind = with tmux, Hivemind = without. **Excellent fit** for "start N agents from Procfile and walk away"
- **Long-running daemons vs short-lived invocations**: short-lived `codex exec` / `claude -p` calls win on observability and reproducibility. Daemons drift

## 8. Snapshot + Replay

- **Every agent action commits** — discipline that pays off. Claude Code subagents that auto-commit are noticeably easier to recover
- **`git autostash` on rebase** — keep agents safe from dirty trees
- **`jj` op log** — best-in-class undo (whole sessions reversible). The killer feature for agentic VCS
- **Reflog + branch backups** — last-resort recovery; works

## 9. Resource Limits

- **Per-invocation time budget**: pass `--timeout` to `codex exec`; wrap `claude -p` in `timeout 600`
- **Token budget**: enforce via prompts ("stop after N tool calls"); track via session logs. No tool does this cleanly yet
- **Concurrency limit**: semaphore file or `xargs -P N`. For 2 agents, just run 2
- **Escalate vs retry**: log to `PHASE-EXEC-NOTES.md`, human reads in morning

---

## (A) Minimum-Viable Autonomous Stack — <30 min, No External Services

For solo dev, Claude Code + Codex CLI, one repo, overnight runs:

```
Tools (all local, all free):
  • git worktree           — isolation
  • tmux                   — session multiplexing
  • Claude Code            — planner + verifier
  • codex exec             — executor (headless)
  • Beads (bd)             — work queue + lock
  • fswatch (macOS)        — file-event trigger
  • bash                   — glue
```

**Files / conventions:**

```
repo/
  .agent/
    queue.md               # ordered task list (bd-backed)
    PHASE-N-PLAN.md        # Claude writes
    PHASE-N-EXEC-NOTES.md  # Codex writes
    PHASE-N-VERIFY.md      # Claude writes
    events.ndjson          # append-only event log
  scripts/
    run-overnight.sh       # the loop
  ../wt-phase-N/           # worktree per phase
```

**Setup (one evening):**
1. `bd init --prefix proj` (already standard in your workflow)
2. Add `scripts/run-overnight.sh` that loops: pick next ready `bd` issue → `git worktree add ../wt-$ID $ID` → `claude -p "plan phase $ID, write .agent/PHASE-$ID-PLAN.md"` → `codex exec --sandbox workspace-write "execute .agent/PHASE-$ID-PLAN.md, commit, write PHASE-$ID-EXEC-NOTES.md"` → `claude -p "verify, write PHASE-$ID-VERIFY.md, bd close if pass"`
3. `tmux new -d -s overnight 'bash scripts/run-overnight.sh'`
4. Optional: `fswatch .agent/*-VERIFY.md` to trigger next-phase notifications

That's the whole stack. No Temporal, no Redis, no Mergify. **Git is the bus, files are the contract, Beads is the lock, tmux keeps it alive.**

## (B) Sequence Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│  scripts/run-overnight.sh  (tmux session "overnight")                │
└──────────────────────────────────────────────────────────────────────┘
        │
        │  loop forever:
        ▼
┌─────────────────────┐
│  bd ready --json    │  ──► picks PHASE_N (priority + deps satisfied)
└─────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────────┐
│  git worktree add ../wt-phase-N phase-N                             │
│  cd ../wt-phase-N                                                   │
└─────────────────────────────────────────────────────────────────────┘
        │
        ▼  [PLAN]
┌─────────────────────────────────────────────────────────────────────┐
│  claude -p --output-format=text \                                   │
│    "Plan phase $N. Read .agent/queue.md. Write                      │
│     .agent/PHASE-$N-PLAN.md with file-level edits + acceptance      │
│     criteria. Commit."                                              │
└─────────────────────────────────────────────────────────────────────┘
        │ writes:  .agent/PHASE-N-PLAN.md
        │ commits: "plan(phase-N): ..."
        │ appends: .agent/events.ndjson  {phase:N,stage:plan,ok:true}
        ▼  [EXECUTE]
┌─────────────────────────────────────────────────────────────────────┐
│  codex exec --sandbox workspace-write \                             │
│    --output-schema schema/exec-result.json \                        │
│    "Execute .agent/PHASE-$N-PLAN.md. Commit each file change.       │
│     On completion write .agent/PHASE-$N-EXEC-NOTES.md."             │
└─────────────────────────────────────────────────────────────────────┘
        │ writes:  src/..., .agent/PHASE-N-EXEC-NOTES.md
        │ commits: many small commits on branch phase-N
        │ appends: events.ndjson  {phase:N,stage:exec,ok:true,files:N}
        ▼  [VERIFY]
┌─────────────────────────────────────────────────────────────────────┐
│  claude -p \                                                        │
│    "Verify phase $N against .agent/PHASE-$N-PLAN.md. Run tests.     │
│     Write .agent/PHASE-$N-VERIFY.md. If pass: bd close $N.          │
│     If fail: bd update $N --status=blocked --notes=..."             │
└─────────────────────────────────────────────────────────────────────┘
        │ writes:  .agent/PHASE-N-VERIFY.md
        │ side-effect: bd close $N  (or block)
        ▼  [SHIP or LOOP]
┌─────────────────────────────────────────────────────────────────────┐
│  if pass: git push origin phase-N && gh pr create --base main       │
│  cd repo && git worktree remove ../wt-phase-N                       │
│  → back to top, pick next bd-ready phase                            │
└─────────────────────────────────────────────────────────────────────┘
```

**Triggers used:**
- **bash loop** (cheapest reliable trigger; no cron drift)
- **`bd ready`** as work queue
- **file existence** of `PHASE-N-VERIFY.md` as stage gate
- **git commit hooks** (`bd hooks install`) for state injection
- **tmux** keeps it alive after you close laptop

**What you do NOT need:** Temporal, Mergify, Redis, MCP message bus, Graphite, Aviator, advisory locks, daemon processes, webhooks.

**Upgrade path when you outgrow this:** swap bash loop for **GitHub Actions** triggered on push (free, repo-native), keep everything else. Beyond that, move to **Temporal** only if you start running 10+ concurrent agents across machines.

## Sources

- [Run parallel sessions with worktrees — Claude Code Docs](https://code.claude.com/docs/en/worktrees)
- [Worktrees — Cursor Docs](https://cursor.com/docs/configuration/worktrees)
- [Inside Claude Code's Shared Task List](https://www.mindstudio.ai/blog/claude-code-agent-teams-shared-task-list)
- [Git Worktrees for AI Coding (MindStudio)](https://www.mindstudio.ai/blog/git-worktrees-parallel-ai-coding-agents)
- [Avoid Losing Work with Jujutsu for AI Coding Agents — Panozzo](https://www.panozzaj.com/blog/2025/11/22/avoid-losing-work-with-jujutsu-jj-for-ai-coding-agents/)
- [Parallel Claude Code with Jujutsu — Kurilyak](https://slavakurilyak.com/posts/parallel-claude-code-with-jujutsu)
- [ccswarm — multi-agent orchestration](https://github.com/nwiizo/ccswarm)
- [muxtree — worktree+tmux](https://dev.to/b-d055/introducing-muxtree-dead-simple-worktree-tmux-sessions-for-ai-coding-2kf2)
- [workmux — Raine Virta](https://raine.dev/blog/introduction-to-workmux/)
- [agtx — blackboard for coding agents](https://github.com/fynnfluegge/agtx)
- [Tmux Orchestrator](https://github.com/Jedward23/Tmux-Orchestrator)
- [agent-teams-tmux skill](https://lobehub.com/skills/smartassets-io-skills-agent-teams-tmux)
- [Codex CLI non-interactive mode](https://developers.openai.com/codex/noninteractive)
- [Codex headless orchestration issue #4219](https://github.com/openai/codex/issues/4219)
- [GitHub stacked PRs / gh-stack](https://github.github.com/gh-stack/)
- [git-spice](https://abhinav.github.io/git-spice/)
- [Mergify vs Aviator](https://mergify.com/compare/aviator/)
- [Agent Bus MCP](https://www.agentbusmcp.com/)
- [MCP November 2025 specification](https://medium.com/@dave-patten/mcps-next-phase-inside-the-november-2025-specification-49f298502b03)
- [Microsoft: Agent2Agent on MCP](https://developer.microsoft.com/blog/can-you-build-agent2agent-communication-on-mcp-yes)
- [Temporal AI agents — IntuitionLabs](https://intuitionlabs.ai/articles/agentic-ai-temporal-orchestration)
- [SQLite locking v3](https://sqlite.org/lockingv3.html)
- [Claude Code parallel subagent SQLite lock bug #14124](https://github.com/anthropics/claude-code/issues/14124)
- [Overmind / Hivemind — Evil Martians](https://evilmartians.com/chronicles/introducing-overmind-and-hivemind)
- [Embracing parallel coding agent lifestyle — Simon Willison](https://simonwillison.net/2025/Oct/5/parallel-coding-agents/)
- [Set up your repo for Claude Code and Codex — Jeremy Watt](https://neonwatty.com/posts/how-to-set-up-your-repo-for-claude-code-and-codex/)

## Related notes

- [[wave-5-multi-agent-case-studies]] · [[wave-5-claude-codex-mechanics]] · [[wave-5-gsd-autonomous]]
- [[00-autonomous-workflow]] · [[00-architecture-overview]]
