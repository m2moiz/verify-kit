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
 *   - Exposes window.__verifyKitOtelForceFlush(): Promise<void> so Playwright
 *     can await a full flush before querying Jaeger (F3).
 *
 * PER-RUN UUID SPAN ATTRIBUTE (BL-5)
 * ───────────────────────────────────
 * When a trace_test_id query param is present in the page URL, initOtel()
 * reads it and attaches it as a "verify_kit.trace_test_id" attribute on
 * each FetchInstrumentation browser span. This allows the harness to assert
 * an explicit WEB_SERVICE_NAME browser span — not just the api server span —
 * so a backend-only trace cannot pass the connectivity assertion (BL-5).
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
import { resourceFromAttributes } from "@opentelemetry/resources";
import { ATTR_SERVICE_NAME } from "@opentelemetry/semantic-conventions";
import { trace, context, SpanStatusCode } from "@opentelemetry/api";
import { WEB_SERVICE_NAME } from "@/config";

// Module-level guard: prevents double-registration when initOtel() is called
// more than once (e.g. React StrictMode double-invoke in development).
let _initialised = false;

// Hold provider reference so window.__verifyKitOtelForceFlush can call forceFlush.
let _provider: WebTracerProvider | null = null;

/**
 * Initialise the browser OTel SDK.
 *
 * Call once at application startup, before createRoot(), so instrumentation is
 * active before the first fetch() can fire.
 *
 * When VITE_OTEL_EXPORTER_OTLP_ENDPOINT is falsy (the default), this function
 * returns immediately and registers nothing.
 *
 * When the SDK is initialised, window.__verifyKitOtelForceFlush is assigned so
 * Playwright can await a complete BatchSpanProcessor flush before querying
 * Jaeger for the trace (F3).
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
    // window.__verifyKitOtelForceFlush is intentionally NOT set on the inert path.
    return;
  }

  // Active path: endpoint is set at build time.
  const exporter = new OTLPTraceExporter({ url: endpoint });
  const resource = resourceFromAttributes({ [ATTR_SERVICE_NAME]: WEB_SERVICE_NAME });
  const provider = new WebTracerProvider({
    resource,
    spanProcessors: [new BatchSpanProcessor(exporter)],
  });

  provider.register({
    contextManager: new ZoneContextManager(),
  });

  // Keep a module-level reference so the force-flush handle can call it.
  _provider = provider;

  // F3: expose window.__verifyKitOtelForceFlush() so Playwright can await a
  // complete BatchSpanProcessor flush before querying Jaeger for the trace.
  (window as unknown as Record<string, unknown>).__verifyKitOtelForceFlush =
    (): Promise<void> => {
      return _provider ? _provider.forceFlush() : Promise.resolve();
    };

  // BL-5: read the per-run trace_test_id from the page URL query params.
  // When present, add it as a span attribute on the browser fetch span so the
  // harness can assert an explicit WEB_SERVICE_NAME span (not just the server span).
  const traceTestId = new URLSearchParams(window.location.search).get(
    "trace_test_id"
  );

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
        // BL-5: attach trace_test_id as a span attribute on every fetch span
        // so the harness can find a browser span carrying the per-run marker.
        applyCustomAttributesOnSpan: traceTestId
          ? (span) => {
              span.setAttribute(
                "verify_kit.trace_test_id",
                traceTestId
              );
            }
          : undefined,
      }),
    ],
  });
}
