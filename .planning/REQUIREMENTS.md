# Requirements: verify-kit

**Defined:** 2026-05-17
**Scope:** v0.1 = Universal foundation + Backend (FastAPI) add-on + LLM add-on. v0.2+ = Web/Audio/Game add-ons.
**Core Value:** A solo developer drops verify-kit into a new project, answers a handful of prompts, and ends up with a project where `just verify` is the ground truth for BOTH the human (pretty terminal + clickable IDE errors) AND the coding agent (MCP server + JSON output + `fix_propose` self-healing) — neither audience obscured.

## Dual-Audience Checklist (gates every feature)

Every requirement implementation must answer all six rows. If any cell is blank, the feature is incomplete.

| # | Audience question | Required answer |
|---|---|---|
| 1 | Human in terminal sees | Pretty colorized output via isatty; spinner; failed checks summarized with one-line next-action hint |
| 2 | Human in VS Code sees | SARIF in Problems panel, JUnit in Testing sidebar — no agent involvement required |
| 3 | Agent calling programmatically gets | Deterministic JSON with stable schema (introspectable via `describe`), error envelope `{code, message, hint, fix_command, docs_url}`, semantic exit codes |
| 4 | Agent has a fix path | Failed check returns `fix_command`; `fix_propose` MCP tool returns unified diff with rationale; agent can re-verify without human round-trip |
| 5 | Human can override agent | Every fix is `--dry-run`-able; destructive MCP tools annotated `destructiveHint: true`; Stop-hook escape hatch (`VERIFY_KIT_SKIP=1`); audit log in `.verify-kit/audit.jsonl` |
| 6 | Both can collaborate mid-flow | Same `verify-kit trace --last` works for both; state file-backed in `.verify-kit/` so human can `cat` while agent runs |

---

## v0.1 Requirements

### Template Foundation (TMPL)

- [ ] **TMPL-01**: User can run `copier copy gh:m2moiz/verify-kit my-project` and get a scaffolded project in <10s with no errors
- [ ] **TMPL-02**: Copier prompts ask for project name, description, author, license, devcontainer toggle, agent-tool toggles (`has_claude_code`, `has_cursor`, `has_windsurf`, etc.), and add-on toggles (`has_backend`, `has_llm` for v0.1; `has_web`, `has_audio`, `has_game` reserved for v0.2)
- [ ] **TMPL-03**: User can run `copier update` in a previously-scaffolded project and pull template improvements via three-way merge with conflict markers surfaced inline
- [ ] **TMPL-04**: Template is SemVer-tagged on git; consumers pin via `--vcs-ref vX.Y.Z`; `.copier-answers.yml` records the exact ref
- [ ] **TMPL-05**: Generated project has correct `.gitignore`, README scaffold, LICENSE file, AGENTS.md, and is committable on first run

### Toolchain & Task Runner (TOOL)

- [ ] **TOOL-01**: Generated project has `.mise.toml` declaring Python (3.13+) and Node (24+) versions with reproducible-install semantics
- [ ] **TOOL-02**: Generated project has `justfile` with canonical targets: `verify`, `verify --quick`, `verify --full`, `verify --check=<id>`, `verify --only=<csv>`, `verify --skip=<csv>`, `verify --fix`, `verify --watch`, `smoke`, `eval`, `refresh-cassettes`, `mutation`, `lint`, `format`, `test-unit`, `test-int`, `test-e2e`, `trace-up`, `trace-down`, `trace`, `shell`
- [ ] **TOOL-03**: Generated project has `Makefile` shim so `make verify` aliases to `just verify` for users without `just` installed
- [ ] **TOOL-04**: `just --list` shows discoverable, well-documented commands
- [ ] **TOOL-05**: `just verify` runs in <2s on a freshly-scaffolded empty project, <500ms on cache-hit re-runs (file-hash keyed)
- [ ] **TOOL-06**: `--check` is the default behavior; `--fix` is opt-in and prompts before auto-mutation

### CI / GitHub Actions (CI)

- [ ] **CI-01**: Generated project has `.github/workflows/ci.yml` (≤15 lines) that installs `mise`, runs `just verify`, reports status
- [ ] **CI-02**: Generated project has `.github/workflows/deploy-smoke.yml` for post-deploy `just smoke [url]` go/no-go
- [ ] **CI-03**: All workflows runnable locally via `act` without changes
- [ ] **CI-04**: CI workflows include caching for `mise`, `uv`, `pnpm`, `pre-commit` to keep PR feedback under 3 minutes
- [ ] **CI-05**: Generated project has `.github/workflows/nightly-eval.yml` for cost-capped live LLM evals (only when `has_llm=true`)

### Devcontainer & Local Dev (DEV)

- [ ] **DEV-01**: Generated project has optional `.devcontainer/devcontainer.json` (Copier-toggleable, NOT default) with `mise` Feature preinstalled
- [ ] **DEV-02**: Generated project has `.pre-commit-config.yaml` running only fast checks (ruff, biome/prettier, gitleaks, end-of-file-fixer, trailing-whitespace) — anything >3s lives in CI only
- [ ] **DEV-03**: Generated project has `.editorconfig`, `.gitattributes` (line endings, language detection, binary markers)

### Claude Code Integration (CLAUDE)

- [ ] **CLAUDE-01**: Generated project has `.claude/hooks/post-tool-use.sh` running lint + typecheck after every Edit/Write
- [ ] **CLAUDE-02**: Generated project has `.claude/hooks/stop.sh` running `just verify --quick` before allowing Claude to declare "done", with `stop_hook_active` recursion guard
- [ ] **CLAUDE-03**: Generated project has `scripts/ralph.sh` — Ralph loop wrapper with hard iteration cap + cost ceiling
- [ ] **CLAUDE-04**: Generated project has `CLAUDE.md` scaffold (thin pointer to AGENTS.md plus Claude-specific conventions)
- [ ] **CLAUDE-05**: Generated project has `.claude/settings.json.example` with `allow` list for read-only `verify-kit *` commands and `ask` for `verify-kit fix`

### Universal Harness Layer (HARN)

- [ ] **HARN-01**: Generated project has Python `harness/` package installable via `uv pip install -e .`
- [ ] **HARN-02**: `harness/verify.py` aggregates exit codes from all subsystem checks into both (a) miette-style pretty terminal render and (b) `.verify/report.json` + `.verify/report.junit.xml` + `.verify/report.sarif`
- [ ] **HARN-03**: `harness/debug_endpoints.py` exposes a FastAPI router for `/__debug/state` and `/__debug/events`, env-gated to `ENV=dev` (404 in prod) — only generated when `has_backend=true`
- [ ] **HARN-04**: `harness/trace_id.py` provides ASGI middleware threading a request_id through every request, log, and provider call (via `asgi-correlation-id`)
- [ ] **HARN-05**: `harness/logging.py` configures structlog with Rich pretty-renderer when TTY, JSON renderer when piped or `LOG_FORMAT=json`; honors `LOG_LEVEL`, `NO_COLOR`, `CI` env vars
- [ ] **HARN-06**: `harness/ralph.py` wraps the Ralph loop pattern: iterate while verify fails, hard cap iterations (default 5), track cumulative cost, surface "stuck — escalating to human" state
- [ ] **HARN-07**: Generated project has `tests/` scaffold: `smoke/`, `golden/` (snapshot fixtures), `properties/` (one Hypothesis example), `fixtures/`
- [ ] **HARN-08**: File-hash-keyed cache at `.verify/cache.db` (SQLite); `just verify` skips checks whose inputs haven't changed; `--no-cache` bypass

### MCP Server (MCP)

- [ ] **MCP-01**: `verify-kit mcp serve` starts a `fastmcp`-based MCP server (stdio transport default, optional `--http :7878`)
- [ ] **MCP-02**: MCP server exposes 13 tools, each with a CLI twin returning identical JSON: `verify`, `verify_check`, `list_checks`, `smoke`, `trace_last`, `debug_state`, `debug_events`, `eval_run`, `eval_compare`, `ralph_run`, `ralph_status`, `fix_propose`, `describe`
- [ ] **MCP-03**: Every MCP tool carries annotations: `readOnlyHint`, `destructiveHint`, `idempotentHint` so IDEs/agents can decide auto-approval
- [ ] **MCP-04**: Generated project includes per-agent MCP config snippets behind Copier prompts: `.cursor/mcp.json`, `.continue/mcpServers/verify-kit.json`, `.zed/settings.json` (`context_servers`), Claude `.claude/settings.json`
- [ ] **MCP-05**: MCP server supports auth via `--token=<value>` for HTTP transport; stdio transport is implicitly trusted

### Agent Conventions (AGT)

- [ ] **AGT-01**: Generated project has `AGENTS.md` at repo root (cross-tool standard read by Cursor/Codex/Copilot/Jules/Aider/Zed/JetBrains/Claude) — build/test/lint commands, code style, security notes
- [ ] **AGT-02**: Optional `CLAUDE.md`, `.cursor/rules/verify-kit.mdc` (alwaysApply ≤200 words), `.windsurf/rules/verify-kit.md`, `.github/copilot-instructions.md` generated when corresponding Copier prompts are true; each is a thin pointer to AGENTS.md plus tool-specific supplements
- [ ] **AGT-03**: Generated project includes `.claude/skills/verify-kit-{verify,debug,eval}/SKILL.md` skills (lazy-loaded per Claude's description-matching)

### Format Contracts (FMT)

- [ ] **FMT-01**: Every command supports `--format={pretty,json,jsonl,sarif,junit,otlp}` — pretty default when TTY, structured when piped or `--format` set; `NO_COLOR` and `CI` env vars respected
- [ ] **FMT-02**: Every error in non-pretty mode follows envelope `{code: string, message: string, hint?: string, fix_command?: string, docs_url?: string}`
- [ ] **FMT-03**: Exit codes are semantic: `0` ok, `1` check-failed, `2` bad-input, `10+` infra/system error
- [ ] **FMT-04**: `verify-kit describe [<command>]` emits JSON Schema of all commands, inputs, outputs, exit codes — agents introspect at runtime
- [ ] **FMT-05**: `verify-kit list-checks` enumerates all available checks with `{id, name, severity, category, description, fixable}` — agents enumerate without running

### IDE Integration (IDE)

- [ ] **IDE-01**: Generated project ships `.vscode/extensions.json` recommending Ruff, Pyright, Python, debugpy, Biome, Vitest, EditorConfig, Just, even-better-toml, vscode-yaml
- [ ] **IDE-02**: Generated project ships `.vscode/settings.json` (project needs only — formatOnSave, rulers, default formatters per language, pytest enablement, file/search excludes — no personal prefs)
- [ ] **IDE-03**: Generated project ships `.vscode/tasks.json` with `verify` as default build (`Ctrl+Shift+B`), tasks delegating to `just`, custom problem matchers for Ruff/Pyright/tsc/Biome so errors are clickable in Problems panel
- [ ] **IDE-04**: Generated project ships `.vscode/launch.json` with debugpy "current pytest", FastAPI uvicorn (when has_backend), and compound configs
- [ ] **IDE-05**: README documents JetBrains/Zed/Neovim equivalent setup (LSP/DAP-first tools work everywhere — no per-IDE config needed beyond the .vscode files)

### Observability (OBS)

- [ ] **OBS-01**: OpenTelemetry SDK installed but inert by default (no exporter configured until `OTEL_EXPORTER_OTLP_ENDPOINT` is set); zero perf cost when off
- [ ] **OBS-02**: `just trace-up` brings up Jaeger all-in-one Docker container at `localhost:16686` with one command; `just trace-down` tears down
- [ ] **OBS-03**: `just trace --last` renders the most recent trace as a terminal waterfall with latency-breakdown bars (same data Jaeger UI shows, readable without leaving terminal)
- [ ] **OBS-04**: Browser/frontend SDK (deferred to web add-on in v0.2; in v0.1, scaffolded but not wired) injects W3C `traceparent` header for end-to-end frontend→backend correlation
- [ ] **OBS-05**: README documents the `docker-compose.observability.yml` pattern and the otel-desktop-viewer / otel-tui alternatives for non-Docker users

### UX Polish (UX)

- [ ] **UX-01**: Errors follow miette/rustc format: header with error code → file:line + source snippet with caret → fix suggestion → docs link → repro command
- [ ] **UX-02**: Did-you-mean suggestions (Levenshtein-1) for misspelled check names, config keys, CLI flags
- [ ] **UX-03**: One config file (`verify-kit.yaml` or `[tool.verify-kit]` in `pyproject.toml`); no dotfile sprawl
- [ ] **UX-04**: On success, output suggests ONE next step (e.g. "All checks passed. Try `just verify --watch` or edit verify-kit.yaml to add a check.")
- [ ] **UX-05**: Generated project is plain and readable — no opaque runner, no obfuscated config; user can delete any check by removing 2 lines
- [ ] **UX-06**: Works offline (no telemetry, no phone-home, no login required for `just verify`); fails gracefully when an optional tool isn't installed ("ruff not found — install with `pip install ruff` or skip with `--skip ruff`")
- [ ] **UX-07**: Spinner only when work >500ms; auto-disabled on `!isatty(stdout)` or `CI=1`
- [ ] **UX-08**: First-run UX passes the 30-second test: from `copier copy` to "I see my project verified" in under 30s on a clean machine with mise+just preinstalled

### LLM Add-on (LLM) — opt-in via `has_llm=true`

- [ ] **LLM-01**: Opt-in via Copier prompt `has_llm: bool` — generates only when enabled; toggling off produces zero LLM artifacts
- [ ] **LLM-02**: Ships `pydantic-ai` as primary agent/typed-call framework; one-line provider swap between Anthropic/OpenAI/Gemini/Groq via model string
- [ ] **LLM-03**: Ships `instructor` for the "one LLM call → Pydantic model" case (no agent loop)
- [ ] **LLM-04**: Ships `litellm` as provider abstraction layer with built-in cache + retries + fallbacks (SQLite cache default)
- [ ] **LLM-05**: Ships `tokencost` + `tokenx` for cost awareness; provides `@cost_budget(usd=0.02, on_exceed="raise")` decorator
- [ ] **LLM-06**: Ships `autoevals` (Braintrust OSS) — pytest-native scorers for factuality/relevance/safety, usable standalone
- [ ] **LLM-07**: Ships `vcrpy` + `pytest-recording` with `before_record_request` filter that scrubs `authorization` and `x-api-key` headers
- [ ] **LLM-08**: Ships `opentelemetry-instrumentation-httpx` so every LLM call gets an OTel span automatically with `gen_ai.*` semantic attributes
- [ ] **LLM-09**: Provides `@llm_call(name="...")` decorator that emits OTel span with prompt/response/cost/latency/retry-count as attributes; Langfuse picks them up via OTel
- [ ] **LLM-10**: Copier prompt `llm_backend: langfuse-cloud | langfuse-self-host | none`; self-host generates `docker-compose.langfuse.yml`; cloud generates `.env.example` with `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY` slots
- [ ] **LLM-11**: Ships `promptfoo.config.yaml` wired to `eval/datasets/golden.jsonl`; `just eval` runs Promptfoo; `nightly-eval.yml` GitHub Action runs Promptfoo with `EVAL_BUDGET_USD` cost cap
- [ ] **LLM-12**: README documents Cloud Hobby → Hetzner CX32 self-host migration path with concrete steps and backup strategy

### Backend (FastAPI) Add-on (API) — opt-in via `has_backend=true`

- [x] **API-01**: Opt-in via Copier prompt `has_backend: bool` — generates only when enabled; toggling off produces zero FastAPI artifacts
- [ ] **API-02**: Ships `fastapi[standard]` baseline — gets `fastapi-cli`, `httpx`, `python-multipart`, `jinja2`; scaffolded `app/main.py` with `/healthz` and `/__debug/*` mounted
- [ ] **API-03**: Ships `pydantic-settings` for env config; `.env.example` documents every var with type and default
- [ ] **API-04**: Ships `sqlalchemy[asyncio]` + `asyncpg` + `alembic` async DB stack with one example model + migration (opt-out via `has_db=false`)
- [ ] **API-05**: Ships `asgi-correlation-id` middleware threading `X-Request-ID` through every request, log line, and outbound HTTP call
- [ ] **API-06**: Ships `structlog` ASGI middleware emitting JSON access logs keyed by `request_id` (Rich pretty in TTY, JSON when piped — same contract as HARN-05)
- [ ] **API-07**: Ships `sse-starlette` for streaming responses (default pattern for AI/LLM routes)
- [ ] **API-08**: Ships `secure` middleware setting OWASP-recommended response headers (CSP, X-Frame-Options, Referrer-Policy, Permissions-Policy) with prod/dev profile
- [ ] **API-09**: Ships `typer` CLI sibling at `app/cli.py` sharing Pydantic models with the FastAPI app (one schema, two interfaces)
- [ ] **API-10**: Ships `pyinstrument` middleware enabling `?profile=true` query param → returns rendered flamegraph HTML (dev-only, env-gated)
- [ ] **API-11**: Ships `anyio` + `httpx` + `asgi-lifespan` canonical async test setup; example `tests/test_app.py` exercises lifespan + one route
- [ ] **API-12**: Ships `schemathesis` wired into `just verify` — fuzzes the live OpenAPI schema for 5xx, schema violations, auth bypasses
- [ ] **API-13**: Ships `dirty-equals` + `polyfactory` for ergonomic test assertions and fixture factories
- [ ] **API-14**: Ships `Testcontainers` Postgres fixture (`@pytest.fixture` returning a containerized DB) for integration tests; cached image
- [ ] **API-15**: Opt-in `has_logfire=true` Copier prompt — installs `logfire` (Pydantic-team OTel) which auto-traces every Anthropic/OpenAI/httpx call with token counts; composes with LLM add-on
- [ ] **API-16**: Opt-in `has_fastapi_mcp=true` Copier prompt — installs `fastapi-mcp` and adds 3-line mount turning the FastAPI app into its own MCP server (every route becomes an MCP tool)
- [ ] **API-17**: Generated project ships `Dockerfile` (multi-stage: `uv` build + slim runtime), `docker-compose.yml` (api + postgres + jaeger), and `.dockerignore` — `just docker-up` brings up the full local stack
- [ ] **API-18**: `just verify` Backend slice runs: schema validation → schemathesis fuzz → smoke (`/healthz`, `/__debug/state`) → integration tests with Testcontainers
- [ ] **API-19**: README documents the canonical FastAPI layout (`app/{main,api,services,models,settings}.py`, `tests/`, `alembic/`) and explains where to add new routes/services without breaking conventions

### Documentation & Validation (DOC)

- [ ] **DOC-01**: Repo has README with: philosophy (why this exists), Quickstart (`copier copy ...`), add-on inventory, update path, troubleshooting, contributing, dual-audience checklist explained
- [ ] **DOC-02**: Repo has CHANGELOG with strict SemVer and "breaking changes for consumers" callout per release
- [ ] **DOC-03**: Repo has CONTRIBUTING.md documenting the smoke-test loop (every PR triggers a scratch consumer run)
- [ ] **DOC-04**: Repo has its own CI workflow that, on every PR, runs `copier copy` onto a scratch dir and confirms `just verify` exits 0 there — regression in the template fails the PR
- [ ] **DOC-05**: Repo has architecture diagram showing the layered design (Universal foundation + add-on slots)

## v2 Requirements (deferred to v0.2+)

### Web Add-on (WEB)

- **WEB-01..12**: Next.js 16 + React 19 + Turbopack scaffold, Biome (vs ESLint), Tailwind v4 + shadcn/ui, Vitest 4 browser mode, @testing-library/react, Playwright + axe, MSW, TanStack Query + nuqs, Zustand, react-hook-form + Zod, Sonner, @vercel/otel, `window.__VERIFY_KIT__` dev global, agent-browser smoke scripts, Argos visual regression (opt-in)

### Audio Add-on (AUD)

- **AUD-01..07**: ffprobe + librosa utilities, Whisper round-trip + jiwer WER, Chromium fake-audio flags Playwright config, Common Voice fixture loader, spectrogram-to-PNG, optional GPT-4o-audio rubric judge

### Game Add-on (GAME)

- **GAME-01..06**: Godot 4 + gdUnit4 + `gdUnit4-action` (xvfb), `window.__game.getState/simulate/advance` JavaScriptBridge, deterministic replay tied to `_physics_process` with seeded RNG, PlayGodot for desktop dev

### Advanced (ADV)

- **ADV-01**: Mutation testing wired into `just mutation` (mutmut for Python, Stryker for TS)
- **ADV-02**: Stagehand add-on for agentic UI exploration beyond scripted smoke
- **ADV-03**: Multi-tenant Langfuse hardening (RBAC across collaborators)
- **ADV-04**: Plop sub-component generators inside generated projects
- **ADV-05**: Go and Rust language add-ons

## Out of Scope (permanent)

| Feature | Reason |
|---------|--------|
| Multi-CI provider support (GitLab/CircleCI/Jenkins) | Premature; ~68% OSS is on GitHub; `act` covers local; thin-wrapper makes future migration trivial |
| Helicone proxy mode | Coupling not worth it across heterogeneous providers |
| Phoenix as primary LLM observability | Weaker multi-project isolation than Langfuse |
| Per-project SQLite logs | "You'll build a worse Langfuse over six months" |
| Earthly | Discontinued July 2025 |
| Dagger | Overkill for solo scale |
| Cookiecutter+Cruft | Copier obsoletes the combo |
| Single-binary Go/Rust harness CLI | Loses extensibility |
| Yeoman | Declining |
| Backstage scaffolder | Enterprise overkill |
| BAML / DSPy / Marvin / Mirascope / Outlines defaults | Too opinionated / too lock-in-heavy; document only |
| Auth/accounts in template | Each consumer handles auth |
| Web UI for the harness itself | CLI-only |
| Real-time observability dashboards beyond Langfuse | Premature for solo |

## Traceability

Mapped to roadmap phases on 2026-05-18. 95/95 v0.1 requirements covered, no orphans, no duplicates.

| Requirement | Phase | Status |
|-------------|-------|--------|
| TMPL-01 | Phase 1 | Pending |
| TMPL-02 | Phase 1 | Pending |
| TMPL-03 | Phase 1 | Pending |
| TMPL-04 | Phase 1 | Pending |
| TMPL-05 | Phase 1 | Pending |
| TOOL-01 | Phase 1 | Pending |
| TOOL-02 | Phase 1 | Pending |
| TOOL-03 | Phase 1 | Pending |
| TOOL-04 | Phase 1 | Pending |
| TOOL-05 | Phase 2 | Pending |
| TOOL-06 | Phase 1 | Pending |
| CI-01 | Phase 1 | Pending |
| CI-02 | Phase 1 | Pending |
| CI-03 | Phase 1 | Pending |
| CI-04 | Phase 1 | Pending |
| CI-05 | Phase 5 | Pending |
| DEV-01 | Phase 1 | Pending |
| DEV-02 | Phase 1 | Pending |
| DEV-03 | Phase 1 | Pending |
| CLAUDE-01 | Phase 3 | Pending |
| CLAUDE-02 | Phase 3 | Pending |
| CLAUDE-03 | Phase 3 | Pending |
| CLAUDE-04 | Phase 3 | Pending |
| CLAUDE-05 | Phase 3 | Pending |
| HARN-01 | Phase 2 | Pending |
| HARN-02 | Phase 2 | Pending |
| HARN-03 | Phase 4 | Pending |
| HARN-04 | Phase 2 | Pending |
| HARN-05 | Phase 2 | Pending |
| HARN-06 | Phase 4 | Pending |
| HARN-07 | Phase 2 | Pending |
| HARN-08 | Phase 2 | Pending |
| MCP-01 | Phase 3 | Pending |
| MCP-02 | Phase 3 | Pending |
| MCP-03 | Phase 3 | Pending |
| MCP-04 | Phase 3 | Pending |
| MCP-05 | Phase 3 | Pending |
| AGT-01 | Phase 1 | Pending |
| AGT-02 | Phase 3 | Pending |
| AGT-03 | Phase 3 | Pending |
| FMT-01 | Phase 2 | Pending |
| FMT-02 | Phase 2 | Pending |
| FMT-03 | Phase 2 | Pending |
| FMT-04 | Phase 2 | Pending |
| FMT-05 | Phase 2 | Pending |
| IDE-01 | Phase 3 | Pending |
| IDE-02 | Phase 3 | Pending |
| IDE-03 | Phase 3 | Pending |
| IDE-04 | Phase 3 | Pending |
| IDE-05 | Phase 3 | Pending |
| OBS-01 | Phase 2 | Pending |
| OBS-02 | Phase 2 | Pending |
| OBS-03 | Phase 2 | Pending |
| OBS-04 | Phase 2 | Pending |
| OBS-05 | Phase 2 | Pending |
| UX-01 | Phase 2 | Pending |
| UX-02 | Phase 2 | Pending |
| UX-03 | Phase 2 | Pending |
| UX-04 | Phase 2 | Pending |
| UX-05 | Phase 2 | Pending |
| UX-06 | Phase 2 | Pending |
| UX-07 | Phase 2 | Pending |
| UX-08 | Phase 2 | Pending |
| LLM-01 | Phase 5 | Pending |
| LLM-02 | Phase 5 | Pending |
| LLM-03 | Phase 5 | Pending |
| LLM-04 | Phase 5 | Pending |
| LLM-05 | Phase 5 | Pending |
| LLM-06 | Phase 5 | Pending |
| LLM-07 | Phase 5 | Pending |
| LLM-08 | Phase 5 | Pending |
| LLM-09 | Phase 5 | Pending |
| LLM-10 | Phase 5 | Pending |
| LLM-11 | Phase 5 | Pending |
| LLM-12 | Phase 5 | Pending |
| API-01 | Phase 4 | Complete |
| API-02 | Phase 4 | Pending |
| API-03 | Phase 4 | Pending |
| API-04 | Phase 4 | Pending |
| API-05 | Phase 4 | Pending |
| API-06 | Phase 4 | Pending |
| API-07 | Phase 4 | Pending |
| API-08 | Phase 4 | Pending |
| API-09 | Phase 4 | Pending |
| API-10 | Phase 4 | Pending |
| API-11 | Phase 4 | Pending |
| API-12 | Phase 4 | Pending |
| API-13 | Phase 4 | Pending |
| API-14 | Phase 4 | Pending |
| API-15 | Phase 4 | Pending |
| API-16 | Phase 4 | Pending |
| API-17 | Phase 4 | Pending |
| API-18 | Phase 4 | Pending |
| API-19 | Phase 4 | Pending |
| DOC-01 | Phase 6 | Pending |
| DOC-02 | Phase 6 | Pending |
| DOC-03 | Phase 6 | Pending |
| DOC-04 | Phase 6 | Pending |
| DOC-05 | Phase 6 | Pending |

---
*Requirements defined: 2026-05-17*
*Last updated: 2026-05-18 — Traceability section populated by gsd-roadmapper for v0.1 (6 phases, 95/95 mapped).*
