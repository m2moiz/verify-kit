---
title: verify-kit Architecture Overview
aliases: [Architecture, Big Picture, Complete Picture]
tags: [verify-kit, architecture, synthesis, moc]
created: 2026-05-17
status: locked-for-v0.1
---

# 🏛️ verify-kit Architecture Overview

> [!abstract] In one paragraph
> verify-kit is a Copier-based scaffold template that drops a self-verifiable agentic-coding harness into any new project. It serves human developers (pretty terminal output, clickable VS Code errors, miette-style error messages) AND coding agents (MCP server, structured JSON/JSONL/SARIF, error envelope with `fix_command`) as equal first-class citizens — neither obscured. The trust anchor is `just verify`: one command that returns 0 only when every check passes.

## The four-layer model

```
┌─ Layer 0 — Universal Foundation ────────────────────────────────┐
│ Copier template · mise toolchain · just verify · Makefile shim   │
│ Rich+structlog (Python) · Pino+pretty (Node) · consola (CLI)     │
│ /__debug/state + /__debug/events · trace_id middleware           │
│ Claude hooks (PostToolUse + Stop) · Ralph loop wrapper           │
│ AGENTS.md (cross-tool) + opt-in CLAUDE.md / .cursor/rules        │
│ verify-kit MCP server (stdio + optional HTTP)                    │
│ --format={pretty,json,jsonl,sarif,junit,otlp} on every command   │
│ describe + list-checks + error envelope + exit code contract     │
│ 4 .vscode files + 5 editor-agnostic conventions                  │
│ OpenTelemetry installed but inert · just trace-up → Jaeger       │
│ miette-style errors · did-you-mean · cache-by-hash · UX polish   │
└──────────────────────────────────────────────────────────────────┘
                                │
       ┌────────────┬───────────┼──────────────┬────────────────┐
       │            │           │              │                │
   ┌───▼───┐   ┌────▼────┐  ┌───▼────┐    ┌────▼────┐      ┌────▼─────┐
   │ Web   │   │  Game   │  │ Audio  │    │  LLM    │      │ Backend  │
   │ v0.2  │   │  v0.2   │  │  v0.2  │    │  v0.1   │      │  v0.1    │
   └───────┘   └─────────┘  └────────┘    └─────────┘      └──────────┘
```

**v0.1 ships:** Universal Foundation + Backend add-on + LLM add-on.
**v0.2 ships:** Web + Audio + Game add-ons (parallel development since they share no deps).

## Dual-audience checklist

> [!info] Gates every feature
> Every requirement must answer all six rows. If any cell is blank, the feature is incomplete.


Every requirement in [`.planning/REQUIREMENTS.md`](../.planning/REQUIREMENTS.md) must answer all six rows. If any cell is blank, the feature is incomplete.

| # | Audience question | Required answer |
|---|---|---|
| 1 | **Human in terminal sees** | Pretty colorized output via isatty; spinner; failed checks summarized with one-line next-action hint |
| 2 | **Human in VS Code sees** | SARIF in Problems panel, JUnit in Testing sidebar — no agent involvement required |
| 3 | **Agent calling programmatically gets** | Deterministic JSON with stable schema (introspectable via `describe`), error envelope `{code, message, hint, fix_command, docs_url}`, semantic exit codes |
| 4 | **Agent has a fix path** | Failed check returns `fix_command`; `fix_propose` MCP tool returns unified diff with rationale; agent can re-verify without human round-trip |
| 5 | **Human can override agent** | Every fix is `--dry-run`-able; destructive MCP tools annotated `destructiveHint: true`; Stop-hook escape hatch (`VERIFY_KIT_SKIP=1`); audit log in `.verify-kit/audit.jsonl` |
| 6 | **Both can collaborate mid-flow** | Same `verify-kit trace --last` works for both; state file-backed in `.verify-kit/` so human can `cat` while agent runs |

## Key conceptual moves

> [!example] Same data, different rendering
> Emit structured events once via structlog/slog/tracing. Render pretty terminal in dev, JSON when piped, OTLP spans to backend. Audience changes, source of truth doesn't.

> [!example] Open protocols, not bespoke ones
> LSP/DAP for IDE features, OTLP for traces, W3C `traceparent` for browser↔backend correlation, MCP for agent tools. verify-kit's job is to wire these protocols up — never invent new ones.

> [!example] isatty discipline
> Pretty for humans when stdout is a TTY. Structured when piped or `--format` set. `gh`, `rg`, `bat`, `cargo`, `kubectl` all do this. Never make humans pass `--pretty`; never make agents pass `--no-color --plain --quiet`.

> [!example] miette/rustc-style errors
> Every error includes: header with code → file:line + source snippet → fix suggestion → docs link → repro command. Same format readable by humans AND parseable by agents.

## Trust anchor

> [!important] `just verify` is THE invocation

```
just verify          → lint + typecheck + unit + integration + smoke (local) + secret-scan
just verify --quick  → skip slow tiers (used by pre-commit + Claude PostToolUse hook)
just verify --full   → also runs nightly-only live LLM evals
just smoke [url]     → <30s post-deploy go/no-go; 5-10 critical flows
just eval            → nightly: live golden-dataset eval against real APIs, cost-capped
just refresh-cassettes → weekly: re-record vcrpy fixtures against live providers
just mutation        → on-demand: Stryker/mutmut quality audit
just trace-up        → docker run jaegertracing/all-in-one
just trace --last    → render most recent trace as terminal waterfall
```

`make verify` aliases to `just verify` via a one-line Makefile shim for users without `just`.

## File layout of a verify-kit-scaffolded project

```
my-project/
├── .mise.toml                   # toolchain versions + task aliases
├── justfile                     # canonical task runner
├── Makefile                     # 1-line shim → just $@
├── verify-kit.yaml              # ONE config file (no dotfile sprawl)
├── pyproject.toml | package.json # standard manifests
├── .gitignore .editorconfig .gitattributes
├── .pre-commit-config.yaml      # fast checks only
├── .github/workflows/
│   ├── ci.yml                   # ~10 lines: just verify
│   ├── nightly-eval.yml         # live LLM evals (when has_llm)
│   └── deploy-smoke.yml         # post-deploy go/no-go
├── .vscode/
│   ├── extensions.json          # recommended extensions
│   ├── settings.json            # project-only settings
│   ├── tasks.json               # tasks delegate to just; problem matchers
│   └── launch.json              # debug configs
├── .devcontainer/               # OPTIONAL (Copier prompt)
│   └── devcontainer.json
├── .claude/
│   ├── hooks/
│   │   ├── post-tool-use.sh     # lint + typecheck after every Edit/Write
│   │   ├── stop.sh              # just verify --quick before Claude says "done"
│   │   └── codex-review.sh      # Cross-AI review (optional)
│   ├── skills/                  # verify-kit-verify, -debug, -eval
│   └── settings.json.example    # permissions for verify-kit commands
├── AGENTS.md                    # cross-tool rules (Cursor/Codex/Aider/...)
├── CLAUDE.md                    # OPTIONAL pointer to AGENTS.md
├── .cursor/rules/verify-kit.mdc # OPTIONAL agent rules
├── harness/                     # Python helper package
│   ├── verify.py                # aggregator → .verify/report.{json,junit.xml,sarif}
│   ├── debug_endpoints.py       # /__debug/* FastAPI router
│   ├── trace_id.py              # ASGI middleware (asgi-correlation-id)
│   ├── logging.py               # Rich+structlog config
│   ├── ralph.py                 # autonomous loop wrapper
│   └── mcp_server.py            # 13-tool MCP server (fastmcp)
├── scripts/
│   ├── ralph.sh                 # autonomous overnight loop
│   └── overnight.sh             # full Claude+Codex autonomous run
├── tests/
│   ├── smoke/                   # agent-browser scripts
│   ├── golden/                  # snapshot fixtures
│   ├── properties/              # one Hypothesis example
│   └── fixtures/
├── .agents/                     # multi-agent coordination
│   ├── SPEC.md                  # user writes
│   ├── PLAN.md                  # Claude writes
│   ├── TASKS.md                 # checkbox checklist (message bus)
│   ├── VERIFY.sh                # deterministic gate
│   ├── JUDGE_PROMPT.md          # LLM judge instructions
│   ├── PHASE-EXEC-NOTES.md      # Codex appends
│   └── events.ndjson            # append-only event log
└── docker-compose.observability.yml  # OPTIONAL: brings up Jaeger
```

## Layer-by-layer stack (decided)

### Universal Foundation (always ships)

| Concern | Tool | Why |
|---|---|---|
| Template engine | [[tools/copier]] | Only mainstream scaffolder with `copier update` + 3-way merge |
| Toolchain + tasks | [[tools/mise]] | Single `.mise.toml` declares versions AND tasks |
| Task runner | [[tools/just]] | Cleanest syntax, `just --list` discoverability |
| Helper package | Python `harness/` | uv-installable; Claude Code skills land easily |
| Logging | Rich + structlog (Py) / Pino + consola (JS) | Structured-by-default, pretty-by-context |
| MCP server | fastmcp (Python) | 13 tools, stdio default, CLI twin per tool |
| Agent rules | AGENTS.md + opt-in supplements | Cross-tool standard (Linux Foundation, 60k+ repos) |
| CI | GitHub Actions + `act` for local | ~68% of OSS lives on GitHub |
| Editor | LSP/DAP-first tools (Ruff, Pyright, Biome) | Native in every editor |
| Trace UI | Jaeger all-in-one (Docker) | One command, ~50MB RAM, classic waterfall |
| OTel SDK | OpenLLMetry / @vercel/otel | OTel `gen_ai.*` semantic conventions stable |

### Backend Add-on (v0.1, opt-in)

12 ship-by-default libs: `fastapi[standard]`, `pydantic-settings`, `sqlalchemy[asyncio]`+`asyncpg`+`alembic`, **`asgi-correlation-id`**, `structlog`, **`sse-starlette`**, `secure`, `typer`, **`pyinstrument`**, `anyio`+`httpx`+`asgi-lifespan`, **`schemathesis`**, `dirty-equals`+`polyfactory`+`pytest-recording`.

Opt-in: **`logfire`** (Pydantic-team OTel SaaS — auto-traces every Anthropic/OpenAI call with token counts), **`fastapi-mcp`** (3 lines turn FastAPI into MCP server).

### LLM Add-on (v0.1, opt-in)

7 ship-by-default libs: **`pydantic-ai`** (the 2026 breakout), **`instructor`** (one-call typed responses), **`litellm`** (provider abstraction), **`tokencost`+`tokenx`** (`@cost_budget` decorator), **`autoevals`** (Braintrust OSS — pytest factuality scorers), **`vcrpy`+`pytest-recording`** (offline-deterministic), **`opentelemetry-instrumentation-httpx`**.

Backend: Langfuse Cloud Hobby (free, 50k events/mo) → Hetzner CX32 self-host (~€7.60/mo) when outgrown.

## What v0.2 looks like

Same pattern, applied to the four remaining add-ons (Web/Audio/Game/Backend-extras). Since they share no dependencies, they can be developed in parallel.

| Add-on | Key tools |
|---|---|
| **Web** | Next.js 16+React 19+Turbopack, Biome, Tailwind v4+shadcn/ui, **Vitest 4 browser mode**, MSW, TanStack Query+**nuqs**, Zustand, `window.__VERIFY_KIT__` global, @vercel/otel, Sentry SDK |
| **Game** | gdUnit4 + `gdUnit4-action` (xvfb), `window.__game.getState/simulate/advance` via JavaScriptBridge, deterministic replay on `_physics_process`, PlayGodot for desktop |
| **Audio** | ffprobe+librosa, Whisper round-trip+jiwer, Chromium `--use-file-for-fake-audio-capture`, Common Voice fixtures, spectrogram-to-PNG, optional GPT-4o-audio judge |

## Related notes

- [[00-stack-decisions]] — all tools with status (ship/opt-in/reject)
- [[00-autonomous-workflow]] — Claude+Codex setup
- [[00-decision-log]] — key decisions with rationale
- [[wave-4-mcp-agent-integration]] — full MCP server spec (13 tools)
- [[wave-3-vscode-ide]] — full IDE integration spec
