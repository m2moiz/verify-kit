---
title: LLM/AI Application Evaluation Frameworks
aliases: [Wave 1 - LLM Eval, LLM Observability Frameworks]
tags: [research, wave-1, llm, eval, observability]
wave: 1
source_agent: llm-eval-frameworks
created: 2026-05-17
---

# AI Application Verification & Evaluation Stack: 2024–2026 Landscape

> [!abstract] Headline
> **OpenLLMetry → Langfuse → Promptfoo → vcrpy → Helicone** is the OSS-first stack. Self-host Langfuse on a Hetzner CX32 for ~$8/mo; everything else is free. The "AI-app verification harness" composes from existing primitives, not a single product.

## 1. LLM Observability Platforms

| Tool | OSS/SaaS | What | Pricing | Agent-loop fit | Limitation |
|---|---|---|---|---|---|
| **[Langfuse](https://langfuse.com)** | OSS (MIT) + managed | Trace every LLM/tool call, prompts/completions/tokens/cost, dataset+eval runs, prompt versioning, LLM-as-judge | Free self-host; managed free 50k events/mo; Pro $59/mo | **Excellent** — best OSS API for programmatic trace queries | Self-host needs Postgres + ClickHouse + Redis + S3; non-trivial ops |
| **[Helicone](https://helicone.ai)** | OSS + SaaS | One-line proxy in front of provider APIs; logs, cost, caching, rate-limit, budget alerts | Free 10k req/mo; Pro $20/mo | **Good** — easiest cost guardrails | Proxy-based; non-HTTP providers need extra work; eval features thinner |
| **[Arize Phoenix](https://phoenix.arize.com)** | OSS (Elastic 2.0) | OpenTelemetry-native trace viewer + eval runner | Free self-host; Arize AX SaaS paid | **Excellent** for OTel-aligned stacks | Engineer-grade UI; SaaS upsell can confuse OSS story |
| **[LangSmith](https://smith.langchain.com)** | SaaS only | Zero-config for LangChain/LangGraph | Free 5k traces/mo, 1 user; $39/user/mo | **Good** if on LangChain; mediocre otherwise | Locked to LangChain; self-host enterprise-paywalled |
| **[Braintrust](https://braintrust.dev)** | SaaS | Eval-first platform: datasets, scorers, CI deployment gates | Free 1M spans/mo; Pro $249/mo | **Excellent** for CI gating; opinionated workflow | No self-host, no free Pro features; vendor lock-in |
| **[Weights & Biases Weave](https://wandb.ai/site/weave)** | SaaS (W&B account) | Trace + eval inside W&B | Free hobby tier | Marginal for pure app-layer LLM work | Heavy if not already W&B shop |
| **[Comet Opik](https://github.com/comet-ml/opik)** | OSS (Apache 2.0) | Trace + eval + prompt playground; LLM-as-judge built in | Free self-host; managed free tier | **Good** — younger but cleanly OSS | Smaller community than Langfuse |
| **[OpenLLMetry / Traceloop](https://www.traceloop.com)** | OSS SDK + SaaS backend | OpenTelemetry instrumentation library; standard `gen_ai.*` spans; ships to *any* OTel backend | OSS free; SaaS varies | **Excellent** as instrumentation layer | Just the wire format; still pick a backend |
| **[Lunary](https://lunary.ai)** | OSS + SaaS | Lightweight trace + cost + prompt mgmt | Free self-host; Pro $20/mo | Good for simple apps | Less depth than Langfuse |
| **[Honeyhive](https://honeyhive.ai)** | SaaS | Trace + eval + dataset + experiments | Custom | Marginal for solo dev | No real OSS path; pricing opaque |

**Honest 2025–2026 consensus:** **Langfuse is the default OSS pick**; **Braintrust dominates SaaS for eval-CI**; **Phoenix wins if you commit to OpenTelemetry**; **Helicone is the cheapest fastest "I just need to see what's happening" answer**.

## 2. LLM Eval Frameworks

| Tool | OSS | Sweet spot | Agent-loop fit | Limitation |
|---|---|---|---|---|
| **[Promptfoo](https://github.com/promptfoo/promptfoo)** | MIT | YAML-declarative eval matrix across N models × M prompts × K test cases; CLI-first; red-team mode | **Excellent** — declarative configs perfect for agent-edited diffs | Node-centric; large prompt graphs get YAML-noisy |
| **[DeepEval](https://github.com/confident-ai/deepeval)** | Apache 2.0 | "pytest for LLMs" — 30+ built-in metrics (G-Eval, faithfulness, hallucination, toxicity) | **Excellent** — reuses existing pytest infra | LLM-as-judge metrics cost money; quality varies by judge model |
| **[RAGAS](https://github.com/explodinggradients/ragas)** | Apache 2.0 | RAG-specific: faithfulness, context precision/recall, answer relevancy; extends to tool-use | **Good** if you have retrieval; overkill otherwise | Narrow focus; metrics need calibration |
| **[Inspect AI (UK AISI)](https://inspect.aisi.org.uk/)** | MIT | Frontier-eval framework; sandboxed agent eval, 200+ pre-built evals, Agent Bridge for OpenAI/LangChain/Pydantic AI; used by Anthropic, DeepMind | **Excellent** for serious agent eval | Heavier setup; aimed at frontier model evaluation |
| **[OpenAI Evals](https://github.com/openai/evals)** | MIT | Reference library; YAML + Python registry | Marginal — historical; teams moved to Promptfoo/DeepEval | Slow updates, OpenAI-centric |
| **[Anthropic eval cookbook](https://docs.anthropic.com/en/docs/test-and-evaluate/develop-tests)** | Docs/snippets | Strong guidance: code-graded → LLM-judge → human, ask judge to reason before scoring | N/A — methodology not a tool | Not a framework you install |

## 3. Agent Testing & Trace Replay

- **[AgentOps](https://www.agentops.ai/)** — SaaS + OSS SDK. Session replay with time-travel debugging for multi-agent runs. Solid for "did agent call tools in right order." Less mature CI integration.
- **Inspect AI Agent Bridge** — best OSS for trajectory-level assertions; can wrap external CLIs (Claude Code, Codex) as evaluated agents
- **Langfuse + dataset replay** — store production traces, replay with new prompt/model, diff trajectories
- **2025 research warning** (Konstantinou et al., ICST 2025): LLM-generated assertions tend to encode current buggy behavior. Human-curated golden traces still matter.

## 4. Prompt Regression & Cassette Replay

- **[Promptfoo](https://promptfoo.dev)** — golden-dataset regression native; `npx promptfoo eval` in CI fails build if scores drop
- **[vcrpy](https://vcrpy.readthedocs.io/)** — generic HTTP cassette recorder. Works fine for any provider using HTTP. **Critical caveat:** default config writes API keys to YAML — must add `before_record_request` filter to scrub `authorization` headers
- **[vcr-langchain](https://github.com/amosjyng/vcr-langchain)** — decorator-based for LangChain
- **[baml_vcr](https://github.com/gr-b/baml_vcr)** — BAML-specific
- **PromptLayer** — SaaS prompt registry with diff/regression

**Pattern that works:** record cassettes for happy-path flows, replay in pre-commit hooks (~zero latency, zero cost), run small live eval set nightly to catch provider drift.

## 5. Cost / Latency Observability Beyond Provider Dashboards

- **Helicone** — budget alerts + per-virtual-key attribution; cheapest path to "alert me when feature crosses $X/day"
- **Langfuse** — token + cost on every span; tag traces with `feature_name`, group by tag
- **LangWatch** — explicitly markets per-feature cost attribution with eval context
- **OpenLLMetry → any OTel backend (Grafana, Datadog, Honeycomb)** — cheapest extension of existing APM

**Actionable pattern:** tag every trace with `feature`, `user_tier`, `prompt_version`; alert on `cost_per_user_session_p95` rather than total spend.

## 6. The "Agent-Drives-the-Harness" Pattern

Bleeding-edge. What exists:

- **[Arize's "self-improving agents"](https://arize.com/blog/closing-the-loop-coding-agents-telemetry-and-the-path-to-self-improving-software/)** — describes the loop: coding agent edits code → runs evals → queries traces via API → iterates
- **["Harness Engineering" — Martin Fowler / Birgitta Böckeler](https://martinfowler.com/articles/harness-engineering.html)** — canonical framing: *guides* (feedforward constraints) plus *sensors* (post-action feedback)
- **Langfuse SDK** — trace queries first-class; agent can `langfuse.fetch_traces(name="my_feature", from=ts)` after smoke test and assert latency/cost/output
- **Promptfoo + GitHub Action** — Claude Code can edit `promptfoo.config.yaml`, push, read CI output

No tool packages this end-to-end. Assemble: `Promptfoo (gates) + Langfuse SDK (trace queries) + vcrpy (deterministic replay)`.

## 7. Official Vendor Guidance (2025–2026)

- **[Anthropic eval cookbook](https://docs.anthropic.com/en/docs/test-and-evaluate/develop-tests)** — define success criteria first; prefer volume of automated graders over hand-graded; have LLM judges reason before scoring; combine code-grade + LLM-grade + human-spot-check
- **[OpenAI × Anthropic joint eval (Aug 2025)](https://openai.com/index/openai-anthropic-safety-evaluation/)** — established cross-lab eval pattern
- **Vercel AI SDK** — recommends Braintrust integration for AI SDK traces
- **OpenTelemetry GenAI SIG** — `gen_ai.*` semantic conventions now stable; `gen_ai.prompt`/`gen_ai.completion` attributes **deprecated in v1.38.0** — use new event-based logging

## Recommended Stack for Solo Dev with Many AI-Heavy Projects

Optimized for: OSS-default, reusable across projects, agent-drivable, low ops burden.

1. **OpenLLMetry SDK** ([traceloop/openllmetry](https://github.com/traceloop/openllmetry)) for instrumentation. Standard `gen_ai.*` spans; works with any backend.
2. **Langfuse (self-hosted, single Docker compose)** as trace/eval/dataset backend. OSS, queryable API, prompt versioning, LLM-judge built in.
3. **Promptfoo** for declarative regression eval in CI. YAML config in each repo; `promptfoo-action` blocks PRs on score drops.
4. **vcrpy** (with API-key scrubbing filter) for deterministic test fixtures. Record happy-path flows once; replay in pre-commit/pytest in milliseconds with zero API cost. Re-record nightly against live providers.
5. **Helicone** (free tier, proxy mode) as **cheap second pair of eyes** for cost alerts. Drops in front of any HTTP provider in one line.

**Optional 6th when shipping autonomous agents:** **Inspect AI** for trajectory-level evals — overkill until multi-step agents in production, but right answer when you do.

This stack composes: OpenLLMetry feeds Langfuse, Langfuse holds golden datasets Promptfoo runs against, vcrpy keeps unit tests deterministic, Helicone watches the wallet. Total monthly cost at solo-dev scale: **~$0** (all free tiers / self-host). Claude Code agent can edit promptfoo configs, run pytest (which replays vcr cassettes), and query `langfuse.fetch_traces()` to verify changes.

## Sources

- [Langfuse alternatives — Braintrust](https://www.braintrust.dev/articles/langfuse-alternatives-2026)
- [Helicone observability guide](https://www.helicone.ai/blog/the-complete-guide-to-LLM-observability-platforms)
- [Latitude: best observability for agents 2026](https://latitude.so/blog/best-llm-observability-tools-agents-latitude-vs-langfuse-langsmith)
- [DeepEval alternatives 2026](https://deepeval.com/blog/deepeval-alternatives-compared)
- [Promptfoo GitHub](https://github.com/promptfoo/promptfoo)
- [Inspect AI](https://inspect.aisi.org.uk/) · [GitHub](https://github.com/UKGovernmentBEIS/inspect_ai)
- [OpenLLMetry GitHub](https://github.com/traceloop/openllmetry)
- [OpenTelemetry GenAI semconv](https://opentelemetry.io/docs/specs/semconv/gen-ai/)
- [vcrpy docs](https://vcrpy.readthedocs.io/en/latest/usage.html)
- [vcr-langchain](https://github.com/amosjyng/vcr-langchain)
- [Eliminating flaky LLM tests with VCR](https://anaynayak.medium.com/eliminating-flaky-tests-using-vcr-tests-for-llms-a3feabf90bc5)
- [AgentOps](https://www.agentops.ai/)
- [Arize: self-improving coding agents harness](https://arize.com/blog/closing-the-loop-coding-agents-telemetry-and-the-path-to-self-improving-software/)
- [Martin Fowler: Harness Engineering](https://martinfowler.com/articles/harness-engineering.html)
- [Anthropic eval docs](https://docs.anthropic.com/en/docs/test-and-evaluate/develop-tests)
- [Promptfoo CI/CD docs](https://www.promptfoo.dev/docs/integrations/ci-cd/)
- [Langfuse cost tracking](https://langfuse.com/docs/observability/features/token-and-cost-tracking)

## Related notes

- [[wave-1-general-verification-harnesses]] · [[wave-2-llm-hosting]] · [[wave-4-ai-sdk-ergonomics]]
- [[00-architecture-overview]] · [[00-stack-decisions]]
- [[tools/langfuse]] · [[tools/promptfoo]]
