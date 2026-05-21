---
title: verify-kit Research Knowledge Base
aliases: [MOC, Map of Content, Research Index]
tags: [moc, verify-kit, research]
created: 2026-05-17
last_updated: 2026-05-17
---

# 🗺️ verify-kit Research Knowledge Base

> [!info] What this is
> Distilled research from **20 parallel research agents across 5 waves** that produced the verify-kit design. Saved in Obsidian-friendly markdown so you can navigate, search, and reference later. Each agent report preserved verbatim in `agent-reports/`; cross-cutting findings synthesized in `synthesis/`; tool quick-cards in `tools/`.

## ⚡ Quick navigation

| Want to know… | Read |
|---|---|
| The complete verify-kit picture | [[00-architecture-overview]] |
| Claude+Codex autonomous setup | [[00-autonomous-workflow]] |
| All chosen tools at a glance | [[00-stack-decisions]] |
| All key decisions with rationale | [[00-decision-log]] |
| Why we rejected X | [[00-stack-decisions#Explicitly rejected]] |
| The dual-audience checklist | [[00-architecture-overview#Dual-audience checklist]] |
| Session retrospectives + mistakes log | [[synthesis/session-2026-05-18-phase-1-and-2-buildout]] |
| Vault tooling (audit script, etc.) | [[scripts/README]] |

## 🧪 Research waves

### Wave 1 — Verification harness foundations
- [[wave-1-general-verification-harnesses]] — Claude hooks, agent-browser, Ralph loop, Schemathesis, Argos
- [[wave-1-game-testing]] — gdUnit4, JavaScriptBridge, PlayGodot, deterministic replay
- [[wave-1-audio-testing]] — Whisper round-trip, Chromium fake-audio, GPT-4o-audio judge
- [[wave-1-llm-eval-frameworks]] — Langfuse, Promptfoo, OpenLLMetry, vcrpy

### Wave 2 — Architecture & hosting
- [[wave-2-scaffolding-tools]] — Copier vs Cookiecutter vs degit vs Yeoman vs Backstage
- [[wave-2-polyglot-orchestration]] — mise vs Just vs Task vs Make vs Bazel vs Dagger
- [[wave-2-llm-hosting]] — Langfuse Cloud Hobby → Hetzner CX32; Phoenix; Helicone
- [[wave-2-ci-portability]] — GitHub Actions vs Dagger/Earthly; modern test pyramid

### Wave 3 — Human-first UX
- [[wave-3-human-friendly-logging]] — Rich+structlog, Pino+pretty, consola, log levels
- [[wave-3-opentelemetry-local]] — Jaeger all-in-one, otel-desktop-viewer, terminal waterfall
- [[wave-3-vscode-ide]] — tasks.json, launch.json, problem matchers, LSP/DAP-first
- [[wave-3-ease-of-use]] — 30-second rule, miette errors, did-you-mean, anti-patterns

### Wave 4 — Framework specifics
- [[wave-4-fastapi-ecosystem]] — pyinstrument, asgi-correlation-id, schemathesis, logfire, fastapi-mcp
- [[wave-4-nextjs-react]] — Biome, Vitest 4 browser mode, MSW, nuqs, `__VERIFY_KIT__` global
- [[wave-4-ai-sdk-ergonomics]] — pydantic-ai, instructor, litellm, autoevals, vcrpy
- [[wave-4-mcp-agent-integration]] — MCP server, AGENTS.md, isatty discipline, dual-audience checklist

### Wave 5 — Multi-agent autonomous workflows
- [[wave-5-multi-agent-case-studies]] — Spotify Honk, Cursor 2.0, Aider Architect/Editor, Ralph loop
- [[wave-5-coordination-primitives]] — git worktrees, jj, beads, tmux, message buses
- [[wave-5-claude-codex-mechanics]] — `codex exec` flags, `claude -p`, hooks, dux, oh-my-hermes, relay
- [[wave-5-gsd-autonomous]] — `/gsd:autonomous`, `/gsd:plan-review-convergence`, stop-hook setup

## 🛠️ Tool quick-cards

Top tools chosen for verify-kit, one card each:

- [[tools/copier]] — template engine
- [[tools/mise]] — toolchain + task spine
- [[tools/just]] — task runner
- [[tools/langfuse]] — LLM observability
- [[tools/promptfoo]] — LLM eval gate
- [[tools/pydantic-ai]] — typed agent framework
- [[tools/instructor]] — one-call typed LLM responses
- [[tools/litellm]] — LLM provider abstraction
- [[tools/autoevals]] — pytest LLM scorers
- [[tools/vcrpy]] — offline-deterministic LLM tests
- [[tools/openllmetry]] — OTel gen_ai spans
- [[tools/jaeger]] — local trace UI
- [[tools/claude-squad]] — multi-agent worktree+tmux orchestrator
- [[tools/agent-browser]] — token-efficient browser automation
- [[tools/fastapi-mcp]] — FastAPI → MCP server in 3 lines

## 🚫 What we deliberately rejected (and why)

Each has a one-line rationale; see [[00-stack-decisions]] for full reasoning.

| Tool/Pattern | Why rejected |
|---|---|
| Helicone proxy mode | Coupling not worth it across heterogeneous providers (fal, Pioneer, Tavily) |
| Phoenix as primary LLM observability | Weaker multi-project isolation than Langfuse |
| Per-project SQLite logs | "You'll build a worse Langfuse over six months" |
| Earthly | Discontinued July 2025 |
| Dagger | Overkill at solo scale |
| Cookiecutter+Cruft | Copier obsoletes the combo |
| Single-binary Go/Rust harness CLI | Loses extensibility (contributors can't add a check in 10 lines) |
| Yeoman | Declining |
| Backstage scaffolder | Enterprise overkill |
| BAML / DSPy | Too lock-in-heavy for v0.1 |
| Cypress | Playwright won |
| Multi-CI portability (GitLab/CircleCI/Jenkins) | Premature; ~68% of OSS is on GitHub |
| Peer-to-peer agent messaging | Infinite loops + cost explosions; file system is the message bus |
| `--dangerously-skip-permissions` + no budget cap | The $50k Claude Code recursion incident vector |

## 📦 Folder structure

```
research/
├── README.md                        # this file (MOC)
├── 00-architecture-overview.md      # complete verify-kit picture
├── 00-autonomous-workflow.md        # Claude+Codex autonomous setup
├── 00-stack-decisions.md            # all chosen tools, with status & rationale
├── 00-decision-log.md               # key decisions with timestamps
├── agent-reports/                   # raw research outputs (20 files)
│   ├── wave-1-*.md                  # 4 files
│   ├── wave-2-*.md                  # 4 files
│   ├── wave-3-*.md                  # 4 files
│   ├── wave-4-*.md                  # 4 files
│   └── wave-5-*.md                  # 4 files
├── synthesis/                       # cross-cutting distilled findings + session retros
│   └── session-2026-05-18-*.md      # Phase 1 build + Phase 2 plan retrospective
├── scripts/                         # vault-maintenance utilities
│   ├── README.md                    # what each script does, how to run
│   └── audit-obsidian.py            # validates wikilinks/embeds/callouts/frontmatter
└── tools/                           # one quick-card per major tool
    └── *.md
```

## 🔄 How to read this

> [!tip] Recommended reading order
> 1. **[[00-architecture-overview]]** — get the big picture
> 2. **[[00-stack-decisions]]** — see all the tools with verdicts
> 3. **[[00-autonomous-workflow]]** — understand the Claude+Codex setup
> 4. **Pick a wave** from the navigation above that interests you
> 5. **Browse `tools/`** when you want details on a specific tool

> [!note] Obsidian users
> Open this folder as a vault (or include in an existing vault) and use Graph View to see the cross-references. All inter-document links use Obsidian wikilink syntax (`[[Note Name]]`). Tags use `#verify-kit/topic` format.

## 📅 Provenance

- **5 research waves, 20 parallel agents** dispatched between 2026-05-16 and 2026-05-17
- All findings cite 2024–2026 sources (current-date verified at research time)
- Each agent's raw output preserved in `agent-reports/`
- Recommendations distilled in `synthesis/` and per-tool cards in `tools/`
- Decisions and rationale tracked in [[00-decision-log]]
