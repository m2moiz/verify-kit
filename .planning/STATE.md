---
gsd_state_version: 1.0
milestone: v0.1
milestone_name: milestone
status: executing
last_updated: "2026-05-21T21:30:00.000Z"
last_activity: 2026-05-21 -- Phase 5 Plan 05-02 complete (harness/llm.py + Traceloop wiring)
progress:
  total_phases: 6
  completed_phases: 2
  total_plans: 28
  completed_plans: 19
  percent: 36
---

# Project State

## Current Position

Phase: 5 (llm-add-on) — EXECUTING
Plan: 05-02 ✅ complete; next 05-03
Next phase: 5 — LLM Add-on (in progress)
Branch: feat/phase-5-llm
Status: Executing Phase 5
Last activity: 2026-05-21 -- Phase 5 Plan 05-01 complete (path-gating contract + 11-pkg deps + LLM env destinations)

## Project Reference

- **Core value:** A solo developer drops verify-kit into a new project, answers a handful of prompts, and gets a project where `just verify` is the ground truth for both human (pretty terminal + clickable IDE errors) AND coding agent (MCP server + JSON output + `fix_propose` self-healing).
- **Current focus:** Phase 5 — llm-add-on
- **Trust anchor:** `just verify` exits 0 only when every check passes; template's own CI runs `copier copy` onto scratch dirs across the add-on matrix and asserts the same.

## Phase Plan

1. ✅ **Phase 1: Template Skeleton & Toolchain** — Copier + mise + just + Makefile shim + base CI + AGENTS.md
2. ✅ **Phase 2: Universal Harness Core** — Python `harness/` package, verify aggregator, structlog/Rich, format contracts, miette errors, OTel scaffold
3. ✅ **Phase 3: Agent Integration & IDE** — MCP server (13 tools), Claude hooks, .vscode files, per-agent rules + MCP snippets
4. ✅ **Phase 4: Backend (FastAPI) Add-on** — 12 default libs + opt-in logfire/fastapi_mcp, Dockerfile, `/__debug/*`, schemathesis, Testcontainers
5. **Phase 5: LLM Add-on** — pydantic-ai + instructor + litellm + autoevals + vcrpy, `@llm_call`/`@cost_budget`, Langfuse, Promptfoo
6. **Phase 6: Template Self-Test & Documentation** — `copier copy` matrix CI on every PR, README, CHANGELOG, CONTRIBUTING, diagram

## Phase 4 Wave Plan

After 04-03 wave-promotion fix (wave 2 → wave 3 to honor its `depends_on: [04-01, 04-02]`):

- **W1:** 04-01 (Copier prompts + path gating)
- **W2:** 04-02 (FastAPI skeleton + settings + middleware + HARN-03 debug router)
- **W3:** 04-03 (Async SQLAlchemy + Alembic + Testcontainers), 04-04 (Typer CLI sibling + Ralph host)
- **W4:** 04-05 (Dockerfile + docker-compose), 04-06 (logfire + fastapi-mcp opt-ins)
- **W5:** 04-07 (verify-backend slice + README)

## Performance Metrics

- Phases complete: 4/6
- Plans complete: 17/24 (Phase 4 contributed 7)
- v0.1 requirements mapped: 95/95 (100%)
- Coverage gaps: none

## Accumulated Context

### Decisions

- See `research/00-decision-log.md` for D-001 through D-020.
- Scope locked: Path 3 (Universal + Backend + LLM in v0.1; Web/Audio/Game deferred to v0.2).
- Granularity: coarse (6 phases, slightly above coarse target due to add-on slot count).
- Phase 4 path-gating contract: see `.planning/REVIEW-CHECKLIST.md` §3 (cross-plan contract drift) and 04-01 replan note for the two-guard rule (Copier `_exclude` + bounded Jinja path shapes).
- [Phase ?]: LIFO middleware order: secure outermost (registered last), pyinstrument innermost (registered first)
- [Phase ?]: CorrelationIdMiddleware validator=None accepts arbitrary inbound IDs, not just UUID4
- [Phase ?]: HARN-03 debug router in universal harness/, conditional mount in app/main.py only
- [Phase ?]: patch(app.main.log, MagicMock) to capture structlog access-log calls (cache_logger_on_first_use bypass)
- [Phase ?]: @app.callback() prevents Typer single-command hoisting in app/cli.py
- [Phase ?]: ralph._spawn is the injectable test seam; executor is a str command name

### Todos

- [x] Execute Phase 4 waves 1-5
- [x] Phase 4 verify-work (gaps closed in 59d3ae5)
- [ ] Phase 4 secure-phase (optional follow-up; threat model unaudited)
- [ ] Phase 4 validate-phase (optional follow-up; Nyquist coverage unaudited)
- [ ] Plan Phase 5 (LLM add-on)

### Blockers

- None.

## Session Continuity

- Last action: Phase 5 discuss-phase completed. 05-CONTEXT.md committed (c8eb9da) with 20 locked decisions across 7 gray areas. Master fast-forwarded to include Phase 4. GAP-06 fix landed (c3eba7f). Beads tracker initialized. 3 Phase 4 validation HIGHs filed as beads issues (verify-kit-plk, -c5a, -r7v), deferred to Phase 6 self-test sweep. Drift-prevention issue #3813 filed upstream at gsd-build/get-shit-done. Local drift-guard fork applied to ~/.claude/get-shit-done/workflows/review.md (source-grounding reviewer pass — first real-world test is Phase 5's plan-review-convergence).
- Next action: `/gsd:plan-phase 5` to generate Phase 5 PLAN.md files from 05-CONTEXT.md. Then `/gsd:plan-review-convergence 5 --codex --max-cycles 3` (which will exercise the local drift-guard for the first time).
- Note: `.planning/` is gitignored but force-added in this project (consistent with prior phase commits — see `dfd22ac`, `1800398`, etc.). Use `git add -f` for planning files; commits to AI-workflow files need `ALLOW_AI_WORKFLOW_FILES=1` to satisfy the global guard hook. Branch is `feat/phase-5-llm` off master.

## Performance Metrics

| Phase | Plan | Duration | Notes |
|-------|------|----------|-------|
| Phase 4 P04-01 | 12m | 4 tasks | 5 files |
| Phase 4 P04-02 | 70m | 14 tasks | 15 files |
| Phase 4 P04-03 | 20m | 6 tasks | 9 files |
| Phase 4 P04-04 | 20m | 4 tasks | 4 files |
| Phase Phase 4 PP04-05 | 7m | 5 tasks | 5 files |
| Phase Phase 4 PP04-07 | 90m | 7 tasks | 8 files |
