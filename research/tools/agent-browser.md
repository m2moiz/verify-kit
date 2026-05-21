---
title: agent-browser
aliases: [vercel agent-browser]
tags: [verify-kit, tools, browser-automation, coordination]
created: 2026-05-18
status: COORDINATION-TOOL
layer: cross-project (not generated)
---

# 🌐 agent-browser

> [!abstract] One-line summary
> Native Rust browser-automation CLI from Vercel Labs — 200-400 tokens per snapshot vs ~10-15K for Playwright MCP.

## What it does

Drives a Chromium-based browser via a single binary CLI. Snapshots return numbered refs (`@e1`, `@e2`) keyed to interactive elements, stable across layout reflows. `screenshot --annotate` overlays the refs visually for multimodal review.

## Why we picked it

The Vercel Labs binary is the canonical "let an agent click around a web app" tool because:

- ~93% token reduction vs Playwright MCP for the same workflow
- Stable `@eN` refs survive layout changes (CSS selectors don't)
- Single Rust binary, no Node/Playwright/Chromium fragility
- `--annotate` overlay = multimodal-friendly snapshots

| Alternative | Why rejected (as default) |
|---|---|
| Playwright MCP | Massive token cost per snapshot |
| Puppeteer | Deprecated, less stable; Playwright superseded |
| Raw Playwright API | Brittle selectors; no agent-friendly ref system |

Playwright as a library still wins for cross-browser test suites; agent-browser is the day-to-day driving tool.

See [[agent-reports/wave-1-general-verification-harnesses]].

## Usage

```bash
# Required first command per session (canonical reference)
agent-browser skills get core --full

# Core loop
agent-browser open https://example.com
agent-browser snapshot -i              # numbered @e1, @e2 refs
agent-browser click @e3
agent-browser snapshot -i              # re-snapshot after any change
agent-browser screenshot --annotate map.png
agent-browser close
```

## Usage in verify-kit

Phase 4 (web add-on, v0.2) will plug agent-browser into the Playwright config alongside `@axe-core/playwright` for accessibility tests. Pre-v0.1 it's the default browser driver for ad-hoc UI inspection during phase verification.

## Install

```bash
# Homebrew (macOS)
brew install vercel/agent-browser/agent-browser

# Direct binary download
curl -fsSL https://agentbrowser.com/install.sh | sh
```

## Gotchas

- **Refs go stale after page change** — always re-snapshot before the next interaction
- **`close --all` vs `close`** — `--all` closes every running browser; `close` just the current session
- **No background mode** — agent-browser drives a visible browser by default. Useful for verification; doesn't suit headless CI (use Playwright there)

## Key docs

- Source: <https://github.com/vercel/agent-browser>
- Skills reference: `agent-browser skills get core --full`

## Related notes

- [[agent-reports/wave-1-general-verification-harnesses]] — discovery context
- [[00-stack-decisions#Universal Foundation — ALWAYS SHIP]] — browser-automation slot
- Memory note `tool_preferences` — replaces Puppeteer / Playwright-MCP as default
