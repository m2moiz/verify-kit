---
title: pydantic-ai
aliases: [pydantic_ai]
tags: [verify-kit, tools, llm-agent-framework, llm-addon]
created: 2026-05-18
status: ALWAYS-SHIP-when-has_llm
layer: LLM Add-on
phase_introduced: Phase 5
---

# 🧠 pydantic-ai

> [!abstract] One-line summary
> Typed agent framework from the Pydantic team — one-line provider swap, built-in OTel tracing, the breakout LLM lib of 2026.

## What it does

`pydantic-ai` is for the "agent loop" case: function-calling, tool use, multi-turn reasoning. You define an `Agent` with a system prompt + a typed result model + a list of Python tool functions; pydantic-ai handles the call-and-respond loop, tool dispatch, and result validation. Provider-agnostic via a single string (`openai:gpt-4o`, `anthropic:claude-haiku-4-5`).

## Why we picked it

For Phase 5's LLM add-on, pydantic-ai is the default agent framework:

| Alternative | Why secondary |
|---|---|
| `instructor` | Use for single-call typed responses ([[tools/instructor]]) — no agent loop |
| `langchain` / `langchain-core` | Heavyweight; opaque chain abstraction |
| `langgraph` | Graph-based agent orchestration; "use only when pydantic-ai is insufficient" |
| `crewai` | Multi-agent abstraction; "use only when pydantic-ai is insufficient" |
| `marvin` | Now a thin wrapper over pydantic-ai (it superseded marvin) |
| BAML | High lock-in DSL; non-Python files |
| DSPy | Very high lock-in; compiled prompts; only valuable with eval set |
| Mirascope | Good but pydantic-ai supersedes |

**Decisive factor:** Pydantic-team maintainer + built-in OTel `gen_ai.*` spans + idiomatic Python typing.

See [[agent-reports/wave-4-ai-sdk-ergonomics]].

## Usage in verify-kit

```python
from pydantic import BaseModel
from pydantic_ai import Agent

class Recommendation(BaseModel):
    title: str
    reasoning: str

agent = Agent[None, Recommendation](
    "anthropic:claude-haiku-4-5",
    system_prompt="You recommend books based on user preferences.",
)

@agent.tool_plain
def search_library(query: str) -> list[str]:
    return [...]  # call your DB / search index

result = await agent.run("Find me something like Borges.")
# result.data is a Recommendation
```

Phase 5 wires this alongside `instructor` (single-call), `litellm` (broad provider coverage), `autoevals` (scorers), `vcrpy` (record/replay), and `tokencost` (USD tracking).

## Install

```python
# In generated project deps when has_llm=true
"pydantic-ai>=0.0.20",
```

## Gotchas

- **OTel is built-in** — pydantic-ai emits `gen_ai.*` spans automatically when `OTEL_EXPORTER_OTLP_ENDPOINT` is set. No extra wiring needed.
- **`@agent.tool_plain` vs `@agent.tool`** — `_plain` for sync functions without context; `agent.tool` for functions that need run-context (run-state access, deps injection).
- **Result model is the contract** — pydantic-ai will retry the LLM if the response doesn't match the model. Tight schemas = fewer hallucinations + more retries; loose schemas = vice versa.
- **Async-first** — most APIs are `await`ed; the sync `Agent.run_sync(...)` exists but loses streaming benefits.

## Key docs

- Docs: <https://ai.pydantic.dev/>
- Getting started: <https://ai.pydantic.dev/agents/>
- Tools: <https://ai.pydantic.dev/tools/>
- Streaming: <https://ai.pydantic.dev/results/#streamed-results>

## Related notes

- [[tools/instructor]] — when you don't need an agent loop
- [[tools/litellm]] — provider abstraction (pydantic-ai can use it as its model)
- [[tools/langfuse]] — observability backend for the OTel spans pydantic-ai emits
- [[00-stack-decisions#LLM Add-on]] — default-shipping slot
- [[agent-reports/wave-4-ai-sdk-ergonomics]] — wave context
