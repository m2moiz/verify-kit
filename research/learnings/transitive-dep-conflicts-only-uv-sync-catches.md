---
title: Transitive dep conflicts are unreachable by spec-time review — only uv sync catches them
aliases: [transitive-dep-conflicts, uv-sync-catches-what-spec-cant, dep-resolver-catches]
tags: [verify-kit, learnings, atomic, dependencies, uv, gsd, verify-work]
created: 2026-05-22
last_updated: 2026-05-22
source_session: [[session-2026-05-22-phase-5-llm-and-verification]]
---

# Transitive dep conflicts are unreachable by spec-time review

> [!abstract] Pattern
> Planning loops, convergence loops, and even Codex adversarial review cannot catch transitive dependency conflicts. Those only surface when `uv sync` (or any resolver) walks the **full** transitive graph against your existing pins. The verify-work cold-start render is the canonical place these surface. Plan accordingly.

## Three Phase 5 incidents

Phase 5 ran 8 convergence cycles, 4 planning revisions, slopcheck, code-review — none of them caught these. All three only surfaced when `uv sync` was actually invoked against the rendered scratch project.

### Incident 1: `opentelemetry-instrumentation-httpx 0.63b1` vs Phase 2 otel-sdk

> [!example] Caught by 05-03 executor mid-execution
> **The pin in 05-01:**
> `opentelemetry-instrumentation-httpx>=0.63b1`
>
> **Phase 2's prior pin:**
> `opentelemetry-sdk==1.41.1` → transitively requires `opentelemetry-semantic-conventions==0.62b1`
>
> **The conflict:** `httpx-instrumentation 0.63b1` requires `semantic-conventions==0.63b1`. Incompatible.
>
> **Where caught:** the 05-03 executor agent ran `uv sync --extra dev` as part of its `<verify>` step and the resolver failed.
>
> **Fix commit:** [`ed1854a`](#) — "fix(deps): pin otel-instrumentation-httpx to 0.62b1 for Phase 2 compat"
>
> **Beads filed:** `verify-kit-x60` (closed)

### Incident 2: `pydantic-ai` meta-pkg pulls `[mistral]`

> [!example] Caught by /gsd:verify-work 5 cold-start render
> **The pin in 05-01 (originally):**
> `pydantic-ai>=1.100,<2`
>
> **The transitive chain the resolver discovered:**
> ```
> pydantic-ai==1.100.0
>   └─→ pydantic-ai-slim[mistral]==1.100.0
>         └─→ mistralai>=2.0.0
>               └─→ opentelemetry-semantic-conventions>=0.60b1,<0.61
> ```
>
> Conflicts with Phase 2's `opentelemetry-sdk==1.41.1` (which pulls semantic-conventions 0.62b1).
>
> **Where caught:** the first `/gsd:verify-work 5` cold-start render. `uv sync --extra dev` errored with a clear conflict trace from the resolver.
>
> **Fix:** switch to `pydantic-ai-slim[anthropic,openai]>=1.100,<2`. Slim + explicit provider extras avoids the `[mistral]` transitive entirely.
>
> **Fix commit:** [`daba26f`](#) — "fix(deps): swap to pydantic-ai-slim + bump fastmcp for Phase 5 sync"

### Incident 3: `fastmcp<3.0` vs `pydantic-ai-slim 1.100`

> [!example] Caught by /gsd:verify-work 5 cold-start render (same commit as incident 2)
> **Phase 3 had speculatively pinned (commit [`163d63a`](#)):**
> `fastmcp>=2.0,<3.0`
>
> **The transitive requirement:**
> `pydantic-ai-slim 1.100` transitively requires `fastmcp>=3.3` via the `[fastmcp]` extra.
>
> **Where caught:** same `/gsd:verify-work 5` cold-start as incident 2.
>
> **Fix:** bump pin to `fastmcp>=3.3,<4`. Filed beads `verify-kit-fastmcp-3x` to track that Phase 3 plans (specifically 03-01 T03 bearer-auth middleware import + T04 ToolAnnotations import) need API revalidation against 3.x when executed.
>
> **Fix commit:** [`daba26f`](#)

## Why this happens

- **PyPI metadata is fragmented.** Each package declares its requirements; the resolver walks the union. You can read every package's pyproject and still miss the transitive intersection.
- **Extras are invisible at the spec level.** `pydantic-ai` listed in pyproject as "pydantic-ai>=1.100" doesn't tell you anything about the `[mistral]` extra. The meta-package pulls all extras silently.
- **Pre-release versions don't show in normal listings.** `mistralai 2.x` requires a specific pre-release-band of semantic-conventions; you'd need to read pre-release metadata to predict the conflict.
- **Convergence loops review intent, not resolution.** Codex can find "this dep name is wrong" or "this version pin is outdated" but it cannot run the full resolver in its head.

## What to do about it

> [!tip] Apply
> - **Always run `/gsd:verify-work` after every phase that adds dependencies.** The cold-start render with `uv sync` is the canonical resolver check. Treat it as non-skippable.
> - **Prefer `*-slim` packages with explicit extras** over meta-packages. `pydantic-ai-slim[anthropic,openai]` is safer than `pydantic-ai` because the meta-package pulls every provider's transitive surface.
> - **When pinning a package that depends on extras-heavy ecosystem libraries** (e.g., OpenTelemetry, pydantic-ai, langchain), use `>=N` without an upper bound, OR commit to revalidating against new majors. Speculative `<N+1` upper bounds age fast and become Phase-N blockers in Phase-(N+2).
> - **File beads when a fix forces revisions to a prior unexecuted phase's pin.** Like `verify-kit-fastmcp-3x` — Phase 3's plans assume `fastmcp 2.x` APIs; Phase 5 forced a bump to 3.x; Phase 3 plans must be re-validated when executed.

## Implication for the GSD workflow

The four-gate sequence (`convergence` → `execute-phase` → `verify-work` → `secure-phase` → `code-review`) is structured exactly right for this:

- **convergence**: catches *spec* drift (cross-plan contracts, API names, decision references)
- **execute-phase**: catches *spec-vs-code* drift (executor writes something different from the plan); transitive deps surface here when `uv sync` runs in a task `<verify>` block
- **verify-work**: catches *full-system* failures — the cold-start render exercises the **whole** transitive graph, which is exactly when these conflicts manifest
- **secure-phase / code-review**: catches behavior bugs in code that resolution alone wouldn't show

Each gate is non-redundant. Skipping verify-work because "convergence passed" is the failure mode that lets transitive conflicts ship.

## Related patterns

- [[each-gate-catches-different-classes-of-bug]] — why all 4 gates are needed.
- [[internal-checker-vs-external-reviewer]] — even external review can't catch transitive resolution.
- [[cost-double-tokenization-pattern]] — code-review's distinct value: behavior bugs that resolution can't see.

## Open questions

- Could a `uv lock --dry-run` step be added to convergence to catch these earlier? Maybe — but it'd require maintaining a draft `pyproject.toml` during planning. Not obviously worth it.
- For Phase 6 — should the template-self-test CI matrix run `uv sync` against EVERY cell, not just `just verify`? Probably yes. Failed sync = failed cell.
