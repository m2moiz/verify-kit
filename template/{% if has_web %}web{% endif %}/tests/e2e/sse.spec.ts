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
 * /__debug/events SSE endpoint (Phase 4 HARN-03 debug router). This spec is an
 * integration test against that live dependency: it probes the backend first
 * and SKIPS (does not fail) when :8000 is unreachable, so the frontend
 * `just verify` passes standalone. The live MessageEvent assertion runs whenever
 * a backend is up — local dev (`just dev`), or a full-stack run that starts
 * uvicorn before Playwright. Skip ≠ pass: a skipped run means the assertion was
 * not exercised, not that SSE works.
 */
import { test, expect } from "@playwright/test";

const SSE_URL = "http://localhost:8000/__debug/events";
const HEALTH_URL = "http://localhost:8000/healthz";

test("SSE EventSource receives a MessageEvent within 3 seconds", async ({ page, request }) => {
  // Probe the backend; skip (not fail) when it is not reachable. A frontend
  // `just verify` must not hard-require a live backend on a fixed port.
  let backendUp = false;
  try {
    const resp = await request.get(HEALTH_URL, { timeout: 2000 });
    backendUp = resp.ok();
  } catch {
    backendUp = false;
  }
  test.skip(!backendUp, `FastAPI backend not reachable at ${HEALTH_URL} — SSE assertion requires a live backend`);

  // Navigate to the app first to establish a same-origin page context.
  await page.goto("/");

  // Use page.evaluate to run an in-browser Promise that:
  //   1. Opens an EventSource to the FastAPI /__debug/events SSE endpoint
  //      using the absolute URL (Pitfall §5 proxy bypass).
  //   2. Resolves with the event data string on the first onmessage callback.
  //   3. Rejects after a 3000ms timeout if no event arrives.
  const received = await page.evaluate((sseUrl) => {
    return new Promise<boolean>((resolve, reject) => {
      const source = new EventSource(sseUrl);

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
  }, SSE_URL);

  expect(received).toBe(true);
});
