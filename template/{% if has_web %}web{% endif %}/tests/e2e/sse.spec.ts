/**
 * SSE EventSource E2E assertion — DEV-W03 / ROADMAP SC-2 (second half).
 *
 * This spec verifies that at least one MessageEvent arrives on the EventSource
 * subscriber (events.ts) within 3 seconds.
 *
 * POLARITY NOTE: This spec ships ONLY in the has_web + has_backend polarity.
 * events.ts is excluded by copier.yml when has_backend=false, so this spec is
 * also excluded under the same guard (see Task 2 / copier.yml _exclude).
 *
 * URL NOTE: The EventSource target is http://localhost:8000/__debug/events —
 * an absolute URL that bypasses Vite's dev proxy buffering (Pitfall §5).
 * See template/web/src/lib/events.ts for the rationale.
 *
 * REQUIREMENTS: A running FastAPI backend (uvicorn on :8000) with the
 * /__debug/events SSE endpoint (Phase 4 HARN-03 debug router) is required for
 * this spec to assert a live event. In CI, the full-stack combo (backend-web /
 * full) starts both uvicorn and vite preview before running Playwright.
 */
import { test, expect } from "@playwright/test";

test("SSE EventSource receives a MessageEvent within 3 seconds", async ({ page }) => {
  // Navigate to the app first to establish a same-origin page context.
  await page.goto("/");

  // Use page.evaluate to run an in-browser Promise that:
  //   1. Opens an EventSource to the FastAPI /__debug/events SSE endpoint
  //      using the absolute URL (Pitfall §5 proxy bypass).
  //   2. Resolves with the event data string on the first onmessage callback.
  //   3. Rejects after a 3000ms timeout if no event arrives.
  const received = await page.evaluate(() => {
    return new Promise<boolean>((resolve, reject) => {
      const source = new EventSource("http://localhost:8000/__debug/events");

      const timer = setTimeout(() => {
        source.close();
        reject(new Error("SSE timeout: no MessageEvent received within 3000ms"));
      }, 3000);

      source.onmessage = () => {
        clearTimeout(timer);
        source.close();
        resolve(true);
      };

      source.onerror = (err) => {
        clearTimeout(timer);
        source.close();
        reject(new Error(`SSE connection error: ${JSON.stringify(err)}`));
      };
    });
  });

  expect(received).toBe(true);
});
