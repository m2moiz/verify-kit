---
title: Project Scaffolding & Updatable Template Tools
aliases: [Wave 2 - Scaffolding, Templates, Copier vs Cookiecutter]
tags: [research, wave-2, scaffolding, copier, templates]
wave: 2
source_agent: scaffolding-tools
created: 2026-05-17
---

# Project Scaffolding & Updatable Template Tools — 2026 State of the Art

> [!abstract] Headline
> **Copier wins.** It's the only mainstream scaffolder that natively solves "re-apply template improvements to existing projects" via `copier update` with three-way merging. `tiangolo/full-stack-fastapi-template` migrated from Cookiecutter to Copier — strong adoption signal.

## 1. Tool Landscape

### Cookiecutter (Python, Jinja2)
- **Link:** https://www.cookiecutter.io/
- **Status 2026:** Active but feature-frozen by intent. De facto baseline for ~10 years.
- **Update story:** **None.** This is the headline limitation. Once `cookiecutter <repo>` runs, template is forgotten. Layer `cruft` on top for retrofit drift detection.
- **Multi-language fit:** Good (file-type agnostic).
- **Limitation:** No update path, JSON-only config, no type-validated prompts. In 2026 it's "stable but legacy."

### Copier (Python, Jinja2 + YAML) — RECOMMENDED
- **Link:** https://copier.readthedocs.io/
- **Status:** Very active. Explicitly framed as **code lifecycle management tool**, not just scaffolder. tiangolo's `full-stack-fastapi-template` migrated to it.
- **Update story:** **Best in class.** `copier update` re-runs template against existing project, three-way merges diff, surfaces conflicts inline (no `.rej` files like cookiecutter). Stores `.copier-answers.yml` recording prompt answers + template commit SHA.
- **Multi-language fit:** **Excellent.** File-type agnostic. Conditional file generation via `{% if use_godot %}project.godot{% endif %}.jinja` filename pattern. Post-gen `tasks:` with `when:` conditions. `_jinja_extensions` for custom Python helpers.
- **Limitation:** Merge conflicts on hand-edited harness files require human resolution (no tool sidesteps this). Steeper YAML schema than cookiecutter's JSON.

### Cruft (Python, layered on Cookiecutter)
- **Link:** https://cruft.github.io/cruft/
- **Status:** Maintained (PRs through 2025–2026).
- **Sweet spot:** Already have large cookiecutter template you can't migrate.
- **Update story:** `cruft update` and `cruft diff` retrofit drift detection. Less integrated than Copier.
- **Verdict:** If starting fresh, **Copier obsoletes the Cookiecutter+Cruft combo**.

### degit / tiged / giget (Node)
- **Links:** [degit](https://github.com/Rich-Harris/degit) (abandoned) · tiged (active fork) · giget (UnJS — powers `nuxi init`)
- **Status:** degit abandoned. tiged is active drop-in fork. giget is what modern Node tooling uses.
- **Update story:** **None.** Pure download tools.
- **Verdict:** Wrong tool for updatable harness. Use only as delivery mechanism for static starter.

### Yeoman
- **Link:** https://yeoman.io/
- **Status 2026:** Declining. Heavy framework. Still alive inside enterprise (VS Code extension generator).
- **Update story:** None native.
- **Verdict:** Avoid in 2026.

### Plop
- **Link:** https://plopjs.com/
- **Sweet spot:** Generating sub-components inside existing project (`plop component Button`). NOT project-level.
- **Fit:** Complementary to Copier — ship `plopfile.js` *inside* template for micro-gen.

### Language-native scaffolders (`npm create *`, `pnpm create *`, `uv init`, `cargo generate`)
- **Sweet spot:** Single-language projects.
- **Update story:** None.
- **Fit for multi-language harness:** **No.** Each only knows its own ecosystem.

### GitHub Template Repositories ("Use this template")
- **Sweet spot:** Zero-tooling discovery.
- **Update story:** **Effectively none.** No diff/merge from template to consumer.
- **Fit:** Good as discovery surface (mark Copier template repo as GitHub template too). Bad as actual sync mechanism.

### Backstage Scaffolder (Spotify)
- **Link:** https://backstage.io/docs/features/software-templates/
- **Status:** Active, enterprise-anchored.
- **Sweet spot:** Internal developer platforms at 50+ services.
- **Fit for indie dev:** **No.** Requires running Backstage. Massive overkill.

## 2. The Updatable Template Problem — What Actually Works

| Approach | Verdict |
|---|---|
| **Copier `update`** | **Best general answer.** Stores answers + template ref in `.copier-answers.yml`; three-way merges on update. |
| **Cruft (on Cookiecutter)** | Workable retrofit; second-best if Copier migration blocked. |
| **Git subtree** | Embeds template as subdirectory. `git subtree pull` brings updates. Works for *vendored harness directories* — terrible for files needing per-project templating (e.g. `pyproject.toml`). |
| **Git submodule** | Same use case as subtree but worse DX. Avoid. |
| **Renovate/Dependabot on versioned template package** | Works if harness publishable (npm/pypi). Doesn't help with templated/scaffolded files. |
| **Monorepo** | Solves by elimination — but contradicts "drop into new projects" goal. |

Honest reality: **Copier is the only widely-adopted tool natively solving "re-apply template + merge diff."** Everything else is workaround.

Pragmatic hybrid: **Copier for templated scaffold + git subtree for `.harness/` directory of literal scripts that don't need templating**. Copier `tasks:` can wire subtree pull on first run.

## 3. Reference Templates Worth Studying

- **[`fastapi/full-stack-fastapi-template`](https://github.com/fastapi/full-stack-fastapi-template)** — Migrated from cookiecutter to **Copier** (`copier copy https://github.com/fastapi/full-stack-fastapi-template my-proj --trust`). Demonstrates `--trust` flag (allows `tasks:` execution), multi-stack
- **`create-t3-app`** — Custom CLI; shows "interactive prompt for optional modules" UX (tRPC? Tailwind? Auth?) done well
- **`pawamoy/copier-pdm`** — Reference Copier template for Python projects
- **Backstage's `software-templates` repo** — Worth skimming for YAML schema design

Common conventions: `template/` subdir holding files; root-level `copier.yml` or `cookiecutter.json` for prompts; `tasks/` or `hooks/` dir for post-gen; `_excludes` for `.git`, `node_modules`.

## 4. Optional Modules ("Add-on Packs")

For "some projects need game testing, others need audio, others just LLM eval":

- **Copier:** Boolean prompts (`needs_game_testing: bool`) gate both files (filename Jinja) and tasks (`when:`). Clean.
- **Cookiecutter:** Pre/post-gen Python hooks delete unwanted dirs after generation. Works but ugly — files exist transiently.
- **Yeoman:** Composability via `composeWith()` — powerful but heavy.
- **Backstage:** Multiple small templates + portal chaining.

Copier's model is cleanest for "harness with à la carte add-ons." Can split into base template + child templates extending it using `_subdirectory` and answer inheritance.

## 5. Versioning & Distribution

- **Git tags + SemVer on template repo.** Consumers pin via `copier copy --vcs-ref v1.4.0 ...`. `.copier-answers.yml` records exact ref so `copier update` knows what they're upgrading from.
- **Don't** publish to npm/PyPI for template repo — Copier reads git directly.
- **Changelog discipline matters more here than for libraries** — breaking changes in harness template can force every downstream project to resolve conflicts. Treat template SemVer seriously.

## Recommendation

**Use Copier** because it's the only mainstream tool natively solving "update existing projects when template improves" — via `copier update` with three-way merging, `.copier-answers.yml` for state, conditional files for optional modules, `tasks:` with `when:` guards for post-gen wiring.

Tag template with SemVer, use `--vcs-ref` to pin, run `copier update` in downstream projects on cadence (Renovate can even auto-PR this).

**Fallback if multi-language polyglot composition becomes dominant pain** (rather than updatability): keep Copier as *scaffolder*, but vendor actually-shared harness scripts (`make verify` target, hook scripts, `/__debug` middleware) into `.harness/` directory pulled via **git subtree** from separate `harness-core` repo. This decouples "templated config" (Copier's job) from "literal shared code" (subtree's job).

**Avoid** Cookiecutter+Cruft for greenfield (Copier obsoletes), Yeoman (declining), Backstage (enterprise overkill), language-native scaffolders (each knows only one lane).

## Sources

- [Copier vs Cookiecutter — DEV Community](https://dev.to/cloudnative_eng/copier-vs-cookiecutter-1jno)
- [Migrate cookiecutter to Copier — Cambridge DevOps](https://guidebook.devops.uis.cam.ac.uk/howtos/development/copier/migrate/)
- [Template Once, Update Everywhere — AI Echoes](https://aiechoes.substack.com/p/template-once-update-everywhere-build-ab3)
- [Cruft vs Copier — Blenddata](https://www.blenddata.nl/en/blogs/cruft-vs-copier-automating-template-updates-at-scale)
- [Cruft docs](https://cruft.github.io/cruft/) · [cruft on GitHub](https://github.com/cruft/cruft)
- [Copier — Configuring a template](https://copier.readthedocs.io/en/stable/configuring/)
- [Copier — Comparisons with other tools](https://copier.readthedocs.io/en/stable/comparisons/)
- [copier-template-extensions](https://github.com/copier-org/copier-template-extensions)
- [Full Stack FastAPI Template](https://github.com/fastapi/full-stack-fastapi-template)
- [Backstage Software Templates docs](https://backstage.io/docs/features/software-templates/)
- [10 tips for better Backstage Software Templates — Red Hat 2025](https://developers.redhat.com/articles/2025/03/17/10-tips-better-backstage-software-templates)
- [Cargo Generate docs](https://cargo-generate.github.io/cargo-generate/)
- [copier-pdm reference template](https://pawamoy.github.io/showcase/copier-pdm/)

## Related notes

- [[wave-2-polyglot-orchestration]] · [[wave-2-ci-portability]]
- [[00-architecture-overview]] · [[00-stack-decisions]]
- [[tools/copier]]
