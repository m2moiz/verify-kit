---
title: OpenTelemetry for Solo-Dev Local Development
aliases: [Wave 3 - OTel, Local OTel, Jaeger, See the Flow]
tags: [research, wave-3, opentelemetry, jaeger, observability]
wave: 3
source_agent: opentelemetry-local
created: 2026-05-17
---

# OpenTelemetry for Solo Devs: "See the Flow" Locally (2025–2026)

> [!abstract] Headline
> **`docker run jaegertracing/all-in-one` is the whole local-OTel story** for solo dev — one container, in-memory storage, classic waterfall at `localhost:16686`, ~50MB idle. For non-Docker users, `otel-desktop-viewer` (single Go binary) or `otel-tui` (terminal UI) are alternatives. **W3C `traceparent` propagation from browser → backend** makes "user clicked → fetch → backend → LLM → tool → response" one trace, not two disconnected trees.

## 1. Local-First Trace Viewers — Shortlist

| Tool | What | Setup | Cost (RAM) | Fit |
|---|---|---|---|---|
| **Jaeger all-in-one** | Single Docker container; collector + query + in-memory storage + classic waterfall UI | `docker run -p 16686:16686 -p 4317:4317 -p 4318:4318 jaegertracing/all-in-one` | ~50 MB idle, can balloon to GB under load | **Excellent** |
| **otel-desktop-viewer** | Single Go binary (CtrlSpice). OTLP receiver + React UI at `localhost:8000`. DuckDB in-memory | `brew install --cask ctrlspice/tap/otel-desktop-viewer` | Tiny (<100 MB) | **Excellent** for pure trace flow |
| **otel-tui** | Terminal UI (ymtdzzz). Trace waterfalls + metrics + logs + topology in TUI | `brew install ymtdzzz/tap/otel-tui` | Tiny | **Excellent** for keyboard-driven devs |
| **SigNoz (local)** | OSS Datadog alt. Logs + metrics + traces in one app. ClickHouse backend | `docker compose up` (5+ containers) | 2–4 GB | Good, but heavy for solo |
| **Uptrace (self-host)** | OTel-native APM, ClickHouse-backed | Docker Compose | 1–2 GB | Good, lighter than SigNoz |
| **Arize Phoenix** | LLM-focused but generic OTel under hood. `localhost:6006` | `pip install arize-phoenix && phoenix serve` | ~300 MB | **Excellent** if work includes LLM calls |
| **Langfuse (self-host)** | LLM-first; has `/api/public/otel` OTLP endpoint since 3.22 | Docker Compose (Postgres + ClickHouse + app) | 2 GB+ | Good once you outgrow Phoenix |
| **Grafana Tempo + Grafana** | Production-grade trace store + Grafana UI | Docker Compose, ≥3 services | 1–2 GB | Marginal — overkill for solo |
| **otel-cli** (equinix-labs) | CLI to emit spans from shell scripts | `go install` | None | Excellent **complement**, not viewer |
| **Docker Desktop OTel** | Built-in OTLP receiver in recent Docker Desktop | Built-in | Free if Docker Desktop runs | Good, but Docker Desktop only |
| **Honeycomb dev mode** | No first-class "honeycomb-local". Free tier (20M events/mo) is local story — needs internet | Account signup | None local | Marginal for offline solo |

**Catches per tool:**
- **Jaeger:** in-memory storage = traces vanish on container restart. UI dated but proven.
- **otel-desktop-viewer:** trace-only. No logs, no metrics. Active but niche.
- **otel-tui:** can't share screenshot with teammate easily.
- **SigNoz/Uptrace:** designed to be real backend — running "just for local dev" is overkill.
- **Phoenix:** UI is LLM-shaped (prompt/response panels everywhere); generic HTTP spans render fine but feel second-class.
- **Langfuse:** Postgres + ClickHouse + worker + web = four containers minimum.

## 2. Minimum Viable Setup for "See My Request Flow"

```bash
# 1. Run Jaeger
docker run -d --rm --name jaeger \
  -p 16686:16686 -p 4317:4317 -p 4318:4318 \
  jaegertracing/all-in-one:latest

# 2. Point your app at it
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
export OTEL_SERVICE_NAME=verify-kit-backend

# 3. Auto-instrument (Python example)
uv add opentelemetry-distro opentelemetry-exporter-otlp \
       opentelemetry-instrumentation-fastapi \
       opentelemetry-instrumentation-httpx
opentelemetry-bootstrap -a install
opentelemetry-instrument uvicorn app.main:app

# 4. Open http://localhost:16686
```

No OTel Collector required — Jaeger 2.0 (Nov 2024) ships embedded collector speaking native OTLP. Only add separate Collector when you need (a) tail-based sampling, (b) fan-out to multiple backends, or (c) processors like attribute redaction. Solo dev doesn't need any.

**Logs + spans + metrics vs just spans:** for "see the flow," spans alone get 80% of value. Add metrics later only if chasing perf regressions. Logs best correlated *into* spans (each log gets `trace_id`/`span_id` injected by auto-instrumentor) rather than collected separately.

## 3. No Viewer At All — Stdout Exporters and `otel-cli`

The `ConsoleSpanExporter` (Python) / `ConsoleSpanExporter` (Node) just `print()`s each span as JSON to stdout when finished. Useful for:
- CI logs (span tree shows up alongside test output)
- Quick sanity checks ("did my instrumentation fire?")
- Agent consumption (Claude Code can grep span JSON)

**Not useful** for humans trying to see waterfall — JSON wrong shape for visual flow.

[`equinix-labs/otel-cli`](https://github.com/equinix-labs/otel-cli) lets shell scripts emit spans: `otel-cli exec --service build --name "npm install" -- npm install`. Pair with any viewer above and shell scripts join same trace as backend.

## 4. Auto-Instrumentation Worth Using 2025–2026

**Python:**
- `opentelemetry-distro` + `opentelemetry-bootstrap -a install` → installs everything detected
- Specific: `opentelemetry-instrumentation-{fastapi,httpx,requests,sqlalchemy,asyncpg,redis,anthropic,openai}`
- `FastAPIInstrumentor.instrument_app(app)` captures route name, status, duration automatically

**Node:**
- `@opentelemetry/auto-instrumentations-node` — single package pulling in HTTP, Express, Fastify, Next.js, Prisma, pg, redis, fetch
- Invoked as `node --require @opentelemetry/auto-instrumentations-node/register app.js`
- Next.js 15+ has first-class OTel via `instrumentation.ts`

**Browser (most solo devs skip):**
- `@opentelemetry/sdk-trace-web` + `@opentelemetry/instrumentation-fetch` + `@opentelemetry/instrumentation-xml-http-request`
- **What makes "user clicked here → frontend hit `/api/score` → backend called Pioneer" actually show as one trace.** Fetch instrumentor injects `traceparent` W3C header; FastAPI/Express auto-instrumentors extract it on receiving side and parent their span to it
- Without this, you get two disconnected trees and lose the "click" anchor

## 5. Is OTel Overkill for Solo Dev? Honest Answer

Two camps:

- **"You don't need OTel until you need it"** — single-process script, `print()` + stack trace beat any tracing setup. Setup tax outweighs payoff.
- **"Instrument from day one"** — moment you have 2+ services, async work, or LLM call trees with retries, structured logging stops being legible. Scrolling through 400 lines of timestamps trying to reconstruct what happened.

Honest split: **structured logging is enough until your request crosses a boundary**. Boundary = network hop, LLM provider call, background job, queue, third-party API. Instant request touches 2+ of those, traces pay for themselves on first bug.

For verify-kit's target user (solo dev building AI-flavored apps), boundaries hit fast: frontend → backend → LLM → tool call → second LLM → response. Exactly when waterfall view stops being luxury.

## 6. OTel + LLM-Specific Traces

`gen_ai.*` semantic conventions still in **Development** (not yet stable), but widely adopted as of 2025. Convention defines spans for LLM client calls with attributes like `gen_ai.system`, `gen_ai.request.model`, `gen_ai.usage.input_tokens`, child events for prompts/completions.

Working instrumentation today:
- `opentelemetry-instrumentation-anthropic` and `opentelemetry-instrumentation-openai` (community + Traceloop's OpenLLMetry)
- Arize's `openinference-instrumentation-{anthropic,openai,langchain,llama-index}` set
- Auto-captures model, token counts, finish reason, latency, and (opt-in via `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true`) actual prompt/response

Backends consuming natively: **Langfuse**, **Phoenix**, **Honeycomb**, **Datadog LLM Observability** (added 2026 for v1.37+).

Jaeger renders them as generic spans — you see `gen_ai.request.model = claude-sonnet-4-7` as attribute. Fine for "see the flow," limited for token/cost analysis.

## 7. VS Code / IDE Integration with Traces

**Weakest part of ecosystem in 2026:**
- No mainstream VS Code extension does "click span → jump to source line"
- Closest is OpenTelemetry's `code.filepath` / `code.lineno` semantic attributes — auto-instrumentors populate them, no editor consumes
- Honeycomb has "Source" code panel in UI; Tempo+Grafana can deep-link if you wire manually

Trace-to-code navigation still manual ⌘-click in file path span attribute hints at. Real gap and real reason agent-based consumption (Claude Code reading span JSON) is currently *better* than human IDE consumption.

## 8. Docker Compose / DevContainer Patterns

Emerging convention is side-file:

```yaml
# docker-compose.observability.yml
services:
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports: ["16686:16686", "4317:4317", "4318:4318"]
    environment: [COLLECTOR_OTLP_ENABLED=true]
```

Brought up with `docker compose -f docker-compose.observability.yml up -d`, or wrapped in `just trace-up` / `make trace-up`. Tear down with `just trace-down`. Per-run reset (drop container) is right default for solo — persistent state cluttered fast.

DevContainers can bake this in via `dockerComposeFile` listing both `docker-compose.yml` and observability file, so every contributor gets it.

## 9. Honest Tradeoffs

- **RAM:** Jaeger all-in-one idles ~50 MB. otel-desktop-viewer/otel-tui under 100 MB. SigNoz/Langfuse 2+ GB. On 16 GB laptop, Jaeger or otel-desktop-viewer free; SigNoz competes with IDE
- **Tracing overhead in dev:** Auto-instrumentation adds ~1–3% latency, well under typical noise. Solo dev should run **100% sampling**
- **Noise:** After ~50 requests, trace list gets long. Jaeger's service+operation filter handles it. otel-desktop-viewer wipes on restart — feature for solo
- **When dev traces become noise:** when you stop reading them. Signal to either (a) tighten span names so waterfall tells story or (b) move to real backend supporting queries

## Recommendation for verify-kit

### (A) Ships by default in generated project

- OTel SDK + auto-instrumentation in `pyproject.toml`/`package.json` — **installed but inert** unless `OTEL_EXPORTER_OTLP_ENDPOINT` set
- `ConsoleSpanExporter` enabled when `VERIFY_KIT_TRACE_STDOUT=1` — agent-driven workflow can grep spans without external dependency
- Browser SDK wired in frontend template with `traceparent` propagation to backend. Disabled-by-default toggle
- Span names use verify-kit convention: `<service>.<verb> <noun>` (e.g. `backend.POST /api/score`, `llm.anthropic.messages.create`, `tool.tavily.search`). What makes waterfall readable

### (B) One-command opt-in for visual UI

Ship `docker-compose.observability.yml` with **Jaeger all-in-one** and `just trace-up` / `just trace-down` recipe. Why Jaeger over otel-desktop-viewer as default:
- Universally recognized — newcomers Google "Jaeger" and find docs
- Survives container restarts for duration of session
- Real URL (`localhost:16686`) you can share in Loom

Document otel-desktop-viewer as **"I don't want Docker"** alternative (single binary). Document otel-tui as **"I live in terminal"** alternative.

### (C) When to graduate to real backend

Tell user to migrate when *any* of:
- Shipping to users (need persistent storage, alerting, query language)
- LLM-heavy work + want token/cost analytics → **Langfuse** (LLM-native) or **Phoenix** (eval + tracing)
- Working with teammate who needs to see same traces → any hosted backend
- Want >24h retention or full-text search across all spans → **SigNoz** (self-host) or **Honeycomb** (free tier 20M events/mo)

### Concrete ASCII mockup — "see the flow" terminal output

When `VERIFY_KIT_TRACE_STDOUT=1` and no Jaeger running, verify-kit renders this on request completion:

```
TRACE  a1f3c2d8e4b69e21  POST /api/score  624ms  OK
├─ frontend.click "Run Score"                              0ms     ▏
├─ frontend.fetch POST /api/score                          2ms   ▎      [traceparent injected]
│  └─ backend.POST /api/score                              4ms   ▎▎▎▎▎▎▎▎▎▎▎▎▎▎▎▎▎▎▎▎▎▎▎▎  616ms
│     ├─ auth.verify_token                                 5ms   ▏                          3ms
│     ├─ llm.anthropic.messages.create                    12ms        ▎▎▎▎▎▎▎▎▎▎▎▎▎▎▎▎     412ms
│     │     gen_ai.request.model=claude-sonnet-4-7
│     │     gen_ai.usage.input_tokens=1,204
│     │     gen_ai.usage.output_tokens=287
│     ├─ tool.tavily.search                              430ms                       ▎▎▎▎    98ms
│     │     query="recent OTel viewers"
│     │     results=8
│     ├─ scorer.rank_results                             532ms                            ▎  47ms
│     └─ db.insert score_event                           582ms                             ▏ 22ms
└─ frontend.render <ScoreCard/>                          620ms                              ▏ 4ms

LATENCY BREAKDOWN
  llm.anthropic         412ms  66%  ████████████████▏
  tool.tavily            98ms  16%  ███▉
  scorer.rank            47ms   8%  █▉
  db.insert              22ms   4%  ▉
  other                  45ms   7%  █▊
```

Bar visualization and percentage breakdown makes it **glanceable** in way raw span JSON or even Jaeger's web UI isn't — human dev tailing logs sees shape of request without leaving terminal.

## Sources

- [otel-desktop-viewer (CtrlSpice)](https://github.com/CtrlSpice/otel-desktop-viewer)
- [otel-tui (ymtdzzz)](https://github.com/ymtdzzz/otel-tui)
- [otel-cli (equinix-labs)](https://github.com/equinix-labs/otel-cli)
- [Jaeger Getting Started](https://www.jaegertracing.io/docs/1.76/getting-started/)
- [Dev Container with OTel Collector + Jaeger](https://oneuptime.com/blog/post/2026-02-06-dev-container-otel-collector-jaeger/view)
- [SigNoz GitHub](https://github.com/SigNoz/signoz)
- [Top 6 Jaeger alternatives (SigNoz)](https://signoz.io/comparisons/jaeger-alternatives/)
- [Arize Phoenix](https://github.com/Arize-ai/phoenix)
- [Langfuse OTel integration](https://langfuse.com/integrations/native/opentelemetry)
- [OTel GenAI semantic conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/)
- [OpenTelemetry FastAPI instrumentation](https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/fastapi/fastapi.html)
- [W3C Trace Context spec](https://www.w3.org/TR/trace-context/)
- [When to use OTel vs simple logging](https://oneuptime.com/blog/post/2026-02-06-opentelemetry-vs-simple-application-logging/view)
- [Tracing shell scripts with OTel (Howard John)](https://blog.howardjohn.info/posts/shell-tracing/)

## Related notes

- [[wave-3-human-friendly-logging]] · [[wave-1-llm-eval-frameworks]] · [[wave-2-llm-hosting]]
- [[00-architecture-overview]] · [[00-stack-decisions]]
- [[tools/jaeger]]
