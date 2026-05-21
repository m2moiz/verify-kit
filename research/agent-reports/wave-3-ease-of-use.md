---
title: Ease-of-Use Patterns in Developer Tools
aliases: [Wave 3 - Ease of Use, DX, 30-Second Rule, Lovable Tools]
tags: [research, wave-3, ux, dx, ease-of-use, design]
wave: 3
source_agent: ease-of-use-patterns
created: 2026-05-17
---

# What Makes Developer Tools "Feel Easy" — Research for verify-kit

> [!abstract] Headline
> Patterns from tools developers love: **30-second rule** (copy to "I see my thing working" under 30s), **miette/rustc-style errors** (context → cause → suggestion → link), **did-you-mean for typos**, **one config file** (no dotfile sprawl), **isatty discipline**, **`--check` default + `--fix` opt-in**, **plain readable generated code** (no opaque runner). The single highest-leverage move: error messages with all four parts.

## 1. Onboarding & First-Run Experience

**The 30-second rule.** Vite popularized "nearly instant" dev startup as table stakes; cold-starts went from ~4.5s on CRA to ~390ms on Vite. Psychological bar: from `npm create` to "I see my thing working" should fit single attention span (~30s). Anything longer needs visible progress.

**Single-command bootstrap non-negotiable.** `npm create vite@latest`, `cargo new`, `gh repo create`, `npm create astro@latest` — all converged: one command, interactive prompts for few decisions that matter, sensible defaults for everything else.

**Interactive prompts vs flags vs config — when each is right** (synthesized from Atlassian's CLI principles + GitHub CLI behavior):
- **TTY detected + missing input → prompt.** Lowers cognitive load for first-timers
- **TTY missing OR `--no-input` flag → fail with helpful message** listing flags. This is CI/scripting contract
- **Config file** only for things you'd set *once per project*, never per-invocation

Create-t3-app and create-astro use this pattern (t3 via Clack). Copier follows it for templates and lets you bypass with `--defaults --force`.

**Sensible defaults > explicit config — modern consensus.** Vite, Astro, Tailwind v4, Bun all default to "works with zero config." Escape hatch is single file (`vite.config.ts`, `astro.config.mjs`), not sprinkling. **For verify-kit**: one `verify-kit.yaml` (or section in `pyproject.toml`), never multiple dotfiles.

## 2. Error Messages That Delight

Canonical pattern across Rust, Elm, miette: **context → cause → suggestion → link**.

**Rust/rustc principles** (Rustacean Principles + RFC 1644):
- Draw eye to *where* with sufficient context to understand *why*
- Header section visually distinct from code section
- Readable without color (color-blind + dumb terminals)
- Labels on source itself, not sentence "notes" at end
- Compiler is *learning tool* — phrasing matters

**miette** packages this UX as Rust crate: source snippets, labeled spans, help text, error codes, clickable links in supported terminals, screen-reader-friendly mode. Lesson for verify-kit: when check fails, output should look like rustc error, not Python traceback.

**Elm's "did you mean"** pattern is gold standard for typo-tolerance. Heroku CLI does same: `pss is not a heroku command. Did you mean ps? [y/n]`. Cheap to implement (Levenshtein on subcommand list), enormous goodwill payoff.

**The Atlassian rule**: include written description **plus fix suggestion plus info link**. Three parts, every time. Raw stack traces are admission of laziness.

**For verify-kit**: failed checks must show `(1) what failed, (2) offending file:line, (3) exact command to fix or inspect, (4) doc link`. Writing these messages is 5x effort of writing check itself. Budget for it.

## 3. Progressive Disclosure & "Right Amount of Magic"

**Two-tier help** (clig.dev): bare command shows concise help with one or two examples and key flags; `-h`/`--help` shows full manual. `jq` is reference. Cargo's third-party subcommand protocol forwards `--help` to subcommand itself — perfectly composable.

**GitHub CLI's discoverability**: `gh` alone lists top-level commands; `gh <command>` lists its subcommands; `--help` uniform at every level. No memorization required.

**"Self-documenting" output**: after `forge login`, Atlassian's CLI suggests `forge create` as next step. GitHub CLI does same with `gh repo create` → suggests `gh repo view`. **For verify-kit**, after `just verify` succeeds: "All 12 checks passed. Next: `just verify --watch` to re-run on save, or edit `verify-kit.yaml` to add checks."

**Catch**: too many suggestions = noise. One next step, max.

## 4. Single Source of Truth & Config Sprawl

**The Vite/Bun consolidation thesis**: one config file, one binary, one mental model. Bun explicitly markets itself as "Node + npm + Webpack + Babel + Jest in one tool." Vite's `vite.config.ts` is single source. Tailwind v4 collapsed config into CSS itself.

**The backlash**: average JS project has `.eslintrc`, `.prettierrc`, `tsconfig.json`, `vitest.config.ts`, `package.json`, `.editorconfig`, `.nvmrc`, `.npmrc`. Developers hate it. Modern tools fight this — pnpm reads `package.json`, biome consolidates lint+format into one file.

**For verify-kit**: one config file. Period. If you must, allow section inside `pyproject.toml` / `package.json` so it doesn't add dotfile to user's root.

## 5. Discoverability & Documentation

**README-first docs** (Astro, Drizzle, t3): README *is* docs for first 5 minutes. Drizzle ships runnable snippets you can paste. Astro's docs read like friendly tutorial, not API reference.

**Inline help with examples**: `gh issue create --help` shows actual invocations. `cargo --help` lists every subcommand on one screen.

**Did-you-mean for typos** at every level (subcommands, flags, config keys). Cheap. Beloved.

## 6. "No Surprises" Principle

- **Respect conventions**: `-f/--force`, `-n/--dry-run`, `-q/--quiet`, `-v/--verbose`. Users' fingers know these
- **Respect environment**: `NO_COLOR`, `XDG_CONFIG_HOME`, `$EDITOR`, `TERM=dumb`. Detect TTY; switch to plain output for pipes
- **Don't silently mutate**: never write outside project dir, never `chmod`, never modify `~/.bashrc` without consent
- **`--dry-run` / `--check` / `--plan`**: Terraform, kubectl, Black, Ruff — all converged. **For verify-kit**: `just verify --check` should report without modifying anything (no autofix unless `--fix`)
- **Fail fast with clear errors > silently degrade**: rule 0. Don't `or {}` a missing config

## 7. Speed as UX Feature

- **<100ms to first output** (clig.dev). Even "Loading config..." beats silence
- **Spinner only when actually doing work >500ms**. Otherwise print raw progress
- **Cache aggressively** (Vite pre-bundles deps once; Ruff/Biome cache on file hash). For verify-kit: cache check results keyed on input file hash. Re-runs should feel free
- **Psychology**: Vite's HMR feels magical because feedback loop sub-perceptual. Same harness 8s vs 800ms is difference between "I'll run before commits" and "I'll run on save"

## 8. "I Can Read the Source"

- **Astro's transparency**: generated project has *your* code, not hidden runtime. CRA's "eject" trapdoor failed because by time you ejected, config was unreadable. Astro/Vite never need ejection
- **For verify-kit**: generated project should contain plain, readable `justfile`, plain Python/JS scripts, no `node_modules`-style black box. Developer should be able to delete or modify any single check without touching verify-kit itself

## 9. Empathy for User's Environment

- **Cross-platform without Docker** for trivial things. macOS + Linux + Windows native (not just WSL)
- **Works offline**: don't phone home, don't require login for `just verify`. (User's stated constraint)
- **No credentials for basics**: gh CLI requires login only for write operations; read works anonymously up to rate limits
- **Graceful degradation**: if `rg` missing, fall back to `grep`; if check tool isn't installed, skip with clear message ("ruff not found — install with `pip install ruff` or skip with `--skip ruff`")

## 10. "No Bloat" — Resist Scope Creep

Ripgrep stayed search tool. fd stayed find tool. **Cargo** opinionated about *project layout* but unopinionated about *what your code does*. **Astro** does sites, not apps. Discipline pays off: focused tools easier to learn and trust.

**For verify-kit**: it verifies. Does not lint, format, deploy, build, or test. It *invokes* tools that do those things, but harness itself stays small.

## 11. Specific Patterns From Tools Developers Love

| Tool | Specific UX move | Why it works | Adapt to verify-kit? |
|---|---|---|---|
| **Vite** | <1s cold start; ESM-first; HMR at module granularity | Sub-perceptual feedback changes behavior | Excellent — cache check results |
| **Astro** | Zero-config + opt-in islands; readable generated code | Defaults serve 90%, escape hatch one file | Excellent — same template philosophy |
| **Bun** | One binary replaces 5 tools | Removes integration friction entirely | Marginal — verify-kit shouldn't replace anything, just orchestrate |
| **gh CLI** | `gh <cmd>` lists subcommands; uniform `--help`; interactive when TTY, flags when not | Discoverability without docs | Excellent |
| **Cargo** | Third-party subcommands via `cargo-foo` binary; workspace = one tool covers test/bench/doc | Extension without core changes | Good — allow `just verify-foo` extensions |
| **Tailwind** | Docs you can grep; JIT means no config tuning | Docs as primary interface | Excellent — invest in README |
| **Vercel CLI** | `vercel` = deploy with smart defaults | Single command = single intent | Good — `just verify` is analog |
| **Drizzle** | TypeScript-first schema, no codegen needed | Removes whole class of toolchain | n/a |
| **miette** | Source snippets + spans + help + link in every diagnostic | Errors become learnable | Excellent — model failed-check output on this |
| **Copier** | Template updates via `copier update` merges upstream diff | Templates evolve without re-scaffolding | Excellent — **use Copier, not Cookiecutter** |
| **create-t3-app** | Clack prompts, modular installers, opt-in pieces | Users pick stack at scaffold time | Good — keep prompt count ≤ 5 |
| **rustc/Elm** | "Did you mean…?" suggestions on typos | Recovers user without doc lookup | Excellent for config keys + flags |

## The Top 10 Decisions verify-kit Should Make (Priority Order)

1. **Use Copier, not Cookiecutter.** Copier supports `copier update` to pull template improvements into existing projects — killer feature for verification harness that improves over time
2. **One command, one config file.** `copier copy gh:.../verify-kit dir/` → `just verify`. Config in `verify-kit.yaml` (or `[tool.verify-kit]` in `pyproject.toml`). Zero dotfile sprawl
3. **`just verify` must run in <2s on clean project, <500ms cached.** Speed is the feature. Cache by file hash
4. **Works offline, no login, no Docker, no agent required.** User's stated constraint and the differentiator
5. **Errors follow miette/Elm/rustc pattern**: what failed → file:line → fix suggestion → doc link. Every check author writes all four parts
6. **Did-you-mean for misspelled check names, config keys, CLI flags.** Levenshtein-1, suggest top match, exit non-zero
7. **Suggest next step on success.** "All checks passed. Try `just verify --watch` or add a check in `verify-kit.yaml`." One suggestion, not three
8. **Generated project is plain and readable.** Plain justfile, plain scripts, no opaque runner. Developer can delete any check
9. **`--check` is default; `--fix` is opt-in.** Never auto-mutate user files without consent
10. **TTY-aware: prompts in terminal, flags in CI.** Detect `isatty`; respect `NO_COLOR`, `CI=true`, `--no-input`

## "First 5 Minutes" UX Walkthrough

```
$ copier copy gh:moiz/verify-kit my-project
  🟢 Project name [my-project]: ▮
  🟢 Language (python/js/polyglot) [python]: ▮
  🟢 Include sample checks? [Y/n]: ▮
  ✓ Created my-project/ (4 files)

  Next steps:
    cd my-project
    just verify

$ cd my-project && just verify
  verify-kit v0.3 · 4 checks · cached (87ms)

  ✓ format     (ruff format --check)         12ms
  ✓ lint       (ruff check)                  41ms
  ✗ typecheck  (pyright)                    1.2s

  ─── typecheck failed ──────────────────────────────
   src/app.py:14:9
   14 │     return name.uppr()
                       ^^^^ "uppr" is not a method on str.
                            Did you mean "upper"?

   Fix:    src/app.py:14
   Docs:   https://verify-kit.dev/checks/typecheck

  3 passed, 1 failed in 1.3s
  ↳ Re-run with `just verify --watch` after fixing.

$ just verify --help
  Run all checks defined in verify-kit.yaml.

  USAGE:
    just verify                 Run all checks
    just verify --watch         Re-run on file change
    just verify --fix           Apply auto-fixes (format, lint)
    just verify --only lint     Run a single check
    just verify --skip pyright  Skip a check

  CHECKS: format, lint, typecheck, test
  CONFIG: verify-kit.yaml
```

Developer's experience:
1. **0–15s**: one command, three prompts, project exists
2. **15–30s**: `just verify` runs, output colored, fast, scannable
3. **30–60s**: one failure has snippet, fix, link. They fix it
4. **60–120s**: re-run shows green. Suggested next step (`--watch`) so obvious they try it. They are now using tool habitually

That's the win.

## Specifically Avoid (Anti-Patterns)

- **Don't ship a TUI/wizard for verification.** Run, output, exit. Drizzle Studio is good; "verify dashboard" is overreach
- **Don't require a daemon, server, or background process.** Pre-commit's daemon mode is footgun
- **Don't auto-install tools.** Detect missing and say "install with X" — don't shell out to pip/npm without consent
- **Don't proliferate flags.** Each flag is maintenance burden and discovery problem. <10 total
- **Don't write multi-line ASCII banners.** Nobody enjoys them on 50th run
- **Don't print "🚀 Initializing verification harness..."** when you mean "doing nothing for 2 seconds." Print *what* you're doing or print nothing
- **Don't require config file to exist.** Zero-config baseline (sensible defaults), config to customize
- **Don't silently skip checks.** Loud about missing tools. Loud about misconfig
- **Don't gate behind `npm login` / `gh auth`.** User said this. Honor it
- **Don't put state in `~/.verify-kit/`.** Project-local cache in `.verify-kit-cache/` (gitignored), so cleanup is `rm -rf project`

## The "Stranger Off the Street" Test

Without reading any docs, developer who has used `npm`, `git`, and any modern CLI should be able to:

1. **Install** by reading first 3 lines of README (one command)
2. **Generate project** by running that command and answering prompts (no flag knowledge required)
3. **Run verification** by typing `just verify` (README told them; `just --list` would have too)
4. **Understand failure** without opening external docs (error message itself is the doc)
5. **Add their own check** by reading `verify-kit.yaml`, copying existing entry, modifying. (No DSL, no plugin API, no class hierarchy)
6. **Disable check** they don't want, by deleting two lines
7. **Update template** when verify-kit improves, with `copier update`

If any requires Googling, tool failed test.

## Sources

- [clig.dev — Command Line Interface Guidelines](https://clig.dev/)
- [Atlassian — 10 Design Principles for Delightful CLIs](https://www.atlassian.com/blog/it-teams/10-design-principles-for-delightful-clis)
- [Vite — Why Vite](https://vite.dev/guide/why)
- [Bun — Official site](https://bun.com/)
- [Rustacean Principles — Improving Compiler Errors](https://rustacean-principles.netlify.app/how_to_rustacean/bring_joy/improving_compiler_error.html)
- [RFC 1644 — Default and Expanded rustc Errors](https://rust-lang.github.io/rfcs/1644-default-and-expanded-rustc-errors.html)
- [miette — Fancy diagnostics for Rust](https://github.com/zkat/miette)
- [GitHub CLI — Manual](https://cli.github.com/manual/)
- [Cargo — External Tools (subcommand protocol)](https://doc.rust-lang.org/cargo/reference/external-tools.html)
- [Cookiecutter vs Copier comparison](https://www.cookiecutter.io/article-post/cookiecutter-alternatives)
- [Project Scaffolding That Evolves With Copier (podcast)](https://www.pythonpodcast.com/episodepage/project-scaffolding-that-evolves-with-software-using-copier)
- [create-t3-app — Installation & CLI](https://create.t3.gg/en/installation)
- [Astro CLI Reference](https://docs.astro.build/en/reference/cli-reference/)
- [UX Design Institute — Onboarding Best Practices 2025](https://www.uxdesigninstitute.com/blog/ux-onboarding-best-practices-guide/)

## Related notes

- [[wave-3-human-friendly-logging]] · [[wave-3-vscode-ide]] · [[wave-2-scaffolding-tools]]
- [[00-architecture-overview]] · [[00-stack-decisions]]
- [[tools/copier]]
