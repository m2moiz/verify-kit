---
title: Stack Decisions
aliases: [Stack, Tools, Decisions, Stack Summary]
tags: [verify-kit, stack, decisions, synthesis]
created: 2026-05-17
status: locked-for-v0.1
---

# 📦 Stack Decisions

> [!abstract] Every tool, with verdict
> 5 research waves × 4 agents each = 20 reports. Tools are categorized as **ALWAYS SHIP** (installed by default in scaffolded projects), **OPT-IN** (gated by Copier prompt), or **REJECTED** (researched, deliberately not used). Rationale included.

## Universal Foundation — ALWAYS SHIP

### Template + orchestration
| Tool | Role | Why |
|---|---|---|
| [[tools/copier\|Copier]] | Template engine | Only scaffolder with native `copier update` + 3-way merge for downstream updates |
| [[tools/mise\|mise]] | Toolchain + task runner | Single `.mise.toml` declares versions AND tasks; solves bootstrap + orchestration |
| [[tools/just\|just]] | Canonical task runner | Cleanest syntax, `just --list` discoverability, recipes can be any language |
| Makefile shim | `make verify` → `just $@` | Users without `just` still work |

### Logging + observability
| Tool | Role | Why |
|---|---|---|
| structlog | Python structured logging | Pretty in TTY (Rich renderer), JSON when piped |
| Rich | Python TUI library | Best-in-class colors, tables, live progress |
| Pino + pino-pretty | Node logging | Fastest; dual rendering pattern |
| consola | Node CLI logging | Auto-detects CI vs TTY |
| asgi-correlation-id | FastAPI middleware | Request IDs in every log line — cheapest observability win |
| trace_id middleware | Cross-component correlation | Universal thread |

### Agent integration
| Tool | Role | Why |
|---|---|---|
| **AGENTS.md** | Cross-tool agent rules file | Linux Foundation standard, 60k+ repos, read by Cursor/Codex/Aider/Copilot/Jules/Zed/JetBrains/Claude |
| **MCP server (fastmcp)** | 13 tools exposed to any MCP client | Universal tool-protocol (Nov 2025 spec stable) |
| Claude Code hooks | PostToolUse + Stop | Blocks "done" claims until `just verify` exits 0 |

### Format contracts
| Format | Use | Standard |
|---|---|---|
| `--format=pretty` (TTY default) | Human terminal | isatty discipline |
| `--format=json` / `--format=jsonl` | Agent consumption | Universal |
| `--format=sarif` | VS Code Problems panel | OASIS standard |
| `--format=junit` | CI test runners | Universal |
| `--format=otlp` | OTel collector | CNCF |

### IDE integration
| File | Role |
|---|---|
| `.vscode/extensions.json` | Recommended extensions on workspace open |
| `.vscode/settings.json` | Project-only (no personal prefs) |
| `.vscode/tasks.json` | `just verify` as default build (`Ctrl+Shift+B`); custom problem matchers for Ruff/Pyright/Biome |
| `.vscode/launch.json` | debugpy + Node + compound configs |
| `.editorconfig`, `.gitattributes`, `.pre-commit-config.yaml` | Editor-agnostic |

### OpenTelemetry (installed but inert)
| Tool | Role |
|---|---|
| OpenLLMetry SDK | OTel `gen_ai.*` semantic conventions |
| `just trace-up` | Brings up Jaeger all-in-one Docker container |
| `just trace --last` | Terminal waterfall render |

---

## Backend Add-on

> [!info] v0.1, ALWAYS SHIP when `has_backend=true`

12 libs installed by default:
1. `fastapi[standard]` — gets `fastapi-cli`, `httpx`, `python-multipart`, jinja2
2. `pydantic-settings` — env config without footguns
3. `sqlalchemy[asyncio]` + `asyncpg` + `alembic` — modern async DB stack
4. `asgi-correlation-id` — request IDs everywhere
5. `structlog` — JSON access logs keyed by request_id
6. `sse-starlette` — streaming responses for AI routes
7. `secure` — OWASP headers in one middleware
8. `typer` — CLI sibling sharing Pydantic models
9. `pyinstrument` — flamegraph on `?profile=true` (dev-only)
10. `anyio` + `httpx` + `asgi-lifespan` — canonical async test setup
11. `schemathesis` — fuzz the live OpenAPI in `just verify`
12. `dirty-equals` + `polyfactory` + `pytest-recording` — fixture & assertion ergonomics

**Opt-in via Copier flag:**
- `--observability=logfire` — Pydantic-team OTel; auto-traces Anthropic/OpenAI with token counts (massive win for AI projects)
- `--mcp` — `fastapi-mcp` mounts FastAPI as MCP server in 3 lines (turns backend into agent tooling)
- `--queue=arq` — async Redis queue scaffold
- `--scheduler=apscheduler` — in-process AsyncIO scheduler
- `--auth=fastapi-users|authlib` — only when explicitly asked
- `--rate-limit` — `slowapi`
- `--cache` — `fastapi-cache2` + Redis
- `--docs=scalar` — Scalar at `/scalar` (modern OpenAPI UI)
- `--server=granian` — Rust-based ASGI server

---

## LLM Add-on

> [!info] v0.1, ALWAYS SHIP when `has_llm=true`

7 libs installed by default:
1. **`pydantic-ai`** — typed agent framework, one-line provider swap, built-in OTel (2026 breakout)
2. **`instructor`** — one-call typed responses (no agent loop case)
3. **`litellm`** — provider abstraction + retries + fallbacks + SQLite cache
4. **`tokencost`** + **`tokenx`** — USD-per-call + `@cost_budget(usd=0.02)` decorator
5. **`autoevals`** (Braintrust OSS) — pytest factuality/relevance scorers, no Braintrust account needed
6. **`vcrpy`** + **`pytest-recording`** — record/replay LLM calls; `before_record_request` filter for header scrubbing
7. **`opentelemetry-instrumentation-httpx`** — auto OTel spans for every LLM call

**Opt-in via Copier flag:**
- `--promptfoo` — declarative YAML eval in CI (Node binary)
- `--deepeval` — pytest-native scorers + Confident AI dashboard
- `--pipecat` — only when building voice agents

**LLM observability backend** (via `llm_backend` Copier prompt):
- `langfuse-cloud` — free Cloud Hobby tier (50k events/mo)
- `langfuse-self-host` — generates `docker-compose.langfuse.yml`
- `none` — no observability backend wired

---

## Web Add-on (v0.2, ALWAYS SHIP when `has_web=true`)

12 libs:
1. Next.js 16 + React 19 + Turbopack (default bundler in 16)
2. TypeScript + **Biome** (10–25× faster than ESLint+Prettier; Next 15.5 ships official support)
3. **Tailwind v4** + shadcn/ui + Radix
4. **Vitest 4 browser mode** (stable Oct 2025) + vitest-browser-react
5. @testing-library/react + userEvent
6. Playwright + @axe-core/playwright
7. **MSW** (Mock Service Worker — network-level mocking in browser + Vitest + Node)
8. TanStack Query v5 + devtools
9. Zustand + **nuqs** (URL state — agent drives UI by URL alone)
10. react-hook-form + Zod
11. Sonner + @uidotdev/usehooks
12. @vercel/otel + Sentry SDK

**Scaffold drops:** `instrumentation.ts` (OTel), root-layout `<ErrorBoundary>` + `onUncaughtError` wired to **`window.__VERIFY_KIT__`** dev global, MSW `mocks/handlers.ts`.

**Opt-in:** Storybook 9, Argos visual regression, Lighthouse CI, Vercel AI SDK, openapi-typescript codegen, React Scan, PostHog.

---

## Game Add-on (v0.2, ALWAYS SHIP when `has_game=true`)

- **gdUnit4** + `gdUnit4-action` GitHub workflow (with `xvfb-run` for input-driven tests)
- **JavaScriptBridge** exposing `window.__game.getState()`, `__game.simulate(action)`, `__game.advance(frames)` via Godot
- Deterministic replay tied to `_physics_process` with seeded RNG
- README section on **PlayGodot** for desktop dev loop

---

## Audio Add-on (v0.2, ALWAYS SHIP when `has_audio=true`)

- `ffprobe` + `librosa` — duration/RMS/silence/sample-rate checks
- **Whisper round-trip** + `jiwer` — TTS → STT → WER assertion
- **Chromium fake-audio flags** Playwright config: `--use-file-for-fake-audio-capture=fixture.wav%noloop`
- Common Voice fixture loader
- Spectrogram-to-PNG (Claude can `Read` waveforms)
- Optional `harness/audio/rubric_judge.py` calling GPT-4o-audio or Gemini 2.5

---

## Multi-agent coordination tools (separate from generated projects)

- ✅ **claude-squad** (`cs`) — tmux + worktree per agent; supports Claude + Codex + OpenCode + Aider
- ✅ **codex** CLI v0.130 — headless via `codex exec`
- ✅ **claude** CLI v2.1.143 — headless via `claude -p`
- ✅ **GSD for Codex** — installed globally; Codex can run `/gsd:execute-phase`
- ✅ **just**, **mise**, **fswatch**, **jq**, **tmux**, **gh**, **uv** — all required tools present
- Configured: `workflow.plan_review_convergence=true`, `review.default_reviewers=["codex"]`

**Alternative orchestrators (researched, not installed):**
- **dux** (Patrick D'Appollonio) — TUI wrapping claude/codex/gemini in worktrees
- **oh-my-hermes** — Claude+Codex specific with `omh handoff` commands
- **relay** — MCP server attached to both CLIs, state in `~/.relay/channels/`

---

## Explicitly rejected

> [!warning] Researched, deliberately not used
> Tools below were evaluated and rejected with concrete reasons. Don't re-litigate without new evidence.


| Tool/Pattern | Why rejected |
|---|---|
| **Helicone proxy mode** | Coupling not worth it across heterogeneous providers (fal, Pioneer, Tavily); self-host stack is heavier than Langfuse for the same outcome |
| **Phoenix as primary LLM observability** | Weaker multi-project isolation than Langfuse (tag-and-filter vs separate creds) |
| **Per-project SQLite logs** (no central backend) | "You'll build a worse Langfuse over six months" |
| **Earthly** (CI portability) | Discontinued July 2025; company pivoted to "Earthly Lunar" AI guardrails |
| **Dagger** (CI portability) | Overkill at solo scale; learning curve doesn't pay back |
| **Cookiecutter + Cruft** | Copier obsoletes the combo (native `copier update` + 3-way merge) |
| **Yeoman** | Declining; ecosystem largely abandoned for new work |
| **Backstage scaffolder** | Enterprise overkill; requires running Backstage |
| **Single-binary Go/Rust harness CLI** | Loses extensibility; contributors can't add a check in 10 lines without rebuilding |
| **BAML** (LLM DSL) | High lock-in; non-Python files; recommend for multi-language teams only |
| **DSPy** (Stanford) | Very high lock-in; opaque compiled prompts; only valuable with labeled eval set |
| **Marvin** | Now thin wrapper over pydantic-ai |
| **Outlines** | Only matters for self-hosted models |
| **Mirascope** | Good but pydantic-ai supersedes |
| **LangGraph / CrewAI** | Recommend only when pydantic-ai insufficient |
| **Cypress** | Playwright won the E2E war |
| **HighlightIO** | Dead post-LaunchDarkly acquisition (March 2025) |
| **tRPC** | Wrong for FastAPI backends; use openapi-typescript |
| **Million Lint (paid)** | React Scan is the free competitor |
| **fastapi-debug-toolbar** | Unmaintained + HTML-only (useless for JSON APIs and agents) |
| **prometheus-fastapi-instrumentator** | Overkill for solo; OTel via Logfire covers same ground |
| **Celery / dramatiq / faststream** | Wrong shape for solo async; arq is the right pick |
| **fastapi-users** | In maintenance mode (security updates only) |
| **assistant-ui** | Original maintainers stepped back May 2025 |
| **Roo Code** | Shut down May 15, 2026 |
| **Multi-CI provider support** (GitLab/CircleCI/Jenkins) | Premature; ~68% of OSS is on GitHub; `act` covers local |
| **Peer-to-peer agent messaging** | Infinite loops + cost explosions; filesystem is the bus |
| **`--dangerously-bypass-approvals-and-sandbox`** outside container | The $50k Claude Code recursion incident vector |

## Related notes

- [[00-architecture-overview]] — complete picture
- [[00-autonomous-workflow]] — Claude+Codex setup
- [[00-decision-log]] — chronological decision history
- Each card in the `tools/` subdirectory covers install + usage + caveats for one tool
