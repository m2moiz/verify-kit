---
title: LiteLLM
aliases: [litellm]
tags: [verify-kit, tools, llm-gateway, llm-addon]
created: 2026-05-18
status: ALWAYS-SHIP-when-has_llm
layer: LLM Add-on
phase_introduced: Phase 5
---

# 🔀 LiteLLM

> [!abstract] One-line summary
> Provider abstraction layer + retries + fallbacks + SQLite cache — call OpenAI, Anthropic, Bedrock, Cohere, Ollama, fal, etc. via one interface.

## What it does

`litellm.completion(...)` is a drop-in for `openai.completions.create(...)` but speaks 100+ provider APIs. Adds retries with exponential backoff, automatic fallback to alternate models, response caching to SQLite, cost tracking, and rate-limit handling.

## Why we picked it

verify-kit's LLM add-on uses heterogeneous providers (OpenAI for completions, Anthropic for Claude, fal/Pioneer/Tavily for other workloads). LiteLLM is the canonical unifier:

- ✅ One interface across 100+ providers
- ✅ Built-in retries and fallbacks (production-grade)
- ✅ SQLite response cache (deterministic tests without VCR)
- ✅ Cost tracking via `tokencost` / `tokenx`
- ✅ Streaming support

| Alternative | Why secondary |
|---|---|
| Raw provider SDKs | Provider-specific glue every time |
| `helicone` (proxy mode) | Coupling not worth it (see [[00-stack-decisions#Explicitly rejected]]) |
| `langchain` providers | Heavier framework lock-in than needed |

See [[agent-reports/wave-4-ai-sdk-ergonomics]].

## Usage in verify-kit

```python
from litellm import completion

response = completion(
    model="anthropic/claude-haiku-4-5",
    messages=[{"role": "user", "content": "..."}],
    fallbacks=["openai/gpt-4o-mini"],
    num_retries=3,
)
```

Phase 5 wires LiteLLM alongside `pydantic-ai`, `instructor`, `tokencost`, `autoevals`, `vcrpy`, and `opentelemetry-instrumentation-httpx`. The OTel httpx instrumentation auto-creates `gen_ai.*` spans for every LiteLLM call (regardless of underlying provider).

## Install

```python
# In generated project deps when has_llm=true
"litellm>=1.50",
```

## Gotchas

- **Provider key auto-detection** — LiteLLM reads `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc. from env automatically; explicit `api_key=` overrides
- **Caching is opt-in** — set `litellm.cache = Cache(type="local")` to enable SQLite caching; pairs with vcrpy for two layers of test determinism
- **Fallback ≠ load-balance** — `fallbacks=[...]` triggers only on failure; for load-balancing, use the Router API
- **Cost tracking via `tokencost`** — call `litellm.completion_cost(...)` to get USD per call; combine with `@cost_budget(usd=0.02)` from `tokencost` for budget enforcement

## Key docs

- Repo: <https://github.com/BerriAI/litellm>
- Provider list: <https://docs.litellm.ai/docs/providers>
- Routing: <https://docs.litellm.ai/docs/routing>
- Caching: <https://docs.litellm.ai/docs/caching/all_caches>

## Related notes

- [[tools/instructor]] — typed responses on top of LiteLLM
- [[tools/pydantic-ai]] — agent framework that can use LiteLLM as its provider
- [[tools/langfuse]] — traces from LiteLLM via OTel land here
- [[00-stack-decisions#LLM Add-on]] — default-shipping slot
