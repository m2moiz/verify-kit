---
title: Jaeger
aliases: [jaeger-all-in-one]
tags: [verify-kit, tools, observability, universal-foundation]
created: 2026-05-18
status: ALWAYS-SHIP
layer: Universal Foundation
phase_introduced: Phase 2
---

# 🐺 Jaeger

> [!abstract] One-line summary
> Open-source distributed tracing — Jaeger all-in-one Docker container is the default trace viewer for `just trace-up`.

## What it does

Jaeger is the canonical OpenTelemetry-compatible trace storage + UI. The `jaegertracing/all-in-one` Docker image bundles agent + collector + query UI in a single container, exposing the UI at `localhost:16686` and accepting OTLP at gRPC port `4317` / HTTP port `4318`.

## Why we picked it

For local observability (Phase 2's OBS-02 / OBS-03), Jaeger all-in-one is the simplest "I want to see traces" UI:

- ✅ One container, two ports
- ✅ OTLP-native (no custom exporter)
- ✅ Free, mature, broadly known
- ✅ Same image used in dev + Backend add-on's `docker-compose.yml`

| Alternative | Why secondary |
|---|---|
| `otel-desktop-viewer` | No Docker required — documented as the non-Docker alternative in OBS-05 README |
| `otel-tui` | Terminal-only viewer; for `just trace --last` in terminal contexts |
| Tempo / Honeycomb / Datadog | SaaS or heavier; appropriate when you outgrow Jaeger |
| Zipkin | Older protocol; OTel maps to it but Jaeger is more native |

See [[agent-reports/wave-3-opentelemetry-local]].

## Usage in verify-kit

Phase 2 ships `just trace-up` and `just trace-down`:

```just
# Bring up Jaeger all-in-one on localhost:16686
trace-up:
    docker run -d --name jaeger \
      -e COLLECTOR_OTLP_ENABLED=true \
      -p 16686:16686 \
      -p 4317:4317 \
      -p 4318:4318 \
      jaegertracing/all-in-one:1.62

# Tear it down
trace-down:
    docker stop jaeger && docker rm jaeger
```

`just trace --last` uses the Jaeger HTTP query API (`/api/traces?service=verify-kit&limit=1`) and renders the most recent trace as a Rich `Tree` waterfall in the terminal — without leaving the shell.

When `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317` is set, the harness's OTel SDK exports spans to Jaeger. When unset, the SDK is inert (see [[00-stack-decisions#OpenTelemetry (installed but inert)]]).

## Install (for verify-kit consumers)

Docker is the only requirement. macOS / Linux users with Docker Desktop or Colima can run `just trace-up` directly. Non-Docker users follow OBS-05's README pointing to `otel-desktop-viewer` or `otel-tui`.

## Gotchas

- **All-in-one image is dev-only** — for production tracing, run the collector / query / storage components separately
- **Memory storage by default** — Jaeger all-in-one stores traces in memory and discards on restart; that's fine for dev verification
- **Port conflicts** — 16686 + 4317 + 4318 are commonly taken (Grafana, etc.); set `JAEGER_UI_PORT` / `OTLP_GRPC_PORT` env vars in the recipe if needed
- **`just trace --last` requires Jaeger to be up** — gracefully degrade with "Jaeger is not running — run `just trace-up` first" when the HTTP query API times out

## Key docs

- Getting started: <https://www.jaegertracing.io/docs/latest/getting-started/>
- All-in-one image: <https://hub.docker.com/r/jaegertracing/all-in-one>
- HTTP query API: <https://www.jaegertracing.io/docs/latest/apis/#http-json-internal>

## Related notes

- [[00-stack-decisions#OpenTelemetry (installed but inert)]] — role in observability
- [[agent-reports/wave-3-opentelemetry-local]] — wave context
- [[tools/openllmetry]] — what emits the spans Jaeger displays
