---
title: claude-squad
aliases: [cs, claude-squad]
tags: [verify-kit, tools, multi-agent, coordination]
created: 2026-05-18
status: COORDINATION-TOOL
layer: cross-project (not generated)
---

# 👥 claude-squad

> [!abstract] One-line summary
> TUI that spawns Claude / Codex / OpenCode / Aider agents in tmux + git worktrees — local-only orchestration.

## What it does

`cs` (or `claude-squad`) launches a textual UI listing your agent runs. Each "session" is a tmux window backed by a git worktree, so multiple agents can work in parallel without stepping on each other. Supports Claude Code, Codex CLI, OpenCode, Aider, and arbitrary commands. Lives entirely on your machine — no network coordination.

## Why we picked it

Verify-kit's multi-agent story (Claude plans / Codex executes boilerplate) needs lightweight worktree orchestration. claude-squad is:

- ✅ Multi-CLI friendly (not Claude-only)
- ✅ Worktree-based isolation matches GSD's executor pattern
- ✅ TUI is fast; no web app to launch
- ✅ Filesystem-only state (no daemon, no network bus)

| Alternative | Why deferred |
|---|---|
| `dux` (Patrick D'Appollonio) | Similar TUI; less established |
| `oh-my-hermes` | Claude+Codex specific; less general |
| `relay` (MCP-based) | Adds a daemon + MCP channel; filesystem bus is enough |

See [[agent-reports/wave-5-coordination-primitives]].

## Usage

```bash
# Launch the TUI
cs

# From inside: 'n' for new session, pick agent (claude / codex / opencode), give it a task
# Each session runs in its own worktree at .squad/worktrees/<id>
```

The "filesystem is the bus" pattern: agents leave handoff files (e.g., `.agents/STATUS` containing `READY` or `DONE`) so a watcher can react without RPC.

## Install

```bash
# Homebrew
brew install smtg-ai/tap/claude-squad

# Or from source
go install github.com/smtg-ai/claude-squad@latest
```

## Gotchas

- **Worktree pruning** — `cs` cleans up its `.squad/worktrees/` on session close, but force-quit can leave stale worktrees; `git worktree prune` is the recovery command.
- **tmux required** — claude-squad uses tmux as the multiplexer; if you don't have tmux installed, install via mise (`mise use -g tmux@latest`).
- **Filesystem bus convention** — verify-kit's pattern: `.agents/STATUS` with literal `READY` / `WORKING` / `DONE` strings. Don't reinvent peer-to-peer messaging — see [[00-stack-decisions#Explicitly rejected]] for why.

## Key docs

- Repo: <https://github.com/smtg-ai/claude-squad>
- Usage examples: in-repo README

## Related notes

- [[00-stack-decisions#Multi-agent coordination tools (separate from generated projects)]] — coordination layer
- [[00-autonomous-workflow]] — Claude+Codex autonomous setup
- [[agent-reports/wave-5-coordination-primitives]] — wave that evaluated it
- Memory note `claude_codex_collab` — the project intent claude-squad implements
