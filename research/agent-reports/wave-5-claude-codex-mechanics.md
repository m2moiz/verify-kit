---
title: Claude Code + Codex CLI Orchestration Mechanics
aliases: [Wave 5 - Claude+Codex, codex exec, claude -p, dux, oh-my-hermes, relay]
tags: [research, wave-5, claude-code, codex, orchestration, headless]
wave: 5
source_agent: claude-codex-mechanics
created: 2026-05-17
---

# Orchestrating Claude Code + Codex CLI on One Repo (2026 Practical Guide)

> [!abstract] Headline
> Working solo-dev pattern in 2026: **worktree + file handoff + headless flags**, NOT MCP buses. Claude plans with `claude -p`, writes `PLAN.md`. Codex executes with `codex exec --cd <worktree> --sandbox workspace-write --ask-for-approval never --output-last-message <path>`, appends `PHASE-EXEC-NOTES.md`, exits with status code bash can branch on. Reach for `relay`/`oh-my-hermes` only when you outgrow 50-line shell script — most solo setups never do.

## 1. Codex CLI — What's Actually There in 2026

OpenAI's `codex` CLI (Rust, currently ~v0.130) has matured into real headless tool.

| Command | Purpose |
|---|---|
| `codex` | Interactive TUI |
| `codex exec` (alias `e`) | **Headless / scripted.** Streams progress to `stderr`, final assistant message to `stdout` — pipeable |
| `codex resume [--last \| SESSION_ID]` | Continue session |
| `codex fork` | Branch from prior session |
| `codex mcp` | Manage MCP server entries (Codex is MCP **client**; `codex mcp serve` exposes it as **server** too) |
| `codex remote-control` | New in v0.130 — headless app-server you drive over WebSocket from another process |

**Critical `codex exec` flags:**

- `--json` — NDJSON event stream (`thread.started`, `turn.completed`, `item.*`)
- `--output-last-message, -o PATH` — write final assistant message to file (handoff goldmine)
- `--output-schema PATH` — force final response to conform to JSON Schema
- `--sandbox {read-only|workspace-write|danger-full-access}` — default is `workspace-write`
- `--ask-for-approval {untrusted|on-request|never}`
- `--dangerously-bypass-approvals-and-sandbox` (alias `--yolo`) — fully autonomous
- `--ephemeral` — don't persist rollout
- `--cd PATH` — set workdir (essential for worktree pattern)
- `--skip-git-repo-check`
- `codex exec -` — read full prompt from stdin

**Config:** `~/.codex/config.toml` (global) or `.codex/config.toml` (per-project, must be "trusted project"). MCP servers under `[mcp_servers.<name>]`:

```toml
[mcp_servers.context7]
command = "npx"
args = ["-y", "@upstash/context7-mcp"]
```

**Project memory:** `AGENTS.md` at repo root. Codex walks from project root down to cwd, reading `AGENTS.override.md` → `AGENTS.md` at each level. Equivalent to Claude's `CLAUDE.md`.

**`/goal` slash command** (shipped in both Codex and Claude Code late 2025) closes the loop: `/goal X until Y without Z` runs until validator confirms completion or budget exhausted. New canonical autonomous primitive.

**Disambiguation:** "Codex" here is OpenAI's `codex` Rust CLI from `openai/codex`, not the 2021 Codex model and not Anthropic's anything.

## 2. Claude Code — Orchestration Surface

- **Headless:** `claude -p "prompt"` (alias `--print`). `--output-format {text|json|stream-json}`. `stream-json` is NDJSON suitable for piping
- **Resume:** `claude --continue` (most recent) or `claude --resume <session-id>`
- **Hooks** (`.claude/settings.json`): `SessionStart`, `SessionEnd`, `PreToolUse`, `PostToolUse`, `Stop`, `SubagentStop`, `UserPromptSubmit`, `Notification`, `PreCompact`. `Stop` and `SubagentStop` are the handoff trigger points
- **Task tool** spawns subagents in-process (shared model budget, separate context window)
- **MCP:** Claude Code consumes MCP servers (`.mcp.json` or `~/.claude/settings.json`) and can host them via `claude mcp serve`
- **Skills/slash commands** live in `.claude/skills/` and `.claude/commands/`

## 3. Inter-Agent Communication — What Actually Works

| Pattern | Reality |
|---|---|
| **File-based (PHASE-EXEC-NOTES.md / STATE.md)** | The dominant pattern. Simple, debuggable, git-trackable. Used by GSD, oh-my-hermes, relay's tickets.json |
| **MCP as bus** | Works. `relay` exposes 19 tools across both CLIs via one MCP server hosted at `~/.relay/`. Best when you want bi-directional querying, not just hand-off |
| **Git commits as signals** | Works with `fswatch`/`inotifywait` watching `.git/refs/heads/<branch>`. Brittle — easy to double-trigger |
| **GitHub Actions between agents** | Heavy. Useful only if PRs are unit of work |
| **Shared SQLite** | Overkill for two agents |
| **tmux panes** | What `dux` and `oh-my-claudecode` use. Human-watchable, scriptable via `tmux send-keys`. Good for "watch them work overnight" |

## 4. Real Meta-Orchestrators in 2026

- **`dux`** (patrickdappollonio) — TUI wrapper spawning claude/codex/gemini/opencode in **isolated git worktrees**. `brew install patrickdappollonio/tap/dux`. Forks sessions but not transcripts
- **`oh-my-hermes`** (HERMESquant) — Specifically Claude+Codex. Drops `.omh/sessions/{claude,codex,handoff}/`. Commands: `omh save --tool codex`, `omh handoff codex`, `omh handoff claude`, `omh forge-merge ...`
- **`relay`** (jcast90) — Attaches as MCP server to both CLIs: `rly claude` / `rly codex`. State in `~/.relay/channels/<id>/{feed.jsonl,tickets.json,decisions/}`. Best abstraction for "two agents in different repos message each other"
- **`mco`** (mco-org) — Neutral dispatch layer, parallel fan-out with JSON/SARIF aggregation
- **`claude-flow`** — separate ecosystem, more about Claude swarms than Claude+Codex specifically

## 5. GSD's Cross-AI Pattern

GSD detects available CLIs by probing `command -v claude codex gemini`. `/gsd:review` shells out: writes artifact to review into temp dir, then invokes other CLI in headless mode (`codex exec --json -o ...` or `gemini -p ...`), captures `-o` output file, parses concerns. `/gsd:plan-review-convergence` is loop: replan in host CLI, re-invoke peer CLI, exit when no HIGH concerns remain. `/gsd:autonomous` chains discuss→plan→execute per phase without human checkpoints — purely within Claude, but reviewers can be external CLIs.

## 6. Sandboxing

- Codex's built-in `--sandbox workspace-write` is cheapest isolation — process-level, no container
- For real isolation: run Codex inside Docker container with repo bind-mounted read-write to **only its worktree** and read-only to `shared/` dir. `vercel-sandbox` and Modal sandboxes both work but overkill solo
- Cap autonomy on dangerous one: Codex with `--sandbox workspace-write --ask-for-approval never` is the **autonomous-but-bounded sweet spot**. Avoid `--yolo` unless containerized

## 7. The Handoff Problem — Answered

- **Done signal:** `codex exec` exits 0/nonzero AND writes to `--output-last-message PATH`. Claude polls file (size > 0 + exit code) or watches via `fswatch -o PATH`
- **Pickup:** Codex reads `PLAN.md` because launching prompt tells it to. There is no magic — file path goes in prompt string
- **Race conditions on commit:** Solved by **worktrees**. Each agent gets own branch + worktree. Merge happens in third process (orchestrator), never by either agent
- **PHASE-EXEC-NOTES.md:** Writer = whoever just finished. Reader = next agent in chain. Append-only with `## YYYY-MM-DD HH:MM <agent>` header per entry. Git history is audit trail

## 8. Cost Guardrails

Codex respects `OPENAI_API_KEY` and surfaces `turn.completed` events with token counts in `--json`. Wrap with `jq` to sum usage. Claude Code emits same in `--output-format stream-json`. Hard caps: wrapper script that increments counter file and `exit 1`s past budget. **Neither CLI has native daily caps — you build it.**

---

## (A) Shortest Autonomous Overnight Loop — Copy-Paste

**`.claude/settings.json`** — fires Codex when Claude finishes plan:

```json
{
  "hooks": {
    "Stop": [{
      "matcher": "",
      "hooks": [{"type": "command", "command": "bash .agents/on-claude-stop.sh"}]
    }]
  }
}
```

**`run-overnight.sh`** at repo root:

```bash
#!/usr/bin/env bash
set -euo pipefail
GOAL="${1:?usage: ./run-overnight.sh \"goal text\"}"
REPO="$(git rev-parse --show-toplevel)"
WT="$REPO/.worktrees/codex"
git worktree add -B codex/work "$WT" main 2>/dev/null || true
mkdir -p "$REPO/.agents"

while true; do
  # 1. Claude plans into PLAN.md (headless, JSON for cost tracking)
  claude -p "Read .agents/STATE.md. Goal: $GOAL.
Write the next atomic task to PLAN.md. If goal is met, write DONE to .agents/STATUS." \
    --output-format stream-json --dangerously-skip-permissions \
    | tee -a .agents/claude.log >/dev/null

  [[ -f .agents/STATUS && "$(cat .agents/STATUS)" == "DONE" ]] && break

  # 2. Codex executes PLAN.md in worktree, writes notes, exits with status
  codex exec --cd "$WT" --sandbox workspace-write --ask-for-approval never \
    --json -o "$REPO/.agents/CODEX-LAST.md" \
    "Read $REPO/PLAN.md. Execute task-by-task with atomic git commits on branch codex/work.
When done, append a dated section to $REPO/.agents/PHASE-EXEC-NOTES.md describing what shipped,
what failed, and what you'd hand back. Exit 0 on success, 2 on partial, 1 on failure." \
    2>>.agents/codex.log
  CODEX_RC=$?

  # 3. Update shared STATE.md for Claude's next iteration
  {
    echo "## $(date -Iseconds) codex rc=$CODEX_RC"
    cat .agents/CODEX-LAST.md
  } >> .agents/STATE.md

  git -C "$WT" push origin codex/work || true
  (( CODEX_RC == 1 )) && { echo "Codex hard-failed"; break; }
done
```

Run: `nohup ./run-overnight.sh "make tests pass without changing public API" >/tmp/overnight.log 2>&1 &`

## (B) Handoff State Machine

```
                     ┌───────────────────────────────────────────┐
                     │              STATE.md (append-only)        │
                     │   read by: Claude    written by: loop      │
                     └───────────────────────────────────────────┘
                              ▲                          │
              writes STATE    │                          │ reads
                              │                          ▼
   ┌──────────────────┐   PLAN.md     ┌──────────────────────────┐
   │   CLAUDE (-p)    │──────────────▶│       PLAN.md             │
   │   plans next     │   writes      │   read by: Codex          │
   │   atomic task    │               └──────────────────────────┘
   └──────────────────┘                          │
        │   ▲                                    ▼
        │   │ STATUS=DONE       ┌───────────────────────────────┐
        │   │ ends loop         │  CODEX exec --cd worktree     │
        │   │                   │  --output-last-message ...    │
        │   │                   │  exit 0 / 2 / 1               │
        │   │                   └───────────────────────────────┘
        │   │                                    │
        │   │                                    ▼
        │   │    appends         ┌───────────────────────────────┐
        │   └────────────────────│ PHASE-EXEC-NOTES.md +         │
        │                        │ CODEX-LAST.md + git commits   │
        │                        └───────────────────────────────┘
        │                                        │
        └────────────────────────────────────────┘
                       loop back to Claude

Transitions:
  Claude.Stop hook → checks PLAN.md exists → launches codex exec
  codex exit 0 → loop continues
  codex exit 2 → loop continues, Claude sees partial in STATE.md
  codex exit 1 → loop breaks, human triage
  STATUS=DONE  → loop breaks, success

Failure modes:
  • PLAN.md empty / malformed     → Codex no-ops; STATE shows "rc=0 no diff"; Claude must detect
  • Codex hangs                   → wrap in `timeout 30m codex exec ...`
  • Both commit to same branch    → prevented by worktree on `codex/work`
  • Webfont/tool timeouts in MCP  → Codex returns nonzero; loop breaks
  • Budget blown                  → wrap codex/claude with token-counting jq filter that exits 1
```

## (C) Codex Starting Prompt (Drop-In)

```bash
#!/usr/bin/env bash
# .agents/run-codex-task.sh — invoked by Claude's Stop hook or overnight loop
set -euo pipefail

REPO="$(git rev-parse --show-toplevel)"
WT="$REPO/.worktrees/codex"
PLAN="$REPO/PLAN.md"
NOTES="$REPO/.agents/PHASE-EXEC-NOTES.md"
OUT="$REPO/.agents/CODEX-LAST.md"

[[ -f "$PLAN" ]] || { echo "no PLAN.md" >&2; exit 3; }
[[ -d "$WT" ]] || git worktree add -B codex/work "$WT" main

read -r -d '' PROMPT <<'EOF' || true
You are the executor agent. Operate strictly inside the current working
directory (a git worktree on branch codex/work). Do NOT touch other branches
or worktrees. Read PLAN.md at the repo root.

For each task in PLAN.md, in order:
  1. State the task in one line.
  2. Make the minimal change to accomplish it.
  3. Run the project's test command (see AGENTS.md). If it fails, fix forward
     up to 2 retries; if still failing, mark the task BLOCKED and stop.
  4. git add the specific files (never `git add .`), then commit with a
     Conventional Commits message referencing the task.

When all tasks pass OR you hit a BLOCKED task, append a section to
.agents/PHASE-EXEC-NOTES.md with today's ISO date, a "Shipped:" bullet list
of commit SHAs + one-line summaries, a "Blocked:" section if any, and a
"Handback:" paragraph telling the planner agent what to decide next.

Exit codes you MUST honor:
  0  = all tasks shipped, tests green
  2  = partial: at least one task shipped, at least one BLOCKED
  1  = nothing shipped / hard failure
EOF

timeout 30m codex exec \
  --cd "$WT" \
  --sandbox workspace-write \
  --ask-for-approval never \
  --skip-git-repo-check \
  --json \
  --output-last-message "$OUT" \
  "$PROMPT"
```

---

**Bottom line:** working solo-dev pattern in 2026 is *worktree + file-handoff + headless flags*, not MCP buses. Claude plans with `claude -p`, writes `PLAN.md` and reads `STATE.md`; Codex executes with `codex exec --cd <worktree> --sandbox workspace-write --ask-for-approval never -o <file>`, appends to `PHASE-EXEC-NOTES.md`, and exits with meaningful code a bash `while` loop can branch on. Reach for `relay` or `oh-my-hermes` only when you outgrow 50-line shell script.

## Sources

- [Codex CLI command reference](https://developers.openai.com/codex/cli/reference)
- [Codex non-interactive mode](https://developers.openai.com/codex/noninteractive)
- [Codex MCP docs](https://developers.openai.com/codex/mcp)
- [Codex AGENTS.md guide](https://developers.openai.com/codex/guides/agents-md)
- [Codex config reference](https://developers.openai.com/codex/config-reference)
- [Codex CLI v0.130 reference (Blake Crosley)](https://blakecrosley.com/guides/codex)
- [Shipyard Codex CLI cheatsheet](https://shipyard.build/blog/codex-cli-cheat-sheet/)
- [Claude Code headless mode](https://code.claude.com/docs/en/headless)
- [Claude Code subagents](https://code.claude.com/docs/en/sub-agents)
- [Claude Code hooks (12 lifecycle events)](https://claudefa.st/blog/tools/hooks/hooks-guide)
- [Agent SDK hooks](https://platform.claude.com/docs/en/agent-sdk/hooks)
- [The /goal command in Codex and Claude Code](https://apidog.com/blog/goal-command-codex-claude-code-autonomous-agents/)
- [Setting up a repo for both Claude Code and Codex (Jeremy Watt)](https://neonwatty.com/posts/how-to-set-up-your-repo-for-claude-code-and-codex/)
- [Running multiple agents in parallel — dux (Patrick D'appollonio)](https://www.patrickdap.com/post/how-to-run-multiple-agents/)
- [Relay — orchestrate coding agents across repos](https://github.com/jcast90/relay)
- [oh-my-hermes — Claude+Codex handoff](https://github.com/HERMESquant/oh-my-hermes)
- [mco — neutral multi-CLI orchestration](https://github.com/mco-org/mco)
- [DEV: How I orchestrate Claude, Codex, Gemini as a swarm](https://dev.to/elophanto/how-i-orchestrate-claude-code-codex-and-gemini-cli-as-a-swarm-4p3c)
- [Beam: orchestrate Claude, Codex, Gemini together](https://getbeam.dev/blog/orchestrate-claude-codex-gemini-together.html)
- [Porting AI coding workflows Claude→Codex](https://dev.to/shinpr/same-framework-different-engine-porting-ai-coding-workflows-from-claude-code-to-codex-cli-n3p)

## Related notes

- [[wave-5-multi-agent-case-studies]] · [[wave-5-coordination-primitives]] · [[wave-5-gsd-autonomous]]
- [[00-autonomous-workflow]] · [[00-architecture-overview]]
