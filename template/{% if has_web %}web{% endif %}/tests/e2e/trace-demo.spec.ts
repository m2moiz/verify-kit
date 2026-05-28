/**
 * trace-demo.spec.ts — real-browser OTel trace driver for the harness check.
 *
 * PURPOSE (D-01, BL-5, F3)
 * ─────────────────────────
 * This spec drives a REAL browser click on /trace-demo?trace_test_id=<uuid>
 * with the browser OTel SDK ENABLED (VITE_OTEL_EXPORTER_OTLP_ENDPOINT set at
 * build time pointing at Jaeger :4318). It then awaits
 * window.__verifyKitOtelForceFlush() to ensure all browser spans have been
 * exported before the harness queries Jaeger for the trace.
 *
 * The per-run UUID passed as trace_test_id is written to a JSON file so the
 * Python harness check (web.otel_trace) can read it and query Jaeger by tag.
 *
 * WHEN VITE_OTEL_EXPORTER_OTLP_ENDPOINT IS UNSET
 * ────────────────────────────────────────────────
 * When the endpoint env var is absent (regular dev / Vitest runs), otel.ts
 * stays inert and window.__verifyKitOtelForceFlush is not set. In that case
 * this spec skips gracefully — it is only meaningful when the SDK is active.
 *
 * NOTE: This file is a plain .ts file — NOT .ts.jinja2.
 * The spec runs inside the mcr.microsoft.com/playwright:v1.60.0-jammy image
 * when the web.otel_trace harness check invokes it (the SAME pinned image as
 * web.lost_pixel per web.py — ADV-2 confirmed sound).
 */
import { test, expect } from "@playwright/test";
import { randomUUID } from "node:crypto";
import { mkdirSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

// The output file read by the Python harness check (web.otel_trace) to get
// the per-run trace_test_id for its Jaeger tag query.
const TRACE_TEST_ID_OUTPUT = resolve("../.verify/web/trace_test_id.json");

test("trace-demo real-click OTel driver", async ({ page }) => {
  // Generate a per-run UUID for the trace correlation marker.
  const traceTestId = randomUUID();

  // Navigate with the trace_test_id query param so otel.ts can attach it as
  // a span attribute on the browser fetch span (BL-5).
  // VITE_OTEL_EXPORTER_OTLP_ENDPOINT must be set in the Vite build for the
  // browser SDK to be active; the playwright.config.ts webServer command must
  // include it when running under web.otel_trace.
  await page.goto(`/?trace_test_id=${encodeURIComponent(traceTestId)}`);

  // Skip gracefully when the SDK is not active (endpoint not set at build time).
  const sdkActive = await page.evaluate(() => {
    return typeof (window as unknown as Record<string, unknown>).__verifyKitOtelForceFlush === "function";
  });

  test.skip(
    !sdkActive,
    `window.__verifyKitOtelForceFlush not defined — ` +
      `VITE_OTEL_EXPORTER_OTLP_ENDPOINT was not set at build time. ` +
      `This spec only runs when the browser OTel SDK is active.`
  );

  // Click the "Fire test fetch" button — this triggers a real fetch() to
  // /api/trace-demo?trace_test_id=<uuid> which creates a browser client span.
  const traceButton = page.getByRole("button", { name: /fire test fetch/i });
  await expect(traceButton).toBeVisible({ timeout: 5_000 });
  await traceButton.click();

  // Wait briefly for the fetch to complete (toast appears on success).
  await page.waitForTimeout(500);

  // Await window.__verifyKitOtelForceFlush() to ensure the BatchSpanProcessor
  // has exported all spans to Jaeger before the harness queries by tag (F3).
  await page.evaluate(async () => {
    const flush = (window as unknown as Record<string, unknown>).__verifyKitOtelForceFlush;
    if (typeof flush === "function") {
      await flush();
    }
  });

  // Write the trace_test_id to disk so the Python harness can read it.
  mkdirSync(resolve("../.verify/web"), { recursive: true });
  writeFileSync(
    TRACE_TEST_ID_OUTPUT,
    JSON.stringify({ trace_test_id: traceTestId, timestamp: Date.now() }, null, 2)
  );

  // Basic smoke: page should still show the gallery (not an error page).
  await expect(page.locator("h1")).toContainText("Component Gallery", {
    timeout: 5_000,
  });
});
