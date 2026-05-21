---
title: Agent-First Integration Patterns (MCP + AGENTS.md)
aliases: [Wave 4 - MCP, Agent Integration, Dual First-Class]
tags: [research, wave-4, mcp, agents-md, dual-audience]
wave: 4
source_agent: mcp-agent-integration
created: 2026-05-17
---

# Agent-First Integration Patterns for Dev Tools (2024–2026)

> [!abstract] Headline
> Three converging forces resolved the "first-class for agents AND humans" problem during 2025: **(1) MCP became universal tool-protocol** (Nov 2025 spec stable); **(2) AGENTS.md became universal rules file** (Linux Foundation-stewarded, 60k+ repos); **(3) isatty(stdout) discipline became standard** (pretty for humans, JSON/SARIF/JUnit when piped). A tool that ships **MCP server + AGENTS.md + `--json` everywhere** is first-class in every agent and every terminal as of mid-2026.

## Synthesis of Landscape

The "first-class for agents AND humans" design problem now has a recognizable canonical answer. Three convergent forces:

1. **MCP became the universal tool-protocol.** Nov 2025 spec stabilized JSON-RPC 2.0 over stdio + Streamable HTTP. Every serious coding agent (Claude Code, Cursor, Continue, Zed, Windsurf, JetBrains AI/Junie, Copilot Workspace) speaks it.
2. **AGENTS.md became the universal rules file.** Linux Foundation–stewarded (Anthropic + OpenAI + Block, Dec 2025). 60k+ repos. Cursor, Codex, Copilot, Jules, Aider, Goose, Factory, Devin, Zed all read it. CLAUDE.md and `.cursor/rules/*.mdc` still exist as agent-specific supplements.
3. **The `isatty(stdout)` discipline became standard.** Pretty for humans, structured (JSON/JSONL/SARIF/JUnit) when piped or `--format=json`. `gh`, `rg`, `bat`, `cargo --message-format=json`, `kubectl -o json` all do this.

## 1. MCP — The Protocol Layer

| Item | Detail |
|---|---|
| **Spec version** | 2025-11-25 (stable). 2026 work in Working Groups. JSON-RPC 2.0 |
| **Primitives** | **Tools** (LLM-callable actions, side-effects OK), **Resources** (read-only data, URI-addressed), **Prompts** (user-invoked templates). Most CLI wrappers expose Tools only |
| **Transports** | **stdio** for local subprocess (default for CLI wrappers), **Streamable HTTP** for hosted/team servers. SSE deprecated March 2025. Rule: if user controls machine, stdio; else HTTP |
| **SDKs** | Python: `fastmcp` (3.0 GA Jan 2026 — versioning, OTel, granular auth; 3.1 adds Code Mode). TypeScript: `@modelcontextprotocol/sdk`. Rust: official. `fastmcp` powers ~70% of all MCP servers |
| **Adoption signal** | Anthropic-blessed, cross-vendor. Universal |
| **Cross-agent portability** | Configuration annoyingly fragmented — Cursor/Claude/Cline/Windsurf share `mcpServers` schema; Zed uses `context_servers`; Continue uses `.continue/mcpServers/*.json`; JetBrains 2025.2+ ships own MCP server. **One server binary, N config snippets** |
| **Dual-audience** | Preserved — MCP server is *additive*. CLI keeps working |
| **verify-kit ship?** | **Yes, by default** |
| **Catch** | Auth/permissions still maturing in enterprise; per-tool risk classification not standardized |

## 2. The AGENTS.md Convention

| Item | Detail |
|---|---|
| **What** | Single Markdown file at repo root. Build/test/lint commands, code style, security notes |
| **Precedence** | Closest AGENTS.md to edited file wins. Explicit chat instruction beats file. CLAUDE.md / `.cursor/rules/*.mdc` are *supplements*, read in addition |
| **Adoption** | 60k+ repos. Codex, Cursor, Copilot, Jules, Aider, Goose, Factory, Devin, Zed, Warp, JetBrains Junie, Claude Code (Claude reads CLAUDE.md preferentially but will also pick up AGENTS.md) |
| **Governance** | Linux Foundation / Agentic AI Foundation (Dec 2025) |
| **verify-kit ship?** | **Yes — generate AGENTS.md by default**, plus optional CLAUDE.md and `.cursor/rules/verify-kit.mdc` behind Copier prompts |
| **Catch** | Some teams now have *both* AGENTS.md and CLAUDE.md/copilot-instructions.md and they drift. Use AGENTS.md as source of truth; agent-specific files should be thin pointers |

## 3. Claude Code Surface Area (2025–2026)

| Surface | Path | Use for verify-kit |
|---|---|---|
| **Hooks** | `.claude/settings.json` → `hooks` block. Events: `SessionStart`, `SessionEnd`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `Stop`, `StopFailure`, `SubagentStop` | `Stop` hook running `verify-kit verify --json` returning non-zero blocks completion. Canonical pattern |
| **Skills** | `~/.claude/skills/<name>/SKILL.md` (personal) or `.claude/skills/<name>/SKILL.md` (project). YAML frontmatter + Markdown body. Lazy-loaded | Ship `verify-kit-verify`, `verify-kit-debug`, `verify-kit-eval` skills |
| **Subagents** | `.claude/agents/<name>.md`. Specialized context-isolated AI | Optional `verify-kit-fixer` subagent reading `verify --json` and proposing patches |
| **Slash commands** | `.claude/commands/<name>.md` | `/verify`, `/smoke`, `/trace-last` thin wrappers over CLI |
| **Memory** | `CLAUDE.md` (project) + `~/.claude/CLAUDE.md` (user) | Project CLAUDE.md ~20 lines pointing at AGENTS.md + verify-kit conventions |
| **Permissions** | `.claude/settings.json` → `permissions.{allow,ask,deny}`. New "auto mode" uses Sonnet 4.6 classifier | Ship `settings.json.example` with verify-kit CLI pre-allowed (read-only) and `verify-kit fix` in `ask` |

## 4. Cursor / Windsurf / Continue / Zed / JetBrains

| Tool | Rules file | MCP config | Notes |
|---|---|---|---|
| **Cursor** | `.cursor/rules/*.mdc` (current). `.cursorrules` deprecated but still read. `globs:` / `alwaysApply:` frontmatter. Keep `alwaysApply` rules <200 words | `.cursor/mcp.json`, `mcpServers` schema | Also reads `AGENTS.md` |
| **Windsurf** | `.windsurfrules` or `.windsurf/rules/`. Cascade-aware | Same `mcpServers` schema as Cursor | Reads AGENTS.md |
| **Continue.dev** | YAML `config.yaml` (slash commands still need legacy `config.json`) | Drop JSON files into `.continue/mcpServers/`. Supports stdio + SSE + Streamable HTTP with auto-fallback | Most permissive — can import Claude/Cursor MCP configs directly |
| **Zed** | `.rules` / `AGENTS.md` / `CLAUDE.md` all read | `.zed/settings.json` → `context_servers` (not `mcpServers`). Forwards MCP to Claude Agent + Codex via ACP | Different key name, same protocol |
| **JetBrains 2025.2+** | AI Assistant / Junie reads AGENTS.md | Ships its *own* MCP server so external clients see IDE as tool. Also consumes MCP | Only IDE that's both MCP server AND client |
| **GitHub Copilot / Workspace** | `.github/copilot-instructions.md` + AGENTS.md | MCP support shipped 2025; uses VS Code mcp config | |

**Dual-audience preserved?** Yes for all — rules files agent-only and invisible to humans; MCP servers don't affect CLI use.

**verify-kit ship?** AGENTS.md (always). CLAUDE.md (opt-in). `.cursor/rules/verify-kit.mdc` (opt-in). `.windsurfrules` (opt-in). Don't ship Zed/Continue/JetBrains specifics — those tools read AGENTS.md.

## 5. Machine-Readable Output Formats

| Format | Use for | Standard | verify-kit |
|---|---|---|---|
| **NDJSON / JSONL** | Streaming events (verify steps, eval rows, ralph progress) | Universal | **Default for `--format=jsonl`** |
| **JSON object** | Single-shot results (smoke, debug-state) | Universal | `--format=json` |
| **SARIF 2.1.0** | Code-quality findings, lints, security scans. Consumed natively by GitHub code-scanning, VS Code SARIF Viewer, Sonar, every linter | OASIS standard | `--format=sarif` for `verify` lint-style checks |
| **JUnit XML** | Test-style results — every CI renders it | de-facto universal | `--format=junit` for `verify`/`smoke` |
| **OpenTelemetry OTLP** | Traces — `trace --last` should emit OTLP so any OTel backend (Jaeger, Honeycomb, Grafana Tempo, Phoenix, Langfuse) consumes them | CNCF | `--format=otlp` for `trace` |
| **Cargo-style `--message-format=json`** | Stream of typed messages, `reason` field discriminates type | Rust ecosystem; good template | Inspiration for JSONL event shape |

**The isatty discipline:** When stdout is TTY → pretty + colors + spinners. When piped or `--format` set → structured. Same single binary. Never make humans pass `--pretty`; never make agents pass `--no-color --plain --quiet`.

## 6. Self-Describing Tool Patterns

From canonical "Rewrite your CLI for AI agents" (Justin Poehnelt):

- **`--describe` / `schema <subcommand>`** — dumps full param schema, request/response types, required scopes as JSON. Agents introspect at runtime instead of reading stale docs in system prompt
- **`--dry-run`** — validates locally, returns planned action as JSON without side effects. Safe for agents
- **`--params <json>`** — accept full payload as JSON for nested structures human flags can't express
- **`--fields <mask>`** — limit response size to protect context window
- **`--sanitize <template>`** — response filtering against prompt-injection from external content
- **`--page-all`** with NDJSON — stream pagination without buffering
- **Per-tool exit code discipline** — 0 = success; 1 = check failed (expected); 2 = invalid input; ≥10 = infrastructure problem. Agents can branch
- **Error envelope** — every error in `--json` mode is `{code, message, hint, fix_command?, docs_url}` so agent has fix path without re-prompting human
- **Input validation** — reject control chars, path traversal, embedded query params, double-encoding. Don't trust agent input

## 7. Permissions & Safety Boundaries

- Claude Code `permissions.{allow,ask,deny}` + auto-mode classifier
- Cursor/Zed per-tool approval (`agent.tool_permissions.default: "confirm" | "allow"`)
- **Read-only vs write-safe vs destructive** classification at MCP-tool level — convention: include `readOnlyHint`, `destructiveHint`, `idempotentHint` annotations on each MCP tool (per MCP spec). Agents and IDEs use to decide what to auto-approve
- `--dry-run` / `--check` everywhere fixes are proposed
- Sandboxing for "let agent run code": Modal, gVisor, Firecracker, Vercel Sandbox

## 8. Concrete Dual-Audience Exemplars

| Tool | Pattern worth stealing |
|---|---|
| **`gh`** | Pretty default, `--json field1,field2` with deterministic schema, `--jq` for inline filtering, `--template` for custom |
| **`cargo`** | `--message-format=json` streams typed compiler events with `reason` discriminator |
| **`rg` / `bat`** | isatty detection; `--json` emits per-match NDJSON |
| **`kubectl`** | `-o json|yaml|jsonpath=...|go-template=...`; same binary, every format |
| **`jq`** | TUI in `-C`, scriptable raw mode otherwise |
| **`pytest`** | `--junit-xml=out.xml` side-channel; pretty stdout untouched |
| **`eslint`** | `--format=sarif` / `--format=json` / `--format=stylish`; multiple formatters in tree |

The pattern: **pretty output is the side-effect; the structured payload is the contract.**

---

## Deliverable A — verify-kit "agent integration stack"

**Ship by default:**
- ✅ `verify-kit-mcp` MCP server binary (stdio transport). Single command: `verify-kit mcp serve`
- ✅ `AGENTS.md` (generated from template; project-specific build/test/conventions)
- ✅ `--format={pretty,json,jsonl,sarif,junit,otlp}` on every command. Default `pretty` when TTY, `jsonl` when piped
- ✅ `verify-kit describe [<command>]` — emits JSON schema of all commands, inputs, outputs, exit codes
- ✅ `verify-kit list-checks` — enumerable check inventory with IDs, severities, fix hints
- ✅ Error envelope `{code, message, hint, fix_command, docs_url}` in all JSON modes
- ✅ Exit-code contract: 0 ok, 1 check-failed, 2 bad-input, 10+ infra
- ✅ `--dry-run` on every mutating command
- ✅ MCP tool annotations (`readOnlyHint`, `destructiveHint`, `idempotentHint`)

**Opt-in via Copier prompts:**
- `has_claude_code` → generates `CLAUDE.md`, `.claude/settings.json.example`, `.claude/skills/verify-kit-*/SKILL.md`, optional `.claude/agents/verify-kit-fixer.md`, Stop hook script template
- `has_cursor` → `.cursor/rules/verify-kit.mdc`
- `has_windsurf` → `.windsurf/rules/verify-kit.md`
- `has_continue` → `.continue/mcpServers/verify-kit.json`
- `has_zed` → `.zed/settings.json` snippet with `context_servers` entry
- `has_jetbrains` → `.idea/mcp.xml` snippet
- `has_copilot` → `.github/copilot-instructions.md` pointer

**Document only:**
- HTTP transport for MCP server (only when teams host shared verify-kit). Provide `verify-kit mcp serve --http :7878` but don't suggest by default

**Adding new agent later** = drop one template file under `template/agents/<agent>/`. No verify-kit core update needed. MCP server + AGENTS.md + JSON output already work; per-agent files are sugar.

## Deliverable B — verify-kit MCP Server Spec

Every MCP tool has **CLI twin** with identical name (kebab→snake) and identical JSON output. MCP tool is thin wrapper that shells out and returns parsed JSON.

| MCP tool | Description | Input schema | Output | CLI twin | Annotations |
|---|---|---|---|---|---|
| **`verify`** | Run full verification harness | `{checks?: string[], format?: "json"\|"sarif"\|"junit", changed_only?: bool}` | `{status: "pass"\|"fail", failed: Check[], passed: int, duration_ms: int, sarif?: object}` | `verify-kit verify [--checks=a,b] [--format=…] [--changed]` | readOnly |
| **`verify_check`** | Run one named check in isolation | `{check_id: string, args?: object}` | `{check_id, status, message, hint?, fix_command?, evidence: object}` | `verify-kit verify --check=<id>` | readOnly |
| **`list_checks`** | Enumerate available checks | `{}` | `Check[] = {id, name, severity, category, description, fixable: bool}` | `verify-kit list-checks --format=json` | readOnly, idempotent |
| **`smoke`** | Fast end-to-end sanity | `{target?: "backend"\|"frontend"\|"all"}` | `{status, steps: Step[], duration_ms}` | `verify-kit smoke [--target=…]` | readOnly |
| **`trace_last`** | Retrieve last run trace | `{run_id?: string, format?: "json"\|"otlp"}` | `{run_id, spans: Span[], events: Event[], started_at, ended_at}` | `verify-kit trace --last [--format=…]` | readOnly, idempotent |
| **`debug_state`** | Current harness state | `{}` | `{env: object, config: object, queue: Item[], locks: Lock[], beads_state?: object}` | `verify-kit debug state --format=json` | readOnly, idempotent |
| **`debug_events`** | Stream recent events | `{since?: ISOString, limit?: int}` | `Event[] = {ts, level, source, message, data}` | `verify-kit debug events --since=… --format=jsonl` | readOnly |
| **`eval_run`** | Run evaluation suite | `{suite: string, model?: string, dataset?: string, dry_run?: bool}` | `{run_id, suite, scores: object, rows: int, duration_ms, artifact_path}` | `verify-kit eval run <suite> [--model=…] [--dry-run]` | destructive (writes artifacts); idempotent only with same seed |
| **`eval_compare`** | Diff two eval runs | `{baseline_run_id: string, candidate_run_id: string}` | `{deltas: Delta[], regressions: Row[], improvements: Row[], verdict: "better"\|"worse"\|"neutral"}` | `verify-kit eval compare <a> <b> --format=json` | readOnly, idempotent |
| **`ralph_run`** | Kick off long-running task | `{task: string, args?: object, dry_run?: bool}` | `{ralph_id, status: "queued"\|"running", started_at}` | `verify-kit ralph run <task> [--dry-run]` | destructive |
| **`ralph_status`** | Poll ralph state | `{ralph_id: string}` | `{ralph_id, status, progress: float, last_event, eta_seconds?}` | `verify-kit ralph status <id> --format=json` | readOnly |
| **`fix_propose`** | Given failed check, return suggested patch (no apply) | `{check_id: string, run_id?: string}` | `{check_id, patch: UnifiedDiff, rationale, confidence: float, fix_command?: string}` | `verify-kit fix propose <check_id> --format=json` | readOnly, idempotent |
| **`describe`** | Self-describe — schema of every tool and command | `{tool?: string}` | JSON Schema document | `verify-kit describe [<command>] --format=json` | readOnly, idempotent |

**Transport:** stdio by default. `--http :7878` available. Spawn via:
```json
{ "verify-kit": { "command": "verify-kit", "args": ["mcp", "serve"] } }
```

## Deliverable C — Dual-Audience Checklist

Every verify-kit feature must answer all six rows before shipping. If any cell blank, feature is incomplete.

| # | Audience question | Required answer |
|---|---|---|
| 1 | **Human in terminal sees:** | Pretty colorized output via `isatty(stdout)`; progress spinner; failed checks summarized with one-line `→ run: verify-kit fix propose <id>` next-action hint. No JSON unless `--format=json` requested |
| 2 | **Human in VS Code / IDE sees:** | SARIF problems in Problems panel (via `--format=sarif` written to `.verify-kit/results.sarif`). JUnit results render in test-explorer panes. No agent involvement required |
| 3 | **Agent calling programmatically gets:** | Deterministic JSON/JSONL with stable schema (introspectable via `describe`). Error envelope `{code, message, hint, fix_command, docs_url}`. Exit code semantically meaningful (0/1/2/10+). No ANSI escapes, no spinners |
| 4 | **Agent has a fix path:** | Failed check returns `fix_command` (concrete CLI to run) and/or `fix_propose` MCP tool returns unified diff with rationale. Agent can call `verify_check` again to confirm. No human round-trip for routine fixes |
| 5 | **Human can override agent:** | Every agent-suggested fix is `--dry-run`-able. Destructive MCP tools annotated `destructiveHint: true` so IDEs prompt. Stop-hook on verification can be skipped with documented escape hatch (`VERIFY_KIT_SKIP=1` env var). Audit log of agent-initiated runs in `.verify-kit/audit.jsonl` |
| 6 | **Both can collaborate mid-flow:** | Same `verify-kit trace --last` works for both: agent reads JSON to plan next fix; human reads pretty timeline to understand what agent did. State (queue, locks, last run) file-backed in `.verify-kit/`, so human can `cat`/inspect while agent mid-run |

**The discipline:** if a feature degrades either audience's experience, redesign. Adding `--format=json` is never enough — human view must also stay first-class. Removing a spinner because "agents don't need it" is regression for humans.

## Sources

- [The 2026 MCP Roadmap](https://blog.modelcontextprotocol.io/posts/2026-mcp-roadmap/)
- [MCP Specification 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25)
- [MCP Transports Spec](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)
- [stdio vs Streamable HTTP — choosing the right MCP transport](https://kirkryan.co.uk/stdio-vs-streamable-http-choosing-the-right-mcp-transport/)
- [FastMCP (jlowin/fastmcp)](https://github.com/jlowin/fastmcp)
- [FastMCP 3.0 GA announcement](https://jlowin.dev/blog/fastmcp-3-launch)
- [AGENTS.md spec site](https://agents.md/)
- [AGENTS.md vs CLAUDE.md cross-tool standard](https://hivetrail.com/blog/agents-md-vs-claude-md-cross-tool-standard)
- [OpenAI Codex — Custom instructions with AGENTS.md](https://developers.openai.com/codex/guides/agents-md)
- [MCP Setup Guide for Cursor / Claude Code / VS Code / Windsurf](https://chatforest.com/guides/mcp-setup-ai-coding-tools/)
- [JetBrains MCP Server (2025.2+)](https://www.jetbrains.com/help/idea/mcp-server.html)
- [Zed — Model Context Protocol docs](https://zed.dev/docs/ai/mcp)
- [Continue.dev MCP setup](https://docs.continue.dev/customize/deep-dives/mcp)
- [Claude Code Hooks reference](https://code.claude.com/docs/en/hooks)
- [Claude Code Skills](https://code.claude.com/docs/en/skills)
- [Claude Code Permissions](https://code.claude.com/docs/en/permissions)
- [Cursor Rules docs](https://cursor.com/docs/context/rules)
- [Rewrite Your CLI for AI Agents (Justin Poehnelt)](https://justin.poehnelt.com/posts/rewrite-your-cli-for-ai-agents/)
- [rustc JSON output](https://doc.rust-lang.org/rustc/json.html)
- [Cargo External Tools (--message-format=json)](https://doc.rust-lang.org/cargo/reference/external-tools.html)
- [SARIF — complete guide (Sonar)](https://www.sonarsource.com/resources/library/sarif/)
- [Agentic AI Foundation (Linux Foundation)](https://intuitionlabs.ai/articles/agentic-ai-foundation-open-standards)

## Related notes

- [[wave-4-fastapi-ecosystem]] · [[wave-4-ai-sdk-ergonomics]] · [[wave-3-vscode-ide]]
- [[wave-5-claude-codex-mechanics]] · [[wave-5-gsd-autonomous]]
- [[00-architecture-overview]] · [[00-stack-decisions]] · [[00-autonomous-workflow]]
