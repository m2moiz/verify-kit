# Project Roadmap

**Project:** verify-kit
**Milestones covered:** v0.1 (Phases 1–6, SHIPPED 2026-05-24) · v0.2 (Phase 7, active)

> **⚠ NOTICE (2026-05-26):** Mid-revision pass on Phase 7 plans, this file was accidentally overwritten and reconstructed from STATE.md + read-cache. Phases 1-6 detail blocks restored 2026-05-26 from phase artifacts (CONTEXT, VERIFICATION/UAT, and PLAN frontmatter). The Phase 7 block (especially the 7 success criteria) is verified verbatim from the planner's read-cache; other sections are best-effort reconstruction. If you spot any discrepancy against pre-2026-05-26 history, restore from STATE.md derivations. The file is gitignored so no git history exists prior to today.

## Phases

### Phase 1: Template Skeleton & Toolchain ✅ SHIPPED 2026-05-18

**Goal**: A bare `copier copy gh:m2moiz/verify-kit my-project` produces a committable project skeleton with the mise+just+Makefile-shim toolchain wired up, AGENTS.md + per-agent rules files (CLAUDE.md / .cursor / .windsurf / copilot-instructions) conditionally rendered from Copier prompts, base GitHub Actions CI (lint + verify + deploy-smoke), and the `harness/` Python package skeleton ready for Phase 2 to fill in. From `copier copy` → working `git init && git add -A && git commit` in <10s.
**Depends on**: Nothing (foundation)
**Requirements**: TMPL-01..05, TOOL-01..04, TOOL-06, CI-01..04, DEV-01..03, AGT-01, CLAUDE-04
**Success Criteria** (what must be TRUE):

  1. `copier copy --defaults --trust ... /tmp/scratch-p1` renders the template in <10s wall time with all baseline files present (`.mise.toml`, `justfile`, `Makefile` shim, `pyproject.toml`, `AGENTS.md`); with `has_devcontainer=true`, `.devcontainer/devcontainer.json` is emitted.
  2. The generated project is immediately committable: `cd /tmp/scratch-p1 && git init && git add -A && git commit -m init` exits 0; `.gitignore` excludes Python/Node caches and env files.
  3. Inside the rendered project, `just --list` shows only working recipes with docstrings — no empty stubs (Area 3: working-only justfile contract).
  4. After `uv sync`, `just verify` runs the harness CLI and reports 3/3 Phase-1 checks passing (`mise.toml.valid`, `copier.answers.valid`, `just-list.renders`) with structured output and exit 0.
  5. Per-agent files render conditionally based on Copier env-detected toggles (`has_claude_code`, `has_cursor`, `has_windsurf`, `has_copilot`) via Form B Jinja-in-path gating (no `_skip_if` — empirically not a real Copier key); `copier update` against a git-backed sandbox template preserves user edits via three-way merge.

**Plans**: 4 plans

  - [x] 01-01-PLAN.md — Copier scaffold base: `copier.yml`, `template/.gitignore`, README/LICENSE, render test (TMPL-01..05)
  - [x] 01-02-PLAN.md — Toolchain spine: `.mise.toml`, `justfile`, `Makefile` shim, `harness/` package skeleton, `pyproject.toml` (PEP 621), `verify-kit` console script (TOOL-01..04, TOOL-06)
  - [x] 01-03-PLAN.md — Dev conventions: `.editorconfig`, `.gitattributes`, `.pre-commit-config.yaml`, optional `.devcontainer/`, `template_extensions/env_detect.py` Jinja extension (DEV-01..03)
  - [x] 01-04-PLAN.md — CI + per-agent files: `ci.yml`, `deploy-smoke.yml`, `AGENTS.md`, conditionally-rendered CLAUDE.md / .cursor / .windsurf / copilot-instructions (CI-01..04, AGT-01, CLAUDE-04)

### Phase 2: Universal Harness Core ✅ SHIPPED 2026-05-18

**Goal**: The Phase 1 `harness/` skeleton becomes a real plugin architecture — a `@register` check registry, a runner with cache-warm/cold paths, multiple report emitters (pretty/json/jsonl/junit/sarif/otlp), a file-hash-keyed SQLite cache, miette-style error envelopes, structured logging via structlog, and an inert-by-default OpenTelemetry scaffold. `just verify --quick` aggregates real subsystem checks and honors the isatty + `--format=*` + semantic exit-code contract across every command.
**Depends on**: Phase 1
**Requirements**: HARN-01, HARN-02, HARN-04..08, TOOL-05, FMT-01..05, UX-01..08, OBS-01..03, OBS-05
**Success Criteria** (what must be TRUE):

  1. `uv pip install -e .` succeeds in the rendered scratch project; `just verify --quick` exits 0 on first run and re-runs in <500ms on cache-hit (TOOL-05 cache budget HARD-gated by `test_cache_hit_under_500ms_internal_duration`).
  2. A forced failure produces a miette/rustc-style terminal render (`error[<code>]: <message>` + `--> file:line:col` + snippet + `hint:` + `fix:` + `docs:`) AND writes three disk artifacts atomically (`.verify/report.json`, `.verify/report.junit.xml`, `.verify/report.sarif`); `EXIT_WRITE_FAILED=12` supersedes `EXIT_CHECK_FAIL=1` on disk-write failure.
  3. `--format=json` output is `ErrorEnvelope`-conformant (`code/message/hint?/fix_command?/docs_url?/file?/line?/column?/snippet?`); semantic exit codes (EXIT_OK=0, EXIT_CHECK_FAIL=1, EXIT_BAD_INPUT=2, EXIT_CACHE_CORRUPT=10, EXIT_TOOL_MISSING=11, EXIT_WRITE_FAILED=12, EXIT_OTEL_UNREACHABLE=13) are wired; pretty is default on TTY, JSON when piped; `NO_COLOR` and `CI` disable color + spinners.
  4. `describe` and `list-checks --format=json` emit stable, schema-versioned JSON catalogs with no `fn` field leakage; misspelling a check ID or flag returns a did-you-mean suggestion via `difflib.get_close_matches` (cutoff 0.6) and exits 2.
  5. `just trace-up` brings up Jaeger all-in-one (1.76.0) on :16686; `just trace --last` renders a waterfall for the last verify run; the OTel scaffold is fully inert until `OTEL_EXPORTER_OTLP_ENDPOINT` is set (zero `opentelemetry.*` lines on `python -X importtime` when unset).

**Plans**: 7 plans

  - [x] 02-01-PLAN.md — Models + registry + did-you-mean + trace_id primitives (foundation for all later waves)
  - [x] 02-02-PLAN.md — Observability scaffold (inert OTel + structlog logging that switches on TTY/CI/LOG_FORMAT/NO_COLOR) (OBS-01, HARN-05)
  - [x] 02-03-PLAN.md — SQLite cache (WAL mode, STRICT table, file-hash key, LRU eviction) + `[tool.verify-kit]` config loader via tomllib (HARN-08, UX-03, UX-06, TOOL-05)
  - [x] 02-04-PLAN.md — Runner + initial check pack (mise, copier.answers, just-list, lint.ruff, lint.biome skip-if-unavailable, format.ruff, format.biome) (HARN-01, UX-06)
  - [x] 02-05-PLAN.md — Report emitters dict (pretty/json/jsonl/junit/sarif/otlp), all serializing the same `VerifyReport` pydantic model (HARN-02, FMT-01, UX-01, UX-07)
  - [x] 02-06-PLAN.md — Core facade + CLI wiring + Jaeger justfile recipes + cwd-contract guard + cache-eviction-order guard (HARN-01/02, FMT-01/03/04/05, UX-02/04/05, OBS-02/03)
  - [x] 02-07-PLAN.md — Test fixtures + golden snapshots + property tests + cache-budget HARD gate + first-run 30s gate + README harness section

### Phase 3: Agent Integration & IDE ✅ SHIPPED 2026-05-19

**Goal**: Both coding agents (Claude/Cursor/Continue/Zed/Codex/Copilot via MCP + AGENTS.md supplements) and human developers in VS Code treat `verify-kit` as a first-class citizen — same data, different rendering. Ships: a 13-tool fastmcp server with stdio default + HTTP bearer auth, Claude Code hooks (PostToolUse + Stop) with recursion guard and skip-env, three Claude skills, conditional per-agent rules files (≤200 words each) and MCP snippets for Cursor/Continue/Zed, a Ralph loop wrapper with iteration + cost caps, and `.vscode/` files with problem matchers wiring miette output into the Problems panel.
**Depends on**: Phase 2
**Requirements**: MCP-01..05, CLAUDE-01..05, AGT-02, AGT-03, IDE-01..05
**Success Criteria** (what must be TRUE):

  1. MCP server registers exactly 13 tools by canonical name (`verify`, `verify_check`, `list_checks`, `smoke`, `trace_last`, `describe`, `ralph_run`, `fix_propose`, `ralph_status`, `debug_state`, `debug_events`, `eval_run`, `eval_compare`), each with `ToolAnnotations(readOnlyHint/destructiveHint/idempotentHint)`; stdio is default, HTTP requires non-empty bearer token (401 on missing/wrong); `verify-kit mcp serve` subcommand wires the CLI.
  2. Claude Code hooks (`post-tool-use.sh` runs `just lint && just typecheck`; `stop.sh` runs `just verify --quick`) honor `stop_hook_active` recursion guard and `VERIFY_KIT_SKIP=1` bypass; Ralph returns the canonical shape `{status, iters, cost_usd, output_path[, reason]}` with `reason` only when stuck and `cost_cap` winning the tie-break under `(max_iters=1, cost_cap_usd=0.001)`.
  3. Per-agent rules files render conditionally on Copier prompts (`has_cursor`, `has_windsurf`, `has_copilot`, `has_continue`, `has_zed`) via Form B Jinja-in-path gating; each rules file is ≤200 words; MCP snippets ship for Cursor (`mcp.json`), Continue (`mcpServers/verify-kit.json`), and Zed (`settings.json` `context_servers`).
  4. CLI ↔ MCP byte-identical guarantee: `tests/test_mcp_cli_byte_identical.py` asserts the same Python entry point backs every MCP tool and its CLI twin; Ralph return shape forbids hallucinated keys (`iters_completed`, `stop_reason`, `converged`, `max_iters_hit`).
  5. `.vscode/` ships `extensions.json` (Ruff/Pyright/Biome/Vitest/Just/etc.), `settings.json`, `tasks.json`, `launch.json`, and a problem matcher that parses miette output into the Problems panel; integration smoke + REVIEW-CHECKLIST static scans verify Phase 3 contracts across the template-render matrix.

**Plans**: 5 plans

  - [x] 03-01-PLAN.md — MCP server core (fastmcp) + 13 tools + bearer auth + `verify-kit mcp serve` CLI (MCP-01/02/03/05)
  - [x] 03-02-PLAN.md — Claude Code hooks + settings.json.example + Ralph loop wrapper + CLAUDE.md scaffold (CLAUDE-01..05)
  - [x] 03-03-PLAN.md — Per-agent rules + MCP snippets + 3 Claude skills (verify/debug/eval) (AGT-02, AGT-03, MCP-04)
  - [x] 03-04-PLAN.md — VS Code integration: extensions, settings, tasks, launch, problem matchers (IDE-01..05)
  - [x] 03-05-PLAN.md — Integration smoke + REVIEW-CHECKLIST static scans + `check-plan-shapes.sh` script extension (MCP-01..03, CLAUDE-01/02, AGT-02/03, IDE-03)

### Phase 4: Backend (FastAPI) Add-on ✅ SHIPPED 2026-05-21

**Goal**: When a consumer answers `has_backend=true`, the scaffolded project gets a runnable FastAPI app under `app/` with a 12-default-lib baseline (fastapi[standard], structlog, asgi-correlation-id, sse-starlette, secure, pyinstrument, anyio, httpx, asgi-lifespan, plus typer for the CLI sibling) plus opt-in sub-flags `has_logfire` (auto-trace) and `has_fastapi_mcp` (3-line MCP mount). `/__debug/state` + `/__debug/events` are exposed only in `ENV=dev`; every request carries the same `X-Request-ID`. `just verify` extends to include schemathesis fuzz against the live OpenAPI plus Testcontainers-Postgres integration tests; a multi-stage `uv`-based Dockerfile + docker-compose (api + postgres + jaeger) ships for local stack-up.
**Depends on**: Phases 2, 3
**Requirements**: API-01..19, HARN-03, HARN-06
**Success Criteria** (what must be TRUE):

  1. `copier copy --data has_backend=true` produces the `app/` tree with all 6 modules (`main.py`, `api.py`, `services.py`, `models.py`, `settings.py`, `cli.py`); `just docker-up` brings up api+postgres+jaeger; `curl localhost:8000/healthz` returns 200; `has_backend=false` produces zero FastAPI files (polarity test enforced by two-guard path gating — top-level `{% if has_backend %}app{% endif %}` + filename-level `{% if has_db %}db.py{% endif %}` to avoid empty-segment leaks).
  2. `/__debug/state` and `/__debug/events` are exposed only when `ENV=dev` (404 in `ENV=prod`); LIFO-ordered middleware stack (CorrelationIdMiddleware with `validator=None`, structlog access log, secure OWASP headers, pyinstrument env-gated to dev) propagates `X-Request-ID` across all layers — verified by 3-way contract test.
  3. `just verify-backend` runs the full slice: schema validation → schemathesis fuzz against live OpenAPI on :8000 → smoke → Testcontainers-Postgres integration tests with `pg_container` session fixture; exits 0 on clean scaffold. (Initial UAT surfaced a testcontainers≥4.0 URL-prefix bug in the asyncpg replace pattern — patched in Phase 6's gap-closure sweep.)
  4. `has_logfire=true` auto-traces FastAPI + httpx via `logfire.configure()` + `LOGFIRE_TOKEN` guard; `has_fastapi_mcp=true` mounts a 3-line `FastApiMCP(app).mount()` after all `include_router` calls; the 4-cell opt-in polarity matrix verifies both sub-flags render correctly in all combinations.
  5. Dockerfile uses 2-stage `uv sync --no-install-project` build; docker-compose passes `docker compose config -q` for both `has_db` polarities; `app/cli.py` is a Typer CLI that imports from `app.models` so Pydantic types are shared with the FastAPI app; HARN-06 (Ralph host wiring inside FastAPI context) verified by `test_ralph_in_app_context.py`.

**Plans**: 7 plans

  - [x] 04-01-PLAN.md — Copier prompts + add-on path gating (`has_backend`/`has_db`/`has_logfire`/`has_fastapi_mcp`); two-guard shape contract (API-01)
  - [x] 04-02-PLAN.md — FastAPI app skeleton + settings + LIFO middleware stack + HARN-03 `/__debug/*` router host (API-02/03/05/06/07/08/10/11, HARN-03)
  - [x] 04-03-PLAN.md — Async SQLAlchemy + asyncpg + Alembic + Testcontainers `pg_container` fixture (API-04/13/14)
  - [x] 04-04-PLAN.md — Typer CLI sibling (`app/cli.py`) sharing Pydantic models with FastAPI + Ralph host wiring (API-09, HARN-06)
  - [x] 04-05-PLAN.md — Multi-stage `uv` Dockerfile + docker-compose (api+postgres+jaeger) + `just docker-up` (API-17)
  - [x] 04-06-PLAN.md — Opt-in sub-flags: `has_logfire` (auto-trace) + `has_fastapi_mcp` (3-line MCP mount); 4-cell polarity matrix (API-15, API-16)
  - [x] 04-07-PLAN.md — `just verify-backend` slice: schemathesis fuzz + smoke + integration + in-process fuzz fallback + README backend section (API-12, API-18, API-19)

### Phase 5: LLM Add-on ✅ SHIPPED 2026-05-22

**Goal**: When a consumer answers `has_llm=true`, the scaffolded project ships an opinionated 11-package LLM stack (pydantic-ai + instructor + litellm + tokencost + autoevals + opentelemetry-instrumentation-httpx + traceloop-sdk + claude-agent-sdk + langfuse, with vcrpy + pytest-recording in dev) plus `@llm_call` and `@cost_budget` decorators emitting OTel `gen_ai.*` spans, Langfuse-cloud / self-host / none backend wiring, a Promptfoo eval gate via `just eval`, and a weekly cost-capped `nightly-eval.yml` workflow. `has_llm=false` produces zero LLM artifacts and zero new dependencies.
**Depends on**: Phase 2
**Requirements**: LLM-01..12, CI-05
**Success Criteria** (what must be TRUE):

  1. `copier copy --data has_llm=true` cold-start: render → `uv sync --extra dev` exits 0 with all 11 LLM packages installed (pydantic-ai-slim 1.100, fastmcp 3.3.1, litellm 1.85.1, tokencost 0.1.26, autoevals 0.2.0, langfuse 4.6.1, traceloop-sdk 0.60.0, opentelemetry-instrumentation-httpx 0.62b1, vcrpy 8.1.1, pytest-recording 0.13.4 — no tokenx-core per D-22 slopcheck rejection); the 12-cell polarity matrix passes 16 forcing-functions across `(has_backend × has_llm × llm_backend)`.
  2. `@llm_call` emits an OTel span `llm.<name>` carrying the full `gen_ai.*` attribute set (`gen_ai.operation.name`, `gen_ai.request.model`, `gen_ai.response.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`) plus `verify_kit.cost_usd`, `verify_kit.latency_ms`, `verify_kit.routing_path`, `verify_kit.retry_count`; `@cost_budget` raises typed `CostBudgetExceeded(budget_usd, accumulated_usd, call_name)` with decorator stacking `@cost_budget OUTER + @llm_call INNER` producing correct ordering (budget check fires AFTER cost recorded).
  3. `call_llm()` is the single routing entry point: `USE_CLAUDE_CODE_SDK=1` OR `(no ANTHROPIC_API_KEY AND sdk importable)` → claude-agent-sdk path (cost_usd=0.0, routing_path=`claude-code-sdk`); else litellm path. Every verify-kit-shipped call site goes through `call_llm()`, NOT `pydantic_ai.Agent.run()` directly (pydantic-ai is shipped as the consumer-facing typed-call ergonomic layer, documented in README LLM-12).
  4. When `has_backend=true AND has_llm=true`, `POST /summarize` exists and calls `call_llm()`, returns `{summary, cost_usd, latency_ms}`; absent in the other 3 cells. `.env.example` lands at the correct path per (has_llm × has_backend) cell — at `app/.env.example` when backend, at root `.env.example` when LLM-only.
  5. `just eval` runs Promptfoo against `eval/datasets/golden.jsonl` (5-10 starter rows demonstrating factuality/relevance/safety/exact-match/regex-match scorers) and writes `.verify/eval-results.json`; `just refresh-cassettes` re-records vcrpy cassettes; `nightly-eval.yml` runs weekly Sunday 04:00 UTC (cron `0 4 * * 0`) with default `EVAL_BUDGET_USD=1.00` hard ceiling; `docker-compose.langfuse.yml` ships only when `llm_backend=self-host`.

**Plans**: 5 plans

  - [x] 05-01-PLAN.md — Copier prompts + dep block + `.env.example` cell routing; tokenx-core dropped per D-22 (LLM-01, LLM-10)
  - [x] 05-02-PLAN.md — `harness/llm.py`: `@llm_call`, `@cost_budget`, `call_llm()` routing entry point with claude-agent-sdk + litellm paths (LLM-02..05, LLM-08, LLM-09)
  - [x] 05-03-PLAN.md — Test infrastructure: vcrpy cassettes, conftest fixtures, autoevals smoke, skip-fixture contract, `harness/checks/eval.py` (LLM-03, LLM-06, LLM-07)
  - [x] 05-04-PLAN.md — Promptfoo config + golden.jsonl starter dataset + `just eval` / `just refresh-cassettes` + `nightly-eval.yml` weekly cron + `docker-compose.langfuse.yml` (LLM-10, LLM-11, CI-05)
  - [x] 05-05-PLAN.md — `POST /summarize` (Phase 4 × Phase 5 composition) + filled-in `verify-kit-eval` SKILL.md + README LLM-12 personal-vs-consumer setup section (LLM-12)

### Phase 6: Template Self-Test & Documentation ✅ SHIPPED 2026-05-23

**Goal**: Two coupled outcomes: (1) repo-level self-verification — a GitHub Actions matrix (`.github/workflows/template-selftest.yml`) runs `copier copy` onto a scratch directory for each meaningful add-on combination on every PR and asserts `just verify` exits 0 inside the generated project (5 Linux rows per-PR + nightly macOS rerun, <10 min wall-clock); (2) OSS-launch readiness — README (quickstart-first, asciinema cast, inline Mermaid architecture diagram, dual-audience six-row checklist), CHANGELOG via release-please, CONTRIBUTING (smoke-test loop + add-a-check + add-an-add-on-slot), OSS boilerplate (LICENSE, SECURITY.md, CODE_OF_CONDUCT.md, ISSUE_TEMPLATE/*), PR template with dual-audience checkboxes, plus the hardening roll-in: 4 OSS-blocker beads (auth scaffold + `/summarize` input defenses + `/echo` hardening + Phase 5 README pass) and 2 deferred Phase 4 audit ceremonies.
**Depends on**: Phases 1, 2, 3, 4, 5
**Requirements**: DOC-01..05, CI-01 (matrix expansion), plus OSS-launch hardening beads verify-kit-3u2/yr7/93h/1v6
**Success Criteria** (what must be TRUE):

  1. `template-selftest.yml` matrix runs 5 rows on Linux per-PR (`base`, `+backend`, `+llm`, `+backend+llm`, `+backend+llm+logfire+fastapi_mcp`); each row does `copier copy --data ... /tmp/scratch-<entry>` → `cd /tmp/scratch-<entry>` → `just verify` → exit 0; nightly macOS workflow reruns the same matrix on a weekly cron; per-PR wall-clock <10 min; cold-start scratch render exits green on all 5 combos post-gap-closure.
  2. README opens quickstart-first (tagline → asciinema cast → one-line `copier copy ...` → why-this-exists) with philosophy after; inline Mermaid architecture diagram (Universal Foundation + four add-on slots) satisfies DOC-05 in the same file; IDE Problems-panel PNG demonstrates the dual-audience promise; dual-audience six-row checklist lives in README as its own section.
  3. CHANGELOG.md is release-please-driven (conventional-commits contract: `feat:` / `fix:` / `feat!:`); each release entry carries a mandatory "Breaking changes for consumers" callout (may be empty); release-please-config.json + .release-please-manifest.json pinned at 0.0.0 baseline; CONTRIBUTING.md covers the smoke-test loop, "add a new check in 10 lines", and "how to add a new add-on slot".
  4. Backend hardening trio lands: `app/auth.py` ships `APIKeyHeader` global dependency + `VERIFYKIT_AUTH_TOKEN` env var + `X-VerifyKit-Token` header + dev-fallback when `env=dev` and token unset + `/healthz` excluded; `/summarize` ships length cap (max_length=5000) + control-char strip + 3-marker prompt-injection denylist + OWASP LLM01 caveat sentence; `/echo` ships length cap + control-char strip (no denylist per scope); 4 OSS-blocker beads closed (verify-kit-3u2/yr7/93h/1v6).
  5. OSS boilerplate complete: LICENSE (MIT), SECURITY.md, CODE_OF_CONDUCT.md (Contributor Covenant 2.1), .github/ISSUE_TEMPLATE/bug.md + feature.md, .github/pull_request_template.md with the six dual-audience rows as checkboxes; 2 deferred Phase 4 audit ceremonies (secure-phase, validate-phase) closed via 06-10; gap-closure plans 06-11/12/13 close GAPs 1-7 from initial UAT (testcontainers asyncpg URL fix, `mise trust`, `uv sync --extra dev`, X-VerifyKit-Token in rendered backend tests, schemathesis `app.state.settings` AttributeError, planning-ID leak in `.env.example`, ruff format/lint sweep).

**Plans**: 13 plans

  - [x] 06-01-PLAN.md — OSS boilerplate: LICENSE, CODE_OF_CONDUCT.md, SECURITY.md, ISSUE_TEMPLATE/bug.md + feature.md
  - [x] 06-02-PLAN.md — Auth scaffold: `app/auth.py` APIKeyHeader + global dep + dev fallback + `/healthz` exclusion (closes verify-kit-3u2)
  - [x] 06-03-PLAN.md — `/summarize` input defenses: length cap + `_INJECTION_MARKERS` 3-regex denylist + OWASP LLM01 caveat (closes verify-kit-yr7)
  - [x] 06-04-PLAN.md — `/echo` hardening: length cap + `_CONTROL_CHARS_ECHO` strip (closes verify-kit-93h)
  - [x] 06-05-PLAN.md — release-please: config + manifest + workflow + conventional-commits contract
  - [x] 06-06-PLAN.md — README authoring + inline Mermaid architecture diagram + asciinema cast + dual-audience checklist
  - [x] 06-07-PLAN.md — CONTRIBUTING.md (smoke-test loop + add-a-check + add-an-add-on-slot) + `.github/pull_request_template.md`
  - [x] 06-08-PLAN.md — template-selftest.yml (5-row Linux matrix per-PR) + template-selftest-macos.yml (weekly cron) + act validation script
  - [x] 06-09-PLAN.md — Phase 5 LLM README human-read pass (closes verify-kit-1v6)
  - [x] 06-10-PLAN.md — Phase 4 deferred audit ceremonies: 04-SECURITY.md + 04-VALIDATION.md retroactive fill
  - [x] 06-11-PLAN.md — Gap-closure sweep: GAPs 1-6 from initial UAT (testcontainers asyncpg URL, mise trust, uv --extra dev, X-VerifyKit-Token in tests, schemathesis app.state.settings, .env.example planning-ID leak)
  - [x] 06-12-SUMMARY.md — GAP-7 closure: ruff format + lint sweep ported back into `template/**/*.jinja2` (closes verify-kit-ooj; files verify-kit-xv1 GAP-8 logfire[fastapi] dep follow-up)
  - [x] 06-13-PLAN.md — Backlog closeout: pre-Phase-6 backlog beads (Phase 3 xw4 + Phase 4 plk/c5a/r7v)

- [x] **Phase 7: Web Add-on (v0.2)** — opt-in `has_web=true`: Vite + React + shadcn/ui + Tailwind v4 frontend under `web/` with two-guard path gating; Vitest + Playwright; axe-core / Lighthouse CI / Lost Pixel verifier checks; browser OTel SDK (sdk-trace-web) wired but inert by default; preset answers files (`personal.yml` + `oss-minimalist.yml`) resolving verify-kit-q8t; CI matrix expanded from 5 → 6 combos (completed 2026-05-27)

### Phase 7: Web Add-on (v0.2)

**Goal**: When a consumer answers `has_web=true`, the scaffolded project gets a working Vite + React + TypeScript + shadcn/ui + Tailwind v4 frontend under `web/` that builds, tests (Vitest unit + Playwright e2e), and folds three web-specific verifier checks (axe-core a11y, Lighthouse CI perf budgets, Lost Pixel visual regression) into `just verify --web` — with browser OTel SDK (`@opentelemetry/sdk-trace-web`) wired but inert by default so click → fetch → FastAPI → DB appears as a single Jaeger waterfall when enabled. Bundled: preset answers files (`personal.yml` + `oss-minimalist.yml`, PII-protected) resolving verify-kit-q8t, and CI matrix expanded from 5 → 6 meaningful combos.
**Depends on**: Phase 4 (Vite dev proxy targets FastAPI :8000; `expose_headers=["traceparent"]` CORS lands in FastAPI middleware; SSE bypass uses `/__debug/events`); Phase 2 (`@register` check registry + ErrorEnvelope contract + SARIF emitter consumed by axe adapter); Phase 3 (MCP `verify_check` + `fix_propose` get five new web tool registrations); Phase 6 (template-selftest matrix is the surface being expanded)
**Requirements**: WEB-01, WEB-02, WEB-03, WEB-04, WEB-05, UI-01, UI-02, UI-03, UI-04, DEV-W01, DEV-W02, DEV-W03, DEV-W04, TEST-W01, TEST-W02, TEST-W03, A11Y-01, A11Y-02, A11Y-03, A11Y-04, PERF-01, PERF-02, PERF-03, PERF-04, VIZ-01, VIZ-02, VIZ-03, VIZ-04, TRACE-01, TRACE-02, TRACE-03, TRACE-04, WMCP-01, WMCP-02, WMCP-03, PRESET-01, PRESET-02, PRESET-03, PRESET-04, PRESET-05, PRESET-06, WCI-01, WCI-02, WCI-03, WCI-04
**Success Criteria** (what must be TRUE):

  1. **Scaffold + build:** Running `copier copy --data-file presets/oss-minimalist.yml --data has_web=true gh:m2moiz/verify-kit /tmp/scratch-p7-web` produces a `web/` subdirectory where `pnpm install --frozen-lockfile && pnpm build && pnpm preview` exits 0; the polarity test `tests/test_web_polarity.py` confirms `has_web=false` leaves zero `web/` artifacts and zero Node deps in `.mise.toml`.
  2. **Dev loop across four polarities:** `just dev` brings up Vite (and FastAPI when `has_backend=true`) in parallel via mprocs for all four polarities (bare, `+web`, `+web+backend`, full stack); the Vite dev proxy routes `/api/*` → `http://localhost:8000` and a Playwright smoke spec asserts an SSE event from FastAPI's `/__debug/events` reaches the UI within 3s by hitting the absolute URL (bypassing the proxy).
  3. **Three new verifier checks land green in the full-stack combo:** `just verify-web` enumerates `--check=web.vitest --check=web.playwright --check=web.lighthouse --check=web.axe --check=web.lost_pixel` (CLI does exact match per `--check`, NOT glob — verified `template/harness/core.py.jinja2:101`). Lighthouse: LCP/CLS/INP budgets, `numberOfRuns: 5, aggregationMethod: median-run`, against `vite preview` only. axe-core writes its own SARIF file at `.verify/web/axe.sarif` via `harness.reports.sarif.emit()` (single-check SARIF; v0.2 does NOT cross-merge into `.verify/report.sarif` — verify-kit-7xm v0.3 bead). Lost Pixel: Docker-pinned `mcr.microsoft.com/playwright:v1.60.0-jammy` capture environment. The aggregate run exits 0; each check emits ErrorEnvelope-conformant JSON on failure with `code`/`hint`/`fix_command`/`docs_url` (per-finding fixability encoded in the `code` suffix — `ErrorEnvelope` has no `fixable` field; `fixable` lives on `@register(..., fixable=True)` per-check).
  4. **MCP twins + agent fix path (v0.2 scope):** The five new check IDs (`web.vitest`, `web.playwright`, `web.lighthouse`, `web.axe`, `web.lost_pixel`) are discoverable via the existing static MCP tools `verify_check(name=...)` and `list_checks()` (verified `template/harness/mcp/tools.py.jinja2:65,77`). The MCP server does NOT dynamically generate one MCP tool per registry entry; per-check MCP tool auto-generation + `readOnlyHint`/`destructiveHint` annotations are deferred to v0.3 (bead **verify-kit-964**). The existing zero-arg MCP `fix_propose()` surfaces the per-finding `fix_command` (e.g., `git add web/.lost-pixel/baseline/<diff>.png` for Lost Pixel — D-W03) via the SARIF envelope; per-finding arg filters (`fix_propose --check=<id> --finding=<route>`) are deferred to v0.3 (bead **verify-kit-pc8**). Misspelling `--check=lighthose` returns a did-you-mean for `lighthouse` (existing CLI behavior).
  5. **Browser OTel propagation:** `@opentelemetry/sdk-trace-web` + `@opentelemetry/instrumentation-fetch` ship installed but inert by default (no exporter cost until `VITE_OTEL_EXPORTER_OTLP_ENDPOINT` is set); when set, a click in the UI produces a single waterfall in `just trace --last` showing browser → fetch → FastAPI → DB linked by `traceparent`; the production bundle adds ≤100KB gzipped when OTel is enabled (Lighthouse budget asserts this).
  6. **Preset answers files (resolves verify-kit-q8t):** `presets/oss-minimalist.yml` (public default) and `presets/personal.yml` (placeholder, no PII) ship in the repo with `_schema_version: "0.2"`; `.gitignore` excludes `presets/*.local.yml`; a pre-commit hook greps staged preset files for email / full-name patterns and blocks commits on match; a CI check fails if a preset's `_schema_version` is missing or out of sync with current `copier.yml` prompt keys; both presets are exercised by the CI matrix (`copier copy --data-file presets/<x>.yml` + `just verify`).
  7. **CI matrix expansion (6 meaningful combos, GAP-10 echo bounded):** `.github/workflows/template-selftest.yml` matrix grows to exactly six combos (`base`, `+backend`, `+llm`, `+web`, `+backend+web`, `+backend+llm+web`); `+web+llm` only is explicitly skipped; pnpm store + Playwright browser cache are keyed off `pnpm-lock.yaml` SHA + Playwright version; Lighthouse + Lost Pixel run only on the full-stack combo (rationale in YAML comments); every matrix job carries `timeout-minutes: 20` and the matrix runs `fail-fast: false`.

**Plans**: 7 plans (linear chain with one parallel wave after 07-02)

  - [x] 07-01-PLAN.md — Copier prompt + two-guard path gating (`has_web` prompt; ~7 `_exclude` entries covering dotfiles; bounded `{% if has_web %}web{% endif %}/` Jinja shape; polarity test scaffolding) — depends on: nothing — risk: LOW (clone of 04-01)
  - [x] 07-02-PLAN.md — Vite + React + TS baseline (Hello-World compile-and-build; `.mise.toml` Node 22 LTS + corepack + pnpm@9 conditional on `has_web`; `pnpm install --frozen-lockfile && pnpm build` polarity assertion) — depends on: 07-01 — risk: LOW
  - [x] 07-03-PLAN.md — Tailwind v4 + shadcn + first components (`components.json`, `src/index.css` with `@import "tailwindcss"` + `@theme`, Button + Card + Input/Label/form via shadcn CLI at template-author time, tsconfig ↔ vite.config alias parity check) — depends on: 07-02 (parallel with 07-04) — risk: MED
  - [x] 07-04-PLAN.md — Vite dev proxy + `just dev` mprocs orchestration (`vite.config.ts` `/api/*` proxy; `src/lib/api.ts.jinja2` polarity-aware base URL; mprocs in `justfile.jinja2`; 4-polarity dev matrix; SSE bypass-proxy doc + smoke) — depends on: 07-02 (parallel with 07-03) — risk: MED
  - [x] 07-05-PLAN.md — Vitest + Playwright + trace fixture (`vitest.config.ts` + happy-dom + passing unit test; `playwright.config.ts` + headless smoke spec; trace fixture that injects `traceparent` on every browser request; `just web-bootstrap` runs `pnpm exec playwright install --with-deps`) — depends on: 07-03 AND 07-04 — risk: MED
  - [x] 07-06-PLAN.md — Harness adapters + check registration + browser OTel SDK wiring (`harness/web/axe_adapter.py`, `lighthouse_adapter.py`, `lostpixel_adapter.py`; `axe_to_sarif.py` ~50 LOC; `harness/checks/web.py` with 5 `@register` entries; per-check SARIF (no cross-check merge in v0.2 — verify-kit-7xm v0.3 bead); MCP twins via existing static `verify_check`/`list_checks` (per-check tool generation deferred to v0.3 — verify-kit-964); Lost Pixel docker capture; `@opentelemetry/sdk-trace-web` + `instrumentation-fetch` installed inert; `VITE_OTEL_EXPORTER_OTLP_ENDPOINT` activation path; CORS `expose_headers=["traceparent"]` lands in FastAPI when `has_web=true`) — depends on: 07-05 — risk: **HIGH** (largest plan; SARIF strict schema; 3 net-new adapter shapes; Lost Pixel cross-platform pinning; bundle-size guard)
  - [x] 07-07-PLAN.md — Recipes + presets + CI matrix + docs (`just dev/verify-web/smoke-web/web-baseline` recipes — `verify-web` enumerates `--check=<id>` flags exactly, no glob; `presets/personal.yml` + `oss-minimalist.yml` + `presets/README.md` + `.gitignore` `*.local.yml` rule + PII pre-commit grep hook + `_schema_version` CI check resolving verify-kit-q8t; template-selftest matrix 5 → 6 combos with caching + Lighthouse/Lost Pixel scoped to full-stack + `timeout-minutes: 20`; README web add-on section + AGENTS.md addendum + dual-audience six-row check for every new feature) — depends on: 07-06 — risk: MED

**UI hint**: yes

**Open question deferred to discuss-phase 7:** VIZ-04 (Lost Pixel baseline storage) — in-git PNGs vs GH Actions cache + `lost-pixel-approve` label workflow. Mapped to Phase 7 with a placeholder; `/gsd:discuss-phase 7` will resolve before plan-phase locks 07-06. **RESOLVED 2026-05-25:** in-git baselines under `web/.lost-pixel/baseline/` (D-W01).

## Dependencies

| Phase | Depends on | Why |
|-------|------------|-----|
| 1 | — | Foundation; nothing precedes the template engine itself |
| 2 | 1 | Harness package needs the Copier+just scaffolding to live inside |
| 3 | 2 | MCP tools and IDE problem matchers wrap harness outputs |
| 4 | 2, 3 | `/__debug/*` router (HARN-03) needs a FastAPI host; problem matchers + MCP snippets predate the slot |
| 5 | 2 | OTel scaffold + format contracts must exist before `@llm_call` emits spans; composes with 4 when both selected |
| 6 | 1, 2, 3, 4, 5 | Self-test exercises every prior phase across the add-on matrix |
| 7 | 2, 3, 4, 6 | Vite dev proxy targets Phase 4 FastAPI :8000; axe adapter consumes Phase 2 ErrorEnvelope + SARIF emitter; 5 new check registrations extend Phase 3 MCP `verify_check`/`list_checks` surface (no dynamic per-check tools in v0.2); CI matrix being expanded is the Phase 6 surface |

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Template Skeleton & Toolchain | 4/4 | ✅ Shipped | 2026-05-18 |
| 2. Universal Harness Core | 7/7 | ✅ Shipped | 2026-05-18 |
| 3. Agent Integration & IDE | 5/5 | ✅ Shipped | 2026-05-19 |
| 4. Backend (FastAPI) Add-on | 7/7 | ✅ Shipped | 2026-05-21 |
| 5. LLM Add-on | 5/5 | ✅ Shipped | 2026-05-22 |
| 6. Template Self-Test & Documentation | 13/13 | ✅ Shipped | 2026-05-23 |
| 7. Web Add-on (v0.2) | 0/7 | Planning (post-Codex review revision pass 2026-05-26) | — |

## Coverage

### v0.1 (SHIPPED)

- v0.1 requirements mapped: **95 / 95** (100%)
- Categories: TMPL (5), TOOL (6), CI (5), DEV (3), CLAUDE (5), HARN (8), MCP (5), AGT (3), FMT (5), IDE (5), OBS (5), UX (8), LLM (12), API (19), DOC (5)
- Orphans: none · Duplicates: none

### v0.2 (active)

- v0.2 requirements mapped: **41 / 41** (100%) — all to Phase 7

## v0.3 Deferred Beads (filed 2026-05-26 during Phase 7 review revision)

- **verify-kit-964** — per-check MCP tool auto-generation from registry (currently static `verify_check(name=...)` only)
- **verify-kit-7xm** — SARIF cross-check merge into `.verify/report.sarif` aggregator (currently per-check SARIF only)
- **verify-kit-pc8** — `fix_propose --check/--finding` arg support (CLI + MCP) (currently parameterless)
