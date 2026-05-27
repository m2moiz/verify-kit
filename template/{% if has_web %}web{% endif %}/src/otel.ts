/**
 * Browser OpenTelemetry SDK initialisation — inert by default.
 *
 * INERT-BY-DEFAULT CONTRACT
 * ─────────────────────────
 * When VITE_OTEL_EXPORTER_OTLP_ENDPOINT is NOT set at build time, this module
 * is a complete no-op: no WebTracerProvider is registered, no span processor is
 * created, no exporter is constructed, and no network traffic is emitted.
 * Tree-shaking drops the exporter code path from the production bundle.
 *
 * ACTIVATION
 * ──────────
 * Set VITE_OTEL_EXPORTER_OTLP_ENDPOINT (e.g. "http://localhost:4318/v1/traces")
 * at Vite build time (or in .env.local for dev).  When present, initOtel():
 *   - Creates a WebTracerProvider with a BatchSpanProcessor → OTLPTraceExporter.
 *   - Registers a ZoneContextManager for async-context propagation.
 *   - Activates FetchInstrumentation so every fetch() call auto-creates a span
 *     and injects a W3C traceparent header.
 *
 * IDEMPOTENCY
 * ───────────
 * A module-level guard prevents double-registration (React StrictMode safe).
 *
 * NOTE: This file is a plain .ts file — NOT .ts.jinja2.
 * Copier conditionals are handled via runtime VITE_* env reads, not Jinja
 * templates (Pitfall §1 single-jinja-TS-file firewall: only vite.config.ts.jinja2
 * and src/config.ts.jinja2 may carry the .jinja2 extension).
 */

// BatchSpanProcessor is re-exported from @opentelemetry/sdk-trace-web
// (which itself re-exports from @opentelemetry/sdk-trace-base).
import { WebTracerProvider, BatchSpanProcessor } from "@opentelemetry/sdk-trace-web";
import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-http";
import { ZoneContextManager } from "@opentelemetry/context-zone";
import { registerInstrumentations } from "@opentelemetry/instrumentation";
import { FetchInstrumentation } from "@opentelemetry/instrumentation-fetch";

// Module-level guard: prevents double-registration when initOtel() is called
// more than once (e.g. React StrictMode double-invoke in development).
let _initialised = false;

/**
 * Initialise the browser OTel SDK.
 *
 * Call once at application startup, before createRoot(), so instrumentation is
 * active before the first fetch() can fire.
 *
 * When VITE_OTEL_EXPORTER_OTLP_ENDPOINT is falsy (the default), this function
 * returns immediately and registers nothing.
 */
export function initOtel(): void {
  // Idempotency guard.
  if (_initialised) return;
  _initialised = true;

  // Vite statically replaces VITE_-prefixed env vars at build time.
  // When the env var is absent the value is undefined (falsy) — inert path.
  const endpoint: string | undefined =
    import.meta.env.VITE_OTEL_EXPORTER_OTLP_ENDPOINT;

  if (!endpoint) {
    // Inert — no provider, no exporter, no network traffic.
    return;
  }

  // Active path: endpoint is set at build time.
  const exporter = new OTLPTraceExporter({ url: endpoint });
  const provider = new WebTracerProvider({
    spanProcessors: [new BatchSpanProcessor(exporter)],
  });

  provider.register({
    contextManager: new ZoneContextManager(),
  });

  // Auto-instrument fetch() calls — injects W3C traceparent headers and
  // creates spans for outbound HTTP requests.
  registerInstrumentations({
    instrumentations: [
      new FetchInstrumentation({
        // Inject traceparent on same-origin requests and localhost (dev servers).
        propagateTraceHeaderCorsUrls: [
          /^https?:\/\/localhost/,
          new RegExp(`^${window.location.origin}`),
        ],
      }),
    ],
  });
}
