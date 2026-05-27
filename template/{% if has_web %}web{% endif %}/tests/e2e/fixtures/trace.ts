import { test as base, expect } from "@playwright/test";
import { randomBytes } from "node:crypto";

/**
 * Generate a W3C traceparent header value.
 * Format: version-traceId-parentId-flags
 * Reference: https://www.w3.org/TR/trace-context/
 */
export function newTraceparent(): string {
  const traceId = randomBytes(16).toString("hex");
  const spanId = randomBytes(8).toString("hex");
  return `00-${traceId}-${spanId}-01`;
}

type TraceFixtures = { traceparent: string };

/**
 * Extended test with `traceparent` fixture.
 * Injects the header on every page navigation via setExtraHTTPHeaders.
 * NOTE: Header-injection ONLY. NO @opentelemetry/sdk-trace-web SDK init
 * (deferred to v0.3 per 07-CONTEXT.md Deferred Ideas).
 */
export const test = base.extend<TraceFixtures>({
  traceparent: async ({ page }, use) => {
    const tp = newTraceparent();
    await page.setExtraHTTPHeaders({ traceparent: tp });
    await use(tp);
  },
});

export { expect };
