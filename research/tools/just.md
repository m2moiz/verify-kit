---
title: just
aliases: [justfile, casey/just]
tags: [verify-kit, tools, task-runner, universal-foundation]
created: 2026-05-18
status: ALWAYS-SHIP
layer: Universal Foundation
phase_introduced: Phase 1
---

# ⚡ just

> [!abstract] One-line summary
> Command runner with cleaner syntax than Make — recipes can be any language, `just --list` is the discoverability surface.

## What it does

`just` reads a `justfile` (or `Justfile`) with named recipes. Each recipe is a list of shell commands (or any interpreter via shebang). `just <name>` runs the recipe. `just --list` prints all recipes with their docstring comments — the canonical "what can I do here?" question.

## Why we picked it

| Alternative | Why rejected |
|---|---|
| Make | Tab-vs-space hostility; `.PHONY` boilerplate; arcane syntax |
| Task (taskfile.dev) | YAML-heavy; verbose; Go ecosystem coupling |
| npm scripts | JS-only; not polyglot |
| mise tasks | Confined to mise; less portable to non-mise users (Makefile shim wouldn't help) |
| bash scripts in `scripts/` | No discoverability; no docstring convention; no `--list` |

**Decisive factor:** the `just verify` invocation is the trust anchor of the entire verify-kit design — see [[00-architecture-overview#Trust anchor]]. Make's syntax would be hostile to the dual-audience checklist (row 1: human can type it without docs).

See [[agent-reports/wave-2-polyglot-orchestration]] for the comparison.

## Usage in verify-kit

Phase 1 ships a working-only `template/justfile.jinja2` (Area 3: no stub recipes). The Phase 1 set:

```just
# Run all verification checks for the project
verify *FLAGS:
    uv run verify-kit verify {% raw %}{{FLAGS}}{% endraw %}

# Run linters (ruff for Python, biome for JS/TS) over the project
lint:
    uv run ruff check .
    @command -v pnpm >/dev/null 2>&1 && pnpm dlx @biomejs/biome check . || true

# Auto-format Python and JS/TS
format:
    uv run ruff format .
    @command -v pnpm >/dev/null 2>&1 && pnpm dlx @biomejs/biome format --write . || true

# Drop into a subshell with the mise-managed env activated
shell:
    mise exec -- $SHELL
```

Phase 2 adds `verify --quick`, `verify --full`, `verify-clean`, `trace-up`, `trace-down`, `trace --last`. Each phase adds only what works in that phase.

## Install (for verify-kit consumers)

```bash
# Easiest: via mise (already required)
mise use -g just@latest

# macOS direct
brew install just

# Linux direct
curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh \
  | bash -s -- --to ~/.local/bin
```

## Gotchas

> [!warning] Empirically verified
> See [[synthesis/session-2026-05-18-phase-1-and-2-buildout#^M-3]] — Codex flagged `just verify --fix` as broken (claiming Just intercepts `--flag` tokens). It does NOT in just 1.51. The variadic `*FLAGS` pattern captures `--fix` correctly without a `-- --fix` separator.

- **Shell defaults to `sh -cu`** — set `set shell := ["bash", "-uc"]` at the top of the justfile for strict-mode bash with proper error propagation.
- **Variadic `*FLAGS` works** — `just verify --fix --check input.py` captures the rest as a space-joined string. Use `{% raw %}{{FLAGS}}{% endraw %}` in Copier templates to pass the literal `{{FLAGS}}` through to the rendered justfile.
- **Recipe docstrings** — comments on the line directly above a recipe become its `just --list` description. Use them.
- **Working-only justfile** — verify-kit's Area 3 decision: ship only recipes that work this phase. Stub recipes pollute `just --list` and lie to users.

## Key docs

- Manual: <https://just.systems/man/en/>
- Variadic recipes: <https://just.systems/man/en/variadic-arguments.html>
- Settings: <https://just.systems/man/en/settings.html>

## Related notes

- [[00-stack-decisions#Universal Foundation — ALWAYS SHIP]] — verdict + role
- [[00-decision-log]] — D-004 records the mise+just split
- [[agent-reports/wave-2-polyglot-orchestration]] — full task-runner comparison
- [[tools/mise]] — what manages just's installation across machines
- [[00-architecture-overview#Trust anchor]] — why `just verify` is THE invocation
