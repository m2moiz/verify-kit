# Roadmap: verify-kit v0.1 — Foundation + Backend + LLM

**Milestone:** v0.1
**Created:** 2026-05-18
**Granularity:** coarse
**Scope:** Universal foundation + Backend (FastAPI) add-on + LLM add-on
**Trust anchor:** every phase ends with `copier copy gh:m2moiz/verify-kit /tmp/scratch-<phase>` producing a project where the phase's slice of `just verify` exits 0.

## Phases

- [ ] **Phase 1: Template Skeleton & Toolchain** — Copier engine, mise/just/Makefile shim, devcontainer toggle, base CI, AGENTS.md, editor-agnostic conventions
- [ ] **Phase 2: Universal Harness Core** — Python `harness/` package: verify aggregator, structlog/Rich logging, trace_id middleware, cache, format contracts, miette errors, UX polish, OTel scaffold
- [ ] **Phase 3: Agent Integration & IDE** — MCP server (13 tools + CLI twins), Claude Code hooks + skills, per-agent rules files (CLAUDE/cursor/windsurf/copilot), per-agent MCP snippets, .vscode files with problem matchers
- [x] **Phase 4: Backend (FastAPI) Add-on** — opt-in `has_backend=true`: 12 default libs + opt-in `has_logfire`/`has_fastapi_mcp`, Dockerfile + docker-compose, `/__debug/*` wired, schemathesis fuzz in verify, Testcontainers integration tests (completed 2026-05-21)
- [ ] **Phase 5: LLM Add-on** — opt-in `has_llm=true`: pydantic-ai + instructor + litellm + tokencost + autoevals + vcrpy, `@llm_call` / `@cost_budget` decorators, Langfuse Cloud/self-host options, Promptfoo + nightly-eval workflow
- [ ] **Phase 6: Template Self-Test & Documentation** — repo's own CI runs `copier copy` onto scratch dir per add-on matrix and asserts `just verify` exits 0; README + CHANGELOG (SemVer with consumer-breaking-changes callout) + CONTRIBUTING + architecture diagram + dual-audience checklist enforcement

## Phase Details

### Phase 1: Template Skeleton & Toolchain

**Goal**: A bare `copier copy` of the template produces a committable, mise+just-ready project skeleton that boots in under 10 seconds and has the cross-tool agent rules file in place.
**Depends on**: Nothing (foundation)
**Requirements**: TMPL-01, TMPL-02, TMPL-03, TMPL-04, TMPL-05, TOOL-01, TOOL-02, TOOL-03, TOOL-04, TOOL-06, CI-01, CI-02, CI-03, CI-04, DEV-01, DEV-02, DEV-03, AGT-01
**Success Criteria** (what must be TRUE):

  1. Running `copier copy <local-template-path> /tmp/scratch-p1` completes in <10s with no errors and produces a project that `git init && git add -A && git commit` accepts cleanly.
  2. The generated project has `.mise.toml` (Python 3.13+, Node 24+), a `justfile` exposing the canonical target names (even as stubs), a `Makefile` one-line shim aliasing `make verify` → `just verify`, and `just --list` renders documented targets.
  3. Running `copier update` against an older `.copier-answers.yml` in the scaffolded project pulls template improvements via three-way merge (verified with a deliberate template diff and a previously-scaffolded scratch dir).
  4. `act -j ci` runs the generated project's `.github/workflows/ci.yml` to completion locally without changes.
  5. `AGENTS.md`, `.editorconfig`, `.gitattributes`, `.pre-commit-config.yaml` (fast checks only) are present in the scaffolded project; devcontainer is present only when the Copier prompt selects it.

**Plans**: 4 plans

  - [ ] 01-01-PLAN.md — Copier engine + template/ repo layout (TMPL-01..05)
  - [ ] 01-02-PLAN.md — Toolchain spine: mise + just + Makefile + harness/ skeleton (TOOL-01..04, TOOL-06)
  - [ ] 01-03-PLAN.md — DX conventions: editorconfig, gitattributes, pre-commit, optional devcontainer, env-detection extension (DEV-01..03)
  - [ ] 01-04-PLAN.md — CI workflows + AGENTS.md canonical + thin per-agent pointers (CI-01..04, AGT-01)

### Phase 2: Universal Harness Core

**Goal**: A scaffolded project has a working `harness/` Python package such that `just verify --quick` aggregates real subsystem checks, emits miette-style errors plus machine-readable JSON/JUnit/SARIF, and honors the isatty + `--format=*` + exit-code contract across every command.
**Depends on**: Phase 1
**Requirements**: HARN-01, HARN-02, HARN-04, HARN-05, HARN-07, HARN-08, TOOL-05, FMT-01, FMT-02, FMT-03, FMT-04, FMT-05, UX-01, UX-02, UX-03, UX-04, UX-05, UX-06, UX-07, UX-08, OBS-01, OBS-02, OBS-03, OBS-05
**Success Criteria** (what must be TRUE):

  1. In a fresh scratch project, `uv pip install -e harness/` succeeds and `just verify --quick` exits 0 in <2s on first run and <500ms on cache hit (`.verify/cache.db` file-hash keyed).
  2. Forcing a check failure produces a miette/rustc-style terminal render (code → file:line + snippet → fix suggestion → docs URL → repro command) AND writes `.verify/report.json`, `.verify/report.junit.xml`, `.verify/report.sarif` whose contents agree with the terminal output.
  3. Piping `verify-kit verify --format=json` to a file yields envelope-conformant errors (`{code, message, hint?, fix_command?, docs_url?}`) and semantic exit codes (0/1/2/10+); `--format=pretty` is the TTY default and `NO_COLOR=1` / `CI=1` disable color and spinners.
  4. `verify-kit describe` and `verify-kit list-checks` emit stable JSON Schema / check catalogs; misspelling a check name (`--check=lnit`) returns a did-you-mean suggestion for `lint`.
  5. `just trace-up` starts Jaeger all-in-one on `localhost:16686`; `just trace --last` renders a terminal waterfall for the most recent trace; OTel SDK is inert (zero exporter cost) until `OTEL_EXPORTER_OTLP_ENDPOINT` is set.

**Plans**: 7 plans

  - [ ] 02-01-PLAN.md — Models + registry + did-you-mean + trace_id contextvar (FMT-02, FMT-03, FMT-05, UX-02, HARN-04)
  - [ ] 02-02-PLAN.md — Lazy OTel observability + structlog three-way renderer (OBS-01, HARN-05)
  - [ ] 02-03-PLAN.md — SQLite WAL cache + [tool.verify-kit] config loader (HARN-08, UX-03, UX-06, TOOL-05)
  - [ ] 02-04-PLAN.md — Phase-1 checks migration + lint/format checks + span-wrapping runner (HARN-01, UX-06)
  - [ ] 02-05-PLAN.md — Six report emitters (pretty/json/jsonl/junit/sarif/otlp) + spinner (HARN-02, FMT-01, UX-01, UX-07)
  - [ ] 02-06-PLAN.md — CLI rewrite (verify/list-checks/describe/trace) + Jaeger client + justfile recipes (FMT-04, FMT-05, UX-04, UX-05, OBS-02, OBS-03)
  - [ ] 02-07-PLAN.md — Test scaffold + non-functional gate tests + OBS-05 README (HARN-07, TOOL-05, UX-08, OBS-01, OBS-05)

### Phase 3: Agent Integration & IDE

**Goal**: Both coding agents (Claude/Cursor/Continue/Zed/Codex/Copilot via MCP + AGENTS.md supplements) and human developers in VS Code (clickable Problems panel, default build task) treat `verify-kit` as a first-class citizen — same data, different rendering.
**Depends on**: Phase 2 (MCP tools wrap harness functions; problem matchers consume harness SARIF)
**Requirements**: MCP-01, MCP-02, MCP-03, MCP-04, MCP-05, CLAUDE-01, CLAUDE-02, CLAUDE-03, CLAUDE-04, CLAUDE-05, AGT-02, AGT-03, IDE-01, IDE-02, IDE-03, IDE-04, IDE-05
**Success Criteria** (what must be TRUE):

  1. `verify-kit mcp serve` starts a fastmcp stdio server (and `--http :7878 --token=<x>` HTTP variant) exposing exactly the 13 named tools (`verify`, `verify_check`, `list_checks`, `smoke`, `trace_last`, `debug_state`, `debug_events`, `eval_run`, `eval_compare`, `ralph_run`, `ralph_status`, `fix_propose`, `describe`); each MCP tool returns byte-identical JSON to its CLI twin and carries `readOnlyHint`/`destructiveHint`/`idempotentHint` annotations.
  2. In a scaffolded project, editing a file in Claude Code triggers `.claude/hooks/post-tool-use.sh` (lint + typecheck) and attempting to declare "done" triggers `.claude/hooks/stop.sh` running `just verify --quick` with a working `stop_hook_active` recursion guard; setting `VERIFY_KIT_SKIP=1` bypasses the gate.
  3. Opening the scaffolded project in VS Code prompts the recommended extensions (`.vscode/extensions.json`), `Ctrl+Shift+B` runs `just verify` as the default build, and a deliberately-introduced Ruff/Pyright/tsc/Biome error appears as a clickable entry in the Problems panel via the custom problem matchers in `tasks.json`.
  4. Per-agent rules + MCP snippets land conditionally on Copier prompts: `CLAUDE.md`, `.cursor/rules/verify-kit.mdc` (alwaysApply, ≤200 words), `.windsurf/rules/verify-kit.md`, `.github/copilot-instructions.md`, `.cursor/mcp.json`, `.continue/mcpServers/verify-kit.json`, `.zed/settings.json`, `.claude/settings.json.example`, `.claude/skills/verify-kit-{verify,debug,eval}/SKILL.md`.
  5. `scripts/ralph.sh` (and the `ralph_run`/`ralph_status` MCP tools backed by `harness/ralph.py`) honors hard iteration cap (default 5) and cumulative USD cost ceiling, surfacing a "stuck — escalating to human" state when exceeded.

**Plans**: TBD

### Phase 4: Backend (FastAPI) Add-on

**Goal**: When a consumer answers `has_backend=true`, the scaffolded project has a runnable FastAPI app with the full 12-lib baseline (plus opt-in `has_logfire` / `has_fastapi_mcp`) and `just verify` extends to include schemathesis fuzz + Testcontainers integration tests against a Postgres container.
**Depends on**: Phase 2 (HARN-03 `/__debug/*` router needs a FastAPI host); Phase 3 (problem matchers + MCP tools predate add-on slot)
**Requirements**: API-01, API-02, API-03, API-04, API-05, API-06, API-07, API-08, API-09, API-10, API-11, API-12, API-13, API-14, API-15, API-16, API-17, API-18, API-19, HARN-03, HARN-06
**Success Criteria** (what must be TRUE):

  1. `copier copy --data has_backend=true ...` produces an `app/` tree (`main`, `api`, `services`, `models`, `settings`, `cli`) where `just docker-up` brings up api + postgres + jaeger and `curl localhost:8000/healthz` returns 200; `has_backend=false` produces zero FastAPI files.
  2. The generated app exposes `/__debug/state` and `/__debug/events` in `ENV=dev` and returns 404 in `ENV=prod`; every request, log line, and outbound httpx call carries the same `X-Request-ID` via `asgi-correlation-id` + structlog ASGI middleware (Rich-pretty in TTY, JSON when piped — same contract as HARN-05).
  3. `just verify` (Backend slice) runs schema validation → schemathesis fuzz against the live OpenAPI → smoke (`/healthz`, `/__debug/state`) → integration tests using a Testcontainers Postgres fixture, and exits 0 on a clean scaffold.
  4. Toggling `has_logfire=true` auto-traces Anthropic/OpenAI/httpx calls with token counts (verified by running the LLM add-on combined and seeing spans in Logfire); toggling `has_fastapi_mcp=true` adds a working 3-line mount turning every FastAPI route into an MCP tool callable from a `claude mcp` client.
  5. Generated project ships `Dockerfile` (multi-stage `uv` build + slim runtime), `docker-compose.yml` (api + postgres + jaeger), `.dockerignore`, `pyinstrument` middleware enabling `?profile=true` (dev-only), `secure` middleware setting OWASP headers, and a typer CLI sibling at `app/cli.py` sharing Pydantic models with the FastAPI app.

**Plans**: TBD

### Phase 5: LLM Add-on

**Goal**: When a consumer answers `has_llm=true`, the scaffolded project has the 7-lib LLM baseline with `@llm_call` / `@cost_budget` decorators emitting OTel `gen_ai.*` spans, a chosen Langfuse backend (Cloud/self-host/none), and a Promptfoo eval gate runnable from `just eval` plus cost-capped nightly CI.
**Depends on**: Phase 2 (OTel scaffold + format contracts); composes with Phase 4 when both add-ons selected
**Requirements**: LLM-01, LLM-02, LLM-03, LLM-04, LLM-05, LLM-06, LLM-07, LLM-08, LLM-09, LLM-10, LLM-11, LLM-12, CI-05
**Success Criteria** (what must be TRUE):

  1. `copier copy --data has_llm=true ...` installs the 11-package LLM baseline via uv: `pydantic-ai`, `instructor`, `litellm`, `tokencost`, `autoevals`, `opentelemetry-instrumentation-httpx`, `traceloop-sdk`, `claude-agent-sdk`, `langfuse` (runtime) + `vcrpy`, `pytest-recording` (dev). `has_llm=false` produces zero LLM artifacts and zero new dependencies. (D-22: tokenx-core dropped during 05-01 execution after slopcheck flagged it SUS (81 downloads) and we recognized redundancy with verify-kit's own `@llm_call` decorator.)
  2. Wrapping a function with `@llm_call(name="x")` emits an OTel span with prompt/response/cost/latency/retry-count attributes and `gen_ai.*` semantic conventions; wrapping it with `@cost_budget(usd=0.02, on_exceed="raise")` raises a typed exception once the cumulative cost crosses the threshold.
  3. The Copier `llm_backend` prompt produces the correct artifacts: `langfuse-cloud` writes `.env.example` with `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` slots, `langfuse-self-host` writes `docker-compose.langfuse.yml`, `none` writes neither — and in all three cases a recorded LLM call shows up in Langfuse when env vars are populated.
  4. `just refresh-cassettes` re-records vcrpy fixtures with `authorization` and `x-api-key` headers scrubbed by `before_record_request`; subsequent test runs work fully offline against the cassettes.
  5. `just eval` runs Promptfoo against `eval/datasets/golden.jsonl` and the `nightly-eval.yml` GitHub Action runs the same with an `EVAL_BUDGET_USD` cost cap, refusing to start if the cap would be exceeded.

**Plans**: 5 plans

  - [x] 05-01-PLAN.md — Copier path-gating + pyproject deps + .env.example LLM credentials (LLM-01, LLM-10)
  - [ ] 05-02-PLAN.md — harness/llm.py: @llm_call, @cost_budget, claude-agent-sdk routing adapter + Traceloop.init wiring (LLM-02, LLM-04, LLM-05, LLM-08, LLM-09)
  - [ ] 05-03-PLAN.md — vcr conftest + tests/llm suite + optional eval check via @register (LLM-03, LLM-06, LLM-07)
  - [x] 05-04-PLAN.md — Promptfoo config + golden.jsonl + justfile recipes + nightly-eval.yml + docker-compose.langfuse.yml (LLM-10, LLM-11, CI-05)
  - [ ] 05-05-PLAN.md — POST /summarize composition + SKILL.md + README LLM-12 + 12-cell polarity test (LLM-12)

### Phase 6: Template Self-Test & Documentation

**Goal**: The template verifies itself: every PR to the template runs `copier copy` across the add-on matrix on a scratch dir and asserts `just verify` exits 0; the repo ships a README/CHANGELOG/CONTRIBUTING/architecture-diagram that explains the philosophy, quickstart, add-on inventory, update path, and dual-audience checklist with consumer-breaking-changes callouts per release.
**Depends on**: Phases 1–5 (self-test exercises everything prior)
**Requirements**: DOC-01, DOC-02, DOC-03, DOC-04, DOC-05
**Success Criteria** (what must be TRUE):

  1. The repo's own `.github/workflows/template-selftest.yml` runs `copier copy` onto a scratch dir for each meaningful matrix entry (`base`, `+backend`, `+llm`, `+backend+llm`, `+backend+llm+logfire+fastapi_mcp`) and fails the PR if `just verify` in any matrix entry exits non-zero.
  2. The repo README documents (a) philosophy / why-this-exists, (b) one-command quickstart, (c) add-on inventory with Copier prompt names, (d) `copier update` path, (e) troubleshooting, (f) the dual-audience six-row checklist with examples — and a new reader can go from `copier copy` to "I see my project verified" in under 30 seconds on a clean machine with mise+just preinstalled (UX-08).
  3. `CHANGELOG.md` uses strict SemVer and every release entry has an explicit "Breaking changes for consumers" callout (even if empty); `CONTRIBUTING.md` documents the smoke-test loop and how to add a new check in 10 lines.
  4. Repo ships an architecture diagram (Mermaid or PNG) showing the Universal Foundation + four add-on slots layered model, matching `research/00-architecture-overview.md`.
  5. The template-selftest workflow runs end-to-end in `act` locally and finishes in under 10 minutes for the full matrix, gating every PR before merge.

**Plans**: TBD

## Dependencies

| Phase | Depends on | Why |
|-------|------------|-----|
| 1 | — | Foundation; nothing precedes the template engine itself |
| 2 | 1 | Harness package needs the Copier+just scaffolding to live inside |
| 3 | 2 | MCP tools and IDE problem matchers wrap harness outputs |
| 4 | 2, 3 | `/__debug/*` router (HARN-03) needs a FastAPI host; problem matchers + MCP snippets predate the slot |
| 5 | 2 | OTel scaffold + format contracts must exist before `@llm_call` emits spans; composes with 4 when both selected |
| 6 | 1, 2, 3, 4, 5 | Self-test exercises every prior phase across the add-on matrix |

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Template Skeleton & Toolchain | 0/0 | Not started | — |
| 2. Universal Harness Core | 0/0 | Not started | — |
| 3. Agent Integration & IDE | 0/0 | Not started | — |
| 4. Backend (FastAPI) Add-on | 0/0 | Not started | — |
| 5. LLM Add-on | 0/0 | Not started | — |
| 6. Template Self-Test & Documentation | 0/0 | Not started | — |

## Coverage

- v0.1 requirements mapped: **95 / 95** (100%)
- Categories: TMPL (5), TOOL (6), CI (5), DEV (3), CLAUDE (5), HARN (8), MCP (5), AGT (3), FMT (5), IDE (5), OBS (5), UX (8), LLM (12), API (19), DOC (5)
- Orphans: none
- Duplicates: none
- v2 requirements (WEB, AUD, GAME, ADV) intentionally excluded — deferred to v0.2+

## Notes / Trade-offs

- **Bundled IDE config into Phase 3** rather than its own phase: only 5 IDE-* requirements and they are conceptually agent-adjacent (the same `tasks.json` problem matchers that make errors clickable for humans also make SARIF reachable for the MCP `fix_propose` tool).
- **Bundled UX/FMT/OBS into Phase 2**: they are all behaviors of the harness package itself; splitting them would create a phase with no concrete artifacts.
- **CI-05 (nightly-eval.yml) is in Phase 5**, not Phase 1, because it is LLM-add-on-conditional; CI-01..04 stay in Phase 1 as the baseline.
- **HARN-03 (`/__debug/*` router) is in Phase 4**, not Phase 2: the router needs a FastAPI host, and shipping it in Phase 2 would force a backend dependency on the universal layer.
- **Phase 6 is intentionally the verifier**: per D-020, Phase 1 runs supervised so the trust anchor exists; subsequent phases progressively autonomous; Phase 6 closes the loop by making verify-kit's own CI use verify-kit on itself.
- **Phase sizing**: each phase targets 0.5–1.5 days of Codex execution (~10–30 atomic commits). Phase 4 (API, 19 requirements) is the largest and may merit a mid-phase checkpoint; Phase 1 and Phase 3 are mid-sized; Phases 5 and 6 are smaller and faster.

---
*Created: 2026-05-18 by gsd-roadmapper for milestone v0.1.*
