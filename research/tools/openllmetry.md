---
title: OpenLLMetry
aliases: [openllmetry, traceloop-openllmetry]
tags: [verify-kit, tools, llm-observability, opentelemetry]
created: 2026-05-18
status: ALWAYS-SHIP-when-has_llm
layer: LLM Add-on (OTel layer)
phase_introduced: Phase 5
---

# 🔭 OpenLLMetry

> [!abstract] One-line summary
> OpenTelemetry SDK extension that emits `gen_ai.*` semantic-convention spans for LLM calls — provider-agnostic.

## What it does

OpenLLMetry wraps the OTel SDK with auto-instrumentation for OpenAI, Anthropic, Cohere, LiteLLM, LangChain, and other LLM libraries. Spans carry the CNCF `gen_ai.*` semantic conventions: `gen_ai.system`, `gen_ai.request.model`, `gen_ai.response.id`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `gen_ai.usage.cost`. Any OTel backend (Jaeger, Langfuse, Honeycomb, Tempo) can ingest them.

## Why we picked it

When `has_llm=true`, the OpenLLMetry SDK is installed automatically so LLM spans show up in Langfuse / Jaeger / wherever the OTel exporter is pointed:

- ✅ Provider-agnostic (instruments OpenAI + Anthropic + LiteLLM + more)
- ✅ Standards-based (`gen_ai.*` semantic conventions are CNCF/OTel)
- ✅ Composes with the harness's existing OTel scaffold ([[00-stack-decisions#OpenTelemetry (installed but inert)]])
- ✅ Maintained by Traceloop (active)

| Alternative | Why secondary |
|---|---|
| `prometheus-fastapi-instrumentator` | OTel via Logfire covers the same ground; PromInst is overkill solo |
| `opentelemetry-instrumentation-httpx` alone | Misses provider-specific attributes (model, token counts) |
| Manual span creation in every LLM call | Tons of boilerplate; OpenLLMetry auto-applies on import |

See [[agent-reports/wave-3-opentelemetry-local]].

## Usage in verify-kit

Phase 5 adds `opentelemetry-instrumentation-httpx` + OpenLLMetry to the LLM add-on deps. Initialization happens at startup when `OTEL_EXPORTER_OTLP_ENDPOINT` is set (lazy import per [[00-stack-decisions#OpenTelemetry (installed but inert)]]):

```python
# harness/observability.py (Phase 2 stub; Phase 5 extends)
import os

if os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    # ... lazy init ...

    # Phase 5 only: auto-instrument LLM libs
    from traceloop.sdk import Traceloop
    Traceloop.init(disable_batch=False)
```

After init, every `openai.completions.create(...)` / `anthropic.messages.create(...)` / `litellm.completion(...)` emits a span with full `gen_ai.*` attributes.

## Install

```python
# In generated project deps when has_llm=true
"traceloop-sdk>=0.21",   # the OpenLLMetry SDK
"opentelemetry-instrumentation-httpx>=0.48",  # generic HTTP span for unknown providers
```

## Gotchas

- **Auto-instrumentation patches on import** — make sure `Traceloop.init()` runs BEFORE any LLM library is imported, or some spans will be missed
- **`gen_ai.prompt.*` and `gen_ai.completion.*` are large** — full prompts can balloon traces; use `Traceloop.init(api_endpoint=..., disable_content_tracing=True)` if storage is a concern
- **`disable_batch=False` matters for short-lived CLIs** — without it, spans are batched and the process exits before flushing. CLI runs need `BatchSpanProcessor.shutdown()` in an `atexit` (see [[synthesis/session-2026-05-18-phase-1-and-2-buildout]] research-flagged item #2)
- **Jaeger doesn't show `gen_ai.*` attributes natively** — but they ARE in the trace; you can see them in the JSON view. Langfuse renders them as a first-class trace shape.

## Key docs

- Repo: <https://github.com/traceloop/openllmetry>
- gen_ai semantic conventions: <https://opentelemetry.io/docs/specs/semconv/gen-ai/>
- Provider instrumentation list: <https://www.traceloop.com/docs/openllmetry/integrations/introduction>

## Related notes

- [[tools/langfuse]] — observability backend that natively renders `gen_ai.*` spans
- [[tools/jaeger]] — fallback local viewer
- [[tools/litellm]] — primary LLM provider; OpenLLMetry instruments its httpx calls
- [[00-stack-decisions#OpenTelemetry (installed but inert)]] — broader OTel role
- [[agent-reports/wave-3-opentelemetry-local]] — wave context
