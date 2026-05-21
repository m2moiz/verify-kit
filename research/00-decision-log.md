---
title: Decision Log
aliases: [Decisions, Decision History, Why Did We]
tags: [verify-kit, decisions, log, synthesis]
created: 2026-05-17
status: living-document
---

# 📜 Decision Log

> [!abstract] Chronological record
> Every significant verify-kit decision with the alternatives considered and the rationale. Update as new decisions land.

## 2026-05-17 — Project genesis

### D-001: verify-kit is its own standalone project, not coupled to Sora ^D-001
- **Considered:** Building verify-kit inside Sora; building both in parallel; standalone repo
- **Chose:** Standalone repo at `~/Documents/code/verify-kit`
- **Why:** Reusable across all future projects; standalone portfolio piece; cleaner abstractions when built in isolation
- **See:** [[00-architecture-overview]]

### D-002: Repo name `verify-kit` ^D-002
- **Considered:** `agentic-harness`, `selfverify`, `copier-agentic-harness`, `verify-kit`
- **Chose:** `verify-kit`
- **Why:** Terse, action-oriented, describes what it does

### D-003: Copier as template engine ^D-003
- **Considered:** Cookiecutter, Cookiecutter+Cruft, Copier, degit, Yeoman, Backstage, GitHub template repos
- **Chose:** **Copier**
- **Why:** Only mainstream scaffolder with native `copier update` + 3-way merge for re-applying improvements; `.copier-answers.yml` records template ref per consumer; `tiangolo/full-stack-fastapi-template` migrated to it (strong adoption signal)
- **See:** [[wave-2-scaffolding-tools]], [[tools/copier]]

### D-004: mise as toolchain + task spine ^D-004
- **Considered:** Make, Just (standalone), Task, mise, Bazel, Pants, Nx, Turborepo, Dagger
- **Chose:** **mise + Python helper package, with Just as task runner**
- **Why:** mise's single `.mise.toml` declares both toolchain versions AND tasks — solves bootstrap + orchestration in one file. Polyglot-native via shebang recipes. Bazel/Pants overkill; Nx/Turborepo JS-shaped; Dagger Docker-heavy.
- **See:** [[wave-2-polyglot-orchestration]], [[tools/mise]], [[tools/just]]

### D-005: GitHub Actions only (no multi-CI portability) ^D-005
- **Considered:** GitHub Actions + `act`, Dagger, Earthly (now dead), CI-portable via `just`
- **Chose:** **GitHub Actions only**, with `act` for local
- **Why:** ~68% of OSS lives on GitHub; CI-portability via Dagger/Earthly = premature optimization; thin-wrapper pattern (CI calls `just verify`) gets 95% portability anyway
- **See:** [[wave-2-ci-portability]]

### D-006: Langfuse Cloud Hobby → self-host on Hetzner CX32 ^D-006
- **Considered:** Langfuse (cloud/self-host), Phoenix, Helicone, per-project SQLite logs
- **Chose:** **Langfuse Cloud Hobby (free 50k events/mo) → self-host Hetzner CX32 (~€7.60/mo) when outgrown**
- **Why:** One personal AI ops backend across all projects; free until outgrown; Phoenix weaker multi-project isolation; Helicone proxy coupling not worth it; per-project SQLite is "you'll build a worse Langfuse over six months"
- **See:** [[wave-2-llm-hosting]], [[tools/langfuse]]

### D-007: Devcontainer optional (NOT default) ^D-007
- **Considered:** Mandatory devcontainer, optional devcontainer, no devcontainer
- **Chose:** **Optional via Copier prompt**
- **Why:** Don't impose Docker dependency on Mac/Linux solo devs; free insurance for cloud + Windows users; opt-in lets the install-Python-on-host majority skip the friction
- **See:** [[wave-3-vscode-ide]]

### D-008: LSP/DAP-first tooling for cross-IDE parity ^D-008
- **Considered:** VS Code-specific config, per-IDE config files, LSP/DAP-first
- **Chose:** **LSP/DAP-first tools** (Ruff, Pyright, Biome, debugpy) + 4 .vscode files as courtesy + 5 editor-agnostic files for everyone
- **Why:** LSP/DAP gives IDE features in VS Code AND JetBrains AND Zed AND Neovim for free. Custom problem matchers in tasks.json make errors clickable. Devcontainer = opt-in (Docker dependency too heavy by default).
- **See:** [[wave-3-vscode-ide]]

### D-009: Dual first-class citizen design ^D-009
- **Considered:** Agent-first (sacrifice human UX), human-first (no agent integration), dual-first-class
- **Chose:** **Dual first-class** with 6-row checklist gating every feature
- **Why:** User has been bitten by both failure modes. Same data, different rendering (pretty terminal for humans, JSON for agents). Use IDE protocols (LSP/DAP/MCP) not bespoke. Six-row checklist gates every feature: human-in-terminal sees X, human-in-IDE sees Y, agent gets Z, agent has fix path, human can override, both can collaborate mid-flow.
- **See:** [[00-architecture-overview#Dual-audience checklist]]

### D-010: MCP server + AGENTS.md as agent-first foundation ^D-010
- **Considered:** No agent integration, MCP only, AGENTS.md only, both
- **Chose:** **Both — MCP server + AGENTS.md**
- **Why:** MCP is the universal tool-protocol (Nov 2025 spec stable, every coding agent speaks it). AGENTS.md is the universal rules file (Linux Foundation, 60k+ repos, read by Cursor/Codex/Aider/Copilot/Jules/Zed/JetBrains/Claude). Both together = first-class in every agent.
- **See:** [[wave-4-mcp-agent-integration]]

### D-011: 13-tool MCP server with CLI twins ^D-011
- **Considered:** No MCP server, MCP-only (no CLI), CLI-only (no MCP), both with twins
- **Chose:** **MCP server with 13 tools, each having a CLI twin returning identical JSON**
- **Why:** Single source of truth; agents use MCP, humans use CLI, both get same data. Tools: verify, verify_check, list_checks, smoke, trace_last, debug_state, debug_events, eval_run, eval_compare, ralph_run, ralph_status, fix_propose, describe
- **See:** [[wave-4-mcp-agent-integration]]

### D-012: miette/rustc-style error format ^D-012
- **Considered:** Plain stack traces, Python tracebacks, miette/rustc-style structured errors
- **Chose:** **miette/rustc-style**: header with code → file:line + source snippet → fix suggestion → docs link → repro command
- **Why:** Same format readable by humans AND parseable by agents. Rustc/miette is the gold standard. Pairs with did-you-mean for typos.
- **See:** [[wave-3-ease-of-use]], [[wave-3-human-friendly-logging]]

### D-013: `--format=*` everywhere + isatty discipline + exit code contract ^D-013
- **Considered:** Pretty-only, JSON-only, both as separate commands, both via flag with isatty default
- **Chose:** **isatty discipline + `--format={pretty,json,jsonl,sarif,junit,otlp}` on every command**
- **Why:** Convention from `gh`, `rg`, `bat`, `cargo`, `kubectl`. Pretty when TTY, structured when piped. Exit codes semantic: 0 ok, 1 check-failed, 2 bad-input, 10+ infra.
- **See:** [[wave-4-mcp-agent-integration]]

### D-014: Path 3 scope — v0.1 = Universal + Backend + LLM, v0.2 = Web/Audio/Game ^D-014
- **Considered:**
  - Path A: All 5 add-ons in v0.1 (~6 weeks)
  - Path B: Universal foundation only in v0.1 (~2 weeks)
  - Path C: Universal + Backend + LLM in v0.1 (~4 weeks)
- **Chose:** **Path C**
- **Why:** Backend and LLM are the two add-ons every project of user's actually uses (FastAPI + LLM calls). They compose naturally — `logfire` auto-traces LLM calls, `fastapi-mcp` exposes LLM endpoints as MCP tools, Schemathesis fuzzes the OpenAPI of AI apps. Web/Audio/Game are narrower; ship in v0.2.

### D-015: pydantic-ai as LLM agent framework + 6 supporting libs ^D-015
- **Considered:** pydantic-ai, instructor, Mirascope, BAML, DSPy, Marvin, raw SDK
- **Chose:** **pydantic-ai (primary) + instructor (single-call typed) + litellm (provider abstraction) + tokencost+tokenx (cost) + autoevals (scoring) + vcrpy (replay) + opentelemetry-instrumentation-httpx (auto-spans)**
- **Why:** pydantic-ai is the 2026 breakout — typed agents, built-in OTel, one-line provider swaps, Pydantic team behind it. instructor for the "one call, typed response" case. litellm for cross-provider abstraction. autoevals from Braintrust OSS gives pytest scorers without Braintrust account. BAML/DSPy too high lock-in for v0.1.
- **See:** [[wave-4-ai-sdk-ergonomics]]

### D-016: `fastapi-mcp` as opt-in Backend add-on feature ^D-016
- **Chose:** Opt-in via `--mcp` Copier flag
- **Why:** Three lines turn FastAPI app into MCP server with OAuth 2.1 — turns user's backend into agent tooling. Killer feature for agent-first projects but not universally needed.
- **See:** [[wave-4-fastapi-ecosystem]]

### D-017: Multi-agent autonomous workflow architecture ^D-017
- **Considered:** Single-agent only, peer-to-peer agents, hierarchical with file contract, supervisor+workers
- **Chose:** **Hierarchical Architect/Editor (Aider pattern) with filesystem as message bus, two git worktrees, Ralph loop wrapper, deterministic VERIFY.sh + LLM judge gate**
- **Why:** Production winners (Spotify Honk, Cursor 2.0, Anthropic research, Factory.ai) all converged on this shape. Aider Architect/Editor is 30–50% cheaper than monolithic agent. Filesystem-as-bus prevents infinite loops. VERIFY.sh + LLM judge catch "passes CI but functionally wrong" (Honk's 25% veto rate).
- **See:** [[00-autonomous-workflow]], [[wave-5-multi-agent-case-studies]]

### D-018: PHASE-EXEC-NOTES.md per phase as Codex→Claude handoff ^D-018
- **Considered:** STATE.md only, JSON state, PHASE-EXEC-NOTES.md per phase, all three
- **Chose:** **All three: STATE.md (append-only progress) + PHASE-EXEC-NOTES.md (Codex documents per-phase work) + `[codex]/[claude]` commit prefixes**
- **Why:** STATE.md gives Claude continuity across sessions; PHASE-EXEC-NOTES.md gives Claude rich handoff context; commit prefix is grep-able audit trail
- **See:** memory note *claude_codex_collab* (in `~/.claude/projects/-Users-moiz-Documents-code-verify-kit/memory/`)

### D-019: GSD as planning ceremony framework (already installed) ^D-019
- **Chose:** GSD v1.42.3 for all planning ceremonies
- **Why:** Already installed; built-in `/gsd:autonomous`, `/gsd:plan-review-convergence --codex`, `/gsd:review` for cross-AI; v1.42.3 supports `--codex` flag so Codex CLI can run GSD skills directly
- **Configured:** `workflow.plan_review_convergence=true`, `review.default_reviewers=["codex"]`
- **See:** [[wave-5-gsd-autonomous]]

### D-020: Conservative Phase 1 execution (supervised, not autonomous) ^D-020
- **Chose:** Supervised first run for Phase 1, autonomous from later phases
- **Why:** Trust must be established. Phase 1 builds the foundation that includes `just verify` — until that exists, there's no deterministic verifier for autonomous loops. Phase 2+ can be progressively autonomous as the harness matures (recursive: verify-kit's `just verify` becomes the trust anchor for verify-kit's own autonomous development).

## Format for new decisions

```markdown
### D-NNN: <Decision title>
- **Considered:** [alternatives]
- **Chose:** [decision]
- **Why:** [rationale]
- **See:** [[related notes]]
```

## Related notes

- [[00-architecture-overview]]
- [[00-stack-decisions]]
- [[00-autonomous-workflow]]
- [[README]] (MOC)
