---
title: Copier
aliases: [copier, Copier template engine]
tags: [verify-kit, tools, scaffolding, universal-foundation]
created: 2026-05-18
status: ALWAYS-SHIP
layer: Universal Foundation
phase_introduced: Phase 1
---

# 🌱 Copier

> [!abstract] One-line summary
> Project template engine with native `copier update` and 3-way merge for re-applying improvements to scaffolded projects.

## What it does

Copier renders Jinja2-templated files from a template repository into a consumer's target directory. Unlike one-shot generators, Copier records its template version and prompt answers in `.copier-answers.yml`, enabling `copier update` to pull in template improvements via git-style 3-way merge — without overwriting consumer edits.

## Why we picked it

| Alternative | Why rejected |
|---|---|
| Cookiecutter + Cruft | Copier obsoletes the combo (native `copier update`); see [[00-decision-log#^D-003]] |
| Yeoman | Declining ecosystem; mostly abandoned |
| Backstage scaffolder | Enterprise overkill; requires running Backstage |
| degit | One-shot only; no update mechanism |
| GitHub template repos | No three-way merge; no answer-file tracking |

**Decisive factor:** `tiangolo/full-stack-fastapi-template` (and many others) migrated to Copier specifically for the update story.

See [[agent-reports/wave-2-scaffolding-tools]] for the full comparison.

## Usage in verify-kit

- Phase 1 lands `copier.yml` at the verify-kit repo root with `_subdirectory: template` (Area 1 decision)
- Each consumer's scaffolded project carries `.copier-answers.yml`; running `copier update` later pulls template improvements
- `_jinja_extensions` registers `template_extensions/env_detect.py` for env-based prompt defaults (Area 2 decision)
- Form B Jinja-in-path (`{% if has_X %}.dir{% endif %}/...`) is the conditional-file mechanism — NOT `_skip_if` (which is not a real Copier key)

## Install

End-user invocation (the README documents this for consumers):

```bash
# uv tool install with the companion package — the loader auto-handles
# template-adjacent extension modules without needing them on PyPI
uv tool install copier --with copier-templates-extensions

# Then:
copier copy gh:m2moiz/verify-kit my-new-project
```

Pinned dev dep:

```toml
# pyproject.toml of verify-kit itself
[dependency-groups]
dev = ["copier>=9.4", ...]
```

## Gotchas (learned the hard way)

> [!warning] Empirically verified during Phase 1
> See [[synthesis/session-2026-05-18-phase-1-and-2-buildout#^M-1]] and [[synthesis/session-2026-05-18-phase-1-and-2-buildout#^M-2]].

1. **`_templates_suffix` defaults to `.jinja`, NOT `.jinja2`** — without `_templates_suffix: .jinja2` in `copier.yml`, every `template/**/*.jinja2` file is copied verbatim with suffix retained and Jinja syntax unrendered. Confirmed in Copier 9.15.1.
2. **`_skip_if` is NOT a recognized Copier key** — silently ignored. Use Form B (Jinja-in-directory-name): `template/{% if has_devcontainer %}.devcontainer{% endif %}/devcontainer.json.jinja2`.
3. **`when: false` computed prompts don't appear in `.copier-answers.yml`** — verify slug derivations via the *rendered* artifact (e.g., generated `pyproject.toml`), not the answers file.
4. **Filename Jinja: keep `.jinja2` suffix OUTSIDE the conditional** — `{% if x %}CLAUDE.md{% endif %}.jinja2` works; `{% if x %}CLAUDE.md.jinja2{% endif %}` ships the literal suffix to the consumer.
5. **Global `copier` CLI from `uv tool install` is isolated** — it can't see project-local `template_extensions/` packages unless installed via `--with` or registered via the documented loader pattern.

## Key docs

- Configuring: <https://copier.readthedocs.io/en/stable/configuring/>
- Updating: <https://copier.readthedocs.io/en/stable/updating/>
- Jinja extensions: <https://copier.readthedocs.io/en/stable/configuring/#jinja-extensions>
- `copier-templates-extensions` loader: <https://github.com/copier-org/copier-templates-extensions>

## Related notes

- [[00-stack-decisions#Universal Foundation — ALWAYS SHIP]] — verdict + role
- [[00-decision-log]] — D-003 records the decision
- [[agent-reports/wave-2-scaffolding-tools]] — full comparison vs Cookiecutter/Cruft/degit/Yeoman/Backstage
- [[00-architecture-overview]] — where Copier fits in the four-layer model
