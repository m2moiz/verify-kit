---
title: VS Code & IDE Integration Patterns
aliases: [Wave 3 - VS Code, IDE Integration, LSP DAP MCP]
tags: [research, wave-3, vscode, ide, lsp, dap, jetbrains, zed]
wave: 3
source_agent: vscode-ide
created: 2026-05-17
---

# Making a Project a First-Class IDE Citizen — Research for verify-kit

> [!abstract] Headline
> **Commit to LSP/DAP-first tooling and everything else falls into place** — Ruff, Pyright, Biome, debugpy speak LSP/DAP so VS Code, JetBrains, Zed, and Neovim all get IDE features for free. Ship four small `.vscode/` files (extensions, settings, tasks, launch) as a courtesy. Custom problem matchers for ruff/mypy make `just verify` errors clickable. **Devcontainer = opt-in, not default**.

## 1. VS Code Tasks (`.vscode/tasks.json`)

- **Link:** https://code.visualstudio.com/docs/debugtest/tasks · https://code.visualstudio.com/docs/reference/tasks-appendix
- **What:** Wraps shell commands (`just verify`, `make smoke`, `npm test`) as VS Code tasks invokable via `Ctrl/Cmd+Shift+B`, `Tasks: Run Task`, or as `preLaunchTask` for debug. `group: { kind: "test", isDefault: true }` wires task to `Tasks: Run Test Task`.

**Key 2025 conventions:**
- **`presentation`:** `panel: "dedicated"` (each task own terminal), `reveal: "silent"` for lint/type-check (only surface on error), `reveal: "always"` for build/test, `clear: true` to wipe stale output
- **`isBackground: true`** for dev servers; pair with background problem matcher pattern (`beginsPattern`/`endsPattern`) so VS Code knows when "ready"
- **Compound tasks:** task with only `dependsOn` and no `command` acts as orchestrator. `dependsOrder: "sequence"` for sequential, omit for parallel — perfect for `verify` = lint + typecheck + test in parallel
- **`problemMatcher`** is load-bearing field — see §6

**Setup:** Low. One file.
**Scope:** VS Code only (Zed reads subset; JetBrains/Neovim ignore).
**Fit:** **Excellent.** Single biggest UX win for VS Code users.
**Catch:** Cursor/Windsurf/Zed read tasks.json with varying fidelity. Don't put critical-path logic in tasks.json — keep in justfile/Makefile and delegate.

## 2. VS Code Launch / Debug (`.vscode/launch.json`) + DAP

- **Link:** https://code.visualstudio.com/docs/debugtest/debugging-configuration · https://microsoft.github.io/debug-adapter-protocol/
- **What:** Defines debug sessions for `debugpy` (Python), `node`/`pwa-chrome` (JS), attach-to-process. **`compounds`** launches multiple configs in parallel — canonical FastAPI+Next.js dual-debug pattern. `preLaunchTask` chains tasks.json task before debugger attaches; `serverReadyAction` detects "ready on port X" and auto-opens browser with debugger attached (needed for Next.js 14+).

**DAP (Debug Adapter Protocol):** M+N standard for debuggers (LSP analog). Any DAP-speaking debugger (`debugpy`, `js-debug`, `gdb` native DAP shipped 2024) works in VS Code, JetBrains Fleet, Zed, Neovim (via `nvim-dap`). Write debug adapter once → IDE-agnostic debugging.

**Setup:** Medium. Compound configs need both halves working independently first.
**Scope:** launch.json = VS Code; underlying DAP = cross-editor.
**Fit:** **Good.** Ship minimal launch.json for common shapes (FastAPI uvicorn, Node script, pytest current file, attach-to-process). Document that debug *adapters* (debugpy) are what actually matter.
**Catch:** Next.js debugging has rough edges across versions. JetBrains rebuilds entire IDE-debugger story per-IDE; launch.json not portable.

## 3. VS Code Test API (Testing Sidebar)

- **Link:** https://code.visualstudio.com/docs/debugtest/testing · https://code.visualstudio.com/api/extension-guides/testing
- **What:** The `TestController` API powers Testing sidebar (run/debug single test, run-all, watch, coverage, inline pass/fail icons). Test discovery is extension-provided: **Python extension** auto-discovers pytest if `python.testing.pytestEnabled=true`; **Vitest extension** discovers `*.test.ts` automatically; **Jest**, **Playwright**, **Go**, **Rust** all have extensions implementing `TestController`.

**Coverage API:** added April 2024 — extensions can now feed coverage data directly into gutters via native test API instead of relying on `Coverage Gutters`. Pytest-cov + Python extension and Vitest + its extension both consume this.

**What makes project "discoverable":**
- pytest: just have `pytest` installed and tests named `test_*.py` / `*_test.py`; ship `pytest.ini` or `[tool.pytest.ini_options]` in `pyproject.toml`
- vitest: have `vitest` in `package.json` and `vitest.config.ts`
- settings.json should opt-in: `"python.testing.pytestEnabled": true`, `"python.testing.unittestEnabled": false`

**Fit:** **Excellent** — but win comes from clean pyproject.toml/vitest.config, not VS Code-specific files.

## 4. Devcontainers (`.devcontainer/devcontainer.json`)

- **Link:** https://containers.dev/ · https://containers.dev/features
- **What:** Reproducible Docker-based dev env. Spec is open and now supported by **VS Code, JetBrains, Zed (v0.218+), GitHub Codespaces, DevPod**. Features = composable, versioned OCI packages. Lifecycle: `onCreate` (image build), `postCreate` (deps install, once), `postStart` (every container start), `postAttach` (every IDE attach).

**2025 reality:**
- Spec mature; feature ecosystem broad
- Zed support exists but extension management in containers still WIP
- Codespaces adoption: real in OSS-onboarding and enterprise; less universal for solo
- DevPod gives Codespaces-like workflow on any cloud/local

**Setup:** Medium. Designing good devcontainer real work; debugging container-vs-host networking eats hours.
**Scope:** Cross-IDE (VS Code, JetBrains, Zed all read same file).
**Fit:** **Marginal-to-good as opt-in; bad as mandatory.** Fantastic safety net for "clone-and-run" demos but adds friction for "I already have Python installed" majority.

## 5. VS Code Settings + `extensions.json`

- **Canonical:** https://code.visualstudio.com/docs/getstarted/settings

**Safe-to-commit settings:**
- `"editor.formatOnSave": true` + `"[python]": { "editor.defaultFormatter": "charliermarsh.ruff" }` etc
- `"editor.rulers": [100]`, `"files.insertFinalNewline": true`, `"files.trimTrailingWhitespace": true`
- `"python.testing.pytestEnabled": true`, `"python.analysis.typeCheckingMode": "basic"`
- `"typescript.tsdk": "node_modules/typescript/lib"`
- `"search.exclude"`, `"files.watcherExclude"` for `node_modules`, `.venv`, build artifacts

**Do NOT commit:** theme, font, keybindings, telemetry, window layout, anything personal.

**`extensions.json`:** `recommendations` array prompts users on workspace open ("This project recommends installing N extensions"). Massive UX win for ~5 lines of JSON.

**Fit:** **Excellent — ship both.**

## 6. Problem Matchers — Clickable Errors

- **Canonical:** https://code.visualstudio.com/docs/reference/tasks-appendix
- **What:** Regex over task output; capture groups for `file`, `line`, `column`, `severity`, `message` populate Problems panel with **clickable** items. Single best ergonomic feature of tasks.json.

**Built-ins:** `$tsc`, `$tsc-watch`, `$eslint-stylish`, `$eslint-compact`, `$go`, `$msCompile`, `$python` (limited).

**Custom for verify-kit's typical stack:**
- **Ruff** (`ruff check --output-format=concise`): pattern `^(.*?):(\d+):(\d+):\s+(\w+)\s+(.*)$`
- **Mypy** (`--show-column-numbers --no-error-summary`): pattern `^(.+?):(\d+):(\d+):\s+(error|warning|note):\s+(.*)$`
- **Pytest:** lean on Python extension's TestController; for raw output, match traceback `^\s*File "(.+?)", line (\d+)`
- **Vitest/tsc** already covered by `$tsc` or Vitest extension

JSON-escape backslashes (`\\d`). Ship custom matchers in tasks.json so even users without Ruff/Mypy extensions get clickable errors.

**Fit:** **Excellent.** What makes `just verify` feel native.

## 7. Editor-Agnostic Conventions (LSP, .editorconfig, .gitattributes, pre-commit)

**LSP (Language Server Protocol):** M+N standard. Same `pyright`/`ruff-lsp`/`biome`/`rust-analyzer`/`gopls` powers every editor. **This is the single most important thing for cross-IDE parity — pick LSP-aware tools and you get IDE features everywhere for free.**

**`.editorconfig`** (https://editorconfig.org): 4M+ downloads on VS Code extension; native support in JetBrains, Visual Studio 2026, GitHub web UI, GitLab. Covers indent, line endings, charset, trim whitespace, final newline. **Ship it.**

**`.gitattributes`:** lock `* text=auto eol=lf`, mark binary assets, configure linguist language detection, set merge/diff drivers for lockfiles. Prevents CRLF chaos on Windows.

**`pre-commit`** (https://pre-commit.com): Python-based hook framework, IDE-agnostic, runs on commit + CI. Ship `.pre-commit-config.yaml` with ruff, prettier/biome, editorconfig-checker, end-of-file-fixer, trailing-whitespace, check-yaml.

**Fit:** **Excellent — all four are no-brainers.**

## 8. JetBrains / Zed / Neovim Parity

**The 80/20:**
- LSP-aware tools → 80% of IDE features for free everywhere
- `.editorconfig` + `.gitattributes` + `pre-commit` → formatting/style parity
- `pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod` → test/run discovery in every IDE
- devcontainer.json → cross-IDE reproducible env

**Where you have to ship per-IDE config:** debug configs (launch.json ↔ JetBrains run configs ↔ `nvim-dap` ↔ Zed debug). No standard. Document *debug recipe* in README; only ship VS Code version.

**Zed** reads tasks via `.zed/tasks.json` (similar shape to VS Code's but not identical), supports devcontainers, speaks LSP+DAP. **Don't ship `.zed/`** unless Zed is primary target.

**JetBrains** uses `.idea/` (do **not** commit personal pieces; `.idea/runConfigurations/*.xml` is the shareable subdirectory). Most teams .gitignore whole `.idea/`.

**Neovim:** no project config to ship. Users carry own. Just expose clean LSP/DAP-compatible tooling.

## 9. The Standardization Story (LSP / DAP / MCP)

- **LSP (2016):** language features (hover, complete, goto-def, diagnostics, formatting). Mature, universal
- **DAP (2017):** debugging UI. Now mature; GDB shipped native DAP in 2024
- **MCP (2024, Anthropic):** Model Context Protocol — exposes tools/resources/prompts to LLMs. Overlaps IDE story (Cursor, Zed, Continue.dev, JetBrains AI support it). For verify-kit, small MCP server exposing `verify`, `smoke`, `eval` as MCP tools would make harness usable by any LLM-capable IDE without bespoke integration

The pattern: **expose your tool through open protocol and every editor gets it for free.** verify-kit's CLI should be source of truth; everything else (tasks.json, JetBrains run configs, MCP tools) is thin adapter.

## 10. "Great IDE Feel" From Beloved Projects

- **Cargo/rust-analyzer:** one project layout convention (`Cargo.toml`), one formatter (`rustfmt`), one LSP. Works identically in every editor. Lesson: **convention > configuration**.
- **pnpm workspaces:** `pnpm-workspace.yaml` + standard `package.json` `scripts` → every IDE picks them up (VS Code's npm script lens, JetBrains npm tool window, Zed task discovery). Lesson: **use ecosystem's standard manifest, not custom one**.
- **Vite HMR:** zero config in IDE — works because dev server speaks browser-native ESM and IDE doesn't need to know. Lesson: **don't require IDE to do work runtime can do**.
- **uv/ruff (Astral):** single tool, single config (`pyproject.toml`), LSP-first design. Reason they feel "native" is they don't *need* IDE-specific config. Lesson: **LSP-first tools win**.

## Recommendations

### (A) `.vscode/` files to ship by default

Four files, all minimal:

1. **`.vscode/extensions.json`** — recommend workspace's tool extensions:
   ```json
   {
     "recommendations": [
       "charliermarsh.ruff", "ms-python.python", "ms-python.vscode-pylance",
       "ms-python.debugpy", "esbenp.prettier-vscode", "biomejs.biome",
       "vitest.explorer", "editorconfig.editorconfig", "skellock.just",
       "tamasfe.even-better-toml", "redhat.vscode-yaml"
     ]
   }
   ```

2. **`.vscode/settings.json`** — project needs only:
   ```json
   {
     "editor.formatOnSave": true, "editor.rulers": [100],
     "files.insertFinalNewline": true, "files.trimTrailingWhitespace": true,
     "[python]": { "editor.defaultFormatter": "charliermarsh.ruff" },
     "[typescript]": { "editor.defaultFormatter": "biomejs.biome" },
     "python.testing.pytestEnabled": true, "python.testing.unittestEnabled": false,
     "python.analysis.typeCheckingMode": "basic",
     "search.exclude": { "**/.venv": true, "**/node_modules": true, "**/dist": true }
   }
   ```

3. **`.vscode/tasks.json`** — delegate to justfile, attach problem matchers:
   - `verify` (default build, `Ctrl+Shift+B`) → `just verify`, compound `dependsOn: [lint, typecheck, test]`
   - `lint`, `typecheck`, `test`, `smoke`, `eval` → each `just <name>` with `presentation: { reveal: "silent" }` for lint/typecheck and custom problem matchers for ruff/mypy/tsc
   - `dev` (background) → `just dev` with `isBackground: true`
   - One task is default test task (`group: { kind: "test", isDefault: true }`)

4. **`.vscode/launch.json`** — three configs + one compound:
   - "Debug Pytest (current file)" — debugpy on `${file}`
   - "Debug Backend (uvicorn)" — debugpy module uvicorn with `serverReadyAction`
   - "Debug Frontend (Next.js)" — pwa-chrome attach
   - Compound: "Debug Full Stack" → both backend + frontend

### (B) Editor-agnostic conventions

Ship all five:

1. **`.editorconfig`** — indent (4 for py, 2 for ts/json/yaml), `end_of_line = lf`, `charset = utf-8`, `insert_final_newline = true`, `trim_trailing_whitespace = true`
2. **`.gitattributes`** — `* text=auto eol=lf`, mark binaries, `*.lock binary`
3. **`.pre-commit-config.yaml`** — ruff, biome/prettier, editorconfig-checker, end-of-file-fixer, trailing-whitespace, check-yaml, check-added-large-files
4. **LSP-first tooling baked into config:** Ruff, Pyright, Biome, rust-analyzer — never legacy tools (flake8, eslint-without-flat-config) for new projects
5. **`pyproject.toml` / `package.json`** as single source of truth — test discovery, formatter rules, lint rules all there, NOT `.vscode/`

### (C) Making `just verify` feel native in VS Code

Three concrete moves:

1. **One-keypress run:** mark verify task as `group: { kind: "build", isDefault: true }` → `Ctrl/Cmd+Shift+B` runs full harness. No memorization.
2. **Clickable errors:** ship custom problem matchers for ruff (`^(.*?):(\d+):(\d+):\s+(\w+)\s+(.*)$`) and mypy. Errors land in Problems panel and jump-to-source on click. Highest-leverage piece.
3. **Native test sidebar:** rely on Python extension + Vitest extension (recommended via extensions.json) to populate Testing sidebar from `pytest`/`vitest`. Run-single-test, debug-test, watch-mode, coverage gutters all come free via Test API + 2024 coverage API.

### (D) Devcontainer: opt-in, not default

**Opinion: opt-in.** Ship working `.devcontainer/devcontainer.json` in `templates/devcontainer/` directory with one-line `just devcontainer-init` to copy into place, but do **not** put in root by default.

Reasoning:
- Devcontainers solve "I don't have Python/Node installed" — real but minority problem for harness audience
- They impose Docker as hard dependency, slow first-run by minutes, rough edges on Apple Silicon, corporate VPNs, offline use
- Codespaces adoption in 2025 real-but-not-universal
- They genuinely help: hackathon demos, OSS onboarding, locked-down enterprise. Hence opt-in
- Base template should assume `uv`/`pnpm`/`just` work on host; devcontainer template wraps for users who need it

## Honest summary

Single highest-leverage decision is **commit to LSP/DAP-first tooling** (Ruff, Pyright, Biome, debugpy, js-debug). Everything else — tasks.json, launch.json, extensions.json — is thin per-IDE adapter. If verify-kit's CLI is clean, its `pyproject.toml`/`package.json` are clean, and tools speak LSP/DAP, then VS Code feels native, JetBrains feels native, Zed feels native, Neovim power users happy.

Ship four `.vscode/` files as courteous default for 70% on VS Code; ship `.editorconfig` + `.gitattributes` + `.pre-commit-config.yaml` for everyone; leave devcontainer as opt-in; document JetBrains/Zed/Neovim equivalence map in README.

## Sources

- [VS Code Tasks docs](https://code.visualstudio.com/docs/debugtest/tasks)
- [VS Code tasks appendix (problem matchers)](https://code.visualstudio.com/docs/reference/tasks-appendix)
- [Aleksandrov: launch.json & tasks.json ultimate guide (2025)](https://www.mykolaaleksandrov.dev/posts/2025/08/vscode-launch-and-tasks-ultimate/)
- [Allison Thackston — VSCode Tasks Problem Matchers](https://www.allisonthackston.com/articles/vscode-tasks-problemmatcher.html)
- [Heap — Getting started with problem matchers](https://michaelheap.com/getting-started-problem-matchers/)
- [Mamezou — Problem matcher explanation (2025)](https://developer.mamezou-tech.com/en/blogs/2025/01/24/vscode-problemmatcher/)
- [VS Code Debug Configuration](https://code.visualstudio.com/docs/debugtest/debugging-configuration)
- [DAP overview](https://microsoft.github.io/debug-adapter-protocol/overview)
- [GDB DAP coverage 2024](https://markaicode.com/gdb-dap-protocol-ide-integration/)
- [nvim-dap](https://github.com/mfussenegger/nvim-dap)
- [VS Code Testing docs](https://code.visualstudio.com/docs/debugtest/testing)
- [Vitest VS Code extension](https://github.com/vitest-dev/vscode)
- [VS Code 1.88 test coverage API](https://devclass.com/2024/04/08/vs-code-updated/)
- [containers.dev](https://containers.dev/)
- [containers.dev — Features](https://containers.dev/features)
- [Ivan Lee — Devcontainers in 2025](https://ivanlee.me/devcontainers-in-2025-a-personal-take/)
- [Zed Dev Containers docs](https://zed.dev/docs/dev-containers)
- [Microsoft vscode repo .vscode/extensions.json](https://github.com/microsoft/vscode/blob/main/.vscode/extensions.json)
- [DEV — Recommend VS Code extensions to teammates](https://dev.to/askrishnapravin/recommend-vs-code-extensions-to-your-future-teammates-4gkb)
- [EditorConfig](https://editorconfig.org/)
- [LSP official site](https://microsoft.github.io/language-server-protocol/)
- [LSP changed everything](https://unixy.io/blog/lsp-changed-everything/)
- [rust-analyzer](https://rust-analyzer.github.io/)
- [Rust in VS Code](https://code.visualstudio.com/docs/languages/rust)

## Related notes

- [[wave-3-human-friendly-logging]] · [[wave-3-ease-of-use]] · [[wave-4-mcp-agent-integration]]
- [[00-architecture-overview]] · [[00-stack-decisions]]
