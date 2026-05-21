---
title: mise
aliases: [mise-en-place, rtx]
tags: [verify-kit, tools, toolchain, universal-foundation]
created: 2026-05-18
status: ALWAYS-SHIP
layer: Universal Foundation
phase_introduced: Phase 1
---

# 🧰 mise

> [!abstract] One-line summary
> Polyglot toolchain manager + task runner — single `.mise.toml` declares both language versions and runnable tasks.

## What it does

`mise` (originally `rtx`) is asdf-compatible but written in Rust. It manages tool versions across languages (Python, Node, Go, Rust, Ruby, etc.) via a per-project `.mise.toml`. Running `mise install` from a fresh checkout brings the user up to the declared versions without polluting global state. It can also run named tasks, but in verify-kit we delegate that responsibility to `just` (see [[tools/just]]).

## Why we picked it

| Alternative | Why rejected |
|---|---|
| `pyenv` + `nvm` + `rbenv` + ... | Per-language tools fragment bootstrap; one config beats many |
| `asdf` | mise is asdf-compatible, faster, better DX |
| `volta` | Node-only |
| Bazel / Pants | Massive overkill for solo + small-team |
| Nx / Turborepo | JavaScript-shaped; wrong fit for polyglot |
| Dagger | Docker-heavy; learning curve doesn't pay back at solo scale |

**Decisive factor:** verify-kit must work for Python + Node + GDScript + bash from day one. mise's single-file polyglot story is the only thing that scales without bootstrap pain.

See [[agent-reports/wave-2-polyglot-orchestration]] for the full comparison.

## Usage in verify-kit

Generated project's `.mise.toml` (from `template/.mise.toml.jinja2`):

```toml
[tools]
python = "3.13"
node = "24"
uv = "latest"
just = "latest"
pnpm = "latest"

[env]
PYTHONDONTWRITEBYTECODE = "1"
```

Consumers run `mise install` once after `copier copy`; subsequent shells auto-activate the declared versions via `mise activate <shell>`.

## Install (for verify-kit consumers)

```bash
# macOS
brew install mise

# Linux / universal
curl https://mise.run | sh

# Activate in shell (one-time):
echo 'eval "$(mise activate bash)"' >> ~/.bashrc   # or zsh
```

## Gotchas

> [!warning] Bootstrap chicken-and-egg
> `mise` itself must be installed by the consumer BEFORE `copier copy` works (Copier itself doesn't depend on mise, but `just verify` does). Document the install in the consumer README's Quickstart.

- `mise install` reads `.mise.toml` and pulls every declared tool — first install can take a minute. Subsequent calls are no-ops.
- `mise exec -- <cmd>` runs a command with the env applied without activating the shell — useful in CI.
- `[env]` block in `.mise.toml` works like `.envrc` for direnv users; respects `PATH` injection.
- The `tools.uv = "latest"` style follows the latest stable; pin a specific version if reproducibility matters.

## Key docs

- Getting started: <https://mise.jdx.dev/getting-started.html>
- `.mise.toml` reference: <https://mise.jdx.dev/configuration.html>
- Tasks (we don't use these — `just` is the task runner): <https://mise.jdx.dev/tasks/>
- Dev Containers feature: <https://github.com/jdx/mise-dev-container>

## Related notes

- [[00-stack-decisions#Universal Foundation — ALWAYS SHIP]] — verdict + role
- [[00-decision-log]] — D-004 records the decision (mise + Python helper, with Just as task runner)
- [[agent-reports/wave-2-polyglot-orchestration]] — full polyglot comparison
- [[tools/just]] — what mise's task runner role was delegated to
