<!-- GSD:project-start source:PROJECT.md -->

## Project

**verify-kit**

verify-kit is a reusable Copier-based scaffold template that bundles a self-verifiable agentic-coding harness for any new software project. It exists because Claude Code (and any autonomous coding agent) is half-blind — it cannot click buttons, hear audio, or watch a game render in real time — so without explicit feedback loops baked into a project from day one, "done" claims are unfounded and the developer becomes the QA function. verify-kit ships a project skeleton where every feature is verifiable end-to-end without human intervention: structured logs, dev-only debug endpoints, headless browser smoke tests, audio round-trip checks, LLM eval gates, and a single `just verify` ground-truth command.

The target user is a solo developer or small team building AI-heavy applications who wants Claude Code to self-verify changes before declaring them complete. The deliverable is a Copier template repo (not a CLI, not a SaaS) consumed via `copier copy gh:m2moiz/verify-kit my-new-project`.

**Core Value:** A solo developer can drop verify-kit into a new project in one command, answer a handful of prompts about which add-ons they need (web/game/audio/llm/backend), and end up with a project where `just verify` is the ground truth Claude Code uses to know whether work is actually done — no broken buttons, no dead audio, no silently-failing AI calls slipping past as "complete."

### Constraints

- **Polyglot**: Must work for projects in Python, TypeScript/JavaScript, GDScript, bash — and accommodate future additions (Go, Rust). Rules out single-language-only orchestrators like `npm create` and `uv init`.
- **Bootstrap minimalism**: A consumer should need only `mise` (auto-installs Python/Node/Godot per `.mise.toml`) + `git` to be productive. Rules out heavy bootstrap like Bazel or full devcontainer mandatory.
- **Updatability**: Template improvements must flow into already-scaffolded downstream projects via `copier update`. Rules out one-shot tools like degit, Yeoman, and GitHub "Use this template" button.
- **CI**: GitHub Actions is the only target. `act` for local runs. Multi-CI portability is explicitly rejected as premature.
- **Hosting (LLM observability)**: One personal Langfuse instance, starting on free Cloud Hobby tier (50k events/mo), migration path to self-hosted Hetzner CX32 (~€7.60/mo) when outgrown. Rules out per-project SQLite, Helicone proxy, Phoenix.
- **License**: MIT (intended OSS portfolio piece on GitHub).
- **Solo-dev scope**: Portfolio quality, not enterprise polish. Cost-conscious. Should not require any paid SaaS to run the v0.1 template.
- **Verification of the verifier**: Every change to the template must be smoke-tested by re-running `copier copy` onto a scratch directory and confirming `just verify` runs green. The template's own CI runs this on every PR.

<!-- GSD:project-end -->

<!-- GSD:stack-start source:STACK.md -->

## Technology Stack

Technology stack not yet documented. Will populate after codebase mapping or first phase.
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.

## Cross-Plan Contract Patterns

Before any planning, review, or replan operation in this project, treat `.planning/REVIEW-CHECKLIST.md` as required reading. It accumulates project-specific patterns (cwd leaks, dead-code-via-narrative-ordering, cross-plan contract drift, etc.) that human review has caught and that future automated review should hunt for.

The file is auto-injected into `/gsd:review` prompts by the workflow extension we landed. For any *other* skill or agent that touches plan files (e.g., `/gsd:patch-replan`, manual fix sessions, plan audits), load this file's contents at the start of work:

!`test -f .planning/REVIEW-CHECKLIST.md && cat .planning/REVIEW-CHECKLIST.md || echo "(no project-local review checklist defined)"`

Treat each pattern in that file as a known landmine. Any match in a plan or source file is a candidate HIGH concern unless it's an explicit prohibition or documented API surface.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
