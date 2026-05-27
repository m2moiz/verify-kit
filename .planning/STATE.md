---
gsd_state_version: 1.0
milestone: v0.2
milestone_name: milestone
status: verifying
last_updated: "2026-05-27T13:41:27.535Z"
last_activity: 2026-05-27
progress:
  total_phases: 7
  completed_phases: 5
  total_plans: 53
  completed_plans: 47
  percent: 71
---

# Project State

## Current Position

Phase: 07
Plan: Not started
Status: Phase 07 verification returned gaps_found (4/7 SC); 6 gaps mapped to 5 gap-closure plans
Resume file: .planning/phases/07-web-add-on-v0-2/07-08-PLAN.md
Last activity: 2026-05-27

Gap-closure waves (each plan serialized on tests/test_web_polarity.py):

- W1: 07-08 (TRACE-01/02/04 browser OTel SDK inert-by-default + TRACE-03 assertion inversion + bundle budget)
- W2: 07-09 (DEV-W04 web/.vscode/ extensions+settings)
- W3: 07-10 (DEV-W03 SSE Playwright 3s assertion)
- W4: 07-11 (VIZ-03 lost-pixel-approve CLI shim; MCP half deferred to v0.3 verify-kit-pc8)
- W5: 07-12 (PRESET-06 CI preset-render + WCI-02 weekly cold-install cron)

Next: /gsd:execute-phase 7 --gaps-only

## Recent milestones — 2026-05-26

- **v0.1.0 released:** First public release shipped via release-please PR #24 (squash sha `264fb8c`). Tag `v0.1.0` + GitHub Release published 22:30 UTC. All Phases 1-6 included; CHANGELOG generated from conventional commits.
- **All PRs from prior sessions resolved:** #12-15 (Dependabot bumps) and #18 (test triage) all merged. No open PRs.
- **History rewrite (security):** `git filter-repo` scrubbed `research/`, `SESSION-HANDOFF.md`, `.claude/hooks/`, `.gsd/` from all 327 commits and added them to .gitignore. Internal-only artifacts now live exclusively inside `.planning/` (gitignored) — never touch the public-tracked surface.
- **Planning vault:** `.planning/` is now a nested git repo (branch `vault`) with private remote `gh:m2moiz/verify-kit-planning` and a 3-trigger autocommit hook (PostToolUse:Agent + Stop + SessionEnd). Rollback safety for agentic workflows. Full details: [[planning_vault]] in project memory.

## Project Reference

- **Core value:** A solo developer drops verify-kit into a new project, answers a handful of prompts, and gets a project where `just verify` is the ground truth for both human (pretty terminal + clickable IDE errors) AND coding agent (MCP server + JSON output + `fix_propose` self-healing).
- **Current focus:** Phase 07 — web-add-on-v0-2
- **Trust anchor:** `just verify` exits 0 only when every check passes; template's own CI runs `copier copy` onto scratch dirs across the add-on matrix and asserts the same. **v0.1: 5/5 green as of CI run 26372325420. v0.2 will expand to 6 combos.**

## Milestone Status

### v0.1 — Foundation + Backend + LLM (SHIPPED 2026-05-24, public MIT release)

6 phases, 34 plans, 95 requirements 100% mapped. All green. Preserved historical record below.

1. ✅ **Phase 1: Template Skeleton & Toolchain** — Copier + mise + just + Makefile shim + base CI + AGENTS.md
2. ✅ **Phase 2: Universal Harness Core** — Python `harness/` package, verify aggregator, structlog/Rich, format contracts, miette errors, OTel scaffold
3. ✅ **Phase 3: Agent Integration & IDE** — MCP server (13 tools), agent hooks, .vscode files, per-agent rules + MCP snippets
4. ✅ **Phase 4: Backend (FastAPI) Add-on** — 12 default libs + opt-in logfire/fastapi_mcp, Dockerfile, `/__debug/*`, schemathesis, Testcontainers
5. ✅ **Phase 5: LLM Add-on** — pydantic-ai + instructor + litellm + autoevals + vcrpy, `@llm_call`/`@cost_budget`, Langfuse, Promptfoo
6. ✅ **Phase 6: Template Self-Test & Documentation** — `copier copy` matrix CI on every PR (5-combo green), README, CHANGELOG, CONTRIBUTING, release-please

### v0.2 — Web Add-on (active, planning)

Single-phase milestone by design. 41 v0.2 requirements, all mapped to Phase 7. Discuss-phase pending on the one open design question (VIZ-04).

7. **Phase 7: Web Add-on** — has_web=true → Vite + React + shadcn/ui + Tailwind v4 + Vitest + Playwright; web-specific harness checks (Lighthouse, axe-core, Lost Pixel); browser OTel SDK (sdk-trace-web) wired but inert by default; preset answers files (`personal.yml` + `oss-minimalist.yml`) resolving verify-kit-q8t; CI matrix 5 → 6 combos

   **Locked design decisions (2026-05-24/25):**

   - Framework: Vite + React (NOT Next.js — Next.js deferred to v0.3 epic verify-kit-23w)
   - UI: shadcn/ui (`shadcn@^4.8`, NOT deprecated `shadcn-ui`) + Tailwind v4 (`@import "tailwindcss"` + `@theme`, NO `tailwind.config.js`)
   - Backend wiring: Vite dev proxy `/api/*` → FastAPI :8000 (no Node runtime in production path); SSE bypass via absolute URL
   - Browser OTel ships in v0.2 (full `@opentelemetry/sdk-trace-web`, not deferred); bundle-size guard ≤100KB gzipped (TRACE-04)
   - Preset PII protection: strong (`.gitignore *.local.yml` + pre-commit grep + `_schema_version` CI check)
   - Package manager: pnpm@9 via corepack; Node 22 LTS via mise (conditional on `has_web`)
   - CI matrix: 6 meaningful combos (`base`, `+backend`, `+llm`, `+web`, `+backend+web`, `+backend+llm+web`); `+web+llm` only explicitly skipped

   **Sub-plan structure (7 plans, linear chain with one parallel wave):**

   ```
   07-01 ──> 07-02 ──┬──> 07-03 ──┐
                     │             ├──> 07-05 ──> 07-06 ──> 07-07
                     └──> 07-04 ──┘
   ```

   - 07-01: Copier prompt + two-guard path gating (LOW)
   - 07-02: Vite + React + TS baseline (LOW)
   - 07-03: Tailwind v4 + shadcn + first components (MED) — parallel with 07-04
   - 07-04: Vite dev proxy + `just dev` mprocs (MED) — parallel with 07-03
   - 07-05: Vitest + Playwright + trace fixture (MED)
   - 07-06: Harness adapters + check registration + browser OTel SDK (**HIGH** — largest plan; SARIF strict; 3 adapter shapes; Docker-pinned Lost Pixel)
   - 07-07: Recipes + presets + CI matrix + docs (MED)

   **Open question (REQ-OPEN, blocks 07-06 finalization):** VIZ-04 — Lost Pixel baseline storage strategy (in-git PNGs vs GH Actions cache + `lost-pixel-approve` label workflow). Resolved by `/gsd:discuss-phase 7`.

## Phase 4 Wave Plan (historical, preserved)

After 04-03 wave-promotion fix (wave 2 → wave 3 to honor its `depends_on: [04-01, 04-02]`):

- **W1:** 04-01 (Copier prompts + path gating)
- **W2:** 04-02 (FastAPI skeleton + settings + middleware + HARN-03 debug router)
- **W3:** 04-03 (Async SQLAlchemy + Alembic + Testcontainers), 04-04 (Typer CLI sibling + Ralph host)
- **W4:** 04-05 (Dockerfile + docker-compose), 04-06 (logfire + fastapi-mcp opt-ins)
- **W5:** 04-07 (verify-backend slice + README)

## Performance Metrics

- Phases complete: **6/7 (86%)** — v0.1 shipped, v0.2 Phase 7 active
- Plans complete: **34/34 (v0.1, 100%)**; v0.2 Phase 7 plans: 0/7
- v0.1 requirements mapped: 95/95 (100%)
- v0.2 requirements mapped: 41/41 (100%)
- Coverage gaps: none
- Template-selftest CI: **5/5 combos green** (run 26372325420, commit 4a4713e) — v0.2 expands to 6 combos
- release-please CI: green (run 26372366711 rerun, after GAP-9 toggle)
- Beads closed in v0.1: 26
- Beads open in v0.1.x backlog: 32 (under epic verify-kit-2ua)

## Accumulated Context

### Decisions

- See `research/00-decision-log.md` for D-001 through D-020.
- Scope locked: Path 3 (Universal + Backend + LLM in v0.1; Web in v0.2; Audio/Game/Next.js/Vanta deferred to v0.3+).
- Granularity: coarse (6 phases v0.1, 1 phase v0.2; total 7).
- Phase 4 path-gating contract: see `.planning/REVIEW-CHECKLIST.md` §3 (cross-plan contract drift) and 04-01 replan note for the two-guard rule (Copier `_exclude` + bounded Jinja path shapes). **This rule is the dominant landmine for Phase 7 (web/ subtree adds more dotfile surface than backend/).**
- Phase 5 dep stack: pydantic-ai-slim>=1.100 forced fastmcp>=3.3 bump (Phase 3 re-validated for 3.x API).
- Phase 5 D-22: dropped tokenx-core after slopcheck flagged it (81 downloads, supply-chain risk).
- Phase 6 auth scaffold: X-VerifyKit-Token + VERIFYKIT_AUTH_TOKEN env slot (06-02).
- Phase 6 PEP 735 migration: `[dependency-groups].dev` is the canonical dev-deps location (NOT `[project.optional-dependencies].dev` which `uv run` does not sync by default — bit us 3x as GAP-5/7/10-L4).
- Phase 6 GAP-10 6-layer CI saga: see postmortem at `.planning/postmortem/verify-kit-v0.1-postmortem.html` §04. **Phase 7 CI matrix expansion budget must reflect this.**
- v0.2 web add-on framework: Vite + React (Next.js deferred — see verify-kit-23w epic).
- v0.2 browser OTel: ships in v0.2 (user override of research recommendation to defer); guarded by Lighthouse bundle-size budget.
- v0.2 preset PII: strong three-layer guard (gitignore + pre-commit grep + schema_version CI check).
- [Phase ?]: Phase 7 plans revised per Codex cross-AI review (5 HIGHs NARROWed, 3 v0.3 beads filed)

### LIFO + middleware + Typer notes (Phases 2-4)

- LIFO middleware order: secure outermost (registered last), pyinstrument innermost (registered first)
- CorrelationIdMiddleware validator=None accepts arbitrary inbound IDs, not just UUID4
- HARN-03 debug router in universal harness/, conditional mount in app/main.py only
- patch(app.main.log, MagicMock) to capture structlog access-log calls (cache_logger_on_first_use bypass)
- @app.callback() prevents Typer single-command hoisting in app/cli.py
- ralph._spawn is the injectable test seam; executor is a str command name

### Todos

- [x] Execute Phase 4 waves 1-5
- [x] Phase 4 verify-work (gaps closed in 59d3ae5)
- [x] Phase 4 secure-phase (re-run 2026-05-23 per 06-10)
- [x] Phase 4 validate-phase (re-run 2026-05-23 per 06-10)
- [x] Plan Phase 5 (LLM add-on)
- [x] Execute Phase 5
- [x] Execute Phase 6 (template self-test + documentation)
- [x] Ship v0.1 publicly (CI green, repo public, release PR open)
- [x] v0.1.x mistake-prevention quick wins (5/5)
- [x] Invoke /gsd:new-milestone for v0.2 (PROJECT.md scope updated 2026-05-25)
- [x] v0.2 ROADMAP.md (Phase 7 mapped, 41/41 v0.2 requirements covered)
- [ ] Resolve verify-kit-q8t (personal-defaults vs OSS-minimalist) — partially resolved by PRESET-01..06 design; VIZ-04 still open
- [ ] `/gsd:discuss-phase 7` — resolve VIZ-04 (Lost Pixel baseline storage)
- [ ] `/gsd:plan-phase 7` — decompose 07-01..07-07 into executable plans
- [ ] Reconcile 3 deferred-human-capture beads: pdc (asciinema cast), 87i (VS Code Problems screenshot), adl (LLM README read-through)
- [ ] Merge release-please PR #1 (chore(main): release 0.1.0) when ready to tag

### Blockers

- None for v0.1 (shipped).
- **Phase 7 plan-phase is soft-blocked on VIZ-04** (Lost Pixel baseline storage) — not blocking discuss-phase invocation; just needs resolution before 07-06 finalizes. All other v0.2 design decisions are locked.

## Session Continuity

- **Last action (2026-05-25):** v0.2 ROADMAP.md created by gsd-roadmapper. Phase 7 (Web Add-on) added with 41/41 v0.2 requirements mapped, 7 success criteria (observable behaviors), 7 sub-plans enumerated (07-01..07-07) with dependencies and risk levels. REQUIREMENTS.md traceability extended (v0.1 rows preserved verbatim). STATE.md bumped to total_phases=7, v0.2 status added.
- **Next action:** `/gsd:discuss-phase 7` with VIZ-04 as the central design topic (Lost Pixel baseline storage: in-git PNGs vs GH Actions cache + label workflow). After discuss-phase resolves, `/gsd:plan-phase 7` decomposes 07-01..07-07 into executable plans.
- **Note:** `.planning/` is gitignored AND untracked (commit 947a582) before going public. New planning files won't be tracked. Commits to AI-workflow files need `ALLOW_AI_WORKFLOW_FILES=1` to satisfy the global guard hook. Branch is `main`.
- **Stop hook active:** session-end-checklist.sh warns on unpushed commits + grep-not-verification + STATE.md/ROADMAP.md drift.

## Performance Metrics (per-plan timing, historical)

| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| Phase 4 | 04-01 | 12m | 4 | 5 |
| Phase 4 | 04-02 | 70m | 14 | 15 |
| Phase 4 | 04-03 | 20m | 6 | 9 |
| Phase 4 | 04-04 | 20m | 4 | 4 |
| Phase 4 | 04-05 | 7m | 5 | 5 |
| Phase 4 | 04-07 | 90m | 7 | 8 |
| Phase 5 | (various) | not tracked at plan grain | — | — |
| Phase 6 | (13 plans) | not tracked at plan grain | — | — |

(Per-plan timing tracking dropped after Phase 4 due to overhead vs value; phase-level wall-clock is the operating signal now.)
