---
title: Langfuse
aliases: [langfuse-cloud, langfuse-self-host]
tags: [verify-kit, tools, llm-observability, llm-addon]
created: 2026-05-18
status: ALWAYS-SHIP-when-has_llm
layer: LLM Add-on
phase_introduced: Phase 5
---

# 📊 Langfuse

> [!abstract] One-line summary
> Open-source LLM observability — traces, costs, evals, prompts in one UI. Free Cloud Hobby tier, self-host path for outgrowth.

## What it does

Langfuse records every LLM call as a trace: prompts, completions, model, latency, tokens, cost. Multi-project isolation (separate creds per project). Web UI for filtering and inspection. Integrates with OpenTelemetry semantic conventions (`gen_ai.*` attributes), so spans land in Langfuse automatically when the OTel exporter is pointed there.

## Why we picked it

| Alternative | Why rejected |
|---|---|
| Phoenix (Arize) | Weaker multi-project isolation (tag-and-filter vs separate creds) |
| Helicone (proxy mode) | Coupling not worth it across heterogeneous providers (fal, Pioneer, Tavily) |
| Per-project SQLite logs | "You'll build a worse Langfuse over six months" |
| Helicone self-host | Heavier stack than Langfuse for same outcome |

**Decisive factor:** one personal ops backend across all projects, free until outgrown.

See [[agent-reports/wave-2-llm-hosting]] for the comparison.

## Usage in verify-kit

Phase 5 (`has_llm=true`) ships:
- Cloud Hobby (default) — `.env.example` with `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` slots
- Self-host option — generates `docker-compose.langfuse.yml`
- `none` — neither is written

The `llm_backend` Copier prompt picks one of the three.

## Hosting trajectory

> [!info] Cost path
> 1. Cloud Hobby (free, 50k events/month) — most projects live here forever
> 2. When outgrown → self-host on Hetzner CX32 (~€7.60/month) — same UI, your storage, your control
> 3. Migration is documented in the generated project's README when `llm_backend=langfuse-self-host`

## Install

```python
# In generated project's deps when has_llm=true
"langfuse>=2",
```

```python
# Usage (autoinstrument or explicit)
from langfuse.decorators import observe

@observe()
def call_llm(prompt: str) -> str:
    ...
```

Or via OpenTelemetry — Langfuse accepts OTLP exports.

## Gotchas

- **Cloud Hobby's 50k events/month** is per-org, not per-project. Heavy traffic projects exhaust quickly; self-host before that becomes a problem.
- **OTel routing** — when sending OTel spans to Langfuse, the auth headers go in `OTEL_EXPORTER_OTLP_HEADERS`, not `OTEL_EXPORTER_OTLP_*` per-tenant.
- **Self-host needs Postgres + ClickHouse + Redis + S3** — `docker-compose.langfuse.yml` brings them all up; about 2 GB RAM minimum.

## Key docs

- Quickstart: <https://langfuse.com/docs/get-started>
- Self-host: <https://langfuse.com/self-hosting>
- OTel integration: <https://langfuse.com/docs/integrations/opentelemetry>
- Decorators: <https://langfuse.com/docs/sdk/python/decorators>

## Related notes

- [[00-stack-decisions#LLM Add-on]] — role
- [[00-decision-log]] — D-006 records the Langfuse vs Phoenix vs Helicone decision
- [[agent-reports/wave-2-llm-hosting]] — full comparison
- [[tools/promptfoo]] — companion eval tool (opt-in)
- [[tools/openllmetry]] — what feeds Langfuse via OTel `gen_ai.*` spans
