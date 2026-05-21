---
title: AI/LLM Developer Ergonomics Layer
aliases: [Wave 4 - AI SDK, LLM Ergonomics, pydantic-ai vs instructor]
tags: [research, wave-4, llm, pydantic-ai, instructor, ai-sdk]
wave: 4
source_agent: ai-sdk-ergonomics
created: 2026-05-17
---

# The LLM Developer Ergonomics Layer (2024–2026)

> [!abstract] Headline
> **7 packages ship by default in the LLM add-on**: `pydantic-ai` (2026 breakout), `instructor` (single-call typed), `litellm` (provider abstraction), `tokencost`+`tokenx` (cost), `autoevals` (pytest scorers from Braintrust OSS), `vcrpy` (offline-deterministic), `opentelemetry-instrumentation-httpx` (auto OTel spans). BAML/DSPy too high lock-in. Marvin now thin wrapper over pydantic-ai. Mirascope good but pydantic-ai supersedes.

## 1. Structured Output / Typed LLM Responses

### Instructor (jxnl) — SHIP
- **Link:** `python.useinstructor.com` / github.com/instructor-ai/instructor
- **What:** Patches provider SDK, takes Pydantic model, gets back validated instances. Uses native function calling under hood
- **License:** MIT, free
- **Lock-in:** Low — Pydantic models portable; remove patch and you have raw SDK calls
- **Dual-audience:** Excellent. Errors are Pydantic `ValidationError` (machine-parseable) AND human-readable
- **Catch:** Strict JSON parsing — chokes on messy reality of LLM output (markdown around JSON, trailing commas, chain-of-thought prefixes). Has retries but eats tokens
- **Verdict:** **Ship by default.** Lowest friction, biggest community, most Stack Overflow coverage

### BAML (BoundaryML) — DOCUMENT
- **Link:** `boundaryml.com` / github.com/BoundaryML/baml
- **What:** A DSL (`.baml` files) → codegen typed clients for Python/TS/Go/Ruby/Java/Rust. "Prisma for LLMs"
- **License:** Apache 2.0 OSS, free; paid hosted "Boundary Studio"
- **Lock-in:** **High** — your prompts live in non-Python DSL, your team learns BAML, your CI runs `baml generate`. Migrating out means rewriting every prompt
- **Killer feature:** **Schema-Aligned Parsing (SAP)** — tolerates real-world model output gunk that breaks Instructor
- **Verdict:** **Document but don't install.** Too opinionated for small add-on; recommend for teams committing to multi-language clients

### Mirascope — DOCUMENT
- **Link:** github.com/Mirascope/mirascope
- **What:** "LLM abstractions that aren't obstructions." Provider-classes (not SDK-patching), Pydantic-typed prompts, chain primitives
- **License:** MIT
- **Lock-in:** Medium — uses own provider abstraction
- **Dual-audience:** Strong typing all the way through. Type-checked prompt templates (PEP 695 string template support)
- **Verdict:** **Document.** Excellent if team dislikes SDK-patch approach. Not default

### pydantic-ai (Pydantic team) — SHIP (PRIMARY)
- **Link:** `ai.pydantic.dev` / github.com/pydantic/pydantic-ai
- **What:** Agent framework where inputs, tool params, outputs all Pydantic models. Built-in OTel. v1.0 shipped Sept 2025, latest 1.85.x as of April 2026. 16.5k+ stars. **Pydantic Logfire** is matching observability product (commercial)
- **License:** MIT
- **Lock-in:** Low at model-provider level (one-line swap between Anthropic/OpenAI/Gemini/Groq/Mistral). Medium at framework level
- **Dual-audience:** Best-in-class. OTel built in, errors are typed exceptions, replay straightforward, type-checker sees everything
- **Verdict:** **Ship by default.** **The 2026 quiet breakout.** For LLM add-on, this is agent-runner of choice

### DSPy (Stanford) — SKIP
- **Link:** `dspy.ai` / github.com/stanfordnlp/dspy
- **What:** Programmatic prompts. You write `Signatures` and `Modules`, DSPy compiles+optimizes prompt strings against your eval set
- **License:** MIT
- **Lock-in:** **Very high.** Your code is no longer "calls to an LLM" — it's a compiled program. Migrating out = rewriting from scratch
- **Dual-audience:** Poor for solo-dev debugging. Compiled prompt opaque; can't easily `print()` what model saw
- **Verdict:** **Skip.** Right tool when you have labeled dataset and need optimization. Wrong tool for "make my LLM calls testable"

### Marvin (Prefect) — SKIP
- **Link:** github.com/PrefectHQ/marvin
- **What:** "Ambient intelligence." Marvin 3.0 is now thin layer **on top of pydantic-ai**
- **Status:** Maintained (Jan 2026 release). Prefect-flavored sugar layer
- **Verdict:** **Skip.** If pydantic-ai works, you don't need this

### Outlines (dottxt) — SKIP for hosted-API users
- **Link:** github.com/dottxt-ai/outlines
- **What:** Grammar/regex/JSON-schema constrained generation at token level
- **Status:** Now mostly relevant via `XGrammar`, default backend in vLLM, SGLang, TensorRT-LLM (March 2026)
- **Verdict:** **Skip for hosted-API users.** Only matters if serving own model

## 2. Agent Frameworks (small footprint)

2026 consensus crystallized into three tiers:

| Framework | Lock-in | Solo usability | Dual-audience |
|---|---|---|---|
| **pydantic-ai** | Low–Med | Excellent (typed, OTel built in) | **Best** |
| **OpenAI Agents SDK** | High (GPT-only optimized) | Good — handoffs, guardrails, sandboxing (April 2026 overhaul) | OK |
| **Claude Agent SDK** (`@anthropic-ai/claude-agent-sdk`) | High (Anthropic-only) | Excellent for filesystem/computer-use; token-heavy at scale | OK |
| **LangGraph** | Medium | Steep curve; built for production audit trails | Decent |
| **CrewAI** | Medium | "Sociological" agents-as-workers. Fast prototyping, brittle at scale | Mediocre |
| **smolagents** (HF) | Low | Code-execution-first; clean for first-time agent builders | Good |
| **agno** (ex-phidata) | Medium | Microsecond instantiation, ~50x lower memory than LangGraph | OK |
| **LlamaIndex Workflows** | Med-High | If you're already in LlamaIndex for RAG | OK |
| **Google ADK** | High (GCP gravity) | Heavy, enterprise-shaped | Mediocre |

**verify-kit verdict:** Ship `pydantic-ai`. Document the rest. "Anthropic-first with OpenAI fallback" people actually run in production is `pydantic-ai` with `models=["anthropic:...", "openai:..."]` and try/except.

## 3. Prompt Management at Small Scale

2026 consensus is **hybrid**: prompts live in version control like code, but in dedicated files (not f-strings) so non-engineers can edit. The "prompts as data" vs "prompts as code" debate converged: **start with files-in-repo, graduate to a registry only when non-engineers need to ship without a deploy.**

- **Promptfoo** — eval-first, also light registry. Already in verify-kit's main scope
- **PromptLayer** — SaaS-first. Good for marketing teams. Skip for solo
- **Latitude** (LGPL-3.0) — OSS prompt CMS + agent platform. Heaviest; only justified if you have non-technical prompt editors
- **Helicone Prompts** — proxy-attached. Couples prompt mgmt with observability
- **Mirascope's `prompt_template` decorator** with type-checked vars
- **Native:** `prompts/*.md` with YAML frontmatter (`name`, `model`, `temperature`, `version`), loaded by `prompts.load("creature_extract")`. ~30 LOC. **This is right starting point**

**verify-kit verdict:** Ship `prompts/*.md` loader pattern. Document the rest.

## 4. Caching, Retries, Fallbacks

- **LiteLLM** — OSS, self-hosted unifier. De facto multi-provider abstraction. ~100+ providers, OpenAI-compatible API, built-in cache/retry/fallback. Lock-in: low (speaks OpenAI's protocol)
- **Portkey** — richer production gateway with logs/guardrails/budgets, OSS gateway + paid SaaS control plane
- **Vercel AI Gateway** — only relevant if on Vercel
- **Custom asyncio-retry (tenacity)** — sufficient until you need cross-provider fallback

**verify-kit verdict:** **Ship LiteLLM** as provider abstraction. Tenacity for in-process retry policy. Skip Portkey/Vercel unless user opts in.

## 5. Tool / Function-Calling Ergonomics

Convention has unified: **tool = Pydantic model + decorated function**. `pydantic-ai` does this natively; Instructor's `Iterable[Tool]` works similarly. MCP servers wrap same shape for cross-process use.

**verify-kit verdict:** Use `pydantic-ai`'s `@agent.tool` for in-process tools. Document MCP for cross-process.

## 6. Streaming Patterns

- **Vercel AI SDK** (`streamObject`, `experimental_useObject`) — best-in-class for streaming partial structured JSON to React UI. Array-output mode streams complete elements as they finish
- **Anthropic SDK** native streaming — fine for server-side
- **`sse-starlette`** on FastAPI for SSE
- "tokens + structured intermediate state" pattern Vercel pioneered (4.1) becoming norm

**verify-kit verdict:** Document `streamObject`. For Python backends, document `sse-starlette` + `pydantic-ai.run_stream()`.

## 7. Eval Frameworks (FRESH ground)

- **inspect_ai** (UK AISI) — solo-test runner, model-graded + heuristic scorers, sandboxed tool eval. Strong for safety/capability evals; overkill for app-level regression
- **DeepEval** — Pytest-native, broad metric library, integrates with Confident AI SaaS for dashboards. **Best fit for CI/CD**
- **Ragas** — pure scoring library for RAG (faithfulness, context precision, answer relevancy). No dashboards. Fastest path to scored RAG
- **HELM** (Stanford) — academic holistic eval; skip unless publishing
- **LangCheck** — multilingual quality metrics; niche
- **AutoEvals** (Braintrust OSS, MIT) — standalone scorer library. Works without Braintrust. **Highly underrated** — drop-in scorers for factuality/relevance/safety, optional logging

**verify-kit verdict:** Promptfoo for declarative (already in scope). **Ship AutoEvals** as in-test scorer library. Document DeepEval for users who want pytest-native + dashboard. Document Ragas for RAG.

## 8. Local LLM for Dev

- **Ollama** has [Anthropic-compatibility shim](https://docs.ollama.com/api/anthropic-compatibility): `ANTHROPIC_BASE_URL=http://localhost:11434`, `ANTHROPIC_AUTH_TOKEN=ollama`
- For Python apps, **LiteLLM proxy** in front of Ollama is cleaner — one endpoint for cloud + local
- **LM Studio** — GUI, fine for spot-checking, not for CI
- **vLLM** — only worth it if serving production traffic

**verify-kit verdict:** Document Ollama+LiteLLM as cost-free dev loop. Don't auto-install.

## 9. Cost & Latency Awareness

- **tiktoken** — OpenAI tokenizer; doesn't work for Claude (different BPE)
- **anthropic.count_tokens()** — free API, doesn't hit rate limit, accurate for Claude 3+
- **tokencost** (AgentOps) — covers 400+ models, gives USD estimates
- **tokenx** — Python decorator (`@track_cost`) for per-function cost + latency. **Exactly the pattern verify-kit needs**

**verify-kit verdict:** **Ship tokencost + tokenx.**

## 10. Voice / Audio

- **Pipecat** (Daily) — Python-first, pipeline-of-frames model. Best for STT→LLM→TTS solo dev. SmartTurnDetection reduces interruption errors ~30% vs VAD
- **LiveKit Agents** — WebRTC-native, multi-user, requires server. Best for "agent in Zoom call"
- **VAPI / Retell** — managed voice; great DX, vendor lock-in
- **Sphinx/Vosk** — local STT fallback

User's SLNG/Gradium are TTS providers; slot **into** Pipecat as TTS processors.

**verify-kit verdict:** Document Pipecat. Don't ship — voice is opt-in.

## 11. Dual-Audience: How Human vs Agent Debugs an LLM Call

The write-side gap matters. Matrix:

| Need | Human tool | Agent tool | Unifying instrument |
|---|---|---|---|
| See input/output | Langfuse UI | log JSON | OTel span attrs |
| See cost | dashboard graph | `usage` dict | tokencost in span attrs |
| See retries | timeline | counter | structured log event |
| Replay differently | "fork this trace" | re-run script | **vcrpy cassette** + named prompt |
| Diff vs reference | visual diff | string compare | **promptfoo assertion** |

**verify-kit's job on write-side:** single `@llm_call` decorator emitting OTel spans with prompt/response/cost/latency/retry-count as attributes. Langfuse picks them up via OTel; agents grep JSON logs.

## 12. Multi-Provider Abstraction Reality

- **LiteLLM** wins for self-host
- **Bedrock Converse** AWS lock-in
- **Vercel AI SDK** wins for JS/edge
- Honest pattern users run: **`pydantic-ai` with provider list + LiteLLM as fallback proxy.** Vendor-specific features (extended thinking, prompt caching, computer use) leak through provider-specific params — abstraction helps for 80%, hurts when you need 20%

---

## (A) verify-kit LLM Add-on Stack (v0.1)

### Always Ship (7 packages)

1. **`pydantic-ai`** — agent + typed-call primitives. Replaces hand-rolled SDK wrappers
2. **`instructor`** — "I just want a Pydantic-typed response from one LLM call, no agent loop"
3. **`litellm`** — provider abstraction + retries + fallbacks + cache (sqlite default)
4. **`tokencost`** — USD-per-call pre-flight + post-flight estimates
5. **`autoevals`** (Braintrust OSS) — drop-in scorers usable from any pytest test
6. **`vcrpy` + `pytest-recording`** — record/replay LLM calls; cassettes in `tests/cassettes/`
7. **`opentelemetry-instrumentation-httpx`** — automatic span creation for every LLM call (LiteLLM also emits OTel)

### Opt-in via prompt (`verify-kit init --llm-extras=...`)

8. **`promptfoo`** (Node binary, optional install) — declarative eval CLI
9. **`deepeval`** — when user wants pytest-native scorers beyond AutoEvals
10. **`pipecat-ai`** — only when user answers "yes" to "are you building voice?"

### Document but don't install

- BAML (multi-language teams)
- DSPy (labeled eval set + optimization)
- Latitude / PromptLayer (non-engineers ship prompts)
- LangGraph / CrewAI / smolagents / agno (when pydantic-ai insufficient)
- Ollama + LiteLLM-proxy (cost-free dev loops)
- Marvin, Outlines, Mirascope (well-defined niches)

Total install footprint: **7 packages**, all OSS, all MIT/Apache-2.0, none with forced SaaS dependency.

## (B) Concrete Code Example — verify-kit-Equipped LLM Call

What writing a Pioneer/Tavily/OpenAI call should look like — typed, instrumented, traceable, replayable, fixture-tested. Same file is source + test.

```python
# backend/app/llm/creature_extract.py
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from verify_kit.llm import llm_call, cost_budget   # OTel + tokencost wrapper

class Creature(BaseModel):
    """Pioneer-extracted creature. Typed so humans read it & agents validate it."""
    name: str = Field(min_length=1, max_length=80)
    abilities: list[str] = Field(min_items=1, max_items=8)
    weakness: str

agent = Agent(
    "anthropic:claude-opus-4-7",          # one-line provider swap
    output_type=Creature,
    system_prompt="Extract a creature spec. One sentence per ability.",
    fallback_models=["openai:gpt-4o"],    # LiteLLM-routed
)

@llm_call(name="creature.extract")        # emits OTel span + Langfuse trace
@cost_budget(usd=0.02, on_exceed="raise") # tokencost pre-flight check
async def extract_creature(prompt: str) -> Creature:
    result = await agent.run(prompt)
    return result.output                  # already a validated Creature

# --- inline test: same file, run with `pytest creature_extract.py` ---
import pytest
@pytest.mark.vcr()                        # cassettes/test_extract.yaml
@pytest.mark.asyncio
async def test_extract_mirror_kraken(snapshot):
    out = await extract_creature("a mirror kraken that copies enemy spells")
    assert out.name.lower().startswith("mirror")
    assert any("copy" in a.lower() for a in out.abilities)
    assert snapshot == out.model_dump()   # syrupy fixture-compare
    # AutoEvals semantic check — same fact, different wording is fine
    from autoevals import Factuality
    score = await Factuality().eval_async(
        output=out.weakness, expected="sunlight or bright light"
    )
    assert score.score >= 0.7
```

**How human reads:** Pydantic model = spec, decorators = guarantees, test below = lived example. Zero indirection.

**How agent verifies:** `pytest --vcr-record=none` runs offline, deterministic. OTel span attributes (`prompt`, `output`, `cost_usd`, `latency_ms`, `provider`, `retries`) emitted as JSON to stdout — greppable. Failure modes typed: `pydantic.ValidationError`, `verify_kit.CostBudgetExceeded`, `autoevals.AssertionError`. No "the LLM said something weird" string-matching.

Re-running with different prompt: edit, delete cassette, re-run with `--vcr-record=new_episodes`. Different model: change `Agent("anthropic:...")` string, delete cassette, re-run.

## Sources

- [BAML vs Instructor: Structured LLM Outputs (Glukhov, Dec 2025)](https://www.glukhov.org/post/2025/12/baml-vs-instruct-for-structured-output-llm-in-python/)
- [8 Best LLM Structured Output Libraries, Ranked 2026 (Techsy)](https://techsy.io/en/blog/best-llm-structured-output-libraries)
- [Pydantic AI official docs](https://ai.pydantic.dev/)
- [PydanticAI v1: The Type-Safe Agent Framework (AgentMarketCap, April 2026)](https://agentmarketcap.ai/blog/2026/04/06/pydanticai-python-agent-framework-langgraph-crewai-comparison)
- [BoundaryML BAML GitHub](https://github.com/BoundaryML/baml)
- [Mirascope GitHub](https://github.com/mirascope/mirascope)
- [DSPy (Stanford)](https://dspy.ai/)
- [Marvin GitHub (PrefectHQ)](https://github.com/PrefectHQ/marvin)
- [Claude Agent SDK vs PydanticAI for Production (MindStudio)](https://www.mindstudio.ai/blog/agent-sdk-vs-framework-claude-pydantic-ai-production)
- [Claude Agents SDK vs OpenAI Agents SDK vs Google ADK (Composio)](https://composio.dev/content/claude-agents-sdk-vs-openai-agents-sdk-vs-google-adk)
- [AI Agents in 2026: LangGraph vs CrewAI vs Smolagents](https://dev.to/pooyagolchian/ai-agents-in-2026-langgraph-vs-crewai-vs-smolagents-with-real-benchmarks-on-local-llms-4ma1)
- [Best LLM Gateways for Engineers 2026 (Inworld)](https://inworld.ai/resources/best-llm-gateways)
- [Top 6 LiteLLM Alternatives 2026 (Eden AI)](https://www.edenai.co/post/best-alternatives-to-litellm)
- [DeepEval vs RAGAS 2026](https://genai.qa/blog/deepeval-vs-ragas/)
- [Autoevals (Braintrust docs)](https://www.braintrust.dev/docs/reference/autoevals) · [GitHub](https://github.com/braintrustdata/autoevals)
- [tokenx GitHub](https://github.com/dvlshah/tokenx)
- [tokencost (AgentOps)](https://github.com/AgentOps-AI/tokencost)
- [Vercel AI SDK Stream Protocols](https://ai-sdk.dev/docs/ai-sdk-ui/stream-protocol)
- [Ollama Anthropic compatibility](https://docs.ollama.com/api/anthropic-compatibility)
- [Eliminating Flaky Tests with VCR for LLMs](https://anaynayak.medium.com/eliminating-flaky-tests-using-vcr-tests-for-llms-a3feabf90bc5)
- [pytest-recording GitHub](https://github.com/kiwicom/pytest-recording)
- [Pipecat vs LiveKit (Cekura)](https://www.cekura.ai/blogs/pipecat-vs-livekit-the-real-difference)

## Related notes

- [[wave-1-llm-eval-frameworks]] · [[wave-2-llm-hosting]] · [[wave-4-fastapi-ecosystem]]
- [[00-architecture-overview]] · [[00-stack-decisions]]
- [[tools/pydantic-ai]] · [[tools/instructor]] · [[tools/litellm]] · [[tools/autoevals]]
