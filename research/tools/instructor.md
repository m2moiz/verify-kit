---
title: instructor
aliases: [instructor-ai]
tags: [verify-kit, tools, llm, llm-addon]
created: 2026-05-18
status: ALWAYS-SHIP-when-has_llm
layer: LLM Add-on
phase_introduced: Phase 5
---

# 🎯 instructor

> [!abstract] One-line summary
> Single-call typed responses from LLMs — define a Pydantic model, get a validated instance back. The "no agent loop" case.

## What it does

Wraps LLM providers (OpenAI, Anthropic, etc.) with a `response_model: Type[BaseModel]` parameter. Sends the request, parses the response, validates against the Pydantic schema, retries on validation failure. One call → one typed object.

## Why we picked it

For LLM features that don't need agent loops (single classification, one-shot extraction, parse-this-text-to-structured), `instructor` is the lightest path:

| Alternative | Why opt for |
|---|---|
| `pydantic-ai` | When you DO need an agent loop or multiple tools — that's its sweet spot |
| `marvin` | Thin wrapper over pydantic-ai now; superseded |
| Raw API + try/except parse | Reinventing the wheel; instructor's retry-on-validation is non-trivial |
| `outlines` | Useful only for self-hosted models |
| BAML | High lock-in; non-Python DSL |

`instructor` and `pydantic-ai` are not redundant — they cover different request shapes.

See [[agent-reports/wave-4-ai-sdk-ergonomics]].

## Usage in verify-kit

```python
# Generated project when has_llm=true
import instructor
from openai import OpenAI
from pydantic import BaseModel

class Sentiment(BaseModel):
    polarity: float       # -1.0 to 1.0
    confidence: float

client = instructor.from_openai(OpenAI())

result = client.chat.completions.create(
    model="gpt-4o-mini",
    response_model=Sentiment,
    messages=[{"role": "user", "content": "Rate this review: ..."}],
)
# result is a validated Sentiment instance
```

Phase 5 wires `instructor` alongside `pydantic-ai`, `litellm`, `tokencost`, `autoevals`, `vcrpy`, `opentelemetry-instrumentation-httpx`.

## Install

```python
# In generated project deps when has_llm=true
"instructor>=1",
```

## Gotchas

- **Retry budget** — `max_retries` parameter controls how many times instructor re-asks the model on validation failure; default is 1. Raise carefully (each retry costs tokens).
- **Provider coverage** — instructor wraps OpenAI, Anthropic, Cohere, Mistral, Ollama. For others, fall back to LiteLLM ([[tools/litellm]]) + manual parsing.
- **Streaming + validation** — partial streaming works for some providers; combining with `response_model` mode requires care.

## Key docs

- Repo: <https://github.com/instructor-ai/instructor>
- Patterns: <https://python.useinstructor.com/concepts/patching/>
- Validation flow: <https://python.useinstructor.com/concepts/validation_context/>

## Related notes

- [[tools/pydantic-ai]] — the agent-loop counterpart
- [[tools/litellm]] — what handles broader provider coverage
- [[00-stack-decisions#LLM Add-on]] — default-shipping slot
- [[agent-reports/wave-4-ai-sdk-ergonomics]] — wave context
